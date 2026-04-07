import json
import zipfile
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

from fastapi import File, UploadFile

from app.db.site_oper import SiteOper
from app.helper.sites import SitesHelper
from app.log import logger
from app.plugins import _PluginBase


class PtdImporter(_PluginBase):
    # 插件名称
    plugin_name = "Vue-PTD站点导入"
    # 插件描述
    plugin_desc = "上传 PTD 备份并按 MoviePilot 标准站点批量导入/更新。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/PT_Depiler.png"
    # 插件版本
    plugin_version = "1.0.1"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "ptdimporter_"
    # 加载顺序
    plugin_order = 29
    # 可使用的用户级别
    auth_level = 2

    # 配置与状态
    _enabled: bool = False
    _only_active: bool = True
    _only_supported: bool = True
    _import_mode: str = "update_auth"
    _import_cookie: bool = True
    _import_token: bool = True
    _import_apikey: bool = True
    _default_ua: str = ""
    _default_proxy: bool = False
    _default_render: bool = False
    _last_preview: Dict[str, Any] = {}

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

    @staticmethod
    def _to_bool(val: Any) -> bool:
        """
        安全地将值转换为布尔类型
        
        :param val: 要转换的值
        :return: 布尔值
        """
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() == "true"
        return bool(val)

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """初始化插件，加载配置"""
        self._enabled = False
        self._only_active = True
        self._only_supported = True
        self._import_mode = "update_auth"
        self._import_cookie = True
        self._import_token = True
        self._import_apikey = True
        self._last_preview = {}

        if config:
            self._enabled = self._to_bool(config.get("enabled", False))
            self._only_active = self._to_bool(config.get("only_active", True))
            self._only_supported = self._to_bool(config.get("only_supported", True))
            self._import_mode = config.get("import_mode") or "update_auth"
            self._import_cookie = self._to_bool(config.get("import_cookie", True))
            self._import_token = self._to_bool(config.get("import_token", True))
            self._import_apikey = self._to_bool(config.get("import_apikey", True))
            self._default_ua = config.get("default_ua") or ""
            self._default_proxy = self._to_bool(config.get("default_proxy", False))
            self._default_render = self._to_bool(config.get("default_render", False))

    def get_state(self) -> bool:
        """获取插件状态"""
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取命令"""
        return []

    def get_api(self) -> List[dict]:
        """获取插件API配置"""
        return [
            {
                "path": "/config",
                "endpoint": self._get_config,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取插件配置"
            },
            {
                "path": "/config",
                "endpoint": self._save_config,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "保存插件配置"
            },
            {
                "path": "/status",
                "endpoint": self._get_status,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取插件状态"
            },
            {
                "path": "/analyze",
                "endpoint": self._analyze_backup,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "上传并解析 PTD 备份"
            },
            {
                "path": "/preview",
                "endpoint": self.get_preview,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取最近一次预览结果"
            },
            {
                "path": "/import",
                "endpoint": self.import_sites,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "导入已匹配站点"
            }
        ]

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """Vue模式下必须实现，返回None和初始配置数据"""
        return None, self._get_config()

    def get_render_mode(self) -> Tuple[str, Optional[str]]:
        """返回Vue渲染模式和组件路径"""
        return "vue", "dist/assets"

    def get_page(self) -> List[dict]:
        """Vue模式下必须实现，返回空列表"""
        return []

    def _get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "enabled": self._enabled,
            "only_active": self._only_active,
            "only_supported": self._only_supported,
            "import_mode": self._import_mode,
            "import_cookie": self._import_cookie,
            "import_token": self._import_token,
            "import_apikey": self._import_apikey,
            "default_ua": self._default_ua,
            "default_proxy": self._default_proxy,
            "default_render": self._default_render,
        }

    def _save_config(self, config_payload: dict) -> Dict[str, Any]:
        """保存配置"""
        config = {
            "enabled": self._to_bool(config_payload.get("enabled", False)),
            "only_active": self._to_bool(config_payload.get("only_active", True)),
            "only_supported": self._to_bool(config_payload.get("only_supported", True)),
            "import_mode": config_payload.get("import_mode") or "update_auth",
            "import_cookie": self._to_bool(config_payload.get("import_cookie", True)),
            "import_token": self._to_bool(config_payload.get("import_token", True)),
            "import_apikey": self._to_bool(config_payload.get("import_apikey", True)),
            "default_ua": config_payload.get("default_ua") or "",
            "default_proxy": self._to_bool(config_payload.get("default_proxy", False)),
            "default_render": self._to_bool(config_payload.get("default_render", False)),
        }
        self.update_config(config)
        self.init_plugin(config)
        return {"success": True, "message": "配置保存成功", "data": self._get_config()}

    def _get_status(self) -> Dict[str, Any]:
        """获取插件状态"""
        preview = self._last_preview or {}
        summary = preview.get("summary") or {}
        return {
            "enabled": self._enabled,
            "only_active": self._only_active,
            "only_supported": self._only_supported,
            "import_mode": self._import_mode,
            "import_cookie": self._import_cookie,
            "import_token": self._import_token,
            "import_apikey": self._import_apikey,
            "last_preview_at": preview.get("generated_at"),
            "summary": summary,
        }

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        return "".join(str(value).strip().lower().split())

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
        host = (parsed.netloc or parsed.path).lower()
        path = parsed.path if parsed.netloc else ""
        path = path.rstrip("/")
        normalized = f"{host}{path}".rstrip("/")
        return normalized

    @classmethod
    def _extract_domain(cls, url: Any) -> str:
        if not url:
            return ""
        raw = str(url).strip()
        if not raw.startswith(("http://", "https://")):
            raw = f"https://{raw}"
        parsed = urlparse(raw)
        return (parsed.netloc or parsed.path).lower().split(":")[0]

    def _build_standard_indexes(self) -> Dict[str, Dict[str, Any]]:
        # 合并接口数据与内置补丁（_HIDDEN_SITES 优先级低于接口，接口有则以接口为准）
        raw_sites = {**self._HIDDEN_SITES, **(self.sites.get_indexsites() or {})}
        url_index: Dict[str, Dict[str, Any]] = {}
        name_index: Dict[str, List[Dict[str, Any]]] = {}
        domain_index: Dict[str, List[Dict[str, Any]]] = {}

        for domain, site in raw_sites.items():
            standard_site = {
                "domain": domain,
                "id": site.get("id"),
                "name": site.get("name") or domain,
                "url": site.get("url") or f"https://{domain}",
                "public": site.get("public"),
            }
            normalized_url = self._normalize_url(standard_site["url"])
            normalized_name = self._normalize_text(standard_site["name"])
            url_index[normalized_url] = standard_site
            name_index.setdefault(normalized_name, []).append(standard_site)
            domain_index.setdefault(domain.lower(), []).append(standard_site)

        return {
            "url_index": url_index,
            "name_index": name_index,
            "domain_index": domain_index,
            "raw": raw_sites,
        }

    def _build_existing_domain_set(self) -> set:
        domains = set()
        for site in self.siteoper.list() or []:
            if getattr(site, "domain", None):
                domains.add(str(site.domain).lower())
        return domains

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}***{value[-4:]}"

    @staticmethod
    def _build_cookie_header(cookie_items: List[dict]) -> str:
        pairs = []
        seen = set()
        for item in cookie_items or []:
            name = str(item.get("name") or "").strip()
            if not name or name in seen:
                continue
            value = unquote(str(item.get("value") or "").strip())
            pairs.append(f"{name}={value}")
            seen.add(name)
        return "; ".join(pairs)

    def _convert_ptd_cookie_to_mp_cookie(self, cookies_payload: Dict[str, List[dict]], source_domain: str, target_domain: str) -> str:
        if not cookies_payload:
            return ""

        matched_items: List[dict] = []
        candidate_domains = [target_domain, source_domain]

        for candidate in candidate_domains:
            candidate = (candidate or "").lower()
            if not candidate:
                continue

            exact = cookies_payload.get(candidate)
            if exact:
                matched_items.extend(exact)

            for cookie_domain, items in cookies_payload.items():
                cookie_domain = str(cookie_domain).lower().lstrip(".")
                if cookie_domain == candidate or candidate.endswith(cookie_domain) or cookie_domain.endswith(candidate):
                    matched_items.extend(items or [])

            if matched_items:
                break

        return self._build_cookie_header(matched_items)

    def _load_backup_bundle(self, file_name: str, content: bytes) -> Tuple[dict, Dict[str, List[dict]]]:
        if not (file_name or "").lower().endswith(".zip"):
            raise ValueError("仅支持上传 PTD 备份压缩包（.zip 格式）")
        with zipfile.ZipFile(__import__("io").BytesIO(content), "r") as zip_file:
            metadata = {}
            cookies = {}
            for member in zip_file.namelist():
                member_name = member.replace("\\", "/").lower()
                if member_name.endswith("metadata.json"):
                    metadata = json.loads(zip_file.read(member).decode("utf-8-sig"))
                elif member_name.endswith("cookies.json"):
                    cookies = json.loads(zip_file.read(member).decode("utf-8-sig"))
            if not metadata:
                raise ValueError("压缩包内缺少 metadata.json")
            return metadata, cookies

    def _parse_metadata(self, payload: dict, cookies_payload: Optional[Dict[str, List[dict]]] = None) -> List[Dict[str, Any]]:
        site_name_map = payload.get("siteNameMap") or {}
        site_host_map = payload.get("siteHostMap") or {}
        sites = payload.get("sites") or {}
        last_user_info = payload.get("lastUserInfo") or {}
        parsed_sites: List[Dict[str, Any]] = []

        for site_key, site_data in sites.items():
            url = site_data.get("url") or ""
            domain = self._extract_domain(url)
            if not domain:
                for host, mapped_site_key in site_host_map.items():
                    if mapped_site_key == site_key:
                        domain = host.lower()
                        break

            input_setting = (site_data.get("inputSetting") or {}) if isinstance(site_data, dict) else {}
            cookie_from_metadata = (site_data.get("cookie") or "") if isinstance(site_data, dict) else ""
            cookie_from_ptd_jar = self._convert_ptd_cookie_to_mp_cookie(
                cookies_payload or {},
                source_domain=domain,
                target_domain=domain,
            )
            final_cookie = cookie_from_metadata or cookie_from_ptd_jar

            # PTD 中 timeout 均为毫秒（如 30000ms = 30s），MP 需要秒，≥1000 则换算，并钳制在 5~60s
            raw_timeout = int(site_data.get("timeout") or 30000)
            ptd_timeout_sec = (raw_timeout // 1000) if raw_timeout >= 1000 else raw_timeout
            ptd_timeout_sec = max(5, min(ptd_timeout_sec, 60))

            parsed_sites.append({
                "site_key": site_key,
                "name": site_name_map.get(site_key) or site_key,
                "url": url,
                "domain": domain,
                "cookie": final_cookie,
                "cookie_masked": self._mask_secret(final_cookie),
                "cookie_source": "metadata" if cookie_from_metadata else ("cookies.json" if cookie_from_ptd_jar else "none"),
                "cookie_convertible": bool(cookie_from_metadata or cookie_from_ptd_jar),
                "apikey": (input_setting.get("apikey") or ""),
                "token": (input_setting.get("token") or ""),
                "rss": site_data.get("rss") or "",
                "ua": site_data.get("ua") or "",
                "proxy": 1 if site_data.get("proxy") else 0,
                "render": 1 if site_data.get("render") else 0,
                "public": 1 if site_data.get("public") else 0,
                "timeout": ptd_timeout_sec,
                "limit_interval": site_data.get("limit_interval") or 0,
                "limit_count": site_data.get("limit_count") or 0,
                "limit_seconds": site_data.get("limit_seconds") or 0,
                "is_active": bool(last_user_info.get(site_key)) if self._only_active else True,
                "user_info_status": (last_user_info.get(site_key) or {}).get("status"),
            })

        return parsed_sites

    @staticmethod
    def _strip_www(host: str) -> str:
        """去掉 host 开头的 www. 前缀"""
        return host[4:] if host.startswith("www.") else host

    def _match_site(self, source_site: Dict[str, Any], standard_indexes: Dict[str, Any], existing_domains: set) -> Dict[str, Any]:
        normalized_url = self._normalize_url(source_site.get("url"))
        normalized_name = self._normalize_text(source_site.get("name"))
        domain = (source_site.get("domain") or "").lower()

        # 额外生成去掉 www. 前缀的变体，用于回退匹配
        normalized_url_nowww = self._strip_www(normalized_url) if normalized_url else ""
        domain_nowww = self._strip_www(domain) if domain else ""

        matched_standard = None
        match_type = "unmatched"
        need_confirm = False

        if normalized_url and standard_indexes["url_index"].get(normalized_url):
            # 严格 URL 匹配（含 www）
            matched_standard = standard_indexes["url_index"][normalized_url]
            match_type = "url"
        elif normalized_url_nowww and normalized_url_nowww != normalized_url and standard_indexes["url_index"].get(normalized_url_nowww):
            # URL 去掉 www. 后匹配
            matched_standard = standard_indexes["url_index"][normalized_url_nowww]
            match_type = "url"
        elif normalized_name and standard_indexes["name_index"].get(normalized_name):
            candidates = standard_indexes["name_index"][normalized_name]
            if len(candidates) == 1:
                matched_standard = candidates[0]
                match_type = "name"
                need_confirm = True
        elif domain and standard_indexes["domain_index"].get(domain):
            # 严格域名匹配（含 www）
            candidates = standard_indexes["domain_index"][domain]
            if len(candidates) == 1:
                matched_standard = candidates[0]
                match_type = "domain"
                need_confirm = True
        elif domain_nowww and domain_nowww != domain and standard_indexes["domain_index"].get(domain_nowww):
            # 域名去掉 www. 后匹配
            candidates = standard_indexes["domain_index"][domain_nowww]
            if len(candidates) == 1:
                matched_standard = candidates[0]
                match_type = "domain"
                need_confirm = True

        if not matched_standard:
            return {
                "source": source_site,
                "status": "unmatched",
                "match_type": match_type,
                "need_confirm": False,
                "message": "未匹配到 MoviePilot 标准站点",
                "standard": None,
                "already_exists": False,
            }

        target_domain = (matched_standard.get("domain") or self._extract_domain(matched_standard.get("url"))).lower()
        # 标准站点 URL 的实际域名（去掉 www.），用于 JSON key 与 URL 域名不一致时的兜底判断
        url_domain = self._strip_www(self._extract_domain(matched_standard.get("url") or "").lower())
        already_exists = target_domain in existing_domains or bool(url_domain and url_domain in existing_domains)
        status = "matched"
        message = "已匹配，可导入"

        if already_exists:
            status = "exists"
            message = "MP中已添加的站点"
        elif need_confirm:
            status = "need_confirm"
            message = "确认无误可直接导入"

        return {
            "source": source_site,
            "status": status,
            "match_type": match_type,
            "need_confirm": need_confirm,
            "message": message,
            "standard": matched_standard,
            "already_exists": already_exists,
            "credential": {
                "cookie_source": source_site.get("cookie_source"),
                "cookie_convertible": source_site.get("cookie_convertible"),
                "cookie_masked": source_site.get("cookie_masked"),
            }
        }

    async def _analyze_backup(self, file: UploadFile = File(...)) -> Dict[str, Any]:
        logger.info(f"{self.plugin_name}: 收到文件上传请求，文件名: {file.filename if file else 'None'}")
        
        if not file:
            logger.info(f"{self.plugin_name}: file 参数为 None")
            return {"success": False, "message": "未检测到上传文件"}
        
        if not file.filename:
            logger.info(f"{self.plugin_name}: 文件没有有效的文件名")
            return {"success": False, "message": "未检测到上传文件名"}

        try:
            content = await file.read()
            logger.info(f"{self.plugin_name}: 文件大小: {len(content)} bytes")
            payload, cookies_payload = self._load_backup_bundle(file.filename, content)
        except Exception as err:
            logger.error(f"{self.plugin_name}: 解析上传文件失败 - {err}")
            return {"success": False, "message": f"文件解析失败: {err}"}

        try:
            parsed_sites = self._parse_metadata(payload, cookies_payload)
            if self._only_active:
                parsed_sites = [site for site in parsed_sites if site.get("is_active")]

            standard_indexes = self._build_standard_indexes()
            existing_domains = self._build_existing_domain_set()
            results = [self._match_site(site, standard_indexes, existing_domains) for site in parsed_sites]

            if self._only_supported:
                results = [item for item in results if item["status"] != "unmatched"]

            summary = {
                "total": len(results),
                "matched": len([item for item in results if item["status"] == "matched"]),
                "need_confirm": len([item for item in results if item["status"] == "need_confirm"]),
                "exists": len([item for item in results if item["status"] == "exists"]),
                "unmatched": len([item for item in results if item["status"] == "unmatched"]),
            }
            self._last_preview = {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_name": file.filename,
                "summary": summary,
                "items": results,
                "import_mode": self._import_mode,
            }
            return {"success": True, "message": "解析成功", "data": self._last_preview}
        except Exception as err:
            logger.error(f"{self.plugin_name}: 生成预览失败 - {err}")
            logger.debug(traceback.format_exc())
            return {"success": False, "message": f"生成预览失败: {err}"}

    def get_preview(self) -> Dict[str, Any]:
        data = dict(self._last_preview or {})
        if data:
            data["import_mode"] = self._import_mode
        return {"success": True, "data": data}

    def import_sites(self, payload: Optional[dict] = None) -> Dict[str, Any]:
        payload = payload or {}
        preview = self._last_preview or {}
        items = preview.get("items") or []
        selected_keys = set(payload.get("site_keys") or [])
        importable_status = {"matched", "need_confirm", "exists"}
        results = []

        # 预先获取系统中已存在的站点映射：domain -> site_id
        existing_sites_map = {}
        for site in self.siteoper.list() or []:
            if getattr(site, "domain", None) and getattr(site, "id", None):
                existing_sites_map[str(site.domain).lower()] = site.id

        for item in items:
            source = item.get("source") or {}
            site_key = source.get("site_key")
            if selected_keys and site_key not in selected_keys:
                continue
            if item.get("status") not in importable_status:
                continue

            already_exists = item.get("already_exists")

            # skip 模式：记录跳过结果而不是静默跳过
            if already_exists and self._import_mode == "skip":
                standard_s = item.get("standard") or {}
                domain_s = (standard_s.get("domain") or self._extract_domain(standard_s.get("url") or "")).lower()
                results.append({
                    "site_key": site_key,
                    "domain": domain_s or site_key,
                    "success": True,
                    "skipped": True,
                    "message": "站点已存在，已跳过（当前模式：跳过）",
                })
                continue

            standard = item.get("standard") or {}
            domain = (standard.get("domain") or self._extract_domain(standard.get("url"))).lower()
            if not domain:
                results.append({"site_key": site_key, "success": False, "message": "目标域名为空"})
                continue

            url_domain = self._strip_www(self._extract_domain(standard.get("url") or "").lower())
            exist_site_id = existing_sites_map.get(domain) or existing_sites_map.get(url_domain)

            # public: 数据库为 bigint，必须转换为 int，避免 psycopg2 类型不匹配
            public_val = standard.get("public") if standard.get("public") is not None else source.get("public", 0)
            safe_public = int(bool(public_val))

            data = {
                "name": standard.get("name") or source.get("name") or site_key,
                "domain": domain,
                "url": standard.get("url") or source.get("url") or f"https://{domain}",
                "rss": source.get("rss") or "",
                "cookie": source.get("cookie") if self._import_cookie else "",
                # ua: 备份有值用备份值，备份为空时用配置中指定的默认 UA
                "ua": source.get("ua") or self._default_ua or "",
                "apikey": source.get("apikey") if self._import_apikey else "",
                "token": source.get("token") if self._import_token else "",
                # proxy/render: PTD 备份中均为 0，若配置了默认值则以配置为准
                "proxy": int(bool(source.get("proxy"))) or int(self._default_proxy),
                "render": int(bool(source.get("render"))) or int(self._default_render),
                "public": safe_public,
                "limit_interval": source.get("limit_interval") or 0,
                "limit_count": source.get("limit_count") or 0,
                "limit_seconds": source.get("limit_seconds") or 0,
                "timeout": source.get("timeout") or 30,
                "is_active": True,
                "pri": int(source.get("sortIndex") or 100),
                "note": {
                    "import_source": "ptdimporter",
                    "ptd_site_key": site_key,
                    "match_type": item.get("match_type"),
                }
            }

            try:
                if already_exists and exist_site_id:
                    if self._import_mode == "update_auth":
                        update_data = {}
                        if data["cookie"]: update_data["cookie"] = data["cookie"]
                        if data["apikey"]: update_data["apikey"] = data["apikey"]
                        if data["token"]:  update_data["token"] = data["token"]
                        if data["ua"]:     update_data["ua"] = data["ua"]
                        if update_data:
                            self.siteoper.update(exist_site_id, update_data)
                            success, message, msg_prefix = True, "", "凭据已更新"
                        else:
                            success, message, msg_prefix = True, "", "未检测到新凭据，无需更新"
                    else:  # update_all
                        self.siteoper.update(exist_site_id, data)
                        success, message, msg_prefix = True, "", "配置已全面覆盖"

                    results.append({
                        "site_key": site_key,
                        "domain": domain,
                        "success": success,
                        "message": f"{msg_prefix} {message}".strip(),
                    })
                else:
                    success, message = self.siteoper.add(**data)
                    results.append({
                        "site_key": site_key,
                        "domain": domain,
                        "success": success,
                        "message": message,
                    })
            except Exception as err:
                results.append({
                    "site_key": site_key,
                    "domain": domain,
                    "success": False,
                    "message": str(err),
                })

        skipped = [r for r in results if r.get("skipped")]
        succeeded = [r for r in results if r.get("success") and not r.get("skipped")]
        failed = [r for r in results if not r.get("success")]
        return {
            "success": True,
            "message": f"导入完成：成功 {len(succeeded)}，跳过 {len(skipped)}，失败 {len(failed)}",
            "data": {
                "total": len(results),
                "success": len(succeeded),
                "skipped": len(skipped),
                "failed": len(failed),
                "items": results,
            }
        }

    def stop_service(self):
        pass
