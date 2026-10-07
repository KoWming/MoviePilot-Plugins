"""本地插件安装：MoviePilot V3 专用实现"""
from __future__ import annotations

import ast
import asyncio
import json
import re
import shutil
import threading
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Body, File, UploadFile
from pydantic import BaseModel, Field

from app import schemas
from app.adapters.external.market import PluginHelper
from app.api.endpoints.plugin import register_plugin
from app.db.oper.systemconfig import SystemConfigOper
from app.schemas.types import SystemConfigKey
from app.sdk.config import settings
from app.sdk.logging import logger
from app.sdk.plugin import _PluginBase, PluginManager

from .ui import PluginUI

# 上传入口允许的扩展名与默认大小上限
ALLOWED_SUFFIX = ".zip"
DEFAULT_MAX_FILE_SIZE = 20 * 1024 * 1024
# 解压时忽略的归档系统目录
IGNORED_ARCHIVE_DIRS = {"__MACOSX"}
# 插件类必须声明的展示属性
REQUIRED_PLUGIN_ATTRS = ("plugin_name", "plugin_desc", "plugin_version")

# 本地插件仓库：默认目录名，位于宿主的 CONFIG_PATH 下（docker 部署即 /config），
# 刻意避开宿主的 <CONFIG_PATH>/plugins —— 那个目录已经被宿主用作插件持久化数据。
DEFAULT_LOCAL_REPO_DIRNAME = "plugin-repo"
# 本地仓库内的索引文件与插件源码目录，布局由宿主规定：<repo>/<索引> + <repo>/<代际>/<id小写>
LOCAL_REPO_PACKAGE_FILE = "package.v3.json"
LOCAL_REPO_PLUGIN_ROOT = "plugins.v3"
LOCAL_REPO_PACKAGE_GENERATION = "v3"


class DependencyStatus(BaseModel):
    """插件依赖处理结果，字段沿用原页面读取的合同。"""

    status: str
    message: str = ""
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    details: List[Dict[str, Any]] = Field(default_factory=list)
    installed_packages_list: List[str] = Field(default_factory=list)


class UploadResultData(BaseModel):
    """一次插件包上传安装的结果。"""

    plugin_id: str
    plugin_display_name: str
    dependencies: DependencyStatus


class InstallStatusData(BaseModel):
    """插件当前是否正在处理安装请求。"""

    is_installing: bool


class BackupFileInfo(BaseModel):
    """单个插件备份文件。"""

    filename: str
    size: int
    modified_time: str


class BackupGroup(BaseModel):
    """按插件分组的备份列表。"""

    plugin_id: str
    plugin_name: str
    backups: List[BackupFileInfo] = Field(default_factory=list)


class BackupActionResult(BaseModel):
    """备份恢复结果。"""

    plugin_id: str
    backup_file: str
    dependencies: DependencyStatus


class BackupDeleteResult(BaseModel):
    """备份删除结果。"""

    plugin_id: str
    backup_file: str


@dataclass(frozen=True)
class PluginPackage:
    """从上传包中解析出的插件事实。"""

    plugin_id: str
    display_name: str
    version: str
    source_dir: Path
    description: str = ""
    icon: str = ""
    author: str = ""

    @property
    def dir_name(self) -> str:
        """运行时插件目录名，同时也是本地仓库内的源码目录名。"""
        return self.plugin_id.lower()


