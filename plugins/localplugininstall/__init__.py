import os
import shutil
import zipfile
import json
import time
import importlib.util
import sys
import threading
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional

from fastapi import UploadFile, File
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
    plugin_version = "1.2"
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
        "temp_path": "/tmp/moviepilot/upload",    # 临时文件路径
        "max_file_size": 10 * 1024 * 1024,        # 最大文件大小 10MB
        "allowed_extensions": ["zip"],            # 允许的文件扩展名
    }

    def init_plugin(self, config: dict = None):
        """初始化插件配置"""
        if config:
            self._config.update(config)
            
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
            
            if init_file.exists():
                # extract_path本身就是插件目录
                actual_plugin_dir_name_from_fs = extract_path.name.lower()
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

    def _install_plugin(self, plugin_id: str, extract_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """
        安装插件
        
        Args:
            plugin_id: 插件ID
            extract_path: 解压后的插件路径
            
        Returns:
            Tuple[bool, str, Dict[str, Any]]: (是否成功, 消息, 依赖安装信息)
        """
        backup_dir = None
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

                    backup_dir = backup_root_dir / f"{plugin_id_for_path}_{int(time.time())}"
                    shutil.copytree(target_dir, backup_dir)
                    logger.info(f"备份现有插件到: {backup_dir}")
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

            # 配置插件状态
            plugin_manager_instance = PluginManager()
            plugin_config = plugin_manager_instance.get_plugin_config(plugin_id)
            if not plugin_config:
                 plugin_config = {"enabled": False}
                 plugin_manager_instance.save_plugin_config(plugin_id, plugin_config)
                 logger.info(f"已为插件 {plugin_id} 保存默认配置 (初始为禁用)。")
            
            # 安装依赖
            dependencies_status = self._install_dependencies(target_dir)
            if dependencies_status["status"] == "error":
                logger.warning(f"依赖安装失败: {dependencies_status['message']}")

            # 添加到已安装插件列表
            install_plugins = SystemConfigOper().get(SystemConfigKey.UserInstalledPlugins) or []
            if plugin_id not in install_plugins:
                install_plugins.append(plugin_id)
                SystemConfigOper().set(SystemConfigKey.UserInstalledPlugins, install_plugins)
                logger.info(f"插件 {plugin_id} 已添加到已安装列表。")

            # 重新加载刚安装的插件
            logger.info(f"调用 PluginManager.reload_plugin() 重新加载插件 {plugin_id}...")
            try:
                def reload_specific_plugin():
                    try:
                        plugin_manager_instance.reload_plugin(plugin_id)
                        logger.info(f"插件 {plugin_id} 重新加载完成")
                    except Exception as e:
                        logger.error(f"插件 {plugin_id} 重新加载失败: {e}")
                
                # 在后台线程中执行插件重新加载，避免阻塞主线程
                reload_thread = threading.Thread(target=reload_specific_plugin, daemon=True)
                reload_thread.start()
                reload_thread.join(timeout=5)
                if reload_thread.is_alive():
                    logger.warning(f"插件 {plugin_id} 重新加载超时，但插件可能已成功加载")

            except Exception as e:
                logger.error(f"插件 {plugin_id} 重新加载异常: {e}")

            # 等待插件加载
            time.sleep(1)

            # 刷新PluginManager实例
            try:
                plugin_manager_instance = PluginManager()
                logger.info(f"重新获取 PluginManager 实例以刷新状态...")
            except Exception as e:
                logger.error(f"重新获取 PluginManager 实例失败: {e}")

            # 注册插件服务
            Scheduler().update_plugin_job(plugin_id)
            register_plugin_api(plugin_id)
            Command().init_commands(plugin_id)

            logger.info(f"插件 {plugin_id} 安装成功")
            return True, f"插件 {plugin_id} 已成功安装到系统。请刷新页面在插件管理页面手动启用。", dependencies_status
            
        except Exception as e:
            # 发生错误时回滚
            if backup_dir and target_dir and target_dir.exists():
                shutil.rmtree(target_dir)
                shutil.copytree(backup_dir, target_dir)
                logger.info(f"安装失败，已回滚到备份")
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
                                                'component': 'VCardTitle',
                                                'props': {
                                                    'class': 'text-h5 font-weight-bold d-flex align-center justify-center'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VIcon',
                                                        'props': {
                                                            'color': 'primary',
                                                            'size': 'large',
                                                            'class': 'mr-2'
                                                        },
                                                        'text': 'mdi-cog'
                                                    },
                                                    {
                                                        'component': 'span',
                                                        'text': '插件设置'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCardSubtitle',
                                                'props': {
                                                    'class': 'text-medium-emphasis text-center'
                                                },
                                                'text': '配置本地插件安装器的行为'
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VDivider',
                                        'props': {'class': 'mx-4 my-2'}
                                    },
                                    {
                                        'component': 'VContainer',
                                        'props': {'class': 'px-md-10 py-4', 'max-width': '800'},
                                        'content': [
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
                                                    {
                                                        'component': 'VRow',
                                                        'content': [
                                                            {
                                                                'component': 'VCol',
                                                                'props': {
                                                                    'cols': 12,
                                                                    'md': 6
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VSwitch',
                                                                        'props': {
                                                                            'model': 'enabled',
                                                                            'label': '启用本地插件安装',
                                                                            'hint': '是否启用此插件，允许从本地上传并安装插件。',
                                                                            'persistent-hint': True,
                                                                            'color': 'primary'
                                                                        }
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'VCol',
                                                                'props': {
                                                                    'cols': 12,
                                                                    'md': 6
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VSwitch',
                                                                        'props': {
                                                                            'model': 'backup_enabled',
                                                                            'label': '安装时启用备份',
                                                                            'hint': '安装或更新插件时，是否自动备份旧的插件文件。',
                                                                            'persistent-hint': True,
                                                                            'color': 'primary'
                                                                        }
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
                    }
                ]
            }
        ], {
            "enabled": True,
            "backup_enabled": True
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
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {{
                alert('错误：请先选择一个ZIP文件！');
                return;
            }}
            const file = fileInput.files[0];

            const maxSize = {self._config.get('max_file_size', 10*1024*1024)};
            if (file.size > maxSize) {{
                 alert(`错误：文件大小超过限制 (${{(maxSize / 1024 / 1024).toFixed(1)}}MB)`);
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
                                                            'border': 'start',
                                                            'border-color': 'primary',
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
                                                                    {'component': 'VIcon', 'props': {'icon': 'mdi-package-variant-plus', 'class': 'mr-2'}},
                                                                    {'component': 'span', 'text': '安装插件'}
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
                                    'elevation': 2,
                                    'class': 'mx-auto rounded-lg',
                                    'border': True
                                },
                                'content': [
                                    {
                                        'component': 'VCardItem',
                                        'props': {
                                            'class': 'pb-0'
                                        },
                                        'content': [
                                            {
                                                'component': 'VCardTitle',
                                                'props': {
                                                    'class': 'text-h6 font-weight-bold d-flex align-center'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VIcon',
                                                        'props': {
                                                            'color': 'info',
                                                            'size': 'default',
                                                            'class': 'mr-2'
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
                                                        'props': {
                                                            'prepend-icon': 'mdi-cog',
                                                            'title': '首次安装'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2'
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
                                                                        'text': '请新打开设置页面保存一下以生效上传API'
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {
                                                            'prepend-icon': 'mdi-folder-zip',
                                                            'title': 'ZIP文件结构'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2'
                                                                },
                                                                'text': '插件包必须包含以下内容：- 插件目录（如 myplugin/）- __init__.py 文件（必须继承 _PluginBase）- requirements.txt（可选，用于声明依赖）- 其他插件相关文件'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {
                                                            'prepend-icon': 'mdi-alert',
                                                            'title': '注意事项'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2'
                                                                },
                                                                'text': '1. 确保插件包大小不超过限制 2. 插件ID必须与目录名一致 3. 安装前请确保插件代码安全可靠 4. 安装失败时请检查错误信息'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {
                                                            'prepend-icon': 'mdi-help-circle',
                                                            'title': '常见问题'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2'
                                                                },
                                                                'text': '1. 安装失败？检查插件包结构是否正确 2. 依赖安装失败？确保requirements.txt格式正确，或尝试手动安装依赖 3. 插件不工作？检查日志获取详细信息 4. 提示"没有找到继承_PluginBase的插件类"？可能是依赖缺失，请检查requirements.txt文件'
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
            { # 添加备份路径提示信息卡片
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12},
                        'content': [
                            {
                                'component': 'VCard',
                                'props': {
                                    'elevation': 2,
                                    'class': 'mx-auto rounded-lg',
                                    'border': True
                                },
                                'content': [
                                    {
                                        'component': 'VCardItem',
                                        'props': {
                                            'class': 'pb-0'
                                        },
                                        'content': [
                                            {
                                                'component': 'VCardTitle',
                                                'props': {
                                                    'class': 'text-h6 font-weight-bold d-flex align-center'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VIcon',
                                                        'props': {
                                                            'color': 'info',
                                                            'size': 'default',
                                                            'class': 'mr-2'
                                                        },
                                                        'text': 'mdi-folder-information' # 文件夹信息图标
                                                    },
                                                    {
                                                        'component': 'span',
                                                        'text': '备份路径说明'
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
                                        'content': [
                                            {
                                                'component': 'VAlert',
                                                'props': {
                                                    'type': 'info',
                                                    'variant': 'tonal',
                                                    'text': f"所有插件的备份文件将保存到此目录：{self.get_data_path() / 'backups'}", # 直接在这里获取路径
                                                    'class': 'mb-2',
                                                    'density': 'comfortable',
                                                    'border': 'start',
                                                    'border-color': 'info',
                                                    'icon': 'mdi-information',
                                                    'elevation': 1,
                                                    'rounded': 'lg'
                                                }
                                            },
                                            {
                                                'component': 'VAlert',
                                                'props': {
                                                    'type': 'warning',
                                                    'variant': 'tonal',
                                                    'text': '请勿手动删除此目录下的文件，除非您确定不再需要这些备份。',
                                                    'density': 'comfortable',
                                                    'border': 'start',
                                                    'border-color': 'warning',
                                                    'icon': 'mdi-alert-box',
                                                    'elevation': 1,
                                                    'rounded': 'lg'
                                                }
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
        return page_structure

    def stop_service(self):
        """停止插件服务"""
        self._config["enabled"] = False
        logger.info("插件已停止")