import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from apscheduler.triggers.cron import CronTrigger
from bs4 import BeautifulSoup
from app.core.config import settings
from app.db.site_oper import SiteOper
from app.helper.browser import PlaywrightHelper
from app.helper.sites import SitesHelper
from app.log import logger
from app.plugins import _PluginBase
from app.scheduler import Scheduler
from app.schemas import NotificationType
from app.utils.http import RequestUtils


class Savept(_PluginBase):
    # 插件名称
    plugin_name = "Vue-PT监护室"
    # 插件描述
    plugin_desc = "展示 PT 站点运行状态、病危通知与站庆预告。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/savept.png"
    # 插件版本
    plugin_version = "1.1.1"
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
    # 是否使用代理
    _use_proxy: bool = False
    # 是否启用浏览器仿真
    _use_browser_emulation: bool = False
    # 缓存上一次抓取结果
    _last_snapshot: Dict[str, Any] = {}
    # 浏览器仿真实例缓存
    _playwright: Optional[PlaywrightHelper] = None

    # MP 标准接口未暴露但实际支持的站点
    _HIDDEN_SITES: Dict[str, Dict[str, Any]] = {
        "exoticaz.to": {
            "id": "exoticaz",
            "name": "ExoticaZ",
            "url": "https://exoticaz.to/",
            "public": False,
        },
    }

    def __init__(self):
        super().__init__()
        self.siteoper = SiteOper()
        self.sites = SitesHelper()

    def init_plugin(self, config: dict = None) -> None:
        """初始化插件配置并设置默认值。"""
        config = config or {}
        self._enabled = self._to_bool(config.get("enabled", True))
        self._source_url = (config.get("source_url") or "https://savept.icu/").strip()
        self._request_timeout = max(int(config.get("request_timeout") or 15), 5)
        self._default_internal_only = bool(config.get("default_internal_only", False))
        self._notify = self._to_bool(config.get("notify", True))
        self._cron = (config.get("cron") or "0 8 * * *").strip()
        self._use_proxy = self._to_bool(config.get("use_proxy", False))
        self._use_browser_emulation = self._to_bool(config.get("use_browser_emulation", False))

        if self._use_browser_emulation:
            if not self._playwright:
                self._playwright = PlaywrightHelper()
        else:
            self._playwright = None

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
            "use_proxy": self._use_proxy,
            "use_browser_emulation": self._use_browser_emulation,
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
            "use_proxy": self._to_bool(config_payload.get("use_proxy", self._use_proxy)),
            "use_browser_emulation": self._to_bool(config_payload.get("use_browser_emulation", self._use_browser_emulation)),
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

    def _get_page_source(self, url: str) -> Optional[str]:
        """获取页面 HTML 源码，支持代理和浏览器仿真。"""
        proxies = self.__get_proxies()
        proxy_server = settings.PROXY_SERVER if self._use_proxy else None

        if self._use_browser_emulation:
            logger.info(f"[{self.plugin_name}] 使用 {settings.BROWSER_EMULATION} 浏览器仿真请求: {url}")
            if not self._playwright:
                self._playwright = PlaywrightHelper()
            return self._playwright.get_page_source(
                url=url,
                cookies=None,
                proxies=proxy_server,
                timeout=max(self._request_timeout, 60),
            )

        response = RequestUtils(proxies=proxies).get_res(url=url)
        if response and response.status_code == 200:
            return response.text

        status_code = response.status_code if response else "无响应"
        logger.error(f"[{self.plugin_name}] 普通请求失败: {url}, 状态码: {status_code}")
        return None

    def __get_proxies(self):
        """获取代理设置。"""
        if not self._use_proxy:
            logger.debug(f"[{self.plugin_name}] 未启用代理")
            return None

        try:
            if hasattr(settings, "PROXY") and settings.PROXY:
                logger.debug(f"[{self.plugin_name}] 使用系统代理: {settings.PROXY}")
                return settings.PROXY
            logger.debug(f"[{self.plugin_name}] 系统代理未配置")
            return None
        except Exception as err:
            logger.error(f"[{self.plugin_name}] 获取代理设置出错: {err}")
            return None

    def _fetch_live_snapshot(self) -> Dict[str, Any]:
        """从源站实时抓取页面并解析站点快照。"""
        html = self._get_page_source(self._source_url)
        if not html:
            raise requests.RequestException("获取页面源码失败")

        alert_texts = self._extract_notice_texts(html)
        year_groups = self._extract_year_groups(html)
        sites = self._annotate_sites_with_mp_status(self._extract_site_cards(html))
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
                    "domain": self._extract_domain(item.get("url")),
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

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        return "".join(str(value).strip().lower().split())

    @classmethod
    def _normalize_site_name_candidates(cls, value: Any) -> List[str]:
        raw = cls._clean_text(value)
        if not raw:
            return []

        candidates: List[str] = []
        seen = set()

        def _add_candidate(text: str) -> None:
            normalized = cls._normalize_text(text)
            if normalized and normalized not in seen:
                seen.add(normalized)
                candidates.append(normalized)

        _add_candidate(raw)

        for separator in [" - ", " – ", " — ", " | ", " ｜ ", "/", "／"]:
            if separator in raw:
                parts = [part.strip() for part in raw.split(separator) if part.strip()]
                for part in parts:
                    _add_candidate(part)
                if parts:
                    _add_candidate(parts[0])

        for stripped in re.split(r"[（(\[【].*?[）)\]】]", raw):
            _add_candidate(stripped)

        return candidates

    @staticmethod
    def _normalize_url(url: Any) -> str:
        if not url:
            return ""
        raw = str(url).strip()
        if not raw:
            return ""
        if not raw.startswith(("http://", "https://")):
            raw = f"https://{raw}"
        parsed = urlparse(raw)
        host = (parsed.netloc or parsed.path).lower().split(":")[0]
        path = parsed.path if parsed.netloc else ""
        path = path.rstrip("/")
        return f"{host}{path}".rstrip("/")

    @staticmethod
    def _strip_www(host: str) -> str:
        return host[4:] if host.startswith("www.") else host

    @classmethod
    def _extract_domain(cls, url: Any) -> str:
        if not url:
            return ""
        raw = str(url).strip()
        if not raw:
            return ""
        if not raw.startswith(("http://", "https://")):
            raw = f"https://{raw}"
        parsed = urlparse(raw)
        return (parsed.netloc or parsed.path).lower().split(":")[0]

    def _build_standard_indexes(self) -> Dict[str, Any]:
        raw_sites = {**self._HIDDEN_SITES, **(self.sites.get_indexsites() or {})}
        url_index: Dict[str, Dict[str, Any]] = {}
        name_index: Dict[str, List[Dict[str, Any]]] = {}
        domain_index: Dict[str, List[Dict[str, Any]]] = {}
        site_groups: Dict[str, Dict[str, Any]] = {}

        for domain, site in raw_sites.items():
            site_domain = str(domain or "").lower()
            site_name = site.get("name") or domain
            site_url = site.get("url") or f"https://{domain}"
            site_id = site.get("id")
            group_key = str(site_id or self._normalize_text(site_name) or site_domain)

            standard_site = site_groups.get(group_key)
            if not standard_site:
                standard_site = {
                    "domain": site_domain,
                    "id": site_id,
                    "name": site_name,
                    "url": site_url,
                    "public": site.get("public"),
                    "alias_domains": set(),
                    "alias_urls": set(),
                    "alias_names": set(),
                }
                site_groups[group_key] = standard_site

            standard_site["alias_domains"].add(site_domain)
            extracted_domain = self._extract_domain(site_url)
            if extracted_domain:
                standard_site["alias_domains"].add(extracted_domain)

            normalized_url = self._normalize_url(site_url)
            if normalized_url:
                standard_site["alias_urls"].add(normalized_url)

            for normalized_name in self._normalize_site_name_candidates(site_name):
                standard_site["alias_names"].add(normalized_name)

        for standard_site in site_groups.values():
            for normalized_url in standard_site["alias_urls"]:
                url_index[normalized_url] = standard_site
            for normalized_name in standard_site["alias_names"]:
                name_index.setdefault(normalized_name, []).append(standard_site)
            for alias_domain in standard_site["alias_domains"]:
                domain_index.setdefault(alias_domain, []).append(standard_site)

        return {
            "url_index": url_index,
            "name_index": name_index,
            "domain_index": domain_index,
        }

    def _build_existing_domain_set(self) -> set:
        domains = set()
        try:
            for site in self.siteoper.list() or []:
                domain = getattr(site, "domain", None)
                if domain:
                    domains.add(str(domain).lower())
                    domains.add(self._strip_www(str(domain).lower()))
        except Exception as err:
            logger.error(f"[{self.plugin_name}] 获取 MP 已有站点失败: {err}")
        return domains

    @staticmethod
    def _pick_unique_standard_site(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        unique_sites: Dict[str, Dict[str, Any]] = {}
        for candidate in candidates:
            key = str(
                candidate.get("id")
                or candidate.get("domain")
                or candidate.get("url")
                or candidate.get("name")
                or ""
            )
            if key and key not in unique_sites:
                unique_sites[key] = candidate
        return next(iter(unique_sites.values())) if len(unique_sites) == 1 else None

    def _match_mp_site(self, site: Dict[str, Any], standard_indexes: Dict[str, Any], existing_domains: set) -> Dict[str, Any]:
        normalized_url = self._normalize_url(site.get("url"))
        normalized_names = self._normalize_site_name_candidates(site.get("name"))
        domain = (site.get("domain") or "").lower()
        normalized_url_nowww = self._strip_www(normalized_url) if normalized_url else ""
        domain_nowww = self._strip_www(domain) if domain else ""

        matched_standard = None
        match_type = "unmatched"

        if normalized_url and standard_indexes["url_index"].get(normalized_url):
            matched_standard = standard_indexes["url_index"][normalized_url]
            match_type = "url"
        elif normalized_url_nowww and normalized_url_nowww != normalized_url and standard_indexes["url_index"].get(normalized_url_nowww):
            matched_standard = standard_indexes["url_index"][normalized_url_nowww]
            match_type = "url"
        elif domain and standard_indexes["domain_index"].get(domain):
            candidates = standard_indexes["domain_index"][domain]
            unique_candidate = self._pick_unique_standard_site(candidates)
            if unique_candidate:
                matched_standard = unique_candidate
                match_type = "domain"
        elif domain_nowww and domain_nowww != domain and standard_indexes["domain_index"].get(domain_nowww):
            candidates = standard_indexes["domain_index"][domain_nowww]
            unique_candidate = self._pick_unique_standard_site(candidates)
            if unique_candidate:
                matched_standard = unique_candidate
                match_type = "domain"
        else:
            for normalized_name in normalized_names:
                if not normalized_name or not standard_indexes["name_index"].get(normalized_name):
                    continue
                candidates = standard_indexes["name_index"][normalized_name]
                unique_candidate = self._pick_unique_standard_site(candidates)
                if unique_candidate:
                    matched_standard = unique_candidate
                    match_type = "name"
                    break

            if not matched_standard and normalized_names:
                fuzzy_candidates: List[Dict[str, Any]] = []
                for standard_site in standard_indexes["url_index"].values():
                    alias_names = standard_site.get("alias_names") or set()
                    for normalized_name in normalized_names:
                        if not normalized_name:
                            continue
                        if any(
                            normalized_name == alias_name
                            or normalized_name in alias_name
                            or alias_name in normalized_name
                            for alias_name in alias_names
                        ):
                            fuzzy_candidates.append(standard_site)
                            break
                unique_candidate = self._pick_unique_standard_site(fuzzy_candidates)
                if unique_candidate:
                    matched_standard = unique_candidate
                    match_type = "name_fuzzy"

        if not matched_standard:
            return {
                **site,
                "mp_supported": False,
                "mp_exists": False,
                "mp_status": "unsupported",
                "mp_status_text": "MP未收录",
                "mp_match_type": match_type,
                "mp_site_id": "",
                "mp_site_name": "",
                "mp_site_domain": "",
                "mp_site_url": "",
                "mp_public": None,
            }

        target_domain = (matched_standard.get("domain") or self._extract_domain(matched_standard.get("url"))).lower()
        alias_domains = matched_standard.get("alias_domains") or set()
        already_exists = False
        for alias_domain in alias_domains:
            alias_domain = str(alias_domain or "").lower()
            alias_domain_nowww = self._strip_www(alias_domain) if alias_domain else ""
            if (alias_domain and alias_domain in existing_domains) or (alias_domain_nowww and alias_domain_nowww in existing_domains):
                already_exists = True
                break

        return {
            **site,
            "mp_supported": True,
            "mp_exists": already_exists,
            "mp_status": "owned" if already_exists else "available",
            "mp_status_text": "MP已拥有" if already_exists else "MP可添加",
            "mp_match_type": match_type,
            "mp_site_id": matched_standard.get("id") or "",
            "mp_site_name": matched_standard.get("name") or "",
            "mp_site_domain": target_domain,
            "mp_site_url": matched_standard.get("url") or "",
            "mp_public": matched_standard.get("public"),
        }

    def _annotate_sites_with_mp_status(self, sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standard_indexes = self._build_standard_indexes()
        existing_domains = self._build_existing_domain_set()
        return [self._match_mp_site(site, standard_indexes, existing_domains) for site in sites]

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
        mp_owned = len([item for item in sites if item.get("mp_status") == "owned"])
        mp_available = len([item for item in sites if item.get("mp_status") == "available"])
        mp_unsupported = len([item for item in sites if item.get("mp_status") == "unsupported"])
        return {
            "total": total,
            "healthy": healthy,
            "critical": critical,
            "closed": closed,
            "internal": internal,
            "external": external,
            "today_anniv": today_anniv,
            "years": len(year_groups),
            "mp_owned": mp_owned,
            "mp_available": mp_available,
            "mp_unsupported": mp_unsupported,
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

