from typing import List, Tuple, Dict, Any
from app.log import logger
from app.plugins import _PluginBase
from app.core.event import eventmanager, Event
from app.schemas.types import ChainEventType
from app.schemas import DiscoverSourceEventData

# 导入其他探索插件
from .bangumidailydiscoverchain import BangumiDailyDiscoverChain
from .bilibilidiscoverchain import BilibiliDiscoverChain
from .mangguodiscoverchain import MangGuoDiscoverChain
from .migudiscoverchain import MiGuDiscoverChain
from .cctvdiscoverchain import CCTVDiscoverChain
from .tencentvideodiscoverchain import TencentVideoDiscoverChain

class ExploreServices(_PluginBase):
    # 插件名称
    plugin_name = "资源探索集合"
    # 插件描述
    plugin_desc = "将DDSRem大佬的Bangumi每日放送、哔哩哔哩、芒果TV、咪咕视频、CCTV、腾讯视频集合在一起"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/ExploreServices.png"
    # 插件版本
    plugin_version = "1.0.1"
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
    _enabled = False      # 插件启用状态
    _bangumi_enabled = False
    _bilibili_enabled = False
    _mgtv_enabled = False
    _miguvideo_enabled = False
    _cctv_enabled = False
    _tencentvideo_enabled = False

    # 插件实例
    _bangumi_plugin = None
    _bilibili_plugin = None
    _mgtv_plugin = None
    _miguvideo_plugin = None
    _cctv_plugin = None
    _tencentvideo_plugin = None

    def init_plugin(self, config: dict = None):
        """
        初始化插件
        """
        # 从配置中加载设置
        if config:
            self._enabled = config.get("enabled", False)
            self._bangumi_enabled = config.get("bangumi_enabled", False)
            self._bilibili_enabled = config.get("bilibili_enabled", False)
            self._mgtv_enabled = config.get("mgtv_enabled", False)
            self._miguvideo_enabled = config.get("miguvideo_enabled", False)
            self._cctv_enabled = config.get("cctv_enabled", False)
            self._tencentvideo_enabled = config.get("tencentvideo_enabled", False)

        # 停止现有任务
        self.stop_service()

        # 根据配置启用/禁用插件
        if self._enabled:
            # Bangumi每日放送探索
            if self._bangumi_enabled:
                self._bangumi_plugin = BangumiDailyDiscoverChain()
                self._bangumi_plugin.init_plugin({"enabled": True})
                # 注册事件处理器
                eventmanager.enable_event_handler(type(self._bangumi_plugin))
                logger.info(f"[{self.plugin_name}] Bangumi plugin enabled and event handler registered")
            
            # 哔哩哔哩探索
            if self._bilibili_enabled:
                self._bilibili_plugin = BilibiliDiscoverChain()
                self._bilibili_plugin.init_plugin({"enabled": True})
                # 注册事件处理器
                eventmanager.enable_event_handler(type(self._bilibili_plugin))
                logger.info(f"[{self.plugin_name}] Bilibili plugin enabled and event handler registered")
            
            # 芒果TV探索
            if self._mgtv_enabled:
                self._mgtv_plugin = MangGuoDiscoverChain()
                self._mgtv_plugin.init_plugin({"enabled": True})
                # 注册事件处理器
                eventmanager.enable_event_handler(type(self._mgtv_plugin))
                logger.info(f"[{self.plugin_name}] MangoTV plugin enabled and event handler registered")
            
            # 咪咕视频探索
            if self._miguvideo_enabled:
                self._miguvideo_plugin = MiGuDiscoverChain()
                self._miguvideo_plugin.init_plugin({"enabled": True})
                # 注册事件处理器
                eventmanager.enable_event_handler(type(self._miguvideo_plugin))
                logger.info(f"[{self.plugin_name}] MiGuVideo plugin enabled and event handler registered")
            
            # CCTV探索
            if self._cctv_enabled:
                self._cctv_plugin = CCTVDiscoverChain()
                self._cctv_plugin.init_plugin({"enabled": True})
                # 注册事件处理器
                eventmanager.enable_event_handler(type(self._cctv_plugin))
                logger.info(f"[{self.plugin_name}] CCTV plugin enabled and event handler registered")

            # 腾讯视频探索
            if self._tencentvideo_enabled:
                self._tencentvideo_plugin = TencentVideoDiscoverChain()
                self._tencentvideo_plugin.init_plugin({"enabled": True})
                # 注册事件处理器
                eventmanager.enable_event_handler(type(self._tencentvideo_plugin))
                logger.info(f"[{self.plugin_name}] TencentVideo plugin enabled and event handler registered")

    def get_state(self) -> bool:
        """
        获取插件状态
        :return: 插件是否启用
        """
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册插件API
        """
        apis = []
        
        # Bangumi每日放送探索
        if self._bangumi_enabled and self._bangumi_plugin:
            bangumi_apis = self._bangumi_plugin.get_api()
            if bangumi_apis:
                apis.extend(bangumi_apis)
                logger.info(f"[{self.plugin_name}] Registered Bangumi APIs: {len(bangumi_apis)}")
        
        # 哔哩哔哩探索
        if self._bilibili_enabled and self._bilibili_plugin:
            bilibili_apis = self._bilibili_plugin.get_api()
            if bilibili_apis:
                apis.extend(bilibili_apis)
                logger.info(f"[{self.plugin_name}] Registered Bilibili APIs: {len(bilibili_apis)}")
        
        # 芒果TV探索
        if self._mgtv_enabled and self._mgtv_plugin:
            mgtv_apis = self._mgtv_plugin.get_api()
            if mgtv_apis:
                apis.extend(mgtv_apis)
                logger.info(f"[{self.plugin_name}] Registered MangoTV APIs: {len(mgtv_apis)}")
        
        # 咪咕视频探索
        if self._miguvideo_enabled and self._miguvideo_plugin:
            migu_apis = self._miguvideo_plugin.get_api()
            if migu_apis:
                apis.extend(migu_apis)
                logger.info(f"[{self.plugin_name}] Registered MiGuVideo APIs: {len(migu_apis)}")
        
        # CCTV探索
        if self._cctv_enabled and self._cctv_plugin:
            cctv_apis = self._cctv_plugin.get_api()
            if cctv_apis:
                apis.extend(cctv_apis)
                logger.info(f"[{self.plugin_name}] Registered CCTV APIs: {len(cctv_apis)}")
        
        # 腾讯视频探索
        if self._tencentvideo_enabled and self._tencentvideo_plugin:
            tencentvideo_apis = self._tencentvideo_plugin.get_api()
            if tencentvideo_apis:
                apis.extend(tencentvideo_apis)
                logger.info(f"[{self.plugin_name}] Registered TencentVideo APIs: {len(tencentvideo_apis)}")
                
        logger.info(f"[{self.plugin_name}] Total registered APIs: {len(apis)}")
        return apis

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VCard',
                        'props': {
                            'class': 'mt-0'
                        },
                        'content': [
                            {
                                'component': 'VCardTitle',
                                'props': {
                                    'class': 'd-flex align-center'
                                },
                                'content': [
                                    {
                                        'component': 'VIcon',
                                        'props': {
                                            'style': 'color: #16b1ff;',
                                            'class': 'mr-2'
                                        },
                                        'text': 'mdi-cog'
                                    },
                                    {
                                        'component': 'span',
                                        'text': '基本设置'
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider'
                            },
                            {
                                'component': 'VCardText',
                                'content': [
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'md': 4
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'enabled',
                                                            'label': '启用插件',
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
                            'class': 'mt-3'
                        },
                        'content': [
                            {
                                'component': 'VCardTitle',
                                'props': {
                                    'class': 'd-flex align-center'
                                },
                                'content': [
                                    {
                                        'component': 'VIcon',
                                        'props': {
                                            'style': 'color: #16b1ff;',
                                            'class': 'mr-2'
                                        },
                                        'text': 'mdi-video'
                                    },
                                    {
                                        'component': 'span',
                                        'text': '探索服务设置'
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider'
                            },
                            {
                                'component': 'VCardText',
                                'content': [
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'bangumi_enabled',
                                                            'label': 'Bangumi每日放送探索',
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'bilibili_enabled',
                                                            'label': '哔哩哔哩探索',
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'mgtv_enabled',
                                                            'label': '芒果TV探索',
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'miguvideo_enabled',
                                                            'label': '咪咕视频探索',
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'cctv_enabled',
                                                            'label': 'CCTV探索',
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'tencentvideo_enabled',
                                                            'label': '腾讯视频探索',
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
                                        'text': '启用插件后，开启对应探索服务将在MoviePilot探索服务中展示对应探索页面，可根据需要进行开启。'
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
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": self._enabled,
            "bangumi_enabled": self._bangumi_enabled,
            "bilibili_enabled": self._bilibili_enabled,
            "mgtv_enabled": self._mgtv_enabled,
            "miguvideo_enabled": self._miguvideo_enabled,
            "cctv_enabled": self._cctv_enabled,
            "tencentvideo_enabled": self._tencentvideo_enabled
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        # 停止所有子插件
        if self._bangumi_plugin:
            self._bangumi_plugin.stop_service()
            # 禁用事件处理器
            eventmanager.disable_event_handler(type(self._bangumi_plugin))
            logger.info(f"[{self.plugin_name}] Bangumi plugin stopped and event handler unregistered")
            self._bangumi_plugin = None
        
        if self._bilibili_plugin:
            self._bilibili_plugin.stop_service()
            # 禁用事件处理器
            eventmanager.disable_event_handler(type(self._bilibili_plugin))
            logger.info(f"[{self.plugin_name}] Bilibili plugin stopped and event handler unregistered")
            self._bilibili_plugin = None
        
        if self._mgtv_plugin:
            self._mgtv_plugin.stop_service()
            # 禁用事件处理器
            eventmanager.disable_event_handler(type(self._mgtv_plugin))
            logger.info(f"[{self.plugin_name}] MangoTV plugin stopped and event handler unregistered")
            self._mgtv_plugin = None
        
        if self._miguvideo_plugin:
            self._miguvideo_plugin.stop_service()
            # 禁用事件处理器
            eventmanager.disable_event_handler(type(self._miguvideo_plugin))
            logger.info(f"[{self.plugin_name}] MiGuVideo plugin stopped and event handler unregistered")
            self._miguvideo_plugin = None
        
        if self._cctv_plugin:
            self._cctv_plugin.stop_service()
            # 禁用事件处理器
            eventmanager.disable_event_handler(type(self._cctv_plugin))
            logger.info(f"[{self.plugin_name}] CCTV plugin stopped and event handler unregistered")
            self._cctv_plugin = None

        if self._tencentvideo_plugin:
            self._tencentvideo_plugin.stop_service()
            # 禁用事件处理器
            eventmanager.disable_event_handler(type(self._tencentvideo_plugin))
            logger.info(f"[{self.plugin_name}] TencentVideo plugin stopped and event handler unregistered")
            self._tencentvideo_plugin = None

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """
        监听识别事件，使用ChatGPT辅助识别名称
        """
        if not self._enabled:
            return
        event_data: DiscoverSourceEventData = event.event_data
        event_data.extra_sources = []  # 先清空，防止脏数据和覆盖
        # Bangumi每日放送探索
        if self._bangumi_enabled and self._bangumi_plugin:
            self._bangumi_plugin.discover_source(event)
        # 哔哩哔哩探索
        if self._bilibili_enabled and self._bilibili_plugin:
            self._bilibili_plugin.discover_source(event)
        # 芒果TV探索
        if self._mgtv_enabled and self._mgtv_plugin:
            self._mgtv_plugin.discover_source(event)
        # 咪咕视频探索
        if self._miguvideo_enabled and self._miguvideo_plugin:
            self._miguvideo_plugin.discover_source(event)
        # CCTV探索
        if self._cctv_enabled and self._cctv_plugin:
            self._cctv_plugin.discover_source(event)
        # 腾讯视频探索
        if self._tencentvideo_enabled and self._tencentvideo_plugin:
            self._tencentvideo_plugin.discover_source(event)
