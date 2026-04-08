import os
import shutil
import zipfile
import json
import re
import ast
import time
from datetime import datetime
import importlib.util
import sys
import threading
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional

from fastapi import UploadFile, File, Body
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.plugins import _PluginBase
from app.log import logger
from app.utils.system import SystemUtils
from app.core.plugin import PluginManager
from app.db.systemconfig_oper import SystemConfigOper
from app.schemas.types import SystemConfigKey
from app.scheduler import Scheduler
from app.command import Command
from app.api.endpoints.plugin import register_plugin_api


class LocalPluginInstall(_PluginBase):
    # 插件名称
    plugin_name = "本地插件安装"
    # 插件描述
    plugin_desc = "上传本地ZIP插件包进行安装。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/LocalPluginInstall.png"
    # 插件版本
    plugin_version = "1.4.0"
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
    _enabled = True
    _file = None
    _install_lock = threading.Lock()  # 防止并发安装

    # 默认配置
    _config = {
        "enabled": True,
        "backup_enabled": True,                   # 启用备份
        "backup_retention": 10,                  # 备份保留份数
        "temp_path": "/tmp/moviepilot/upload",    # 临时文件路径
        "max_file_size": 10 * 1024 * 1024,        # 最大文件大小 10MB
        "allowed_extensions": ["zip"],            # 允许的文件扩展名
    }

    def init_plugin(self, config: dict = None):
        """初始化插件配置"""
        if config:
            if "enabled" not in config:
                config["enabled"] = True
            if "backup_enabled" not in config:
                config["backup_enabled"] = True
            self._config.update(config)

        try:
            backup_retention = int(self._config.get("backup_retention", 10) or 10)
        except (TypeError, ValueError):
            backup_retention = 10
        self._config["backup_retention"] = max(1, backup_retention)
            
        temp_path = Path(self._config.get('temp_path'))
        if not temp_path.exists():
            try:
                temp_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建临时目录: {temp_path}")
            except Exception as e:
                logger.error(f"创建临时目录失败 {temp_path}: {e}")
                self._config["enabled"] = False  # 临时路径创建失败则禁用插件
            
    def get_state(self) -> bool:
        """获取插件运行状态"""
        return self._enabled

    def _validate_plugin_structure(self, extract_path: Path, guessed_plugin_dir_name: str) -> Tuple[bool, str, str, str]:
        """
        验证插件结构
        
        Args:
            extract_path: 解压后的插件路径
            guessed_plugin_dir_name: 推测的插件目录名
            
        Returns:
            Tuple[bool, str, str, str]: (是否有效, 插件ID, 插件显示名称, 错误信息)
        """
        try:
            logger.info(f"开始验证插件结构: {extract_path}")
            
            # 检查extract_path本身是否包含__init__.py文件
            init_file = extract_path / "__init__.py"
            actual_plugin_dir_name_from_fs: str = ""
            is_root_plugin_layout = False
            
            if init_file.exists():
                # extract_path本身就是插件目录
                is_root_plugin_layout = True
                logger.info(f"检测到extract_path本身包含__init__.py文件，插件目录: {extract_path}, 实际目录名: {actual_plugin_dir_name_from_fs}")
            else:
                # 检查是否有插件子目录
                plugin_dirs = [d for d in extract_path.iterdir() if d.is_dir() and not d.name.startswith('__')]
                
                logger.info(f"找到的子目录: {[d.name for d in plugin_dirs]}")
                
                if len(plugin_dirs) == 0:
                    return False, "", "", "ZIP包中没有找到插件目录或__init__.py文件"
                elif len(plugin_dirs) > 1:
                    return False, "", "", "ZIP包中包含多个目录，请确保只有一个插件目录"
                else:
                    plugin_dir = plugin_dirs[0]
                    actual_plugin_dir_name_from_fs = plugin_dir.name.lower()
                    init_file = plugin_dir / "__init__.py"
                    if not init_file.exists():
                        return False, "", "", f"插件目录 '{actual_plugin_dir_name_from_fs}' 中缺少 __init__.py 文件"
                    logger.info(f"找到插件子目录: {plugin_dir}, 实际目录名: {actual_plugin_dir_name_from_fs}")

            # 检查__init__.py文件和获取插件类
            try:
                plugin_class = self._find_plugin_class(init_file, guessed_plugin_dir_name)
                if not plugin_class:
                    return False, "", "", f"在 __init__.py 中没有找到继承 _PluginBase 的插件类"
            except ImportError as e:
                # 处理依赖缺失等导入错误
                error_msg = str(e)
                
                # 检查是否有 requirements.txt 文件
                requirements_file = extract_path / "requirements.txt"
                if not requirements_file.exists():
                    # 检查插件子目录中是否有 requirements.txt
                    plugin_dirs = [d for d in extract_path.iterdir() if d.is_dir() and not d.name.startswith('__')]
                    if plugin_dirs:
                        requirements_file = plugin_dirs[0] / "requirements.txt"
                
                if requirements_file.exists():
                    logger.info(f"检测到 requirements.txt 文件，尝试先安装依赖: {requirements_file}")
                    # 尝试安装依赖
                    dependencies_status = self._install_dependencies(extract_path)
                    if dependencies_status["status"] == "success":
                        logger.info("依赖安装成功，重新尝试导入插件")
                        # 重新尝试导入
                        try:
                            plugin_class = self._find_plugin_class(init_file, guessed_plugin_dir_name)
                            if not plugin_class:
                                return False, "", "", f"依赖安装后仍无法找到继承 _PluginBase 的插件类"
                        except ImportError as e2:
                            return False, "", "", f"依赖安装后插件导入仍失败: {str(e2)}"
                    else:
                        return False, "", "", f"依赖安装失败: {dependencies_status['message']}。原始错误: {error_msg}"
                else:
                    return False, "", "", f"插件导入失败: {error_msg}。请确保插件包包含 requirements.txt 文件，或手动安装所需依赖。"
            
            # 获取插件类名和显示名称
            actual_plugin_id_for_manager = plugin_class.__name__
            plugin_display_name = getattr(plugin_class, 'plugin_name', actual_plugin_id_for_manager)

            if is_root_plugin_layout:
                actual_plugin_dir_name_from_fs = actual_plugin_id_for_manager.lower()

            # 验证文件系统目录名与插件类名的小写形式是否一致
            if actual_plugin_dir_name_from_fs != actual_plugin_id_for_manager.lower():
                 return False, "", "", (
                    f"插件目录名 ('{actual_plugin_dir_name_from_fs}') 与插件类名的小写形式 ('{actual_plugin_id_for_manager.lower()}') 不一致。"
                    f"请确保插件的ZIP包结构中，插件目录名与插件类名的小写形式相同。"
                )
            
            # 检查必要的插件属性
            required_attrs = ['plugin_name', 'plugin_desc', 'plugin_version']
            missing_attrs = []
            
            for attr in required_attrs:
                if not hasattr(plugin_class, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                return False, "", "", f"插件类缺少必要属性: {', '.join(missing_attrs)}"
            
            return True, actual_plugin_id_for_manager, plugin_display_name, ""
            
        except Exception as e:
            return False, "", "", f"验证插件结构时发生错误: {str(e)}"

    def _find_plugin_class(self, init_file: Path, guessed_plugin_dir_name: str) -> Optional[type]:
        """
        在__init__.py文件中查找继承_PluginBase的插件类
        
        Args:
            init_file: __init__.py文件路径
            guessed_plugin_dir_name: 推测的插件目录名
            
        Returns:
            Optional[type]: 找到的插件类或None
        """
        try:
            # 创建唯一的模块名避免冲突
            module_name = f"dynamic_plugin_{guessed_plugin_dir_name}_{int(time.time() * 1000)}"
            spec = importlib.util.spec_from_file_location(module_name, init_file)
            if not spec:
                return None
                
            # 创建并执行模块
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找继承_PluginBase的类
            found_plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    hasattr(attr, '__bases__') and
                    any('_PluginBase' in str(base) for base in attr.__bases__)):
                    found_plugin_class = attr
                    break
            
            if found_plugin_class:
                logger.info(f"在 {init_file.name} 中找到插件类: {found_plugin_class.__name__}")
                return found_plugin_class
            return None
            
        except ModuleNotFoundError as e:
            # 处理依赖缺失的情况
            missing_module = str(e).split("'")[1] if "'" in str(e) else "未知模块"
            logger.warning(f"插件依赖缺失: {missing_module}")
            raise ImportError(f"插件依赖缺失: {missing_module}。请确保插件包包含 requirements.txt 文件，或手动安装所需依赖。")
        except ImportError as e:
            # 处理其他导入错误
            logger.error(f"导入插件模块时发生错误: {e}")
            raise ImportError(f"导入插件模块失败: {e}")
        except Exception as e:
            logger.error(f"查找插件类时发生错误: {e}", exc_info=True)
            return None

    def _verify_plugin_loading(self, plugin_id_for_manager: str) -> bool:
        """
        验证插件是否可以正常加载
        
        Args:
            plugin_id_for_manager: 插件ID (插件类名，保留大小写)
            
        Returns:
            bool: 插件是否加载成功
        """
        try:
            plugin_manager = PluginManager()
            
            # 获取PluginManager的内部状态
            all_known_plugins = plugin_manager.get_plugin_ids()
            currently_running_plugins = plugin_manager.get_running_plugin_ids()
            logger.info(f"[_verify_plugin_loading] PluginManager known plugins: {all_known_plugins}")
            logger.info(f"[_verify_plugin_loading] PluginManager running plugins: {currently_running_plugins}")

            # 检查插件是否在已知插件列表中
            if plugin_id_for_manager not in all_known_plugins:
                logger.error(f"插件 {plugin_id_for_manager} 未在PluginManager的已识别插件列表中找到。")
                return False

            if plugin_id_for_manager not in currently_running_plugins:
                logger.error(f"插件 {plugin_id_for_manager} 未在PluginManager的运行态插件中找到。")
                return False

            # 检查插件状态
            plugin_state = plugin_manager.get_plugin_state(plugin_id_for_manager)
            if not plugin_state:
                logger.warning(f"插件 {plugin_id_for_manager} 状态为禁用。")
                return False

            logger.info(f"插件 {plugin_id_for_manager} 加载验证通过。")
            return True
            
        except Exception as e:
            logger.error(f"验证插件加载时发生错误: {e}", exc_info=True)
            return False

    def _install_dependencies(self, plugin_dir: Path) -> Dict[str, Any]:
        """
        安装插件依赖
        
        Args:
            plugin_dir: 插件目录路径
            
        Returns:
            Dict[str, Any]: 依赖安装结果
        """
        requirements_file = plugin_dir / "requirements.txt"
        
        if not requirements_file.exists():
            return {
                "status": "success",
                "message": "无需安装依赖",
                "total_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "details": [],
                "installed_packages_list": []
            }
        
        try:
            # 读取依赖列表
            with open(requirements_file, 'r', encoding='utf-8') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not requirements:
                return {
                    "status": "success",
                    "message": "依赖文件为空，无需安装依赖",
                    "total_count": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "details": [],
                    "installed_packages_list": []
                }
            
            total_count = len(requirements)
            logger.info(f"需要安装的依赖列表: {requirements}")
            logger.info(f"总共需要安装 {total_count} 个依赖")
            
            # 构建安装策略
            strategies = []
            
            if settings.PIP_PROXY:
                strategies.append(("镜像站", ["pip", "install", "-r", str(requirements_file), "-i", settings.PIP_PROXY, "-v"]))
            
            if settings.PROXY_HOST:
                strategies.append(("代理", ["pip", "install", "-r", str(requirements_file), "--proxy", settings.PROXY_HOST, "-v"]))
            
            strategies.append(("直连", ["pip", "install", "-r", str(requirements_file), "-v"]))
            
            # 尝试不同策略安装
            final_status = "error"
            final_message = "所有依赖安装策略均失败"
            final_success_count = 0
            final_failed_count = 0
            final_installed_packages = []
            install_attempts_details = []

            for strategy_name, pip_command in strategies:
                logger.info(f"[PIP] 开始使用{strategy_name}策略安装依赖")
                logger.info(f"[PIP] 执行命令: {' '.join(pip_command)}")

                success, message = SystemUtils.execute_with_subprocess(pip_command)

                attempt_success_count = 0
                attempt_failed_count = 0
                attempt_installed_packages = []

                if success:
                    attempt_success_count = total_count
                    # 解析已安装的包名
                    if message:
                        for line in message.splitlines():
                            if 'successfully installed' in line.lower():
                                try:
                                    parts = line.split('Successfully installed')[1].strip().split()
                                    for part in parts:
                                        pkg_name = part.split('-')[0]
                                        attempt_installed_packages.append(pkg_name)
                                except Exception as e:
                                    logger.debug(f"解析已安装包名失败: {e}")
                    final_status = "success"
                    final_message = f"使用{strategy_name}策略安装依赖成功"
                    final_success_count = total_count
                    final_failed_count = 0
                    final_installed_packages = attempt_installed_packages
                    break
                else:
                    attempt_failed_count = total_count
                    final_message = f"所有依赖安装策略均失败: {message or '未知错误'}"

                install_attempts_details.append({
                    "strategy": strategy_name,
                    "success": success,
                    "success_count": attempt_success_count,
                    "failed_count": attempt_failed_count,
                    "installed_packages": attempt_installed_packages,
                    "message": message or "无输出信息"
                })

            return {
                "status": final_status,
                "message": final_message,
                "total_count": total_count,
                "success_count": final_success_count,
                "failed_count": final_failed_count,
                "details": install_attempts_details,
                "installed_packages_list": final_installed_packages
            }

        except Exception as e:
            logger.error(f"依赖安装异常: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"依赖安装异常: {str(e)}",
                "total_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "details": [],
                "installed_packages_list": []
            }

    def _create_plugin_backup_zip(self, source_dir: Path, backup_zip_path: Path) -> None:
        """将现有插件目录备份为 ZIP，压缩包内根目录名保持为插件目录名。"""
        ignore_names = {"__pycache__"}

        with zipfile.ZipFile(backup_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                dirs[:] = [dir_name for dir_name in dirs if dir_name not in ignore_names]

                root_path = Path(root)
                for file_name in files:
                    file_path = root_path / file_name
                    arcname = file_path.relative_to(source_dir.parent)
                    zipf.write(file_path, arcname)

    def _restore_plugin_from_backup_zip(self, backup_zip_path: Path, target_dir: Path) -> None:
        """从 ZIP 备份恢复插件目录。"""
        if target_dir.exists():
            shutil.rmtree(target_dir)

        with zipfile.ZipFile(backup_zip_path, 'r') as zipf:
            zipf.extractall(target_dir.parent)

    def _cleanup_old_backups(self, backup_root_dir: Path, plugin_id_for_path: str) -> None:
        """按保留份数清理旧备份。"""
        retention = self._config.get("backup_retention", 10)
        try:
            retention = int(retention)
        except (TypeError, ValueError):
            retention = 10
        retention = max(1, retention)

        backup_files = sorted(
            backup_root_dir.glob(f"{plugin_id_for_path}_*.zip"),
            key=lambda path: path.stat().st_mtime,
            reverse=True
        )

        for old_backup in backup_files[retention:]:
            try:
                old_backup.unlink()
                logger.info(f"已清理旧备份压缩包: {old_backup}")
            except Exception as e:
                logger.warning(f"清理旧备份压缩包失败 {old_backup}: {e}")

    def _get_backup_root_dir(self) -> Path:
        """获取备份目录。"""
        backup_root_dir = self.get_data_path() / "backups"
        backup_root_dir.mkdir(parents=True, exist_ok=True)
        return backup_root_dir

    def _parse_backup_filename(self, filename: str) -> Optional[Dict[str, str]]:
        """解析备份文件名。"""
        match = re.match(r"^(?P<plugin_id>.+)_(?P<backup_time>\d{4}\.\d{2}\.\d{2}_\d{2}-\d{2}-\d{2})\.zip$", filename)
        if not match:
            return None
        return match.groupdict()

    def _extract_plugin_name_from_backup_zip(self, backup_zip_path: Path, fallback_plugin_id: str) -> str:
        """从备份 ZIP 中提取插件中文名。"""
        try:
            with zipfile.ZipFile(backup_zip_path, 'r') as zipf:
                init_candidates = [
                    name for name in zipf.namelist()
                    if name.endswith("/__init__.py") and not any(part.startswith("__") for part in Path(name).parts[:-1])
                ]

                if not init_candidates:
                    return fallback_plugin_id

                init_content = zipf.read(init_candidates[0]).decode('utf-8', errors='ignore')
                match = re.search(r"^\s*plugin_name\s*=\s*(.+)$", init_content, re.MULTILINE)
                if not match:
                    return fallback_plugin_id

                plugin_name_expr = match.group(1).split('#', 1)[0].strip()
                plugin_name = ast.literal_eval(plugin_name_expr)
                return str(plugin_name).strip() if plugin_name else fallback_plugin_id
        except Exception as e:
            logger.warning(f"解析备份插件名称失败 {backup_zip_path.name}: {e}")
            return fallback_plugin_id

    def _list_backup_groups(self) -> List[Dict[str, Any]]:
        """按插件分组返回备份列表。"""
        backup_root_dir = self._get_backup_root_dir()
        grouped_backups: Dict[str, List[Dict[str, Any]]] = {}
        plugin_name_map: Dict[str, str] = {}

        for backup_file in sorted(backup_root_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True):
            parsed = self._parse_backup_filename(backup_file.name)
            if not parsed:
                logger.warning(f"跳过无法识别命名规则的备份文件: {backup_file.name}")
                continue

            plugin_id = parsed["plugin_id"]
            plugin_name_map.setdefault(plugin_id, self._extract_plugin_name_from_backup_zip(backup_file, plugin_id))
            grouped_backups.setdefault(plugin_id, []).append({
                "filename": backup_file.name,
                "backup_time": parsed["backup_time"],
                "size": backup_file.stat().st_size,
                "modified_time": datetime.fromtimestamp(backup_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

        result = []
        for plugin_id, backups in grouped_backups.items():
            result.append({
                "plugin_id": plugin_id,
                "plugin_name": plugin_name_map.get(plugin_id, plugin_id),
                "backups": backups
            })

        result.sort(key=lambda item: item["plugin_id"])
        return result

    def _delete_backup_file(self, plugin_id: str, backup_file: str) -> Tuple[bool, str]:
        """删除指定备份 ZIP。"""
        parsed = self._parse_backup_filename(backup_file)
        if not parsed:
            return False, "备份文件名格式无效"

        if parsed.get("plugin_id") != plugin_id:
            return False, "备份文件与插件 ID 不匹配"

        backup_root_dir = self._get_backup_root_dir()
        backup_path = backup_root_dir / backup_file
        if not backup_path.exists() or not backup_path.is_file():
            return False, "备份文件不存在"

        try:
            backup_path.unlink()
            logger.info(f"已删除备份文件: {backup_file}")
            return True, f"备份文件 {backup_file} 已删除"
        except Exception as e:
            logger.error(f"删除备份文件失败 {backup_file}: {e}", exc_info=True)
            return False, f"删除备份文件失败: {e}"

    def _finalize_plugin_installation(self, plugin_id: str, target_dir: Path) -> Dict[str, Any]:
        """完成插件安装后的依赖安装、注册与加载。"""
        plugin_manager_instance = PluginManager()
        plugin_config = plugin_manager_instance.get_plugin_config(plugin_id)
        if not plugin_config:
            plugin_config = {"enabled": False}
            plugin_manager_instance.save_plugin_config(plugin_id, plugin_config)
            logger.info(f"已为插件 {plugin_id} 保存默认配置 (初始为禁用)。")

        dependencies_status = self._install_dependencies(target_dir)
        if dependencies_status["status"] == "error":
            logger.warning(f"依赖安装失败: {dependencies_status['message']}")

        install_plugins = SystemConfigOper().get(SystemConfigKey.UserInstalledPlugins) or []
        if plugin_id not in install_plugins:
            install_plugins.append(plugin_id)
            SystemConfigOper().set(SystemConfigKey.UserInstalledPlugins, install_plugins)
            logger.info(f"插件 {plugin_id} 已添加到已安装列表。")

        logger.info(f"调用 PluginManager.reload_plugin() 重新加载插件 {plugin_id}...")
        try:
            def reload_specific_plugin():
                try:
                    plugin_manager_instance.reload_plugin(plugin_id)
                    logger.info(f"插件 {plugin_id} 重新加载完成")
                except Exception as e:
                    logger.error(f"插件 {plugin_id} 重新加载失败: {e}")

            reload_thread = threading.Thread(target=reload_specific_plugin, daemon=True)
            reload_thread.start()
            reload_thread.join(timeout=5)
            if reload_thread.is_alive():
                logger.warning(f"插件 {plugin_id} 重新加载超时，但插件可能已成功加载")
        except Exception as e:
            logger.error(f"插件 {plugin_id} 重新加载异常: {e}")

        time.sleep(1)

        try:
            plugin_manager_instance = PluginManager()
            logger.info("重新获取 PluginManager 实例以刷新状态...")
        except Exception as e:
            logger.error(f"重新获取 PluginManager 实例失败: {e}")

        Scheduler().update_plugin_job(plugin_id)
        register_plugin_api(plugin_id)
        Command().init_commands(plugin_id)
        return dependencies_status

    def _restore_plugin_install(self, plugin_id: str, backup_file: str) -> Tuple[bool, str, Dict[str, Any]]:
        """从指定备份恢复并安装插件。"""
        plugin_id_for_path = plugin_id.lower()
        parsed = self._parse_backup_filename(backup_file)
        if not parsed:
            return False, "备份文件名格式无效", {"status": "error", "message": "备份文件名格式无效"}

        if parsed["plugin_id"].lower() != plugin_id_for_path:
            return False, "备份文件与插件不匹配", {"status": "error", "message": "备份文件与插件不匹配"}

        backup_root_dir = self._get_backup_root_dir()
        backup_zip_path = backup_root_dir / backup_file
        if not backup_zip_path.exists() or not backup_zip_path.is_file():
            return False, "备份文件不存在", {"status": "error", "message": "备份文件不存在"}

        target_dir = Path("/app/app/plugins") / plugin_id_for_path

        try:
            self._restore_plugin_from_backup_zip(backup_zip_path, target_dir)
            logger.info(f"已从备份恢复插件目录: {backup_zip_path}")

            init_file = target_dir / "__init__.py"
            if not init_file.exists():
                raise FileNotFoundError("恢复后的插件目录中缺少 __init__.py")

            plugin_class = self._find_plugin_class(init_file, plugin_id_for_path)
            if not plugin_class:
                raise ValueError("恢复后的插件中没有找到继承 _PluginBase 的插件类")

            actual_plugin_id = plugin_class.__name__
            if actual_plugin_id.lower() != plugin_id_for_path:
                raise ValueError(f"恢复后的插件类名 {actual_plugin_id} 与备份插件目录不匹配")

            dependencies_status = self._finalize_plugin_installation(actual_plugin_id, target_dir)
            logger.info(f"插件 {actual_plugin_id} 已从备份恢复安装成功")
            return True, f"插件 {actual_plugin_id} 已成功从备份恢复安装。请刷新页面在插件管理页面手动启用。", dependencies_status
        except Exception as e:
            logger.error(f"恢复插件备份失败: {e}", exc_info=True)
            return False, f"恢复插件失败: {e}", {"status": "error", "message": f"恢复插件失败: {e}"}

    def _install_plugin(self, plugin_id: str, extract_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """
        安装插件
        
        Args:
            plugin_id: 插件ID
            extract_path: 解压后的插件路径
            
        Returns:
            Tuple[bool, str, Dict[str, Any]]: (是否成功, 消息, 依赖安装信息)
        """
        backup_zip_path = None
        target_dir = None
        
        try:
            # 统一插件ID为小写（仅用于文件路径）
            plugin_id_for_path = plugin_id.lower()
            target_dir = Path("/app/app/plugins") / plugin_id_for_path

            # 备份现有插件（如果存在）
            if target_dir.exists():
                if self._config.get("backup_enabled", True):
                    backup_root_dir = self.get_data_path() / "backups"
                    if not backup_root_dir.exists():
                        backup_root_dir.mkdir(parents=True, exist_ok=True)
                        logger.info(f"创建插件备份目录: {backup_root_dir}")
                    backup_time = datetime.now().strftime("%Y.%m.%d_%H-%M-%S")
                    backup_zip_path = backup_root_dir / f"{plugin_id_for_path}_{backup_time}.zip"
                    self._create_plugin_backup_zip(target_dir, backup_zip_path)
                    logger.info(f"备份现有插件到压缩包: {backup_zip_path}")
                    self._cleanup_old_backups(backup_root_dir, plugin_id_for_path)
                else:
                    logger.info("备份已禁用，跳过现有插件备份。")
                
                shutil.rmtree(target_dir)
                logger.info(f"旧插件目录 {target_dir} 已删除。")
            else:
                logger.info(f"目标插件目录 {target_dir} 不存在，无需备份。")

            # 确定插件源目录
            plugin_source = None
            if (extract_path / "__init__.py").exists():
                plugin_source = extract_path
                logger.info(f"使用extract_path作为插件源目录: {plugin_source}")
            else:
                plugin_dirs = [d for d in extract_path.iterdir() if d.is_dir() and not d.name.startswith('__')]
                logger.info(f"在 {extract_path} 中找到的子目录: {[d.name for d in plugin_dirs]}")

                if plugin_dirs:
                    plugin_source = plugin_dirs[0]
                    logger.info(f"使用插件子目录作为源: {plugin_source}")
                else:
                    plugin_source = extract_path
                    logger.info(f"使用解压目录作为源: {plugin_source}")

            # 复制插件文件
            shutil.copytree(plugin_source, target_dir)
            logger.info(f"复制插件文件到: {target_dir}")
            dependencies_status = self._finalize_plugin_installation(plugin_id, target_dir)

            logger.info(f"插件 {plugin_id} 安装成功")
            return True, f"插件 {plugin_id} 已成功安装到系统。请刷新页面在插件管理页面手动启用。", dependencies_status
            
        except Exception as e:
            # 发生错误时回滚
            if backup_zip_path and target_dir:
                try:
                    self._restore_plugin_from_backup_zip(backup_zip_path, target_dir)
                    logger.info("安装失败，已从备份压缩包回滚插件")
                except Exception as restore_error:
                    logger.error(f"安装失败，回滚备份压缩包时出错: {restore_error}", exc_info=True)
            return False, f"安装过程中发生错误: {str(e)}", {"status": "error", "message": "安装失败，无法获取依赖信息"}

    async def upload_plugin(self, file: UploadFile = File(...)) -> JSONResponse:
        """
        处理插件ZIP包上传和安装
        
        Args:
            file: 上传的ZIP文件
            
        Returns:
            JSONResponse: 安装结果
        """
        logger.debug("=== LocalUploadPlugin: 开始处理插件上传 ===")
        
        # 检查并发安装
        if not self._install_lock.acquire(blocking=False):
            logger.warning("检测到其他插件正在安装中，拒绝并发安装请求")
            return JSONResponse(status_code=429, content={
                "code": 429,
                "message": "检测到其他插件正在安装中，请等待当前安装完成后再试"
            })
        
        # 检查插件是否启用
        if not self.get_state():
            logger.warning("本地插件安装插件未启用，拒绝上传请求")
            self._install_lock.release() 
            return JSONResponse(status_code=403, content={
                "code": 403,
                "message": "本地插件安装插件未启用，请在插件设置中启用后重试"
            })

        temp_path = Path(self._config.get('temp_path'))
        save_path = None
        extract_path = None
        
        try:
            logger.info(f"开始处理插件上传: {file.filename}")

            # 检查文件大小
            try:
                file.file.seek(0, os.SEEK_END)
                file_size = file.file.tell()
                file.file.seek(0)
            except Exception as e:
                 logger.error(f"检查文件大小失败: {e}")
                 if file and hasattr(file, 'file') and not file.file.closed:
                     try:
                         file.file.close()
                     except Exception as close_e:
                         logger.warning(f"关闭文件句柄时出错: {close_e}")
                 return JSONResponse(status_code=500, content={
                     "code": 500, "message": "无法检查文件大小"
                 })

            if file_size > self._config.get('max_file_size'):
                msg = f"文件大小超过限制：{self._config.get('max_file_size') / 1024 / 1024:.1f}MB"
                logger.warning(f"{file.filename}: {msg} (实际大小: {file_size} bytes)")
                if file and hasattr(file, 'file') and not file.file.closed:
                     try:
                         file.file.close()
                     except Exception as close_e:
                         logger.warning(f"关闭文件句柄时出错: {close_e}")
                return JSONResponse(status_code=400, content={"code": 400, "message": msg})
            
            # 检查文件类型
            if not file.filename or not file.filename.lower().endswith('.zip'):
                msg = "只支持ZIP格式的插件包"
                logger.warning(f"{file.filename}: {msg}")
                if file and hasattr(file, 'file') and not file.file.closed:
                     try:
                         file.file.close()
                     except Exception as close_e:
                         logger.warning(f"关闭文件句柄时出错: {close_e}")
                return JSONResponse(status_code=400, content={"code": 400, "message": msg})

            # 保存文件
            save_path = temp_path / file.filename
            logger.info(f"保存文件到: {save_path}")
            try:
                with save_path.open('wb') as buffer:
                    shutil.copyfileobj(file.file, buffer)
                if file and hasattr(file, 'file') and not file.file.closed:
                    file.file.close()
                    logger.debug("上传文件句柄已关闭")
            except Exception as e:
                logger.error(f"保存文件失败 {save_path}: {e}")
                if file and hasattr(file, 'file') and not file.file.closed:
                     try:
                         file.file.close()
                     except Exception as close_e:
                         logger.warning(f"关闭文件句柄时出错: {close_e}")
                return JSONResponse(status_code=500, content={"code": 500, "message": f"保存文件失败: {e}"})

            # 处理ZIP文件
            plugin_id_for_manager = None
            try:
                logger.info(f"开始处理ZIP文件: {save_path}")
                with zipfile.ZipFile(save_path, 'r') as zip_ref:
                    all_files = zip_ref.namelist()
                    logger.info(f"ZIP包内文件列表: {all_files}")
                    
                    # 查找__init__.py文件
                    init_files = [f for f in all_files if f.endswith('__init__.py')]
                    if not init_files:
                        msg = "ZIP包中未找到__init__.py文件"
                        logger.error(msg)
                        return JSONResponse(status_code=400, content={"code": 400, "message": msg})
                    
                    # 推断插件目录名
                    init_path = init_files[0]
                    path_parts = Path(init_path).parts
                    if len(path_parts) >= 2:
                        plugin_dir_name_temp = path_parts[0].lower()
                    else:
                        plugin_dir_name_temp = save_path.stem.lower()
                    
                    logger.info(f"确定用于文件系统路径的插件目录名为: {plugin_dir_name_temp}")
                    
                    # 创建解压目录
                    final_extract_root_path = temp_path / plugin_dir_name_temp
                    if final_extract_root_path.exists():
                        logger.info(f"清理已存在的最终解压目录: {final_extract_root_path}")
                        shutil.rmtree(final_extract_root_path)
                    final_extract_root_path.mkdir(parents=True, exist_ok=True)
                    
                    logger.info(f"开始解压到最终目录: {final_extract_root_path}")

                    # 检查是否需要跳过根目录
                    first_file_parts = Path(all_files[0]).parts if all_files else []
                    skip_first_dir = False
                    if len(first_file_parts) > 0 and first_file_parts[0].lower() == plugin_dir_name_temp:
                        skip_first_dir = True
                        logger.info(f"检测到ZIP包内包含根目录 '{plugin_dir_name_temp}'，解压时将跳过此目录。")
                    
                    # 解压文件
                    for file_info in zip_ref.infolist():
                        if '__MACOSX' in file_info.filename:
                            continue
                            
                        source_path_in_zip = Path(file_info.filename)
                        target_sub_path = source_path_in_zip
                        if skip_first_dir and len(source_path_in_zip.parts) > 1 and source_path_in_zip.parts[0].lower() == plugin_dir_name_temp:
                            target_sub_path = Path(*source_path_in_zip.parts[1:])
                        
                        target_file_path = final_extract_root_path / target_sub_path
                        target_file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        if not file_info.is_dir():
                            with zip_ref.open(file_info) as source, open(target_file_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                    
                    extract_path = final_extract_root_path
                    logger.info(f"解压完成，插件实际解压到: {extract_path}")

            except zipfile.BadZipFile:
                msg = "无效或损坏的ZIP文件"
                logger.error(f"{save_path}: {msg}")
                return JSONResponse(status_code=400, content={"code": 400, "message": msg})
            except Exception as e:
                msg = f"处理ZIP文件时出错: {e}"
                logger.error(f"{save_path}: {msg}", exc_info=True)
                return JSONResponse(status_code=500, content={"code": 500, "message": msg})
            
            # 验证插件结构
            is_valid, plugin_id_for_manager, plugin_display_name, error_msg = self._validate_plugin_structure(extract_path, plugin_dir_name_temp)
            if not is_valid:
                return JSONResponse(status_code=400, content={"code": 400, "message": error_msg})
                    
            logger.info(f"插件结构验证通过，插件ID (用于PluginManager): {plugin_id_for_manager}")
                
            # 安装插件
            success, message, dependencies_status = self._install_plugin(plugin_id_for_manager, extract_path)
                                
            if success:
                return JSONResponse(status_code=200, content={
                    "code": 200,
                    "message": message,
                    "data": {
                        "plugin_id": plugin_id_for_manager,
                        "plugin_display_name": plugin_display_name,
                        "dependencies": dependencies_status
                    }
                })
            else:
                return JSONResponse(status_code=500, content={
                    "code": 500,
                    "message": message
                })

        except Exception as e:
            logger.error(f"插件上传处理失败: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={
                "code": 500,
                "message": f"插件上传处理失败：{e}"
            })

        finally:
            # 清理临时资源
            logger.debug("开始清理临时资源...")
            
            if extract_path and extract_path.exists():
                try:
                    shutil.rmtree(extract_path)
                    logger.info(f"清理临时解压目录: {extract_path}")
                except Exception as e:
                    logger.error(f"清理目录失败 {extract_path}: {e}")
            
            if save_path and save_path.exists():
                try:
                    save_path.unlink()
                    logger.info(f"清理临时ZIP文件: {save_path}")
                except Exception as e:
                    logger.error(f"清理文件失败 {save_path}: {e}")
            
            if file and hasattr(file, 'file') and not file.file.closed:
                try:
                    file.file.close()
                    logger.debug("最终清理：上传文件句柄已关闭")
                except Exception as e:
                    logger.warning(f"关闭上传文件句柄时出错: {e}")
            
            logger.debug("临时资源清理完成")
            self._install_lock.release()
            logger.debug("安装锁已释放")

    def get_api(self) -> List[Dict[str, Any]]:
        """注册API接口"""
        return [
            {
                "path": "/localupload",
                "endpoint": self.upload_plugin,
                "methods": ["POST"],
                "summary": "上传插件",
                "description": "上传本地ZIP插件包进行安装"
            },
            {
                "path": "/install_status",
                "endpoint": self.get_install_status,
                "methods": ["GET"],
                "summary": "获取安装状态",
                "description": "获取当前插件安装状态"
            },
            {
                "path": "/backup_list",
                "endpoint": self.get_backup_list,
                "methods": ["GET"],
                "summary": "获取备份列表",
                "description": "获取插件备份列表"
            },
            {
                "path": "/restore_backup",
                "endpoint": self.restore_backup,
                "methods": ["POST"],
                "summary": "恢复备份",
                "description": "从备份恢复安装插件"
            },
            {
                "path": "/delete_backup",
                "endpoint": self.delete_backup,
                "methods": ["POST"],
                "summary": "删除备份",
                "description": "删除指定插件备份 ZIP"
            }
        ]

    async def get_install_status(self) -> JSONResponse:
        """获取当前安装状态"""
        is_installing = self._install_lock.locked()
        return JSONResponse(status_code=200, content={
            "code": 200,
            "data": {
                "is_installing": is_installing
            }
        })

    async def get_backup_list(self) -> JSONResponse:
        """获取插件备份列表。"""
        try:
            backups = self._list_backup_groups()
            return JSONResponse(status_code=200, content={
                "code": 200,
                "data": backups
            })
        except Exception as e:
            logger.error(f"获取备份列表失败: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={
                "code": 500,
                "message": f"获取备份列表失败: {e}"
            })

    async def restore_backup(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        """从备份恢复安装插件。"""
        if not self._install_lock.acquire(blocking=False):
            return JSONResponse(status_code=429, content={
                "code": 429,
                "message": "检测到其他插件正在安装中，请等待当前安装完成后再试"
            })

        try:
            if not self.get_state():
                return JSONResponse(status_code=403, content={
                    "code": 403,
                    "message": "本地插件安装插件未启用，请在插件设置中启用后重试"
                })

            plugin_id = str((payload or {}).get("plugin_id") or "").strip()
            backup_file = str((payload or {}).get("backup_file") or "").strip()
            if not plugin_id or not backup_file:
                return JSONResponse(status_code=400, content={
                    "code": 400,
                    "message": "缺少 plugin_id 或 backup_file 参数"
                })

            success, message, dependencies_status = self._restore_plugin_install(plugin_id, backup_file)
            if success:
                return JSONResponse(status_code=200, content={
                    "code": 200,
                    "message": message,
                    "data": {
                        "plugin_id": plugin_id,
                        "backup_file": backup_file,
                        "dependencies": dependencies_status
                    }
                })

            return JSONResponse(status_code=500, content={
                "code": 500,
                "message": message,
                "data": {
                    "plugin_id": plugin_id,
                    "backup_file": backup_file,
                    "dependencies": dependencies_status
                }
            })
        finally:
            self._install_lock.release()

    async def delete_backup(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        """删除插件备份 ZIP。"""
        try:
            if not self.get_state():
                return JSONResponse(status_code=403, content={
                    "code": 403,
                    "message": "本地插件安装插件未启用，请在插件设置中启用后重试"
                })
            plugin_id = str((payload or {}).get("plugin_id") or "").strip()
            backup_file = str((payload or {}).get("backup_file") or "").strip()
            if not plugin_id or not backup_file:
                return JSONResponse(status_code=400, content={
                    "code": 400,
                    "message": "缺少 plugin_id 或 backup_file 参数"
                })
            success, message = self._delete_backup_file(plugin_id, backup_file)
            status_code = 200 if success else 500
            code = 200 if success else 500
            return JSONResponse(status_code=status_code, content={
                "code": code,
                "message": message,
                "data": {
                    "plugin_id": plugin_id,
                    "backup_file": backup_file
                }
            })
        except Exception as e:
            logger.error(f"删除备份失败: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={
                "code": 500,
                "message": f"删除备份失败: {e}"
            })

    def get_service(self) -> List[Dict[str, Any]]:
        """获取服务列表"""
        pass

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取命令列表"""
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """拼装插件配置页面"""
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mb-6',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {'class': 'px-6 pb-0'},
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {'class': 'd-flex align-center text-h6'},
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-3',
                                                    'size': 'default'
                                                },
                                                'text': 'mdi-cog'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '基本设置'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider',
                                'props': {'class': 'mx-4 my-2'}
                            },
                            {
                                'component': 'VCardText',
                                'props': {'class': 'px-6 pb-6'},
                                'content': [
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'enabled',
                                                            'label': '启用插件',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'backup_enabled',
                                                            'label': '安装时启用备份',
                                                            'color': 'info',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 4},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'backup_retention',
                                                            'label': '备份保留份数(默认10)',
                                                            'type': 'number',
                                                            'min': 1,
                                                            'step': 1,
                                                            'active': True,
                                                            'persistent-hint': True,
                                                            'placeholder': '默认保留10份'
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mb-6',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {'class': 'px-6 pb-0'},
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {'class': 'd-flex align-center text-h6 mb-0'},
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-3',
                                                    'size': 'default'
                                                },
                                                'text': 'mdi-information'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '备份说明'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider',
                                'props': {'class': 'mx-4 my-2'}
                            },
                            {
                                'component': 'VCardText',
                                'props': {'class': 'px-6 py-0'},
                                'content': [
                                    {
                                        'component': 'VList',
                                        'props': {
                                            'lines': 'two',
                                            'density': 'comfortable'
                                        }
                                        ,
                                        'content': [
                                            {
                                                'component': 'VListItem',
                                                'props': {'lines': 'two'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-items-start'},
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'primary',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-folder-zip'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '备份保存位置'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': f"备份压缩包统一保存到目录：{self.get_data_path() / 'backups'}"
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {'lines': 'two'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-items-start'},
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'success',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-archive-arrow-down'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '备份命名规则'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '备份文件名格式为“插件目录名_YYYY.MM.DD_HH-MM-SS.zip”，压缩包内部目录名保持为原插件目录名。'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {'lines': 'two'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-items-start'},
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'warning',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-broom'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '自动清理规则'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '备份时会自动跳过 __pycache__ 目录，并在超过保留份数后删除最旧的同名插件备份压缩包。'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {'lines': 'two'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-items-start'},
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-archive-refresh'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '安装失败自动回滚'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '如果新插件安装过程中发生异常，系统会自动使用刚生成的备份压缩包回滚恢复原有插件目录。'
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                ]
            }
        ], {
            "enabled": True,
            "backup_enabled": True,
            "backup_retention": 10
        }

    def get_page(self) -> List[dict]:
        """拼装插件详情页面"""
        # 获取API Token并转换为安全的JavaScript字符串
        api_token_value = settings.API_TOKEN
        js_safe_api_token = json.dumps(api_token_value)

        # 构建上传插件的JavaScript代码
        onclick_js = f"""
        (async (button) => {{
            const fileInput = document.querySelector('#localupload-file-input');
            const noticeModal = document.getElementById('localupload-notice-modal');
            const noticeText = document.getElementById('localupload-notice-text');
            const showNotice = (message) => {{
                if (noticeText) noticeText.textContent = message;
                if (noticeModal) noticeModal.style.display = 'flex';
            }};
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {{
                showNotice('请先选择一个ZIP文件！');
                return;
            }}
            const file = fileInput.files[0];
            const maxSize = {self._config.get('max_file_size', 10*1024*1024)};
            if (file.size > maxSize) {{
                 showNotice(`文件大小超过限制 (${{(maxSize / 1024 / 1024).toFixed(1)}}MB)`);
                 return;
            }}

            const formData = new FormData();
            formData.append('file', file);
            button.disabled = true;
            const originalText = button.textContent;
            button.textContent = '安装中...';
            const errorAlert = document.getElementById('localupload-error-alert');
            const successAlert = document.getElementById('localupload-success-alert');
            if (errorAlert) errorAlert.style.display = 'none';
            if (successAlert) successAlert.style.display = 'none';

            try {{
                const apiKey = {js_safe_api_token};
                const apiUrl = `/api/v1/plugin/LocalPluginInstall/localupload?apikey=${{encodeURIComponent(apiKey)}}`;
                const response = await fetch(apiUrl, {{
                    method: 'POST',
                    body: formData,
                }});

                const result = await response.json();
                if (response.ok && result.code === 200) {{
                    if (successAlert) {{
                        let successMessage = result.data?.plugin_display_name || result.message || '插件安装成功！';
                        successMessage = `插件 "${{successMessage}}" 已成功安装到系统。请刷新页面在插件管理页面手动启用。`;
                        
                        if (result.data && result.data.dependencies) {{
                            const deps = result.data.dependencies;
                            if (deps.total_count > 0) {{
                                successMessage += '<br><br><strong>依赖安装详情：</strong>';
                                successMessage += '<br>• 总依赖数量：' + deps.total_count + ' 个';
                                successMessage += '<br>• 成功安装：' + deps.success_count + ' 个';
                                successMessage += '<br>• 安装失败：' + deps.failed_count + ' 个';
                                successMessage += '<br>• 安装状态：' + (deps.status === 'success' ? '✅ 成功' : '❌ 失败');
                                if (deps.message) {{
                                    successMessage += '<br>• 详细信息：' + deps.message;
                                }}
                                if (deps.details && deps.details.length > 0) {{
                                    const lastDetail = deps.details[deps.details.length - 1];
                                    if (lastDetail.installed_packages && lastDetail.installed_packages.length > 0) {{
                                        successMessage += '<br>• 已安装包：' + lastDetail.installed_packages.join(', ');
                                    }}
                                }}
                            }} else {{
                                successMessage += '<br><br><strong>依赖安装：</strong>无需安装依赖';
                            }}
                        }}
                        successAlert.innerHTML = successMessage;
                        successAlert.style.whiteSpace = 'pre-line';
                        successAlert.style.display = 'block';
                    }} else {{
                        alert('成功: ' + (result.message || '插件安装成功！'));
                    }}
                    if (fileInput) fileInput.value = '';
                }} else if (response.status === 429) {{
                    const errorMsg = result.message || '检测到其他插件正在安装中，请等待当前安装完成后再试';
                    if (errorAlert) {{
                        errorAlert.innerHTML = errorMsg;
                        errorAlert.style.display = 'block';
                    }} else {{
                        alert('提示: ' + errorMsg);
                    }}
                }} else {{
                    const errorMsg = result.message || '安装失败，状态码: ' + response.status;
                    if (errorAlert) {{
                        let errorMessage = errorMsg;
                        if (result.data && result.data.dependencies) {{
                            const deps = result.data.dependencies;
                            errorMessage += '<br><br><strong>依赖安装详情：</strong>';
                            if (deps.total_count > 0) {{
                                errorMessage += '<br>• 总依赖数量：' + deps.total_count + ' 个';
                                errorMessage += '<br>• 成功安装：' + deps.success_count + ' 个';
                                errorMessage += '<br>• 安装失败：' + deps.failed_count + ' 个';
                                errorMessage += '<br>• 安装状态：' + (deps.status === 'success' ? '✅ 成功' : '❌ 失败');
                            }} else {{
                                errorMessage += '<br>• 无需安装依赖';
                            }}
                            if (deps.message) {{
                                errorMessage += '<br>• 详细信息：' + deps.message;
                            }}
                        }}
                        errorAlert.innerHTML = errorMessage;
                        errorAlert.style.whiteSpace = 'pre-line';
                        errorAlert.style.display = 'block';
                    }} else {{
                        alert('失败: ' + errorMsg);
                    }}
                }}

            }} catch (error) {{
                const errorMsg = '请求发送失败: ' + error;
                if (errorAlert) {{
                    errorAlert.textContent = errorMsg;
                    errorAlert.style.display = 'block';
                }} else {{
                    alert(errorMsg);
                }}
                console.error("Fetch error:", error);

            }} finally {{
                button.disabled = false;
                button.textContent = originalText;
            }}
        }})(this)
        """

        restore_onclick_js = f"""
        (async (button) => {{
            const errorAlert = document.getElementById('localupload-error-alert');
            const successAlert = document.getElementById('localupload-success-alert');
            const modal = document.getElementById('localupload-backup-modal');
            const backupContainer = document.getElementById('localupload-backup-list-container');
            const confirmModal = document.getElementById('localupload-confirm-modal');
            const confirmText = document.getElementById('localupload-confirm-text');
            const confirmIconWrap = document.getElementById('localupload-confirm-icon-wrap');
            const confirmCancelBtn = document.getElementById('localupload-confirm-cancel');
            const confirmOkBtn = document.getElementById('localupload-confirm-ok');
            const confirmIconPathMap = {{
                'mdi-alert': 'M13 14H11V9H13M13 18H11V16H13M1 21H23L12 2L1 21Z',
                'mdi-delete-alert': 'M9 3V4H4V6H5V19A2 2 0 0 0 7 21H17A2 2 0 0 0 19 19V6H20V4H15V3H9M7 6H17V19H7V6M9 8V17H11V8H9M13 8V17H15V8H13Z',
                'mdi-backup-restore': 'M12 3A9 9 0 0 0 3 12H0L4 16L8 12H5A7 7 0 1 1 12 19C10.39 19 8.9 18.45 7.72 17.53L6.29 18.96A8.96 8.96 0 0 0 12 21A9 9 0 0 0 12 3Z'
            }};
            const renderConfirmIcon = (iconName, iconColor) => {{
                if (!confirmIconWrap) {{
                    return;
                }}

                confirmIconWrap.replaceChildren();
                confirmIconWrap.style.color = iconColor;

                const svgNs = 'http://www.w3.org/2000/svg';
                const svg = document.createElementNS(svgNs, 'svg');
                svg.setAttribute('viewBox', '0 0 24 24');
                svg.setAttribute('width', '22');
                svg.setAttribute('height', '22');
                svg.setAttribute('fill', 'currentColor');
                svg.setAttribute('aria-hidden', 'true');

                const path = document.createElementNS(svgNs, 'path');
                path.setAttribute('d', confirmIconPathMap[iconName] || confirmIconPathMap['mdi-alert']);
                svg.appendChild(path);
                confirmIconWrap.appendChild(svg);
            }};
            const closeModal = () => {{
                if (modal) modal.style.display = 'none';
            }};
            const openModal = () => {{
                if (modal) modal.style.display = 'flex';
            }};
            const showConfirm = (message, confirmTextValue = '确认', confirmButtonColor = '#ef4444', confirmIconName = 'mdi-alert', confirmIconColor = '#ef4444') => new Promise((resolve) => {{
                if (!confirmModal || !confirmText || !confirmCancelBtn || !confirmOkBtn) {{
                    resolve(false);
                    return;
                }}

                confirmText.textContent = message;
                confirmOkBtn.textContent = confirmTextValue;
                confirmOkBtn.style.background = confirmButtonColor;
                renderConfirmIcon(confirmIconName, confirmIconColor);
                confirmModal.style.display = 'flex';
                const cleanup = () => {{
                    confirmModal.style.display = 'none';
                    confirmCancelBtn.onclick = null;
                    confirmOkBtn.onclick = null;
                }};

                confirmCancelBtn.onclick = () => {{
                    cleanup();
                    resolve(false);
                }};

                confirmOkBtn.onclick = () => {{
                    cleanup();
                    resolve(true);
                }};
            }});

            if (errorAlert) errorAlert.style.display = 'none';
            if (successAlert) successAlert.style.display = 'none';

            const formatSize = (size) => {{
                if (!size) return '0 B';
                const units = ['B', 'KB', 'MB', 'GB'];
                let value = size;
                let index = 0;
                while (value >= 1024 && index < units.length - 1) {{
                    value /= 1024;
                    index += 1;
                }}
                return `${{value.toFixed(index === 0 ? 0 : 2)}} ${{units[index]}}`;
            }};

            const renderDependencies = (deps) => {{
                if (!deps) return '';
                if (!deps.total_count) return '<br><br><strong>依赖安装：</strong>无需安装依赖';
                let html = '<br><br><strong>依赖安装详情：</strong>';
                html += '<br>• 总依赖数量：' + (deps.total_count || 0) + ' 个';
                html += '<br>• 成功安装：' + (deps.success_count || 0) + ' 个';
                html += '<br>• 安装失败：' + (deps.failed_count || 0) + ' 个';
                html += '<br>• 安装状态：' + (deps.status === 'success' ? '✅ 成功' : '❌ 失败');
                if (deps.message) {{
                    html += '<br>• 详细信息：' + deps.message;
                }}
                return html;
            }};

            const loadBackupList = async () => {{
                backupContainer.innerHTML = '<div class="text-medium-emphasis">正在加载备份列表...</div>';

                const apiKey = {js_safe_api_token};
                const response = await fetch(`/api/v1/plugin/LocalPluginInstall/backup_list?apikey=${{encodeURIComponent(apiKey)}}`);
                const result = await response.json();

                if (!(response.ok && result.code === 200)) {{
                    throw new Error(result.message || '获取备份列表失败');
                }}

                const groups = result.data || [];
                if (!groups.length) {{
                    backupContainer.innerHTML = '<div class="text-medium-emphasis">暂无可用备份。</div>';
                    return;
                }}

                const modalTitle = document.getElementById('localupload-backup-modal-title');
                if (modalTitle) {{
                    const modalTitleText = modalTitle.querySelector('.localupload-backup-modal-title-text');
                    if (modalTitleText) {{
                        modalTitleText.textContent = '备份管理 - 共 ' + groups.reduce((sum, group) => sum + (group.backups ? group.backups.length : 0), 0) + ' 个备份';
                    }}
                }}

                const html = groups.map((group, groupIndex) => {{
                    const backups = group.backups || [];
                    const rows = backups.map((backup, backupIndex) => `
                        <div class="localupload-backup-row" style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-top:1px solid rgba(128,128,128,.15);flex-wrap:wrap;">
                            <div style="min-width:260px;flex:1;">
                                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-weight:600;word-break:break-all;">
                                    <span>${{backup.filename}}</span>
                                    ${{backupIndex === 0 ? '<span class="localupload-backup-latest-tag" style="display:inline-flex;align-items:center;height:22px;padding:0 8px;border-radius:999px;background:rgba(34,197,94,.12);color:#16a34a;font-size:12px;font-weight:700;line-height:1;">最新</span>' : ''}}
                                </div>
                                <div class="localupload-backup-meta" style="font-size:12px;color:rgba(128,128,128,.9);margin-top:4px;">
                                    备份时间：${{backup.modified_time}} ｜ 文件大小：${{formatSize(backup.size)}}
                                </div>
                            </div>
                            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                                <button
                                    type="button"
                                    class="localupload-delete-backup-btn"
                                    data-plugin-id="${{group.plugin_id}}"
                                    data-plugin-name="${{group.plugin_name}}"
                                    data-backup-file="${{backup.filename}}"
                                    style="border:1px solid rgba(239,68,68,.32);border-radius:8px;padding:5px 14px;background:#fff;color:#ef4444;cursor:pointer;font-weight:600;font-size:13px;line-height:1.2;"
                                >删除</button>
                                <button
                                    type="button"
                                    class="localupload-restore-btn"
                                    data-plugin-id="${{group.plugin_id}}"
                                    data-plugin-name="${{group.plugin_name}}"
                                    data-backup-file="${{backup.filename}}"
                                    style="border:none;border-radius:8px;padding:5px 14px;background:#16b1ff;color:#fff;cursor:pointer;font-weight:600;font-size:13px;line-height:1.2;"
                                >恢复</button>
                            </div>
                        </div>
                    `).join('');

                    return `
                        <details class="localupload-backup-group" ${{groupIndex === 0 ? 'open' : ''}} style="border:1px solid rgba(128,128,128,.2);border-radius:12px;padding:12px 16px;background:rgba(22,177,255,.04);margin-bottom:12px;overflow:hidden;">
                            <summary class="localupload-backup-summary" style="cursor:pointer;font-weight:700;outline:none;">${{group.plugin_name}} <span class="localupload-backup-summary-count" style="color:rgba(128,128,128,.9);font-weight:400;">(${{backups.length}} 个备份)</span></summary>
                            <div class="localupload-backup-group-body" style="margin-top:12px;max-height:320px;overflow-y:auto;padding-right:4px;box-sizing:border-box;">${{rows}}</div>
                        </details>
                    `;
                }}).join('');

                backupContainer.innerHTML = html;
                bindBackupAccordions();
                bindDeleteButtons();
                bindRestoreButtons();
            }};

            const bindDeleteButtons = () => {{
                backupContainer.querySelectorAll('.localupload-delete-backup-btn').forEach((item) => {{
                    item.addEventListener('click', async (event) => {{
                        const actionButton = event.currentTarget;
                        const pluginId = actionButton.getAttribute('data-plugin-id');
                        const pluginName = actionButton.getAttribute('data-plugin-name') || pluginId;
                        const backupFile = actionButton.getAttribute('data-backup-file');
                        if (!pluginId || !backupFile) return;

                        const confirmed = await showConfirm(`确认删除插件 ${{pluginName}} 的备份文件：${{backupFile}} 吗？`, '确认删除', '#ef4444', 'mdi-delete-alert', '#ef4444');
                        if (!confirmed) {{
                            return;
                        }}

                        actionButton.disabled = true;
                        const originalText = actionButton.textContent;
                        actionButton.textContent = '删除中...';

                        try {{
                            const apiKey = {js_safe_api_token};
                            const response = await fetch(`/api/v1/plugin/LocalPluginInstall/delete_backup?apikey=${{encodeURIComponent(apiKey)}}`, {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ plugin_id: pluginId, backup_file: backupFile }})
                            }});
                            const result = await response.json();

                            if (response.ok && result.code === 200) {{
                                if (successAlert) {{
                                    successAlert.textContent = result.message || '删除成功';
                                    successAlert.style.display = 'block';
                                }}
                                await loadBackupList();
                            }} else {{
                                if (errorAlert) {{
                                    errorAlert.textContent = result.message || '删除失败';
                                    errorAlert.style.display = 'block';
                                }}
                            }}
                        }} catch (error) {{
                            if (errorAlert) {{
                                errorAlert.textContent = '删除请求发送失败: ' + error;
                                errorAlert.style.display = 'block';
                            }}
                            console.error('Delete backup error:', error);
                        }} finally {{
                            actionButton.disabled = false;
                            actionButton.textContent = originalText;
                        }}
                    }});
                }});
            }};

            const bindRestoreButtons = () => {{
                backupContainer.querySelectorAll('.localupload-restore-btn').forEach((item) => {{
                    item.addEventListener('click', async (event) => {{
                        const actionButton = event.currentTarget;
                        const pluginId = actionButton.getAttribute('data-plugin-id');
                        const pluginName = actionButton.getAttribute('data-plugin-name') || pluginId;
                        const backupFile = actionButton.getAttribute('data-backup-file');
                        if (!pluginId || !backupFile) return;

                        const confirmed = await showConfirm(`确认恢复插件 ${{pluginName}} 的备份文件：${{backupFile}} 吗？`, '确认恢复', '#16b1ff', 'mdi-backup-restore', '#16b1ff');
                        if (!confirmed) {{
                            return;
                        }}

                        actionButton.disabled = true;
                        const originalText = actionButton.textContent;
                        actionButton.textContent = '恢复中...';

                        try {{
                            const apiKey = {js_safe_api_token};
                            const response = await fetch(`/api/v1/plugin/LocalPluginInstall/restore_backup?apikey=${{encodeURIComponent(apiKey)}}`, {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ plugin_id: pluginId, backup_file: backupFile }})
                            }});
                            const result = await response.json();

                            if (response.ok && result.code === 200) {{
                                if (successAlert) {{
                                    successAlert.innerHTML = (result.message || '恢复成功') + renderDependencies(result.data?.dependencies);
                                    successAlert.style.whiteSpace = 'pre-line';
                                    successAlert.style.display = 'block';
                                }}
                                closeModal();
                            }} else {{
                                if (errorAlert) {{
                                    errorAlert.innerHTML = (result.message || '恢复失败') + renderDependencies(result.data?.dependencies);
                                    errorAlert.style.whiteSpace = 'pre-line';
                                    errorAlert.style.display = 'block';
                                }}
                            }}
                        }} catch (error) {{
                            if (errorAlert) {{
                                errorAlert.textContent = '恢复请求发送失败: ' + error;
                                errorAlert.style.display = 'block';
                            }}
                            console.error('Restore backup error:', error);
                        }} finally {{
                            actionButton.disabled = false;
                            actionButton.textContent = originalText;
                        }}
                    }});
                }});
            }};

            const bindBackupAccordions = () => {{
                const detailItems = backupContainer.querySelectorAll('.localupload-backup-group');
                detailItems.forEach((detail) => {{
                    detail.addEventListener('toggle', () => {{
                        if (!detail.open) return;
                        detailItems.forEach((other) => {{
                            if (other !== detail) {{
                                other.open = false;
                            }}
                        }});
                    }});
                }});
            }};

            try {{
                button.disabled = true;
                button.textContent = '加载中...';
                openModal();
                await loadBackupList();
            }} catch (error) {{
                backupContainer.innerHTML = '<div style="color:#ff5252;">' + error + '</div>';
                if (errorAlert) {{
                    errorAlert.textContent = '获取备份列表失败: ' + error;
                    errorAlert.style.display = 'block';
                }}
                console.error('Load backup list error:', error);
            }} finally {{
                button.disabled = false;
                button.textContent = '从备份恢复';
            }}
        }})(this)
        """

        page_structure = [
             {
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12},
                        'content': [
                            {
                                'component': 'VCard',
                                'props': {
                                    'elevation': 3,
                                    'class': 'mx-auto rounded-lg',
                                    'border': True
                                },
                                'content': [
                                    {
                                        'component': 'VCardItem',
                                        'props': {
                                            'class': 'pb-0 d-flex flex-column align-center justify-center'
                                        },
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'class': 'mb-2'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VCardTitle',
                                                        'props': {
                                                            'class': 'text-h5 font-weight-bold d-flex align-center justify-center'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'info',
                                                                    'size': 'large',
                                                                    'class': 'mr-2'
                                                                },
                                                                'text': 'mdi-upload'
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': '上传插件'
                                                            }
                                                        ]
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'class': 'text-center mb-2'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VCardSubtitle',
                                                        'props': {
                                                            'class': 'text-medium-emphasis'
                                                        },
                                                        'text': '上传本地ZIP插件包进行安装'
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VDivider',
                                        'props': {
                                            'class': 'mx-4 my-2'
                                        }
                                    },
                                    {
                                        'component': 'VContainer',
                                        'props': {
                                            'class': 'px-md-10 py-4',
                                            'max-width': '800'
                                        },
                                        'content': [
                                            {
                                                'component': 'VCardText',
                                                'content': [
                                                    { # 信息提示
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'info',
                                                            'variant': 'tonal',
                                                            'text': '请确保插件包包含__init__.py文件且继承_PluginBase类。如果插件有依赖，请确保包含requirements.txt文件。',
                                                            'class': 'mb-6',
                                                            'density': 'comfortable',
                                                            'icon': 'mdi-information',
                                                            'elevation': 1,
                                                            'rounded': 'lg'
                                                        }
                                                    },
                                                    { # 成功提示
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'success',
                                                            'variant': 'tonal',
                                                            'class': 'mb-6',
                                                            'density': 'comfortable',
                                                            'border': 'start',
                                                            'icon': 'mdi-check-circle',
                                                            'elevation': 1,
                                                            'rounded': 'lg',
                                                            'id': 'localupload-success-alert',
                                                            'style': 'display: none;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-1'
                                                                }
                                                            }
                                                        ]
                                                    },
                                                    { # 错误提示
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'error',
                                                            'variant': 'tonal',
                                                            'class': 'mb-6',
                                                            'density': 'comfortable',
                                                            'border': 'start',
                                                            'icon': 'mdi-alert',
                                                            'elevation': 1,
                                                            'rounded': 'lg',
                                                            'id': 'localupload-error-alert',
                                                            'style': 'display: none;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-1'
                                                                }
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VSheet',
                                                        'props': {
                                                            'class': 'pa-6',
                                                            'rounded': 'lg',
                                                            'elevation': 0,
                                                            'border': True,
                                                            'color': 'background'
                                                        },
                                                        'content': [
                                                            { # 文件输入框
                                                                'component': 'VFileInput',
                                                                'props': {
                                                                    'model': 'file',
                                                                    'label': '选择插件ZIP包',
                                                                    'hint': f'最大文件大小：{self._config.get("max_file_size") / 1024 / 1024:.1f}MB',
                                                                    'persistent-hint': True,
                                                                    'chips': True,
                                                                    'multiple': False,
                                                                    'show-size': True,
                                                                    'accept': '.zip',
                                                                    'prepend-icon': 'mdi-folder-zip',
                                                                    'size': 'x-large',
                                                                    'height': '64',
                                                                    'variant': 'outlined',
                                                                    'class': 'mb-6 custom-file-input',
                                                                    'style': 'font-size: 24px;',
                                                                    'id': 'localupload-file-input',
                                                                    'density': 'default',
                                                                    'color': 'primary',
                                                                    'bg-color': 'surface'
                                                                }
                                                            },
                                                            { # 按钮
                                                                'component': 'VRow',
                                                                'props': {
                                                                    'class': 'mt-2'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VCol',
                                                                        'props': {'cols': 12, 'md': 6},
                                                                        'content': [
                                                                            {
                                                                                'component': 'VBtn',
                                                                                'props': {
                                                                                    'color': 'primary',
                                                                                    'block': True,
                                                                                    'size': 'large',
                                                                                    'onclick': onclick_js,
                                                                                    'id': 'localupload-install-button',
                                                                                    'elevation': 2,
                                                                                    'rounded': 'lg',
                                                                                    'class': 'text-none font-weight-bold'
                                                                                },
                                                                                'content': [
                                                                                    {'component': 'span', 'text': '安装插件'}
                                                                                ]
                                                                            }
                                                                        ]
                                                                    },
                                                                    {
                                                                        'component': 'VCol',
                                                                        'props': {'cols': 12, 'md': 6},
                                                                        'content': [
                                                                            {
                                                                                'component': 'VBtn',
                                                                                'props': {
                                                                                    'color': 'info',
                                                                                    'variant': 'outlined',
                                                                                    'block': True,
                                                                                    'size': 'large',
                                                                                    'onclick': restore_onclick_js,
                                                                                    'id': 'localupload-show-backup-button',
                                                                                    'elevation': 0,
                                                                                    'rounded': 'lg',
                                                                                    'class': 'text-none font-weight-bold'
                                                                                },
                                                                                'content': [
                                                                                    {'component': 'span', 'text': '从备份恢复'}
                                                                                ]
                                                                            }
                                                                        ]
                                                                    },
                                                                ]
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            { # 添加提示信息卡片
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12},
                        'content': [
                            {
                                'component': 'VCard',
                                'props': {
                                    'variant': 'flat',
                                    'class': 'mb-6',
                                    'color': 'surface'
                                },
                                'content': [
                                    {
                                        'component': 'VCardItem',
                                        'props': {'class': 'px-6 pb-0'},
                                        'content': [
                                            {
                                                'component': 'VCardTitle',
                                                'props': {'class': 'd-flex align-center text-h6 mb-0'},
                                                'content': [
                                                    {
                                                        'component': 'VIcon',
                                                        'props': {
                                                            'style': 'color: #16b1ff;',
                                                            'class': 'mr-3',
                                                            'size': 'default',
                                                        },
                                                        'text': 'mdi-information'
                                                    },
                                                    {
                                                        'component': 'span',
                                                        'text': '插件安装说明'
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VDivider',
                                        'props': {
                                            'class': 'mx-4 my-2'
                                        }
                                    },
                                    {
                                        'component': 'VCardText',
                                        'props': {'class': 'px-6 py-0'},
                                        'content': [
                                            {
                                                'component': 'VList',
                                                'props': {
                                                    'lines': 'two',
                                                    'density': 'comfortable'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'primary',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-cog'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '首次安装'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '首次安装请点击右下角设置打开 启用插件 保存，如果安装提示'
                                                                    },
                                                                    {
                                                                        'component': 'VChip',
                                                                        'props': {
                                                                            'color': 'error',
                                                                            'size': 'small',
                                                                            'class': 'mx-1'
                                                                        },
                                                                        'text': '安装失败，状态码: 404'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '请重新打开设置页面保存一下以生效安装API'
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'success',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-folder-zip'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': 'ZIP文件结构'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '插件包必须包含以下内容：- 插件目录（如 myplugin/）- __init__.py 文件（必须继承 _PluginBase）- requirements.txt（可选，用于声明依赖）- 其他插件相关文件'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'success',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-vuejs'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': 'Vue联邦插件结构'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '支持安装 Vue 联邦插件。ZIP 可直接以文件为根目录打包，至少包含 __init__.py，以及前端构建产物目录 dist/（通常为 dist/assets/...）；如有 Python 依赖，可同时包含 requirements.txt。'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'warning',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-alert'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '注意事项'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '1. 确保插件包大小不超过限制 2. 插件ID必须与目录名一致 3. 安装前请确保插件代码安全可靠 4. 安装失败时请检查错误信息'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'warning',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-help-circle'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '常见问题'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '1. 安装失败？检查插件包结构是否正确 2. 依赖安装失败？确保requirements.txt格式正确，或尝试手动安装依赖 3. 插件不工作？检查日志获取详细信息 4. 提示"没有找到继承_PluginBase的插件类"？可能是依赖缺失，请检查requirements.txt文件'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'info',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-folder-information'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '备份路径说明'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': f'所有插件的备份文件将保存到此目录：{self.get_data_path() / "backups"}。请勿手动删除此目录下的文件，除非您确定不再需要这些备份。'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'info',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-backup-restore'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '恢复功能说明'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '点击“从备份恢复”可打开备份列表，列表会按插件名称分组显示历史备份 ZIP。展开对应插件后，选择需要的备份文件并点击“恢复”即可重新安装该版本插件。恢复时不会额外创建一次新备份，请确认所选版本无误后再执行。'
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'div',
                'props': {
                    'id': 'localupload-backup-modal',
                    'style': 'display:none;position:fixed;inset:0;z-index:3000;background:#3A354180;align-items:center;justify-content:center;padding:24px;'
                },
                'content': [
                    {
                        'component': 'div',
                        'props': {
                            'id': 'localupload-backup-modal-card',
                            'style': 'width:min(720px,100%);height:min(70vh,640px);background:#ffffff;border:1px solid rgba(226,232,240,1);border-radius:16px;box-shadow:0 12px 32px rgba(15,23,42,.16);overflow:hidden;display:flex;flex-direction:column;position:relative;'
                        },
                        'content': [
                            {
                                'component': 'div',
                                'props': {
                                    'id': 'localupload-backup-modal-header',
                                    'style': 'display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid rgba(128,128,128,.18);flex:0 0 auto;'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'id': 'localupload-backup-modal-title',
                                            'style': 'font-size:18px;font-weight:700;color:#111827;display:flex;align-items:center;'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'color': '#16b1ff',
                                                    'size': '20',
                                                    'class': 'mr-2'
                                                },
                                                'text': 'mdi-folder-download'
                                            },
                                            {
                                                'component': 'span',
                                                'props': {
                                                    'class': 'localupload-backup-modal-title-text'
                                                },
                                                'text': '选择备份并恢复安装'
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'button',
                                        'props': {
                                            'id': 'localupload-backup-modal-close',
                                            'type': 'button',
                                            'onclick': "document.getElementById('localupload-backup-modal').style.display='none'",
                                            'style': 'border:none;background:transparent;font-size:24px;line-height:1;cursor:pointer;color:#6b7280;padding:0 4px;'
                                        },
                                        'text': '×'
                                    }
                                ]
                            },
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'padding:18px 22px;overflow:hidden;flex:1;min-height:0;'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'id': 'localupload-backup-list-container',
                                            'style': 'height:100%;overflow-y:auto;overflow-x:hidden;scrollbar-width:none;-ms-overflow-style:none;padding-right:2px;'
                                        }
                                    },
                                    {
                                        'component': 'style',
                                        'text': '#localupload-backup-list-container::-webkit-scrollbar{width:0;height:0;display:none;}'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'div',
                'props': {
                    'id': 'localupload-notice-modal',
                    'style': 'display:none;position:fixed;inset:0;z-index:3001;background:#3A354180;align-items:center;justify-content:center;padding:24px;pointer-events:none;'
                },
                'content': [
                    {
                        'component': 'div',
                        'props': {
                            'id': 'localupload-notice-card',
                            'style': 'min-width:320px;max-width:min(440px,100%);background:#ffffff;border:1px solid rgba(226,232,240,1);border-radius:16px;box-shadow:0 12px 32px rgba(15,23,42,.18);padding:22px 22px 18px 22px;pointer-events:auto;'
                        },
                        'content': [
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'display:flex;align-items:flex-start;gap:14px;'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'style': 'display:flex;align-items:center;justify-content:center;flex:0 0 auto;width:28px;height:28px;color:#ef4444;font-size:20px;font-weight:700;'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'color': '#ef4444',
                                                    'size': '22'
                                                },
                                                'text': 'mdi-alert'
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'style': 'flex:1;min-width:0;'
                                        },
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'id': 'localupload-notice-title',
                                                    'style': 'font-size:16px;font-weight:700;color:#1f2937;margin-bottom:8px;'
                                                },
                                                'text': '错误提示：'
                                            },
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'id': 'localupload-notice-text',
                                                    'style': 'font-size:14px;line-height:1.6;color:#4b5563;word-break:break-word;'
                                                },
                                                'text': ''
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'display:flex;justify-content:flex-end;margin-top:18px;'
                                },
                                'content': [
                                    {
                                        'component': 'button',
                                        'props': {
                                            'id': 'localupload-notice-ok',
                                            'type': 'button',
                                            'onclick': "document.getElementById('localupload-notice-modal').style.display='none'",
                                            'style': 'border:none;border-radius:10px;padding:7px 16px;background:#16b1ff;color:#fff;font-size:13px;line-height:1.2;font-weight:700;cursor:pointer;'
                                        },
                                        'text': '知道了'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'div',
                'props': {
                    'id': 'localupload-confirm-modal',
                    'style': 'display:none;position:fixed;inset:0;z-index:3002;background:#3A354180;align-items:center;justify-content:center;padding:24px;pointer-events:none;'
                },
                'content': [
                    {
                        'component': 'div',
                        'props': {
                            'id': 'localupload-confirm-card',
                            'style': 'min-width:320px;max-width:min(460px,100%);background:#ffffff;border:1px solid rgba(226,232,240,1);border-radius:16px;box-shadow:0 12px 32px rgba(15,23,42,.18);padding:22px 22px 18px 22px;pointer-events:auto;'
                        },
                        'content': [
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'display:flex;align-items:flex-start;gap:14px;'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'id': 'localupload-confirm-icon-wrap',
                                            'style': 'display:flex;align-items:center;justify-content:center;flex:0 0 auto;width:28px;height:28px;color:#ef4444;font-size:20px;font-weight:700;'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'color': '#ef4444',
                                                    'size': '22'
                                                },
                                                'text': 'mdi-alert'
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'style': 'flex:1;min-width:0;'
                                        },
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'id': 'localupload-confirm-title',
                                                    'style': 'font-size:16px;font-weight:700;color:#1f2937;margin-bottom:8px;'
                                                },
                                                'text': '请确认操作'
                                            },
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'id': 'localupload-confirm-text',
                                                    'style': 'font-size:14px;line-height:1.6;color:#4b5563;word-break:break-word;'
                                                },
                                                'text': ''
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'display:flex;justify-content:flex-end;gap:10px;margin-top:18px;'
                                },
                                'content': [
                                    {
                                        'component': 'button',
                                        'props': {
                                            'id': 'localupload-confirm-cancel',
                                            'type': 'button',
                                            'style': 'border:1px solid rgba(148,163,184,.4);border-radius:10px;padding:7px 16px;background:#fff;color:#475569;font-size:13px;line-height:1.2;font-weight:700;cursor:pointer;'
                                        },
                                        'text': '取消'
                                    },
                                    {
                                        'component': 'button',
                                        'props': {
                                            'id': 'localupload-confirm-ok',
                                            'type': 'button',
                                            'style': 'border:none;border-radius:10px;padding:7px 16px;background:#ef4444;color:#fff;font-size:13px;line-height:1.2;font-weight:700;cursor:pointer;'
                                        },
                                        'text': '确认'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'style',
                'text': '.v-theme--dark #localupload-backup-modal,[data-theme="dark"] #localupload-backup-modal,.v-theme--dark #localupload-notice-modal,[data-theme="dark"] #localupload-notice-modal,.v-theme--dark #localupload-confirm-modal,[data-theme="dark"] #localupload-confirm-modal{background:rgba(15,23,42,.62) !important;}.v-theme--dark #localupload-backup-modal-card,[data-theme="dark"] #localupload-backup-modal-card,.v-theme--dark #localupload-notice-card,[data-theme="dark"] #localupload-notice-card,.v-theme--dark #localupload-confirm-card,[data-theme="dark"] #localupload-confirm-card{background:#111827 !important;border-color:rgba(71,85,105,.55) !important;box-shadow:0 18px 42px rgba(0,0,0,.45) !important;}.v-theme--dark #localupload-backup-modal-header,[data-theme="dark"] #localupload-backup-modal-header{border-bottom-color:rgba(71,85,105,.55) !important;}.v-theme--dark #localupload-backup-modal-title,[data-theme="dark"] #localupload-backup-modal-title,.v-theme--dark #localupload-notice-title,[data-theme="dark"] #localupload-notice-title,.v-theme--dark #localupload-confirm-title,[data-theme="dark"] #localupload-confirm-title{color:#f9fafb !important;}.v-theme--dark #localupload-backup-modal-close,[data-theme="dark"] #localupload-backup-modal-close{color:#cbd5e1 !important;}.v-theme--dark .localupload-backup-group,[data-theme="dark"] .localupload-backup-group{background:rgba(37,99,235,.12) !important;border-color:rgba(71,85,105,.55) !important;}.v-theme--dark .localupload-backup-summary,[data-theme="dark"] .localupload-backup-summary{color:#f9fafb !important;}.v-theme--dark .localupload-backup-summary-count,[data-theme="dark"] .localupload-backup-summary-count,.v-theme--dark .localupload-backup-meta,[data-theme="dark"] .localupload-backup-meta{color:#94a3b8 !important;}.v-theme--dark .localupload-backup-row,[data-theme="dark"] .localupload-backup-row{border-top-color:rgba(71,85,105,.4) !important;color:#e5e7eb !important;}.v-theme--dark .localupload-backup-group-body,[data-theme="dark"] .localupload-backup-group-body{color:#e5e7eb !important;}.v-theme--dark .localupload-delete-backup-btn,[data-theme="dark"] .localupload-delete-backup-btn{background:#1f2937 !important;color:#f87171 !important;border-color:rgba(248,113,113,.4) !important;}.v-theme--dark .localupload-restore-btn,[data-theme="dark"] .localupload-restore-btn{background:#0ea5e9 !important;color:#ffffff !important;}.v-theme--dark .localupload-backup-latest-tag,[data-theme="dark"] .localupload-backup-latest-tag{background:rgba(34,197,94,.18) !important;color:#86efac !important;}.v-theme--dark #localupload-notice-text,[data-theme="dark"] #localupload-notice-text,.v-theme--dark #localupload-confirm-text,[data-theme="dark"] #localupload-confirm-text{color:#cbd5e1 !important;}.v-theme--dark #localupload-confirm-cancel,[data-theme="dark"] #localupload-confirm-cancel{background:#1f2937 !important;color:#e5e7eb !important;border-color:rgba(148,163,184,.3) !important;}.v-theme--dark #localupload-notice-ok,[data-theme="dark"] #localupload-notice-ok{box-shadow:none !important;}@media (prefers-color-scheme: dark){#localupload-backup-modal,#localupload-notice-modal,#localupload-confirm-modal{background:rgba(15,23,42,.62) !important;}#localupload-backup-modal-card,#localupload-notice-card,#localupload-confirm-card{background:#111827 !important;border-color:rgba(71,85,105,.55) !important;box-shadow:0 18px 42px rgba(0,0,0,.45) !important;}#localupload-backup-modal-header{border-bottom-color:rgba(71,85,105,.55) !important;}#localupload-backup-modal-title,#localupload-notice-title,#localupload-confirm-title{color:#f9fafb !important;}#localupload-backup-modal-close{color:#cbd5e1 !important;} .localupload-backup-group{background:rgba(37,99,235,.12) !important;border-color:rgba(71,85,105,.55) !important;} .localupload-backup-summary{color:#f9fafb !important;} .localupload-backup-summary-count,.localupload-backup-meta{color:#94a3b8 !important;} .localupload-backup-row{border-top-color:rgba(71,85,105,.4) !important;color:#e5e7eb !important;} .localupload-backup-group-body{color:#e5e7eb !important;} .localupload-delete-backup-btn{background:#1f2937 !important;color:#f87171 !important;border-color:rgba(248,113,113,.4) !important;} .localupload-restore-btn{background:#0ea5e9 !important;color:#ffffff !important;} .localupload-backup-latest-tag{background:rgba(34,197,94,.18) !important;color:#86efac !important;}#localupload-notice-text,#localupload-confirm-text{color:#cbd5e1 !important;}#localupload-confirm-cancel{background:#1f2937 !important;color:#e5e7eb !important;border-color:rgba(148,163,184,.3) !important;}#localupload-notice-ok{box-shadow:none !important;}'
            }
        ]
        return page_structure

    def stop_service(self):
        """停止插件服务"""
        self._config["enabled"] = False
        logger.info("插件已停止")