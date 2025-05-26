import dataclasses
from datetime import datetime
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


@dataclasses.dataclass
class Option:
    value: int
    text: str


weekdays = [
    (0, "全部"),
    (1, "星期一"),
    (2, "星期二"),
    (3, "星期三"),
    (4, "星期四"),
    (5, "星期五"),
    (6, "星期六"),
    (7, "星期日"),
]


class BangumiDailyDiscoverChain(_PluginBase):
    # 插件名称
    plugin_name = "Bangumi每日放送探索"
    # 插件描述
    plugin_desc = "让探索支持Bangumi每日放送的数据浏览。"
    # 插件图标
    plugin_icon = "Bangumi_A.png"
    # 插件版本
    plugin_version = "1.0.1"
    # 插件作者
    plugin_author = "DDSRem"
    # 作者主页
    author_url = "https://github.com/DDSRem"
    # 插件配置项ID前缀
    plugin_config_prefix = "bangumidailydiscoverchain_"
    # 加载顺序
    plugin_order = 99
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/bangumidaily_discover",
                "endpoint": self.bangumidaily_discover,
                "methods": ["GET"],
                "summary": "Bangumi每日放送探索数据源",
                "description": "获取Bangumi每日放送探索数据",
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
    def __request(self) -> List[schemas.MediaInfo]:
        """
        请求Bangumi每日放送 API
        """
        api_url = "https://api.bgm.tv/calendar"
        headers = {
            "User-Agent": settings.USER_AGENT,
            "Referer": "https://api.bgm.tv/",
        }
        res = RequestUtils(headers=headers).get_res(api_url)
        if res is None:
            raise Exception("无法连接Bangumi每日放送，请检查网络连接！")
        if not res.ok:
            raise Exception(f"请求Bangumi每日放送 API失败：{res.text}")
        return res.json()

    def bangumidaily_discover(
        self,
        weekday: str = "0",
        page: int = 1,
        count: int = 20,
    ) -> List[schemas.MediaInfo]:
        """
        获取Bangumi每日放送探索数据
        """

        def __series_to_media(series_info: dict) -> schemas.MediaInfo:
            vote_average = None
            rating_info = series_info.get("rating", None)
            if rating_info is not None:
                vote_average = rating_info.get("score", None)

            if series_info.get("name_cn"):
                title = series_info.get("name_cn")
            else:
                title = series_info.get("name")
            return schemas.MediaInfo(
                type="电视剧",
                source="bangumi",
                title=title,
                mediaid_prefix="bangumidaily",
                media_id=series_info.get("id"),
                bangumi_id=series_info.get("id"),
                poster_path=series_info.get("images").get("large"),
                vote_average=vote_average,
                first_air_date=series_info.get("air_date", None)
            )

        try:
            result = self.__request()
        except Exception as err:
            logger.error(str(err))
            return []
        if not result:
            return []
        results = []
        for day_entry in result:
            if str(weekday) == "0":
                for item in day_entry["items"]:
                    results.append(__series_to_media(item))
            else:
                if str(day_entry["weekday"]["id"]) == str(weekday):
                    for item in day_entry["items"]:
                        results.append(__series_to_media(item))
                else:
                    continue
        if page * count <= len(results):
            last_num = page * count
        else:
            last_num = len(results)
        return results[(page - 1) * count : last_num]

    @staticmethod
    def bangumidaily_filter_ui() -> List[dict]:
        """
        Bangumi每日放送过滤参数UI配置
        """
        today_weekday = datetime.today().weekday() + 1
        options = [Option(value=w[0], text=w[1]) for w in weekdays]

        def sort_key(opt: Option):
            if opt.value == 0:
                return (0, 0)
            if opt.value == today_weekday:
                return (1, 0)
            return (2, opt.value)

        sorted_options = sorted(options, key=sort_key)
        ui_data = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": opt.value},
                "text": opt.text,
            }
            for opt in sorted_options
        ]

        return [
            {
                "component": "div",
                "props": {"class": "flex justify-start items-center"},
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "星期"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "weekday"},
                        "content": ui_data,
                    },
                ],
            },
        ]

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """
        监听识别事件，使用ChatGPT辅助识别名称
        """
        if not self._enabled:
            return
        event_data: DiscoverSourceEventData = event.event_data
        bangumidaily_source = schemas.DiscoverMediaSource(
            name="Bangumi每日放送",
            mediaid_prefix="bangumidaily",
            api_path=f"plugin/ExploreServices/bangumidaily_discover?apikey={settings.API_TOKEN}",
            filter_params={"weekday": "0"},
            filter_ui=self.bangumidaily_filter_ui(),
        )
        event_data.extra_sources.append(bangumidaily_source)

    def stop_service(self):
        """
        退出插件
        """
        pass
