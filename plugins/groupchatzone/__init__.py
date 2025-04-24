# 标准库导入
import inspect
import pytz
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 第三方库导入
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from ruamel.yaml import CommentedMap

# 本地应用/库导入
from app.core.config import settings
from app.core.event import eventmanager
from app.db.site_oper import SiteOper
from app.helper.module import ModuleHelper
from app.helper.sites import SitesHelper
from app.scheduler import Scheduler
from app.log import logger
from app.plugins import _PluginBase
from app.plugins.groupchatzone.sites import ISiteHandler
from app.schemas.types import EventType, NotificationType
from app.utils.timer import TimerUtils

class GroupChatZone(_PluginBase):
    # 插件名称
    plugin_name = "群聊区"
    # 插件描述
    plugin_desc = "执行站点喊话、获取反馈、定时任务。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/Octopus.png"
    # 插件版本
    plugin_version = "2.0.2"
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
    sites: SitesHelper = None      # 站点助手实例
    siteoper: SiteOper = None      # 站点操作实例
    
    # 定时器
    _scheduler: Optional[BackgroundScheduler] = None
    # 站点处理器
    _site_handlers = []
    #织梦奖励刷新时间
    _zm_next_time: Optional[int] = None

    # 配置属性
    _enabled: bool = False          # 是否启用插件
    _cron: str = ""                 # 定时任务表达式  
    _onlyonce: bool = False         # 是否仅运行一次
    _notify: bool = False           # 是否发送通知
    _interval_cnt: int = 2          # 执行间隔时间(秒)
    _chat_sites: List[str] = []     # 选择的站点列表
    _sites_messages: str = ""       # 自定义站点消息
    _start_time: Optional[int] = None    # 运行开始时间
    _end_time: Optional[int] = None      # 运行结束时间
    _lock: Optional[threading.Lock] = None    # 线程锁
    _running: bool = False          # 是否正在运行
    _get_feedback: bool = False     # 是否获取反馈
    _feedback_timeout: int = 5      # 获取反馈的超时时间(秒)
    _use_proxy: bool = True        # 是否使用代理
    _medal_bonus: bool = False     # 是否领取织梦勋章套装奖励

    def init_plugin(self, config: Optional[dict] = None):
        self._lock = threading.Lock()
        self.sites = SitesHelper()
        self.siteoper = SiteOper()
        
        # 加载站点处理器
        self._site_handlers = ModuleHelper.load('app.plugins.groupchatzone.sites', filter_func=lambda _, obj: hasattr(obj, 'match'))

        # 停止现有任务
        self.stop_service()

        if config:
            self._enabled = config.get("enabled", False)
            self._cron = str(config.get("cron", ""))
            self._onlyonce = bool(config.get("onlyonce", False))
            self._notify = bool(config.get("notify", False))
            self._interval_cnt = int(config.get("interval_cnt", 2))
            self._chat_sites = config.get("chat_sites", [])
            self._sites_messages = str(config.get("sites_messages", ""))
            self._get_feedback = bool(config.get("get_feedback", False))
            self._feedback_timeout = int(config.get("feedback_timeout", 5))
            self._use_proxy = bool(config.get("use_proxy", True))
            self._medal_bonus = bool(config.get("medal_bonus", False))

            # 过滤掉已删除的站点
            all_sites = [site.id for site in self.siteoper.list_order_by_pri()] + [site.get("id") for site in self.__custom_sites()]
            self._chat_sites = [site_id for site_id in self._chat_sites if site_id in all_sites]

            # 保存配置
            self.__update_config()

        # 加载模块
        if self._enabled or self._onlyonce:

            # 定时服务
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)

            # 立即运行一次
            if self._onlyonce:
                try:
                    # 如果勋章奖励开关打开，添加勋章奖励领取任务
                    if self._medal_bonus:
                        logger.info("勋章奖励开关已打开，添加勋章奖励领取任务")
                        self._scheduler.add_job(func=self.send_medal_bonus, trigger='date',
                                                run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=6),
                                                name="群聊区服务 - 勋章奖励领取")

                    logger.info("群聊区服务启动，立即运行一次")
                    self._scheduler.add_job(func=self.send_site_messages, trigger='date',
                                            run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                            name="群聊区服务")

                    # 关闭一次性开关
                    self._onlyonce = False
                    # 保存配置
                    self.__update_config()

                    # 启动任务
                    if self._scheduler and self._scheduler.get_jobs():
                        self._scheduler.print_jobs()
                        self._scheduler.start()
                except Exception as e:
                    logger.error(f"启动一次性任务失败: {str(e)}")

    def get_site_handler(self, site_info: dict):
        """
        获取站点对应的处理器
        """
        # 添加use_proxy到site_info中
        site_info["use_proxy"] = self._use_proxy
        # 添加feedback_timeout到site_info中
        site_info["feedback_timeout"] = self._feedback_timeout
        
        for handler_class in self._site_handlers:
            if (inspect.isclass(handler_class) and 
                issubclass(handler_class, ISiteHandler) and 
                handler_class != ISiteHandler):
                handler = handler_class(site_info)
                if handler.match():
                    return handler
        return None

    def get_state(self) -> bool:
        return self._enabled

    def __update_config(self):
        """
        更新配置
        """
        self.update_config(
            {
                "chat_sites": self._chat_sites,
                "cron": self._cron,
                "enabled": self._enabled,
                "feedback_timeout": self._feedback_timeout,
                "get_feedback": self._get_feedback,
                "interval_cnt": self._interval_cnt,
                "medal_bonus": self._medal_bonus,
                "notify": self._notify,
                "onlyonce": self._onlyonce,
                "sites_messages": self._sites_messages,
                "use_proxy": self._use_proxy
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
        """
        services = []
        
        # 原有的群聊区服务
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
                        services.extend(self.__get_random_schedule())
                    else:
                        # 正常的cron表达式
                        services.append({
                            "id": "GroupChatZone",
                            "name": "群聊区服务",
                            "trigger": CronTrigger.from_crontab(self._cron),
                            "func": self.send_site_messages,
                            "kwargs": {}
                        })
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
                                services.extend(self.__get_random_schedule())
                            else:
                                services.append({
                                    "id": "GroupChatZone",
                                    "name": "群聊区服务",
                                    "trigger": "interval",
                                    "func": self.send_site_messages,
                                    "kwargs": {
                                        "hours": interval_hours,
                                    }
                                })
                        else:
                            logger.error("群聊区服务启动失败，周期格式错误")
                            services.extend(self.__get_random_schedule())
                    else:
                        # 尝试解析为小时间隔
                        try:
                            interval_hours = float(str(self._cron).strip())
                            # 检查间隔是否过小（小于1小时）
                            if interval_hours < 1:
                                logger.warning(f"检测到间隔过小 ({interval_hours}小时)，已自动调整为默认随机执行")
                                services.extend(self.__get_random_schedule())
                            else:
                                # 默认0-24 按照周期运行
                                services.append({
                                    "id": "GroupChatZone",
                                    "name": "群聊区服务",
                                    "trigger": "interval",
                                    "func": self.send_site_messages,
                                    "kwargs": {
                                        "hours": interval_hours,
                                    }
                                })
                        except ValueError:
                            logger.error(f"无法解析周期配置: {self._cron}，已自动调整为默认随机执行")
                            services.extend(self.__get_random_schedule())
            except Exception as err:
                logger.error(f"定时任务配置错误：{str(err)}")
                services.extend(self.__get_random_schedule())
        elif self._enabled:
            # 使用随机调度
            services.extend(self.__get_random_schedule())

        if self._enabled and self._zm_next_time:
            
            # 如果_zm_next_time存在且时间差大于0，使用_zm_next_time中的时间
            if hasattr(self, '_zm_next_time') and self._zm_next_time and self._zm_next_time.get('total_seconds', 0) > 0:
                hours = self._zm_next_time.get('hours', 0)
                minutes = self._zm_next_time.get('minutes', 0)
                seconds = self._zm_next_time.get('seconds', 0)
                logger.info(f"使用最新邮件时间差值设置: {hours}小时 {minutes}分钟 {seconds}秒")
            
            # 添加定时任务
            services.append({
                "id": "GroupChatZoneZm",
                "name": "群聊区服务 - 织梦下次执行任务",
                "trigger": "interval", 
                "func": self.send_zm_site_messages,
                "kwargs": {
                    "hours": hours,
                    "minutes": minutes,
                    "seconds": seconds
                }
            })

        if services:
            return services

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
                "name": "群聊区服务",
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
        from .form import form
        # 获取站点列表
        all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
        
        # 构建站点选项
        site_options = [{"title": site.get("name"), "value": site.get("id")} for site in all_sites]
        return form(site_options)

    def __custom_sites(self) -> List[Any]:
        """
        获取自定义站点列表
        """
        custom_sites = []
        custom_sites_config = self.get_config("CustomSites")
        if custom_sites_config and custom_sites_config.get("enabled"):
            custom_sites = custom_sites_config.get("sites")
        return custom_sites

    def get_page(self) -> List[dict]:
        pass

    def _get_proxies(self):
        """
        获取代理设置
        """
        if not self._use_proxy:
            logger.info("未启用代理")
            return None
            
        try:
            # 获取系统代理设置
            if hasattr(settings, 'PROXY') and settings.PROXY:
                logger.info(f"使用系统代理: {settings.PROXY}")
                return settings.PROXY
            else:
                logger.warning("系统代理未配置")
                return None
        except Exception as e:
            logger.error(f"获取代理设置出错: {str(e)}")
            return None

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
            
            # 原有的消息发送逻辑
            if not self._chat_sites:
                logger.info("没有配置需要发送消息的站点")
                return
            
            site_messages = self._sites_messages if isinstance(self._sites_messages, str) else ""
            if not site_messages.strip():
                logger.info("没有配置需要发送的消息")
                return
            
            # 获取站点信息
            try:
                all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
                # 过滤掉没有选中的站点
                do_sites = [site for site in all_sites if site.get("id") in self._chat_sites]
                
                if not do_sites:
                    logger.info("没有找到有效的站点")
                    return
            except Exception as e:
                logger.error(f"获取站点信息失败: {str(e)}")
                return
            
            # 解析站点消息
            try:
                site_msgs = self.parse_site_messages(site_messages)
                if not site_msgs:
                    logger.info("没有解析到有效的站点消息")
                    return
            except Exception as e:
                logger.error(f"解析站点消息失败: {str(e)}")
                return
            
            # 获取大青虫站点的特权信息
            dqc_privileges = None
            for site in do_sites:
                if site.get("name") == "大青虫":
                    try:
                        handler = self.get_site_handler(site)
                        if handler:
                            dqc_privileges = handler.get_user_privileges()
                            if dqc_privileges:
                                vip_end = dqc_privileges.get("vip_end_time", "无")
                                rainbow_end = dqc_privileges.get("rainbow_end_time", "无") 
                                level_name = dqc_privileges.get("level_name", "无")
                                logger.info(f"获取大青虫站点特权信息成功 - VIP到期时间: {vip_end}, 彩虹ID到期时间: {rainbow_end}, 等级名称: {level_name}")
                            break
                    except Exception as e:
                        logger.error(f"获取大青虫站点特权信息失败: {str(e)}")
                    break
            
            # 获取织梦站点的用户数据统计信息
            zm_stats = None
            for site in do_sites:
                if "织梦" in site.get("name", "").lower():
                    try:
                        handler = self.get_site_handler(site)
                        if handler and hasattr(handler, 'get_user_stats'):
                            zm_stats = handler.get_user_stats()
                            if zm_stats:
                                logger.info(f"获取织梦站点用户数据统计信息成功: {zm_stats}")
                                break
                    except Exception as e:
                        logger.error(f"获取织梦站点用户数据统计信息失败: {str(e)}")
                    continue
            
            # 执行站点发送消息
            site_results = {}
            all_feedback = []
            for site in do_sites:
                site_name = site.get("name")
                logger.info(f"开始处理站点: {site_name}")
                messages = site_msgs.get(site_name, [])

                if not messages:
                    logger.warning(f"站点 {site_name} 没有需要发送的消息！")
                    continue

                success_count = 0
                failure_count = 0
                failed_messages = []
                skipped_messages = []
                site_feedback = []
                
                # 获取站点处理器
                try:
                    handler = self.get_site_handler(site)
                    if not handler:
                        logger.error(f"站点 {site_name} 没有对应的处理器")
                        continue
                except Exception as e:
                    logger.error(f"获取站点 {site_name} 的处理器失败: {str(e)}")
                    continue

                for i, message_info in enumerate(messages):
                    # 检查是否需要过滤消息
                    if site_name == "大青虫" and dqc_privileges:
                        msg_type = message_info.get("type")
                        if msg_type == "vip":
                            # 获取等级名称
                            level_name = dqc_privileges.get("level_name", "")
                            # 定义高等级列表
                            high_levels = ["养老族", "发布员", "总版主", "管理员", "维护开发员", "主管"]
                            
                            # 如果等级高于VIP,直接跳过
                            if level_name in high_levels:
                                skip_reason = f"你都已经是 [{level_name}] 了，还求什么VIP？"
                                logger.info(f"跳过求VIP消息，{skip_reason}")
                                skipped_messages.append({
                                    "message": message_info.get("content"),
                                    "reason": skip_reason
                                })
                                continue
                                
                            # 如果等级不是高等级,则判断VIP到期时间
                            vip_end = dqc_privileges.get("vip_end_time", "")
                            if vip_end == "":
                                logger.info(f"可以发送求VIP消息，因为VIP已到期")
                            else:
                                skip_reason = f"VIP未到期，到期时间: {vip_end}"
                                logger.info(f"跳过求VIP消息，{skip_reason}")
                                skipped_messages.append({
                                    "message": message_info.get("content"),
                                    "reason": skip_reason
                                })
                                continue
                        if msg_type == "rainbow":
                            rainbow_end = dqc_privileges.get("rainbow_end_time", "")
                            if rainbow_end == "":
                                logger.info(f"可以发送求彩虹ID消息，因为彩虹ID已到期")
                            else:
                                skip_reason = f"彩虹ID未到期，到期时间: {rainbow_end}"
                                logger.info(f"跳过求彩虹ID消息，{skip_reason}")
                                skipped_messages.append({
                                    "message": message_info.get("content"),
                                    "reason": skip_reason
                                })
                                continue
                            
                    # 检查织梦站点消息是否需要过滤
                    if site_name == "织梦":
                        # 检查织梦站点定时任务是否已存在
                        try:
                            zm_jobs = [job for job in Scheduler().list() 
                                       if job.name == "群聊区服务 - 织梦下次执行任务"]
                            if zm_jobs:
                                # 获取任务的剩余时间
                                next_run = zm_jobs[0].next_run if hasattr(zm_jobs[0], 'next_run') else ""
                                skip_reason = f"织梦站点定时任务已存在，跳过消息发送\n"
                                skip_reason += f"{f'  ✉️ 织梦 下次奖励获取将在{next_run}后执行' if next_run else '执行时间未知'}"
                                logger.info(skip_reason)
                                skipped_messages.append({
                                    "message": message_info.get("content"),
                                    "reason": skip_reason
                                })
                                continue
                        except Exception as e:
                            logger.error(f"检查织梦任务失败: {str(e)}")
                    
                    try:
                        # 发送消息
                        if "织梦" in site_name:
                            success, msg = handler.send_messagebox(message_info.get("content"), zm_stats=zm_stats)
                        else:
                            success, msg = handler.send_messagebox(message_info.get("content"))
                        if success:
                            success_count += 1
                            # 获取反馈
                            if self._get_feedback:
                                try:
                                    time.sleep(self._feedback_timeout)  # 等待反馈
                                    feedback = handler.get_feedback(message_info.get("content"))
                                    if feedback:
                                        site_feedback.append(feedback)
                                        all_feedback.append(feedback)
                                except Exception as e:
                                    logger.error(f"获取站点 {site_name} 的反馈失败: {str(e)}")
                        else:
                            failure_count += 1
                            failed_messages.append(f"{message_info.get('content')} ({msg})")
                            
                    except Exception as e:
                        logger.error(f"向站点 {site_name} 发送消息 '{message_info.get('content')}' 失败: {str(e)}")
                        failure_count += 1
                        failed_messages.append(message_info.get("content"))

                    if i < len(messages) - 1:
                        logger.info(f"等待 {self._interval_cnt} 秒后继续发送下一条消息...")
                        time.sleep(self._interval_cnt)
                
                # 当站点处理完成后，对于织梦站点获取最新邮件时间
                logger.debug(f"站点 {site_name} 消息处理完成，成功消息数: {success_count}")
                
                # 通过站点名称判断是否为织梦站点
                is_zm_site = "织梦" in site_name
                
                # 如果是织梦站点且有成功发送的消息，获取最新邮件时间
                if is_zm_site and success_count > 0:
                    try:
                        logger.info(f"{site_name} 站点消息发送完成，获取最新邮件时间...")
                        
                        # 检查方法是否存在
                        if hasattr(handler, 'get_latest_message_time'):
                            latest_time = handler.get_latest_message_time()
                            if latest_time:
                                # 将时间保存到handler实例中，以便在通知中显示
                                handler._latest_message_time = latest_time
                                logger.info(f"成功获取织梦站点 {site_name} 最新邮件时间: {latest_time}")
                            else:
                                logger.warning(f"未能获取织梦站点 {site_name} 的最新邮件时间")
                        else:
                            logger.error(f"织梦站点 {site_name} 的处理器没有get_latest_message_time方法")
                    except Exception as e:
                        logger.error(f"获取织梦站点 {site_name} 最新邮件时间时出错: {str(e)}")
                
                site_results[site_name] = {
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "failed_messages": failed_messages,
                    "skipped_messages": skipped_messages,
                    "feedback": site_feedback,
                    "handler": handler  # 保存handler引用以便在通知时获取最新邮件时间
                }

            # 发送通知
            if self._notify:
                try:
                    self._send_notification(site_results, all_feedback)
                except Exception as e:
                    logger.error(f"发送通知失败: {str(e)}")
            
            # 重新注册插件
            self.reregister_plugin()
            
        except Exception as e:
            logger.error(f"发送站点消息时发生异常: {str(e)}")
        finally:
            self._running = False
            if self._lock and hasattr(self._lock, 'locked') and self._lock.locked():
                try:
                    self._lock.release()
                except RuntimeError:
                    pass
            logger.debug("喊话任务执行完成")

    def reregister_plugin(self) -> None:
        """
        重新注册插件
        """
        logger.info("重新注册插件")
        Scheduler().update_plugin_job(self.__class__.__name__)

    def _send_notification(self, site_results: Dict[str, Dict], all_feedback: List[Dict]):
        """
        发送通知
        """
        title = "💬群聊区任务完成报告"
        total_sites = len(site_results)
        notification_text = f"🌐 站点总数: {total_sites}\n"
        
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
        notification_text += "\n📋 喊话反馈:\n"
        
        # 按站点整理反馈和跳过的消息
        for site_name, result in site_results.items():
            feedbacks = result.get("feedback", [])
            skipped_messages = result.get("skipped_messages", [])
            
            if feedbacks or skipped_messages:
                notification_text += f"\n━━━ {site_name} 站点反馈 ━━━\n"
                
                # 处理反馈消息
                for feedback in feedbacks:
                    message = feedback.get("message", "")
                    rewards = feedback.get("rewards", [])
                    
                    if rewards:
                        notification_text += f"✏️ 消息: \"{message}\"\n"
                        
                        # 根据不同类型显示不同图标
                        for reward in rewards:
                            reward_type = reward.get("type", "")
                            icon = NotificationIcons.get(reward_type)
                            
                            if reward_type in ["raw_feedback","上传量", "下载量", "魔力值", "工分", "VIP", "彩虹ID", "电力", "象草", "青蛙"]:
                                notification_text += f"  {icon} {reward.get('description', '')}\n"
                
                # 处理跳过的消息
                for msg in skipped_messages:
                    notification_text += f"✏️跳过: \"{msg['message']}\"\n"
                    notification_text += f"  📌 {msg['reason']}\n"

                # 显示最新邮件时间（如果有）
                handler = result.get("handler")
                
                # 通过站点名称判断是否为织梦站点
                is_zm_site = "织梦" in site_name
                
                # 如果是织梦站点并且有最新邮件时间，则显示
                if handler and is_zm_site and hasattr(handler, '_latest_message_time') and handler._latest_message_time:
                    # 将时间字符串转换为datetime对象
                    latest_time = datetime.strptime(handler._latest_message_time, "%Y-%m-%d %H:%M:%S")
                    # 计算距离下次执行的时间差
                    now = datetime.now()
                    seconds_diff = 24 * 3600 - (now - latest_time).total_seconds()
                    hours = int(seconds_diff // 3600)
                    minutes = int((seconds_diff % 3600) // 60)
                    seconds = int(seconds_diff % 60)
                    notification_text += f"  ✉️ {site_name} 下次奖励获取将在{hours}小时{minutes}分{seconds}秒后执行"

                    # 保存为下次执行时间
                    self._zm_next_time = {
                        "hours": hours,
                        "minutes": minutes, 
                        "seconds": seconds,
                        "total_seconds": seconds_diff
                    }
        
        notification_text += f"\n\n⏱️ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"

        self.post_message(
            mtype=NotificationType.SiteMessage,
            title=title,
            text=notification_text
        )

    def _send_tasks_notification(self, results: List[str]):
        """
        发送任务完成通知
        :param results: 任务执行结果列表
        """
        if not self._medal_bonus:
            return
            
        title = "💬群聊区任务系统执行报告"
        notification_text = "🎖️ 勋章奖励领取:\n"
        
        if results:
            notification_text += "\n".join(results)
        else:
            notification_text += "未找到有效的站点处理器"
            
        notification_text += f"\n\n⏱️ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
        
        self.post_message(
            mtype=NotificationType.SiteMessage,
            title=title,
            text=notification_text
        )

    def get_selected_sites(self) -> List[Dict[str, Any]]:
        """
        获取已选中的站点列表
        """
        all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
        return [site for site in all_sites if site.get("id") in self._chat_sites]

    def parse_site_messages(self, site_messages: str) -> Dict[str, List[Dict]]:
        """
        解析输入的站点消息
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
                messages = []
                
                # 解析消息内容
                for msg in parts[1:]:
                    msg = msg.strip()
                    if not msg:
                        continue
                        
                    # 解析消息类型
                    msg_type = None
                    if "求VIP" in msg:
                        msg_type = "vip"
                    elif "求彩虹ID" in msg:
                        msg_type = "rainbow"
                        
                    messages.append({
                        "content": msg,
                        "type": msg_type
                    })
                
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
            logger.error(f"解析站点消息时出现异常: {str(e)}")
        finally:
            logger.info(f"解析完成，共配置 {len(result)} 个有效站点的消息")
            return result

    def send_message_to_site(self, site_info: CommentedMap, message: str):
        """
        使用站点处理器向站点发送消息
        """
        handler = self.get_site_handler(site_info)
        if handler:
            return handler.send_message(message)
        return False, "无法找到对应的站点处理器"

    def stop_service(self):
        """
        退出插件
        """
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
            # 保存配置
            self.__update_config()

    def __remove_site_id(self, do_sites, site_id):
        """
        从站点列表中移除指定站点
        """
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

    def send_zm_site_messages(self, zm_stats: Dict = None):
        """
        只执行织梦站点的喊话任务
        """
        if not self._lock:
            self._lock = threading.Lock()
            
        if not self._lock.acquire(blocking=False):
            logger.warning("已有任务正在执行，本次调度跳过！")
            return
            
        try:
            self._running = True
            
            # 获取所有站点
            all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
            
            # 过滤出织梦站点
            zm_sites = [site for site in all_sites if "织梦" in site.get("name", "").lower()]
            
            if not zm_sites:
                logger.info("没有找到织梦站点")
                return
                
            # 解析站点消息
            site_messages = self._sites_messages if isinstance(self._sites_messages, str) else ""
            if not site_messages.strip():
                logger.info("没有配置需要发送的消息")
                return
                
            try:
                site_msgs = self.parse_site_messages(site_messages)
                if not site_msgs:
                    logger.info("没有解析到有效的站点消息")
                    return
            except Exception as e:
                logger.error(f"解析站点消息失败: {str(e)}")
                return
                
            # 获取织梦站点的用户数据统计信息
            zm_stats = None
            for site in zm_sites:
                try:
                    handler = self.get_site_handler(site)
                    if handler and hasattr(handler, 'get_user_stats'):
                        zm_stats = handler.get_user_stats()
                        if zm_stats:
                            logger.info(f"获取织梦站点用户数据统计信息成功: {zm_stats}")
                            break
                except Exception as e:
                    logger.error(f"获取织梦站点用户数据统计信息失败: {str(e)}")
                    continue
                
            # 执行站点发送消息
            site_results = {}
            all_feedback = []
            
            for site in zm_sites:
                site_name = site.get("name")
                logger.info(f"开始处理织梦站点: {site_name}")
                messages = site_msgs.get(site_name, [])

                if not messages:
                    logger.warning(f"站点 {site_name} 没有需要发送的消息！")
                    continue

                success_count = 0
                failure_count = 0
                failed_messages = []
                skipped_messages = []
                site_feedback = []
                
                # 获取站点处理器
                try:
                    handler = self.get_site_handler(site)
                    if not handler:
                        logger.error(f"站点 {site_name} 没有对应的处理器")
                        continue
                except Exception as e:
                    logger.error(f"获取站点 {site_name} 的处理器失败: {str(e)}")
                    continue

                for i, message_info in enumerate(messages):
                    try:
                        # 发送消息
                        if "织梦" in site_name:
                            success, msg = handler.send_messagebox(message_info.get("content"), zm_stats=zm_stats)
                        else:
                            success, msg = handler.send_messagebox(message_info.get("content"))
                        if success:
                            success_count += 1
                            # 获取反馈
                            if self._get_feedback:
                                try:
                                    time.sleep(self._feedback_timeout)  # 等待反馈
                                    feedback = handler.get_feedback(message_info.get("content"))
                                    if feedback:
                                        site_feedback.append(feedback)
                                        all_feedback.append(feedback)
                                except Exception as e:
                                    logger.error(f"获取站点 {site_name} 的反馈失败: {str(e)}")
                        else:
                            failure_count += 1
                            failed_messages.append(f"{message_info.get('content')} ({msg})")
                            
                    except Exception as e:
                        logger.error(f"向站点 {site_name} 发送消息 '{message_info.get('content')}' 失败: {str(e)}")
                        failure_count += 1
                        failed_messages.append(message_info.get("content"))

                    if i < len(messages) - 1:
                        logger.info(f"等待 {self._interval_cnt} 秒后继续发送下一条消息...")
                        time.sleep(self._interval_cnt)
                
                # 获取最新邮件时间
                try:
                    logger.info(f"{site_name} 站点消息发送完成，获取最新邮件时间...")
                    if hasattr(handler, 'get_latest_message_time'):
                        latest_time = handler.get_latest_message_time()
                        if latest_time:
                            handler._latest_message_time = latest_time
                            logger.info(f"成功获取织梦站点 {site_name} 最新邮件时间: {latest_time}")
                        else:
                            logger.warning(f"未能获取织梦站点 {site_name} 的最新邮件时间")
                    else:
                        logger.error(f"织梦站点 {site_name} 的处理器没有get_latest_message_time方法")
                except Exception as e:
                    logger.error(f"获取织梦站点 {site_name} 最新邮件时间时出错: {str(e)}")
                
                site_results[site_name] = {
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "failed_messages": failed_messages,
                    "skipped_messages": skipped_messages,
                    "feedback": site_feedback,
                    "handler": handler
                }

            # 发送通知
            if self._notify:
                try:
                    self._send_notification(site_results, all_feedback)
                except Exception as e:
                    logger.error(f"发送通知失败: {str(e)}")
            
            self.reregister_plugin()
            
        except Exception as e:
            logger.error(f"发送织梦站点消息时发生异常: {str(e)}")
        finally:
            self._running = False
            if self._lock and hasattr(self._lock, 'locked') and self._lock.locked():
                try:
                    self._lock.release()
                except RuntimeError:
                    pass
            logger.debug("织梦站点喊话任务执行完成")

    def send_medal_bonus(self) -> Tuple[bool, str]:
        """
        执行勋章奖励任务
        :return: (是否成功, 结果信息)
        """
        if not self._medal_bonus:
            return False, "勋章奖励任务未启用"
            
        try:
            # 获取织梦站点
            zm_sites = [site for site in self.sites.get_indexers() if "织梦" in site.get("name", "").lower()]
            if not zm_sites:
                return False, "未找到织梦站点"
                
            results = []
            for site in zm_sites:
                handler = self.get_site_handler(site)
                if handler and hasattr(handler, 'medal_bonus'):
                    success, msg = handler.medal_bonus()
                    if success:
                        logger.info(f"站点 {site.get('name')} 勋章奖励领取成功: {msg}")
                        results.append(f"✅ {site.get('name')} {msg}")
                    else:
                        logger.error(f"站点 {site.get('name')} 勋章奖励领取失败: {msg}")
                        results.append(f"❌ {site.get('name')}  勋章奖励领取失败: {msg}")
                        
            if not results:
                return False, f"未找到有效的{site.get('name')}站点处理器"
                
            # 发送任务完成通知
            self._send_tasks_notification(results)
                
            return True, "\n".join(results)
        
        except Exception as e:
            logger.error(f"执行勋章奖励任务失败: {str(e)}")
            return False, f"执行失败: {str(e)}"

class NotificationIcons:
    """
    通知图标常量
    """
    UPLOAD = "⬆️"
    DOWNLOAD = "⬇️"
    BONUS = "✨"
    WORK = "🔧"
    POWER = "⚡"
    VICOMO = "🐘"
    FROG = "🐸"
    VIP = "👑"
    RAINBOW = "🌈"
    FEEDBACK = "📝"
    DEFAULT = "📌"
    
    @classmethod
    def get(cls, reward_type: str) -> str:
        """
        获取奖励类型对应的图标
        """
        icon_map = {
            "上传量": cls.UPLOAD,
            "下载量": cls.DOWNLOAD,
            "魔力值": cls.BONUS,
            "工分": cls.WORK,
            "电力": cls.POWER,
            "象草": cls.VICOMO,
            "青蛙": cls.FROG,
            "VIP": cls.VIP,
            "彩虹ID": cls.RAINBOW,
            "raw_feedback": cls.FEEDBACK
        }
        return icon_map.get(reward_type, cls.DEFAULT)
