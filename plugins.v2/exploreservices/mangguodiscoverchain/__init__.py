from typing import Any, List, Dict, Tuple

from cachetools import cached, TTLCache

from app import schemas
from app.core.config import settings
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import DiscoverSourceEventData
from app.schemas.types import ChainEventType
from app.utils.http import RequestUtils


CHANNEL_PARAMS = {
    "电视剧": "2",
    "电影": "3",
    "动漫": "50",
    "少儿": "10",
    "综艺": "1",
    "纪录片": "51",
    "教育": "115",
}

HEADERS = {
    "User-Agent": settings.USER_AGENT,
    "Referer": "https://www.mgtv.com",
}

BASE_UI = None


def init_base_ui():
    """ "
    初始化 UI
    """
    ui = []
    for key, _ in CHANNEL_PARAMS.items():
        params_ui = {
            "platform": "pcweb",
            "allowedRC": "1",
            "channelId": CHANNEL_PARAMS[key],
            "_support": "10000000",
        }
        res = RequestUtils(headers=HEADERS).get_res(
            "https://pianku.api.mgtv.com/rider/config/channel/v1",
            params=params_ui,
        )
        for item in res.json().get("data").get("listItems"):
            data = [
                {
                    "component": "VChip",
                    "props": {
                        "filter": True,
                        "tile": True,
                        "value": j["tagId"],
                    },
                    "text": j["tagName"],
                }
                for j in item["items"]
                if j["tagName"] != "全部"
            ]
            ui.append(
                {
                    "component": "div",
                    "props": {
                        "class": "flex justify-start items-center",
                        "show": "{{mtype == '" + key + "'}}",
                    },
                    "content": [
                        {
                            "component": "div",
                            "props": {"class": "mr-5"},
                            "content": [
                                {"component": "VLabel", "text": item["typeName"]}
                            ],
                        },
                        {
                            "component": "VChipGroup",
                            "props": {"model": item["eName"]},
                            "content": data,
                        },
                    ],
                }
            )
    return ui


