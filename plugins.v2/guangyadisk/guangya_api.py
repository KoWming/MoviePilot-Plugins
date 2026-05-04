"""
光鸭云盘基础操作类
"""

import ast
import shutil
import time
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from app import schemas
from app.core.config import global_vars, settings
from app.log import logger
from app.modules.filemanager.storages import transfer_process

from .guangya_client import GuangYaClient


class GuangYaApi:
    """
    光鸭云盘基础操作类
    """

    _FILE_LIST_URL = "https://api.guangyapan.com/nd.bizuserres.s/v1/file/get_file_list"
    _ASSETS_URL = "https://api.guangyapan.com/nd.bizassets.s/v1/get_assets"
    _DOWNLOAD_URL = "https://api.guangyapan.com/nd.bizuserres.s/v1/get_res_download_url"
    _VOD_DOWNLOAD_URL = "https://api.guangyapan.com/nd.bizuserres.s/v1/file/get_vod_download_url"

    _id_cache: Dict[str, str] = {}
    _item_cache: Dict[str, Dict[str, Any]] = {}

    def __init__(
        self,
        client: GuangYaClient,
        disk_name: str,
        page_size: int = 100,
        order_by: int = 3,
        sort_type: int = 1,
        permanently_delete: bool = False,
    ):
        """
        初始化光鸭云盘操作实例。
        """
        self.client = client
        self._disk_name = disk_name
        self._page_size = page_size or 100
        self._order_by = order_by
        self._sort_type = sort_type
        self._permanently_delete = permanently_delete
        self.transtype = {"move": "移动", "copy": "复制"}
        self._id_cache["/"] = ""

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        规范化路径格式。
        """
        normalized = str(path or "/").replace("\\", "/")
        if normalized in ("", "."):
            return "/"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        normalized = normalized.rstrip("/") or "/"
        return normalized

    def _build_path(self, parent_path: str, name: str, is_dir: bool) -> str:
        """
        根据父路径和名称构建完整路径。
        """
        normalized_parent = self._normalize_path(parent_path)
        item_path = f"{normalized_parent.rstrip('/')}/{name}" if normalized_parent != "/" else f"/{name}"
        return item_path + ("/" if is_dir else "")

    @staticmethod
    def _normalize_fileid(fileid: Optional[str], path: Optional[str] = None) -> str:
        """
        规范化文件 ID。
        """
        normalized_fileid = str(fileid or "")
        normalized_path = str(path or "").replace("\\", "/")
        if normalized_fileid == "root" and normalized_path in ("", "/"):
            return ""
        return normalized_fileid

    def _cache_item(self, item: schemas.FileItem) -> None:
        """
        缓存文件项与路径映射。
        """
        normalized_path = self._normalize_path(item.path)
        normalized_fileid = self._normalize_fileid(item.fileid, normalized_path)
        if normalized_path != "/" and normalized_fileid:
            self._id_cache[normalized_path] = normalized_fileid
        self._item_cache[normalized_path] = {
            "storage": item.storage,
            "fileid": normalized_fileid,
            "parent_fileid": str(item.parent_fileid or ""),
            "name": item.name,
            "basename": item.basename,
            "extension": item.extension,
            "type": item.type,
            "path": item.path,
            "size": item.size,
            "modify_time": item.modify_time,
            "thumbnail": getattr(item, "thumbnail", None),
            "pickcode": item.pickcode,
            "drive_id": getattr(item, "drive_id", None),
        }

    def _invalidate_path_cache(self, path: str) -> None:
        """
        失效指定路径相关缓存。
        """
        normalized_path = self._normalize_path(path)
        self._id_cache.pop(normalized_path, None)
        self._item_cache.pop(normalized_path, None)
        dir_key = normalized_path if normalized_path == "/" else f"{normalized_path.rstrip('/')}/"
        file_key = normalized_path.rstrip("/") or "/"
        self._id_cache.pop(dir_key, None)
        self._item_cache.pop(dir_key, None)
        self._id_cache.pop(file_key, None)
        self._item_cache.pop(file_key, None)

    def _cache_path_id(self, path: str, file_id: str) -> None:
        """
        缓存路径与文件 ID 的映射关系。
        """
        normalized_path = self._normalize_path(path)
        normalized_fileid = self._normalize_fileid(file_id, normalized_path)
        if normalized_path != "/" and normalized_fileid:
            self._id_cache[normalized_path] = normalized_fileid

    @staticmethod
    def _is_success(resp: Dict[str, Any]) -> bool:
        """
        判断接口响应是否成功。
        """
        if not isinstance(resp, dict):
            return False
        code = resp.get("code")
        msg = str(resp.get("msg") or resp.get("message") or "").lower()
        return code in (0, 200, "0", "200", None) and msg not in ("error", "fail", "failed")

    @staticmethod
    def _get_data(resp: Dict[str, Any]) -> Any:
        """
        提取响应中的 data 数据。
        """
        if not isinstance(resp, dict):
            return {}
        return resp.get("data") or resp.get("result") or resp

    @staticmethod
    def _first_value(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
        """
        按候选字段顺序获取首个有效值。
        """
        for key in keys:
            if isinstance(data, dict) and data.get(key) is not None:
                return data.get(key)
        return default

    @staticmethod
    def _parse_time(value: Any) -> Optional[float]:
        """
        解析时间字段为时间戳。
        """
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            return value / 1000 if value > 9999999999 else value
        if isinstance(value, str):
            try:
                if value.isdigit():
                    num = int(value)
                    return num / 1000 if num > 9999999999 else num
                return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except Exception:
                return None
        return None

    def _extract_list(self, resp: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从响应中提取列表数据。
        """
        data = self._get_data(resp)
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ("list", "files", "items", "records", "fileList", "infoList", "InfoList"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return []

    def _find_number(self, data: Any, keys: List[str]) -> Optional[float]:
        """
        在嵌套数据中查找数值字段。
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key in keys and value not in (None, ""):
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        pass
            for value in data.values():
                found = self._find_number(value, keys)
                if found is not None:
                    return found
        elif isinstance(data, list):
            for value in data:
                found = self._find_number(value, keys)
                if found is not None:
                    return found
        return None

    def _request_assets(self) -> Dict[str, Any]:
        """
        获取空间信息原始响应。
        """
        return self.client.get_assets()

    def _to_file_item(self, item: Dict[str, Any], parent_path: str = "/") -> schemas.FileItem:
        """
        将原始文件数据转换为 FileItem。
        """
        file_id = str(self._first_value(item, ["fileId", "id", "fid", "resId"], ""))
        parent_id = str(self._first_value(item, ["parentId", "parent_file_id", "parentFileId"], ""))
        name = self._first_value(item, ["fileName", "name", "filename"], "") or ""
        raw_type = self._first_value(item, ["type", "resType", "fileType", "dirType"])
        is_dir = bool(
            item.get("isDir")
            or item.get("is_dir")
            or item.get("dir")
            or raw_type in (2, "dir", "folder")
        )
        if raw_type in (0, 1, "file"):
            is_dir = False
        path = f"{parent_path.rstrip('/')}/{name}" if parent_path != "/" else f"/{name}"
        file_path = path + ("/" if is_dir else "")
        size = self._first_value(item, ["fileSize", "size", "Size"], None)
        modify_time = self._parse_time(
            self._first_value(item, ["utime", "updateTime", "updatedAt", "UpdateAt", "modifyTime", "mtime"])
        )

        if file_id:
            self._id_cache[path] = file_id
            if is_dir:
                self._id_cache[file_path.rstrip("/")] = file_id

        file_item = schemas.FileItem(
            storage=self._disk_name,
            fileid=file_id,
            parent_fileid=parent_id,
            name=name,
            basename=Path(name).stem,
            extension=Path(name).suffix[1:] if not is_dir and Path(name).suffix else None,
            type="dir" if is_dir else "file",
            path=file_path,
            size=int(size) if size not in (None, "") and not is_dir else None,
            modify_time=modify_time,
            thumbnail=self._first_value(item, ["thumbnail", "thumb", "cover"], None),
            pickcode=str(item),
            drive_id=str(self._first_value(item, ["gcid", "GCID", "md5"], "")) or None,
        )
        self._cache_item(file_item)
        return file_item

    def _iter_parent_items(self, parent_id: str, parent_path: str) -> List[schemas.FileItem]:
        """
        分页遍历指定父目录下的全部文件项。
        """
        results: List[schemas.FileItem] = []
        page = 0
        while True:
            response = self.client.get_file_list(
                parent_id=parent_id,
                page_size=self._page_size,
                order_by=self._order_by,
                sort_type=self._sort_type,
                file_types=[],
                page=page,
            )
            if not self._is_success(response):
                break
            item_list = self._extract_list(response)
            if not item_list:
                break
            for item in item_list:
                results.append(self._to_file_item(item, parent_path))
            total = (response.get("data") or {}).get("total") or 0
            if len(item_list) < self._page_size or (total and len(results) >= total):
                break
            page += 1
        return results

    def _path_to_id(self, path: str) -> str:
        """
        根据路径解析对应的文件 ID。
        """
        normalized_path = self._normalize_path(path)
        if normalized_path == "/":
            return ""
        if normalized_path in self._id_cache:
            return self._id_cache[normalized_path]

        current_id = ""
        current_path = "/"
        parts = Path(normalized_path).parts[1:]
        for part in parts:
            found = None
            parent_item = schemas.FileItem(
                storage=self._disk_name,
                fileid=current_id,
                path=current_path,
                type="dir",
            )
            for item in self.list(parent_item):
                if item.name == part:
                    found = item
                    break
            if not found:
                raise FileNotFoundError(f"【光鸭云盘】{normalized_path} 不存在")
            current_id = found.fileid or ""
            current_path = found.path if found.type == "dir" else str(Path(found.path).parent)
        self._id_cache[normalized_path] = current_id
        return current_id

    def list(self, fileitem: schemas.FileItem, page: int = 0, page_size: int = 100) -> List[schemas.FileItem]:
        """
        获取目录下的文件列表。
        """
        if fileitem.type == "file":
            item = self.detail(fileitem)
            return [item] if item else []

        if fileitem.path == "/":
            file_id = ""
        else:
            file_id = fileitem.fileid or self._path_to_id(fileitem.path)

        items: List[schemas.FileItem] = []
        try:
            response = self.client.get_file_list(
                parent_id=file_id or "",
                page_size=max(page_size, self._page_size),
                order_by=self._order_by,
                sort_type=self._sort_type,
                file_types=[],
                page=page,
            )
            if not self._is_success(response):
                logger.debug(f"【光鸭云盘】获取文件列表失败: {response}")
                return items
            for raw in self._extract_list(response):
                items.append(self._to_file_item(raw, fileitem.path or "/"))
        except Exception as err:
            logger.debug(f"【光鸭云盘】获取信息失败: {err}")
        return items

    def detail(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        """
        获取文件详情。
        """
        if fileitem.path:
            item = self.get_item(Path(fileitem.path))
            if item:
                return item
        return fileitem if fileitem.fileid else None

    def create_folder(self, fileitem: schemas.FileItem, name: str) -> Optional[schemas.FileItem]:
        """
        在指定目录下创建文件夹。
        """
        try:
            new_path = Path(fileitem.path) / name
            parent_id = fileitem.fileid or self._path_to_id(fileitem.path)
            response = self.client.create_dir(parent_id=parent_id or "", dir_name=name)
            if not self._is_success(response):
                logger.debug(f"【光鸭云盘】创建目录失败: {response}")
                return None
            data = self._get_data(response)
            raw = data.get("info") or data.get("Info") or data if isinstance(data, dict) else {}
            file_id = str(self._first_value(raw, ["fileId", "id", "FileId"], ""))
            self._id_cache[str(new_path).replace("\\", "/")] = file_id
            folder_item = schemas.FileItem(
                storage=self._disk_name,
                fileid=file_id,
                parent_fileid=parent_id,
                path=str(new_path).replace("\\", "/") + "/",
                name=name,
                basename=name,
                type="dir",
                modify_time=int(datetime.now().timestamp()),
                pickcode=str(raw),
            )
            self._cache_item(folder_item)
            return folder_item
        except Exception as err:
            logger.debug(f"【光鸭云盘】创建目录失败: {err}")
            return None

    def get_folder(self, path: Path) -> Optional[schemas.FileItem]:
        """
        获取目录，不存在时自动创建。
        """
        folder = self.get_item(path)
        if folder:
            return folder

        current = schemas.FileItem(storage=self._disk_name, path="/", fileid="", type="dir")
        for part in path.parts[1:]:
            next_folder = None
            for sub_folder in self.list(current):
                if sub_folder.type == "dir" and sub_folder.name == part:
                    next_folder = sub_folder
                    break
            if not next_folder:
                next_folder = self.create_folder(current, part)
            if not next_folder:
                logger.warning(f"【光鸭云盘】创建目录 {current.path}{part} 失败！")
                return None
            current = next_folder
        return current

    def get_item(self, path: Path) -> Optional[schemas.FileItem]:
        """
        按路径获取单个文件项。
        """
        normalized = self._normalize_path(str(path))
        if normalized == "/":
            root_item = schemas.FileItem(
                storage=self._disk_name,
                path="/",
                fileid="",
                name=self._disk_name,
                basename=self._disk_name,
                type="dir",
            )
            self._cache_item(root_item)
            return root_item

        cached = self._item_cache.get(normalized)
        if cached:
            return schemas.FileItem(**cached)

        try:
            parent_path = path.parent if path.parent.as_posix() else Path("/")
            parent_id = self._path_to_id(parent_path.as_posix())
            parent = schemas.FileItem(
                storage=self._disk_name,
                path=parent_path.as_posix() if parent_path.as_posix() != "." else "/",
                fileid=parent_id,
                type="dir",
            )
            target_name = path.name
            for item in self.list(parent):
                if item.name == target_name:
                    return item
            return None
        except FileNotFoundError:
            return None
        except Exception as err:
            logger.debug(f"【光鸭云盘】获取文件信息失败: {err}")
            return None

    def get_parent(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        """
        获取文件项的父目录。
        """
        return self.get_item(Path(fileitem.path).parent)

    def _list_recycle_items(self, page: int = 0, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        获取回收站文件列表。
        """
        response = self.client.get_file_list(
            parent_id="",
            page_size=page_size,
            order_by=10,
            sort_type=0,
            file_types=[],
            page=page,
            dir_type=4,
        )
        return self._extract_list(response)

    def _find_recycle_item(self, fileitem: schemas.FileItem, retry: int = 10, interval: float = 0.5) -> Dict[str, Any]:
        """
        在回收站中查找目标文件。
        """
        target_name = fileitem.name or Path(fileitem.path).name
        target_path = str(fileitem.path or "").rstrip("/")
        for index in range(retry):
            for page in range(3):
                for raw in self._list_recycle_items(page=page, page_size=100):
                    raw_name = self._first_value(raw, ["fileName", "name", "filename"], "") or ""
                    if raw_name != target_name:
                        continue
                    raw_path = str(self._first_value(raw, ["location", "path", "filePath", "parentPath"], "") or "").rstrip("/")
                    if raw_path and target_path and target_path not in raw_path and raw_path not in target_path:
                        continue
                    return raw
            if index < retry - 1:
                time.sleep(interval)
        return {}

    def _delete_permanently_from_recycle(self, fileitem: schemas.FileItem) -> bool:
        """
        从回收站中永久删除文件。
        """
        recycle_item = self._find_recycle_item(fileitem)
        recycle_file_id = str(self._first_value(recycle_item, ["fileId", "id", "fid", "resId"], ""))
        if not recycle_file_id:
            return True
        response = self.client.delete_file([recycle_file_id])
        if not self._is_success(response):
            logger.warning(f"【光鸭云盘】永久删除失败，文件可能仍在回收站: {response}")
            return True
        return True

    def delete(self, fileitem: schemas.FileItem) -> bool:
        """
        删除文件或目录。
        """
        try:
            file_id = fileitem.fileid or self._path_to_id(fileitem.path)
            response = self.client.delete_file([file_id])
            if not self._is_success(response):
                logger.debug(f"【光鸭云盘】删除文件失败: {response}")
                return False
            self._invalidate_path_cache(fileitem.path)
            if self._permanently_delete:
                return self._delete_permanently_from_recycle(fileitem)
            return True
        except Exception as err:
            logger.debug(f"【光鸭云盘】删除文件异常: {err}")
            return False

    def rename(self, fileitem: schemas.FileItem, name: str) -> bool:
        """
        重命名文件或目录。
        """
        try:
            file_id = fileitem.fileid or self._path_to_id(fileitem.path)
            response = self.client.rename(file_id=file_id, new_name=name)
            if not self._is_success(response):
                logger.debug(f"【光鸭云盘】重命名失败: {response}")
                return False
            self._invalidate_path_cache(fileitem.path)
            return True
        except Exception as err:
            logger.debug(f"【光鸭云盘】重命名异常: {err}")
            return False

    @staticmethod
    def _parse_pickcode(value: Any) -> Dict[str, Any]:
        """
        解析 pickcode 中保存的原始文件信息。
        """
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        if isinstance(value, str):
            try:
                parsed = ast.literal_eval(value)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def _normalize_download_fileitem(self, fileitem: schemas.FileItem) -> schemas.FileItem:
        """
        规范化下载前的文件项信息。
        """
        pickcode = self._parse_pickcode(fileitem.pickcode)
        raw = pickcode.get("fileInfo") if isinstance(pickcode.get("fileInfo"), dict) else pickcode
        if not isinstance(raw, dict):
            raw = {}
        if not raw and fileitem.path and (not fileitem.fileid or not fileitem.name):
            item = self.get_item(Path(fileitem.path))
            if item:
                return item
        raw_file_id = str(self._first_value(raw, ["fileId", "id", "fid", "resId"], ""))
        raw_name = self._first_value(raw, ["fileName", "name", "filename"], "") or ""
        if not raw_file_id or not raw_name:
            return fileitem
        if fileitem.fileid == raw_file_id and fileitem.name:
            return fileitem
        location = pickcode.get("location") if isinstance(pickcode, dict) else None
        normalized_path = f"/{str(location).lstrip('/')}" if location else str(Path(fileitem.path) / raw_name).replace("\\", "/")
        return schemas.FileItem(
            storage=fileitem.storage,
            fileid=raw_file_id,
            parent_fileid=str(self._first_value(raw, ["parentId", "parent_file_id", "parentFileId"], fileitem.parent_fileid or "")),
            name=raw_name,
            basename=Path(raw_name).stem,
            extension=Path(raw_name).suffix[1:] if Path(raw_name).suffix else None,
            type="file",
            path=normalized_path,
            size=int(raw.get("fileSize")) if raw.get("fileSize") not in (None, "") else fileitem.size,
            modify_time=self._parse_time(self._first_value(raw, ["utime", "updateTime", "updatedAt", "modifyTime"], fileitem.modify_time)),
            thumbnail=self._first_value(raw, ["thumbnail", "thumb", "cover"], getattr(fileitem, "thumbnail", None)),
            pickcode=str(raw),
            drive_id=str(self._first_value(raw, ["gcid", "GCID", "md5"], getattr(fileitem, "drive_id", "") or "")) or None,
        )

    def _get_download_url(self, fileitem: schemas.FileItem) -> Optional[str]:
        """
        获取文件下载链接。
        """
        file_id = fileitem.fileid or self._path_to_id(fileitem.path)
        response = self.client.get_download_url(file_id)
        if self._is_success(response):
            data = self._get_data(response)
            download_url = self._first_value(
                data if isinstance(data, dict) else {},
                ["signedURL", "downloadUrl", "download_url", "url"],
            )
            if download_url:
                return download_url

        if response.get("code") != 143:
            logger.debug(f"【光鸭云盘】普通下载链接获取失败: {response}")

        if not getattr(fileitem, "drive_id", None):
            logger.error(f"【光鸭云盘】获取下载链接失败: {response}")
            return None

        vod_response = self.client._request(
            "POST",
            self._VOD_DOWNLOAD_URL,
            data={"fileId": file_id, "gcid": fileitem.drive_id},
        )
        if not self._is_success(vod_response):
            logger.error(f"【光鸭云盘】获取下载链接失败: {vod_response}")
            return None
        data = self._get_data(vod_response)
        download_url = self._first_value(
            data if isinstance(data, dict) else {},
            ["signedURL", "downloadUrl", "download_url", "url"],
        )
        if not download_url:
            logger.error("【光鸭云盘】获取下载链接失败: 无URL")
            return None
        return download_url

    def download(self, fileitem: schemas.FileItem, path: Path = None) -> Optional[Path]:
        """
        下载文件到本地路径。
        """
        try:
            fileitem = self._normalize_download_fileitem(fileitem)
            download_url = self._get_download_url(fileitem)
            if not download_url:
                return None
            local_path = (path or settings.TEMP_PATH) / (fileitem.name or Path(fileitem.path).name or fileitem.fileid)
        except Exception as err:
            logger.error(f"【光鸭云盘】获取下载链接失败: {fileitem.name} - {err}")
            return None

        file_size = fileitem.size
        progress_callback = transfer_process(Path(fileitem.path).as_posix())

        try:
            with requests.get(download_url, stream=True, timeout=300) as response_obj:
                response_obj.raise_for_status()
                downloaded_size = 0
                with open(local_path, "wb") as file_obj:
                    for chunk in response_obj.iter_content(chunk_size=10 * 1024 * 1024):
                        if global_vars.is_transfer_stopped(fileitem.path):
                            return None
                        if not chunk:
                            continue
                        file_obj.write(chunk)
                        downloaded_size += len(chunk)
                        if file_size:
                            progress_callback((downloaded_size * 100) / file_size)
            progress_callback(100)
            return local_path
        except Exception as err:
            logger.error(f"【光鸭云盘】下载失败: {fileitem.name} - {err}")
            try:
                if local_path.exists():
                    local_path.unlink()
            except Exception:
                pass
            return None

    def _extract_file_info(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        """
        从上传响应中提取文件信息。
        """
        data = self._get_data(resp)
        if not isinstance(data, dict):
            return {}
        for key in ("fileInfo", "info", "Info", "detail"):
            value = data.get(key)
            if isinstance(value, dict):
                return value
        return data

    def _has_uploaded_file(self, resp: Dict[str, Any]) -> bool:
        """
        判断上传响应中是否已包含文件信息。
        """
        raw = self._extract_file_info(resp)
        return bool(self._first_value(raw, ["fileId", "id", "fid", "resId", "FileId"], ""))

    def _wait_upload_done(self, result: Dict[str, Any], max_try: int = 120, interval: float = 1.0) -> Dict[str, Any]:
        """
        轮询等待上传任务完成。
        """
        task_data = self._get_data(result)
        task_id = str(self._first_value(task_data if isinstance(task_data, dict) else {}, ["taskId", "task_id"], ""))
        if not task_id:
            return result
        last_result = result
        pending_status = (0, 1, 3, 146, 147, 155, 163, "0", "1", "3", "146", "147", "155", "163")
        for index in range(max_try):
            try:
                status_info = self.client.get_task_status(task_id)
                if isinstance(status_info, dict):
                    status_code = status_info.get("code")
                    if status_code in (145, "145"):
                        return status_info
                    status_data = self._get_data(status_info)
                    status = self._first_value(status_data if isinstance(status_data, dict) else {}, ["status", "taskStatus"], None)
                    if status in (2, "2", "success", "done", "finished"):
                        info = self.client.get_file_info_by_task_id(task_id)
                        if self._has_uploaded_file(info):
                            return info
                        last_result = info if isinstance(info, dict) else status_info
                    elif status not in pending_status and not self._is_success(status_info):
                        return status_info
            except Exception:
                pass

            info = self.client.get_file_info_by_task_id(task_id)
            if self._has_uploaded_file(info):
                return info
            last_result = info
            code = info.get("code") if isinstance(info, dict) else None
            msg = str(info.get("msg") or info.get("message") or "") if isinstance(info, dict) else ""
            if code in (145, "145"):
                return info
            if code not in (147, "147") and "上传中" not in msg:
                return info
            if index < max_try - 1:
                time.sleep(interval)
        return last_result

    def _confirm_uploaded_item(self, target_path: Path, retry: int = 20, interval: float = 0.5) -> Optional[schemas.FileItem]:
        """
        确认上传后的文件在云盘中可见。
        """
        target_path = Path(target_path)
        for index in range(retry):
            parent_path = target_path.parent if target_path.parent.as_posix() else Path("/")
            parent_id = self._path_to_id(parent_path.as_posix())
            parent = schemas.FileItem(
                storage=self._disk_name,
                path=parent_path.as_posix() if parent_path.as_posix() != "." else "/",
                fileid=parent_id,
                type="dir",
            )
            for item in self.list(parent):
                if item.name == target_path.name:
                    return item
            self._id_cache.pop(target_path.as_posix(), None)
            if index < retry - 1:
                time.sleep(interval)
        return None

    def _build_uploaded_item(self, target_path: Path, target_name: str, parent_id: str, file_size: int, raw: Dict[str, Any] = None) -> schemas.FileItem:
        """
        基于上传响应构造文件项。
        """
        raw = raw or {}
        file_id = str(self._first_value(raw, ["fileId", "id", "FileId", "fid", "resId"], ""))
        return schemas.FileItem(
            storage=self._disk_name,
            fileid=file_id,
            parent_fileid=parent_id,
            path=Path(target_path).as_posix(),
            type="file",
            name=target_name,
            basename=Path(target_name).stem,
            extension=Path(target_name).suffix[1:] if Path(target_name).suffix else None,
            size=file_size,
            modify_time=int(datetime.now().timestamp()),
            pickcode=str(raw),
            thumbnail=self._first_value(raw, ["thumbnail", "thumb", "cover"], None),
            drive_id=str(self._first_value(raw, ["gcid", "GCID", "md5"], "")) or None,
        )

    def upload(self, target_dir: schemas.FileItem, local_path: Path, new_name: Optional[str] = None) -> Optional[schemas.FileItem]:
        """
        上传本地文件到目标目录。
        """
        if local_path.is_dir():
            return self.upload_folder(target_dir, local_path, new_name)

        target_name = new_name or local_path.name
        target_path = Path(target_dir.path) / target_name
        parent_id = target_dir.fileid or self._path_to_id(target_dir.path)

        try:
            progress_callback = transfer_process(local_path.as_posix())
            file_size = local_path.stat().st_size
            hash_md5 = md5()
            with open(local_path, "rb") as file_obj:
                for chunk in iter(lambda: file_obj.read(4096), b""):
                    hash_md5.update(chunk)
            file_md5 = hash_md5.hexdigest().upper()

            flash_response = self.client.check_flash_upload(
                task_id="",
                gcid=file_md5,
                file_size=file_size,
                file_name=target_name,
                parent_id=parent_id or "",
            )
            if self._is_success(flash_response) and flash_response.get("data"):
                visible_item = self._confirm_uploaded_item(target_path, retry=10, interval=0.3)
                if visible_item:
                    progress_callback(100)
                    return visible_item

            response = self.client.get_upload_token(
                file_name=target_name,
                file_size=file_size,
                file_md5=file_md5,
                parent_id=parent_id or "",
                capacity=2,
            )

            if response.get("code") == 156:
                visible_item = self._confirm_uploaded_item(target_path, retry=20, interval=0.5)
                if visible_item:
                    progress_callback(100)
                    return visible_item

            if not self._is_success(response):
                return None

            data = response.get("data", {}) or {}
            object_path = data.get("objectPath", "")
            bucket_name = data.get("bucketName", "")
            endpoint = data.get("endPoint", "") or data.get("fullEndPoint", "")
            creds = data.get("creds", {}) or {}
            access_key_id = creds.get("accessKeyID", "")
            secret_access_key = creds.get("secretAccessKey", "")
            session_token = creds.get("sessionToken", "")

            if endpoint and bucket_name and object_path and access_key_id and secret_access_key and session_token:
                parsed = urlparse(endpoint if endpoint.startswith("http") else f"https://{endpoint}")
                host = parsed.netloc or parsed.path
                if bucket_name and host.startswith(bucket_name + "."):
                    host = host[len(bucket_name) + 1 :]
                self.client.upload_file_multipart(
                    endpoint=f"https://{host}",
                    bucket_name=bucket_name,
                    object_path=object_path,
                    file_path=str(local_path),
                    oss_access_key_id=access_key_id,
                    oss_access_key_secret=secret_access_key,
                    security_token=session_token,
                    progress_callback=lambda consumed, total: progress_callback((consumed * 100) / total) if total else None,
                )

            task_id = str(self._first_value(data, ["taskId", "task_id"], ""))
            result = response
            if task_id:
                result = self._wait_upload_done({"data": {"taskId": task_id}})

            item = self._confirm_uploaded_item(target_path)
            if item:
                progress_callback(100)
                return item

            if isinstance(result, dict):
                raw = self._extract_file_info(result)
                if self._has_uploaded_file(result):
                    progress_callback(100)
                    return self._build_uploaded_item(target_path, target_name, parent_id, file_size, raw)

            return None
        except Exception as err:
            logger.error(f"【光鸭云盘】上传失败: {target_name} - {err}")
            return None

    def upload_folder(self, target_dir: schemas.FileItem, local_path: Path, new_name: Optional[str] = None) -> Optional[schemas.FileItem]:
        """
        递归上传本地文件夹。
        """
        folder_name = new_name or local_path.name
        cloud_folder = self.create_folder(target_dir, folder_name)
        if not cloud_folder:
            return None
        for child in local_path.iterdir():
            if global_vars.is_transfer_stopped(child.as_posix()):
                return None
            if child.is_dir():
                if not self.upload_folder(cloud_folder, child):
                    return None
            else:
                if not self.upload(cloud_folder, child):
                    return None
        return cloud_folder

    def _wait_item_visible(self, parent_path: Path, name: str, retry: int = 10, interval: float = 0.5) -> Optional[schemas.FileItem]:
        """
        等待文件项在目标目录中可见。
        """
        target_path = Path(parent_path) / name
        for index in range(retry):
            item = self.get_item(target_path)
            if item:
                return item
            if index < retry - 1:
                time.sleep(interval)
        return None

    def copy(self, fileitem: schemas.FileItem, path: Path, new_name: str = None) -> bool:
        """
        复制文件到目标目录。
        """
        try:
            target_parent = Path(path)
            target_id = self._path_to_id(target_parent.as_posix())
            file_id = fileitem.fileid or self._path_to_id(fileitem.path)
            response = self.client.copy_file([file_id], target_parent_id=target_id or "")
            if not self._is_success(response):
                return False
            task_id = str(self._first_value(self._get_data(response) if isinstance(self._get_data(response), dict) else {}, ["taskId", "task_id"], ""))
            if task_id:
                self._wait_upload_done({"data": {"taskId": task_id}})
            copied_item = self._wait_item_visible(target_parent, fileitem.name or Path(fileitem.path).name)
            if not copied_item:
                return False
            if new_name and new_name != copied_item.name:
                return self.rename(copied_item, new_name)
            return True
        except Exception as err:
            logger.debug(f"【光鸭云盘】复制文件异常: {err}")
            return False

    def move(self, fileitem: schemas.FileItem, path: Path, new_name: str = None) -> bool:
        """
        移动文件到目标目录。
        """
        try:
            target_parent = Path(path)
            source_path = Path(fileitem.path)
            current_name = fileitem.name or source_path.name
            target_name = new_name or current_name
            if target_parent.as_posix() == source_path.parent.as_posix():
                if target_name == current_name:
                    return True
                return self.rename(fileitem, target_name)

            target_id = self._path_to_id(target_parent.as_posix())
            file_id = fileitem.fileid or self._path_to_id(fileitem.path)
            response = self.client.move_file([file_id], target_parent_id=target_id or "")
            if not self._is_success(response):
                return False
            task_id = str(self._first_value(self._get_data(response) if isinstance(self._get_data(response), dict) else {}, ["taskId", "task_id"], ""))
            if task_id:
                self._wait_upload_done({"data": {"taskId": task_id}})
            moved_item = self._wait_item_visible(target_parent, current_name)
            if not moved_item:
                return False
            if target_name != moved_item.name:
                return self.rename(moved_item, target_name)
            return True
        except Exception as err:
            logger.debug(f"【光鸭云盘】移动文件异常: {err}")
            return False

    def snapshot(self, fileitem: schemas.FileItem) -> List[schemas.FileItem]:
        """
        递归获取目录下全部文件快照。
        """
        result: List[schemas.FileItem] = []

        def __walk(_item: schemas.FileItem):
            for child in self.list(_item):
                if child.type == "dir":
                    __walk(child)
                else:
                    result.append(child)

        __walk(fileitem)
        return result

    def exists(self, fileitem: schemas.FileItem) -> bool:
        """
        判断文件项是否存在。
        """
        return bool(self.get_item(Path(fileitem.path)))

    def usage(self) -> Optional[schemas.StorageUsage]:
        """
        获取存储空间使用情况。
        """
        try:
            assets = self._request_assets()
            if not self._is_success(assets):
                return schemas.StorageUsage(total=0, available=0)
            data = self._get_data(assets)
            total = self._find_number(data, [
                "totalSpaceSize", "total_space", "totalSpace", "total", "totalSize", "total_size",
                "capacity", "spaceTotal", "quota", "quotaSize",
            ])
            used = self._find_number(data, [
                "usedSpaceSize", "used_space", "usedSpace", "used", "usedSize", "used_size",
                "spaceUsed", "useSize", "fileSize",
            ])
            available = self._find_number(data, [
                "freeSpaceSize", "free_space", "freeSpace", "free", "available", "freeSize",
                "free_size", "availableSpace", "spaceAvailable", "remain", "remainSize", "remainingSize",
            ])
            total = float(total or 0)
            if available is None:
                available = max(total - float(used or 0), 0) if total else 0
            return schemas.StorageUsage(total=total, available=float(available or 0))
        except Exception as err:
            logger.debug(f"【光鸭云盘】获取空间使用情况失败: {err}")
            return schemas.StorageUsage(total=0, available=0)

    def support_transtype(self) -> dict:
        """
        获取支持的传输类型。
        """
        return self.transtype

    def is_support_transtype(self, transtype: str) -> bool:
        """
        判断是否支持指定传输类型。
        """
        return transtype in self.transtype

    @staticmethod
    def copy_local(src: Path, dst: Path) -> bool:
        """
        本地复制文件或目录。
        """
        try:
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            return True
        except Exception:
            return False
