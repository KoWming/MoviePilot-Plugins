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
    plugin_version = "2.3.2"
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
    
    #织梦邮件时间
    _zm_mail_time: Optional[int] = None
    
    # 织梦执行控制属性
    _last_zm_execution_time: Optional[datetime] = None  # 上次织梦执行时间
    _zm_execution_cooldown: int = 600 # 织梦执行冷却时间（秒），默认10分钟
    _zm_mail_retry_count: int = 0  # 邮件时间获取重试次数
    _max_zm_mail_retries: int = 3  # 最大重试次数

    # 配置属性
    _enabled: bool = False          # 是否启用插件
    _cron: str = ""                 # 定时任务表达式  
    _onlyonce: bool = False         # 是否仅运行一次
    _notify: bool = True           # 是否发送通知
    _interval_cnt: int = 2          # 执行间隔时间(秒)
    _chat_sites: List[str] = []     # 选择的站点列表
    _sites_messages: str = ""       # 自定义站点消息
    _start_time: Optional[int] = None    # 运行开始时间
    _end_time: Optional[int] = None      # 运行结束时间
    _lock: Optional[threading.Lock] = None    # 其他站点任务锁
    _zm_lock: Optional[threading.Lock] = None    # 织梦站点任务锁
    _running: bool = False          # 是否正在运行
    _get_feedback: bool = True     # 是否获取反馈
    _feedback_timeout: int = 5      # 获取反馈的超时时间(秒)
    _use_proxy: bool = True        # 是否使用代理
    _zm_independent: bool = True  # 是否织梦独立运行
    _qingwa_daily_bonus: bool = False  # 是否青蛙每日福利领取
    _longpt_daily_lottery: bool = False  # 是否LongPT每日抽奖
    _retry_count: int = 2          # 喊话失败重试次数
    _retry_interval: int = 10      # 喊话失败重试间隔(分钟)
    _zm_interval: int = 60      # 独立织梦喊话间隔(秒)
    _retry_notify: bool = False     # 是否发送重试通知
    
    # 重试相关属性
    _failed_messages: List[Dict] = []  # 存储失败消息的详细信息
    _current_retry_count: int = 0      # 当前重试次数
    _next_retry_time: Optional[datetime] = None       # 下次重试的精确时间
    _retry_lock: Optional[threading.Lock] = None  # 重试任务锁
    _failed_messages_max: int = 100  # 失败消息最大保留条数，防止内存增长

    def _prune_failed_messages(self) -> None:
        """
        失败消息内存清理：超过最大阈值时，仅保留最新的 100 条。
        """
        try:
            if isinstance(self._failed_messages, list):
                total = len(self._failed_messages)
                if total > self._failed_messages_max:
                    drop = total - self._failed_messages_max
                    self._failed_messages = self._failed_messages[-self._failed_messages_max:]
                    logger.warning(f"失败消息过多，已清理较早的 {drop} 条，仅保留最近 {self._failed_messages_max} 条")
        except Exception as e:
            logger.error(f"清理失败消息时发生异常: {str(e)}")

    def init_plugin(self, config: Optional[dict] = None):
        self._lock = threading.Lock()
        self._zm_lock = threading.Lock()
        self._retry_lock = threading.Lock()
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
            self._notify = bool(config.get("notify", True))
            self._interval_cnt = int(config.get("interval_cnt", 2))
            self._chat_sites = config.get("chat_sites", [])
            self._sites_messages = str(config.get("sites_messages", ""))
            self._get_feedback = bool(config.get("get_feedback", True))
            self._feedback_timeout = int(config.get("feedback_timeout", 5))
            self._use_proxy = bool(config.get("use_proxy", True))
            self._zm_independent = bool(config.get("zm_independent", True))
            self._qingwa_daily_bonus = bool(config.get("qingwa_daily_bonus", False))
            self._longpt_daily_lottery = bool(config.get("longpt_daily_lottery", False))
            self._retry_count = int(config.get("retry_count", 2))
            self._retry_interval = int(config.get("retry_interval", 10))
            self._retry_notify = bool(config.get("retry_notify", False))
            self._zm_interval = int(config.get("zm_interval", 60))
            self._zm_mail_time = config.get("zm_mail_time")
            
            # 恢复织梦执行控制状态
            self._last_zm_execution_time = config.get("last_zm_execution_time")
            if self._last_zm_execution_time and isinstance(self._last_zm_execution_time, str):
                try:
                    self._last_zm_execution_time = datetime.fromisoformat(self._last_zm_execution_time)
                except ValueError:
                    self._last_zm_execution_time = None
            self._zm_execution_cooldown = int(config.get("zm_execution_cooldown", 600))
            self._zm_mail_retry_count = int(config.get("zm_mail_retry_count", 0))
            self._max_zm_mail_retries = int(config.get("max_zm_mail_retries", 3))
            
            # 恢复重试相关状态
            self._failed_messages = config.get("failed_messages", [])
            # 清理超量的失败消息，避免历史数据过大
            self._prune_failed_messages()
            self._current_retry_count = int(config.get("current_retry_count", 0))
            next_retry_time_str = config.get("next_retry_time")
            if next_retry_time_str:
                try:
                    # 确保从字符串转换回带时区的datetime对象
                    tz = pytz.timezone(settings.TZ)
                    parsed = datetime.fromisoformat(next_retry_time_str)
                    self._next_retry_time = parsed if parsed.tzinfo else tz.localize(parsed)
                except (ValueError, TypeError):
                    self._next_retry_time = None
            else:
                self._next_retry_time = None

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
                    logger.info("群聊区服务启动，立即运行一次")

                    # 清除织梦冷却时间，确保本次立即执行不受冷却限制
                    self._last_zm_execution_time = None

                    # 先启动织梦站点任务
                    if self._zm_independent:
                        self._scheduler.add_job(func=self.send_zm_site_messages, trigger='date',
                                            run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                            name="群聊区织梦服务")
                        logger.info("已添加织梦站点任务")

                    # 再启动其他站点任务
                    self._scheduler.add_job(func=self.send_site_messages, trigger='date',
                                            run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=30),
                                            name="群聊区服务")
                    logger.info("已添加普通站点任务")

                    # 关闭一次性开关
                    self._onlyonce = False
                    # 保存配置
                    self.__update_config()

                    # 启动任务
                    if self._scheduler and self._scheduler.get_jobs():
                        self._scheduler.print_jobs()
                        self._scheduler.start()
                        
                    # 立即执行一次时，清除原有的重试状态
                    if self._failed_messages:
                        logger.info("立即执行一次，清除原有的重试状态")
                        self._failed_messages = []
                        self._current_retry_count = 0
                        # 保存配置以清理重试状态
                        self.__update_config()
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
        # 添加longpt_daily_lottery到site_info中
        site_info["longpt_daily_lottery"] = self._longpt_daily_lottery
        # 添加retry_count到site_info中
        site_info["retry_count"] = self._retry_count
        # 添加retry_interval到site_info中
        site_info["retry_interval"] = self._retry_interval
        
        # 补充render字段，确保从数据库获取最新状态
        if site_info.get("id"):
            try:
                site = self.siteoper.get(site_info.get("id"))
                if site:
                    site_info["render"] = site.render
            except Exception as e:
                logger.error(f"获取站点渲染状态失败: {str(e)}")

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
                "notify": self._notify,
                "onlyonce": self._onlyonce,
                "sites_messages": self._sites_messages,
                "use_proxy": self._use_proxy,
                "zm_independent": self._zm_independent,
                "zm_mail_time": self._zm_mail_time,
                "zm_interval": self._zm_interval,
                "last_zm_execution_time": self._last_zm_execution_time.isoformat() if self._last_zm_execution_time else None,
                "zm_execution_cooldown": self._zm_execution_cooldown,
                "zm_mail_retry_count": self._zm_mail_retry_count,
                "max_zm_mail_retries": self._max_zm_mail_retries,
                "qingwa_daily_bonus": self._qingwa_daily_bonus,
                "longpt_daily_lottery": self._longpt_daily_lottery,
                "retry_count": self._retry_count,
                "retry_interval": self._retry_interval,
                "retry_notify": self._retry_notify,
                "failed_messages": self._failed_messages,
                "current_retry_count": self._current_retry_count,
                "next_retry_time": self._next_retry_time.isoformat() if self._next_retry_time else None
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
                            "name": "群聊区 - 定时任务",
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
                                    "name": "群聊区 - 定时任务",
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
                                    "name": "群聊区 - 定时任务",
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

        if self._enabled and self._zm_independent:
            # 添加织梦定时任务
            if self._zm_mail_time:
                try:
                    tz = pytz.timezone(settings.TZ)
                    # 将存储的时间字符串转换为 aware datetime（带时区）
                    mail_time = datetime.strptime(self._zm_mail_time, "%Y-%m-%d %H:%M:%S")
                    if mail_time.tzinfo is None:
                        mail_time = tz.localize(mail_time)
                    # 计算24小时后的时间（aware）
                    next_time = mail_time + timedelta(hours=24)
                    # 获取当前 aware 时间
                    now = datetime.now(tz=tz)
                    # 若已过期，则顺延到当前+3秒
                    if (next_time - now).total_seconds() <= 0:
                        logger.info("距离上次邮件已超过24小时,将立即执行")
                        next_time = now + timedelta(seconds=3)
                        hours = minutes = seconds = 0
                    else:
                        # 转换为小时、分钟、秒（仅用于日志显示）
                        diff_seconds = int((next_time - now).total_seconds())
                        hours = diff_seconds // 3600
                        minutes = (diff_seconds % 3600) // 60
                        seconds = diff_seconds % 60
                        logger.info(f"距离下次执行还有 {hours}小时 {minutes}分钟 {seconds}秒")
                except Exception as e:
                    logger.error(f"计算织梦定时任务时间参数失败: {str(e)}")
                    # 立即获取邮件时间
                    logger.info("计算时间参数失败，将立即获取邮件时间")
                    if self.get_zm_mail_time():
                        # 重新计算时间参数
                        return self.get_service()
                    return services
            else:
                # 如果没有邮件时间,立即获取邮件时间
                logger.info("未找到上次邮件时间，将立即获取邮件时间")
                if self.get_zm_mail_time():
                    # 重新计算时间参数
                    return self.get_service()
                return services

            # 检查是否有织梦站点被选中
            has_zm_site = False
            for site_id in self._chat_sites:
                site = self.siteoper.get(site_id)
                if site and "织梦" in site.name:
                    has_zm_site = True
                    break
            
            # 只有在有织梦站点被选中且开启独立织梦喊话开关时才添加定时任务
            if has_zm_site and self._zm_independent:
                # 添加定时任务
                services.append({
                    "id": "GroupChatZoneZm",
                    "name": "群聊区 - 织梦定时任务",
                    "trigger": "date",
                    "func": self.send_zm_site_messages,
                    "kwargs": {
                        "run_date": next_time
                    }
                })
                logger.info(f"已添加织梦定时任务（date）：将在 {next_time.strftime('%Y-%m-%d %H:%M:%S')} 运行")
            else:
                if has_zm_site:
                    logger.info("有织梦站点但未开启独立织梦喊话开关，不添加织梦定时任务")
                else:
                    logger.info("没有选中织梦站点，不添加织梦定时任务")
        
        # 如果有重试任务，添加到服务列表中
        if self._next_retry_time and self._next_retry_time > datetime.now(tz=pytz.timezone(settings.TZ)):
            services.append({
                "id": "GroupChatZoneRetry",
                "name": f"群聊区 - 重试任务 (第{self._current_retry_count + 1}次)",
                "trigger": "date",
                "func": self._execute_retry,
                "kwargs": {
                    "run_date": self._next_retry_time
                }
            })
            logger.info(f"已注册重试任务，将在 {self._next_retry_time.strftime('%Y-%m-%d %H:%M:%S')} 执行")

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
                "name": "群聊区 - 定时任务",
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
        
        # 定义目标站点名称
        target_site_names = ["大青虫", "青蛙", "织梦", "象站", "幸运", "藏宝阁","天枢","好学", "Moment", "RailgunPT", "PTLGS", "LongPT", "LuckPT","13City","PTS"]

        # 过滤站点，只保留目标站点
        filtered_sites = [site for site in all_sites if site.get("name") in target_site_names]
        
        # 构建站点选项
        site_options = [{"title": site.get("name"), "value": site.get("id")} for site in filtered_sites]
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
            logger.warning("已有其他站点任务正在执行，本次调度跳过！")
            return
            
        try:
            self._running = True
            
            # 清空之前的失败消息列表
            self._failed_messages = []
            
            # 原有的消息发送逻辑
            if not self._chat_sites:
                logger.info("没有配置需要发送消息的站点")
                return
            
            # 获取站点信息
            try:
                all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
                # 根据独立织梦喊话开关决定是否过滤织梦站点
                do_sites = [site for site in all_sites if site.get("id") in self._chat_sites and (not site.get("name", "").startswith("织梦") or not self._zm_independent)]
                
                if not do_sites:
                    logger.info("没有找到有效的站点")
                    return
            except Exception as e:
                logger.error(f"获取站点信息失败: {str(e)}")
                return
            
            # 检查是否需要执行青蛙每日福利购买 - 优先执行
            daily_bonus_result = None
            if self._qingwa_daily_bonus:
                # 在所有选中的站点中查找青蛙站点
                all_selected_sites = [site for site in all_sites if site.get("id") in self._chat_sites]
                logger.info(f"青蛙每日福利购买开关已启用，开始检查青蛙站点...")
                logger.info(f"选中的站点列表: {[site.get('name') for site in all_selected_sites]}")
                
                for site in all_selected_sites:
                    if "青蛙" in site.get("name", ""):
                        try:
                            handler = self.get_site_handler(site)
                            if handler and hasattr(handler, 'buy_daily_bonus'):
                                logger.info(f"开始执行青蛙每日福利购买: {site.get('name')}")
                                success, msg = handler.buy_daily_bonus()
                                daily_bonus_result = {
                                    "success": success,
                                    "message": msg,
                                    "site_name": site.get("name")
                                }
                                break
                        except Exception as e:
                            logger.error(f"执行青蛙每日福利购买时发生异常: {str(e)}")
                            daily_bonus_result = {
                                "success": False,
                                "message": f"执行异常: {str(e)}",
                                "site_name": site.get("name")
                            }
                            break
                else:
                    logger.info("未找到青蛙站点")
            
            # 检查是否需要执行LongPT每日抽奖 - 优先执行
            lottery_result = None
            if self._longpt_daily_lottery:
                # 在所有选中的站点中查找LongPT站点
                all_selected_sites = [site for site in all_sites if site.get("id") in self._chat_sites]
                logger.info(f"LongPT每日抽奖开关已启用，开始检查LongPT站点...")
                logger.info(f"选中的站点列表: {[site.get('name') for site in all_selected_sites]}")
                
                for site in all_selected_sites:
                    if "LongPT" in site.get("name", ""):
                        try:
                            handler = self.get_site_handler(site)
                            if handler and hasattr(handler, 'daily_lottery'):
                                logger.info(f"开始执行LongPT每日抽奖: {site.get('name')}")
                                success, msg = handler.daily_lottery()
                                lottery_result = {
                                    "success": success,
                                    "message": msg,
                                    "site_name": site.get("name")
                                }
                                break
                        except Exception as e:
                            logger.error(f"执行LongPT每日抽奖时发生异常: {str(e)}")
                            lottery_result = {
                                "success": False,
                                "message": f"执行异常: {str(e)}",
                                "site_name": site.get("name")
                            }
                            break
                else:
                    logger.info("未找到LongPT站点")
            
            site_messages = self._sites_messages if isinstance(self._sites_messages, str) else ""
            if not site_messages.strip():
                logger.info("没有配置需要发送的消息")
                
                # 即使没有喊话消息，也要发送通知（如果有每日福利购买结果或抽奖结果）
                if self._notify and (daily_bonus_result or lottery_result):
                    try:
                        self._send_notification({}, [], daily_bonus_result, lottery_result)
                    except Exception as e:
                        logger.error(f"发送通知失败: {str(e)}")
                
                # 重新注册插件
                self.reregister_plugin()
                return
            
            # 解析站点消息
            try:
                site_msgs = self.parse_site_messages(site_messages)
                if not site_msgs:
                    logger.info("没有解析到有效的站点消息")
                    # 即使没有解析到喊话消息，也要发送通知（如果有每日福利购买结果或抽奖结果）
                    if self._notify and (daily_bonus_result or lottery_result):
                        try:
                            self._send_notification({}, [], daily_bonus_result, lottery_result)
                        except Exception as e:
                            logger.error(f"发送通知失败: {str(e)}")
                    # 重新注册插件
                    self.reregister_plugin()
                    return
            except Exception as e:
                logger.error(f"解析站点消息失败: {str(e)}")
                # 即使解析失败，也要发送通知（如果有每日福利购买结果或抽奖结果）
                if self._notify and (daily_bonus_result or lottery_result):
                    try:
                        self._send_notification({}, [], daily_bonus_result, lottery_result)
                    except Exception as e:
                        logger.error(f"发送通知失败: {str(e)}")
                # 重新注册插件
                self.reregister_plugin()
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
                    
                    try:
                        # 发送消息
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
                            failed_messages.append(f"{message_info.get('content')}")
                            # 记录失败消息到全局列表，用于重试
                            self._failed_messages.append({
                                "site_name": site_name,
                                "site_id": site.get("id"),
                                "message": message_info.get("content"),
                                "interval": message_info.get("interval"),
                                "error": msg
                            })
                            
                    except Exception as e:
                        logger.error(f"向站点 {site_name} 发送消息 '{message_info.get('content')}' 失败: {str(e)}")
                        failure_count += 1
                        failed_messages.append(message_info.get("content"))
                        # 记录失败消息到全局列表，用于重试
                        self._failed_messages.append({
                            "site_name": site_name,
                            "site_id": site.get("id"),
                            "message": message_info.get("content"),
                            "interval": message_info.get("interval"),
                            "error": str(e)
                        })

                    if i < len(messages) - 1:
                        # 优先使用配置的自定义间隔
                        msg_interval = message_info.get("interval")
                        if msg_interval is not None:
                            interval = msg_interval
                            logger.info(f"使用自定义间隔: 等待 {interval} 秒后继续发送下一条消息...")
                        else:
                            # 如果是Moment、天枢站点，使用默认30秒间隔
                            interval = 30 if "Moment" in site_name or "天枢" in site_name else self._interval_cnt
                            logger.info(f"等待 {interval} 秒后继续发送下一条消息...")
                        time.sleep(interval)
                logger.debug(f"站点 {site_name} 消息处理完成，成功消息数: {success_count}")

                site_results[site_name] = {
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "failed_messages": failed_messages,
                    "skipped_messages": skipped_messages,
                    "feedback": site_feedback
                }

            # 保存配置以持久化失败消息（保存前先清理）
            self._prune_failed_messages()
            self.__update_config()
            
            # 先发送任务完成通知
            if self._notify:
                try:
                    self._send_notification(site_results, all_feedback, daily_bonus_result, lottery_result)
                except Exception as e:
                    logger.error(f"发送通知失败: {str(e)}")
            
            # 然后检查是否有失败消息，如果有则创建重试任务
            if self._failed_messages and self._retry_count > 0:
                logger.info(f"检测到 {len(self._failed_messages)} 条失败消息，开始创建重试任务")
                try:
                    self._create_retry_task()
                except Exception as e:
                    logger.error(f"创建重试任务失败: {str(e)}")
            elif self._failed_messages:
                logger.info(f"检测到 {len(self._failed_messages)} 条失败消息，但重试次数为0，不创建重试任务")
            else:
                logger.info("没有失败消息，无需创建重试任务")
            
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

    def _send_notification(self, site_results: Dict[str, Dict], all_feedback: List[Dict], daily_bonus_result: Dict = None, lottery_result: Dict = None):
        """
        发送通知
        """
        # 判断是否只有青蛙每日福利购买任务或LongPT每日抽奖任务
        only_daily_bonus = len(site_results) == 0 and daily_bonus_result is not None and lottery_result is None
        only_lottery = len(site_results) == 0 and lottery_result is not None and daily_bonus_result is None
        both_tasks = len(site_results) == 0 and daily_bonus_result is not None and lottery_result is not None
        
        if only_daily_bonus:
            # 只有青蛙每日福利购买时的简化通知
            title = "🐸青蛙每日福利购买报告"
            notification_text = ""
            
            if daily_bonus_result["success"]:
                notification_text += f"✅ 购买成功\n"
                notification_text += f"📝 详情: 消耗1蝌蚪，获得1000蝌蚪。\n"
            else:
                notification_text += f"❌ 购买失败\n"
                notification_text += f"📝 原因: {daily_bonus_result['message']}\n"
            
            notification_text += f"\n\n⏱️ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
        elif only_lottery:
            # 只有LongPT每日抽奖时的简化通知
            title = "🎰LongPT每日抽奖报告"
            notification_text = ""
            
            if lottery_result["success"]:
                notification_text += f"✅ 成功参加\n"
                notification_text += f"📝 详情: {lottery_result['message']}\n"
            else:
                notification_text += f"❌ 参加失败\n"
                notification_text += f"📝 原因: {lottery_result['message']}\n"
            
            notification_text += f"\n\n⏱️ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
        elif both_tasks:
            # 同时有青蛙每日福利购买和LongPT每日抽奖时的通知
            title = "🎁每日任务报告"
            notification_text = ""
            
            # 青蛙每日福利购买结果
            notification_text += "🐸 青蛙每日福利购买:\n"
            if daily_bonus_result["success"]:
                notification_text += f"  ✅ 购买成功\n"
                notification_text += f"  📝 详情: 消耗1蝌蚪，获得1000蝌蚪。\n"
            else:
                notification_text += f"  ❌ 购买失败\n"
                notification_text += f"  📝 原因: {daily_bonus_result['message']}\n"
            
            notification_text += "\n🎰 LongPT每日抽奖:\n"
            if lottery_result["success"]:
                notification_text += f"  ✅ 成功参加\n"
                notification_text += f"  📝 详情: {lottery_result['message']}\n"
            else:
                notification_text += f"  ❌ 参加失败\n"
                notification_text += f"  📝 原因: {lottery_result['message']}\n"
            
            notification_text += f"\n\n⏱️ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
        else:
            # 原有的完整通知格式
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
                                
                                if reward_type in ["raw_feedback","上传量", "下载量", "魔力值", "工分", "VIP", "彩虹ID", "电力", "象草", "青蛙", "火花", "啤酒瓶"]:
                                    notification_text += f"  {icon} {reward.get('description', '')}\n"
                    
                    # 处理跳过的消息
                    for msg in skipped_messages:
                        notification_text += f"✏️跳过: \"{msg['message']}\"\n"
                        notification_text += f"  📌 {msg['reason']}\n"

                    # 添加每日福利购买状态到青蛙站点反馈中
                    if "青蛙" in site_name and daily_bonus_result:
                        notification_text += "\n━━━━━━━━━━━━━━━━━\n"
                        notification_text += "\n🎁 每日福利购买状态:\n"
                        if daily_bonus_result["success"]:
                            notification_text += f"  ✅ 购买成功\n"
                            notification_text += f"  📝 详情: 消耗1蝌蚪，获得1000蝌蚪。\n"
                        else:
                            notification_text += f"  ❌ 购买失败\n"
                            notification_text += f"  📝 原因: {daily_bonus_result['message']}\n"
                    
                    # 添加每日抽奖状态到LongPT站点反馈中
                    if "LongPT" in site_name and lottery_result:
                        notification_text += "\n━━━━━━━━━━━━━━━━━\n"
                        notification_text += "\n🎰 每日抽奖状态:\n"
                        if lottery_result["success"]:
                            notification_text += f"  ✅ 成功参加\n"
                            notification_text += f"  📝 详情: {lottery_result['message']}\n"
                        else:
                            notification_text += f"  ❌ 参加失败\n"
                            notification_text += f"  📝 原因: {lottery_result['message']}\n"

                    # 显示最新邮件时间（如果有）
                    handler = result.get("handler")
                    
                    # 通过站点名称判断是否为织梦站点
                    is_zm_site = "织梦" in site_name
                    
                    # 如果是织梦站点并且有最新邮件时间，则显示
                    if handler and is_zm_site and hasattr(handler, '_latest_message_time') and handler._latest_message_time:
                        # 将时间字符串转换为datetime对象
                        tz = pytz.timezone(settings.TZ)
                        latest_time = tz.localize(datetime.strptime(handler._latest_message_time, "%Y-%m-%d %H:%M:%S"))
                        # 计算距离下次执行的时间差（统一使用 aware 时间）
                        now = datetime.now(tz=tz)
                        seconds_diff = 24 * 3600 - int((now - latest_time).total_seconds())
                        hours = int(seconds_diff // 3600)
                        minutes = int((seconds_diff % 3600) // 60)
                        seconds = int(seconds_diff % 60)
                        notification_text += f"  ✉️ {site_name} 下次奖励获取将在{hours}小时{minutes}分{seconds}秒后执行"
            
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
                
                # 检查最后一个部分是否为时间间隔设定 (如 60s)
                custom_interval = None
                if len(parts) > 2:
                    last_part = parts[-1].strip()
                    if last_part.lower().endswith('s') and last_part[:-1].isdigit():
                        custom_interval = int(last_part[:-1])
                        # 移除最后一个部分，它不是消息内容
                        parts = parts[:-1]
                
                # 解析消息内容
                for msg in parts[1:]:
                    msg = msg.strip()
                    if not msg:
                        continue
                        
                    # 解析消息类型
                    msg_type = None
                    msg_lower = msg.lower()  # 转换为小写以支持大小写不敏感比较
                    if "求vip" in msg_lower:
                        msg_type = "vip"
                    elif "求彩虹id" in msg_lower:
                        msg_type = "rainbow"
                        
                    msg_data = {
                        "content": msg,
                        "type": msg_type
                    }
                    # 如果有自定义间隔，加入到消息数据中
                    if custom_interval is not None:
                        msg_data["interval"] = custom_interval
                        
                    messages.append(msg_data)
                
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
            
            # 清理重试任务
            self._next_retry_time = None
            
            # 重置重试相关状态
            self._failed_messages = []
            self._current_retry_count = 0
            
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
        if not self._zm_lock:
            self._zm_lock = threading.Lock()
            
        if not self._zm_lock.acquire(blocking=False):
            logger.warning("已有织梦站点任务正在执行，本次调度跳过！")
            return
            
        try:
            # 检查冷却时间
            if self._last_zm_execution_time:
                tz = pytz.timezone(settings.TZ)
                last = self._last_zm_execution_time
                if last.tzinfo is None:
                    last = tz.localize(last)
                time_since_last = datetime.now(tz=tz) - last
                if time_since_last.total_seconds() < self._zm_execution_cooldown:
                    remaining_time = self._zm_execution_cooldown - time_since_last.total_seconds()
                    logger.info(f"织梦站点执行冷却中，距离下次可执行还有 {remaining_time:.0f} 秒")
                    return
            
            # 记录执行时间
            tz = pytz.timezone(settings.TZ)
            self._last_zm_execution_time = datetime.now(tz=tz)
            self._running = True
            
            # 清空之前的失败消息列表
            self._failed_messages = []
            
            # 检查是否有织梦站点被选中
            has_zm_site = False
            for site_id in self._chat_sites:
                site = self.siteoper.get(site_id)
                if site and "织梦" in site.name:
                    has_zm_site = True
                    break
            
            if not has_zm_site:
                logger.info("没有选中织梦站点，不执行织梦站点任务")
                return
            
            # 获取所有站点
            all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
            
            # 过滤出织梦站点
            zm_sites = [site for site in all_sites if "织梦" in site.get("name", "").lower() and site.get("id") in self._chat_sites]
            
            if not zm_sites:
                logger.info("没有找到选中的织梦站点")
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
                            failed_messages.append(f"{message_info.get('content')}")
                            # 记录失败消息到全局列表，用于重试
                            self._failed_messages.append({
                                "site_name": site_name,
                                "site_id": site.get("id"),
                                "message": message_info.get("content"),
                                "interval": message_info.get("interval"),
                                "error": msg
                            })
                            
                    except Exception as e:
                        logger.error(f"向站点 {site_name} 发送消息 '{message_info.get('content')}' 失败: {str(e)}")
                        failure_count += 1
                        failed_messages.append(message_info.get("content"))
                        # 记录失败消息到全局列表，用于重试
                        self._failed_messages.append({
                            "site_name": site_name,
                            "site_id": site.get("id"),
                            "message": message_info.get("content"),
                            "interval": message_info.get("interval"),
                            "error": str(e)
                        })

                    if i < len(messages) - 1:
                        # 优先使用配置的自定义间隔
                        msg_interval = message_info.get("interval")
                        if msg_interval is not None:
                            interval = msg_interval
                            logger.info(f"使用自定义间隔: 等待 {interval} 秒后继续发送下一条消息...")
                        else:
                            interval = self._zm_interval
                            logger.info(f"等待 {interval} 秒后继续发送下一条消息...")
                        time.sleep(interval)
                
                # 获取最新邮件时间
                try:
                    logger.info(f"{site_name} 站点消息发送完成，获取最新邮件时间...")
                    if hasattr(handler, 'get_latest_message_time'):
                        latest_time = handler.get_latest_message_time()
                        if latest_time:
                            try:
                                # 将时间字符串转换为datetime对象以验证格式
                                datetime.strptime(latest_time, "%Y-%m-%d %H:%M:%S")
                                handler._latest_message_time = latest_time
                                self._zm_mail_time = latest_time
                                # 更新配置以持久化存储
                                self.__update_config()
                                logger.info(f"成功保存 {site_name} 站点最新邮件时间: {latest_time}")
                            except ValueError:
                                logger.error(f"{site_name} 站点最新邮件时间格式错误: {latest_time}")
                        else:
                            logger.warning(f"未能获取 {site_name} 站点的最新邮件时间")
                    else:
                        logger.error(f"{site_name} 站点的处理器没有get_latest_message_time方法")
                except Exception as e:
                    logger.error(f"获取 {site_name} 站点的最新邮件时间时出错: {str(e)}")
                
                site_results[site_name] = {
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "failed_messages": failed_messages,
                    "skipped_messages": skipped_messages,
                    "feedback": site_feedback,
                    "handler": handler
                }

            # 保存配置以持久化失败消息
            self.__update_config()
            
            # 先发送任务完成通知
            if self._notify:
                try:
                    self._send_notification(site_results, all_feedback)
                except Exception as e:
                    logger.error(f"发送通知失败: {str(e)}")
            
            # 然后检查是否有失败消息，如果有则创建重试任务
            if self._failed_messages and self._retry_count > 0:
                logger.info(f"检测到 {len(self._failed_messages)} 条失败消息，开始创建重试任务")
                try:
                    self._create_retry_task()
                except Exception as e:
                    logger.error(f"创建重试任务失败: {str(e)}")
            elif self._failed_messages:
                logger.info(f"检测到 {len(self._failed_messages)} 条失败消息，但重试次数为0，不创建重试任务")
            else:
                logger.info("没有失败消息，无需创建重试任务")
            
            self.reregister_plugin()
            
        except Exception as e:
            logger.error(f"发送织梦站点消息时发生异常: {str(e)}")
        finally:
            self._running = False
            if self._zm_lock and hasattr(self._zm_lock, 'locked') and self._zm_lock.locked():
                try:
                    self._zm_lock.release()
                except RuntimeError:
                    pass
            logger.debug("织梦站点喊话任务执行完成")

    def _create_retry_task(self):
        """
        创建重试定时任务
        """
        if not self._failed_messages:
            logger.info("没有失败消息，无需创建重试任务")
            return
            
        if self._current_retry_count >= self._retry_count:
            logger.info(f"已达到最大重试次数 {self._retry_count}，不再创建重试任务")
            return
            
        # 计算下次重试时间
        next_retry_time = datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(minutes=self._retry_interval)
        
        # 保存下次重试时间
        self._next_retry_time = next_retry_time

        # 更新配置
        self.__update_config()
        
        logger.info(f"已创建重试任务，将在 {next_retry_time.strftime('%Y-%m-%d %H:%M:%S')} 执行第 {self._current_retry_count + 1} 次重试")

        # 发送重试通知（如果开关开启）
        if self._retry_notify:
            self._send_retry_notification(next_retry_time)
        # 触发插件重新注册，让外部调度拾取新的重试任务
        self.reregister_plugin()

    def _execute_retry(self):
        """
        执行重试任务
        """
        if not self._retry_lock:
            self._retry_lock = threading.Lock()
            
        if not self._retry_lock.acquire(blocking=False):
            logger.warning("已有重试任务正在执行，本次重试跳过！")
            return
            
        try:
            logger.info(f"开始执行第 {self._current_retry_count + 1} 次重试任务")
            
            if not self._failed_messages:
                logger.info("没有失败消息需要重试")
                return
                
            # 按站点分组失败消息
            site_failed_messages = {}
            for failed_msg in self._failed_messages:
                site_name = failed_msg["site_name"]
                if site_name not in site_failed_messages:
                    site_failed_messages[site_name] = []
                site_failed_messages[site_name].append(failed_msg)
            
            # 执行重试
            retry_results = {}
            new_failed_messages = []
            
            for site_name, failed_msgs in site_failed_messages.items():
                logger.info(f"重试站点 {site_name} 的失败消息")
                
                success_count = 0
                failure_count = 0
                site_new_failed_messages = []
                
                for i, failed_msg in enumerate(failed_msgs):
                    try:
                        site_id = failed_msg["site_id"]
                        message = failed_msg["message"]
                        
                        # 根据站点ID重新获取站点信息和处理器
                        all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
                        site_info = None
                        for site in all_sites:
                            if site.get("id") == site_id:
                                site_info = site
                                break
                        
                        if not site_info:
                            logger.error(f"重试时无法找到站点 {site_name} (ID: {site_id})")
                            failure_count += 1
                            site_new_failed_messages.append(failed_msg)
                            continue
                        
                        # 重新创建处理器
                        handler = self.get_site_handler(site_info)
                        if not handler:
                            logger.error(f"重试时无法创建站点 {site_name} 的处理器")
                            failure_count += 1
                            site_new_failed_messages.append(failed_msg)
                            continue
                        
                        # 重新发送消息
                        if "织梦" in site_name:
                            # 尝试获取统计信息（这里简单处理，可能为空）
                            success, msg = handler.send_messagebox(message)
                        else:
                            success, msg = handler.send_messagebox(message)
                        
                        if success:
                            success_count += 1
                            logger.info(f"重试成功: {site_name} - {message}")
                        else:
                            failure_count += 1
                            logger.warning(f"重试失败: {site_name} - {message} ({msg})")
                            # 记录新的失败消息
                            site_new_failed_messages.append(failed_msg)
                            
                    except Exception as e:
                        failure_count += 1
                        logger.error(f"重试异常: {site_name} - {failed_msg['message']} - {str(e)}")
                        # 记录新的失败消息
                        site_new_failed_messages.append(failed_msg)
                    
                    if i < len(failed_msgs) - 1:
                        # 优先使用消息中的自定义间隔
                        msg_interval = failed_msg.get("interval")
                        if msg_interval is not None:
                            interval = msg_interval
                            logger.info(f"重试使用自定义间隔: 等待 {interval} 秒...")
                        else:
                            interval = self._interval_cnt
                            logger.info(f"重试等待 {interval} 秒...")
                        time.sleep(interval)
            
            # 更新失败消息列表
            self._failed_messages = new_failed_messages
            
            # 增加重试次数
            self._current_retry_count += 1
            
            # 保存配置以持久化失败消息和重试状态（保存前先清理）
            self._prune_failed_messages()
            self.__update_config()
            
            # 清理当前执行的重试任务时间点
            self._next_retry_time = None

            # 如果还有失败消息且未达到最大重试次数，继续创建重试任务
            if self._failed_messages and self._current_retry_count < self._retry_count:
                logger.info(f"重试后仍有失败消息，将创建第 {self._current_retry_count + 1} 次重试任务")
                self._create_retry_task()
            else:
                logger.info("所有重试任务已完成或已达到最大重试次数")
                # 重置重试计数
                self._current_retry_count = 0
                # 清空失败消息列表
                self._failed_messages = []
                
                # 保存已清理的配置
                self.__update_config()
                
                # 发送最终重试结果通知
                if self._notify:
                    self._send_final_retry_notification(retry_results)

        except Exception as e:
            logger.error(f"执行重试任务时发生异常: {str(e)}")
        finally:
            # 安全释放重试锁
            if self._retry_lock:
                try:
                    if self._retry_lock.locked():
                        self._retry_lock.release()
                except (RuntimeError, AttributeError):
                    pass

    def _send_retry_notification(self, next_retry_time: datetime):
        """
        发送重试通知
        """
        if not self._failed_messages:
            return
            
        # 按站点分组失败消息
        site_failed_messages = {}
        for failed_msg in self._failed_messages:
            site_name = failed_msg["site_name"]
            if site_name not in site_failed_messages:
                site_failed_messages[site_name] = []
            site_failed_messages[site_name].append(failed_msg)
        
        # 构建通知内容
        title = "⚠️ 喊话失败重试通知"
        notification_text = ""
        
        # 站点列表
        site_names = list(site_failed_messages.keys())
        notification_text += f"🌐 站点: {', '.join(site_names)}\n"
        
        # 重试信息
        notification_text += f"🔄 当前重试次数: 第{self._current_retry_count + 1}次\n"
        notification_text += f"📊 剩余重试次数: {self._retry_count - self._current_retry_count - 1}次\n"
        notification_text += f"⏰ 重试间隔: {self._retry_interval}分钟\n"
        notification_text += f"🕐 下次重试时间: {next_retry_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        notification_text += "\n"
        
        # 失败消息详情
        for site_name, failed_msgs in site_failed_messages.items():
            notification_text += f"🚫 {site_name}失败的消息:\n"
            for i, failed_msg in enumerate(failed_msgs, 1):
                notification_text += f"  {i}. {failed_msg['message']}\n"
            notification_text += "\n"
        
        notification_text += f"⏱️ 通知发送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
        
        # 发送通知
        self.post_message(
            mtype=NotificationType.SiteMessage,
            title=title,
            text=notification_text
        )

    def _send_final_retry_notification(self, retry_results: Dict[str, Dict]):
        """
        发送最终重试结果通知
        """
        if not retry_results:
            return
            
        title = "🔄 喊话重试任务完成报告"
        notification_text = ""
        
        # 统计总体结果
        total_sites = len(retry_results)
        total_success = sum(result["success_count"] for result in retry_results.values())
        total_failure = sum(result["failure_count"] for result in retry_results.values())
        
        notification_text += f"📊 重试统计:\n"
        notification_text += f"🌐 站点总数: {total_sites}\n"
        notification_text += f"✅ 重试成功: {total_success}条\n"
        notification_text += f"❌ 重试失败: {total_failure}条\n\n"
        
        # 各站点结果
        for site_name, result in retry_results.items():
            success_count = result["success_count"]
            failure_count = result["failure_count"]
            
            if success_count > 0 and failure_count == 0:
                notification_text += f"✅ {site_name}: 全部重试成功\n"
            elif success_count > 0 and failure_count > 0:
                notification_text += f"⚠️ {site_name}: 成功{success_count}条，失败{failure_count}条\n"
            else:
                notification_text += f"❌ {site_name}: 全部重试失败\n"
        
        notification_text += f"\n⏱️ 报告时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
        
        # 发送通知
        self.post_message(
            mtype=NotificationType.SiteMessage,
            title=title,
            text=notification_text
        )

    def get_zm_mail_time(self) -> bool:
        """
        获取织梦站点的最新邮件时间
        :return: 是否成功获取
        """
        try:
            # 如果重试次数过多，使用默认间隔
            if self._zm_mail_retry_count >= self._max_zm_mail_retries:
                logger.warning(f"邮件时间获取失败次数过多（{self._zm_mail_retry_count}次），使用默认24小时间隔")
                # 将邮件时间设置为当前时间，从而下次执行时间为 当前时间 + 24 小时
                tz = pytz.timezone(settings.TZ)
                self._zm_mail_time = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
                self._zm_mail_retry_count = 0  # 重置重试计数
                self.__update_config()
                return True
            
            # 获取所有站点
            all_sites = [site for site in self.sites.get_indexers() if not site.get("public")] + self.__custom_sites()
            
            # 过滤出织梦站点
            zm_sites = [site for site in all_sites if "织梦" in site.get("name", "").lower() and site.get("id") in self._chat_sites]
            
            if not zm_sites:
                logger.info("没有找到选中的织梦站点")
                self._zm_mail_retry_count += 1
                return False
                
            # 遍历织梦站点获取邮件时间
            for site in zm_sites:
                try:
                    handler = self.get_site_handler(site)
                    if handler and hasattr(handler, 'get_latest_message_time'):
                        latest_time = handler.get_latest_message_time()
                        if latest_time:
                            try:
                                # 将时间字符串转换为datetime对象以验证格式
                                datetime.strptime(latest_time, "%Y-%m-%d %H:%M:%S")
                                self._zm_mail_time = latest_time
                                self._zm_mail_retry_count = 0  # 重置重试计数
                                # 更新配置以持久化存储
                                self.__update_config()
                                logger.info(f"成功获取 {site.get('name')} 站点最新邮件时间: {latest_time}")
                                return True
                            except ValueError:
                                logger.error(f"{site.get('name')} 站点最新邮件时间格式错误: {latest_time}")
                        else:
                            logger.warning(f"未能获取 {site.get('name')} 站点的最新邮件时间")
                    else:
                        logger.error(f"{site.get('name')} 站点的处理器没有get_latest_message_time方法")
                except Exception as e:
                    logger.error(f"获取 {site.get('name')} 站点的最新邮件时间时出错: {str(e)}")
                    continue
            
            # 如果所有站点都获取失败，增加重试计数
            self._zm_mail_retry_count += 1
            logger.warning(f"获取邮件时间失败，重试次数: {self._zm_mail_retry_count}/{self._max_zm_mail_retries}")
            return False  
        except Exception as e:
            logger.error(f"获取织梦站点邮件时间时发生异常: {str(e)}")
            self._zm_mail_retry_count += 1
            return False

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
    SPARK = "🔥"
    BEER = "🍺"
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
            "火花": cls.SPARK,
            "啤酒瓶": cls.BEER,
            "raw_feedback": cls.FEEDBACK
        }
        return icon_map.get(reward_type, cls.DEFAULT)