class MangGuoDiscoverChain(_PluginBase):
    # 插件名称
    plugin_name = "芒果TV探索"
    # 插件描述
    plugin_desc = "让探索支持芒果TV的数据浏览。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/DDS-Derek/MoviePilot-Plugins/main/icons/mangguo_A.jpg"
    # 插件版本
    plugin_version = "1.0.1"
    # 插件作者
    plugin_author = "DDSRem"
    # 作者主页
    author_url = "https://github.com/DDSRem"
    # 插件配置项ID前缀
    plugin_config_prefix = "mangguodiscoverchain_"
    # 加载顺序
    plugin_order = 99
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False

    def init_plugin(self, config: dict = None):
        global BASE_UI
        if config:
            self._enabled = config.get("enabled")
        if "hitv.com" not in settings.SECURITY_IMAGE_DOMAINS:
            settings.SECURITY_IMAGE_DOMAINS.append("hitv.com")
        BASE_UI = init_base_ui()

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/mangguo_discover",
                "endpoint": self.mangguo_discover,
                "methods": ["GET"],
                "summary": "芒果TV探索数据源",
                "description": "获取芒果TV探索数据",
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                "component": "VForm",
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
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ], {"enabled": False}

    def get_page(self) -> List[dict]:
        pass

    @cached(cache=TTLCache(maxsize=32, ttl=1800))
    def __request(self, **kwargs) -> List[schemas.MediaInfo]:
        """
        请求芒果TV API
        """
        api_url = "https://pianku.api.mgtv.com/rider/list/pcweb/v3"
        res = RequestUtils(headers=HEADERS).get_res(api_url, params=kwargs)
        if res is None:
            raise Exception("无法连接芒果TV，请检查网络连接！")
        if not res.ok:
            raise Exception(f"请求芒果TV API失败：{res.text}")
        return res.json().get("data").get("hitDocs")

    def mangguo_discover(
        self,
        mtype: str = "电视剧",
        chargeInfo: str = None,
        sort: str = None,
        kind: str = None,
        edition: str = None,
        area: str = None,
        fitAge: str = None,
        year: str = None,
        feature: str = None,
        page: int = 1,
        count: int = 80,
    ) -> List[schemas.MediaInfo]:
        """
        获取芒果TV探索数据
        """

        def __movie_to_media(movie_info: dict) -> schemas.MediaInfo:
            """
            电影数据转换为MediaInfo
            """
            return schemas.MediaInfo(
                type="电影",
                title=movie_info.get("title"),
                year=movie_info.get("year"),
                title_year=f"{movie_info.get('title')} ({movie_info.get('year')})",
                mediaid_prefix="mangguo",
                media_id=str(movie_info.get("clipId")),
                poster_path=movie_info.get("img"),
            )

        def __series_to_media(series_info: dict) -> schemas.MediaInfo:
            """
            电视剧数据转换为MediaInfo
            """
            return schemas.MediaInfo(
                type="电视剧",
                title=series_info.get("title"),
                year=series_info.get("year"),
                title_year=f"{series_info.get('title')} ({series_info.get('year')})",
                mediaid_prefix="mangguo",
                media_id=str(series_info.get("clipId")),
                poster_path=series_info.get("img"),
            )

        try:
            params = {
                "allowedRC": "1",
                "platform": "pcweb",
                "channelId": CHANNEL_PARAMS[mtype],
                "pn": str(page),
                "pc": str(count),
                "hudong": "1",
                "_support": "10000000",
            }
            if chargeInfo:
                params.update({"chargeInfo": chargeInfo})
            if sort:
                params.update({"sort": sort})
            if kind:
                params.update({"kind": kind})
            if edition:
                params.update({"edition": edition})
            if area:
                params.update({"area": area})
            if fitAge:
                params.update({"fitAge": fitAge})
            if year:
                params.update({"year": year})
            if feature:
                params.update({"feature": feature})
            result = self.__request(**params)
        except Exception as err:
            logger.error(str(err))
            return []
        if not result:
            return []
        if mtype == "电影":
            results = [__movie_to_media(movie) for movie in result]
        else:
            results = [__series_to_media(series) for series in result]
        return results

    @staticmethod
    def mangguo_filter_ui() -> List[dict]:
        """
        芒果TV过滤参数UI配置
        """

        mtype_ui = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": key},
                "text": key,
            }
            for key in CHANNEL_PARAMS
        ]
        ui = [
            {
                "component": "div",
                "props": {"class": "flex justify-start items-center"},
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "种类"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "mtype"},
                        "content": mtype_ui,
                    },
                ],
            },
        ]
        for i in BASE_UI:
            ui.append(i)

        return ui

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """
        监听识别事件，使用ChatGPT辅助识别名称
        """
        if not self._enabled:
            return
        event_data: DiscoverSourceEventData = event.event_data
        mangguo_source = schemas.DiscoverMediaSource(
            name="芒果TV",
            mediaid_prefix="mangguodiscover",
            api_path=f"plugin/ExploreServices/mangguo_discover?apikey={settings.API_TOKEN}",
            filter_params={
                "mtype": "电视剧",
                "chargeInfo": None,
                "sort": None,
                "kind": None,
                "edition": None,
                "area": None,
                "fitAge": None,
                "year": None,
                "feature": None,
            },
            filter_ui=self.mangguo_filter_ui(),
            depends={
                "chargeInfo": ["mtype"],
                "sort": ["mtype"],
                "kind": ["mtype"],
                "edition": ["mtype"],
                "area": ["mtype"],
                "fitAge": ["mtype"],
                "year": ["mtype"],
                "feature": ["mtype"],
            },
        )
        event_data.extra_sources.append(mangguo_source)

    def stop_service(self):
        """
        退出插件
        """
        pass
