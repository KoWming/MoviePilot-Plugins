from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from app.sdk.events import Event, eventmanager
from app.sdk.logging import logger
from app.sdk.plugin import _PluginBase
from app.schemas import DiscoverSourceEventData
from app.schemas.types import ChainEventType, MediaSource

from .modules import MODULE_LABELS, MODULE_ORDER, build_module
from .modules.base import SourceModule as _SourceModule

MODULE_SWITCH_KEYS = tuple(f"{key}_enabled" for key in MODULE_ORDER)


class ExploreServices(_PluginBase):
    """
    探索服务聚合插件

    把多个探索数据源收拢到一个插件内统一开关，各数据源实现仍保留上游原生媒体身份、
    筛选参数和媒体识别逻辑，探索卡片、搜索与订阅链路继续指向当前聚合插件实例
    """

    # 插件名称
    plugin_name = "探索服务聚合"
    # 插件描述
    plugin_desc = "统一管理和配置所有探索数据源插件。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/ExploreServices.png"
    # 插件版本
    plugin_version = "3.0.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "exploreservices_"
    # 加载顺序
    plugin_order = 12
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _modules: Dict[str, _SourceModule] = {}
    _enabled_modules: Dict[str, bool] = {}
    _iqiyi_cookie = ""
    _iqiyi_refresh_cron = ""

    def init_plugin(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        根据配置初始化各探索源模块

        :param config (Dict): 插件配置字典
        """
        config = config or {}
        self._modules = {}
        self._enabled_modules = {}
        self._iqiyi_cookie = config.get("iqiyi_cookie") or ""
        self._iqiyi_refresh_cron = config.get("iqiyi_refresh_cron") or ""
        for module_key in MODULE_ORDER:
            enabled = bool(config.get(f"{module_key}_enabled", False))
            self._enabled_modules[module_key] = enabled
            module = build_module(self, module_key)
            self._modules[module_key] = module
            module.set_enabled(enabled)
            if not enabled:
                continue
            module_config: Dict[str, Any] = {"enabled": True}
            if module_key == "iqiyi":
                module_config["cookie"] = self._iqiyi_cookie
                module_config["refresh_cron"] = self._iqiyi_refresh_cron
            init_started = perf_counter()
            try:
                module.init_plugin(module_config)
            except Exception as err:
                logger.error(
                    f"初始化探索源 {MODULE_LABELS.get(module_key, module_key)} 失败：{err}",
                    exc_info=True,
                )
                module.set_enabled(False)
                self._enabled_modules[module_key] = False
            init_elapsed = perf_counter() - init_started
            if init_elapsed >= 1:
                logger.info(
                    f"{MODULE_LABELS.get(module_key, module_key)} 探索源初始化耗时 {init_elapsed:.2f} 秒"
                )

    def get_state(self) -> bool:
        """
        返回插件是否处于运行状态

        :return bool: 至少一个探索源启用时为真
        """
        return any(module.get_state() for module in self._modules.values())

    def _iter_enabled(self) -> List[_SourceModule]:
        """
        返回当前启用的探索源模块

        :return List: 启用的模块实例列表
        """
        return [module for module in self._modules.values() if module.get_state()]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面

        :return Tuple: 页面配置与默认数据结构
        """
        switches = [
            {
                "component": "VCol",
                "props": {"cols": 12, "md": 4},
                "content": [
                    {
                        "component": "VSwitch",
                        "props": {
                            "model": f"{module_key}_enabled",
                            "label": f"启用{MODULE_LABELS[module_key]}探索源",
                        },
                    }
                ],
            }
            for module_key in MODULE_ORDER
        ]
        form = [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VCard",
                        "props": {"class": "mt-0"},
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
                                        "text": "mdi-compass-outline",
                                    },
                                    {"component": "span", "text": "探索源开关"},
                                ],
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": switches,
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VCard",
                        "props": {"class": "mt-3"},
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
                                        "text": "mdi-video-vintage",
                                    },
                                    {"component": "span", "text": "爱奇艺 Cookie"},
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
                                                "props": {"cols": 12},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "iqiyi_cookie",
                                                            "label": "爱奇艺 Cookie",
                                                            "placeholder": "从爱奇艺浏览器复制 Cookie（含 __dfp），留空自动获取",
                                                            "variant": "outlined",
                                                            "hint": "用于绕过爱奇艺风控，支持标准字符串、浏览器表格与 JSON 格式",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            }
                                        ],
                                    },
                                    {
                                        "component": "VRow",
                                        "props": {"class": "mt-2"},
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12},
                                                "content": [
                                                    {
                                                        "component": "VCronField",
                                                        "props": {
                                                            "model": "iqiyi_refresh_cron",
                                                            "label": "爱奇艺 Cookie 定时刷新周期(cron)",
                                                            "variant": "outlined",
                                                            "color": "primary",
                                                            "hide-details": True,
                                                            "placeholder": "例如 0 */2 * * *，留空则不启用定时刷新",
                                                        },
                                                    },
                                                    {
                                                        "component": "div",
                                                        "props": {
                                                            "class": "text-caption text-medium-emphasis mt-1"
                                                        },
                                                        "text": "爱奇艺 Cookie 有效期较短，建议每 2 小时刷新一次，可在后台提前预热",
                                                    },
                                                ],
                                            }
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VCard",
                        "props": {"variant": "flat", "class": "mt-3", "color": "surface"},
                        "content": [
                            {
                                "component": "VCardItem",
                                "props": {"class": "px-6 pb-0"},
                                "content": [
                                    {
                                        "component": "VCardTitle",
                                        "props": {"class": "d-flex align-center text-h6"},
                                        "content": [
                                            {
                                                "component": "VIcon",
                                                "props": {
                                                    "style": "color: #16b1ff;",
                                                    "class": "mr-2",
                                                },
                                                "text": "mdi-information",
                                            },
                                            {"component": "span", "text": "使用说明"},
                                        ],
                                    }
                                ],
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "props": {"class": "px-6"},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-body-1"},
                                        "text": "开启对应探索源后，MoviePilot 探索页会展示对应数据源；数据源实现保留上游原生媒体身份，可直接用于详情识别、搜索和订阅。",
                                    },
                                    {
                                        "component": "div",
                                        "props": {"class": "text-body-1 mt-2"},
                                        "content": [
                                            {"component": "span", "text": "探索源实现来自 "},
                                            {
                                                "component": "a",
                                                "props": {
                                                    "href": "https://github.com/DDSRem-Dev/MoviePilot-Plugins",
                                                    "target": "_blank",
                                                    "style": "color: #16b1ff; text-decoration: underline;",
                                                },
                                                "text": "DDSRem",
                                            },
                                            {"component": "span", "text": " 的 V3 插件与 "},
                                            {
                                                "component": "a",
                                                "props": {
                                                    "href": "https://github.com/LLL001a/MoviePilot-Plugins",
                                                    "target": "_blank",
                                                    "style": "color: #16b1ff; text-decoration: underline;",
                                                },
                                                "text": "LLL001a",
                                            },
                                            {"component": "span", "text": " 的爱奇艺探索，感谢大佬们的开源项目。"},
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ]
            }
        ]
        default_data: Dict[str, Any] = {key: False for key in MODULE_SWITCH_KEYS}
        default_data["iqiyi_cookie"] = ""
        default_data["iqiyi_refresh_cron"] = ""
        return form, default_data

    def get_api(self) -> List[Dict[str, Any]]:
        """
        返回启用探索源的数据源 API

        :return List: API 端点列表
        """
        apis: List[Dict[str, Any]] = []
        paths = set()
        for module in self._iter_enabled():
            provider = getattr(module, "get_api", None)
            if not callable(provider):
                continue
            try:
                endpoints = provider() or []
            except Exception as err:
                logger.error(
                    f"获取 {MODULE_LABELS.get(module.module_key, module.module_key)} API 失败：{err}",
                    exc_info=True,
                )
                continue
            for endpoint in endpoints:
                path = endpoint.get("path")
                if not path or path in paths:
                    continue
                paths.add(path)
                apis.append(endpoint)
        return apis

    def get_page(self) -> Optional[List[dict]]:
        """
        返回插件详情页，当前无静态页面

        :return List: 页面配置
        """
        pass

    def get_module(self) -> Dict[str, Any]:
        """
        返回聚合后的媒体识别模块

        :return Dict: 模块方法映射
        """
        return {
            "recognize_media": self.recognize_media,
            "async_recognize_media": self.async_recognize_media,
        }

    def get_media_source(self) -> List[Dict[str, Any]]:
        """
        返回启用探索源声明的媒体来源

        :return List: 媒体数据源声明列表
        """
        sources: List[Dict[str, Any]] = []
        seen = set()
        for module in self._iter_enabled():
            provider = getattr(module, "get_media_source", None)
            if not callable(provider):
                continue
            try:
                declared = provider() or []
            except Exception as err:
                logger.warning(
                    f"获取 {MODULE_LABELS.get(module.module_key, module.module_key)} 媒体来源失败：{err}"
                )
                continue
            for source in declared:
                media_source = source.get("media_source")
                key = str(media_source)
                if key in seen:
                    continue
                seen.add(key)
                sources.append(source)
        return sources

    def recognize_media(
        self,
        meta: Any = None,
        mtype: Any = None,
        media_source: Optional[MediaSource] = None,
        media_id: Optional[str] = None,
        episode_group: Optional[str] = None,
        cache: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        按媒体来源分派媒体识别

        :param meta (Any): 已知媒体元数据
        :param mtype (MediaType): 媒体类型
        :param media_source (MediaSource): 媒体来源
        :param media_id (str): 来源原生媒体 ID
        :param episode_group (str): 剧集组
        :param cache (bool): 是否使用 MoviePilot 识别缓存
        :param kwargs (Any): 兼容 MoviePilot 模块参数

        :return Any: 识别结果，未命中时返回 None
        """
        payload: Dict[str, Any] = {
            "meta": meta,
            "mtype": mtype,
            "media_source": media_source,
            "media_id": media_id,
            "episode_group": episode_group,
            "cache": cache,
        }
        payload.update(kwargs)
        for module in self._iter_enabled():
            handler = getattr(module, "recognize_media", None)
            if not callable(handler):
                continue
            try:
                media = handler(**payload)
            except Exception as err:
                logger.error(
                    f"{MODULE_LABELS.get(module.module_key, module.module_key)} 识别失败：{err}",
                    exc_info=True,
                )
                continue
            if media:
                return media
        return None

    async def async_recognize_media(
        self,
        meta: Any = None,
        mtype: Any = None,
        media_source: Optional[MediaSource] = None,
        media_id: Optional[str] = None,
        episode_group: Optional[str] = None,
        cache: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        按媒体来源异步分派媒体识别

        :param meta (Any): 已知媒体元数据
        :param mtype (MediaType): 媒体类型
        :param media_source (MediaSource): 媒体来源
        :param media_id (str): 来源原生媒体 ID
        :param episode_group (str): 剧集组
        :param cache (bool): 是否使用 MoviePilot 识别缓存
        :param kwargs (Any): 兼容 MoviePilot 模块参数

        :return Any: 识别结果，未命中时返回 None
        """
        payload: Dict[str, Any] = {
            "meta": meta,
            "mtype": mtype,
            "media_source": media_source,
            "media_id": media_id,
            "episode_group": episode_group,
            "cache": cache,
        }
        payload.update(kwargs)
        for module in self._iter_enabled():
            handler = getattr(module, "async_recognize_media", None)
            if not callable(handler):
                continue
            try:
                media = await handler(**payload)
            except Exception as err:
                logger.error(
                    f"{MODULE_LABELS.get(module.module_key, module.module_key)} 异步识别失败：{err}",
                    exc_info=True,
                )
                continue
            if media:
                return media
        return None

    def get_service(self) -> List[Dict[str, Any]]:
        """
        返回启用探索源的定时服务

        :return List: 定时服务列表
        """
        services: List[Dict[str, Any]] = []
        for module in self._iter_enabled():
            provider = getattr(module, "get_service", None)
            if not callable(provider):
                continue
            try:
                declared = provider() or []
            except Exception as err:
                logger.warning(
                    f"获取 {MODULE_LABELS.get(module.module_key, module.module_key)} 定时服务失败：{err}"
                )
                continue
            for service in declared:
                item = dict(service)
                service_id = item.get("id") or module.module_key
                item["id"] = f"{self.__class__.__name__}.{service_id}"
                label = MODULE_LABELS.get(module.module_key, module.module_key)
                service_name = item.get("name") or "定时任务"
                if label not in service_name:
                    service_name = f"{label}{service_name}"
                item["name"] = service_name
                services.append(item)
        return services

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event) -> None:
        """
        监听探索数据源事件，注册各启用探索源

        :param event (Event): 探索数据源事件
        """
        if not self.get_state():
            return
        if getattr(event, "event_data", None) is None:
            return
        event_data: DiscoverSourceEventData = event.event_data
        event_data.extra_sources = event_data.extra_sources or []
        dispatch_started = perf_counter()
        for module in self._iter_enabled():
            handler = getattr(module, "discover_source", None)
            if not callable(handler):
                continue
            module_started = perf_counter()
            try:
                handler(event)
            except Exception as err:
                logger.error(
                    f"注册 {MODULE_LABELS.get(module.module_key, module.module_key)} 探索源失败：{err}",
                    exc_info=True,
                )
            module_elapsed = perf_counter() - module_started
            if module_elapsed >= 1:
                logger.warning(
                    f"{MODULE_LABELS.get(module.module_key, module.module_key)} 探索源注册耗时 {module_elapsed:.2f} 秒"
                )
        dispatch_elapsed = perf_counter() - dispatch_started
        if dispatch_elapsed >= 1:
            logger.warning(f"探索数据源注册总耗时 {dispatch_elapsed:.2f} 秒")

    def stop_service(self) -> None:
        """
        停止插件并释放各探索源资源
        """
        for module in self._modules.values():
            try:
                module.stop_service()
            except Exception as err:
                logger.warning(
                    f"停止 {MODULE_LABELS.get(module.module_key, module.module_key)} 失败：{err}"
                )
        self._modules = {}
        self._enabled_modules = {}
