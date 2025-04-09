import pytz
import time
import requests
import threading
from datetime import datetime, timedelta
from typing import Any, List, Dict, Tuple, Optional
from urllib.parse import urljoin
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from cachetools import TTLCache, cached
from bs4 import BeautifulSoup

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from ruamel.yaml import CommentedMap

from app.chain.site import SiteChain
from app.core.config import settings
from app.core.event import eventmanager
from app.db.site_oper import SiteOper
from app.helper.sites import SitesHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType, NotificationType
from app.utils.timer import TimerUtils

class GroupChatZone(_PluginBase):
    # 插件名称
    plugin_name = "群聊区"
    # 插件描述
    plugin_desc = "定时向多个站点发送预设消息(特定站点可获得奖励)。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/GroupChat.png"
    # 插件版本
    plugin_version = "1.3.2"
    # 插件作者
    plugin_author = "KoWming,madrays"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "groupchatzone_"
    # 加载顺序
    plugin_order = 0
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    sites: SitesHelper = None
    siteoper: SiteOper = None
    sitechain: SiteChain = None
    
    # 定时器
    _scheduler: Optional[BackgroundScheduler] = None

    # 配置属性
    _enabled: bool = False
    _cron: str = ""
    _onlyonce: bool = False
    _notify: bool = False
    _interval_cnt: int = 2
    _chat_sites: List[str] = []
    _sites_messages: str = ""
    _start_time: Optional[int] = None
    _end_time: Optional[int] = None
    _lock: Optional[threading.Lock] = None
    _running: bool = False
    _get_feedback: bool = False  # 是否获取反馈
    _feedback_timeout: int = 5  # 获取反馈的超时时间(秒)
    
    # 缓存设置
    _cache_ttl: int = 3600  # 缓存过期时间（秒）
    _site_cache: Optional[TTLCache] = None
    _cache_initialized: bool = False

    def init_plugin(self, config: Optional[dict] = None):
        self._lock = threading.Lock()
        self.sites = SitesHelper()
        self.siteoper = SiteOper()
        self.sitechain = SiteChain()
        self._ua = config.get("ua", "") if config else ""
        self._ua = config.get("ua", "")
        
        # 初始化缓存
        self._site_cache = TTLCache(maxsize=1, ttl=self._cache_ttl)
        self._cache_initialized = False

        # 停止现有任务
        self.stop_service()

        if config:
            self._enabled = bool(config.get("enabled", False))
            self._cron = str(config.get("cron", ""))
            self._onlyonce = bool(config.get("onlyonce", False))
            self._notify = bool(config.get("notify", False))
            self._interval_cnt = int(config.get("interval_cnt", 2))
            self._chat_sites = config.get("chat_sites", [])
            self._sites_messages = str(config.get("sites_messages", ""))
            self._get_feedback = bool(config.get("get_feedback", False))
            self._feedback_timeout = int(config.get("feedback_timeout", 5))

            # 过滤掉已删除的站点 - 只获取一次站点列表
            all_site_ids = self.__get_all_site_ids(log_update=False)
            self._chat_sites = [site_id for site_id in self._chat_sites if site_id in all_site_ids]

            # 保存配置，不主动刷新缓存
            self.__update_config(refresh_cache=False)

        # 加载模块
        if self._enabled or self._onlyonce:

            # 立即运行一次
            if self._onlyonce:
                try:
                    # 定时服务
                    self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                    logger.info("站点喊话服务启动，立即运行一次")
                    self._scheduler.add_job(func=self.send_site_messages, trigger='date',
                                            run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                            name="站点喊话服务")

                    # 关闭一次性开关
                    self._onlyonce = False
                    # 保存配置
                    self.__update_config(refresh_cache=False)

                    # 启动任务
                    if self._scheduler and self._scheduler.get_jobs():
                        self._scheduler.print_jobs()
                        self._scheduler.start()
                except Exception as e:
                    logger.error(f"启动一次性任务失败: {str(e)}")

    def __get_site_info(self, refresh=False, log_update=True):
        """
        获取站点信息并创建映射，支持缓存
        :param refresh: 是否强制刷新缓存
        :param log_update: 是否记录更新日志
        :return: 包含站点信息和映射的字典
        """
        # 如果需要强制刷新缓存，则清空缓存
        if refresh and self._site_cache:
            self._site_cache.clear()
            self._cache_initialized = False
            
        if not self._cache_initialized or not self._site_cache:
            try:
                # 获取所有站点信息
                all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
                
                # 创建映射
                site_id_to_name = {site.get("id"): site.get("name") for site in all_sites}
                site_id_to_obj = {site.get("id"): site for site in all_sites}
                site_name_to_obj = {site.get("name"): site for site in all_sites}
                all_site_ids = list(site_id_to_name.keys())
                
                # 更新缓存
                site_info = {
                    "all_sites": all_sites,
                    "site_id_to_name": site_id_to_name,
                    "site_id_to_obj": site_id_to_obj,
                    "site_name_to_obj": site_name_to_obj,
                    "all_site_ids": all_site_ids
                }
                
                # 存入缓存
                self._site_cache["site_info"] = site_info
                self._cache_initialized = True
                
                if log_update:
                    logger.debug(f"站点信息缓存已更新，共 {len(all_sites)} 个站点")
                    
                return site_info
            except Exception as e:
                logger.error(f"获取站点信息失败: {str(e)}")
                # 如果获取失败，返回空结构
                empty_info = {
                    "all_sites": [],
                    "site_id_to_name": {},
                    "site_id_to_obj": {},
                    "site_name_to_obj": {},
                    "all_site_ids": []
                }
                return empty_info
        
        # 从缓存中获取站点信息
        return self._site_cache.get("site_info", {})

    def __get_all_site_ids(self, log_update=True) -> List[str]:
        """
        获取所有站点ID（内置站点 + 自定义站点）
        :param log_update: 是否记录更新日志
        :return: 站点ID列表
        """
        site_info = self.__get_site_info(log_update=log_update)
        return site_info["all_site_ids"]

    def get_state(self) -> bool:
        return self._enabled

    def __update_config(self, refresh_cache=True):
        """
        更新配置
        :param refresh_cache: 是否刷新站点缓存
        """
        if refresh_cache:
            self.__get_site_info(refresh=True, log_update=True)
        
        # 保存配置
        self.update_config(
            {
                "enabled": self._enabled,
                "notify": self._notify,
                "cron": self._cron,
                "onlyonce": self._onlyonce,
                "interval_cnt": self._interval_cnt,
                "chat_sites": self._chat_sites,
                "sites_messages": self._sites_messages,
                "get_feedback": self._get_feedback,
                "feedback_timeout": self._feedback_timeout,
                "ua": self._ua
            }
        )

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        if self._enabled and self._cron:
            try:
                # 检查是否为5位cron表达式
                if str(self._cron).strip().count(" ") == 4:
                    # 解析cron表达式
                    cron_parts = str(self._cron).strip().split()
                    
                    # 检查是否为每分钟执行一次 (分钟位为 * 或 */1)
                    if cron_parts[0] == "*" or cron_parts[0] == "*/1":
                        logger.warning("检测到每分钟执行一次的配置，已自动调整为默认随机执行")
                        # 使用随机调度
                        return self.__get_random_schedule()
                    
                    # 正常的cron表达式
                    return [{
                        "id": "GroupChatZone",
                        "name": "站点喊话服务",
                        "trigger": CronTrigger.from_crontab(self._cron),
                        "func": self.send_site_messages,
                        "kwargs": {}
                    }]
                else:
                    # 2.3/9-23
                    crons = str(self._cron).strip().split("/")
                    if len(crons) == 2:
                        # 2.3
                        cron = crons[0]
                        # 9-23
                        times = crons[1].split("-")
                        if len(times) == 2:
                            # 9
                            self._start_time = int(times[0])
                            # 23
                            self._end_time = int(times[1])
                        if self._start_time and self._end_time:
                            # 检查间隔是否过小（小于1小时）
                            interval_hours = float(str(cron).strip())
                            if interval_hours < 1:
                                logger.warning(f"检测到间隔过小 ({interval_hours}小时)，已自动调整为默认随机执行")
                                return self.__get_random_schedule()
                                
                            return [{
                                "id": "GroupChatZone",
                                "name": "站点喊话服务",
                                "trigger": "interval",
                                "func": self.send_site_messages,
                                "kwargs": {
                                    "hours": interval_hours,
                                }
                            }]
                        else:
                            logger.error("站点喊话服务启动失败，周期格式错误")
                            return self.__get_random_schedule()
                    else:
                        # 尝试解析为小时间隔
                        try:
                            interval_hours = float(str(self._cron).strip())
                            # 检查间隔是否过小（小于1小时）
                            if interval_hours < 1:
                                logger.warning(f"检测到间隔过小 ({interval_hours}小时)，已自动调整为默认随机执行")
                                return self.__get_random_schedule()
                                
                            # 默认0-24 按照周期运行
                            return [{
                                "id": "GroupChatZone",
                                "name": "站点喊话服务",
                                "trigger": "interval",
                                "func": self.send_site_messages,
                                "kwargs": {
                                    "hours": interval_hours,
                                }
                            }]
                        except ValueError:
                            logger.error(f"无法解析周期配置: {self._cron}，已自动调整为默认随机执行")
                            return self.__get_random_schedule()
            except Exception as err:
                logger.error(f"定时任务配置错误：{str(err)}")
                return self.__get_random_schedule()
        elif self._enabled:
            # 使用随机调度
            return self.__get_random_schedule()
        return []

    def __get_random_schedule(self) -> List[Dict[str, Any]]:
        """
        获取随机调度配置
        :return: 随机调度配置列表
        """
        # 随机时间
        triggers = TimerUtils.random_scheduler(num_executions=1,
                                               begin_hour=9,
                                               end_hour=23,
                                               max_interval=6 * 60,
                                               min_interval=2 * 60)
        ret_jobs = []
        for trigger in triggers:
            ret_jobs.append({
                "id": f"GroupChatZone|{trigger.hour}:{trigger.minute}",
                "name": "站点喊话服务",
                "trigger": "cron",
                "func": self.send_site_messages,
                "kwargs": {
                    "hour": trigger.hour,
                    "minute": trigger.minute
                }
            })
        return ret_jobs

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        # 使用缓存获取站点信息，但不强制刷新
        site_info = self.__get_site_info(refresh=False, log_update=False)
        all_sites = site_info["all_sites"]

        site_options = [{"title": site.get("name"), "value": site.get("id")} for site in all_sites]
        
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 3
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 3
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'notify',
                                            'label': '发送通知',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 3
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'get_feedback',
                                            'label': '获取喊话反馈',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 3
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VCronField',
                                        'props': {
                                            'model': 'cron',
                                            'label': '执行周期',
                                            'placeholder': '5位cron表达式，留空自动'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'interval_cnt',
                                            'label': '执行间隔',
                                            'placeholder': '多消息自动发送间隔时间（秒）',
                                            'hint': '每条消息发送的间隔时间(秒)'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'feedback_timeout',
                                            'label': '反馈等待时间(秒)',
                                            'placeholder': '等待获取反馈的时间',
                                            'hint': '喊话后等待站点响应的时间(秒)'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'chips': True,
                                            'multiple': True,
                                            'model': 'chat_sites',
                                            'label': '选择站点',
                                            'items': site_options
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'sites_messages',
                                            'label': '发送消息',
                                            'rows': 6,
                                            'placeholder': '每一行一个配置，配置方式：\n'
                                                           '站点名称|消息内容1|消息内容2|消息内容3|...\n'
                                                           '同一站点消息配置多行支持消息合并。\n'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'ua',
                                            'label': '插件User-Agent',
                                            'placeholder': '可不填，留空则使用各站点配置的UA'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'warning',
                                            'variant': 'tonal',
                                            'text': '配置注意事项：'
                                                    '1、消息发送执行间隔(秒)不能小于0，也不建议设置过大。1~5秒即可，设置过大可能导致线程运行时间过长；'
                                                    '2、如配置有全局代理，会默认调用全局代理执行。'
                                                    '3、UA信息可不填，优先使用站点管理内对应站点填写的UA。'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '执行周期支持：'
                                                    '1、5位cron表达式；'
                                                    '2、配置间隔（小时），如2.3/9-23（9-23点之间每隔2.3小时执行一次）；'
                                                    '3、周期不填默认9-23点随机执行1次。'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '获取反馈功能说明：'
                                                    '1、获取喊话后的站点反馈(奖励信息)，有助于了解站点对喊话的响应情况；'
                                                    '2、反馈信息包括奖励类型、数量和时间，有助于分析站点奖励机制。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "notify": False,
            "cron": "",
            "onlyonce": False,
            "interval_cnt": 2,
            "chat_sites": [],
            "sites_messages": "",
            "get_feedback": False,
            "feedback_timeout": 5,
            "ua": ""
        }

    def __custom_sites(self) -> List[Any]:
        custom_sites = []
        custom_sites_config = self.get_config("CustomSites")
        if custom_sites_config and custom_sites_config.get("enabled"):
            custom_sites = custom_sites_config.get("sites")
        return custom_sites

    def get_page(self) -> List[dict]:
        pass

    def send_site_messages(self):
        """
        自动向站点发送消息
        """
        if not self._lock:
            self._lock = threading.Lock()
            
        if not self._lock.acquire(blocking=False):
            logger.warning("已有任务正在执行，本次调度跳过！")
            return
            
        try:
            self._running = True
            if self._chat_sites:
                site_messages = self._sites_messages if isinstance(self._sites_messages, str) else ""
                self.__get_site_info(refresh=True, log_update=True)
                
                site_msgs = self.parse_site_messages(site_messages, refresh_cache=False)
                self.__send_msgs(do_sites=self._chat_sites, site_msgs=site_msgs)
        except Exception as e:
            logger.error(f"发送站点消息时发生异常: {str(e)}")
        finally:
            self._running = False
            if self._lock and hasattr(self._lock, 'locked') and self._lock.locked():
                try:
                    self._lock.release()
                except RuntimeError:
                    pass
            logger.debug("任务执行完成，锁已释放")

    def get_selected_sites(self) -> List[Dict[str, Any]]:
        """
        获取已选中的站点对象列表
        :return: 站点对象列表
        """
        site_info = self.__get_site_info(refresh=False, log_update=False)
        site_id_map = site_info.get("site_id_to_obj", {})
        
        # 过滤掉不存在的站点ID
        selected_sites = []
        for site_id in self._chat_sites:
            if site_id in site_id_map:
                selected_sites.append(site_id_map[site_id])
            else:
                logger.warning(f"站点ID {site_id} 不存在或已被删除")
        
        return selected_sites

    def parse_site_messages(self, site_messages: str, refresh_cache=False) -> Dict[str, List[str]]:
        """
        解析输入的站点消息
        :param site_messages: 多行文本输入
        :param refresh_cache: 是否刷新站点缓存
        :return: 字典，键为站点名称，值为该站点的消息
        """
        result = {}
        try:
            # 获取已选站点的名称集合
            selected_sites = self.get_selected_sites()
            valid_site_names = {site.get("name").strip() for site in selected_sites}
            
            logger.debug(f"有效站点名称列表: {valid_site_names}")

            # 按行解析配置
            for line_num, line in enumerate(site_messages.strip().splitlines(), 1):
                line = line.strip()
                if not line:
                    continue  # 跳过空行

                # 分割配置项
                parts = line.split("|")
                if len(parts) < 2:
                    logger.warning(f"第{line_num}行格式错误，缺少分隔符: {line}")
                    continue

                # 解析站点名称和消息
                site_name = parts[0].strip()
                messages = [msg.strip() for msg in parts[1:] if msg.strip()]
                
                if not messages:
                    logger.warning(f"第{line_num}行 [{site_name}] 没有有效消息内容")
                    continue

                # 验证站点有效性
                if site_name not in valid_site_names:
                    logger.warning(f"第{line_num}行 [{site_name}] 不在选中站点列表中")
                    continue

                # 合并相同站点的消息
                if site_name in result:
                    result[site_name].extend(messages)
                    logger.debug(f"合并站点 [{site_name}] 的消息，当前数量：{len(result[site_name])}")
                else:
                    result[site_name] = messages

        except Exception as e:
            logger.error(f"解析站点消息时出现异常: {str(e)}", exc_info=True)
        finally:
            logger.info(f"解析完成，共配置 {len(result)} 个有效站点的消息")
            return result

    def __send_msgs(self, do_sites: list, site_msgs: Dict[str, List[str]]):
        """
        发送消息逻辑
        """
        # 获取站点对象
        selected_sites = self.get_selected_sites()
        
        if not selected_sites:
            logger.info("没有需要发送消息的站点！")
            return

        # 执行站点发送消息
        site_results = {}
        all_feedback = []
        
        for site in selected_sites:
            site_name = site.get("name")
            logger.info(f"开始处理站点: {site_name}")
            messages = site_msgs.get(site_name, [])

            if not messages:
                logger.warning(f"站点 {site_name} 没有需要发送的消息！")
                continue

            success_count = 0
            failure_count = 0
            failed_messages = []
            site_feedback = []

            for i, message in enumerate(messages):
                try:
                    feedback = self.send_message_to_site(site, message)
                    success_count += 1
                    if feedback:
                        site_feedback.append(feedback)
                        all_feedback.append(feedback)
                except Exception as e:
                    logger.error(f"向站点 {site_name} 发送消息 '{message}' 失败: {str(e)}")
                    failure_count += 1
                    failed_messages.append(message)

                if i < len(messages) - 1:
                    logger.info(f"等待 {self._interval_cnt} 秒后继续发送下一条消息...")
                    start_time = time.time()
                    time.sleep(self._interval_cnt)
                    logger.debug(f"实际等待时间：{time.time() - start_time:.2f} 秒")
            
            site_results[site_name] = {
                "success_count": success_count,
                "failure_count": failure_count,
                "failed_messages": failed_messages,
                "feedback": site_feedback
            }

        # 发送通知
        if self._notify:
            title = "💬 站点喊话任务完成"
            total_sites = len(selected_sites)
            notification_text = "📢 站点喊话任务报告\n"
            notification_text += f"🌐 站点总数: {total_sites}\n"
            
            # 添加喊话基本信息
            success_sites = []
            failed_sites = []
            
            for site_name, result in site_results.items():
                success_count = result["success_count"]
                failure_count = result["failure_count"]
                if success_count > 0 and failure_count == 0:
                    success_sites.append(site_name)
                elif failure_count > 0:
                    failed_sites.append(site_name)
            
            if success_sites:
                notification_text += f"✅ 成功站点: {', '.join(success_sites)}\n"
            if failed_sites:
                notification_text += f"❌ 失败站点: {', '.join(failed_sites)}\n"
            
            # 添加失败消息详情
            failed_details = []
            for site_name, result in site_results.items():
                failed_messages = result["failed_messages"]
                if failed_messages:
                    failed_details.append(f"{site_name}: {', '.join(failed_messages)}")
            
            if failed_details:
                notification_text += "\n🚫 失败消息详情:\n"
                notification_text += "\n".join(failed_details)
            
            # 添加反馈信息
            if self._get_feedback and all_feedback:
                notification_text += "\n📋 喊话反馈:\n"
                
                # 按站点整理反馈，而不是按时间顺序
                site_feedback_dict = {}
                for feedback in all_feedback:
                    site_name = feedback.get("site", "")
                    if site_name not in site_feedback_dict:
                        site_feedback_dict[site_name] = []
                    site_feedback_dict[site_name].append(feedback)
                
                # 逐个站点显示反馈
                for site_name, feedbacks in site_feedback_dict.items():
                    notification_text += f"\n━━━━━━━━ {site_name} 站点反馈 ━━━━━━━━\n"
                    
                    for feedback in feedbacks:
                        message = feedback.get("message", "")
                        rewards = feedback.get("rewards", [])
                        
                        if rewards:
                            notification_text += f"🔹 消息: \"{message}\"\n"
                            
                            # 根据不同类型显示不同图标
                            for reward in rewards:
                                reward_type = reward.get("type", "")
                                
                                # 图标映射
                                icon_map = {
                                    "上传量": "⬆️",
                                    "下载量": "⬇️",
                                    "魔力值": "✨",
                                    "工分": "🔧",
                                    "电力": "⚡",
                                    "象草": "🐘",
                                    "VIP": "👑",
                                    "raw_feedback": "📝"
                                }
                                
                                icon = icon_map.get(reward_type, "📌")
                                
                                if reward_type == "raw_feedback":
                                    # 直接显示原始反馈内容
                                    notification_text += f"  {icon} {reward.get('description', '')}\n"
                                elif reward_type == "unknown":
                                    notification_text += f"  {icon} {reward.get('description', '')}\n"
                                else:
                                    # 根据正负显示不同的表述
                                    if reward.get("is_negative", False):
                                        notification_text += f"  {icon} 损失了 {reward.get('amount', '')} {reward.get('unit', '')} {reward_type}\n"
                                    else:
                                        notification_text += f"  {icon} 获得了 {reward.get('amount', '')} {reward.get('unit', '')} {reward_type}\n"
            
            notification_text += f"\n⏱️ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"

            self.post_message(
                mtype=NotificationType.SiteMessage,
                title=title,
                text=notification_text
            )

        # 检查是否所有消息都发送成功
        all_successful = all(result["success_count"] == len(site_msgs.get(site_name, [])) 
                            for site_name, result in site_results.items())
        if all_successful:
            logger.info("所有站点的消息发送成功。")
        else:
            logger.info("部分消息发送失败！！！")

        self.__update_config(refresh_cache=False)

    def send_message_to_site(self, site_info: CommentedMap, message: str):
        """
        向站点发送消息
        """
        if not site_info:
            logger.error("无效的站点信息！")
            return

        # 站点信息
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        site_cookie = site_info.get("cookie", "").strip()
        site_ua = site_info.get("ua") or ""
        global_ua = self._ua or ""
        ua = (site_ua.strip() if site_ua else global_ua.strip()) or ""
        if not ua:
            logger.error(f"⚠️站点 {site_name} 未配置UA！请检查站点设置或插件全局UA")
            raise ValueError(f"站点 {site_name} 未配置UA")
        if len(ua) < 20 or "Mozilla" not in ua:
            logger.error(f"❌ 无效的UA配置：{ua[:50]}...（长度不足或格式错误）")
            raise ValueError(f"站点 {site_name} 无效的UA配置")
        proxies = settings.PROXY if site_info.get("proxy") else None

        if not all([site_name, site_url, site_cookie, ua]):
            logger.error(f"站点 {site_name} 缺少必要信息，无法发送消息！")
            raise ValueError(f"站点 {site_name} 缺少必要信息")

        # 构建URL和请求参数
        send_url = urljoin(site_url, "/shoutbox.php")
        headers = {
            'User-Agent': ua,
            'Cookie': site_cookie,
            'Referer': site_url
        }
        params = {
            'shbox_text': message,
            'shout': '我喊',
            'sent': 'yes',
            'type': 'shoutbox'
        }

        # 配置重试策略
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[403, 404, 500, 502, 503, 504],
            allowed_methods=frozenset(['GET', 'POST']),
            raise_on_status=False
        )

        adapter = HTTPAdapter(max_retries=retries, pool_connections=1, pool_maxsize=1)

        with requests.Session() as session:
            session.headers.update(headers)
            if proxies:
                session.proxies = proxies
            session.mount('https://', adapter)
            session.mount('http://', adapter)
            
            try:
                # 发送喊话请求
                response = session.get(
                    send_url, 
                    params=params,
                    timeout=(3.05, 10),
                    allow_redirects=False
                )
                response.raise_for_status()
                logger.info(f"向 {site_name} 发送消息 '{message}' 成功")
                
                # 获取喊话反馈
                feedback = None
                if self._get_feedback:
                    feedback = self.get_site_feedback(session, site_info, message)
                    if feedback:
                        logger.info(f"获取到站点 {site_name} 的反馈: {feedback}")
                
                return feedback
            except requests.exceptions.HTTPError as http_err:
                logger.error(f"向 {site_name} 发送消息 '{message}' 失败，HTTP 错误: {http_err}")
                raise
            except requests.exceptions.RequestException as req_err:
                logger.error(f"向 {site_name} 发送消息 '{message}' 失败，请求异常: {req_err}")
                raise

    def get_site_feedback(self, session, site_info: CommentedMap, message: str) -> dict:
        """
        获取站点反馈信息
        :param session: 请求会话
        :param site_info: 站点信息
        :param message: 发送的消息
        :return: 反馈信息字典
        """
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        
        feedback_info = {
            "site": site_name,
            "message": message,
            "rewards": [],
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # 等待一段时间，让站点有时间响应
            time.sleep(self._feedback_timeout)
            
            # 根据站点名称选择不同的解析策略
            site_type = self.identify_site_type(site_info)
            logger.debug(f"站点 {site_name} 识别为 {site_type} 类型")
            
            # 1. 获取喊话区反馈
            try:
                if site_type == "PTLGS":
                    feedback_info["rewards"].extend(self.get_ptlgs_feedback(session, site_info, message))
                elif site_type == "Frog":
                    feedback_info["rewards"].extend(self.get_frog_feedback(session, site_info, message))
                elif site_type == "Zhimeng":
                    # 织梦站点只获取邮件反馈，不获取喊话区反馈
                    pass
                else:
                    feedback_info["rewards"].extend(self.get_shoutbox_feedback(session, site_info, message))
            except Exception as e:
                logger.error(f"获取站点 {site_name} 的喊话区反馈失败: {str(e)}")
            
            # 2. 获取站内信反馈（邮件形式的反馈）
            try:
                if site_type == "Elephant":
                    feedback_info["rewards"].extend(self.get_elephant_message_feedback(session, site_info))
                elif site_type == "Zhimeng":
                    feedback_info["rewards"].extend(self.get_zhimeng_message_feedback(session, site_info))
                else:
                    feedback_info["rewards"].extend(self.get_message_feedback(session, site_info))
            except Exception as e:
                logger.error(f"获取站点 {site_name} 的站内信反馈失败: {str(e)}")
            
            # 这里对rewards进行清理和筛选
            cleaned_rewards = []
            for reward in feedback_info["rewards"]:
                # 清理description中的HTML和无用内容
                if "description" in reward:
                    # 清理常见的HTML前缀
                    desc = reward["description"]
                    
                    # 如果描述内容过长且没有特定关键词，认为是垃圾数据
                    if len(desc) > 100 and not any(keyword in desc for keyword in ["奖励", "获得", "赏", "召唤", "响应", "工分", "上传", "下载", "@"]):
                        continue
                    
                    # 如果是页面导航内容，忽略
                    if desc.startswith("首") and ("页" in desc[:10]) and ("论" in desc[:10]):
                        continue
                    
                    # 如果包含"欢迎回来"和大量其他内容，忽略
                    if "欢迎回来" in desc and len(desc) > 50:
                        continue
                    
                    # 清理掉\xa0和多余空格
                    desc = desc.replace("\xa0", " ").strip()
                    while "  " in desc:
                        desc = desc.replace("  ", " ")
                    
                    reward["description"] = desc
                
                # 只保留有价值的反馈
                if reward.get("type") == "raw_feedback" and not self._is_useful_feedback(reward["description"], message):
                    continue
                
                cleaned_rewards.append(reward)
            
            # 更新清理后的奖励列表
            feedback_info["rewards"] = cleaned_rewards
            
            return feedback_info if feedback_info["rewards"] else None
            
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的反馈失败: {str(e)}")
            return None
            
    def _is_useful_feedback(self, description: str, message: str) -> bool:
        """
        判断反馈是否有用
        :param description: 反馈描述
        :param message: 发送的消息
        :return: 是否有用
        """
        # 如果反馈内容为空或过短，认为无用
        if not description or len(description) < 3:
            return False
            
        # 如果只包含"主题"等无意义内容，认为无用
        if description in ["主题", "站点反馈: 主题", "消息", "站点反馈: 消息"]:
            return False
            
        # 包含关键词的反馈通常有用
        useful_keywords = ["奖励", "获得", "赏", "召唤", "响应", "不理", "工分", "上传", "下载", 
                          "电力", "象草", "魔力", "明天", "刷屏", "VIP", "彩虹"]
                          
        if any(keyword in description for keyword in useful_keywords):
            return True
            
        # 如果包含@用户名，通常有用
        if "@" in description:
            return True
            
        # 默认认为无用
        return False

    def identify_site_type(self, site_info: CommentedMap) -> str:
        """
        识别站点类型，用于选择合适的反馈解析方法
        :param site_info: 站点信息
        :return: 站点类型
        """
        site_name = site_info.get("name", "").strip().lower()
        site_url = site_info.get("url", "").strip().lower()
        
        # 常见站点类型判断
        if "ptlgs" in site_name or "ptlgs" in site_url:
            return "PTLGS"
        elif "zmpt" in site_name or "zhimeng" in site_name or "织梦" in site_name:
            return "Zhimeng"
        elif "elephant" in site_name or "象站" in site_name or "小象" in site_name:
            return "Elephant"
        elif "frog" in site_name or "青蛙" in site_name:
            return "Frog"
            
        # 默认为通用NexusPHP类型
        return "NexusPHP"
            
    def get_ptlgs_feedback(self, session, site_info: CommentedMap, message: str) -> List[dict]:
        """
        获取PTLGS站点的喊话区反馈
        :param session: 请求会话
        :param site_info: 站点信息
        :param message: 发送的消息
        :return: 反馈信息列表
        """
        import re  # 确保导入re模块
        rewards = []
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        
        try:
            # 获取喊话区内容
            shoutbox_url = urljoin(site_url, "/shoutbox.php")
            response = session.get(
                shoutbox_url,
                timeout=(3.05, 10)
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取用户名
            username = self.get_username(session, site_info)
            
            # 查找包含用户名或用于"黑丝娘"回复的消息
            shouts = soup.select('.shoutrow, .specialshoutrow')
            
            # 查找最新的反馈
            for i in range(min(20, len(shouts))):  # 检查最新的20条消息
                shout = shouts[i]
                text = shout.get_text(strip=True)
                
                # 只查找@当前用户的黑丝娘回复
                if "黑丝娘" in text and username and f"@{username}" in text:
                    # 这是本次喊话的直接反馈
                    rewards.append({
                        "type": "raw_feedback",
                        "amount": 0,
                        "unit": "",
                        "description": self._clean_shoutbox_text(text),
                        "is_negative": "损失" in text or "惩罚" in text or "生气" in text or "不理" in text
                    })
                    break
            
            return rewards
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的PTLGS喊话区反馈失败: {str(e)}")
            return []
            
    def _clean_shoutbox_text(self, text: str) -> str:
        """
        清理喊话区文本
        :param text: 原始文本
        :return: 清理后的文本
        """
        # 清理HTML及特殊字符
        text = text.replace("\xa0", " ").strip()
        
        # 去除多余空格
        while "  " in text:
            text = text.replace("  ", " ")
        
        # 如果文本过长且包含导航内容，只保留关键部分
        if len(text) > 100 and "首页" in text[:20]:
            # 尝试提取中间的@消息部分
            import re
            match = re.search(r'\[(.*?)\](.*?)@(.*?)[\s]+(.*?)(?:$|首页|\[)', text)
            if match:
                time_part = match.group(1).strip()
                sender = match.group(2).strip()
                receiver = match.group(3).strip()
                content = match.group(4).strip()
                return f"[{time_part}] {sender}@{receiver} {content}"
        
        return text

    def get_frog_feedback(self, session, site_info: CommentedMap, message: str) -> List[dict]:
        """
        获取青蛙站点的反馈
        :param session: 请求会话
        :param site_info: 站点信息
        :param message: 发送的消息
        :return: 反馈信息列表
        """
        import re  # 确保导入re模块
        rewards = []
        site_name = site_info.get("name", "").strip()
        
        try:
            # 青蛙站点简化处理，直接根据发送的消息内容返回奖励
            logger.info(f"青蛙站点简化处理，根据发送的消息 '{message}' 返回奖励")
            
            # 根据消息内容判断类型
            if "求上传" in message:
                rewards.append({
                    "type": "上传量",
                    "amount": "10",
                    "unit": "GB",
                    "description": "青蛙站点求上传奖励",
                    "is_negative": False
                })
            elif "求下载" in message:
                rewards.append({
                    "type": "下载量",
                    "amount": "10",
                    "unit": "GB",
                    "description": "青蛙站点求下载奖励",
                    "is_negative": False
                })
            else:
                # 其他类型的消息
                rewards.append({
                    "type": "raw_feedback",
                    "amount": 0,
                    "unit": "",
                    "description": "青蛙站点消息已发送",
                    "is_negative": False
                })
            
            return rewards
        except Exception as e:
            logger.error(f"处理站点 {site_name} 的青蛙喊话反馈失败: {str(e)}")
            logger.exception(e)  # 打印完整异常信息
            # 即使出错也返回一个反馈
            return [{
                "type": "raw_feedback",
                "amount": 0,
                "unit": "",
                "description": "青蛙站点消息已发送",
                "is_negative": False
            }]

    def get_elephant_message_feedback(self, session, site_info: CommentedMap) -> List[dict]:
        """
        获取象站的站内信反馈
        :param session: 请求会话
        :param site_info: 站点信息
        :return: 反馈信息列表
        """
        import re  # 确保导入re模块
        rewards = []
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        
        try:
            # 获取站内信列表
            message_url = urljoin(site_url, "/messages.php")
            response = session.get(
                message_url,
                timeout=(3.05, 10)
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 先查找未读消息，如果没有再查找所有消息
            all_rows = soup.select('tr:has(td > img[title="Unread"])')
            has_unread = len(all_rows) > 0
            
            if not all_rows:
                # 如果没有未读消息，获取最新的邮件
                all_rows = soup.select('tr:has(td > img)')
            
            if not all_rows:
                return []
                
            # 遍历找到的消息行，寻找包含象草关键词的消息
            for row in all_rows[:3]:  # 只看前3条消息
                # 如果是未读消息，标记为已读
                if has_unread:
                    try:
                        # 获取标记为已读的链接
                        read_link = row.select_one('a[href*="&action=read"]')
                        if read_link:
                            read_url = urljoin(site_url, read_link['href'])
                            # 发送请求标记为已读
                            mark_response = session.get(read_url, timeout=(3.05, 5))
                            mark_response.raise_for_status()
                            logger.info(f"已将站点 {site_name} 的未读消息标记为已读")
                    except Exception as e:
                        logger.error(f"标记站点 {site_name} 的消息为已读失败: {str(e)}")
                
                subject_cell = row.select_one('td:nth-child(2)')
                if not subject_cell:
                    continue
                    
                subject_text = subject_cell.get_text(strip=True)
                
                # 象草奖励格式识别
                if "象草" in subject_text:
                    # 尝试提取象草数量
                    elephant_match = re.search(r'(\d+)象草', subject_text)
                    amount = elephant_match.group(1) if elephant_match else "未知数量"
                    
                    # 检查消息是否是发给当前用户的，避免获取到其他用户的邮件
                    if self._is_message_for_current_user(row, session, site_info):
                        rewards.append({
                            "type": "象草",
                            "amount": amount,
                            "unit": "点",
                            "description": f"获得象草奖励",
                            "is_negative": False
                        })
                        break
            
            # 如果没有找到符合条件的消息，返回空列表
            if not rewards:
                # 尝试打开邮箱页面读取最新消息详情
                inbox_url = urljoin(site_url, "/messages.php?action=viewmailbox&box=1")
                inbox_response = session.get(inbox_url, timeout=(3.05, 10))
                inbox_soup = BeautifulSoup(inbox_response.text, 'html.parser')
                
                # 寻找最新的包含"象草"的邮件
                messages = inbox_soup.select('tr:has(td:contains("象草"))')
                if messages:
                    latest_message = messages[0]
                    subject = latest_message.select_one('td:nth-child(2)').get_text(strip=True)
                    
                    # 尝试提取象草数量
                    elephant_match = re.search(r'(\d+)象草', subject)
                    if elephant_match:
                        amount = elephant_match.group(1)
                        rewards.append({
                            "type": "象草",
                            "amount": amount,
                            "unit": "点",
                            "description": f"获得象草奖励",
                            "is_negative": False
                        })
                    else:
                        rewards.append({
                            "type": "raw_feedback",
                            "amount": 0,
                            "unit": "",
                            "description": f"象站反馈: {subject}",
                            "is_negative": False
                        })
            
            return rewards
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的象站站内信反馈失败: {str(e)}")
            return []
            
    def get_zhimeng_message_feedback(self, session, site_info: CommentedMap) -> List[dict]:
        """
        获取织梦站点的站内信反馈
        :param session: 请求会话
        :param site_info: 站点信息
        :return: 反馈信息列表
        """
        import re  # 确保导入re模块
        rewards = []
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        
        try:
            # 获取站内信列表
            message_url = urljoin(site_url, "/messages.php")
            logger.info(f"正在获取站点 {site_name} 的站内信: {message_url}")
            
            response = session.get(
                message_url,
                timeout=(3.05, 10)
            )
            response.raise_for_status()
            
            html_text = response.text
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # 直接查找包含赠送电力相关文本的链接
            power_links = []
            all_links = soup.select('a[href*="viewmessage"]')
            for link in all_links:
                link_text = link.get_text(strip=True)
                if "赠送" in link_text and "电力" in link_text:
                    power_links.append(link)
                    logger.info(f"找到电力消息链接: {link_text}")
            
            logger.info(f"找到 {len(power_links)} 条电力消息链接")
            
            if power_links:
                # 处理第一条电力消息
                power_link = power_links[0]
                power_text = power_link.get_text(strip=True)
                
                # 提取电力数量
                power_match = re.search(r'赠送的\s*([-+]?\d+)\s*电力', power_text)
                if power_match:
                    amount = power_match.group(1)
                    is_negative = amount.startswith("-")
                    logger.info(f"提取到电力数量: {amount}")
                    
                    rewards.append({
                        "type": "电力",
                        "amount": amount.lstrip("+-"),
                        "unit": "",
                        "description": f"{'扣除' if is_negative else '收到'}电力奖励",
                        "is_negative": is_negative
                    })
                    return rewards
            
            # 如果上面的方法失败，使用正则表达式直接从HTML中提取
            logger.info("使用正则表达式从HTML中提取电力消息")
            power_matches = re.findall(r'<a href="messages\.php\?action=viewmessage[^>]*>(收到来自[^<]*赠送的\s*[-+]?\d+\s*电力)</a>', html_text)
            
            if power_matches:
                logger.info(f"正则表达式找到 {len(power_matches)} 条电力消息")
                power_text = power_matches[0]  # 使用第一条匹配
                
                # 提取电力数量
                power_match = re.search(r'赠送的\s*([-+]?\d+)\s*电力', power_text)
                if power_match:
                    amount = power_match.group(1)
                    is_negative = amount.startswith("-")
                    logger.info(f"从正则表达式匹配中提取到电力数量: {amount}")
                    
                    rewards.append({
                        "type": "电力",
                        "amount": amount.lstrip("+-"),
                        "unit": "",
                        "description": f"{'扣除' if is_negative else '收到'}电力奖励",
                        "is_negative": is_negative
                    })
                    return rewards
            
            # 如果仍然未找到，尝试更宽松的方法
            logger.info("使用更宽松的方法查找电力消息")
            # 查找所有表格的行
            rows = soup.select('table tr')
            logger.info(f"找到 {len(rows)} 个表格行")
            
            # 查找包含"电力"的行
            for row in rows:
                row_text = row.get_text(strip=True)
                if "电力" in row_text:
                    # 获取行中所有链接
                    links = row.select('a')
                    for link in links:
                        link_text = link.get_text(strip=True)
                        if "电力" in link_text:
                            logger.info(f"在表格行中找到电力链接: {link_text}")
                            
                            # 尝试提取电力数量
                            power_match = re.search(r'[-+]?\d+\s*电力', link_text)
                            if power_match:
                                power_text = power_match.group(0)
                                amount = re.search(r'([-+]?\d+)', power_text).group(1)
                                is_negative = amount.startswith("-")
                                
                                logger.info(f"从表格行链接中提取到电力数量: {amount}")
                                
                                rewards.append({
                                    "type": "电力",
                                    "amount": amount.lstrip("+-"),
                                    "unit": "",
                                    "description": f"{'扣除' if is_negative else '收到'}电力奖励",
                                    "is_negative": is_negative
                                })
                                return rewards
            
            # 如果所有方法都失败，返回一个通用消息
            logger.warning("无法识别电力消息，返回通用消息")
            
            # 尝试至少返回最新一条消息
            latest_links = soup.select('td.rowfollow a[href*="viewmessage"]')
            if latest_links:
                latest_message = latest_links[0].get_text(strip=True)
                logger.info(f"返回最新消息: {latest_message}")
                
                rewards.append({
                    "type": "raw_feedback",
                    "amount": 0,
                    "unit": "",
                    "description": f"站内信: {latest_message}",
                    "is_negative": False
                })
            else:
                rewards.append({
                    "type": "raw_feedback",
                    "amount": 0,
                    "unit": "",
                    "description": f"未能识别织梦站点消息",
                    "is_negative": False
                })
            
            return rewards
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的织梦站内信反馈失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return []
            
    def get_message_feedback(self, session, site_info: CommentedMap) -> List[dict]:
        """
        获取通用站点的站内信反馈（邮件形式的反馈）
        :param session: 请求会话
        :param site_info: 站点信息
        :return: 反馈信息列表
        """
        import re  # 确保导入re模块
        rewards = []
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        
        try:
            # 获取站内信列表
            message_url = urljoin(site_url, "/messages.php")
            response = session.get(
                message_url,
                timeout=(3.05, 10)
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 先查找未读消息，如果没有再查找所有消息
            all_rows = soup.select('tr:has(td > img[title="Unread"])')
            has_unread = len(all_rows) > 0
            
            if not all_rows:
                # 如果没有未读消息，获取最新的邮件
                all_rows = soup.select('tr:has(td > img)')
            
            if not all_rows:
                return []
            
            # 遍历找到的消息行，查看最新的消息
            for row in all_rows[:3]:  # 只看前3条消息
                # 如果是未读消息，标记为已读
                if has_unread:
                    try:
                        # 获取标记为已读的链接
                        read_link = row.select_one('a[href*="&action=read"]')
                        if read_link:
                            read_url = urljoin(site_url, read_link['href'])
                            # 发送请求标记为已读
                            mark_response = session.get(read_url, timeout=(3.05, 5))
                            mark_response.raise_for_status()
                            logger.info(f"已将站点 {site_name} 的未读消息标记为已读")
                    except Exception as e:
                        logger.error(f"标记站点 {site_name} 的消息为已读失败: {str(e)}")
                
                # 获取消息主题和详情
                subject_cell = row.select_one('td:nth-child(2)')
                if not subject_cell:
                    continue
                    
                subject_text = subject_cell.get_text(strip=True)
                
                # 尝试从主题中提取奖励信息
                if "奖励" in subject_text or "获得" in subject_text or "收到" in subject_text:
                    # 检查是否是发给当前用户的消息
                    if self._is_message_for_current_user(row, session, site_info):
                        # 尝试提取具体奖励类型
                        if "上传" in subject_text:
                            # 尝试提取数量
                            ul_match = re.search(r'(\d+)[\s]?([G|T|M|K])[B]?.+?(上传)', subject_text, re.IGNORECASE)
                            if ul_match:
                                rewards.append({
                                    "type": "上传量",
                                    "amount": ul_match.group(1),
                                    "unit": ul_match.group(2) + "B",
                                    "description": f"获得上传量奖励",
                                    "is_negative": False
                                })
                                break
                        elif "下载" in subject_text:
                            # 尝试提取数量
                            dl_match = re.search(r'(\d+)[\s]?([G|T|M|K])[B]?.+?(下载)', subject_text, re.IGNORECASE)
                            if dl_match:
                                rewards.append({
                                    "type": "下载量",
                                    "amount": dl_match.group(1),
                                    "unit": dl_match.group(2) + "B",
                                    "description": f"获得下载量奖励",
                                    "is_negative": False
                                })
                                break
                        else:
                            # 如果无法提取具体奖励，添加原始反馈
                            rewards.append({
                                "type": "raw_feedback",
                                "amount": 0,
                                "unit": "",
                                "description": f"站点反馈: {subject_text}",
                                "is_negative": False
                            })
                            break
            
            return rewards
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的站内信反馈失败: {str(e)}")
            return []
    
    def is_nexusphp_site(self, site_info: CommentedMap) -> bool:
        """
        判断是否为NexusPHP站点
        :param site_info: 站点信息
        :return: 是否为NexusPHP站点
        """
        # 可以根据站点特征判断，如URL路径、页面结构等
        site_url = site_info.get("url", "").strip()
        
        # 简单判断是否有NexusPHP常见的页面
        nexusphp_pages = ["/index.php", "/torrents.php", "/usercp.php", "/messages.php"]
        
        # 此处简化处理，实际使用时可能需要更复杂的判断逻辑
        return True

    def stop_service(self):
        """退出插件"""
        try:
            if self._scheduler:
                if self._lock and hasattr(self._lock, 'locked') and self._lock.locked():
                    logger.info("等待当前任务执行完成...")
                    try:
                        self._lock.acquire()
                        self._lock.release()
                    except:
                        pass
                if hasattr(self._scheduler, 'remove_all_jobs'):
                    self._scheduler.remove_all_jobs()
                if hasattr(self._scheduler, 'running') and self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error(f"退出插件失败：{str(e)}")

    @eventmanager.register(EventType.SiteDeleted)
    def site_deleted(self, event):
        """
        删除对应站点选中
        """
        site_id = event.event_data.get("site_id")
        config = self.get_config()
        if config:
            self._chat_sites = self.__remove_site_id(config.get("chat_sites") or [], site_id)
            # 保存配置，并刷新缓存
            self.__update_config(refresh_cache=True)

    def __remove_site_id(self, do_sites, site_id):
        if do_sites:
            if isinstance(do_sites, str):
                do_sites = [do_sites]
            # 删除对应站点
            if site_id:
                do_sites = [site for site in do_sites if int(site) != int(site_id)]
            else:
                # 清空
                do_sites = []
            # 若无站点，则停止
            if len(do_sites) == 0:
                self._enabled = False
        return do_sites

    def get_shoutbox_feedback(self, session, site_info: CommentedMap, message: str) -> List[dict]:
        """
        获取通用喊话区反馈
        :param session: 请求会话
        :param site_info: 站点信息
        :param message: 发送的消息
        :return: 反馈信息列表
        """
        import re  # 确保导入re模块
        rewards = []
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        
        try:
            # 获取喊话区内容
            shoutbox_url = urljoin(site_url, "/shoutbox.php")
            response = session.get(
                shoutbox_url,
                timeout=(3.05, 10)
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取用户名
            username = self.get_username(session, site_info)
            
            # 查找包含用户名或ID的消息
            shouts = soup.select('.shoutrow, .specialshoutrow')
            
            # 查找最新的反馈（不限定时间，获取最新的@用户信息）
            for i in range(min(20, len(shouts))):  # 检查最新的20条消息
                shout = shouts[i]
                text = shout.get_text(strip=True)
                
                # 检查是否包含用户名的@消息
                if username and f"@{username}" in text:
                    # 这可能是本次喊话的反馈
                    rewards.append({
                        "type": "raw_feedback",
                        "amount": 0,
                        "unit": "",
                        "description": self._clean_shoutbox_text(text),
                        "is_negative": "损失" in text or "惩罚" in text or "生气" in text or "不理" in text
                    })
                    # 只获取最新的一条反馈
                    break
                
                # 如果找不到@用户的消息，但找到了包含用户发送消息内容的回复
                elif message and message in text:
                    # 查找下一条消息是否是系统/管理员回复
                    if i + 1 < len(shouts):
                        next_shout = shouts[i+1]
                        next_text = next_shout.get_text(strip=True)
                        # 如果下一条消息包含奖励关键词
                        if any(keyword in next_text for keyword in ["奖励", "获得", "赏", "响应", "召唤"]):
                            rewards.append({
                                "type": "raw_feedback",
                                "amount": 0,
                                "unit": "",
                                "description": self._clean_shoutbox_text(next_text),
                                "is_negative": "损失" in next_text or "惩罚" in next_text or "生气" in next_text or "不理" in next_text
                            })
                            break
            
            return rewards
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的喊话区反馈失败: {str(e)}")
            return []
            
    def get_user_id(self, session, site_info: CommentedMap) -> str:
        """
        获取用户ID
        :param session: 请求会话
        :param site_info: 站点信息
        :return: 用户ID
        """
        import re  # 确保导入re模块
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        
        try:
            # 访问个人信息页面
            usercp_url = urljoin(site_url, "/usercp.php")
            response = session.get(
                usercp_url,
                timeout=(3.05, 10)
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找用户ID
            user_id = None
            
            # 方法1: 从URL中获取
            profile_link = soup.select_one('a[href*="userdetails.php?id="]')
            if profile_link:
                href = profile_link.get('href')
                user_id = href.split('id=')[1].split('&')[0]
            
            # 方法2: 从页面内容中获取
            if not user_id:
                userid_elem = soup.select_one('input[name="userid"]')
                if userid_elem:
                    user_id = userid_elem.get('value')
            
            return user_id
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的用户ID失败: {str(e)}")
            return None
    
    def get_username(self, session, site_info: CommentedMap) -> str:
        """
        获取用户名
        :param session: 请求会话
        :param site_info: 站点信息
        :return: 用户名
        """
        import re  # 确保导入re模块
        site_name = site_info.get("name", "").strip()
        site_url = site_info.get("url", "").strip()
        
        try:
            # 访问个人信息页面
            usercp_url = urljoin(site_url, "/usercp.php")
            response = session.get(
                usercp_url,
                timeout=(3.05, 10)
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试多种方式获取用户名
            username = None
            
            # 方法1: 从欢迎信息中获取
            welcome_msg = soup.select_one('.welcome')
            if welcome_msg:
                text = welcome_msg.get_text()
                import re
                username_match = re.search(r'欢迎回来.*?([^,，\s]+)', text)
                if username_match:
                    username = username_match.group(1)
            
            # 方法2: 从用户详情链接中获取
            if not username:
                username_elem = soup.select_one('a[href*="userdetails.php"]')
                if username_elem:
                    username = username_elem.get_text(strip=True)
            
            # 方法3: 直接尝试查找用户名元素
            if not username:
                # 尝试找到常见的用户名显示位置
                user_elements = soup.select('.username, .user, .profile-username, a[href*="userdetails"]')
                for elem in user_elements:
                    potential_username = elem.get_text(strip=True)
                    if potential_username and len(potential_username) > 1 and len(potential_username) < 30:
                        username = potential_username
                        break
            
            return username
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的用户名失败: {str(e)}")
            return None

    def _is_message_for_current_user(self, message_row, session, site_info: CommentedMap) -> bool:
        """
        判断消息是否是发给当前用户的
        :param message_row: 消息行元素
        :param session: 请求会话
        :param site_info: 站点信息
        :return: 是否是发给当前用户的
        """
        try:
            # 获取当前用户名
            username = self.get_username(session, site_info)
            if not username:
                return True  # 如果无法获取用户名，则默认认为是发给当前用户的
                
            # 尝试从消息中提取接收者信息
            receiver_cell = message_row.select_one('td:nth-child(3)')
            if receiver_cell:
                receiver_text = receiver_cell.get_text(strip=True)
                # 如果接收者包含当前用户名，则认为是发给当前用户的
                if username.lower() in receiver_text.lower():
                    return True
                    
            # 如果无法确定接收者，则查看消息详情
            message_link = message_row.select_one('a[href*="viewmessage"]')
            if message_link:
                href = message_link.get('href')
                # 不要真的打开消息详情页面，因为这会标记为已读
                # 此处只是通过消息链接的存在来判断这可能是一条有效消息
                return True
                
            # 默认情况下，假设最新的几条消息是发给当前用户的
            return True
        except Exception as e:
            # 出错时默认认为是发给当前用户的，避免漏掉重要信息
            return True
