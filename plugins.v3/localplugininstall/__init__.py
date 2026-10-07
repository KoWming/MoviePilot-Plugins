"""本地插件安装：MoviePilot V3 专用实现"""
from __future__ import annotations

import ast
import asyncio
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

    @property
    def dir_name(self) -> str:
        """运行时插件目录名。"""
        return self.plugin_id.lower()


class LocalPluginInstall(_PluginBase):
    # 插件名称
    plugin_name = "本地插件安装"
    # 插件描述
    plugin_desc = "上传本地ZIP插件包进行安装。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/LocalPluginInstall.png"
    # 插件版本
    plugin_version = "3.0.0"
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
            return schemas.Response(
                success=True,
                message=result.message,
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
            package_dir = extract_root
        elif not plugin_dirs:
            return None, "ZIP包中没有找到插件目录或__init__.py文件"
        elif len(plugin_dirs) > 1:
            return None, "ZIP包中包含多个目录，请确保只有一个插件目录"
        else:
            package_dir = plugin_dirs[0]
            init_file = package_dir / "__init__.py"
            if not init_file.exists():
                return None, f"插件目录 '{package_dir.name}' 中缺少__init__.py文件"

        return self._read_plugin_class(init_file, package_dir)

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
    def _read_plugin_class(init_file: Path, package_dir: Path) -> Tuple[Optional[PluginPackage], str]:
        """
        用AST解析插件类，不执行上传的源码。

        :param init_file: __init__.py路径
        :param package_dir: 插件源码目录
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
            if package_dir.name.lower() != plugin_id.lower():
                return None, (
                    f"插件目录名 ('{package_dir.name}') 与插件类名的小写形式 "
                    f"('{plugin_id.lower()}') 不一致，请调整ZIP包结构"
                )
            return PluginPackage(
                plugin_id=plugin_id,
                display_name=attrs["plugin_name"],
                version=attrs["plugin_version"],
                source_dir=package_dir,
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
        写入运行时插件目录并完成装载登记。

        :param package: 插件包事实
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
        return InstallOutcome(
            success=True,
            message=message,
            data=UploadResultData(
                plugin_id=package.plugin_id,
                plugin_display_name=package.display_name,
                dependencies=dependencies,
            ),
        )

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

    @classmethod
    def failed(cls, message: str) -> "InstallOutcome":
        """
        构造失败结果。

        :param message: 失败原因
        :return: 失败结果
        """
        return cls(success=False, message=message)
