import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from apscheduler.triggers.cron import CronTrigger
from bs4 import BeautifulSoup
from app.plugins import _PluginBase
from app.scheduler import Scheduler
from app.schemas import NotificationType


class Savept(_PluginBase):
    # 插件名称
    plugin_name = "Vue-PT监护室"
    # 插件描述
    plugin_desc = "展示 PT 站点运行状态、病危通知与站庆预告。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/savept.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "savept_"
    # 加载顺序
    plugin_order = 36
    # 可使用的用户级别
    auth_level = 2

    # 配置与缓存
    # 插件是否启用
    _enabled: bool = True
    # 监控源地址
    _source_url: str = "https://savept.icu/"
    # 页面抓取超时时间（秒）
    _request_timeout: int = 15
    # 是否默认仅展示内站
    _default_internal_only: bool = False
    # 是否发送定时公告通知
    _notify: bool = True
    # 公告定时任务 Cron 表达式
    _cron: str = "0 8 * * *"
    # 缓存上一次抓取结果
    _last_snapshot: Dict[str, Any] = {}

    def init_plugin(self, config: dict = None) -> None:
        """初始化插件配置并设置默认值。"""
        config = config or {}
        self._enabled = self._to_bool(config.get("enabled", True))
        self._source_url = (config.get("source_url") or "https://savept.icu/").strip()
        self._request_timeout = max(int(config.get("request_timeout") or 15), 5)
        self._default_internal_only = bool(config.get("default_internal_only", False))
        self._notify = self._to_bool(config.get("notify", True))
        self._cron = (config.get("cron") or "0 8 * * *").strip()

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def get_state(self) -> bool:
        """获取插件启用状态。"""
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """返回插件命令列表。"""
        return []

    def get_render_mode(self) -> Tuple[str, Optional[str]]:
        """返回渲染模式和前端资源目录。"""
        return "vue", "dist/assets"

    def get_sidebar_nav(self) -> List[Dict[str, Any]]:
        """返回侧边栏导航配置。"""
        return [
            {
                "nav_key": "main",
                "title": "PT监护室",
                "icon": "mdi-heart-pulse",
                "section": "discovery",
                "order": 18,
            },
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        """返回插件 API 路由定义。"""
        return [
            {
                "path": "/config",
                "endpoint": self._get_config,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取插件配置",
            },
            {
                "path": "/config",
                "endpoint": self._save_config,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "保存插件配置",
            },
            {
                "path": "/summary",
                "endpoint": self._get_summary,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取概览统计",
            },
            {
                "path": "/sites",
                "endpoint": self._get_sites,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取站点列表",
            },
            {
                "path": "/refresh",
                "endpoint": self._refresh_snapshot,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "刷新站点快照",
            },
        ]

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """Vue 插件需要返回页面配置数据。"""
        return None, self._get_config()

    def get_page(self) -> List[dict]:
        """Vue 模式下返回页面路由列表。"""
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """注册定时公告推送服务。"""
        services: List[Dict[str, Any]] = []
        if self._enabled and self._notify and self._cron:
            try:
                services.append(
                    {
                        "id": self.__class__.__name__.lower(),
                        "name": f"{self.plugin_name} - 公告定时推送",
                        "trigger": CronTrigger.from_crontab(self._cron),
                        "func": self._cron_push_notice,
                        "kwargs": {},
                    }
                )
            except Exception:
                pass
        return services

    def stop_service(self) -> None:
        """插件卸载时的清理逻辑。"""
        try:
            Scheduler().remove_plugin_job(self.__class__.__name__.lower())
        except Exception:
            pass

    def _persist_config(self) -> None:
        """持久化当前配置到插件存储。"""
        self.update_config(self._get_config())

    def _get_config(self) -> Dict[str, Any]:
        """获取当前插件配置。"""
        return {
            "enabled": self._enabled,
            "source_url": self._source_url,
            "request_timeout": self._request_timeout,
            "default_internal_only": self._default_internal_only,
            "notify": self._notify,
            "cron": self._cron or "0 8 * * *",
        }

    def _save_config(self, config_payload: dict) -> Dict[str, Any]:
        """保存配置并刷新当前插件状态。"""
        config_payload = config_payload or {}
        config_to_save = {
            "enabled": self._to_bool(config_payload.get("enabled", self._enabled)),
            "source_url": (config_payload.get("source_url") or self._source_url or "https://savept.icu/").strip(),
            "request_timeout": max(int(config_payload.get("request_timeout") or self._request_timeout or 15), 5),
            "default_internal_only": self._to_bool(config_payload.get("default_internal_only", self._default_internal_only)),
            "notify": self._to_bool(config_payload.get("notify", self._notify)),
            "cron": (config_payload.get("cron") or self._cron or "0 8 * * *").strip(),
        }
        self.stop_service()
        self.init_plugin(config_to_save)
        self.update_config(config_to_save)
        return {"success": True, "message": "配置已保存", "data": self._get_config()}

    def _get_summary(self) -> Dict[str, Any]:
        """获取当前统计汇总数据。"""
        snapshot = self._load_snapshot(force_refresh=False)
        return {"success": True, "data": snapshot.get("summary", {})}

    def _get_sites(self) -> Dict[str, Any]:
        """获取完整站点快照和公告数据。"""
        snapshot = self._load_snapshot(force_refresh=False)
        return {"success": True, "data": snapshot}

    def _refresh_snapshot(self, payload: dict = None) -> Dict[str, Any]:
        """强制刷新一次实时快照。"""
        snapshot = self._load_snapshot(force_refresh=True)
        return {"success": True, "message": "刷新成功", "data": snapshot}

    def _cron_push_notice(self) -> None:
        """按 Cron 定时抓取并推送公告。"""
        try:
            snapshot = self._load_snapshot(force_refresh=True)
            self._send_notice(snapshot)
        except Exception:
            pass

    def _send_notice(self, snapshot: Dict[str, Any]) -> None:
        """发送公告通知。"""
        if not self._notify:
            return

        title = "【🩺PT监护室】公告推送"
        text = self._build_notice_message(snapshot)
        try:
            self.post_message(
                mtype=NotificationType.Plugin,
                title=title,
                text=text,
            )
        except Exception:
            pass

    def _build_notice_message(self, snapshot: Dict[str, Any]) -> str:
        """格式化公告通知文本。"""
        alerts = snapshot.get("alerts") or []
        fetched_at = snapshot.get("fetched_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        grouped = {"critical": [], "success": [], "info": [], "error": []}
        for alert in alerts:
            level = alert.get("level")
            text = self._clean_text(alert.get("text"))
            if level in grouped and text:
                grouped[level].extend(self._split_notice_items(level, text))

        sections = [
            ("critical", "⚠️ 病危通知："),
            ("success", "✅ 恢复公告："),
            ("info", "🎉 站庆预告："),
            ("error", "🕯️ 死亡讣告："),
        ]

        lines: List[str] = []
        has_notice = False
        for key, title in sections:
            items = grouped.get(key) or []
            if not items:
                continue
            has_notice = True
            lines.append("━━━━━━━━━━━━━━")
            lines.append(title)
            for item in items:
                lines.append(f"• {item}")

        if not has_notice:
            lines.extend([
                "━━━━━━━━━━━━━━",
                "ℹ️ 暂无公告",
            ])

        lines.append("━━━━━━━━━━━━━━")
        lines.append(f"🕐 推送时间：{fetched_at}")
        return "\n".join(lines)

    def _split_notice_items(self, level: str, text: str) -> List[str]:
        """将公告正文拆分为逐条通知。"""
        text = self._clean_text(text).lstrip("• ").strip()
        if level == "critical":
            text = re.sub(r"^监测到站点异常，正在全力抢救中[：:]\s*", "", text)

        parts = re.split(r"\s*\|\s*", text)
        items: List[str] = []
        for part in parts:
            normalized = self._normalize_notice_item(level, part)
            if normalized:
                items.append(normalized)
        return items

    def _normalize_notice_item(self, level: str, text: Optional[str]) -> str:
        """规范单条公告的显示格式。"""
        item = self._clean_text(text).lstrip("• ").strip()
        if not item:
            return ""

        if level == "critical":
            item = re.sub(r"[，,]\s*濒临死亡$", "(濒临死亡)", item)
            item = re.sub(r"\s*\(\s*濒临死亡\s*\)$", "(濒临死亡)", item)
        elif level == "success":
            item = re.sub(r"[，,]\s*(于[^()]+恢复)$", r"(\1)", item)
            item = re.sub(r"\s*\(\s*(于[^()]+恢复)\s*\)$", r"(\1)", item)

        return item

    def _load_snapshot(self, force_refresh: bool = False) -> Dict[str, Any]:
        """加载缓存快照，必要时刷新或回退到兜底数据。"""
        if self._last_snapshot and not force_refresh:
            return self._last_snapshot
        try:
            snapshot = self._fetch_live_snapshot()
            if snapshot.get("sites"):
                self._last_snapshot = snapshot
                self.save_data("last_snapshot", snapshot)
                return snapshot
        except Exception as err:
            cached = self.get_data("last_snapshot") or {}
            if cached:
                cached["warning"] = f"实时抓取失败，已回退缓存：{err}"
                self._last_snapshot = cached
                return cached
            empty_snapshot = {
                "source_url": self._source_url,
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {
                    "total": 0,
                    "healthy": 0,
                    "critical": 0,
                    "closed": 0,
                    "internal": 0,
                    "external": 0,
                    "today_anniv": 0,
                    "years": 0,
                },
                "alerts": [],
                "year_groups": [],
                "sites": [],
                "default_internal_only": self._default_internal_only,
                "warning": f"实时抓取失败，暂无缓存可用：{err}",
            }
            self._last_snapshot = empty_snapshot
            return empty_snapshot

    def _fetch_live_snapshot(self) -> Dict[str, Any]:
        """从源站实时抓取页面并解析站点快照。"""
        response = requests.get(self._source_url, timeout=self._request_timeout)
        response.raise_for_status()
        html = response.text

        alert_texts = self._extract_notice_texts(html)
        year_groups = self._extract_year_groups(html)
        sites = self._extract_site_cards(html)
        summary = self._build_summary(sites, year_groups)

        return {
            "source_url": self._source_url,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "alerts": alert_texts,
            "year_groups": year_groups,
            "sites": sites,
            "default_internal_only": self._default_internal_only,
        }

    def _extract_notice_texts(self, html: str) -> List[Dict[str, str]]:
        """从页面中提取公告文本并返回标准化结果。"""
        soup = BeautifulSoup(html, "html.parser")
        notice_map = {
            "病危通知：": "critical",
            "恢复公告：": "success",
            "站庆预告：": "info",
            "死亡讣告：": "error",
        }
        results: List[Dict[str, str]] = []

        for strong in soup.find_all("strong"):
            title = self._clean_text(strong.get_text())
            level = notice_map.get(title)
            if not level:
                continue

            container = strong.parent
            if not container:
                continue

            text = self._clean_text(container.get_text(" ", strip=True))
            if text.startswith(title):
                text = self._clean_text(text[len(title):])

            if text:
                results.append({"level": level, "text": text})

        return results

    def _extract_year_groups(self, html: str) -> List[Dict[str, Any]]:
        """解析页面中的年份分组统计数据。"""
        groups: List[Dict[str, Any]] = []
        for year, count in re.findall(r">\s*(\d{4}|未知)\s*年\s*<.*?\((\d+) 个站点\)", html, re.S):
            groups.append({"year": year, "count": int(count)})
        return groups

    def _extract_site_cards(self, html: str) -> List[Dict[str, Any]]:
        """解析站点卡片并返回结构化站点列表。"""
        cards: List[Dict[str, Any]] = []
        pattern = re.compile(
            r'<a href="(?P<url>[^"]+)"[^>]*class="card-link"[^>]*data-year="(?P<year>[^"]+)"[^>]*data-status="(?P<status_key>[^"]+)"[^>]*data-search="(?P<search>[^"]*)"[^>]*data-type="(?P<site_type>[^"]+)"[^>]*data-anniversary="(?P<anniversary_flag>[^"]+)"[^>]*>\s*<div class="card[^>]*"[^>]*data-opentime="(?P<open_time>[^"]*)"[^>]*data-closetime="(?P<close_time>[^"]*)"[^>]*>.*?<div class="status-strip[^"]*" title="(?P<status_text>[^"]+)">.*?</div>\s*(?:<div class="anniversary-badge">\s*(?P<anniversary_text>[^<]+)\s*</div>)?\s*(?:<div class="duration-badge">\s*(?P<duration_text>[^<]+)\s*</div>)?\s*<img class="site-icon"[^>]*src="(?P<icon>[^"]+)"[^>]*>\s*<div class="card-title">\s*(?P<title>[^<]+)\s*</div>',
            re.S,
        )
        for match in pattern.finditer(html):
            item = match.groupdict()
            cards.append(
                {
                    "name": self._clean_text(item.get("title")),
                    "url": item.get("url"),
                    "icon": item.get("icon"),
                    "year": item.get("year"),
                    "status": self._normalize_status(item.get("status_key"), item.get("status_text")),
                    "status_text": self._clean_text(item.get("status_text")),
                    "site_type": "内站" if item.get("site_type") == "internal" else "外站",
                    "site_type_key": item.get("site_type"),
                    "anniversary_flag": item.get("anniversary_flag"),
                    "anniversary_text": self._clean_text(item.get("anniversary_text")),
                    "duration_text": self._clean_text(item.get("duration_text")),
                    "open_time": item.get("open_time"),
                    "close_time": item.get("close_time"),
                    "search": self._clean_text(item.get("search")),
                }
            )
        return cards

    def _build_summary(self, sites: List[Dict[str, Any]], year_groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建站点统计汇总数据。"""
        total = len(sites)
        healthy = len([item for item in sites if item.get("status") == "healthy"])
        critical = len([item for item in sites if item.get("status") == "critical"])
        closed = len([item for item in sites if item.get("status") == "closed"])
        internal = len([item for item in sites if item.get("site_type_key") == "internal"])
        external = len([item for item in sites if item.get("site_type_key") != "internal"])
        today_anniv = len([
            item for item in sites
            if item.get("status") != "closed" and self._is_today_anniversary(item.get("anniversary_text"))
        ])
        return {
            "total": total,
            "healthy": healthy,
            "critical": critical,
            "closed": closed,
            "internal": internal,
            "external": external,
            "today_anniv": today_anniv,
            "years": len(year_groups),
        }

    @staticmethod
    def _is_today_anniversary(value: Optional[str]) -> bool:
        text = Savept._clean_text(value)
        return "0天" in text or "今天" in text

    @staticmethod
    def _clean_text(value: Optional[str]) -> str:
        if not value:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()

    @staticmethod
    def _normalize_status(status_key: Optional[str], status_text: Optional[str]) -> str:
        """标准化页面状态为内部状态码。"""
        status_key = (status_key or "").lower()
        status_text = (status_text or "").strip()
        if status_key == "online" or "运行" in status_text or "健康" in status_text:
            return "healthy"
        if status_key in {"down", "critical"} or "病危" in status_text or "抢救" in status_text:
            return "critical"
        if status_key in {"closed", "offline"} or "已关站" in status_text or "死亡" in status_text:
            return "closed"
        return "unknown"

