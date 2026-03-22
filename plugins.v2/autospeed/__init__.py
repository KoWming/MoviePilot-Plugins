import threading
from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional, Tuple

from apscheduler.triggers.cron import CronTrigger

from app.log import logger
from app.plugins import _PluginBase
from app.scheduler import Scheduler
from app.schemas import NotificationType

class AutoSpeed(_PluginBase):
    # 插件名称
    plugin_name = "Vue-网络测速"
    # 插件描述
    plugin_desc = "使用Speedtest.net定时自动测速，支持手动触发，记录历史趋势。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/AutoSpeed.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "KoWming,鱼丸粗面"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "autospeed_"
    # 加载顺序
    plugin_order = 50
    # 可使用的用户级别
    auth_level = 1

    # 配置与状态
    _enabled: bool = False
    _notify: bool = True
    _cron: Optional[str] = None
    _mode: str = "closest"
    _server_id: str = ""
    _retry_count: int = 2
    _history_limit: int = 31

    # 运行状态标识（防止并发重复测速）
    _running: bool = False

    def __init__(self):
        super().__init__()

    @staticmethod
    def _to_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() == "true"
        return bool(val)

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """初始化插件，加载配置"""
        try:
            self.stop_service()
            if config:
                self._enabled = self._to_bool(config.get("enabled", False))
                self._notify = self._to_bool(config.get("notify", True))
                self._cron = config.get("cron") or "0 */6 * * *"
                self._mode = config.get("mode") or "closest"
                self._server_id = config.get("server_id") or ""
                self._retry_count = int(config.get("retry_count", 2))
                self._history_limit = int(config.get("history_limit", 31))

            if not self._enabled:
                logger.info(f"{self.plugin_name}: 插件未启用")
                return

            logger.info(f"{self.plugin_name}: 初始化完成，Cron={self._cron}，模式={self._mode}")
        except Exception as e:
            logger.error(f"{self.plugin_name}: 初始化失败: {e}")

    def get_state(self) -> bool:
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/config",
                "endpoint": self._api_get_config,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取配置",
            },
            {
                "path": "/config",
                "endpoint": self._api_save_config,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "保存配置",
            },
            {
                "path": "/servers",
                "endpoint": self._api_get_servers,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取测速节点列表",
            },
            {
                "path": "/history",
                "endpoint": self._api_get_history,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "查询历史测速记录",
            },
            {
                "path": "/run",
                "endpoint": self._api_run,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "手动触发测速",
            },
            {
                "path": "/latest",
                "endpoint": self._api_get_latest,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取最近一次测速结果",
            },
            {
                "path": "/status",
                "endpoint": self._api_get_status,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取插件状态",
            },
        ]

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """Vue 模式下返回 None 和初始配置"""
        return None, self._api_get_config()

    def get_render_mode(self) -> Tuple[str, Optional[str]]:
        """返回 Vue 渲染模式"""
        return "vue", "dist/assets"

    def get_page(self) -> List[dict]:
        """Vue 模式下返回空列表"""
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """注册公共定时服务"""
        services = []
        if self._enabled and self._cron:
            try:
                services.append(
                    {
                        "id": "autospeed",
                        "name": "网络测速 - 定时任务",
                        "trigger": CronTrigger.from_crontab(self._cron),
                        "func": self._speedtest_task,
                        "kwargs": {},
                    }
                )
                logger.info(f"{self.plugin_name}: 定时服务已注册，Cron={self._cron}")
            except Exception as e:
                logger.error(f"{self.plugin_name}: 注册定时服务失败: {e}")
        return services

    def stop_service(self):
        """停止定时服务"""
        try:
            Scheduler().remove_plugin_job(self.__class__.__name__.lower())
        except Exception as e:
            logger.debug(f"{self.plugin_name}: 停止服务: {e}")

    # ------------------------------------------------------------------ #
    #  测速核心逻辑（基于 speedtest-cli Python API）
    # ------------------------------------------------------------------ #

    def _get_servers_list(self) -> List[Dict]:
        """获取 Speedtest 节点列表"""
        try:
            import speedtest
            st = speedtest.Speedtest()
            st.get_servers()
            # get_servers() 返回 {distance: [server_dict, ...], ...} 结构
            servers_raw = st.get_servers()
            result = []
            for srv_list in servers_raw.values():
                for srv in srv_list:
                    result.append(
                        {
                            "id": srv.get("id"),
                            "name": srv.get("sponsor", srv.get("name", "未知")),
                            "location": srv.get("name", ""),
                            "country": srv.get("country", ""),
                            "host": srv.get("host", ""),
                        }
                    )
            # 按 id 去重后返回
            seen = set()
            unique = []
            for s in result:
                if s["id"] not in seen:
                    seen.add(s["id"])
                    unique.append(s)
            return unique
        except Exception as e:
            logger.error(f"{self.plugin_name}: 获取节点列表失败: {e}")
            return []

    def _get_target_server(self, mode: str, server_id: str) -> Optional[List]:
        """
        根据模式选择目标节点列表。
        closest: 返回 None（让 speedtest 自动选最优）
        fixed:   返回指定 ID 的节点列表（如 [12345]）
        其他:     在节点列表中按运营商关键字筛选
        """
        if mode == "closest":
            return None
        if mode == "fixed" and server_id:
            try:
                return [int(server_id)]
            except ValueError:
                logger.warning(f"{self.plugin_name}: 无效的固定节点 ID: {server_id}")
                return None

        # 按运营商关键字筛选
        keyword_map = {
            "telecom": ["telecom", "电信", "chinanet", "ct"],
            "unicom": ["unicom", "联通", "cucc"],
            "mobile": ["mobile", "移动", "cmcc"],
        }
        keywords = keyword_map.get(mode, [])
        if not keywords:
            return None

        try:
            import speedtest
            st = speedtest.Speedtest()
            servers_raw = st.get_servers()
            for srv_list in servers_raw.values():
                for srv in srv_list:
                    name = (
                        str(srv.get("name", "")) + str(srv.get("sponsor", ""))
                    ).lower()
                    for kw in keywords:
                        if kw in name:
                            return [int(srv["id"])]
        except Exception as e:
            logger.warning(f"{self.plugin_name}: 运营商节点筛选失败: {e}")
        return None

    def _run_speedtest(self, server_ids: Optional[List] = None) -> bool:
        """
        执行测速。
        server_ids: None 表示自动选最优节点，否则为 [int(id)] 列表
        """
        max_retries = self._retry_count
        for attempt in range(max_retries + 1):
            logger.info(f"{self.plugin_name}: 开始测速（第 {attempt + 1} 次）...")
            try:
                import speedtest
                st = speedtest.Speedtest()

                if server_ids:
                    st.get_servers(server_ids)
                    st.get_best_server()
                else:
                    st.get_best_server()

                download_mbps = round(st.download() / 1e6, 2)
                upload_mbps = round(st.upload() / 1e6, 2)
                ping_ms = round(st.results.ping, 2)
                srv = st.results.dict().get("server", {})
                server_name = f"{srv.get('sponsor', '未知')} - {srv.get('name', '未知')}"
                server_id_used = str(srv.get("id", ""))

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record = {
                    "timestamp": timestamp,
                    "download": download_mbps,
                    "upload": upload_mbps,
                    "ping": ping_ms,
                    "server_name": server_name,
                    "server_id": server_id_used,
                }
                self._save_result(record)

                logger.info(
                    f"{self.plugin_name}: 测速成功 — 下行 {download_mbps} Mbps, "
                    f"上行 {upload_mbps} Mbps, 延迟 {ping_ms} ms, 节点: {server_name}"
                )

                if self._notify:
                    self._send_notify(success=True, record=record)

                return True

            except Exception as e:
                logger.warning(f"{self.plugin_name}: 第 {attempt + 1} 次测速失败: {e}")
                if attempt < max_retries:
                    import time
                    time.sleep(10)
                else:
                    if self._notify:
                        self._send_notify(success=False, error=str(e))
                    return False
        return False

    # ------------------------------------------------------------------ #
    #  数据管理（基于 MoviePilot save_data / get_data）
    # ------------------------------------------------------------------ #

    def _save_result(self, record: Dict) -> None:
        """保存测速结果到历史记录和最新结果"""
        # 更新最新结果
        self.save_data("latest", record)

        # 追加到历史列表，动态保留条数
        history: List[Dict] = self.get_data("history") or []
        history.append(record)
        if len(history) > self._history_limit:
            history = history[-self._history_limit:]
        self.save_data("history", history)

    def _get_history(self, days: int = 7) -> List[Dict]:
        """查询历史记录，days=0 表示返回全部"""
        history: List[Dict] = self.get_data("history") or []
        if days <= 0 or not history:
            return history
        threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        return [r for r in history if r.get("timestamp", "") >= threshold]

    # ------------------------------------------------------------------ #
    #  定时任务
    # ------------------------------------------------------------------ #

    def _speedtest_task(self) -> None:
        """定时任务入口"""
        if self._running:
            logger.warning(f"{self.plugin_name}: 上一次测速仍在进行中，跳过本次调度")
            return
        logger.info(f"{self.plugin_name}: 定时测速任务启动")
        self.save_data("last_run", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._running = True
        try:
            server_ids = self._get_target_server(self._mode, self._server_id)
            self._run_speedtest(server_ids)
        finally:
            self._running = False

    # ------------------------------------------------------------------ #
    #  通知
    # ------------------------------------------------------------------ #

    def _send_notify(self, success: bool, record: Optional[Dict] = None, error: str = "") -> None:
        """发送测速结果通知"""
        try:
            if success and record:
                title = "【🚀 网络测速】报告"
                text = (
                    "──────────\n"
                    "📈 测速结果：\n"
                    f"⬇️ 下行速度：{record['download']} Mbps\n"
                    f"⬆️ 上行速度：{record['upload']} Mbps\n"
                    f"⚡ 响应延迟：{record['ping']} ms\n"
                    f"🌐 测速节点：{record['server_name']}\n"
                    f"🆔 节点 I D：{record['server_id']}\n"
                    "──────────\n"
                    f"⏰ 测试时间：{record['timestamp']}"
                )
            else:
                title = "【🚀 网络测速】测速失败"
                text = (
                    "──────────\n"
                    "❌ 错误信息：\n"
                    f"⚠️ 失败原因：{error or '未知错误'}\n"
                    "──────────\n"
                    f"⏰ 测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

            self.post_message(
                mtype=NotificationType.Plugin,
                title=title,
                text=text,
            )
        except Exception as e:
            logger.warning(f"{self.plugin_name}: 发送通知失败: {e}")

    # ------------------------------------------------------------------ #
    #  API 接口实现
    # ------------------------------------------------------------------ #

    def _api_get_config(self) -> Dict[str, Any]:
        """GET /config — 获取当前配置"""
        return {
            "enabled": self._enabled,
            "notify": self._notify,
            "cron": self._cron or "0 */6 * * *",
            "mode": self._mode,
            "server_id": self._server_id,
            "retry_count": self._retry_count,
            "history_limit": self._history_limit,
        }

    def _api_save_config(self, payload: dict = None) -> Dict[str, Any]:
        """POST /config — 保存配置并重新注册服务"""
        if not payload:
            return {"success": False, "msg": "参数为空"}
        try:
            new_config = {
                "enabled": self._to_bool(payload.get("enabled", self._enabled)),
                "notify": self._to_bool(payload.get("notify", self._notify)),
                "cron": payload.get("cron") or self._cron,
                "mode": payload.get("mode") or self._mode,
                "server_id": payload.get("server_id") or "",
                "retry_count": int(payload.get("retry_count", self._retry_count)),
                "history_limit": int(payload.get("history_limit", self._history_limit)),
            }
            self.init_plugin(new_config)
            self.update_config(new_config)
            return {"success": True, "msg": "配置已保存"}
        except Exception as e:
            logger.error(f"{self.plugin_name}: 保存配置失败: {e}")
            return {"success": False, "msg": str(e)}

    def _api_get_servers(self) -> Dict[str, Any]:
        """GET /servers — 获取节点列表"""
        servers = self._get_servers_list()
        return {"servers": servers}

    def _api_get_history(self, days: int = 7) -> Dict[str, Any]:
        """GET /history?days=7 — 获取历史测速数据"""
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 7
        records = self._get_history(days)
        return {
            "total": len(records),
            "records": records,
        }

    def _api_run(self, payload: dict = None) -> Dict[str, Any]:
        """POST /run — 手动触发测速（异步）"""
        if self._running:
            return {"success": False, "msg": "测速正在进行中，请稍后再试"}

        mode = (payload or {}).get("mode") or self._mode
        server_id = (payload or {}).get("server_id") or self._server_id

        def _do_run():
            self._running = True
            try:
                server_ids = self._get_target_server(mode, server_id)
                self._run_speedtest(server_ids)
            finally:
                self._running = False

        t = threading.Thread(target=_do_run, daemon=True)
        t.start()
        return {"success": True, "msg": "测速已开始，请稍后刷新结果"}

    def _api_get_latest(self) -> Dict[str, Any]:
        """GET /latest — 获取最近一次测速结果"""
        latest = self.get_data("latest")
        if latest:
            return {"has_data": True, "record": latest}
        return {"has_data": False, "record": None}

    def _api_get_status(self) -> Dict[str, Any]:
        """GET /status — 获取插件状态（包括定时任务信息）"""
        next_run_time = "未配置"
        task_status = "未启用"

        if self._enabled and self._cron:
            try:
                scheduler = Scheduler()
                schedule_list = scheduler.list()
                for task in schedule_list:
                    if task.provider == self.plugin_name:
                        task_status = task.status
                        if hasattr(task, "next_run") and task.next_run:
                            next_run_time = task.next_run
                        break
            except Exception as e:
                logger.debug(f"{self.plugin_name}: 获取定时任务信息失败: {e}")
                task_status = "获取失败"

        return {
            "enabled": self._enabled,
            "running": self._running,
            "cron": self._cron,
            "mode": self._mode,
            "task_status": task_status,
            "next_run_time": next_run_time,
            "last_run": self.get_data("last_run"),
            "latest": self.get_data("latest"),
        }
