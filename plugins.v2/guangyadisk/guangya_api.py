"""
光鸭云盘基础操作类
"""

from __future__ import annotations

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

from app import schemas
from app.core.config import global_vars, settings
from app.log import logger
from app.modules.filemanager.storages import transfer_process

from .guangya_client import GuangYaClient


class GuangYaApi:
    """
    光鸭云盘基础操作类。
    """

    _id_cache: Dict[str, str] = {}
    _item_cache: Dict[str, dict] = {}

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
        初始化 API。
        """
        self.client = client
        self._disk_name = disk_name
        self._page_size = page_size or 100
        self._order_by = order_by
        self._sort_type = sort_type
        self._permanently_delete = permanently_delete
        self._pending_purge_keys = set()
        self._pending_purge_lock = threading.Lock()
        self.transtype = {"move": "移动", "copy": "复制"}

    @staticmethod
    def _normalize_path(path: str) -> str:
        normalized = str(path or "/").replace("\\", "/")
        if normalized in ("", "."):
            return "/"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        normalized = normalized.rstrip("/") or "/"
        return normalized

    def _build_path(self, parent_path: str, name: str, is_dir: bool) -> str:
        normalized_parent = self._normalize_path(parent_path)
        item_path = f"{normalized_parent.rstrip('/')}/{name}" if normalized_parent != "/" else f"/{name}"
        return item_path + ("/" if is_dir else "")

    @staticmethod
    def _normalize_fileid(fileid: Optional[str], path: Optional[str] = None) -> str:
        normalized_fileid = str(fileid or "")
        normalized_path = str(path or "").replace("\\", "/")
        if normalized_fileid == "root" and normalized_path in ("", "/"):
            return ""
        return normalized_fileid

    def _cache_item(self, item: schemas.FileItem) -> None:
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
            "pickcode": item.pickcode,
        }

    def _invalidate_path_cache(self, path: str) -> None:
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
        normalized_path = self._normalize_path(path)
        normalized_fileid = self._normalize_fileid(file_id, normalized_path)
        if normalized_path != "/" and normalized_fileid:
            self._id_cache[normalized_path] = normalized_fileid

    def _iter_parent_items(self, parent_id: str, parent_path: str) -> List[schemas.FileItem]:
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
            if response.get("code", -1) != 0 and response.get("msg") != "success":
                break
            data = response.get("data", {}) or {}
            item_list = data.get("list", []) or []
            if not item_list:
                break
            for item in item_list:
                results.append(self._build_file_item_from_api(parent_path, item))
            total = data.get("total") or 0
            if len(item_list) < self._page_size or (total and len(results) >= total):
                break
            page += 1
        return results

    def _iter_recycle_items(self) -> List[schemas.FileItem]:
        results: List[schemas.FileItem] = []
        page = 1
        while True:
            response = self.client.get_file_list(
                parent_id="",
                page_size=self._page_size,
                order_by=10,
                sort_type=0,
                file_types=[],
                page=page,
                dir_type=4,
            )
            if response.get("code", -1) != 0 and response.get("msg") != "success":
                break
            data = response.get("data", {}) or {}
            item_list = data.get("list", []) or []
            if not item_list:
                break
            for item in item_list:
                recycle_item = self._build_file_item_from_api("/", item)
                recycle_item.path = self._build_path("/.recycle_bin", recycle_item.name, recycle_item.type == "dir")
                results.append(recycle_item)
            total = data.get("total") or 0
            if len(item_list) < self._page_size or (total and len(results) >= total):
                break
            page += 1
        return results

    def _match_recycle_item(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        target_fileid = str(fileitem.fileid or "")
        target_name = str(fileitem.name or "")
        target_size = fileitem.size
        candidates = self._iter_recycle_items()

        for item in candidates:
            if target_fileid and str(item.fileid or "") == target_fileid:
                return item

        same_name_items = [item for item in candidates if item.name == target_name]
        if len(same_name_items) == 1:
            return same_name_items[0]

        if target_size is not None:
            sized_items = [item for item in same_name_items if item.size == target_size]
            if len(sized_items) == 1:
                return sized_items[0]

        return None

    def _purge_from_recycle(self, fileitem: schemas.FileItem, max_try: int = 8, interval: float = 1.0) -> bool:
        recycle_item = None
        for index in range(max_try):
            recycle_item = self._match_recycle_item(fileitem)
            if recycle_item:
                break
            if index < max_try - 1:
                time.sleep(interval)

        if not recycle_item:
            logger.warning(f"【光鸭云盘】未在回收站中定位到待彻底删除项目: {fileitem.name}")
            return False

        response = self.client.delete_file([recycle_item.fileid])
        if response.get("msg") != "success" and response.get("code") != 0:
            logger.warning(f"【光鸭云盘】回收站彻底删除失败: {response}")
            return False

        task_id = (response.get("data", {}) or {}).get("taskId", "")
        if task_id and not self._wait_task_done(task_id, allow_missing=True):
            return False
        return True

    @staticmethod
    def _clone_fileitem(fileitem: schemas.FileItem) -> schemas.FileItem:
        return schemas.FileItem(
            storage=fileitem.storage,
            fileid=str(fileitem.fileid or ""),
            parent_fileid=str(fileitem.parent_fileid or ""),
            name=fileitem.name,
            basename=fileitem.basename,
            extension=fileitem.extension,
            type=fileitem.type,
            path=fileitem.path,
            size=fileitem.size,
            modify_time=fileitem.modify_time,
            pickcode=fileitem.pickcode,
        )

    def _build_purge_key(self, fileitem: schemas.FileItem) -> str:
        return str(fileitem.fileid or "") or self._normalize_path(fileitem.path or fileitem.name or "")

    def _schedule_purge_from_recycle(
        self,
        fileitem: schemas.FileItem,
        initial_delay: float = 15.0,
        max_try: int = 90,
        interval: float = 2.0,
    ) -> None:
        purge_item = self._clone_fileitem(fileitem)
        purge_key = self._build_purge_key(purge_item)

        with self._pending_purge_lock:
            if purge_key in self._pending_purge_keys:
                logger.info(f"【光鸭云盘】彻底删除任务已在队列中: {purge_item.name}")
                return
            self._pending_purge_keys.add(purge_key)

        def _worker() -> None:
            try:
                logger.info(f"【光鸭云盘】已加入延迟彻底删除队列，等待刮削及空目录清理完成: {purge_item.name}")
                if initial_delay > 0:
                    time.sleep(initial_delay)
                if self._purge_from_recycle(purge_item, max_try=max_try, interval=interval):
                    logger.info(f"【光鸭云盘】延迟彻底删除成功: {purge_item.name}")
                else:
                    logger.warning(f"【光鸭云盘】延迟彻底删除失败，回收站中仍未找到目标: {purge_item.name}")
            except Exception as err:
                logger.warning(f"【光鸭云盘】延迟彻底删除异常: {purge_item.name} - {err}")
            finally:
                with self._pending_purge_lock:
                    self._pending_purge_keys.discard(purge_key)

        threading.Thread(target=_worker, name=f"guangya-purge-{int(time.time())}", daemon=True).start()

    def _find_item_in_parent(
        self,
        parent_path: str,
        name: str,
        expected_type: Optional[str] = None,
    ) -> Optional[schemas.FileItem]:
        normalized_parent_path = self._normalize_path(parent_path)
        parent_id = ""
        if normalized_parent_path != "/":
            try:
                parent_id = self._path_to_id(normalized_parent_path)
            except FileNotFoundError:
                return None

        for item in self._iter_parent_items(parent_id=parent_id, parent_path=normalized_parent_path):
            if item.name != name:
                continue
            if expected_type and item.type != expected_type:
                continue
            return item
        return None

    def _wait_item_visible(
        self,
        parent_path: str,
        name: str,
        expected_type: Optional[str] = None,
        max_try: int = 10,
        interval: float = 0.3,
    ) -> Optional[schemas.FileItem]:
        for index in range(max_try):
            item = self._find_item_in_parent(parent_path=parent_path, name=name, expected_type=expected_type)
            if item:
                return item
            if index < max_try - 1:
                time.sleep(interval)
        return None

    @staticmethod
    def _is_task_missing(response: Optional[dict]) -> bool:
        payload = response or {}
        code = payload.get("code")
        message = str(payload.get("msg") or payload.get("error") or "")
        return code in (145, 147) or "任务不存在" in message

    def _restore_cached_item(self, path: str) -> Optional[schemas.FileItem]:
        cached = self._item_cache.get(self._normalize_path(path))
        if not cached:
            return None
        return schemas.FileItem(**cached)

    def _build_file_item_from_api(self, parent_path: str, item: dict) -> schemas.FileItem:
        file_name = item.get("fileName", "")
        item_id = str(item.get("fileId", ""))
        is_dir = item.get("resType") == 2
        file_path = self._build_path(parent_path, file_name, is_dir)
        file_item = schemas.FileItem(
            storage=self._disk_name,
            fileid=item_id,
            parent_fileid=str(item.get("parentId", "") or ""),
            name=file_name,
            basename=file_name if is_dir else Path(file_name).stem,
            extension=None if is_dir or not Path(file_name).suffix else Path(file_name).suffix[1:],
            type="dir" if is_dir else "file",
            path=file_path,
            size=item.get("fileSize") if not is_dir else None,
            modify_time=int(item.get("utime") or item.get("updateTime") or 0) or None,
            pickcode=str(item),
        )
        self._cache_item(file_item)
        return file_item

    def _wait_task_done(
        self,
        task_id: str,
        max_try: int = 300,
        interval: int = 1,
        allow_missing: bool = False,
    ) -> bool:
        """
        等待任务完成。
        """
        if not task_id:
            return True

        for index in range(max_try):
            status_response = self.client.get_task_status(task_id)
            status_code = status_response.get("code", -1)
            status_data = status_response.get("data", {}) or {}
            status = status_data.get("status")
            if status == 2:
                return True

            if status in (0, 1, 3, 145, 146, 147, 155, 163) and index < max_try - 1:
                time.sleep(interval)
                continue

            info_response = self.client.get_file_info_by_task_id(task_id)
            info_code = info_response.get("code", -1)
            info_data = info_response.get("data", {}) or {}
            if info_data.get("fileId"):
                return True

            if allow_missing and (self._is_task_missing(status_response) or self._is_task_missing(info_response)):
                logger.info(f"【光鸭云盘】任务 {task_id} 状态已失效，转由后续文件可见性确认结果")
                return True

            message = status_response.get("msg") or info_response.get("msg") or ""
            logger.warning(
                f"【光鸭云盘】任务 {task_id} 未确认完成: status={status} code={status_code}/{info_code} msg={message}"
            )
            return False

        logger.error(f"【光鸭云盘】任务 {task_id} 超时")
        return False

    def _path_to_id(self, path: str) -> str:
        """
        通过路径获取文件 ID。
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
            response = self.client.get_file_list(
                parent_id=current_id,
                page_size=self._page_size,
                order_by=self._order_by,
                sort_type=self._sort_type,
                file_types=[],
            )
            if response.get("code", -1) != 0 and response.get("msg") != "success":
                raise FileNotFoundError(f"【光鸭云盘】{normalized_path} 不存在")
            data = response.get("data", {}) or {}
            items = data.get("list", []) or []
            found = None
            for item in items:
                if item.get("fileName") == part:
                    found = item
                    break
            if not found:
                raise FileNotFoundError(f"【光鸭云盘】{normalized_path} 不存在")
            current_id = str(found.get("fileId", ""))
            current_path = f"{current_path.rstrip('/')}/{part}" if current_path != "/" else f"/{part}"
            self._cache_path_id(current_path, current_id)
            self._build_file_item_from_api(str(Path(current_path).parent).replace("\\", "/") or "/", found)

        return current_id

    def list(self, fileitem: schemas.FileItem) -> List[schemas.FileItem]:
        """
        浏览文件或目录。
        """
        if fileitem.type == "file":
            item = self.detail(fileitem)
            return [item] if item else []

        normalized_dir_path = self._normalize_path(fileitem.path)
        file_id = self._normalize_fileid(fileitem.fileid, normalized_dir_path)
        if normalized_dir_path != "/" and not file_id:
            file_id = self._path_to_id(normalized_dir_path)

        dir_item = schemas.FileItem(
            storage=self._disk_name,
            fileid=file_id,
            parent_fileid=str(fileitem.parent_fileid or ""),
            path="/" if normalized_dir_path == "/" else f"{normalized_dir_path}/",
            name=fileitem.name or ("/" if normalized_dir_path == "/" else Path(normalized_dir_path).name),
            basename=fileitem.basename or ("/" if normalized_dir_path == "/" else Path(normalized_dir_path).name),
            type="dir",
        )
        self._cache_item(dir_item)

        results: List[schemas.FileItem] = []
        page = 0
        while True:
            response = self.client.get_file_list(
                parent_id=file_id,
                page_size=self._page_size,
                order_by=self._order_by,
                sort_type=self._sort_type,
                file_types=[],
                page=page,
            )
            if response.get("code", -1) != 0 and response.get("msg") != "success":
                break
            data = response.get("data", {}) or {}
            item_list = data.get("list", []) or []
            if not item_list:
                break
            for item in item_list:
                results.append(self._build_file_item_from_api(normalized_dir_path, item))
            total = data.get("total") or 0
            if len(item_list) < self._page_size or (total and len(results) >= total):
                break
            page += 1
        return results

    def create_folder(self, fileitem: schemas.FileItem, name: str) -> Optional[schemas.FileItem]:
        """
        创建目录。
        """
        try:
            normalized_parent_path = self._normalize_path(fileitem.path)
            parent_id = self._normalize_fileid(fileitem.fileid, normalized_parent_path)
            if normalized_parent_path != "/" and not parent_id:
                parent_id = self._path_to_id(normalized_parent_path)
            response = self.client.create_dir(parent_id=parent_id, dir_name=name)
            if response.get("msg") != "success" and response.get("code") != 0:
                logger.debug(f"【光鸭云盘】创建目录失败: {response}")
                return None
            data = response.get("data", {}) or {}
            new_path = self._normalize_path(str(Path(normalized_parent_path) / name))
            self._id_cache[new_path] = str(data.get("fileId", ""))
            folder_item = schemas.FileItem(
                storage=self._disk_name,
                fileid=str(data.get("fileId", "")),
                parent_fileid=str(parent_id or ""),
                path=new_path + "/",
                name=name,
                basename=name,
                type="dir",
                modify_time=int(datetime.now().timestamp()),
                pickcode=str(data),
            )
            self._cache_item(folder_item)
            return folder_item
        except Exception as err:
            logger.debug(f"【光鸭云盘】创建目录失败: {err}")
            return None

    def get_folder(self, path: Path) -> Optional[schemas.FileItem]:
        """
        获取目录，不存在则创建。
        """
        folder = self.get_item(path)
        if folder:
            return folder

        current = schemas.FileItem(storage=self._disk_name, path="/", fileid="")
        for part in path.parts[1:]:
            next_folder = None
            for sub_folder in self.list(current):
                if sub_folder.type == "dir" and sub_folder.name == part:
                    next_folder = sub_folder
                    break
            if not next_folder:
                next_folder = self.create_folder(current, part)
            if not next_folder:
                return None
            current = next_folder
        return current

    def get_item(self, path: Path) -> Optional[schemas.FileItem]:
        """
        查询文件或目录。
        """
        normalized = self._normalize_path(str(path))
        if normalized == "/":
            root_item = schemas.FileItem(
                storage=self._disk_name,
                fileid="",
                parent_fileid="",
                path="/",
                name="/",
                basename="/",
                type="dir",
            )
            self._cache_item(root_item)
            return root_item

        cached_item = self._restore_cached_item(normalized)
        if cached_item:
            return cached_item

        try:
            file_id = self._path_to_id(normalized)
        except FileNotFoundError:
            return None

        parent_path = self._normalize_path(str(Path(normalized).parent))
        target_name = Path(normalized).name
        item = self._find_item_in_parent(parent_path=parent_path, name=target_name)
        if item and str(item.fileid or "") == file_id:
            return item
        return None

    def get_parent(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        """
        获取父目录。
        """
        current_path = (fileitem.path or "/").replace("\\", "/")
        normalized_path = self._normalize_path(current_path)
        if normalized_path == "/":
            return self.get_item(Path("/"))

        parent_path = self._normalize_path(str(Path(normalized_path).parent))

        cached_parent = self._restore_cached_item(parent_path)
        if cached_parent and cached_parent.type == "dir":
            return cached_parent

        parent_fileid = str(fileitem.parent_fileid or "")
        grand_parent_fileid = ""
        if parent_path != "/":
            try:
                parent_item = self.get_item(Path(parent_path))
                if parent_item:
                    grand_parent_fileid = str(parent_item.parent_fileid or "")
                    if not parent_fileid:
                        parent_fileid = str(parent_item.fileid or "")
            except Exception:
                pass

        parent_item = schemas.FileItem(
            storage=self._disk_name,
            fileid=parent_fileid,
            parent_fileid=grand_parent_fileid,
            path=parent_path if parent_path == "/" else f"{parent_path.rstrip('/')}/",
            name="/" if parent_path == "/" else Path(parent_path).name,
            basename="/" if parent_path == "/" else Path(parent_path).name,
            type="dir",
        )
        self._cache_item(parent_item)
        return parent_item

    def delete(self, fileitem: schemas.FileItem) -> bool:
        """
        删除文件或目录。
        """
        try:
            response = self.client.delete_file([fileitem.fileid])
            if response.get("msg") != "success" and response.get("code") != 0:
                return False
            task_id = (response.get("data", {}) or {}).get("taskId", "")
            if task_id and not self._wait_task_done(task_id, allow_missing=True):
                return False
            if self._permanently_delete:
                self._schedule_purge_from_recycle(fileitem)
            self._invalidate_path_cache(fileitem.path)
            return True
        except Exception as err:
            logger.debug(f"【光鸭云盘】删除异常: {err}")
            return False

    def rename(self, fileitem: schemas.FileItem, name: str) -> bool:
        """
        重命名文件或目录。
        """
        try:
            response = self.client.rename(file_id=fileitem.fileid, new_name=name)
            if response.get("msg") != "success" and response.get("code") != 0:
                return False
            self._invalidate_path_cache(fileitem.path)
            new_path = self._normalize_path(str(Path(fileitem.path).parent / name))
            renamed_item = schemas.FileItem(
                storage=self._disk_name,
                fileid=str(fileitem.fileid or ""),
                parent_fileid=str(fileitem.parent_fileid or ""),
                path=new_path + ("/" if fileitem.type == "dir" else ""),
                name=name,
                basename=name if fileitem.type == "dir" else Path(name).stem,
                extension=None if fileitem.type == "dir" or not Path(name).suffix else Path(name).suffix[1:],
                type=fileitem.type,
                size=fileitem.size,
                modify_time=int(datetime.now().timestamp()),
                pickcode=fileitem.pickcode,
            )
            self._cache_item(renamed_item)
            return True
        except Exception as err:
            logger.debug(f"【光鸭云盘】重命名异常: {err}")
            return False

    def download(self, fileitem: schemas.FileItem, path: Path = None) -> Optional[Path]:
        """
        下载文件。
        """
        try:
            response = self.client.get_download_url(fileitem.fileid)
            if response.get("msg") != "success" and response.get("code") != 0:
                return None
            data = response.get("data", {}) or {}
            download_url = data.get("signedURL") or data.get("downloadUrl")
            if not download_url:
                return None
            local_path = (path or settings.TEMP_PATH) / fileitem.name
            file_size = fileitem.size
            progress_callback = transfer_process(Path(fileitem.path).as_posix())
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
                if 'local_path' in locals() and local_path.exists():
                    local_path.unlink()
            except Exception:
                pass
            return None

    def upload(
        self,
        target_dir: schemas.FileItem,
        local_path: Path,
        new_name: Optional[str] = None,
    ) -> Optional[schemas.FileItem]:
        """
        上传文件或目录。
        """
        if local_path.is_dir():
            return self.upload_folder(target_dir, local_path)
        return self._upload_single_file_public(target_dir, local_path, new_name)

    def upload_batch(
        self,
        target_dir: schemas.FileItem,
        local_paths: List[Path],
    ) -> List[Optional[schemas.FileItem]]:
        """
        并行上传多个文件。
        """
        if not local_paths:
            return []
        if len(local_paths) == 1:
            return [self._upload_single_file_public(target_dir, local_paths[0])]

        results: List[Optional[schemas.FileItem]] = [None] * len(local_paths)

        def _upload_one(index: int, upload_path: Path):
            return index, self._upload_single_file_public(target_dir, upload_path)

        with ThreadPoolExecutor(max_workers=min(5, len(local_paths))) as executor:
            futures = [executor.submit(_upload_one, index, upload_path) for index, upload_path in enumerate(local_paths)]
            for future in as_completed(futures):
                try:
                    index, result = future.result()
                    results[index] = result
                except Exception as err:
                    logger.error(f"【光鸭云盘】并行上传异常: {err}")
        return results

    def _upload_single_file_public(
        self,
        target_dir: schemas.FileItem,
        local_path: Path,
        new_name: Optional[str] = None,
    ) -> Optional[schemas.FileItem]:
        """
        上传单文件对外包装。
        """
        target_name = new_name or local_path.name
        parent_id = target_dir.fileid or self._path_to_id(target_dir.path)
        return self._upload_single_file(
            folder_id=parent_id,
            local_path=local_path,
            target_dir_path=target_dir.path,
            target_name=target_name,
        )

    def _upload_single_file(
        self,
        folder_id: str,
        local_path: Path,
        target_dir_path: str,
        target_name: str = None,
    ) -> Optional[schemas.FileItem]:
        """
        上传单个文件。
        """
        target_name = target_name or local_path.name
        target_path = Path(target_dir_path) / target_name
        file_size = local_path.stat().st_size
        hash_md5 = md5()
        with open(local_path, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(4096), b""):
                hash_md5.update(chunk)
        file_md5 = hash_md5.hexdigest().upper()

        progress_callback = transfer_process(local_path.as_posix())

        try:
            flash_response = self.client.check_flash_upload(
                task_id="",
                gcid=file_md5,
                file_size=file_size,
                file_name=target_name,
                parent_id=folder_id,
            )
            if flash_response.get("msg") == "success" and flash_response.get("data"):
                data = flash_response.get("data", {}) or {}
                progress_callback(100)
                return schemas.FileItem(
                    storage=self._disk_name,
                    fileid=str(data.get("fileId", "")),
                    path=str(target_path),
                    type="file",
                    name=data.get("fileName", target_name),
                    basename=Path(target_name).stem,
                    extension=Path(target_name).suffix[1:] if Path(target_name).suffix else None,
                    pickcode=str(data),
                    size=file_size,
                    modify_time=int(datetime.now().timestamp()),
                )
        except Exception as err:
            logger.debug(f"【光鸭云盘】秒传检查失败: {err}")

        try:
            response = self.client.get_upload_token(
                file_name=target_name,
                file_size=file_size,
                file_md5=file_md5,
                parent_id=folder_id,
                capacity=2,
            )
            if response.get("code") == 156:
                task_id = (response.get("data", {}) or {}).get("taskId", "")
                if task_id and self._wait_task_done(task_id):
                    task_response = self.client.get_file_info_by_task_id(task_id)
                    data = task_response.get("data", {}) or {}
                    file_id = str(data.get("fileId", ""))
                    if file_id:
                        self._cache_path_id(str(target_path), file_id)
                        progress_callback(100)
                        return schemas.FileItem(
                            storage=self._disk_name,
                            fileid=file_id,
                            path=str(target_path),
                            type="file",
                            name=data.get("fileName", target_name),
                            basename=Path(target_name).stem,
                            extension=Path(target_name).suffix[1:] if Path(target_name).suffix else None,
                            pickcode=str(data),
                            size=file_size,
                            modify_time=int(datetime.now().timestamp()),
                        )
            if response.get("msg") != "success" and response.get("code") != 0:
                return None

            data = response.get("data", {}) or {}
            task_id = data.get("taskId", "")
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
            if task_id and not self._wait_task_done(task_id):
                return None
            task_response = self.client.get_file_info_by_task_id(task_id)
            task_data = task_response.get("data", {}) or {}
            file_id = str(task_data.get("fileId", ""))
            if not file_id:
                return None
            self._cache_path_id(str(target_path), file_id)
            progress_callback(100)
            uploaded_item = schemas.FileItem(
                storage=self._disk_name,
                fileid=file_id,
                path=str(target_path),
                type="file",
                name=task_data.get("fileName", target_name),
                basename=Path(target_name).stem,
                extension=Path(target_name).suffix[1:] if Path(target_name).suffix else None,
                pickcode=str(task_data),
                size=file_size,
                modify_time=int(datetime.now().timestamp()),
            )
            self._cache_item(uploaded_item)
            return uploaded_item
        except Exception as err:
            logger.error(f"【光鸭云盘】上传失败: {target_name} - {err}")
            return None

    def upload_folder(
        self,
        target_dir: schemas.FileItem,
        local_path: Path,
    ) -> Optional[schemas.FileItem]:
        """
        上传目录。
        """
        try:
            folder = self.create_folder(target_dir, local_path.name)
            if not folder:
                return None
            success_count = 0
            fail_count = 0
            for item in local_path.iterdir():
                result = self.upload(folder, item)
                if result:
                    success_count += 1
                else:
                    fail_count += 1
            logger.info(
                f"【光鸭云盘】目录上传完成: {local_path.name}, 成功: {success_count}, 失败: {fail_count}"
            )
            return folder
        except Exception as err:
            logger.error(f"【光鸭云盘】目录上传失败: {local_path.name} - {err}")
            return None

    def detail(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        """
        获取文件详情。
        """
        return self.get_item(Path(fileitem.path))

    def copy(self, fileitem: schemas.FileItem, path: Path, new_name: str) -> bool:
        """
        复制文件或目录。
        """
        try:
            normalized_target_parent = self._normalize_path(str(path))
            target_id = self._path_to_id(normalized_target_parent)
            response = self.client.copy_file([fileitem.fileid], target_id)
            if response.get("msg") != "success" and response.get("code") != 0:
                return False
            task_id = (response.get("data", {}) or {}).get("taskId", "")
            if task_id and not self._wait_task_done(task_id, allow_missing=True):
                return False
            copied_item = self._wait_item_visible(
                parent_path=normalized_target_parent,
                name=fileitem.name,
                expected_type=fileitem.type,
            )
            if not copied_item:
                return False
            if new_name and new_name != fileitem.name:
                return self.rename(copied_item, new_name)
            return True
        except Exception as err:
            logger.debug(f"【光鸭云盘】复制异常: {err}")
            return False

    def move(self, fileitem: schemas.FileItem, path: Path, new_name: str) -> bool:
        """
        移动文件或目录。
        """
        try:
            normalized_target_parent = self._normalize_path(str(path))
            normalized_source_path = self._normalize_path(fileitem.path)
            normalized_source_parent = self._normalize_path(str(Path(normalized_source_path).parent))
            current_name = fileitem.name or Path(normalized_source_path).name
            target_name = new_name or current_name

            if normalized_target_parent == normalized_source_parent:
                if target_name == current_name:
                    logger.info(
                        f"【光鸭云盘】跳过同目录移动空操作: {normalized_source_path} -> {normalized_target_parent}"
                    )
                    return True
                return self.rename(fileitem, target_name)

            target_id = self._path_to_id(normalized_target_parent)
            response = self.client.move_file([fileitem.fileid], target_id)
            if response.get("msg") != "success" and response.get("code") != 0:
                return False
            task_id = (response.get("data", {}) or {}).get("taskId", "")
            if task_id and not self._wait_task_done(task_id, allow_missing=True):
                return False
            self._invalidate_path_cache(fileitem.path)
            moved_item = self._wait_item_visible(
                parent_path=normalized_target_parent,
                name=fileitem.name,
                expected_type=fileitem.type,
            )
            if not moved_item:
                return False
            if target_name != fileitem.name:
                return self.rename(moved_item, target_name)
            return True
        except Exception as err:
            logger.debug(f"【光鸭云盘】移动异常: {err}")
            return False

    def link(self, _fileitem: schemas.FileItem, _target_file: Path) -> bool:
        _ = (_fileitem, _target_file)
        return False

    def softlink(self, _fileitem: schemas.FileItem, _target_file: Path) -> bool:
        _ = (_fileitem, _target_file)
        return False

    def usage(self) -> Optional[schemas.StorageUsage]:
        """
        获取存储使用情况。
        """
        try:
            response = self.client.get_assets()
            if response.get("msg") != "success" and response.get("code") != 0:
                return None
            data = response.get("data", {}) or {}
            total = data.get("totalSpaceSize", 0) or 0
            used = data.get("usedSpaceSize")
            if used is None:
                return schemas.StorageUsage(total=total, available=0)
            return schemas.StorageUsage(total=total, available=total - used if total else 0)
        except Exception as err:
            logger.debug(f"【光鸭云盘】获取空间信息异常: {err}")
            return None

    def support_transtype(self) -> dict:
        """
        支持的整理方式。
        """
        return self.transtype

    def is_support_transtype(self, transtype: str) -> bool:
        """
        判断是否支持整理方式。
        """
        return transtype in self.transtype
