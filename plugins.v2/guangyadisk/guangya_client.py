"""
光鸭云盘 HTTP 客户端
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Callable, Dict, Optional

import oss2
import requests

from app.log import logger


class GuangYaClient:
    """
    光鸭云盘 HTTP 客户端。
    """

    ACCOUNT_BASE_URL = "https://account.guangyapan.com"
    API_BASE_URL = "https://api.guangyapan.com"
    DEFAULT_CLIENT_ID = "aMe-8VSlkrbQXpUR"

    @staticmethod
    def _mask_token(token: Optional[str], keep: int = 10) -> str:
        """
        脱敏显示 token。
        """
        if not token:
            return ""
        token = str(token)
        if len(token) <= keep * 2:
            return token
        return f"{token[:keep]}...{token[-keep:]}"

    def __init__(
        self,
        access_token: str = None,
        refresh_token: str = None,
        client_id: str = None,
        device_id: str = None,
        on_token_refresh: Callable[[str, str], None] = None,
    ):
        """
        初始化客户端。
        """
        self._access_token = (access_token or "").strip()
        self._refresh_token = (refresh_token or "").strip()
        self._client_id = (client_id or self.DEFAULT_CLIENT_ID).strip() or self.DEFAULT_CLIENT_ID
        self._device_id = self._normalize_device_id(device_id) or self._generate_device_id()
        self._on_token_refresh = on_token_refresh
        self._last_refresh_attempted = False
        self._last_refresh_invalid = False
        self._last_refresh_result: Dict[str, Any] = {}
        self._session = requests.Session()
        self._session.headers.update(self._build_common_headers())

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def last_refresh_attempted(self) -> bool:
        return self._last_refresh_attempted

    @property
    def last_refresh_invalid(self) -> bool:
        return self._last_refresh_invalid

    @property
    def last_refresh_result(self) -> Dict[str, Any]:
        return self._last_refresh_result

    @staticmethod
    def _generate_device_id() -> str:
        """
        生成设备 ID。
        """
        return uuid.uuid4().hex

    @staticmethod
    def _normalize_device_id(device_id: Optional[str]) -> str:
        """
        规范化设备 ID。
        """
        if not device_id:
            return ""
        return str(device_id).replace("-", "").strip()

    def _build_common_headers(self) -> Dict[str, str]:
        """
        构建公共请求头。
        """
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Referer": "https://www.guangyupan.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN",
            "X-Client-Id": self._client_id,
            "X-Client-Version": "0.0.1",
            "X-Device-Id": self._device_id,
            "X-Device-Model": "chrome%2F147.0.0.0",
            "X-Device-Name": "PC-Chrome",
            "X-Device-Sign": f"wdi10.{self._device_id}xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "X-Net-Work-Type": "NONE",
            "X-Os-Version": "Win32",
            "X-Platform-Version": "1",
            "X-Protocol-Version": "301",
            "X-Provider-Name": "NONE",
            "X-Sdk-Version": "9.0.2",
        }

    @staticmethod
    def _is_auth_invalid_result(result: Dict[str, Any]) -> bool:
        if not isinstance(result, dict):
            return False
        combined = " ".join(
            [
                str(result.get("error") or ""),
                str(result.get("msg") or ""),
                str(result.get("error_description") or ""),
                str(result),
            ]
        )
        keywords = [
            "unauthenticated",
            "无效token",
            "authorize failed",
            "认证失败",
            "invalid_grant",
            "invalid token",
            "invalid_token",
            "token expiry",
        ]
        combined_lower = combined.lower()
        return any(keyword.lower() in combined_lower for keyword in keywords)

    def _get_auth_headers(self, use_access_token: bool = True) -> Dict[str, str]:
        """
        获取认证头。
        """
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Did": self._device_id,
            "Dt": "4",
            "did": self._device_id,
            "dt": "4",
        }
        if use_access_token and self._access_token:
            headers["accessToken"] = self._access_token
        return headers

    def _request(
        self,
        method: str,
        url: str,
        data: dict = None,
        headers: dict = None,
        need_auth: bool = True,
        retry_on_401: bool = True,
        treat_http_error_as_response: bool = False,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求。
        """
        req_headers = self._session.headers.copy()
        if headers:
            req_headers.update(headers)
        if need_auth and self._access_token:
            req_headers.update(self._get_auth_headers())

        if need_auth:
            logger.debug(
                "【光鸭云盘】发起请求: %s %s, device_id=%s, access_token=%s, refresh_token=%s",
                method.upper(),
                url,
                self._device_id,
                self._mask_token(self._access_token),
                self._mask_token(self._refresh_token),
            )

        try:
            if method.upper() == "GET":
                response = self._session.get(url, headers=req_headers, params=data, timeout=timeout)
            elif method.upper() == "PUT":
                response = self._session.put(url, headers=req_headers, data=data, timeout=timeout)
            else:
                response = self._session.post(url, headers=req_headers, json=data, timeout=timeout)
            response.raise_for_status()
            if not response.text:
                return {"msg": "success", "code": 0}
            return response.json()
        except requests.exceptions.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else None
            if treat_http_error_as_response and err.response is not None:
                try:
                    return err.response.json()
                except Exception:
                    return {
                        "msg": "error",
                        "code": status_code or -1,
                        "error": err.response.text[:500] if err.response.text else str(err),
                    }
            if status_code == 401 and retry_on_401 and need_auth:
                logger.info(
                    "【光鸭云盘】Token 失效，尝试刷新: access_token=%s, refresh_token=%s, device_id=%s",
                    self._mask_token(self._access_token),
                    self._mask_token(self._refresh_token),
                    self._device_id,
                )
                if self.refresh_access_token():
                    return self._request(
                        method=method,
                        url=url,
                        data=data,
                        headers=headers,
                        need_auth=need_auth,
                        retry_on_401=False,
                        treat_http_error_as_response=treat_http_error_as_response,
                        timeout=timeout,
                    )
            detail = f"{status_code} {err.response.reason}" if err.response is not None else str(err)
            try:
                if err.response is not None and err.response.text:
                    detail = f"{detail} - {err.response.text[:500]}"
            except Exception:
                pass
            logger.error(f"【光鸭云盘】请求失败: {url} - {detail}")
            return {"msg": "error", "code": -1, "error": detail}
        except requests.exceptions.RequestException as err:
            logger.error(f"【光鸭云盘】请求失败: {url} - {err}")
            return {"msg": "error", "code": -1, "error": str(err)}

    def get_device_code(self) -> Optional[Dict[str, Any]]:
        """
        获取设备码与二维码。
        """
        result = self._request(
            method="POST",
            url=f"{self.ACCOUNT_BASE_URL}/v1/auth/device/code",
            data={
                "scope": "user",
                "client_id": self._client_id,
            },
            need_auth=False,
        )
        if result.get("error"):
            return None
        return result

    def poll_device_code(self, device_code: str) -> Optional[Dict[str, Any]]:
        """
        轮询设备码状态。
        """
        result = self._request(
            method="POST",
            url=f"{self.ACCOUNT_BASE_URL}/v1/auth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": self._client_id,
            },
            need_auth=False,
            treat_http_error_as_response=True,
        )
        if result.get("error") == "authorization_pending":
            return {"waiting": True, "message": "等待扫码中..."}
        if result.get("access_token"):
            self._access_token = result.get("access_token") or ""
            self._refresh_token = result.get("refresh_token") or ""
            return result
        return None

    def refresh_access_token(self) -> bool:
        """
        刷新访问令牌。
        """
        self._last_refresh_attempted = True
        self._last_refresh_invalid = False
        self._last_refresh_result = {}
        if not self._refresh_token:
            self._last_refresh_invalid = True
            self._last_refresh_result = {"error": "missing_refresh_token", "msg": "refresh_token 为空"}
            logger.warning("【光鸭云盘】刷新失败：refresh_token 为空")
            return False
        old_access_token = self._access_token
        old_refresh_token = self._refresh_token
        result = self._request(
            method="POST",
            url=f"{self.ACCOUNT_BASE_URL}/v1/auth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
            },
            need_auth=False,
        )
        self._last_refresh_result = result if isinstance(result, dict) else {"result": result}
        if result.get("access_token"):
            self._access_token = result.get("access_token") or ""
            self._refresh_token = result.get("refresh_token") or self._refresh_token
            self._last_refresh_invalid = False
            logger.info(
                "【光鸭云盘】Token 刷新成功: access_token %s -> %s, refresh_token %s -> %s",
                self._mask_token(old_access_token),
                self._mask_token(self._access_token),
                self._mask_token(old_refresh_token),
                self._mask_token(self._refresh_token),
            )
            if self._on_token_refresh:
                try:
                    self._on_token_refresh(self._access_token, self._refresh_token)
                except Exception as err:
                    logger.error(f"【光鸭云盘】Token 刷新回调失败: {err}")
            return True
        self._last_refresh_invalid = self._is_auth_invalid_result(result)
        logger.warning(
            "【光鸭云盘】Token 刷新失败: device_id=%s, refresh_token=%s, auth_invalid=%s, response=%s",
            self._device_id,
            self._mask_token(old_refresh_token),
            self._last_refresh_invalid,
            result,
        )
        return False

    def get_user_info(self) -> Dict[str, Any]:
        """
        获取用户信息。
        """
        return self._request("GET", f"{self.ACCOUNT_BASE_URL}/v1/user/me")

    def get_assets(self) -> Dict[str, Any]:
        """
        获取空间信息。
        """
        return self._request("POST", f"{self.API_BASE_URL}/nd.bizassets.s/v1/get_assets", data={})

    def get_file_list(
        self,
        parent_id: str = "",
        page_size: int = 100,
        order_by: int = 3,
        sort_type: int = 1,
        file_types: list = None,
        page: int = 0,
        dir_type: int = None,
    ) -> Dict[str, Any]:
        """
        获取文件列表。
        """
        data = {
            "parentId": parent_id or "",
            "page": page,
            "pageSize": page_size,
            "orderBy": order_by,
            "sortType": sort_type,
            "fileTypes": file_types or [],
        }
        if dir_type is not None:
            data["dirType"] = dir_type
        return self._request(
            method="POST",
            url=f"{self.API_BASE_URL}/nd.bizuserres.s/v1/file/get_file_list",
            data=data,
        )

    def create_dir(self, parent_id: str, dir_name: str, fail_if_exist: bool = True) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/file/create_dir",
            data={
                "parentId": parent_id or "",
                "dirName": dir_name,
                "failIfNameExist": fail_if_exist,
            },
        )

    def rename(self, file_id: str, new_name: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/file/rename",
            data={"fileId": file_id, "newName": new_name},
        )

    def delete_file(self, file_ids: list) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/file/delete_file",
            data={"fileIds": file_ids},
        )

    def move_file(self, file_ids: list, target_parent_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/file/move_file",
            data={"fileIds": file_ids, "parentId": target_parent_id},
        )

    def copy_file(self, file_ids: list, target_parent_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/file/copy_file",
            data={"fileIds": file_ids, "parentId": target_parent_id},
        )

    def get_download_url(self, file_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/get_res_download_url",
            data={"fileId": file_id},
        )

    def get_upload_token(
        self,
        file_name: str,
        file_size: int,
        file_md5: str,
        parent_id: str = "",
        capacity: int = 1,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/get_res_center_token",
            data={
                "capacity": capacity,
                "name": file_name,
                "res": {"fileSize": file_size, "md5": file_md5},
                "parentId": parent_id or "",
            },
        )

    def check_flash_upload(
        self,
        task_id: str,
        gcid: str,
        file_size: int = None,
        file_name: str = None,
        parent_id: str = None,
    ) -> Dict[str, Any]:
        data = {"taskId": task_id, "gcid": gcid}
        if file_size is not None:
            data["fileSize"] = file_size
        if file_name:
            data["name"] = file_name
        if parent_id is not None:
            data["parentId"] = parent_id
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/check_can_flash_upload",
            data=data,
        )

    def get_resume_token(self, task_id: str, file_size: int) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/get_res_center_resume_token",
            data={
                "capacity": 2,
                "res": {"fileSize": file_size},
                "taskId": task_id,
            },
        )

    def get_file_info_by_task_id(self, task_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/file/get_info_by_task_id",
            data={"taskId": task_id},
        )

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{self.API_BASE_URL}/nd.bizuserres.s/v1/get_task_status",
            data={"taskId": task_id},
        )

    def upload_file_multipart(
        self,
        endpoint: str,
        bucket_name: str,
        object_path: str,
        file_path: str,
        oss_access_key_id: str,
        oss_access_key_secret: str,
        security_token: str,
        progress_callback: Callable = None,
    ) -> Optional[str]:
        """
        使用 OSS SDK 分片上传。
        """
        try:
            if not endpoint.startswith("http"):
                endpoint = f"https://{endpoint}"
            auth = oss2.StsAuth(oss_access_key_id, oss_access_key_secret, security_token)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            result = oss2.resumable_upload(
                bucket,
                object_path,
                file_path,
                part_size=5 * 1024 * 1024,
                progress_callback=progress_callback,
            )
            return result.etag if hasattr(result, "etag") else str(result)
        except Exception as err:
            logger.error(f"【光鸭云盘】OSS 分片上传失败: {err}")
            return None