class LocalPluginInstall(_PluginBase):
    # 插件名称
    plugin_name = "本地插件安装"
    # 插件描述
    plugin_desc = "上传本地ZIP插件包进行安装。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/LocalPluginInstall.png"
    # 插件版本
    plugin_version = "3.1.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "localplugininstall_"
    # 加载顺序
    plugin_order = 0
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled: bool = True
    _backup_enabled: bool = True
    _backup_retention: int = 10
    _max_file_size: int = DEFAULT_MAX_FILE_SIZE
    # 本地插件仓库路径；留空时用 CONFIG_PATH 下的默认目录
    _local_repo_path: str = ""
    # 安装互斥锁只保护本实例；不同实例各自安装互不影响
    _install_lock: threading.Lock = threading.Lock()

    def init_plugin(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        生效配置信息。

        :param config: 插件配置字典
        """
        config = config or {}
        self._enabled = bool(config.get("enabled", True))
        self._backup_enabled = bool(config.get("backup_enabled", True))
        try:
            retention = int(config.get("backup_retention", 10) or 10)
        except (TypeError, ValueError):
            retention = 10
        self._backup_retention = max(1, retention)
        self._local_repo_path = str(config.get("local_repo_path") or "").strip()
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            logger.error(f"创建工作目录 {self.workspace} 失败：{error}")

    def get_state(self) -> bool:
        """
        获取插件运行状态
        """
        return bool(self._enabled)

    @property
    def workspace(self) -> Path:
        """上传与解压使用插件实例自己的数据目录，避免共享路径冲突。"""
        return self.get_data_path() / "workspace"

    @property
    def backup_root(self) -> Path:
        """插件备份根目录。"""
        return self.get_data_path() / "backups"

    @staticmethod
    def plugins_root() -> Path:
        """解析宿主的运行时插件目录。"""
        return Path(settings.ROOT_PATH) / "app" / "plugins"

    @property
    def local_repo_root(self) -> Path:
        """
        本地插件仓库根目录。

        未配置时回落到 CONFIG_PATH 下的默认目录；必须使用绝对路径，
        因为宿主解析 PLUGIN_LOCAL_REPO_PATHS 里的相对路径时以 ROOT_PATH 为基准。
        """
        configured = self._local_repo_path
        if configured:
            return Path(configured).expanduser()
        return Path(settings.CONFIG_PATH) / DEFAULT_LOCAL_REPO_DIRNAME

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册API接口
        """
        return [
            {
                "path": "/localupload",
                "endpoint": self.upload_plugin,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "上传并安装插件包",
                "description": "上传本地ZIP插件包，写入运行时插件目录并完成装载登记",
                "response_model": schemas.Response[UploadResultData],
            },
            {
                "path": "/install_status",
                "endpoint": self.get_install_status,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取安装状态",
                "response_model": schemas.Response[InstallStatusData],
            },
            {
                "path": "/backup_list",
                "endpoint": self.get_backup_list,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取备份列表",
                "response_model": schemas.Response[List[BackupGroup]],
            },
            {
                "path": "/restore_backup",
                "endpoint": self.restore_backup,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "从备份恢复插件",
                "response_model": schemas.Response[BackupActionResult],
            },
            {
                "path": "/delete_backup",
                "endpoint": self.delete_backup,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "删除插件备份",
                "response_model": schemas.Response[BackupDeleteResult],
            },
        ]

    async def get_install_status(self) -> schemas.Response[InstallStatusData]:
        """
        获取当前安装状态
        """
        return schemas.Response(
            success=True,
            data=InstallStatusData(is_installing=self._install_lock.locked()),
        )

    async def upload_plugin(self, file: UploadFile = File(...)) -> schemas.Response[UploadResultData]:
        """
        处理插件ZIP包上传和安装。

        :param file: 上传的ZIP文件
        :return: 安装结果
        """
        if not self._install_lock.acquire(blocking=False):
            return schemas.Response(success=False, message="已有安装任务在执行，请稍后重试")
        try:
            if not self.get_state():
                return schemas.Response(success=False, message="插件未启用，请在插件设置中启用后重试")
            filename = (file.filename or "").strip()
            if not filename.lower().endswith(ALLOWED_SUFFIX):
                return schemas.Response(success=False, message="只支持ZIP格式的插件包")
            zip_path = await self._save_upload(file, filename)
            if zip_path is None:
                return schemas.Response(success=False, message="保存上传文件失败")
            try:
                result = await asyncio.to_thread(self.install_from_zip, zip_path)
            finally:
                zip_path.unlink(missing_ok=True)
            if not result.success:
                return schemas.Response(success=False, message=result.message)

            message = result.message
            if result.host_install is not None:
                plugin_id, repo_url = result.host_install
                installed, host_message = await self._install_via_host(plugin_id, repo_url)
                if not installed:
                    return schemas.Response(
                        success=False,
                        message=f"插件已写入本地仓库，但宿主安装失败：{host_message}",
                    )
                # 宿主安装命令是自包含的：落盘、来源身份、本体启用位、定向重载与
                # 路由注册都在网关内完成（initializers/plugins.py:584-601 注入了
                # loadable_marker / target_reloader / registration_refresher），
                # 这里不再重复登记，避免同一个插件被重载与注册两次。
                message = (
                    f"插件 {plugin_id} 安装成功，已建立本地来源；"
                    "请刷新页面在插件管理页面手动启用。"
                )
            return schemas.Response(
                success=True,
                message=message,
                data=result.data,
            )
        except Exception as error:
            logger.error(f"插件上传处理失败：{error}", exc_info=True)
            return schemas.Response(success=False, message=f"插件上传处理失败：{error}")
        finally:
            self._install_lock.release()

    async def _save_upload(self, file: UploadFile, filename: str) -> Optional[Path]:
        """
        把上传文件落到工作目录。

        :param file: 上传的ZIP文件
        :param filename: 用户提供的文件名
        :return: 落盘路径，失败时为 None
        """
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
            target = self.workspace / Path(filename).name
            size = 0
            with target.open("wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > self._max_file_size:
                        buffer.close()
                        target.unlink(missing_ok=True)
                        logger.warning(f"{filename} 超过大小上限 {self._max_file_size} 字节")
                        return None
                    buffer.write(chunk)
            return target
        except OSError as error:
            logger.error(f"保存上传文件失败：{error}")
            return None
        finally:
            await file.close()

    def install_from_zip(self, zip_path: Path) -> InstallOutcome:
        """
        解压、校验并安装一个插件包（阻塞操作，调用方负责放入线程池）。

        :param zip_path: 已落盘的ZIP路径
        :return: 安装结果
        """
        extract_root = self.workspace / f"extract_{zip_path.stem}"
        try:
            shutil.rmtree(extract_root, ignore_errors=True)
            extract_root.mkdir(parents=True, exist_ok=True)
            package, error = self._prepare_package(zip_path, extract_root)
            if package is None:
                return InstallOutcome.failed(error)
            return self._install_package(package)
        except Exception as error:
            logger.error(f"安装插件包失败：{error}", exc_info=True)
            return InstallOutcome.failed(f"安装过程中发生错误：{error}")
        finally:
            shutil.rmtree(extract_root, ignore_errors=True)

    def _prepare_package(self, zip_path: Path, extract_root: Path) -> Tuple[Optional[PluginPackage], str]:
        """
        解压并校验插件包结构。

        :param zip_path: ZIP路径
        :param extract_root: 解压根目录
        :return: (插件包事实, 错误信息)
        """
        try:
            with zipfile.ZipFile(zip_path) as archive:
                if not self._extract_members(archive, extract_root):
                    return None, "插件包包含越界成员，已拒绝解压"
        except zipfile.BadZipFile:
            return None, "无效或损坏的ZIP文件"
        except OSError as error:
            return None, f"解压插件包失败：{error}"

        init_file = extract_root / "__init__.py"
        plugin_dirs = [
            item for item in extract_root.iterdir()
            if item.is_dir() and not item.name.startswith("__")
        ]
        if init_file.exists():
            # 平铺布局：源码直接位于压缩包根。解压根是临时目录（extract_*），
            # 它的名字与插件无关，不能拿来做目录名校验。
            package_dir = extract_root
            wrapped_layout = False
        elif not plugin_dirs:
            return None, "ZIP包中没有找到插件目录或__init__.py文件"
        elif len(plugin_dirs) > 1:
            return None, "ZIP包中包含多个目录，请确保只有一个插件目录"
        else:
            package_dir = plugin_dirs[0]
            init_file = package_dir / "__init__.py"
            if not init_file.exists():
                return None, f"插件目录 '{package_dir.name}' 中缺少__init__.py文件"
            wrapped_layout = True

        return self._read_plugin_class(init_file, package_dir, wrapped_layout)

    def _extract_members(self, archive: zipfile.ZipFile, extract_root: Path) -> bool:
        """
        把ZIP成员解压到目标目录，拒绝越界与符号链接成员。

        :param archive: 已打开的ZIP
        :param extract_root: 目标根目录
        :return: 是否全部成员都在根目录内
        """
        for member in archive.infolist():
            if member.is_dir():
                continue
            if IGNORED_ARCHIVE_DIRS & set(Path(member.filename).parts):
                continue
            target = self._safe_target(extract_root, member.filename)
            if target is None:
                logger.error(f"插件包成员越界，已拒绝：{member.filename}")
                return False
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
            except OSError as error:
                logger.error(f"解压成员 {member.filename} 失败：{error}")
                return False
        return True

    @staticmethod
    def _safe_target(root: Path, member_name: str) -> Optional[Path]:
        """
        把ZIP成员名解析为根目录内的目标路径。

        :param root: 目标根目录
        :param member_name: ZIP成员名
        :return: 安全的目标路径，越界时为 None
        """
        name = member_name.replace("\\", "/")
        parts = [part for part in name.split("/") if part not in ("", ".")]
        if not parts or any(part == ".." for part in parts):
            return None
        target = root.joinpath(*parts)
        try:
            if not target.resolve().is_relative_to(root.resolve()):
                return None
        except OSError:
            return None
        return target

    @staticmethod
    def _read_plugin_class(
        init_file: Path, package_dir: Path, wrapped_layout: bool = True
    ) -> Tuple[Optional[PluginPackage], str]:
        """
        用AST解析插件类，不执行上传的源码。

        :param init_file: __init__.py路径
        :param package_dir: 插件源码目录
        :param wrapped_layout: 压缩包是否自带插件目录；平铺包没有可校验的目录名
        :return: (插件包事实, 错误信息)
        """
        try:
            tree = ast.parse(init_file.read_text(encoding="utf-8", errors="replace"))
        except OSError as error:
            return None, f"读取__init__.py失败：{error}"
        except SyntaxError as error:
            return None, f"__init__.py 语法错误：{error}"

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {
                base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
                for base in node.bases
            }
            if "_PluginBase" not in bases:
                continue
            attrs = LocalPluginInstall._class_string_attrs(node)
            missing = [name for name in REQUIRED_PLUGIN_ATTRS if name not in attrs]
            if missing:
                return None, f"插件类缺少必要属性: {', '.join(missing)}"
            plugin_id = node.name
            # 运行时目录名由类名推导（见 PluginPackage.dir_name），压缩包里的目录名
            # 不影响安装结果。旧实现（V2）对两种布局也都照常安装，因此这里只记录不拒绝。
            if wrapped_layout and package_dir.name.lower() != plugin_id.lower():
                logger.info(
                    f"压缩包目录名 '{package_dir.name}' 与插件类名 '{plugin_id}' 不一致，"
                    f"仍将按类名安装到 '{plugin_id.lower()}'"
                )
            return PluginPackage(
                plugin_id=plugin_id,
                display_name=attrs["plugin_name"],
                version=attrs["plugin_version"],
                source_dir=package_dir,
                description=attrs.get("plugin_desc", ""),
                icon=attrs.get("plugin_icon", ""),
                author=attrs.get("plugin_author", ""),
            ), ""
        return None, "在 __init__.py 中没有找到继承 _PluginBase 的插件类"

    @staticmethod
    def _class_string_attrs(node: ast.ClassDef) -> Dict[str, str]:
        """
        读取插件类顶层声明的字符串属性。

        :param node: 类定义节点
        :return: 属性名到字符串值的映射
        """
        attrs: Dict[str, str] = {}
        for statement in node.body:
            if not isinstance(statement, ast.Assign):
                continue
            value = statement.value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    attrs[target.id] = value.value
        return attrs

    def _install_package(self, package: PluginPackage) -> InstallOutcome:
        """
        安装插件包。

        优先把包发布到本地插件仓库，再把安装动作交给宿主的安装网关：只有经由宿主
        的本地来源安装，插件才会拿到 LOCAL_ONLY 来源身份，卡片不再提示「需确认
        仓库」。本地仓库不可用时回落到直接写运行时目录。

        :param package: 插件包事实
        :return: 安装结果
        """
        repo_error = self._publish_to_local_repo(package)
        if repo_error:
            logger.warning(f"发布插件到本地仓库失败，改用直接安装：{repo_error}")
            note = (
                f"本地插件仓库不可用（{repo_error}），本次未建立本地来源，"
                "卡片仍会提示「需确认仓库」"
            )
            return self._install_package_directly(package, note)

        plugin_dir = self.local_repo_root / LOCAL_REPO_PLUGIN_ROOT / package.dir_name
        dependencies = self._install_dependencies(plugin_dir)
        if dependencies.status == "error":
            logger.warning(f"插件依赖处理未成功：{dependencies.message}")

        self._remember_installed(package.plugin_id)
        repo_url = PluginHelper.make_local_repo_url(
            package.plugin_id,
            str(self.local_repo_root),
            LOCAL_REPO_PACKAGE_GENERATION,
        )
        logger.info(
            f"插件 {package.plugin_id} 已发布到本地仓库 {self.local_repo_root}，交由宿主安装"
        )
        return InstallOutcome(
            success=True,
            message=(
                f"插件 {package.plugin_id} v{package.version} 已发布到本地仓库，"
                "正在交由宿主安装"
            ),
            data=UploadResultData(
                plugin_id=package.plugin_id,
                plugin_display_name=package.display_name,
                dependencies=dependencies,
            ),
            host_install=(package.plugin_id, repo_url),
        )

    def _install_package_directly(self, package: PluginPackage, note: str = "") -> InstallOutcome:
        """
        直接把插件包写入运行时目录并完成装载登记（本地仓库不可用时的兜底）。

        :param package: 插件包事实
        :param note: 追加在成功提示后的说明
        :return: 安装结果
        """
        target_dir = self.plugins_root() / package.dir_name
        backup_zip: Optional[Path] = None
        if target_dir.exists():
            if self._backup_enabled:
                backup_zip = self._create_backup(target_dir)
            shutil.rmtree(target_dir)
            logger.info(f"旧插件目录 {target_dir} 已移除")

        try:
            shutil.copytree(package.source_dir, target_dir)
        except OSError as error:
            if backup_zip is not None:
                self._restore_from_backup(backup_zip, target_dir)
            return InstallOutcome.failed(f"写入插件目录失败：{error}")
        logger.info(f"插件 {package.plugin_id} 已写入 {target_dir}")

        dependencies = self._install_dependencies(target_dir)
        if dependencies.status == "error":
            logger.warning(f"插件依赖处理未成功：{dependencies.message}")

        try:
            self._register_plugin(package.plugin_id)
        except Exception as error:
            logger.error(f"插件 {package.plugin_id} 装载登记失败：{error}", exc_info=True)
            return InstallOutcome.failed(f"插件已写入但加载失败：{error}")

        message = (
            f"插件 {package.plugin_id} v{package.version} 安装成功，"
            "请刷新页面在插件管理页面手动启用。"
        )
        if note:
            message = f"{message}（{note}）"
        return InstallOutcome(
            success=True,
            message=message,
            data=UploadResultData(
                plugin_id=package.plugin_id,
                plugin_display_name=package.display_name,
                dependencies=dependencies,
            ),
        )

    def _publish_to_local_repo(self, package: PluginPackage) -> str:
        """
        把插件包按宿主规定的本地仓库布局落盘，并登记仓库路径。

        布局为 <repo>/package.v3.json + <repo>/plugins.v3/<id小写>/，二者缺一，
        宿主都不会把它识别成可用的本地候选。

        :param package: 插件包事实
        :return: 空字符串表示成功，否则为失败原因
        """
        repo_root = self.local_repo_root
        plugin_dir = repo_root / LOCAL_REPO_PLUGIN_ROOT / package.dir_name
        try:
            repo_root.mkdir(parents=True, exist_ok=True)
            shutil.rmtree(plugin_dir, ignore_errors=True)
            plugin_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(package.source_dir, plugin_dir)
        except OSError as error:
            return f"写入本地仓库失败：{error}"

        index_error = self._update_local_repo_index(repo_root, package)
        if index_error:
            shutil.rmtree(plugin_dir, ignore_errors=True)
            return index_error

        return self._register_local_repo_path(repo_root)

    @staticmethod
    def _update_local_repo_index(repo_root: Path, package: PluginPackage) -> str:
        """
        在本地仓库索引里登记插件条目，保留索引中已有的其他插件与字段。

        :param repo_root: 本地仓库根目录
        :param package: 插件包事实
        :return: 空字符串表示成功，否则为失败原因
        """
        index_file = repo_root / LOCAL_REPO_PACKAGE_FILE
        index: Dict[str, Any] = {}
        if index_file.is_file():
            try:
                loaded = json.loads(index_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                return f"读取本地仓库索引失败：{error}"
            if not isinstance(loaded, dict):
                return f"本地仓库索引 {index_file} 不是合法对象"
            index = loaded

        existing = index.get(package.plugin_id)
        entry: Dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
        # version 是宿主索引里唯一必填字段；这里只覆盖插件包真实声明的展示信息，
        # 不写 v3 代际标记——显式 v3:false 会让宿主直接拒绝这个候选。
        entry.update(
            {
                "name": package.display_name,
                "description": package.description,
                "version": package.version,
            }
        )
        if package.icon:
            entry["icon"] = package.icon
        if package.author:
            entry["author"] = package.author
        index[package.plugin_id] = entry

        try:
            index_file.write_text(
                json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            return f"写入本地仓库索引失败：{error}"
        return ""

    @staticmethod
    def _register_local_repo_path(repo_root: Path) -> str:
        """
        确保本地仓库路径已出现在宿主的 PLUGIN_LOCAL_REPO_PATHS 中。

        :param repo_root: 本地仓库根目录
        :return: 空字符串表示成功，否则为失败原因
        """
        target = str(repo_root)
        current = str(getattr(settings, "PLUGIN_LOCAL_REPO_PATHS", "") or "")
        entries = [
            item.strip()
            for item in re.split(r"[\n,，]", current)
            if item.strip()
        ]
        if any(LocalPluginInstall._same_path(item, target) for item in entries):
            return ""

        entries.append(target)
        # 宿主用 set_key 写 <CONFIG_PATH>/app.env；该键已在环境变量中声明时会拒绝写入
        success, message = settings.update_setting(
            "PLUGIN_LOCAL_REPO_PATHS", ",".join(entries)
        )
        if success is False:
            return message or "宿主拒绝写入 PLUGIN_LOCAL_REPO_PATHS"
        logger.info(f"已把本地插件仓库 {target} 登记到 PLUGIN_LOCAL_REPO_PATHS")
        return ""

    @staticmethod
    def _same_path(left: str, right: str) -> bool:
        """
        宽松比较两个路径字符串，避免仅因写法不同而重复登记。

        :param left: 路径一
        :param right: 路径二
        :return: 是否指向同一路径
        """
        if left == right:
            return True
        try:
            return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            return False

    @staticmethod
    async def _install_via_host(plugin_id: str, repo_url: str) -> Tuple[bool, str]:
        """
        把安装动作交给宿主的插件安装网关，由它建立本地来源身份并写入运行时目录。

        :param plugin_id: 插件ID
        :param repo_url: 本地来源标识
        :return: (是否成功, 说明)
        """
        helper = PluginHelper()
        try:
            # 必须走异步入口：同步版在事件循环内会被直接拒绝
            return await helper.async_install(
                plugin_id,
                repo_url,
                package_version=LOCAL_REPO_PACKAGE_GENERATION,
                force_install=True,
            )
        except Exception as error:
            logger.error(f"请求宿主安装 {plugin_id} 失败：{error}", exc_info=True)
            return False, f"宿主安装失败：{error}"

    def _register_plugin(self, plugin_id: str) -> str:
        """
        登记装载位、重载并刷新注册。

        :param plugin_id: 插件ID
        :return: 运行态状态值
        """
        # 装载判据在实例表启用位上：不登记这一行，插件装完当次能跑、重启即消失
        manager = PluginManager()
        manager.mark_plugin_loadable(plugin_id)
        self._remember_installed(plugin_id)
        runtime_status = manager.reload_plugin_tree(plugin_id)
        register_plugin(plugin_id)
        logger.info(f"插件 {plugin_id} 重载结果：{runtime_status}")
        return getattr(runtime_status, "value", str(runtime_status))

    @staticmethod
    def _remember_installed(plugin_id: str) -> bool:
        """
        把插件加入已安装清单，保留原有条目。

        :param plugin_id: 插件ID
        :return: 是否新增了条目
        """
        def mutation(_db: Any, current: Any) -> Tuple[bool, Any]:
            """在配置写锁内读取旧值并回写最终清单。"""
            installed = list(current or [])
            if plugin_id in installed:
                return False, installed
            installed.append(plugin_id)
            return True, installed

        try:
            return bool(
                SystemConfigOper().update_atomically(
                    SystemConfigKey.UserInstalledPlugins, mutation
                )
            )
        except Exception as error:
            logger.error(f"写入插件安装清单失败：{error}", exc_info=True)
            return False

    def _install_dependencies(self, package_dir: Path) -> DependencyStatus:
        """
        只处理本次安装的插件自己声明的依赖。

        宿主的依赖服务按全部已装插件统计缺失项，直接引用会把别的插件的依赖
        算到本次安装头上；这里先读本插件声明的清单，只报告与它相关的部分。

        :param package_dir: 已落盘的插件目录
        :return: 依赖处理结果
        """
        declared, error = self._declared_dependencies(package_dir)
        if error:
            return DependencyStatus(status="error", message=error)
        if not declared:
            return DependencyStatus(status="success", message="无需安装依赖")

        try:
            result = PluginManager.install_plugin_missing_dependencies_with_status()
        except Exception as install_error:
            return DependencyStatus(
                status="error",
                message=f"依赖处理失败：{install_error}",
                total_count=len(declared),
                failed_count=len(declared),
            )
        missing_names = {
            self._requirement_name(item)
            for item in (getattr(result, "missing", None) or [])
        }
        affected = [item for item in declared if self._requirement_name(item) in missing_names]
        if not affected:
            return DependencyStatus(
                status="success",
                message="依赖已满足，无需安装",
                total_count=len(declared),
                success_count=len(declared),
            )
        if bool(getattr(result, "success", False)):
            return DependencyStatus(
                status="success",
                message="依赖已由宿主依赖服务安装",
                total_count=len(declared),
                success_count=len(declared),
                installed_packages_list=affected,
                details=[
                    {
                        "strategy": "宿主依赖服务",
                        "success": True,
                        "installed_packages": affected,
                    }
                ],
            )
        return DependencyStatus(
            status="error",
            message="依赖尚未就绪，请查看日志或重启 MoviePilot 后重试",
            total_count=len(declared),
            success_count=len(declared) - len(affected),
            failed_count=len(affected),
            details=[
                {
                    "strategy": "宿主依赖服务",
                    "success": False,
                    "installed_packages": [],
                }
            ],
        )

    @staticmethod
    def _declared_dependencies(package_dir: Path) -> Tuple[List[str], str]:
        """
        读取插件包自己声明的依赖清单，与宿主的清单优先级保持一致。

        :param package_dir: 插件目录
        :return: (依赖声明列表, 错误信息)
        """
        pyproject = package_dir / "pyproject.toml"
        if pyproject.is_file():
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            except OSError as error:
                return [], f"读取 pyproject.toml 失败：{error}"
            except tomllib.TOMLDecodeError as error:
                return [], f"pyproject.toml 解析失败：{error}"
            project = data.get("project")
            if not isinstance(project, dict):
                return [], "pyproject.toml 缺少 [project] 配置"
            declared = project.get("dependencies") or []
            if not isinstance(declared, list):
                return [], "pyproject.toml 的 dependencies 必须是数组"
            return [str(item) for item in declared if str(item).strip()], ""

        requirements = package_dir / "requirements.txt"
        if requirements.is_file():
            try:
                content = requirements.read_text(encoding="utf-8")
            except OSError as error:
                return [], f"读取 requirements.txt 失败：{error}"
            return [
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ], ""
        return [], ""

    @staticmethod
    def _requirement_name(requirement: str) -> str:
        """
        取依赖声明的规范名，用于和宿主的缺失列表比对。

        :param requirement: 依赖声明，可能带版本约束、extras 或环境标记
        :return: 规范化后的包名
        """
        name = re.split(r"[<>=!~;\[\s]", requirement.strip(), maxsplit=1)[0]
        return name.replace("_", "-").replace(".", "-").lower()

    # ------------------------------------------------------------------
    # 备份
    # ------------------------------------------------------------------

    def _create_backup(self, source_dir: Path) -> Optional[Path]:
        """
        把现有插件目录备份为ZIP。

        :param source_dir: 插件目录
        :return: 备份文件路径，失败时为 None
        """
        try:
            self.backup_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y.%m.%d_%H-%M-%S")
            backup_zip = self.backup_root / f"{source_dir.name}_{stamp}.zip"
            with zipfile.ZipFile(backup_zip, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in source_dir.rglob("*"):
                    if "__pycache__" in path.parts or not path.is_file():
                        continue
                    archive.write(path, path.relative_to(source_dir.parent))
            logger.info(f"已备份插件目录到 {backup_zip}")
            self._cleanup_backups(source_dir.name)
            return backup_zip
        except (OSError, zipfile.BadZipFile) as error:
            logger.error(f"备份插件目录失败：{error}")
            return None

    def _restore_from_backup(self, backup_zip: Path, target_dir: Path) -> None:
        """
        从备份ZIP恢复插件目录。

        :param backup_zip: 备份文件
        :param target_dir: 目标插件目录
        """
        staging = self.workspace / f"restore_{target_dir.name}"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(backup_zip) as archive:
                if not self._verify_backup_layout(archive, target_dir.name):
                    raise ValueError("备份内容与插件目录不匹配，已拒绝恢复")
                if not self._extract_members(archive, staging):
                    raise ValueError("备份文件包含越界成员，已拒绝恢复")
            source = staging / target_dir.name
            if not (source / "__init__.py").is_file():
                raise ValueError("备份内容缺少__init__.py")
            shutil.rmtree(target_dir, ignore_errors=True)
            shutil.copytree(source, target_dir)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        logger.info(f"已从 {backup_zip} 恢复插件目录")

    @staticmethod
    def _verify_backup_layout(archive: zipfile.ZipFile, dir_name: str) -> bool:
        """
        校验备份包内所有成员都位于插件目录之下。

        :param archive: 已打开的备份ZIP
        :param dir_name: 期望的插件目录名
        :return: 是否符合备份布局
        """
        for member in archive.infolist():
            parts = [
                part for part in member.filename.replace("\\", "/").split("/")
                if part not in ("", ".")
            ]
            if not parts:
                continue
            if parts[0] != dir_name:
                return False
        return True

    def _cleanup_backups(self, dir_name: str) -> None:
        """
        按保留份数清理旧备份。

        :param dir_name: 插件目录名
        """
        backups = sorted(self.backup_root.glob(f"{dir_name}_*.zip"))
        for stale in backups[: max(0, len(backups) - self._backup_retention)]:
            try:
                stale.unlink()
                logger.info(f"已清理旧备份 {stale.name}")
            except OSError as error:
                logger.warning(f"清理旧备份 {stale.name} 失败：{error}")

    def _parse_backup_name(self, filename: str) -> Optional[Dict[str, str]]:
        """
        解析备份文件名。

        :param filename: 备份文件名
        :return: 目录名与时间戳，无法解析时为 None
        """
        stem = Path(filename).stem
        if "_" not in stem:
            return None
        dir_name, stamp = stem.split("_", 1)
        if not dir_name or not stamp:
            return None
        return {"dir_name": dir_name, "stamp": stamp}

    def _list_backup_groups(self) -> List[BackupGroup]:
        """
        按插件分组返回备份列表。

        :return: 备份分组
        """
        if not self.backup_root.exists():
            return []
        groups: Dict[str, List[BackupFileInfo]] = {}
        for path in self.backup_root.glob("*.zip"):
            parsed = self._parse_backup_name(path.name)
            if not parsed:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            groups.setdefault(parsed["dir_name"], []).append(
                BackupFileInfo(
                    filename=path.name,
                    size=stat.st_size,
                    modified_time=datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                )
            )
        return [
            BackupGroup(
                plugin_id=dir_name,
                plugin_name=self._display_name(dir_name),
                backups=sorted(items, key=lambda item: item.filename, reverse=True),
            )
            for dir_name, items in sorted(groups.items())
        ]

    @staticmethod
    def _display_name(dir_name: str) -> str:
        """
        读取插件目录内声明的展示名，失败时回落目录名。

        :param dir_name: 插件目录名
        :return: 展示名
        """
        package, _ = LocalPluginInstall._read_plugin_class(
            LocalPluginInstall.plugins_root() / dir_name / "__init__.py",
            LocalPluginInstall.plugins_root() / dir_name,
        )
        return package.display_name if package else dir_name

    def _resolve_backup(self, dir_name: str, backup_file: str) -> Optional[Path]:
        """
        校验备份文件确实位于备份目录内。

        :param dir_name: 插件目录名
        :param backup_file: 备份文件名
        :return: 备份文件路径，非法时为 None
        """
        name = Path(backup_file).name
        parsed = self._parse_backup_name(name)
        if not parsed or parsed["dir_name"] != dir_name:
            return None
        candidate = self.backup_root / name
        if not candidate.is_file():
            return None
        return candidate

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    async def get_backup_list(self) -> schemas.Response[List[BackupGroup]]:
        """
        获取插件备份列表
        """
        try:
            groups = await asyncio.to_thread(self._list_backup_groups)
        except Exception as error:
            logger.error(f"获取备份列表失败：{error}", exc_info=True)
            return schemas.Response(success=False, message=f"获取备份列表失败：{error}")
        return schemas.Response(success=True, data=groups)

    async def restore_backup(
        self, payload: Dict[str, Any] = Body(...)
    ) -> schemas.Response[BackupActionResult]:
        """
        从备份恢复安装插件。

        :param payload: 含 plugin_id 与 backup_file 的请求体
        """
        if not self.get_state():
            return schemas.Response(success=False, message="插件未启用，请在插件设置中启用后重试")
        dir_name = str((payload or {}).get("plugin_id") or "").strip().lower()
        backup_file = str((payload or {}).get("backup_file") or "").strip()
        if not dir_name or not backup_file:
            return schemas.Response(success=False, message="缺少 plugin_id 或 backup_file 参数")
        if not self._install_lock.acquire(blocking=False):
            return schemas.Response(success=False, message="已有安装任务在执行，请稍后重试")
        try:
            result = await asyncio.to_thread(self._restore_install, dir_name, backup_file)
        finally:
            self._install_lock.release()
        return schemas.Response(success=result.success, message=result.message, data=result.data)

    def _restore_install(self, dir_name: str, backup_file: str) -> InstallOutcome:
        """
        从指定备份恢复并重新登记插件。

        :param dir_name: 插件目录名
        :param backup_file: 备份文件名
        :return: 恢复结果
        """
        backup_zip = self._resolve_backup(dir_name, backup_file)
        if backup_zip is None:
            return InstallOutcome.failed("备份文件不存在或与插件不匹配")
        target_dir = self.plugins_root() / dir_name
        try:
            self._restore_from_backup(backup_zip, target_dir)
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            return InstallOutcome.failed(f"恢复备份失败：{error}")

        package, error = self._read_plugin_class(
            target_dir / "__init__.py", target_dir
        )
        if package is None:
            return InstallOutcome.failed(f"备份内容校验失败：{error}")

        dependencies = self._install_dependencies(target_dir)
        try:
            self._register_plugin(package.plugin_id)
        except Exception as register_error:
            logger.error(f"恢复后装载登记失败：{register_error}", exc_info=True)
            return InstallOutcome.failed(f"恢复完成但加载失败：{register_error}")
        return InstallOutcome(
            success=True,
            message=f"插件 {package.plugin_id} 已从备份恢复，请刷新页面手动启用。",
            data=BackupActionResult(
                plugin_id=package.plugin_id,
                backup_file=backup_file,
                dependencies=dependencies,
            ),
        )

    async def delete_backup(
        self, payload: Dict[str, Any] = Body(...)
    ) -> schemas.Response[BackupDeleteResult]:
        """
        删除指定插件备份。

        :param payload: 含 plugin_id 与 backup_file 的请求体
        """
        dir_name = str((payload or {}).get("plugin_id") or "").strip().lower()
        backup_file = str((payload or {}).get("backup_file") or "").strip()
        if not dir_name or not backup_file:
            return schemas.Response(success=False, message="缺少 plugin_id 或 backup_file 参数")
        backup_zip = self._resolve_backup(dir_name, backup_file)
        if backup_zip is None:
            return schemas.Response(success=False, message="备份文件不存在或与插件不匹配")
        try:
            backup_zip.unlink()
        except OSError as error:
            logger.error(f"删除备份失败：{error}")
            return schemas.Response(success=False, message=f"删除备份失败：{error}")
        return schemas.Response(
            success=True,
            message="备份已删除",
            data=BackupDeleteResult(plugin_id=dir_name, backup_file=backup_zip.name),
        )

    # ------------------------------------------------------------------
    # 页面
    # ------------------------------------------------------------------

    @staticmethod
    def get_command() -> Optional[List[Dict[str, Any]]]:
        """
        获取命令
        """
        return None

    def get_page(self) -> List[dict]:
        """
        数据页面
        """
        return self._ui().get_page(self.__class__.__name__)

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return self._ui().get_form()

    def _ui(self) -> PluginUI:
        """
        构造绑定当前实例的页面构建器。

        :return: 页面构建器
        """
        return PluginUI(self.get_data_path(), self._max_file_size)

    def get_service(self) -> List[Dict[str, Any]]:
        """
        获取服务列表
        """
        return []

    def stop_service(self) -> None:
        """
        停止插件服务
        """
        self._enabled = False
        logger.info("本地插件安装已停止")


@dataclass
class InstallOutcome:
    """安装或恢复的统一结果，供内部与 API 层共用。"""

    success: bool
    message: str = ""
    data: Any = None
    # 需要在事件循环里交给宿主完成的安装步骤：(插件ID, 本地来源标识)。
    # 为空表示已在本线程内直接装好（本地仓不可用时的兜底路径）。
    host_install: Optional[Tuple[str, str]] = None

    @classmethod
    def failed(cls, message: str) -> "InstallOutcome":
        """
        构造失败结果。

        :param message: 失败原因
        :return: 失败结果
        """
        return cls(success=False, message=message)
