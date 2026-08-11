"""
MoviePilot-Tools 扩展服务端同步插件。

为 Chrome 扩展 MoviePilot-Tools-2.0 提供插件数据目录文件读写端点：
  POST /api/v1/plugin/MoviePilotTools/upload
  GET  /api/v1/plugin/MoviePilotTools/download

落盘：settings.PLUGIN_DATA_PATH / MoviePilotTools / {user}/...
敏感项（Token/PIN/密钥）由扩展侧过滤，本插件不做业务识别。
"""
from __future__ import annotations

import asyncio
import base64
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

from fastapi import Body, Query
from fastapi.responses import JSONResponse

from app.chain.download import DownloadChain  # pyright: ignore[reportMissingImports]
from app.core.config import settings  # pyright: ignore[reportMissingImports]
from app.helper.directory import validate_download_save_path  # pyright: ignore[reportMissingImports]
from app.log import logger  # pyright: ignore[reportMissingImports]
from torrentool.api import Torrent  # pyright: ignore[reportMissingImports]
from app.plugins import _PluginBase  # pyright: ignore[reportMissingImports]

# 相对路径：Unicode 字母数字、下划线、短横、点、斜杠；禁止绝对路径与 ..
_SAFE_PATH_RE = re.compile(r"^[\w\-.\/]+$", re.UNICODE)
# 默认允许的后缀（MoviePilot-Tools 2.0 备份文件）
_DEFAULT_SUFFIXES = {
    ".mpt2",  # 2.0 加密备份主文件（backup.mpt2）
    ".json",  # 备份清单 manifest.json
}
# 路径中禁止出现的敏感文件名片段（扩展本就不该同步，双保险）
_BLOCKED_NAME_PARTS = (
    "token",
    "password",
    "passwd",
    "secret",
    "pin",
    "master_key",
    "private",
    "credential_key",
)


