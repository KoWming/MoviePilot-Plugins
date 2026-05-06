from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from fastapi import File, UploadFile
from app.core.config import settings
from app.plugins import _PluginBase


class Zpic(_PluginBase):
    # 插件名称
    plugin_name = "Vue-Zpic图床"
    # 插件描述
    plugin_desc = "上传、阅览、管理Zpic图床。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/Photoview_A.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "zpic_"
    # 加载顺序
    plugin_order = 35
    # 可使用的用户级别
    auth_level = 1

    _enabled: bool = False                        # 是否启用插件
    _base_url: str = "https://www.imgurl.org"     # Zpic 站点地址
    _email: str = ""                              # 登录邮箱
    _token: str = ""                              # 登录令牌
    _uid: str = ""                                # 用户 ID
    _role: str = ""                               # 用户角色
    _tier: str = ""                               # 订阅套餐等级
    _user_info: Dict[str, Any] = {}               # 用户信息
    _subscription: Dict[str, Any] = {}            # 订阅信息
    _open_token: str = ""                         # 开放接口令牌

    def init_plugin(self, config: dict = None):
        """
        初始化插件配置。
        """
        config = config or {}
        self._enabled = bool(config.get("enabled", False))
        self._base_url = self._normalize_base_url(
            config.get("base_url") or "https://www.imgurl.org"
        )
        self._email = (config.get("email") or "").strip()
        self._token = (config.get("token") or "").strip()
        self._uid = (config.get("uid") or "").strip()
        self._role = (config.get("role") or "").strip()
        self._tier = (config.get("tier") or "").strip()
        self._user_info = config.get("user_info") or {}
        self._subscription = config.get("subscription") or {}
        self._open_token = (config.get("open_token") or "").strip()

    def get_state(self) -> bool:
        """
        获取插件启用状态。
        """
        return bool(self._enabled)

    @staticmethod
    def _append_security_image_domain(url: str) -> None:
        """
        添加安全图片域名。
        """
        if not url or not str(url).startswith(("http://", "https://")):
            return
        parsed_url = urlparse(str(url))
        image_domain = f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url.scheme and parsed_url.netloc else None
        if image_domain and image_domain not in settings.SECURITY_IMAGE_DOMAINS:
            settings.SECURITY_IMAGE_DOMAINS.append(image_domain)

    @staticmethod
    def _iter_storage_domain_urls(data: Any) -> List[str]:
        """
        递归提取存储域名地址。
        """
        urls: List[str] = []
        if isinstance(data, str):
            urls.append(data)
        elif isinstance(data, list):
            for item in data:
                urls.extend(Zpic._iter_storage_domain_urls(item))
        elif isinstance(data, dict):
            for key in ("domains", "storage_domains", "domain", "url", "host", "value"):
                urls.extend(Zpic._iter_storage_domain_urls(data.get(key)))
            for value in data.values():
                if isinstance(value, (dict, list)):
                    urls.extend(Zpic._iter_storage_domain_urls(value))
        return urls

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        返回插件命令列表。
        """
        return []

    def get_render_mode(self) -> Tuple[str, Optional[str]]:
        """
        返回 Vue 渲染模式。
        """
        return "vue", "dist/assets"

    def get_sidebar_nav(self) -> List[Dict[str, Any]]:
        """
        返回侧边栏导航配置。
        """
        return [
            {
                "nav_key": "main",
                "title": "Zpic图床",
                "icon": "mdi-cloud-upload-outline",
                "section": "discovery",
                "order": 10,
            },
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        """
        返回插件 API 路由。
        """
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
                "path": "/status",
                "endpoint": self._get_status,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取远程账号状态",
            },
            {
                "path": "/captcha",
                "endpoint": self._get_captcha,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取登录验证码",
            },
            {
                "path": "/login",
                "endpoint": self._login,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "登录 Zpic",
            },
            {
                "path": "/logout",
                "endpoint": self._logout,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "退出登录",
            },
            {
                "path": "/albums",
                "endpoint": self._get_albums,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取相册列表",
            },
            {
                "path": "/images",
                "endpoint": self._get_images,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "获取图片列表",
            },
            {
                "path": "/albums/create",
                "endpoint": self._create_album,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "创建相册",
            },
            {
                "path": "/albums/update",
                "endpoint": self._update_album,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "更新相册",
            },
            {
                "path": "/albums/delete",
                "endpoint": self._delete_album,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "删除相册",
            },
            {
                "path": "/system/config",
                "endpoint": self._get_system_config,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取系统配置",
            },
            {
                "path": "/system/domains",
                "endpoint": self._get_storage_domains,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取存储域名列表",
            },
            {
                "path": "/system/config",
                "endpoint": self._update_system_config,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "更新系统配置",
            },
            {
                "path": "/upload",
                "endpoint": self._upload_image,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "上传图片",
            },
            {
                "path": "/images/delete",
                "endpoint": self._delete_images,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "批量删除图片",
            },
        ]

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """
        返回插件配置表单。
        """
        return None, self._get_config()

    def get_page(self) -> List[dict]:
        """
        返回插件详情页面配置。
        """
        return []

    def stop_service(self):
        """
        停止插件服务。
        """
        pass

    @staticmethod
    def _normalize_base_url(url: str) -> str:
        """
        规范化 Zpic 站点地址。
        """
        raw = (url or "https://www.imgurl.org").strip()
        if not raw:
            raw = "https://www.imgurl.org"
        if not raw.startswith(("http://", "https://")):
            raw = f"https://{raw}"
        return raw.rstrip("/")

    def _persist_config(self):
        """
        持久化插件配置。
        """
        self.update_config(
            {
                "enabled": self._enabled,
                "base_url": self._base_url,
                "email": self._email,
                "token": self._token,
                "open_token": self._open_token,
                "uid": self._uid,
                "role": self._role,
                "tier": self._tier,
                "user_info": self._user_info,
                "subscription": self._subscription,
            }
        )

    def _clear_auth_state(self):
        """
        清理认证状态并持久化。
        """
        self._token = ""
        self._uid = ""
        self._role = ""
        self._tier = ""
        self._user_info = {}
        self._subscription = {}
        self._persist_config()

    def _headers(self, auth: bool = False) -> Dict[str, str]:
        """
        构建请求头信息。
        """
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": self._base_url,
            "Referer": f"{self._base_url}/account/albums",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
        }
        if auth:
            if not self._token:
                raise ValueError("请先登录 Zpic")
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = False,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        请求 Zpic 远程接口。
        """
        url = f"{self._base_url}{path}"
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=self._headers(auth=auth),
                json=payload,
                params=params,
                timeout=20,
            )
        except requests.RequestException as err:
            raise ValueError(f"请求远程接口失败: {err}") from err

        try:
            data = response.json()
        except ValueError as err:
            raise ValueError("远程接口返回的不是有效 JSON") from err

        if response.status_code == 401 or data.get("code") == 401:
            if auth:
                self._clear_auth_state()
            raise ValueError(data.get("msg") or "登录态失效，请重新登录")

        if response.status_code >= 400:
            raise ValueError(data.get("msg") or f"远程接口请求失败: HTTP {response.status_code}")

        if data.get("code") not in (None, 200):
            raise ValueError(data.get("msg") or "远程接口返回失败")

        return data

    def _sync_storage_security_image_domains(self) -> None:
        """
        同步存储安全图片域名。
        """
        result = self._request("GET", "/api/user/storage_domains", auth=True)
        data = result.get("data") or {}
        for domain_url in self._iter_storage_domain_urls(data):
            self._append_security_image_domain(domain_url)

    def _refresh_remote_state(self) -> Dict[str, Any]:
        """
        刷新远程账号状态。
        """
        if not self._token:
            self._user_info = {}
            self._subscription = {}
            self._uid = ""
            self._role = ""
            self._tier = ""
            return self._build_status()

        info_data = self._request("GET", "/api/user/info", auth=True).get("data") or {}
        sub_data = self._request("GET", "/api/user/subscription", auth=True).get("data") or {}
        self._user_info = info_data
        self._subscription = sub_data
        self._uid = info_data.get("uid") or self._uid
        self._role = info_data.get("role") or self._role
        self._tier = info_data.get("tier") or sub_data.get("tier") or self._tier
        self._email = info_data.get("email") or self._email
        self._persist_config()
        return self._build_status()

    def _build_status(self, error: str = "") -> Dict[str, Any]:
        """
        构建账号状态数据。
        """
        return {
            "enabled": self._enabled,
            "base_url": self._base_url,
            "email": self._email,
            "logged_in": bool(self._token),
            "token": self._token,
            "uid": self._uid,
            "role": self._role,
            "tier": self._tier,
            "user": self._user_info,
            "subscription": self._subscription,
            "error": error,
        }

    def _get_config(self) -> Dict[str, Any]:
        """
        获取插件配置。
        """
        return {
            "enabled": self._enabled,
            "base_url": self._base_url,
            "email": self._email,
            "token": self._token,
            "open_token": self._open_token,
            "uid": self._uid,
            "role": self._role,
            "tier": self._tier,
        }

    def _save_config(self, config_payload: dict) -> Dict[str, Any]:
        """
        保存插件配置。
        """
        self._enabled = bool(config_payload.get("enabled", self._enabled))
        self._base_url = self._normalize_base_url(
            config_payload.get("base_url") or self._base_url
        )
        self._email = (config_payload.get("email") or self._email or "").strip()
        self._open_token = (config_payload.get("open_token") or self._open_token or "").strip()
        token = (config_payload.get("token") or "").strip()
        if token:
            self._token = token
        self._persist_config()
        return {
            "success": True,
            "message": "配置保存成功",
            "data": self._get_config(),
        }

    def _get_status(self) -> Dict[str, Any]:
        """
        获取远程账号状态。
        """
        try:
            status = self._refresh_remote_state() if self._token else self._build_status()
            return {"success": True, "data": status}
        except Exception as err:
            return {"success": False, "message": str(err), "data": self._build_status(str(err))}

    def _get_captcha(self) -> Dict[str, Any]:
        """
        获取登录验证码。
        """
        try:
            result = self._request("GET", "/api/captcha", auth=False)
            return {
                "success": True,
                "message": result.get("msg") or "success",
                "data": result.get("data") or {},
            }
        except Exception as err:
            return {"success": False, "message": str(err)}

    def _login(self, payload: dict) -> Dict[str, Any]:
        """
        登录 Zpic 账号。
        """
        email = (payload.get("email") or "").strip()
        password = payload.get("password") or ""
        captcha_key = (payload.get("captcha_key") or "").strip()
        captcha_value = (payload.get("captcha_value") or "").strip()

        if not email or not password:
            return {"success": False, "message": "邮箱和密码不能为空"}
        if not captcha_key or not captcha_value:
            return {"success": False, "message": "请先获取并填写验证码"}

        try:
            result = self._request(
                "POST",
                "/api/email_login",
                auth=False,
                payload={
                    "email": email,
                    "password": password,
                    "captcha_key": captcha_key,
                    "captcha_value": captcha_value,
                },
            )
            data = result.get("data") or {}
            self._token = (data.get("token") or "").strip()
            self._email = email
            self._uid = data.get("uid") or ""
            self._role = data.get("role") or ""
            self._enabled = True
            status = self._refresh_remote_state()
            self._sync_storage_security_image_domains()
            return {
                "success": True,
                "message": "登录成功",
                "data": {
                    "token": self._token,
                    "status": status,
                },
            }
        except Exception as err:
            return {"success": False, "message": str(err)}

    def _logout(self) -> Dict[str, Any]:
        """
        退出 Zpic 登录。
        """
        self._clear_auth_state()
        return {"success": True, "message": "已退出登录"}

    def _get_albums(self) -> Dict[str, Any]:
        """
        获取相册列表。
        """
        try:
            result = self._request("GET", "/api/user/album_list", auth=True)
            items = ((result.get("data") or {}).get("items")) or []
            return {"success": True, "data": items}
        except Exception as err:
            return {"success": False, "message": str(err), "data": []}

    def _get_images(self, payload: dict = None) -> Dict[str, Any]:
        """
        获取图片列表。
        """
        payload = payload or {}
        try:
            page = max(int(payload.get("page") or 1), 1)
            limit = min(max(int(payload.get("limit") or 12), 1), 100)
            album_id = int(payload.get("album_id") or 0)
            keyword = (payload.get("keyword") or "").strip()

            # 插件侧统一做本地搜索：filename/imgid/hash/ext 都可匹配，然后再分页。
            if keyword:
                all_items: List[Dict[str, Any]] = []
                fetch_page = 1
                fetch_limit = 100
                while True:
                    result = self._request(
                        "POST",
                        "/api/user/image_list",
                        auth=True,
                        payload={
                            "page": fetch_page,
                            "limit": fetch_limit,
                            "album_id": album_id,
                            "keyword": "",
                        },
                    )
                    data = result.get("data") or {}
                    items = data.get("items") or []
                    all_items.extend(items)
                    total = int(data.get("total") or len(all_items))
                    if len(all_items) >= total or not items:
                        break
                    fetch_page += 1

                keyword_lower = keyword.lower()
                matched_items = [
                    item for item in all_items
                    if keyword_lower in str(item.get("filename") or "").lower()
                    or keyword_lower in str(item.get("imgid") or "").lower()
                    or keyword_lower in str(item.get("hash") or "").lower()
                    or keyword_lower in str(item.get("ext") or "").lower()
                ]
                start = (page - 1) * limit
                return {
                    "success": True,
                    "data": {
                        "total": len(matched_items),
                        "page": page,
                        "limit": limit,
                        "items": matched_items[start:start + limit],
                    },
                }

            result = self._request(
                "POST",
                "/api/user/image_list",
                auth=True,
                payload={
                    "page": page,
                    "limit": limit,
                    "album_id": album_id,
                    "keyword": "",
                },
            )
            return {
                "success": True,
                "data": result.get("data") or {
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "items": [],
                },
            }
        except Exception as err:
            return {
                "success": False,
                "message": str(err),
                "data": {"total": 0, "page": 1, "limit": 12, "items": []},
            }

    def _create_album(self, payload: dict) -> Dict[str, Any]:
        """
        创建相册。
        """
        try:
            name = (payload.get("name") or "").strip()
            description = (payload.get("description") or "").strip()
            if not name:
                return {"success": False, "message": "相册名称不能为空"}
            result = self._request(
                "POST",
                "/api/user/create_album",
                auth=True,
                payload={"name": name, "description": description},
            )
            return {"success": True, "message": "创建成功", "data": result.get("data")}
        except Exception as err:
            return {"success": False, "message": str(err)}

    def _update_album(self, payload: dict) -> Dict[str, Any]:
        """
        更新相册信息。
        """
        try:
            album_id = int(payload.get("album_id") or 0)
            name = (payload.get("name") or "").strip()
            description = (payload.get("description") or "").strip()
            if not album_id:
                return {"success": False, "message": "album_id 不能为空"}
            if not name:
                return {"success": False, "message": "相册名称不能为空"}
            result = self._request(
                "POST",
                "/api/user/update_album",
                auth=True,
                payload={
                    "album_id": album_id,
                    "name": name,
                    "description": description,
                },
            )
            return {"success": True, "message": "更新成功", "data": result.get("data")}
        except Exception as err:
            return {"success": False, "message": str(err)}

    def _delete_album(self, payload: dict) -> Dict[str, Any]:
        """
        删除相册。
        """
        try:
            album_id = int(payload.get("album_id") or 0)
            if not album_id:
                return {"success": False, "message": "album_id 不能为空"}
            result = self._request(
                "POST",
                "/api/user/delete_album",
                auth=True,
                payload={"album_id": album_id},
            )
            return {"success": True, "message": "删除成功", "data": result.get("data")}
        except Exception as err:
            return {"success": False, "message": str(err)}

    def _get_system_config(self) -> Dict[str, Any]:
        """
        获取 Zpic 系统配置。
        """
        try:
            result = self._request("GET", "/api/user/get_own_config", auth=True)
            data = result.get("data") or {}
            data["tier"] = self._tier or (self._subscription or {}).get("tier") or "free"
            return {"success": True, "data": data}
        except Exception as err:
            return {"success": False, "message": str(err), "data": {}}

    def _get_storage_domains(self) -> Dict[str, Any]:
        """
        获取存储域名列表。
        """
        try:
            result = self._request("GET", "/api/user/storage_domains", auth=True)
            data = result.get("data") or {}
            return {"success": True, "data": data}
        except Exception as err:
            return {"success": False, "message": str(err), "data": {}}

    def _update_system_config(self, payload: dict) -> Dict[str, Any]:
        """
        更新 Zpic 系统配置。
        """
        try:
            action = payload.get("action") or "update_own_config"
            compress = payload.get("compress")
            storage_slug = payload.get("storage_slug")
            storage_domain = payload.get("storage_domain")
            watermark_enabled = payload.get("watermark_enabled")
            watermark_text = payload.get("watermark_text")

            update_payload = {"action": action}
            if compress is not None:
                update_payload["compress"] = compress
            if watermark_enabled is not None:
                update_payload["watermark_enabled"] = watermark_enabled
            if watermark_text is not None:
                update_payload["watermark_text"] = watermark_text
            if storage_slug is not None:
                update_payload["storage_slug"] = storage_slug
            if storage_domain is not None:
                update_payload["storage_domain"] = storage_domain

            result = self._request(
                "POST",
                "/api/user/update_own_config",
                auth=True,
                payload=update_payload,
            )
            return {
                "success": True,
                "message": "系统配置已更新",
                "data": result.get("data") or {},
            }
        except Exception as err:
            return {"success": False, "message": str(err)}

    async def _upload_image(self, file: UploadFile = File(...)) -> Dict[str, Any]:
        """
        上传图片到 Zpic。
        """
        if not self._open_token:
            return {"success": False, "message": "请先在设置中配置开放令牌（Open Token）"}

        if not file:
            return {"success": False, "message": "未选择文件"}

        # 读取上传文件内容
        try:
            content = await file.read()
        except Exception as err:
            return {"success": False, "message": f"读取上传文件失败: {err}"}

        if not content:
            return {"success": False, "message": "上传文件内容为空"}

        # 构建转发用的 multipart/form-data
        files = {"file": (file.filename or "image.jpg", content, file.content_type or "image/jpeg")}

        # 额外参数（从 query params 或 JSON body 中获取）
        # MoviePilot 对于非文件参数，可能需要通过其他方式传递
        # 暂时不传 params，后续可通过 JSON body 扩展
        data = {}

        # 直接用 requests 发送 multipart/form-data 到 Zpic API V3
        url = f"{self._base_url}/api/v3/upload"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._open_token}",
        }

        try:
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            result = resp.json()
        except requests.RequestException as err:
            return {"success": False, "message": f"上传请求失败: {err}"}
        except ValueError as err:
            return {"success": False, "message": f"解析响应失败: {err}"}

        if result.get("code") != 200:
            return {"success": False, "message": result.get("msg", "上传失败"), "data": result}

        return {"success": True, "message": "上传成功", "data": result.get("data")}

    def _delete_images(self, payload: dict) -> Dict[str, Any]:
        """
        批量删除图片。
        """
        if not self._token:
            return {"success": False, "message": "请先登录 Zpic"}

        image_ids = payload.get("image_ids") or []
        if not image_ids:
            return {"success": False, "message": "请选择要删除的图片"}

        if not isinstance(image_ids, list):
            image_ids = [image_ids]

        try:
            total_deleted = 0
            last_data = None
            for index in range(0, len(image_ids), 10):
                batch_ids = image_ids[index:index + 10]
                result = self._request(
                    "POST",
                    "/api/user/delete_images",
                    auth=True,
                    payload={"image_ids": batch_ids},
                )
                last_data = result.get("data")
                total_deleted += ((last_data or {}).get("count")) or len(batch_ids)
            return {"success": True, "message": f"已删除 {total_deleted} 张图片", "data": last_data}
        except Exception as err:
            return {"success": False, "message": str(err)}
