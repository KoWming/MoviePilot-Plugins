import time
import base64
import html
import re
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from apscheduler.triggers.cron import CronTrigger

from app.log import logger
from app.core.config import settings
from app.plugins import _PluginBase
from app.scheduler import Scheduler
from app.schemas import NotificationType
from app.db.site_oper import SiteOper

# 验证码识别重试次数
_CAPTCHA_RETRY = 3


class SiqiFram(_PluginBase):
    # 插件名称
    plugin_name = "Vue-思齐农场"
    # 插件描述
    plugin_desc = "农场管理、种植、收获、偷菜、点赞。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/siqi.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "siqifram_"
    # 加载顺序
    plugin_order = 28
    # 可使用的用户级别
    auth_level = 2

    # 配置与运行状态
    # 插件是否启用
    _enabled: bool = False
    # 是否发送任务完成通知
    _notify: bool = True
    # 自动任务 Cron 表达式
    _cron: Optional[str] = None
    # 思齐站点 Cookie，留空时尝试读取站点管理中的 Cookie
    _cookie: Optional[str] = None
    # 默认种子 ID，用于自动补种
    _seed_id: str = "1"
    # 是否自动补种空地
    _auto_plant: bool = True
    # 是否自动收获成熟作物
    _auto_harvest: bool = True
    # 是否自动出售背包库存
    _auto_sell: bool = False
    # 是否自动偷菜
    _auto_steal: bool = False
    # 是否自动点赞农场
    _auto_like: bool = False
    # 是否使用 MP 系统代理访问站点
    _use_proxy: bool = False
    # 是否启用 AI 辅助验证码识别
    _use_ai_captcha: bool = False
    # 请求失败重试次数
    _retry_count: int = 2
    # 请求失败重试间隔（秒）
    _retry_interval: int = 3
    # 默认站点地址
    _site_url: str = "https://si-qi.xyz"
    # 站点管理操作实例
    _siteoper = None

    @staticmethod
    def _to_bool(val: Any) -> bool:
        """将常见布尔配置值转换为 bool。"""
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "on")
        return bool(val)

    @staticmethod
    def _to_int(val: Any, default: int = 0) -> int:
        """将配置值转换为 int，失败时返回默认值。"""
        try:
            return int(val)
        except Exception:
            return default

    def _normalize_cron(self, cron: Any, default: str = "5 */4 * * *") -> str:
        """校验并规范化 Cron 表达式，使用 MP 配置时区。"""
        cron_text = str(cron or "").strip() or default
        try:
            CronTrigger.from_crontab(cron_text, timezone=settings.TZ)
            return cron_text
        except Exception as e:
            logger.warning(f"{self.plugin_name}: Cron表达式无效 '{cron_text}'，使用默认值 '{default}' - {e}")
            return default

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """初始化插件配置，并根据站点信息更新基础地址。"""
        try:
            self.stop_service()
            self._siteoper = SiteOper()
            self._cron = self._normalize_cron(self._cron)
            if config:
                self._enabled = self._to_bool(config.get("enabled", False))
                self._notify = self._to_bool(config.get("notify", True))
                self._cron = self._normalize_cron(config.get("cron"))
                self._cookie = config.get("cookie") or ""
                self._seed_id = str(config.get("seed_id") or "1")
                self._auto_plant = self._to_bool(config.get("auto_plant", True))
                self._auto_harvest = self._to_bool(config.get("auto_harvest", True))
                self._auto_sell = self._to_bool(config.get("auto_sell", False))
                self._auto_steal = self._to_bool(config.get("auto_steal", False))
                self._auto_like = self._to_bool(config.get("auto_like", False))
                self._use_proxy = self._to_bool(config.get("use_proxy", False))
                self._use_ai_captcha = self._to_bool(config.get("use_ai_captcha", False))
                self._retry_count = self._to_int(config.get("retry_count"), 2)
                self._retry_interval = self._to_int(config.get("retry_interval"), 3)

            site_url, _ = self._get_site_info()
            if site_url:
                self._site_url = site_url.rstrip("/")

            if not self._enabled:
                logger.info(f"{self.plugin_name} 服务未启用")
                return
            logger.info(f"{self.plugin_name}: 已启用，CRON={self._cron}")
        except Exception as e:
            logger.error(f"{self.plugin_name} 服务启动失败: {e}")

    def get_state(self) -> bool:
        """获取插件启用状态。"""
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """返回插件命令列表。"""
        return []

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """Vue 模式下返回空表单与当前配置。"""
        return None, self._get_config()

    def get_render_mode(self) -> Tuple[str, Optional[str]]:
        """返回渲染模式和前端资源目录。"""
        return "vue", "dist/assets"

    def get_page(self) -> List[dict]:
        """Vue 模式下不返回传统页面配置。"""
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """注册插件定时任务服务。"""
        if self._enabled and self._cron:
            return [{
                "id": "siqifram",
                "name": "思齐农场 - 定时任务",
                "trigger": CronTrigger.from_crontab(self._cron, timezone=settings.TZ),
                "func": self._farm_task,
                "kwargs": {}
            }]
        return []

    def stop_service(self):
        """停止并移除插件定时任务。"""
        try:
            Scheduler().remove_plugin_job(self.__class__.__name__.lower())
        except Exception as e:
            logger.debug(f"{self.plugin_name} 停止服务失败: {e}")

    def get_api(self) -> List[dict]:
        """返回插件后端 API 路由配置。"""
        return [
            {"path": "/config", "endpoint": self._get_config, "methods": ["GET"], "auth": "bear", "summary": "获取配置"},
            {"path": "/config", "endpoint": self._save_config, "methods": ["POST"], "auth": "bear", "summary": "保存配置"},
            {"path": "/status", "endpoint": self._get_status, "methods": ["GET"], "auth": "bear", "summary": "插件状态"},
            {"path": "/data", "endpoint": self._get_data, "methods": ["GET"], "auth": "bear", "summary": "农场数据"},
            {"path": "/refresh", "endpoint": self._refresh_data, "methods": ["POST"], "auth": "bear", "summary": "刷新数据"},
            {"path": "/plant", "endpoint": self._plant, "methods": ["POST"], "auth": "bear", "summary": "种植"},
            {"path": "/plant-fill", "endpoint": self._plant_fill_empty, "methods": ["POST"], "auth": "bear", "summary": "一键种植空地"},
            {"path": "/buy-plot-slot", "endpoint": self._buy_plot_slot, "methods": ["POST"], "auth": "bear", "summary": "购买菜地坑位"},
            {"path": "/harvest", "endpoint": self._harvest, "methods": ["POST"], "auth": "bear", "summary": "收获单格"},
            {"path": "/harvest-ready", "endpoint": self._harvest_ready, "methods": ["POST"], "auth": "bear", "summary": "收获成熟作物"},
            {"path": "/harvest-ocr", "endpoint": self._harvest_ready_ocr, "methods": ["POST"], "auth": "bear", "summary": "验证码一键收获"},
            {"path": "/captcha", "endpoint": self._get_harvest_captcha, "methods": ["GET"], "auth": "bear", "summary": "一键收获验证码"},
            {"path": "/harvest-all", "endpoint": self._harvest_all, "methods": ["POST"], "auth": "bear", "summary": "验证码一键收获"},
            {"path": "/sell", "endpoint": self._sell_inventory, "methods": ["POST"], "auth": "bear", "summary": "出售背包"},
            {"path": "/steal", "endpoint": self._steal_once, "methods": ["POST"], "auth": "bear", "summary": "偷菜一次"},
            {"path": "/steal-target", "endpoint": self._get_steal_target, "methods": ["POST"], "auth": "bear", "summary": "获取偷菜目标农场"},
            {"path": "/steal-plot", "endpoint": self._steal_plot, "methods": ["POST"], "auth": "bear", "summary": "偷取指定作物"},
            {"path": "/steal-finish", "endpoint": self._finish_stealing, "methods": ["POST"], "auth": "bear", "summary": "完成偷菜会话"},
            {"path": "/like-random", "endpoint": self._like_random, "methods": ["POST"], "auth": "bear", "summary": "随机点赞"},
            {"path": "/like-targets", "endpoint": self._like_targets, "methods": ["POST"], "auth": "bear", "summary": "获取随机点赞目标"},
            {"path": "/like-farm", "endpoint": self._like_farm, "methods": ["POST"], "auth": "bear", "summary": "点赞农场"},
            {"path": "/visit-farm", "endpoint": self._visit_farm, "methods": ["POST"], "auth": "bear", "summary": "访问农场"},
            {"path": "/visit-random", "endpoint": self._visit_random_farm, "methods": ["POST"], "auth": "bear", "summary": "随机访问农场"},
            {"path": "/stage-image", "endpoint": self._stage_image, "methods": ["GET"], "auth": "bear", "summary": "代理作物阶段图片"},
            {"path": "/cookie", "endpoint": self.__get_cookie, "methods": ["GET"], "auth": "bear", "summary": "获取站点Cookie"},
        ]

    def _get_config(self) -> Dict[str, Any]:
        """获取当前插件配置。"""
        return {
            "enabled": self._enabled,
            "notify": self._notify,
            "cron": self._cron or "",
            "cookie": self._cookie or "",
            "seed_id": self._seed_id,
            "auto_plant": self._auto_plant,
            "auto_harvest": self._auto_harvest,
            "auto_sell": self._auto_sell,
            "auto_steal": self._auto_steal,
            "auto_like": self._auto_like,
            "use_proxy": self._use_proxy,
            "use_ai_captcha": self._use_ai_captcha,
            "ai_available": getattr(settings, "AI_AGENT_ENABLE", False),
            "retry_count": self._retry_count,
            "retry_interval": self._retry_interval,
        }

    def _save_config(self, config: dict = None) -> Dict[str, Any]:
        """保存插件配置并重新初始化服务。"""
        if config is None:
            config = {}
        config["cron"] = self._normalize_cron(config.get("cron"))
        self.update_config(config)
        self.init_plugin(config)
        Scheduler().update_plugin_job(self.__class__.__name__.lower())
        return {"success": True, "message": "配置已保存", "config": self._get_config()}

    def _get_status(self) -> Dict[str, Any]:
        """获取插件运行状态与最近任务结果。"""
        return {
            "enabled": self._enabled,
            "cron": self._cron,
            "use_proxy": self._use_proxy,
            "next_run_time": self._get_next_run_time(),
            "last_run": self.get_data("last_run"),
            "last_result": self.get_data("last_result"),
            "farm_status": self.get_data("farm_status"),
        }

    def _get_next_run_time(self) -> str:
        """获取定时任务下一次运行时间。"""
        if not self._enabled or not self._cron:
            return "未配置定时任务"
        try:
            scheduler = Scheduler()
            for task in scheduler.list():
                if task.provider == self.plugin_name:
                    return getattr(task, "next_run", None) or "等待执行"
        except Exception as e:
            logger.debug(f"{self.plugin_name}: 获取下次执行时间失败: {e}")
        return f"按配置执行: {self._cron}"

    def _get_site_info(self) -> Tuple[Optional[str], Optional[str]]:
        """从站点管理中读取思齐站点地址和 User-Agent。"""
        try:
            if not self._siteoper:
                return None, None
            site = self._siteoper.get_by_domain("si-qi.xyz")
            if not site:
                site = self._siteoper.get_by_domain("siqi.xyz")
            if not site:
                return None, None
            return getattr(site, "url", None), getattr(site, "ua", None)
        except Exception as e:
            logger.warning(f"{self.plugin_name}: 获取站点信息失败: {e}")
            return None, None

    def __get_cookie(self):
        """获取可用 Cookie，优先使用插件配置，其次读取站点管理。"""
        try:
            if self._cookie and str(self._cookie).strip().lower() != "cookie":
                return {"success": True, "cookie": self._cookie}
            site = self._siteoper.get_by_domain("si-qi.xyz") if self._siteoper else None
            if not site and self._siteoper:
                site = self._siteoper.get_by_domain("siqi.xyz")
            if not site:
                return {"success": False, "msg": "未添加思齐站点（si-qi.xyz）"}
            cookie = getattr(site, "cookie", None)
            if not cookie or str(cookie).strip().lower() == "cookie":
                return {"success": False, "msg": "站点 Cookie 为空或无效"}
            self._cookie = cookie
            return {"success": True, "cookie": cookie}
        except Exception as e:
            return {"success": False, "msg": f"获取 Cookie 失败: {e}"}

    def _stage_image(self, path: str = "") -> Dict[str, Any]:
        """代理作物阶段图片，返回 base64 编码的图片数据"""
        if not path:
            return {"success": False, "message": "缺少 path 参数"}
        site_url, user_agent = self._get_site_info()
        base_url = (site_url or self._site_url).rstrip("/")
        image_url = f"{base_url}/{path.lstrip('/')}"
        headers = {
            "user-agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132 Safari/537.36",
            "referer": f"{base_url}/plant_game.php",
            "accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        if self._cookie:
            headers["cookie"] = self._cookie
        try:
            resp = requests.get(image_url, headers=headers, proxies=self._get_proxies(), timeout=15)
            if resp.status_code == 200 and resp.content:
                content_type = resp.headers.get("content-type", "image/png")
                b64 = base64.b64encode(resp.content).decode("utf-8")
                return {"success": True, "data": f"data:{content_type};base64,{b64}"}
        except Exception as e:
            logger.warning(f"{self.plugin_name}: 代理图片失败 {image_url}: {e}")
        return {"success": False, "message": "图片加载失败"}

    def _get_proxies(self):
        """根据配置返回代理设置。"""
        return settings.PROXY if self._use_proxy else None

    def _request(self, action: Optional[str] = None, method: str = "GET", data: dict = None, params: dict = None) -> Optional[requests.Response]:
        """请求思齐农场接口，自动附加 Cookie、Referer 与 action 参数。"""
        cookie_res = self.__get_cookie()
        if not cookie_res.get("success"):
            logger.error(f"{self.plugin_name}: {cookie_res.get('msg')}")
            return None

        site_url, user_agent = self._get_site_info()
        base_url = (site_url or self._site_url).rstrip("/")
        user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132 Safari/537.36"
        url = f"{base_url}/plant_game.php"
        headers = {
            "cookie": self._cookie,
            "referer": f"{base_url}/plant_game.php",
            "user-agent": user_agent,
            "accept": "application/json, text/javascript, */*; q=0.01",
            "x-requested-with": "XMLHttpRequest",
        }
        params = dict(params or {})
        payload = dict(data or {})
        if action:
            if method.upper() == "GET":
                params["action"] = action
            else:
                payload["action"] = action

        for idx in range(max(1, self._retry_count + 1)):
            try:
                if method.upper() == "POST":
                    return requests.post(url, headers=headers, data=payload, params=params, proxies=self._get_proxies(), timeout=30)
                return requests.get(url, headers=headers, params=params, proxies=self._get_proxies(), timeout=30)
            except Exception as e:
                logger.warning(f"{self.plugin_name}: 请求异常 {action or ''} {idx + 1}: {e}")
                if idx < self._retry_count:
                    time.sleep(self._retry_interval)
        return None

    @staticmethod
    def _json_response(response: Optional[requests.Response]) -> Dict[str, Any]:
        """将接口响应转换为 JSON 字典，兼容非 JSON 返回。"""
        if not response:
            return {"success": False, "message": "请求失败"}
        try:
            return response.json()
        except Exception:
            text = response.text[:500] if response is not None else ""
            return {"success": False, "message": "站点返回非 JSON 数据", "raw": text}

    def _get_data(self) -> Dict[str, Any]:
        """获取农场数据并缓存最新状态。"""
        data = self.get_farm_data()
        if data.get("success"):
            self.save_data("farm_status", data)
        return data

    def _refresh_data(self, payload: dict = None) -> Dict[str, Any]:
        """手动刷新农场数据并记录刷新时间。"""
        data = self.get_farm_data()
        if data.get("success"):
            self.save_data("farm_status", data)
            self.save_data("last_run", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return data

    def get_farm_data(self) -> Dict[str, Any]:
        """请求站点 fetch 接口并补充汇总统计与页面元信息。"""
        res = self._request("fetch", "GET")
        data = self._json_response(res)
        if data.get("success"):
            data["summary"] = self._build_summary(data)
            page_meta = self._get_page_meta()
            data["current_username"] = data.get("current_username") or page_meta.get("current_username", "")
            data["user_steal_gain"] = data.get("user_steal_gain", page_meta.get("user_steal_gain", 0))
            data["user_farm_like_total"] = data.get("user_farm_like_total", page_meta.get("user_farm_like_total", 0))
        return data

    def _get_current_username(self) -> str:
        """从页面元信息中获取当前用户名。"""
        return self._get_page_meta().get("current_username", "")

    def _get_page_meta(self) -> Dict[str, Any]:
        """解析农场页面中的用户名、偷菜收益和点赞统计。"""
        try:
            response = self._request(None, "GET")
            if not response or not response.text:
                return {}
            text = response.text
            username_match = re.search(r"<a[^>]+userdetails\.php\?id=\d+[^>]*>\s*<b>([^<]+)</b>", text)
            steal_match = re.search(r'id=["\']user-steal-gain["\'][^>]*>\s*([^<]+)\s*</span>', text)
            like_match = re.search(r'id=["\']user-farm-like-total["\'][^>]*>\s*([^<]+)\s*</span>', text)
            return {
                "current_username": html.unescape(username_match.group(1)).strip() if username_match else "",
                "user_steal_gain": self._parse_number(steal_match.group(1)) if steal_match else 0,
                "user_farm_like_total": self._parse_number(like_match.group(1)) if like_match else 0,
            }
        except Exception as e:
            logger.debug(f"{self.plugin_name}: 解析页面统计失败: {e}")
            return {}

    @staticmethod
    def _parse_number(value: Any) -> float:
        """从字符串中提取数字。"""
        try:
            text = re.sub(r"[^0-9.\-]", "", str(value or ""))
            if not text:
                return 0
            num = float(text)
            return int(num) if num.is_integer() else num
        except Exception:
            return 0

    @staticmethod
    def _build_summary(data: Dict[str, Any]) -> Dict[str, Any]:
        """根据农场数据构建成熟、空地、已种植和背包汇总。"""
        user_lands = data.get("user_lands") or []
        now = int(time.time())
        ready = sum(1 for item in user_lands if SiqiFram._is_plot_ready(item, now))
        empty = sum(1 for item in user_lands if not item.get("seed_id"))
        planted = sum(1 for item in user_lands if item.get("seed_id"))
        inventory = sum(int(item.get("quantity") or 0) for item in data.get("inventory") or [])
        return {"ready": ready, "empty": empty, "planted": planted, "inventory": inventory}

    @staticmethod
    def _is_plot_ready(plot: Dict[str, Any], now: Optional[int] = None) -> bool:
        """判断单个坑位是否已成熟可收获。"""
        if not plot or not plot.get("seed_id"):
            return False
        if str(plot.get("is_ready")) == "1":
            return True
        try:
            harvest_time = int(float(plot.get("harvest_time") or 0))
        except Exception:
            harvest_time = 0
        return harvest_time > 0 and harvest_time <= (now or int(time.time()))

    def _plant(self, payload: dict = None) -> Dict[str, Any]:
        """在指定坑位种植作物。"""
        payload = payload or {}
        data = {
            "land_id": payload.get("land_id"),
            "plot_index": payload.get("plot_index"),
            "seed_id": payload.get("seed_id") or self._seed_id,
        }
        result = self._json_response(self._request("plant", "POST", data=data))
        self._save_latest_if_success(result)
        return result

    def _plant_fill_empty(self, payload: dict = None) -> Dict[str, Any]:
        """一键为空地补种默认或指定种子。"""
        payload = payload or {}
        result = self._json_response(self._request("plant_fill_empty", "POST", data={"seed_id": payload.get("seed_id") or self._seed_id}))
        self._save_latest_if_success(result)
        return result

    def _buy_plot_slot(self, payload: dict = None) -> Dict[str, Any]:
        """购买指定农场的下一个坑位。"""
        payload = payload or {}
        land_id = payload.get("land_id")
        if land_id is None or land_id == "":
            return {"success": False, "message": "缺少 land_id"}
        result = self._json_response(self._request("buy_plot_slot", "POST", data={"land_id": land_id}))
        self._save_latest_if_success(result)
        return result

    def _harvest(self, payload: dict = None) -> Dict[str, Any]:
        """收获指定坑位作物。"""
        payload = payload or {}
        result = self._json_response(self._request("harvest", "POST", data={"land_id": payload.get("land_id"), "plot_index": payload.get("plot_index")}))
        self._save_latest_if_success(result)
        return result

    def _harvest_ready(self, payload: dict = None) -> Dict[str, Any]:
        """逐格收获所有成熟作物，作为验证码一键收获的兜底方案。"""
        data = self.get_farm_data()
        if not data.get("success"):
            return data
        logs = []
        now = int(time.time())
        for plot in data.get("user_lands") or []:
            if self._is_plot_ready(plot, now):
                res = self._harvest({"land_id": plot.get("land_id"), "plot_index": plot.get("plot_index")})
                logs.append(res.get("msg") or res.get("message") or str(res.get("success")))
                time.sleep(0.3)
        fresh = self.get_farm_data()
        if fresh.get("success"):
            self.save_data("farm_status", fresh)
        return {"success": True, "message": f"已尝试收获 {len(logs)} 个成熟作物", "logs": logs, "farm_status": fresh}

    def _get_harvest_captcha(self) -> Dict[str, Any]:
        """获取一键收获验证码信息。"""
        return self._json_response(self._request("get_harvest_all_captcha", "POST"))

    def _harvest_all(self, payload: dict = None) -> Dict[str, Any]:
        """提交验证码并调用站点一键收获接口。"""
        payload = payload or {}
        data = {"imagehash": payload.get("imagehash"), "imagestring": payload.get("imagestring")}
        result = self._json_response(self._request("harvest_all", "POST", data=data))
        if result.get("success"):
            self._save_latest_if_success(result)
        return result

    def _ocr_captcha(self, image_url: str) -> Optional[str]:
        """通过 MP OCR 服务识别验证码图片，返回识别文本或 None"""
        site_url, user_agent = self._get_site_info()
        base_url = (site_url or self._site_url).rstrip("/")
        # 处理相对路径
        full_url = image_url if image_url.startswith("http") else f"{base_url}/{image_url.lstrip('/')}"
        headers = {
            "user-agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "referer": f"{base_url}/plant_game.php",
            "accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        if self._cookie:
            headers["cookie"] = self._cookie
        try:
            resp = requests.get(full_url, headers=headers, proxies=self._get_proxies(), timeout=15)
            if resp.status_code != 200 or not resp.content:
                logger.warning(f"{self.plugin_name}: 验证码图片下载失败 {resp.status_code}")
                return None
            image_b64 = base64.b64encode(resp.content).decode("utf-8")
        except Exception as e:
            logger.warning(f"{self.plugin_name}: 验证码图片下载异常: {e}")
            return None

        ocr_host = getattr(settings, "OCR_HOST", None)
        if not ocr_host:
            logger.warning(f"{self.plugin_name}: OCR_HOST 未配置，跳过 OCR 识别")
            return None
        ocr_url = f"{ocr_host.rstrip('/')}/captcha/base64"
        try:
            ocr_resp = requests.post(
                ocr_url,
                json={"base64_img": image_b64},
                timeout=30,
            )
            if ocr_resp.status_code == 200:
                result = ocr_resp.json()
                text = (result.get("result") or "").strip()
                if text:
                    logger.info(f"{self.plugin_name}: OCR 识别验证码结果: {text}")
                    return text
                logger.warning(f"{self.plugin_name}: OCR 返回空结果: {result}")
            else:
                logger.warning(f"{self.plugin_name}: OCR 服务返回 {ocr_resp.status_code}")
        except Exception as e:
            logger.warning(f"{self.plugin_name}: OCR 请求异常: {e}")
        return None

    def _ai_recognize_captcha(self, image_url: str) -> Optional[str]:
        """通过 MP AI 智能助手 (RecognizeCaptchaTool) 识别验证码"""
        if not getattr(settings, "AI_AGENT_ENABLE", False):
            logger.warning(f"{self.plugin_name}: AI 智能助手未启用，跳过 AI 识别")
            return None
        try:
            from app.agent.tools.impl.recognize_captcha import RecognizeCaptchaTool
            import asyncio
            import json
            import concurrent.futures

            cookie_res = self.__get_cookie()
            cookie = cookie_res.get("cookie", "")
            _, user_agent = self._get_site_info()
            ua = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

            tool = RecognizeCaptchaTool(session_id="siqifram", user_id="plugin")

            async def _do_recognize():
                raw = await tool.run(
                    image_url=image_url,
                    cookie=cookie or "",
                    user_agent=ua,
                    allow_private_network=False,
                )
                if isinstance(raw, str):
                    return json.loads(raw)
                return raw

            try:
                asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(asyncio.run, _do_recognize())
                    result = fut.result(timeout=60)
            except RuntimeError:
                result = asyncio.run(_do_recognize())

            if isinstance(result, dict) and result.get("success"):
                text = (result.get("captcha_text") or "").strip()
                if text:
                    logger.info(f"{self.plugin_name}: AI 识别验证码结果: {text}")
                    return text
            logger.warning(f"{self.plugin_name}: AI 识别无结果: {result}")
        except ImportError:
            logger.warning(f"{self.plugin_name}: RecognizeCaptchaTool 不可用")
        except Exception as e:
            logger.warning(f"{self.plugin_name}: AI 识别异常: {e}")
        return None

    def _harvest_ready_ocr(self) -> Dict[str, Any]:
        """OCR 验证码识别 → harvest_all，失败则 AI 降级 → 逐格收获兜底"""
        for attempt in range(_CAPTCHA_RETRY):
            captcha_resp = self._get_harvest_captcha()
            captcha = captcha_resp.get("captcha")
            if not captcha_resp.get("success") or not captcha:
                logger.warning(f"{self.plugin_name}: 获取验证码失败(第{attempt+1}次)")
                continue
            imagehash = captcha.get("imagehash")
            image_url = captcha.get("image_url")
            if not imagehash or not image_url:
                continue

            captcha_text = self._ocr_captcha(image_url)
            if not captcha_text:
                logger.warning(f"{self.plugin_name}: OCR 识别失败(第{attempt+1}次)")
                continue

            result = self._harvest_all({"imagehash": imagehash, "imagestring": captcha_text})
            if result.get("success"):
                fresh = self.get_farm_data()
                if fresh.get("success"):
                    self.save_data("farm_status", fresh)
                return {"success": True, "message": result.get("msg") or "一键收获成功", "harvest_result": result}
            if result.get("captcha_required") or "验证码" in (result.get("msg") or result.get("message") or ""):
                logger.warning(f"{self.plugin_name}: 验证码错误，第{attempt+1}次重试")
                continue
            break

        # OCR 全失败 → AI 辅助识别（如启用）
        if self._use_ai_captcha and getattr(settings, "AI_AGENT_ENABLE", False):
            logger.info(f"{self.plugin_name}: OCR 收获失败，尝试 AI 辅助识别验证码")
            for attempt in range(_CAPTCHA_RETRY):
                captcha_resp = self._get_harvest_captcha()
                captcha = captcha_resp.get("captcha")
                if not captcha_resp.get("success") or not captcha:
                    continue
                imagehash = captcha.get("imagehash")
                image_url = captcha.get("image_url")
                if not imagehash or not image_url:
                    continue

                captcha_text = self._ai_recognize_captcha(image_url)
                if not captcha_text:
                    logger.warning(f"{self.plugin_name}: AI 识别失败(第{attempt+1}次)")
                    continue

                result = self._harvest_all({"imagehash": imagehash, "imagestring": captcha_text})
                if result.get("success"):
                    fresh = self.get_farm_data()
                    if fresh.get("success"):
                        self.save_data("farm_status", fresh)
                    return {"success": True, "message": result.get("msg") or "一键收获成功", "harvest_result": result}
                if result.get("captcha_required") or "验证码" in (result.get("msg") or result.get("message") or ""):
                    continue
                break

        # 全部失败 → 降级到逐格收获
        logger.warning(f"{self.plugin_name}: OCR+AI 收获均失败，降级到逐格收获")
        return self._harvest_ready()

    def _sell_inventory(self, payload: dict = None) -> Dict[str, Any]:
        """出售指定背包作物库存。"""
        payload = payload or {}
        result = self._json_response(self._request("sell_inventory", "POST", data={"seed_id": payload.get("seed_id"), "quantity": payload.get("quantity", 1)}))
        self._save_latest_if_success(result)
        return result

    def _sell_all_inventory(self) -> Dict[str, Any]:
        """出售背包中所有可出售作物库存。"""
        farm = self.get_farm_data()
        if not farm.get("success"):
            return {"success": False, "message": farm.get("msg") or farm.get("message") or "获取背包失败"}
        inventory = farm.get("inventory") or []
        logs = []
        for item in inventory:
            seed_id = item.get("seed_id")
            quantity = self._to_int(item.get("quantity"), 0)
            if not seed_id or quantity <= 0:
                continue
            result = self._json_response(self._request("sell_inventory", "POST", data={"seed_id": seed_id, "quantity": quantity}))
            logs.append(result.get("msg") or result.get("message") or f"已尝试出售 {quantity} 份")
            time.sleep(0.3)
        fresh = self.get_farm_data()
        if fresh.get("success"):
            self.save_data("farm_status", fresh)
        return {"success": True, "message": f"已尝试出售 {len(logs)} 类库存" if logs else "背包暂无可出售库存", "logs": logs, "farm_status": fresh}

    def _get_steal_target(self, payload: dict = None) -> Dict[str, Any]:
        """获取可偷菜目标农场。"""
        return self._json_response(self._request("get_victim_farm", "POST"))

    def _steal_plot(self, payload: dict = None) -> Dict[str, Any]:
        """偷取指定目标农场的指定坑位作物。"""
        payload = payload or {}
        result = self._json_response(self._request("steal_vegetable", "POST", data={
            "victim_id": payload.get("victim_id"),
            "land_id": payload.get("land_id"),
            "plot_index": payload.get("plot_index"),
        }))
        self._save_latest_if_success(result)
        return result

    def _finish_stealing(self, payload: dict = None) -> Dict[str, Any]:
        """结束当前偷菜会话并刷新农场状态。"""
        result = self._json_response(self._request("finish_stealing", "POST"))
        if result.get("success"):
            fresh = self.get_farm_data()
            if fresh.get("success"):
                self.save_data("farm_status", fresh)
        return result

    def _steal_once(self, payload: dict = None) -> Dict[str, Any]:
        """自动寻找可偷作物，并按今日剩余可偷数量执行偷菜流程。"""
        victim = self._json_response(self._request("get_victim_farm", "POST"))
        if not victim.get("success"):
            if self._is_daily_action_exhausted(victim):
                self._mark_daily_action_done("steal", victim)
            return victim
        victim_id = victim.get("victim_id")
        max_count = self._to_int(victim.get("max_steal_count"), 0)
        stolen_today = self._to_int(victim.get("steal_count_today"), 0)
        remaining = max_count - stolen_today if max_count > 0 else 1
        if remaining <= 0:
            result = {"success": False, "message": "今日可偷数量已用完", "victim": victim}
            self._mark_daily_action_done("steal", result)
            return result

        victim_lands = victim.get("victim_lands") or []
        unlocked_lands = {
            int(land.get("id"))
            for land in victim_lands
            if land.get("id") is not None and (land.get("unlocked") is None or self._to_int(land.get("unlocked"), 1))
        }
        plots = []
        candidate_plots = victim.get("victim_plots") or []
        # 兼容旧结构：lands/user_lands 内嵌 plots
        if not candidate_plots:
            for land in victim.get("lands") or victim.get("user_lands") or []:
                if not isinstance(land, dict):
                    continue
                land_id = land.get("id") or land.get("land_id")
                for plot in land.get("plots") or []:
                    if isinstance(plot, dict):
                        candidate_plots.append({**plot, "land_id": plot.get("land_id") or land_id})
        for plot in candidate_plots:
            if not isinstance(plot, dict):
                continue
            land_id = plot.get("land_id")
            if victim_lands and (land_id is None or int(land_id) not in unlocked_lands):
                continue
            if self._is_plot_ready(plot):
                plots.append((land_id, plot.get("plot_index")))
        if not plots:
            return {"success": False, "message": "未找到可偷作物", "victim": victim}

        logs = []
        success_count = 0
        total_reward = 0
        last_result = {"success": False, "message": "偷菜失败"}
        for land_id, plot_index in plots[:remaining]:
            if land_id is None or plot_index is None:
                continue
            result = self._json_response(self._request("steal_vegetable", "POST", data={"victim_id": victim_id, "land_id": land_id, "plot_index": plot_index}))
            last_result = result
            logs.append(result.get("msg") or result.get("message") or str(result.get("success")))
            if result.get("success"):
                success_count += 1
                total_reward += self._to_int(result.get("reward"), 0)
                time.sleep(0.3)
            else:
                break

        if success_count > 0:
            self._json_response(self._request("finish_stealing", "POST"))
            fresh = self.get_farm_data()
            if fresh.get("success"):
                self.save_data("farm_status", fresh)
            result = {"success": True, "message": f"偷菜完成：成功 {success_count} 个，获得 {total_reward} 魔力", "logs": logs, "last_result": last_result}
            self._mark_daily_action_done("steal", result)
            return result
        result = {"success": False, "message": last_result.get("msg") or last_result.get("message") or "偷菜失败", "logs": logs, "victim": victim}
        if self._is_daily_action_exhausted(result):
            self._mark_daily_action_done("steal", result)
        return result

    def _like_random(self, payload: dict = None) -> Dict[str, Any]:
        """随机获取点赞目标并批量点赞，或按传入用户名点赞。"""
        payload = payload or {}
        if payload.get("usernames"):
            result = self._json_response(self._request("like_farm_batch", "POST", data={"usernames": payload.get("usernames")}))
            self._save_latest_if_success(result)
            if result.get("success") or self._is_daily_action_exhausted(result):
                self._mark_daily_action_done("like", result)
            return result
        targets = self._json_response(self._request("random_like_targets", "POST"))
        if not targets.get("success"):
            if self._is_daily_action_exhausted(targets):
                self._mark_daily_action_done("like", targets)
            return targets
        usernames = "\n".join(targets.get("usernames") or [])
        if not usernames:
            result = {"success": False, "message": "没有可点赞目标", "targets": targets}
            self._mark_daily_action_done("like", result)
            return result
        result = self._json_response(self._request("like_farm_batch", "POST", data={"usernames": usernames}))
        self._save_latest_if_success(result)
        if result.get("success") or self._is_daily_action_exhausted(result):
            self._mark_daily_action_done("like", result)
        return result

    def _like_targets(self, payload: dict = None) -> Dict[str, Any]:
        """获取随机点赞目标用户名列表。"""
        return self._json_response(self._request("random_like_targets", "POST"))

    def _like_farm(self, payload: dict = None) -> Dict[str, Any]:
        """点赞指定目标农场。"""
        payload = payload or {}
        target_id = payload.get("target_id")
        if not target_id:
            return {"success": False, "message": "缺少 target_id"}
        result = self._json_response(self._request("like_farm", "POST", data={"target_id": target_id}))
        self._save_latest_if_success(result)
        return result

    def _visit_farm(self, payload: dict = None) -> Dict[str, Any]:
        """按用户名访问指定用户农场。"""
        payload = payload or {}
        username = payload.get("username", "").strip()
        if not username:
            return {"success": False, "message": "请输入用户名"}
        result = self._json_response(self._request("view_farm_by_username", "POST", data={"username": username}))
        # 确保用户名始终可用
        if result.get("success"):
            if not any(result.get(k) for k in ["target_desc_name", "target_name", "target_username", "username", "user_name"]):
                result["target_desc_name"] = username
            result["request_username"] = username
        return result

    def _visit_random_farm(self, payload: dict = None) -> Dict[str, Any]:
        """随机访问一个用户农场。"""
        result = self._json_response(self._request("view_random_farm", "POST"))
        if result.get("success"):
            name = result.get("target_desc_name") or result.get("target_name") or result.get("target_username") or result.get("username") or result.get("user_name") or "随机用户"
            result["target_desc_name"] = name
        return result

    @staticmethod
    def _today_key() -> str:
        """返回当前日期键，用于每日任务去重。"""
        return datetime.now().strftime("%Y-%m-%d")

    def _is_daily_action_done(self, action: str) -> bool:
        """判断指定自动动作今天是否已经完成或确认无剩余次数。"""
        return self.get_data(f"auto_{action}_done_date") == self._today_key()

    @staticmethod
    def _is_daily_action_exhausted(result: Dict[str, Any]) -> bool:
        """判断接口结果是否表示今日次数已用完或没有可执行目标。"""
        message = str(result.get("msg") or result.get("message") or "")
        exhausted_keywords = (
            "今日可偷数量已用完",
            "没有可点赞目标",
            "已用完",
            "无剩余",
            "没有剩余",
            "达到上限",
            "次数不足",
        )
        return any(keyword in message for keyword in exhausted_keywords)

    def _mark_daily_action_done(self, action: str, result: Dict[str, Any] = None) -> None:
        """记录指定自动动作今天已完成，避免定时任务重复请求。"""
        self.save_data(f"auto_{action}_done_date", self._today_key())
        if result is not None:
            self.save_data(f"auto_{action}_done_result", result.get("msg") or result.get("message") or "已完成")

    def _save_latest_if_success(self, result: Dict[str, Any]) -> None:
        """接口成功后刷新并缓存最新农场状态。"""
        if result.get("success"):
            fresh = self.get_farm_data()
            if fresh.get("success"):
                self.save_data("farm_status", fresh)
                self.save_data("last_run", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @staticmethod
    def _format_plant_task_message(message: Any) -> str:
        """格式化定时任务推送中的一键种植结果。"""
        text = str(message or "种植完成").strip()
        match = re.match(r"^(.*?：)(.+?)[，,]\s*(共种植\s*\d+\s*坑.*)$", text)
        if not match:
            return text
        prefix, crops, summary = match.groups()
        crops = re.sub(r"[，,]\s*", "、", crops.strip())
        return f"{prefix}\n━━━{crops}\n━━━{summary.strip()}"

    def _farm_task(self) -> None:
        """执行定时自动化任务并发送格式化通知。"""
        logs = []
        try:
            run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_data("last_run", run_time)
            if self._auto_harvest:
                res = self._harvest_ready_ocr()
                logs.append(f"🌾 收获：{res.get('message') or '收获完成'}")
            if self._auto_sell:
                res = self._sell_all_inventory()
                logs.append(f"💰 出售：{res.get('msg') or res.get('message') or '出售完成'}")
            if self._auto_plant:
                res = self._plant_fill_empty({"seed_id": self._seed_id})
                plant_message = self._format_plant_task_message(res.get("msg") or res.get("message") or "种植完成")
                logs.append(f"🌱 种植：{plant_message}")
            if self._auto_steal:
                if self._is_daily_action_done("steal"):
                    logs.append("🥷 偷菜：今日已完成，自动跳过")
                else:
                    res = self._steal_once()
                    logs.append(f"🥷 偷菜：{res.get('msg') or res.get('message') or '偷菜完成'}")
            if self._auto_like:
                if self._is_daily_action_done("like"):
                    logs.append("👍 点赞：今日已完成，自动跳过")
                else:
                    res = self._like_random()
                    logs.append(f"👍 点赞：{res.get('msg') or res.get('message') or '点赞完成'}")
            data = self.get_farm_data()
            if data.get("success"):
                self.save_data("farm_status", data)
            summary = data.get("summary") or {}
            username = data.get("current_username") or "-"
            user_bonus = data.get("user_bonus", "-")
            result = "\n".join([
                "━━━━━━━━━━━━━━",
                "✨ 状态：✅执行完成",
                "━━━━━━━━━━━━━━",
                "📋 操作结果",
                *(logs or ["ℹ️ 本次无自动操作"]),
                "━━━━━━━━━━━━━━",
                "📊 农场统计",
                f"👤 用户：{username}",
                f"🪄 魔力值：{user_bonus}",
                f"🌾 成熟作物：{summary.get('ready', '-')}",
                f"🌱 已种植：{summary.get('planted', '-')}",
                f"🕳️ 空地：{summary.get('empty', '-')}",
                f"🎒 背包库存：{summary.get('inventory', '-')}",
                "━━━━━━━━━━━━━━",
                f"🕐 执行时间：{run_time}",
            ])
            self.save_data("last_result", result)
            if self._notify:
                self.post_message(mtype=NotificationType.SiteMessage, title="【🌱思齐农场】任务完成", text=result)
        except Exception as e:
            logger.error(f"{self.plugin_name}: 定时任务失败: {e}")
            run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = "\n".join([
                "━━━━━━━━━━━━━━",
                "✨ 状态：❌执行失败",
                "━━━━━━━━━━━━━━",
                f"⚠️ 错误信息：{e}",
                "━━━━━━━━━━━━━━",
                f"🕐 执行时间：{run_time}",
            ])
            self.save_data("last_result", result)
            if self._notify:
                self.post_message(mtype=NotificationType.SiteMessage, title="【🌱思齐农场】任务失败", text=result)
