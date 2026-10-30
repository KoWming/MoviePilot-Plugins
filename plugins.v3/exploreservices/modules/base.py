from typing import Any, Dict, Optional


class SourceModule:
    """
    探索源聚合模块的公共基类

    各探索源以普通类形式挂在聚合插件内，不再作为独立插件注册。配置、数据、处理链和
    运行实例标识统一由宿主插件实例owner提供，数据键按模块前缀隔离，避免多个探索源
    共用一个媒体身份缓存
    """

    plugin_name: str = ""
    _enabled: bool = False

    def __init__(self, owner: Any, module_key: str) -> None:
        """
        初始化探索源模块

        :param owner (Any): 所属聚合插件实例
        :param module_key (str): 模块标识，用于数据命名空间隔离
        """
        self._owner = owner
        self.module_key = module_key
        self._enabled = False

    @property
    def plugin_id(self) -> str:
        """
        返回宿主插件ID

        用于拼接探索数据源API地址，保证聚合后仍指向当前运行实例

        :return str: 宿主插件类名
        """
        return self._owner.__class__.__name__

    @property
    def chain(self) -> Any:
        """
        返回宿主插件处理链

        :return Any: 插件处理链实例
        """
        return self._owner.chain

    def get_state(self) -> bool:
        """
        返回模块是否启用

        :return bool: 启用状态
        """
        return bool(self._enabled)

    def set_enabled(self, enabled: bool) -> None:
        """
        设置模块启用状态

        :param enabled (bool): 是否启用
        """
        self._enabled = bool(enabled)

    def _scoped_key(self, key: str) -> str:
        """
        生成带模块前缀的数据键

        :param key (str): 原始数据键

        :return str: 隔离后的数据键
        """
        return f"{self.module_key}:{key}"

    def get_data(self, key: Optional[str] = None) -> Any:
        """
        读取模块数据

        :param key (str): 数据键，为空时返回本模块的全部数据

        :return Any: 数据值
        """
        if key is None:
            data = self._owner.get_data() or {}
            prefix = self._scoped_key("")
            if not isinstance(data, dict):
                return {}
            return {
                item_key[len(prefix):]: value
                for item_key, value in data.items()
                if isinstance(item_key, str) and item_key.startswith(prefix)
            }
        return self._owner.get_data(self._scoped_key(key))

    def save_data(self, key: str, value: Any) -> None:
        """
        保存模块数据

        :param key (str): 数据键
        :param value (Any): 数据值
        """
        self._owner.save_data(self._scoped_key(key), value)

    async def async_get_data(self, key: Optional[str] = None) -> Any:
        """
        异步读取模块数据

        :param key (str): 数据键，为空时返回本模块的全部数据

        :return Any: 数据值
        """
        if key is None:
            data = await self._owner.async_get_data() or {}
            prefix = self._scoped_key("")
            if not isinstance(data, dict):
                return {}
            return {
                item_key[len(prefix):]: value
                for item_key, value in data.items()
                if isinstance(item_key, str) and item_key.startswith(prefix)
            }
        return await self._owner.async_get_data(self._scoped_key(key))

    async def async_save_data(self, key: str, value: Any) -> None:
        """
        异步保存模块数据

        :param key (str): 数据键
        :param value (Any): 数据值
        """
        await self._owner.async_save_data(self._scoped_key(key), value)

    def stop_service(self) -> None:
        """
        停止模块运行的服务，默认无资源需要释放
        """
        return None

    def module_summary(self) -> Dict[str, Any]:
        """
        返回模块运行摘要

        :return Dict: 模块名称与启用状态
        """
        return {
            "key": self.module_key,
            "name": self.plugin_name,
            "enabled": bool(self._enabled),
        }