class MoviePilotTools(_PluginBase):
    # 插件名称
    plugin_name = "MoviePilot Tools 同步"
    # 插件描述
    plugin_desc = "为 MoviePilot-Tools 扩展提供服务端文件同步与直接下载能力。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/LocalPluginInstall.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "moviepilottools_"
    # 加载顺序
    plugin_order = 5
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enabled = False
    _max_file_size = 150 * 1024 * 1024  # 150MB
    _allowed_suffixes: List[str] = list(_DEFAULT_SUFFIXES)
    _direct_download_enabled = False
    _max_torrent_size = 10 * 1024 * 1024  # 10MB

    def init_plugin(self, config: Optional[Dict[str, Any]] = None) -> None:
        """初始化插件配置。"""
        cfg = config or {}
        self._enabled = bool(cfg.get("enabled", False))
        try:
            size_mb = float(cfg.get("max_file_size_mb", 150) or 150)
        except (TypeError, ValueError):
            size_mb = 150
        self._max_file_size = max(1, int(size_mb * 1024 * 1024))

        self._direct_download_enabled = bool(cfg.get("direct_download_enabled", False))
        try:
            torrent_size_mb = float(cfg.get("max_torrent_size_mb", 10) or 10)
        except (TypeError, ValueError):
            torrent_size_mb = 10
        self._max_torrent_size = max(1, int(torrent_size_mb * 1024 * 1024))

        raw_suffix = cfg.get("allowed_suffixes") or ""
        if isinstance(raw_suffix, str) and raw_suffix.strip():
            suffixes = []
            for item in raw_suffix.replace("\n", ",").split(","):
                s = item.strip().lower()
                if not s:
                    continue
                if not s.startswith("."):
                    s = f".{s}"
                suffixes.append(s)
            self._allowed_suffixes = suffixes or list(_DEFAULT_SUFFIXES)
        else:
            self._allowed_suffixes = list(_DEFAULT_SUFFIXES)

        # 确保数据目录存在
        data_path = self.get_data_path()
        logger.info(
            f"{self.plugin_name}: {'已启用' if self._enabled else '未启用'}，"
            f"数据目录={data_path}，单文件上限={self._max_file_size} bytes，"
            f"直接下载={'已启用' if self._direct_download_enabled else '未启用'}，"
            f"种子上限={self._max_torrent_size} bytes"
        )

    def get_state(self) -> bool:
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_page(self) -> List[dict]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        return []

    def stop_service(self):
        """无后台任务，无需清理。"""
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册扩展同步 API。
        auth=bear：扩展携带登录 JWT（Authorization: Bearer），亦可回退 API Token。
        最终路径：
          /api/v1/plugin/MoviePilotTools/upload
          /api/v1/plugin/MoviePilotTools/download
          /api/v1/plugin/MoviePilotTools/list
          /api/v1/plugin/MoviePilotTools/delete
          /api/v1/plugin/MoviePilotTools/download/direct
          /api/v1/plugin/MoviePilotTools/health
        """
        return [
            {
                "path": "/upload",
                "endpoint": self.api_upload,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "上传/覆盖同步文件",
                "description": "将扩展数据文件写入插件数据目录，body: {path, content, encoding?}",
            },
            {
                "path": "/upload_chunk",
                "endpoint": self.api_upload_chunk,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "分块上传同步文件",
                "description": "逐块上传并在最后一块原子合并，body: {path, upload_id, index, total, content}",
            },
            {
                "path": "/download",
                "endpoint": self.api_download,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "下载同步文件",
                "description": "从插件数据目录读取文件，query: path=相对路径",
            },
            {
                "path": "/download_chunk",
                "endpoint": self.api_download_chunk,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "分块下载同步文件",
                "description": "按字节偏移读取文件，query: path, offset, size",
            },
            {
                "path": "/list",
                "endpoint": self.api_list,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "列出同步文件",
                "description": "列出数据目录文件，query: prefix=可选子路径",
            },
            {
                "path": "/delete",
                "endpoint": self.api_delete,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "删除同步文件",
                "description": "删除数据目录中的文件，body: {path}",
            },
            {
                "path": "/download/direct",
                "endpoint": self.api_download_direct,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "直接添加下载任务",
                "description": "跳过媒体识别，提交磁力链接或 base64 种子文件到 MoviePilot 下载器",
            },
            {
                "path": "/health",
                "endpoint": self.api_health,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "健康检查",
                "description": "检查插件启用状态、数据目录与直接下载能力",
            },
        ]

    # ------------------------------------------------------------------
    # API handlers
    # ------------------------------------------------------------------

    async def api_health(self) -> JSONResponse:
        data_path = self.get_data_path()
        return self._ok(
            {
                "enabled": self.get_state(),
                "data_path": str(data_path),
                "max_file_size": self._max_file_size,
                "allowed_suffixes": self._allowed_suffixes,
                "plugin_version": self.plugin_version,
                "capabilities": {
                    "direct_download": self._direct_download_enabled,
                    "direct_download_types": ["magnet", "torrent"],
                    "max_torrent_size": self._max_torrent_size,
                },
            }
        )

    async def api_download_direct(
        self, payload: Dict[str, Any] = Body(...)
    ) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")
        if not self._direct_download_enabled:
            return self._err(403, "直接下载功能未启用")

        body = payload or {}
        content_type = str(body.get("type") or "").strip().lower()
        content = body.get("content")
        downloader = str(body.get("downloader") or "").strip() or None
        save_path = str(body.get("save_path") or "").strip()
        labels = self._merge_download_labels(body.get("labels") or body.get("label"))

        if content_type not in ("magnet", "torrent"):
            return self._err(400, "type 仅支持 magnet 或 torrent")
        if not isinstance(content, str) or not content.strip():
            return self._err(400, "缺少 content 参数")
        if not save_path:
            return self._err(400, "缺少 save_path，请从 MoviePilot 可用下载路径中选择")

        try:
            download_dir = Path(validate_download_save_path(save_path))
        except (TypeError, ValueError) as e:
            return self._err(400, f"下载保存路径无效: {e}")

        if content_type == "magnet":
            direct_content: str | bytes = content.strip()
            if not re.match(
                r"^magnet:\?[^#]*\bxt=urn:btih:(?:[A-Fa-f0-9]{40}|[A-Za-z2-7]{32})(?:&|$)",
                direct_content,
                re.IGNORECASE,
            ):
                return self._err(400, "磁力链接无效或缺少合法 BTIH")
        else:
            try:
                direct_content = base64.b64decode(content, validate=True)
            except Exception:
                return self._err(400, "种子文件 base64 解码失败")
            if not direct_content:
                return self._err(400, "种子文件内容为空")
            if len(direct_content) > self._max_torrent_size:
                return self._err(
                    413,
                    f"种子文件超过大小限制：{self._max_torrent_size / 1024 / 1024:.1f}MB",
                )
            try:
                torrent = Torrent.from_string(direct_content)  # pyright: ignore[reportArgumentType]
                if not torrent.name:
                    return self._err(400, "种子文件缺少有效名称")
            except Exception as e:
                return self._err(400, f"种子文件格式无效: {e}")

        try:
            result = await asyncio.to_thread(
                DownloadChain().download,
                content=direct_content,
                download_dir=download_dir,
                cookie=None,
                label=labels,
                downloader=downloader,
            )
            if not result:
                return self._err(502, "未找到可用下载器")

            downloader_name, download_id, layout, error_message = result
            if not download_id:
                return self._err(502, error_message or "下载器未返回任务标识")

            logger.info(
                f"{self.plugin_name}: 直接下载任务添加成功 "
                f"type={content_type}, downloader={downloader_name}, id={download_id}"
            )
            return self._ok(
                {
                    "success": True,
                    "download_id": download_id,
                    "downloader": downloader_name,
                    "layout": layout,
                    "save_path": str(download_dir),
                },
                message="任务添加成功",
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 直接下载失败: {e}", exc_info=True)
            return self._err(500, f"直接下载失败: {e}")

    async def api_upload(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        body = payload or {}
        rel_path = str(body.get("path") or "").strip()
        content = body.get("content")
        encoding = str(body.get("encoding") or "utf-8").strip().lower()
        updated_at = body.get("updatedAt") or body.get("updated_at")

        if content is None:
            return self._err(400, "缺少 content 参数")
        if not isinstance(content, str):
            return self._err(400, "content 必须为字符串（文本或 base64）")

        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)

        try:
            if encoding in ("base64", "b64"):
                try:
                    raw = base64.b64decode(content, validate=False)
                except Exception as e:
                    return self._err(400, f"base64 解码失败: {e}")
            else:
                raw = content.encode("utf-8")

            if len(raw) > self._max_file_size:
                return self._err(
                    400,
                    f"文件超过大小限制：{self._max_file_size / 1024 / 1024:.1f}MB",
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            # 原子写：先写临时文件再替换
            tmp = target.with_suffix(target.suffix + f".tmp.{int(time.time() * 1000)}")
            tmp.write_bytes(raw)
            tmp.replace(target)

            # 可选：按客户端 updatedAt 回写 mtime（秒）
            if updated_at is not None:
                try:
                    ts = float(updated_at)
                    # 兼容毫秒时间戳
                    if ts > 1e12:
                        ts = ts / 1000.0
                    import os

                    os.utime(target, (ts, ts))
                except (TypeError, ValueError, OSError):
                    pass

            stat = target.stat()
            logger.info(f"{self.plugin_name}: 上传成功 {rel_path} ({stat.st_size} bytes)")
            return self._ok(
                {
                    "path": self._to_posix(rel_path),
                    "size": stat.st_size,
                    "updatedAt": int(stat.st_mtime * 1000),
                },
                message="上传成功",
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 上传失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"上传失败: {e}")

    async def api_upload_chunk(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        """分块上传：每块独立小请求，最后一块到达后原子合并为目标文件。"""
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        body = payload or {}
        rel_path = str(body.get("path") or "").strip()
        upload_id = str(body.get("upload_id") or "").strip()
        content = body.get("content")
        updated_at = body.get("updatedAt") or body.get("updated_at")
        raw_index = body.get("index")
        raw_total = body.get("total")
        if raw_index is None or raw_total is None:
            return self._err(400, "缺少 index/total 参数")
        try:
            index = int(raw_index)
            total = int(raw_total)
        except (TypeError, ValueError):
            return self._err(400, "index/total 必须为整数")

        if not upload_id or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", upload_id):
            return self._err(400, "upload_id 无效")
        if not isinstance(content, str):
            return self._err(400, "content 必须为 base64 字符串")
        if total < 1 or index < 0 or index >= total or total > 10000:
            return self._err(400, "分块序号无效")

        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)

        try:
            raw = base64.b64decode(content, validate=False)
            if len(raw) > min(self._max_file_size, 1024 * 1024):
                return self._err(400, "单个分块不能超过 1MB")

            chunk_dir = self.get_data_path() / ".chunks" / upload_id
            chunk_dir.mkdir(parents=True, exist_ok=True)
            meta_file = chunk_dir / "meta.txt"
            expected_meta = f"{self._to_posix(rel_path)}\n{total}"
            if meta_file.exists() and meta_file.read_text("utf-8") != expected_meta:
                return self._err(409, "upload_id 已被其他上传任务占用")
            meta_file.write_text(expected_meta, encoding="utf-8")
            (chunk_dir / f"{index:06d}.part").write_bytes(raw)

            parts = [chunk_dir / f"{i:06d}.part" for i in range(total)]
            if not all(part.exists() for part in parts):
                return self._ok({"path": self._to_posix(rel_path), "index": index, "total": total})

            size = sum(part.stat().st_size for part in parts)
            if size > self._max_file_size:
                self._remove_tree(chunk_dir)
                return self._err(
                    400,
                    f"文件超过大小限制：{self._max_file_size / 1024 / 1024:.1f}MB",
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + f".tmp.{int(time.time() * 1000)}")
            with tmp.open("wb") as output:
                for part in parts:
                    with part.open("rb") as source:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            output.write(block)
            tmp.replace(target)
            self._remove_tree(chunk_dir)

            if updated_at is not None:
                try:
                    import os
                    ts = float(updated_at)
                    if ts > 1e12:
                        ts = ts / 1000.0
                    os.utime(target, (ts, ts))
                except (TypeError, ValueError, OSError):
                    pass

            stat = target.stat()
            logger.info(f"{self.plugin_name}: 分块上传成功 {rel_path} ({stat.st_size} bytes)")
            return self._ok(
                {
                    "path": self._to_posix(rel_path),
                    "size": stat.st_size,
                    "updatedAt": int(stat.st_mtime * 1000),
                    "completed": True,
                },
                message="上传成功",
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 分块上传失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"分块上传失败: {e}")

    async def api_download(
        self,
        path: str = Query(..., description="相对路径，如 user/settings.json"),
        encoding: str = Query("utf-8", description="utf-8 或 base64"),
    ) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        rel_path = unquote(str(path or "").strip())
        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)

        if not target.exists() or not target.is_file():
            return self._err(404, "文件不存在")

        try:
            raw = target.read_bytes()
            enc = (encoding or "utf-8").strip().lower()
            if enc in ("base64", "b64"):
                content = base64.b64encode(raw).decode("ascii")
                content_encoding = "base64"
            else:
                # 文本优先 utf-8，失败回退 latin-1 保真
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    content = base64.b64encode(raw).decode("ascii")
                    content_encoding = "base64"
                else:
                    content_encoding = "utf-8"

            stat = target.stat()
            # 顶层 content 字段兼容扩展 core/mp-backend.ts 的 res.data?.content
            return JSONResponse(
                status_code=200,
                content={
                    "code": 200,
                    "message": "ok",
                    "content": content,
                    "encoding": content_encoding,
                    "path": self._to_posix(rel_path),
                    "size": stat.st_size,
                    "updatedAt": int(stat.st_mtime * 1000),
                    "data": {
                        "content": content,
                        "encoding": content_encoding,
                        "path": self._to_posix(rel_path),
                        "size": stat.st_size,
                        "updatedAt": int(stat.st_mtime * 1000),
                    },
                },
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 下载失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"下载失败: {e}")

    async def api_download_chunk(
        self,
        path: str = Query(..., description="相对路径"),
        offset: int = Query(0, ge=0, description="字节偏移"),
        size: int = Query(256 * 1024, ge=1, le=1024 * 1024, description="读取字节数"),
    ) -> JSONResponse:
        """分块下载：避免大文件响应体触发代理限制。"""
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        rel_path = unquote(str(path or "").strip())
        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)
        if not target.exists() or not target.is_file():
            return self._err(404, "文件不存在")

        try:
            total = target.stat().st_size
            with target.open("rb") as file:
                file.seek(min(offset, total))
                raw = file.read(size)
            next_offset = min(offset + len(raw), total)
            return self._ok(
                {
                    "path": self._to_posix(rel_path),
                    "content": base64.b64encode(raw).decode("ascii"),
                    "offset": offset,
                    "next_offset": next_offset,
                    "total": total,
                    "done": next_offset >= total,
                }
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 分块下载失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"分块下载失败: {e}")

    async def api_list(
        self,
        prefix: str = Query("", description="可选子目录前缀，如 username"),
    ) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        base = self.get_data_path()
        prefix = unquote(str(prefix or "").strip()).lstrip("/").replace("\\", "/")

        if prefix:
            ok, root, message = self._resolve_safe_path(prefix, allow_dir=True)
            if not ok or root is None:
                return self._err(400, message)
        else:
            root = base

        if not root.exists():
            return self._ok({"files": [], "prefix": prefix})

        files: List[Dict[str, Any]] = []
        try:
            if root.is_file():
                rel = root.relative_to(base).as_posix()
                stat = root.stat()
                files.append(
                    {
                        "path": rel,
                        "size": stat.st_size,
                        "updatedAt": int(stat.st_mtime * 1000),
                        "is_dir": False,
                    }
                )
            else:
                for p in sorted(root.rglob("*")):
                    if not p.is_file():
                        continue
                    # 跳过临时文件
                    if ".tmp." in p.name:
                        continue
                    try:
                        rel = p.relative_to(base).as_posix()
                        stat = p.stat()
                        files.append(
                            {
                                "path": rel,
                                "size": stat.st_size,
                                "updatedAt": int(stat.st_mtime * 1000),
                                "is_dir": False,
                            }
                        )
                    except ValueError:
                        continue
            return self._ok({"files": files, "prefix": prefix, "count": len(files)})
        except Exception as e:
            logger.error(f"{self.plugin_name}: 列表失败: {e}", exc_info=True)
            return self._err(500, f"列表失败: {e}")

    async def api_delete(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        rel_path = str((payload or {}).get("path") or "").strip()
        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)

        if not target.exists():
            return self._err(404, "文件不存在")
        if not target.is_file():
            return self._err(400, "仅支持删除文件")

        try:
            target.unlink()
            # 清理空父目录（不越过数据根）
            self._cleanup_empty_parents(target.parent)
            logger.info(f"{self.plugin_name}: 已删除 {rel_path}")
            return self._ok({"path": self._to_posix(rel_path)}, message="删除成功")
        except Exception as e:
            logger.error(f"{self.plugin_name}: 删除失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"删除失败: {e}")

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_download_labels(labels: Any) -> Optional[str]:
        if isinstance(labels, list):
            items = [str(item).strip() for item in labels if str(item).strip()]
        else:
            items = [
                item.strip()
                for item in str(labels or "").replace("\n", ",").split(",")
                if item.strip()
            ]
        system_tag = str(settings.TORRENT_TAG or "").strip()
        if system_tag and system_tag not in items:
            items.append(system_tag)
        return ",".join(dict.fromkeys(items)) if items else None

    def _resolve_safe_path(
        self, rel_path: str, allow_dir: bool = False
    ) -> Tuple[bool, Optional[Path], str]:
        """
        将相对路径解析到插件数据目录内，防目录穿越。
        返回 (ok, absolute_path, error_message)
        """
        if not rel_path:
            return False, None, "缺少 path 参数"

        # 统一分隔符、去掉前导 /
        cleaned = unquote(rel_path).replace("\\", "/").strip()
        cleaned = cleaned.lstrip("/")
        if not cleaned:
            return False, None, "path 无效"
        if cleaned.startswith("..") or "/../" in f"/{cleaned}/" or cleaned.endswith("/.."):
            return False, None, "path 不允许包含 .."
        if cleaned.startswith("~") or ":" in cleaned.split("/")[0]:
            return False, None, "path 不允许为绝对路径"
        if not _SAFE_PATH_RE.match(cleaned):
            return False, None, "path 含非法字符，仅允许字母数字 _ - . /"

        # 敏感名拦截
        lower_parts = [p.lower() for p in cleaned.split("/") if p]
        for part in lower_parts:
            for blocked in _BLOCKED_NAME_PARTS:
                if blocked in part:
                    return False, None, f"禁止同步敏感路径片段: {part}"

        base = self.get_data_path().resolve()
        target = (base / cleaned).resolve()

        # 必须在 base 内
        try:
            target.relative_to(base)
        except ValueError:
            return False, None, "path 越界，拒绝访问"

        if not allow_dir:
            # 文件必须有后缀，且在白名单
            suffix = target.suffix.lower()
            if not suffix:
                return False, None, "path 必须包含合法文件后缀"
            if suffix not in self._allowed_suffixes:
                return False, None, f"不支持的文件类型: {suffix}"

        return True, target, ""

    @staticmethod
    def _remove_tree(directory: Path) -> None:
        if not directory.exists():
            return
        for path in sorted(directory.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        directory.rmdir()

    def _cleanup_empty_parents(self, directory: Path) -> None:
        base = self.get_data_path().resolve()
        try:
            current = directory.resolve()
            while current != base and base in current.parents:
                if current.exists() and current.is_dir() and not any(current.iterdir()):
                    current.rmdir()
                    current = current.parent
                else:
                    break
        except Exception:
            pass

    @staticmethod
    def _to_posix(path: str) -> str:
        return str(path or "").replace("\\", "/").lstrip("/")

    @staticmethod
    def _ok(data: Any = None, message: str = "ok") -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"code": 200, "message": message, "data": data},
        )

    @staticmethod
    def _err(code: int, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={"code": code, "message": message, "data": None},
        )

    # ------------------------------------------------------------------
    # 配置页
    # ------------------------------------------------------------------

    def get_form(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """拼装插件配置页面。"""
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VCard",
                        "props": {"variant": "flat", "class": "mb-4"},
                        "content": [
                            {
                                "component": "VCardTitle",
                                "props": {"class": "d-flex align-center"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "style": "color: #16b1ff;",
                                            "class": "mr-2",
                                        },
                                        "text": "mdi-cloud-sync",
                                    },
                                    {"component": "span", "text": "基本设置"},
                                ],
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "enabled",
                                                            "label": "启用插件",
                                                            "color": "primary",
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "max_file_size_mb",
                                                            "label": "单文件上限(MB)",
                                                            "type": "number",
                                                            "min": 1,
                                                            "hint": "默认 150MB，覆盖浏览器扩展完整备份",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "allowed_suffixes",
                                                        "label": "允许后缀(逗号分隔)",
                                                        "hint": "留空使用默认：mpt2,json",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VCard",
                        "props": {"variant": "flat", "class": "mb-4"},
                        "content": [
                            {
                                "component": "VCardTitle",
                                "props": {"class": "d-flex align-center"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "style": "color: #16b1ff;",
                                            "class": "mr-2",
                                        },
                                        "text": "mdi-download-network-outline",
                                    },
                                    {"component": "span", "text": "直接下载设置"},
                                ],
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "direct_download_enabled",
                                                            "label": "允许直接下载",
                                                            "color": "primary",
                                                            "hint": "跳过媒体识别提交磁力或种子任务",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "max_torrent_size_mb",
                                                            "label": "种子大小上限(MB)",
                                                            "type": "number",
                                                            "min": 1,
                                                            "hint": "仅限制直接上传的 .torrent 文件；保存路径由扩展从 MoviePilot 可用路径中提交",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VCard",
                        "props": {"variant": "flat", "class": "mb-4"},
                        "content": [
                            {
                                "component": "VCardTitle",
                                "props": {"class": "d-flex align-center"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "style": "color: #16b1ff;",
                                            "class": "mr-2",
                                        },
                                        "text": "mdi-information-outline",
                                    },
                                    {"component": "span", "text": "使用说明"},
                                ],
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-body-2"},
                                        "content": [
                                            {
                                                "component": "p",
                                                "text": "📦 本插件为 MoviePilot-Tools 浏览器扩展提供「服务端文件同步」能力。"
                                                        "数据以文件形式落在插件数据目录。",
                                            },
                                            {
                                                "component": "p",
                                                "props": {"class": "mt-2"},
                                                "text": "🔌 插件暴露 API 接口：",
                                            },
                                            {
                                                "component": "ul",
                                                "props": {"class": "ml-4"},
                                                "content": [
                                                    {
                                                        "component": "li",
                                                        "text": "⬆️ 上传：POST /api/v1/plugin/MoviePilotTools/upload  body: {path, content, encoding?}",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "⬇️ 下载：GET  /api/v1/plugin/MoviePilotTools/download?path=user/backup.mpt2",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "📂 列表：GET  /api/v1/plugin/MoviePilotTools/list?prefix=user",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "🗑️ 删除：POST /api/v1/plugin/MoviePilotTools/delete  body: {path}",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "🧲 直接下载：POST /api/v1/plugin/MoviePilotTools/download/direct",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "💓 健康检查：GET  /api/v1/plugin/MoviePilotTools/health",
                                                    },
                                                ],
                                            },
                                            {
                                                "component": "p",
                                                "props": {"class": "mt-2"},
                                                "text": "🗃️ 备份仅生成两个文件：加密主文件 backup.mpt2 与清单 manifest.json，"
                                                        "按用户隔离存放于插件目录，真实路径如 "
                                                        "/config/plugins/MoviePilotTools/{username}/backups/{snapshot}。"
                                            },
                                            {
                                                "component": "p",
                                                "props": {"class": "mt-2"},
                                                "text": "⚙️ 上传限制：单文件默认 ≤ 150MB；允许后缀默认仅 .mpt2 / .json"
                                                        "（可在本页「单文件上限」与「允许后缀」中调整）。",
                                            },
                                            {
                                                "component": "p",
                                                "props": {"class": "mt-2"},
                                                "text": "🔒 Token / PIN / 密钥等敏感项由扩展本地加密存储，永不同步到本插件。",
                                            },
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            }
        ], {
            "enabled": False,
            "max_file_size_mb": 150,
            "allowed_suffixes": "",
            "direct_download_enabled": False,
            "max_torrent_size_mb": 10,
        }
