from typing import Any, List, Dict, Tuple
from app.plugins import _PluginBase
from app.core.event import eventmanager, Event
from app.schemas.types import ChainEventType
from app.schemas import DiscoverSourceEventData

# 导入子模块
from .modules import tencentvideo, bilibili, cctv, mangguo, bangumidaily, migu

MODULE_LABELS = {
    "tencentvideo": "腾讯视频",
    "bilibili": "哔哩哔哩",
    "cctv": "CCTV",
    "mangguo": "芒果TV",
    "bangumidaily": "Bangumi每日放送",
    "migu": "咪咕视频",
}

class ExploreServices(_PluginBase):
    # 插件名称
    plugin_name = "探索服务聚合"
    # 插件描述
    plugin_desc = "统一管理和配置所有探索数据源插件。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/ExploreServices.png"
    # 插件版本
    plugin_version = "1.0.2"
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

    # 子模块注册表
    modules = {
        "tencentvideo": tencentvideo,
        "bilibili": bilibili,
        "cctv": cctv,
        "mangguo": mangguo,
        "bangumidaily": bangumidaily,
        "migu": migu,
    }
    enabled_modules: Dict[str, bool] = {}

    def init_plugin(self, config: dict = None):
        if config:
            for name in self.modules:
                self.enabled_modules[name] = config.get(f"{name}_enabled", False)
        else:
            for name in self.modules:
                self.enabled_modules[name] = False

    def get_state(self) -> bool:
        return any(self.enabled_modules.values())

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        plugin_names = "、".join(MODULE_LABELS.values())
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
                                        "props": {"style": "color: #16b1ff;", "class": "mr-2"},
                                        "text": "mdi-compass-outline"
                                    },
                                    {
                                        "component": "span",
                                        "text": "探索源开关"
                                    }
                                ]
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
                                                            "model": f"{name}_enabled",
                                                            "label": f"启用{MODULE_LABELS.get(name, name)}探索源",
                                                        },
                                                    }
                                                ],
                                            }
                                            for name in self.modules
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
                            'class': 'mt-3',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {
                                    'class': 'px-6 pb-0'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-2'
                                                },
                                                'text': 'mdi-information'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '使用说明'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider'
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1'
                                        },
                                        'text': '开启对应探索服务将在MoviePilot探索服务中展示对应探索页面，可根据需要进行开启。'
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1 mt-2'
                                        },
                                        'content': [
                                            {
                                                'component': 'span',
                                                'text': '致谢'
                                            },
                                            {
                                                'component': 'a',
                                                'props': {
                                                    'href': 'https://github.com/DDS-Derek/MoviePilot-Plugins',
                                                    'target': '_blank',
                                                    'style': 'color: #16b1ff; text-decoration: underline;'
                                                },
                                                'text': 'DDSRem大佬'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '，感谢大佬提供的优质插件项目。'
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1 mt-2'
                                        },
                                        'text': f'当前聚合插件：{plugin_names}'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        default_data = {f"{name}_enabled": False for name in self.modules}
        return form, default_data

    def get_api(self) -> List[Dict[str, Any]]:
        apis = []
        for name, mod in self.modules.items():
            if self.enabled_modules.get(name):
                apis.extend(mod.get_api(self))
        return apis

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        event_data: DiscoverSourceEventData = event.event_data
        for name, mod in self.modules.items():
            if self.enabled_modules.get(name):
                mod.discover_source(self, event_data)

    def stop_service(self):
        for name, mod in self.modules.items():
            if hasattr(mod, "stop_service"):
                mod.stop_service() 