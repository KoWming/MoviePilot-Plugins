from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os
import time
import uuid

from app import schemas
from app.core.event import Event, eventmanager
from app.helper.storage import StorageHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import FileItem, StorageOperSelectionEventData
from app.schemas.types import ChainEventType

from .guangya_api import GuangYaApi
from .guangya_client import GuangYaClient


class GuangYaDisk(_PluginBase):
    # 插件名称
    plugin_name = "Vue-光鸭云盘储存"
    # 插件描述
    plugin_desc = "使存储支持光鸭云盘。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/GuangyaDisk.png"
    # 插件版本
    plugin_version = "1.0.2"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项 ID 前缀
    plugin_config_prefix = "guangyadisk_"
    # 加载顺序
    plugin_order = 99
    # 可使用的用户级别
    auth_level = 1

    _enabled = False
    _disk_name = "光鸭云盘"
    _client: Optional[GuangYaClient] = None
    _guangya_api: Optional[GuangYaApi] = None

    _access_token: str = ""
    _refresh_token: str = ""
    _client_id: str = GuangYaClient.DEFAULT_CLIENT_ID
    _device_id: str = ""
    _device_code: str = ""
    _poll_interval: int = 5
    _page_size: int = 100
    _order_by: int = 3
    _sort_type: int = 1
    _permanently_delete: bool = False
    _user_code: str = ""
    _verification_uri: str = ""
    _qr_expires_at: float = 0

    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)

    @staticmethod
    def _mask_token(token: str, keep: int = 10) -> str:
        """
        脱敏显示 token。
        """
        if not token:
            return ""
        token = str(token)
        if len(token) <= keep * 2:
            return token
        return f"{token[:keep]}...{token[-keep:]}"

    def __init__(self):
        """
        初始化插件。
        """
        super().__init__()

    def _clear_auth_state(self, reason: str = ""):
        """
        清理认证状态并持久化。
        """
        if reason:
            logger.warning(f"【光鸭云盘】清理登录状态: {reason}")
        self._access_token = ""
        self._refresh_token = ""
        self._device_code = ""
        self._user_code = ""
        self._verification_uri = ""
        self._qr_expires_at = 0
        if self._client:
            self._client._access_token = ""
            self._client._refresh_token = ""
        self.update_config(
            {
                "enabled": self._enabled,
                "access_token": "",
                "refresh_token": "",
                "client_id": self._client_id,
                "device_id": self._device_id,
                "poll_interval": self._poll_interval,
                "page_size": self._page_size,
                "order_by": self._order_by,
                "sort_type": self._sort_type,
                "permanently_delete": self._permanently_delete,
            }
        )

    def init_plugin(self, config: dict = None):
        """
        初始化插件。
        """
        if not config:
            return

        storage_helper = StorageHelper()
        storages = storage_helper.get_storagies()
        if not any(
            s.type == self._disk_name and s.name == self._disk_name for s in storages
        ):
            storage_helper.add_storage(
                storage=self._disk_name,
                name=self._disk_name,
                conf={},
            )

        self._enabled = bool(config.get("enabled"))
        self._access_token = (config.get("access_token") or "").strip()
        self._refresh_token = (config.get("refresh_token") or "").strip()
        self._client_id = (
            (config.get("client_id") or GuangYaClient.DEFAULT_CLIENT_ID).strip()
            or GuangYaClient.DEFAULT_CLIENT_ID
        )
        self._device_id = (config.get("device_id") or "").strip()
        self._page_size = int(config.get("page_size") or 100)
        self._order_by = int(config.get("order_by") or 3)
        self._sort_type = int(config.get("sort_type") or 1)
        self._poll_interval = int(config.get("poll_interval") or 5)
        self._permanently_delete = bool(config.get("permanently_delete"))

        logger.info(
            "【光鸭云盘】初始化插件: enabled=%s, device_id=%s, has_access_token=%s, has_refresh_token=%s",
            self._enabled,
            self._device_id,
            bool(self._access_token),
            bool(self._refresh_token),
        )

        def on_token_refresh(access_token: str, refresh_token: str):
            """
            token 刷新后自动持久化。
            """
            logger.info("【光鸭云盘】收到 Token 刷新回调，准备保存配置")
            self._access_token = access_token
            self._refresh_token = refresh_token
            config_payload = {
                "enabled": self._enabled,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "client_id": self._client_id,
                "device_id": self._device_id,
                "poll_interval": self._poll_interval,
                "page_size": self._page_size,
                "order_by": self._order_by,
                "sort_type": self._sort_type,
                "permanently_delete": self._permanently_delete,
            }
            self.update_config(config_payload)
            logger.info("【光鸭云盘】Token 已自动保存")

        try:
            self._client = GuangYaClient(
                access_token=self._access_token,
                refresh_token=self._refresh_token,
                client_id=self._client_id,
                device_id=self._device_id,
                on_token_refresh=on_token_refresh,
            )
            self._device_id = self._client.device_id
            self._guangya_api = GuangYaApi(
                client=self._client,
                disk_name=self._disk_name,
                page_size=self._page_size,
                order_by=self._order_by,
                sort_type=self._sort_type,
                permanently_delete=self._permanently_delete,
            )
        except Exception as err:
            logger.error(f"光鸭云盘客户端创建失败: {err}")
            self._client = None
            self._guangya_api = None

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_render_mode(self) -> Tuple[str, Optional[str]]:
        """
        返回 Vue 渲染模式。
        """
        return "vue", "dist/assets"

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件 API 端点。
        """
        return [
            {
                "path": "/config",
                "endpoint": self._get_config,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "获取配置",
            },
            {
                "path": "/config",
                "endpoint": self._save_config,
                "auth": "bear",
                "methods": ["POST"],
                "summary": "保存配置",
            },
            {
                "path": "/login/qrcode",
                "endpoint": self.get_qrcode,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "获取扫码登录二维码",
            },
            {
                "path": "/login/poll",
                "endpoint": self.poll_login,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "轮询扫码登录状态",
            },
            {
                "path": "/login/logout",
                "endpoint": self.logout,
                "auth": "bear",
                "methods": ["POST"],
                "summary": "退出登录",
            },
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        Vue 模式下返回空表单与初始配置。
        """
        return None, {
            "enabled": False,
            "access_token": "",
            "refresh_token": "",
            "client_id": GuangYaClient.DEFAULT_CLIENT_ID,
            "device_id": "",
            "poll_interval": 5,
            "page_size": 100,
            "order_by": 3,
            "sort_type": 1,
            "permanently_delete": False,
        }

    def get_page(self) -> List[dict]:
        """
        Vue 模式下返回空页面。
        """
        return []

    def _get_config(self) -> Dict[str, Any]:
        """
        获取当前配置。
        """
        def _pick_first(data: Dict[str, Any], *keys: str) -> Any:
            for key in keys:
                value = data.get(key)
                if value not in (None, ""):
                    return value
            return None

        def _to_int(value: Any) -> int:
            if value in (None, ""):
                return 0
            try:
                return int(value)
            except (TypeError, ValueError):
                try:
                    return int(float(value))
                except (TypeError, ValueError):
                    return 0

        def _is_auth_invalid(result: Dict[str, Any]) -> bool:
            if not isinstance(result, dict):
                return False
            error_text = str(result.get("error") or "")
            msg_text = str(result.get("msg") or "")
            detail_text = str(result)
            return any(
                keyword in f"{error_text} {msg_text} {detail_text}"
                for keyword in ["unauthenticated", "无效token", "Authorize failed", "认证失败"]
            )

        def _should_clear_auth(result: Dict[str, Any]) -> bool:
            if not _is_auth_invalid(result):
                return False
            if not self._client:
                return False
            return bool(self._client.last_refresh_attempted and self._client.last_refresh_invalid)

        config = {
            "enabled": self._enabled,
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "client_id": self._client_id or GuangYaClient.DEFAULT_CLIENT_ID,
            "device_id": self._device_id,
            "poll_interval": self._poll_interval,
            "page_size": self._page_size,
            "order_by": self._order_by,
            "sort_type": self._sort_type,
            "permanently_delete": self._permanently_delete,
            "logged_in": False,
            "user_code": self._user_code,
            "verification_uri": self._verification_uri,
            "qr_expires_in": max(int(self._qr_expires_at - time.time()), 0) if self._qr_expires_at else 0,
        }
        
        # 如果已登录，尝试获取用户信息和空间统计
        if self._access_token and self._client:
            try:
                # 获取用户信息
                user_info = self._client.get_user_info() or {}
                if _should_clear_auth(user_info):
                    self._clear_auth_state(
                        f"access_token/refresh_token 已失效，需要重新扫码登录: {self._client.last_refresh_result}"
                    )
                    config["access_token"] = ""
                    config["refresh_token"] = ""
                    config["device_id"] = self._device_id
                    config["user_name"] = ""
                    config["user_id"] = ""
                    config["vip_level"] = ""
                    config["member_expire_time"] = 0
                    config["total_space"] = 0
                    config["used_space"] = 0
                    config["free_space"] = 0
                    config["file_count"] = 0
                    return config
                if _is_auth_invalid(user_info):
                    logger.warning(f"【光鸭云盘】用户信息接口认证异常，但未确认 refresh_token 失效，暂不清空登录态: {user_info}")
                    config["user_name"] = ""
                    config["user_id"] = ""
                    config["vip_level"] = ""
                    config["member_expire_time"] = 0
                    config["total_space"] = 0
                    config["used_space"] = 0
                    config["free_space"] = 0
                    config["file_count"] = 0
                    return config

                user_data = user_info.get("data") if isinstance(user_info.get("data"), dict) else user_info
                user_name = _pick_first(
                    user_data,
                    "name",
                    "user_name",
                    "username",
                    "nickname",
                    "nickName",
                    "phone",
                    "mobile",
                    "display_name",
                    "preferred_username",
                )
                user_id = _pick_first(
                    user_data,
                    "user_id",
                    "userId",
                    "id",
                    "sub",
                    "uid",
                    "openId",
                )
                vip_level = _pick_first(
                    user_data,
                    "vip_level",
                    "vipLevel",
                    "vip",
                    "level",
                    "memberLevel",
                    "vipName",
                    "memberType",
                )

                if user_name is None and user_id is not None:
                    user_name = user_id

                if user_name is None and user_id is None:
                    logger.warning(f"【光鸭云盘】用户信息无有效身份字段，视为未登录: {user_info}")
                    config["user_name"] = ""
                    config["user_id"] = ""
                    config["vip_level"] = ""
                    config["member_expire_time"] = 0
                    config["total_space"] = 0
                    config["used_space"] = 0
                    config["free_space"] = 0
                    config["file_count"] = 0
                    return config

                config["user_name"] = "" if user_name is None else str(user_name)
                config["user_id"] = "" if user_id is None else str(user_id)
                config["vip_level"] = "" if vip_level is None else str(vip_level)
                config["member_expire_time"] = 0
                config["logged_in"] = True
                
                # 获取空间统计
                assets_info = self._client.get_assets() or {}
                if _should_clear_auth(assets_info):
                    self._clear_auth_state(
                        f"空间信息接口返回未认证，且 refresh_token 已失效，需要重新扫码登录: {self._client.last_refresh_result}"
                    )
                    config["logged_in"] = False
                    config["access_token"] = ""
                    config["refresh_token"] = ""
                    config["user_name"] = ""
                    config["user_id"] = ""
                    config["vip_level"] = ""
                    config["member_expire_time"] = 0
                    config["total_space"] = 0
                    config["used_space"] = 0
                    config["free_space"] = 0
                    config["file_count"] = 0
                    return config
                if _is_auth_invalid(assets_info):
                    logger.warning(f"【光鸭云盘】空间信息接口认证异常，但未确认 refresh_token 失效，暂不清空登录态: {assets_info}")
                    config["total_space"] = 0
                    config["used_space"] = 0
                    config["free_space"] = 0
                    config["file_count"] = 0
                    return config

                assets_data = assets_info.get("data") if isinstance(assets_info.get("data"), dict) else assets_info
                total_space = _to_int(
                    _pick_first(
                        assets_data,
                        "totalSpaceSize",
                        "total_space",
                        "totalSpace",
                        "total",
                    )
                )
                used_space_raw = _pick_first(
                    assets_data,
                    "usedSpaceSize",
                    "used_space",
                    "usedSpace",
                    "used",
                )
                used_space = _to_int(used_space_raw)
                free_space_raw = _pick_first(
                    assets_data,
                    "freeSpaceSize",
                    "free_space",
                    "freeSpace",
                    "free",
                    "available",
                )
                free_space = _to_int(free_space_raw)
                if free_space == 0 and total_space and used_space_raw not in (None, ""):
                    free_space = max(total_space - used_space, 0)

                config["total_space"] = total_space
                config["used_space"] = used_space
                config["free_space"] = free_space
                config["file_count"] = _to_int(
                    _pick_first(assets_data, "file_count", "fileCount", "totalFileCount")
                )
                config["member_expire_time"] = _to_int(
                    _pick_first(assets_data, "vipExpireTime", "vip_expire_time", "expireTime")
                )
            except Exception as err:
                logger.error(f"【光鸭云盘】获取用户信息失败: {err}")
                config["logged_in"] = False
                config["user_name"] = ""
                config["user_id"] = ""
                config["vip_level"] = ""
                config["member_expire_time"] = 0
                config["total_space"] = 0
                config["used_space"] = 0
                config["free_space"] = 0
                config["file_count"] = 0
        else:
            config["user_name"] = ""
            config["user_id"] = ""
            config["vip_level"] = ""
            config["member_expire_time"] = 0
            config["total_space"] = 0
            config["used_space"] = 0
            config["free_space"] = 0
            config["file_count"] = 0
        
        return config

    def _save_config(self, config_payload: dict) -> Dict[str, Any]:
        """
        保存插件配置。
        """
        try:
            config_payload = config_payload or {}
            new_config = {
                "enabled": bool(config_payload.get("enabled", self._enabled)),
                "access_token": (config_payload.get("access_token") or self._access_token or "").strip(),
                "refresh_token": (config_payload.get("refresh_token") or self._refresh_token or "").strip(),
                "client_id": (
                    (config_payload.get("client_id") or self._client_id or GuangYaClient.DEFAULT_CLIENT_ID).strip()
                    or GuangYaClient.DEFAULT_CLIENT_ID
                ),
                "device_id": (config_payload.get("device_id") or self._device_id or "").strip(),
                "poll_interval": int(config_payload.get("poll_interval") or self._poll_interval or 5),
                "page_size": int(config_payload.get("page_size") or self._page_size or 100),
                "order_by": int(config_payload.get("order_by") or self._order_by or 3),
                "sort_type": int(config_payload.get("sort_type") or self._sort_type or 1),
                "permanently_delete": bool(config_payload.get("permanently_delete", self._permanently_delete)),
            }
            self.update_config(new_config)
            self.init_plugin(new_config)
            return {
                "success": True,
                "message": "配置保存成功",
                "data": self._get_config(),
            }
        except Exception as err:
            logger.error(f"【光鸭云盘】保存配置失败: {err}")
            return {
                "success": False,
                "message": f"保存配置失败: {err}",
            }

    def get_module(self) -> Dict[str, Any]:
        """
        获取插件模块声明。
        """
        return {
            "list_files": self.list_files,
            "any_files": self.any_files,
            "download_file": self.download_file,
            "upload_file": self.upload_file,
            "delete_file": self.delete_file,
            "rename_file": self.rename_file,
            "get_file_item": self.get_file_item,
            "get_parent_item": self.get_parent_item,
            "snapshot_storage": self.snapshot_storage,
            "storage_usage": self.storage_usage,
            "support_transtype": self.support_transtype,
            "create_folder": self.create_folder,
            "exists": self.exists,
            "get_item": self.get_item,
        }

    @eventmanager.register(ChainEventType.StorageOperSelection)
    def storage_oper_selection(self, event: Event):
        """
        监听存储选择事件。
        """
        if not self._enabled:
            return
        event_data: StorageOperSelectionEventData = event.event_data
        if event_data.storage == self._disk_name:
            event_data.storage_oper = self._guangya_api  # noqa: SLF001

    def list_files(
        self, fileitem: schemas.FileItem, recursion: bool = False
    ) -> Optional[List[schemas.FileItem]]:
        """
        查询目录下所有目录和文件。
        """
        if fileitem.storage != self._disk_name:
            return None
        if not self._guangya_api:
            return []

        result: List[schemas.FileItem] = []

        def _walk(_item: FileItem, _recursion: bool = False):
            items = self._guangya_api.list(_item)
            if not items:
                return
            if _recursion:
                for sub_item in items:
                    if sub_item.type == "dir":
                        _walk(sub_item, _recursion)
                    else:
                        result.append(sub_item)
            else:
                result.extend(items)

        _walk(fileitem, recursion)
        return result

    def any_files(
        self, fileitem: schemas.FileItem, extensions: list = None
    ) -> Optional[bool]:
        """
        查询目录下是否存在任意目标文件。
        """
        if fileitem.storage != self._disk_name:
            return None
        if not self._guangya_api:
            return False

        def _any(_item: FileItem) -> bool:
            items = self._guangya_api.list(_item)
            if not items:
                return False
            if not extensions:
                return True
            for sub_item in items:
                if (
                    sub_item.type == "file"
                    and sub_item.extension
                    and f".{sub_item.extension.lower()}" in extensions
                ):
                    return True
                if sub_item.type == "dir" and _any(sub_item):
                    return True
            return False

        return _any(fileitem)

    def create_folder(
        self, fileitem: schemas.FileItem, name: str
    ) -> Optional[schemas.FileItem]:
        if fileitem.storage != self._disk_name:
            return None
        if not self._guangya_api:
            return None
        return self._guangya_api.create_folder(fileitem=fileitem, name=name)

    def download_file(
        self, fileitem: schemas.FileItem, path: Path = None
    ) -> Optional[Path]:
        if fileitem.storage != self._disk_name:
            return None
        if not self._guangya_api:
            return None
        return self._guangya_api.download(fileitem, path)

    def upload_file(
        self, fileitem: schemas.FileItem, path: Path, new_name: Optional[str] = None
    ) -> Optional[schemas.FileItem]:
        if fileitem.storage != self._disk_name:
            return None
        if not self._guangya_api:
            return None
        return self._guangya_api.upload(fileitem, path, new_name)

    def delete_file(self, fileitem: schemas.FileItem) -> Optional[bool]:
        if fileitem.storage != self._disk_name:
            return None
        if not self._guangya_api:
            return None
        return self._guangya_api.delete(fileitem)

    def rename_file(self, fileitem: schemas.FileItem, name: str) -> Optional[bool]:
        if fileitem.storage != self._disk_name:
            return None
        if not self._guangya_api:
            return None
        return self._guangya_api.rename(fileitem, name)

    def exists(self, fileitem: schemas.FileItem) -> Optional[bool]:
        if fileitem.storage != self._disk_name:
            return None
        return True if self.get_item(fileitem) else False

    def get_item(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        if fileitem.storage != self._disk_name:
            return None
        return self.get_file_item(storage=fileitem.storage, path=Path(fileitem.path))

    def get_file_item(self, storage: str, path: Path) -> Optional[schemas.FileItem]:
        if storage != self._disk_name:
            return None
        if not self._guangya_api:
            return None
        return self._guangya_api.get_item(path)

    def get_parent_item(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        if fileitem.storage != self._disk_name:
            return None
        if not self._guangya_api:
            return None
        return self._guangya_api.get_parent(fileitem)

    def snapshot_storage(
        self,
        storage: str,
        path: Path,
        last_snapshot_time: float = None,
        max_depth: int = 5,
    ) -> Optional[Dict[str, Dict]]:
        if storage != self._disk_name:
            return None
        if not self._guangya_api:
            return {}

        files_info: Dict[str, Dict] = {}

        def _snapshot(_fileitem: schemas.FileItem, current_depth: int = 0):
            try:
                if _fileitem.type == "dir":
                    if current_depth >= max_depth:
                        return
                    if (
                        self.snapshot_check_folder_modtime  # noqa
                        and last_snapshot_time
                        and _fileitem.modify_time
                        and _fileitem.modify_time <= last_snapshot_time
                    ):
                        return
                    for sub_file in self._guangya_api.list(_fileitem):
                        _snapshot(sub_file, current_depth + 1)
                else:
                    modify_time = getattr(_fileitem, "modify_time", 0) or 0
                    if not last_snapshot_time or modify_time > last_snapshot_time:
                        files_info[_fileitem.path] = {
                            "size": _fileitem.size or 0,
                            "modify_time": modify_time,
                            "type": _fileitem.type,
                        }
            except Exception as err:
                logger.debug(f"Snapshot error for {_fileitem.path}: {err}")

        root_item = self._guangya_api.get_item(path)
        if not root_item:
            return {}
        _snapshot(root_item)
        return files_info

    def storage_usage(self, storage: str) -> Optional[schemas.StorageUsage]:
        if storage != self._disk_name:
            return None
        if not self._guangya_api:
            return None
        return self._guangya_api.usage()

    def support_transtype(self, storage: str) -> Optional[dict]:
        if storage != self._disk_name:
            return None
        return {"move": "移动", "copy": "复制"}

    def get_qrcode(self) -> Dict[str, Any]:
        """
        获取扫码二维码。
        """
        try:
            self._device_id = uuid.uuid4().hex
            self._qr_expires_at = 0
            temp_client = GuangYaClient(
                access_token=None,
                refresh_token=None,
                client_id=self._client_id,
                device_id=self._device_id,
            )
            result = temp_client.get_device_code()
            if not result:
                return {"success": False, "message": "获取二维码失败"}

            self._device_code = result.get("device_code") or ""
            self._poll_interval = int(result.get("interval") or self._poll_interval or 5)
            self._user_code = result.get("user_code") or ""
            self._verification_uri = result.get("verification_uri") or ""
            expires_in = int(result.get("expires_in") or 300)
            self._qr_expires_at = time.time() + expires_in

            return {
                "success": True,
                "user_code": self._user_code,
                "verification_uri": self._verification_uri,
                "verification_uri_complete": result.get("verification_uri_complete") or "",
                "expires_in": expires_in,
                "device_id": self._device_id,
            }
        except Exception as err:
            logger.error(f"【光鸭云盘】获取二维码失败: {err}")
            return {"success": False, "message": f"获取二维码失败: {err}"}

    def poll_login(self) -> Dict[str, Any]:
        """
        轮询扫码登录状态。
        """
        if not self._device_code:
            return {"success": False, "message": "请先获取二维码"}
        if self._qr_expires_at and time.time() > self._qr_expires_at:
            return {"success": False, "message": "二维码已过期，请重新获取"}

        try:
            temp_client = GuangYaClient(
                access_token=None,
                refresh_token=None,
                client_id=self._client_id,
                device_id=self._device_id,
            )
            result = temp_client.poll_device_code(self._device_code)
            if result and result.get("waiting"):
                return {"success": False, "message": result.get("message") or "等待扫码中...", "waiting": True}
            if not result or not result.get("access_token"):
                return {"success": False, "message": "等待扫码中...", "waiting": True}

            self._access_token = result.get("access_token") or ""
            self._refresh_token = result.get("refresh_token") or ""
            self.update_config(
                {
                    "enabled": self._enabled,
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "device_id": self._device_id,
                    "poll_interval": self._poll_interval,
                    "page_size": self._page_size,
                    "order_by": self._order_by,
                    "sort_type": self._sort_type,
                    "permanently_delete": self._permanently_delete,
                }
            )
            self.init_plugin(
                {
                    "enabled": self._enabled,
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "device_id": self._device_id,
                    "poll_interval": self._poll_interval,
                    "page_size": self._page_size,
                    "order_by": self._order_by,
                    "sort_type": self._sort_type,
                    "permanently_delete": self._permanently_delete,
                }
            )
            self._device_code = ""
            logger.info("【光鸭云盘】扫码登录成功")
            return {
                "success": True,
                "message": "登录成功",
                "device_id": self._device_id,
            }
        except Exception as err:
            logger.error(f"【光鸭云盘】轮询登录失败: {err}")
            return {"success": False, "message": f"轮询失败: {err}"}

    def logout(self) -> Dict[str, Any]:
        """
        退出登录。
        """
        self._access_token = ""
        self._refresh_token = ""
        self._device_code = ""
        self._user_code = ""
        self._verification_uri = ""
        self._qr_expires_at = 0
        self._client = None
        self._guangya_api = None

        self.update_config(
            {
                "enabled": self._enabled,
                "access_token": "",
                "refresh_token": "",
                "client_id": self._client_id,
                "device_id": "",
                "poll_interval": self._poll_interval,
                "page_size": self._page_size,
                "order_by": self._order_by,
                "sort_type": self._sort_type,
                "permanently_delete": self._permanently_delete,
            }
        )
        return {"success": True, "message": "已退出登录"}

    def stop_service(self):
        """
        退出插件。
        """
        pass
