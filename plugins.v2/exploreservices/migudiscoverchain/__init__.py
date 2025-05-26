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


class MiGuDiscoverChain(_PluginBase):
    # 插件名称
    plugin_name = "咪咕视频探索"
    # 插件描述
    plugin_desc = "让探索支持咪咕视频的数据浏览。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/DDS-Derek/MoviePilot-Plugins/main/icons/migu_A.png"
    # 插件版本
    plugin_version = "1.0.3"
    # 插件作者
    plugin_author = "DDSRem"
    # 作者主页
    author_url = "https://github.com/DDSRem"
    # 插件配置项ID前缀
    plugin_config_prefix = "migudiscoverchain_"
    # 加载顺序
    plugin_order = 99
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _base_api = "https://jadeite.migu.cn/search/v3/category"
    _enabled = False

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
        if "http://wapx.cmvideo.cn:8080" not in settings.SECURITY_IMAGE_DOMAINS:
            settings.SECURITY_IMAGE_DOMAINS.append("http://wapx.cmvideo.cn:8080")

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/migu_discover",
                "endpoint": self.migu_discover,
                "methods": ["GET"],
                "summary": "咪咕视频探索数据源",
                "description": "获取咪咕视频探索数据",
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
    def __request(
        self, page_num: int, page_size: int, **kwargs
    ) -> List[schemas.MediaInfo]:
        """
        请求 咪咕视频 API
        """
        api_url = self._base_api
        params = {
            "pageStart": str(page_num),
            "pageNum": str(page_size),
            "copyrightTerminal": 3,
        }
        if kwargs:
            params.update(kwargs)
        headers = {
            "User-Agent": settings.USER_AGENT,
            "Referer": "https://www.miguvideo.com/",
        }
        res = RequestUtils(headers=headers).get_res(
            api_url,
            params=params,
        )
        if res is None:
            raise Exception("无法连接咪咕视频，请检查网络连接！")
        if not res.ok:
            raise Exception(f"请求咪咕视频 API失败：{res.text}")
        return res.json().get("body").get("data")

    def migu_discover(
        self,
        mtype: str = "电视剧",
        mediaType: str = None,
        mediaArea: str = None,
        mediaYear: str = None,
        rankingType: str = None,
        payType: str = None,
        gender: str = None,
        mediaAge: str = None,
        page: int = 1,
        count: int = 21,
    ) -> List[schemas.MediaInfo]:
        """
        获取咪咕视频探索数据
        """

        def __movie_to_media(movie_info: dict) -> schemas.MediaInfo:
            """
            电影数据转换为MediaInfo
            """
            first_air_date = None
            if movie_info.get("publishTime"):
                first_air_date = movie_info.get("publishTime")
            return schemas.MediaInfo(
                type="电影",
                title=movie_info.get("name"),
                year=movie_info.get("year"),
                title_year=f"{movie_info.get('name')} ({movie_info.get('year')})",
                mediaid_prefix="migu",
                media_id=str(movie_info.get("pID")),
                poster_path=movie_info.get("h5pics").get("highResolutionV"),
                vote_average=movie_info.get("score"),
                first_air_date=first_air_date,
            )

        def __series_to_media(series_info: dict) -> schemas.MediaInfo:
            """
            电视剧数据转换为MediaInfo
            """
            first_air_date = None
            if series_info.get("publishTime"):
                first_air_date = series_info.get("publishTime")
            return schemas.MediaInfo(
                type="电视剧",
                title=series_info.get("name"),
                year=series_info.get("year"),
                title_year=f"{series_info.get('name')} ({series_info.get('year')})",
                mediaid_prefix="migu",
                media_id=str(series_info.get("pID")),
                release_date=series_info.get("publishTime"),
                poster_path=series_info.get("h5pics").get("highResolutionV"),
                vote_average=series_info.get("score"),
                first_air_date=first_air_date,
            )

        try:
            if mtype == "电视剧":
                media_info = [
                    "1002581,1003861,1003863,1003866,1002601,1004761,1004121,1004641,1005521,1005261",
                    "1001",
                    "",
                    "",
                ]
            elif mtype == "电影":
                media_info = [
                    "1002581,1002601,1003862,1003864,1003866,1004121,1003861,1004761,1004641",
                    "1000",
                    "全片",
                    "2",
                ]
            elif mtype == "综艺":
                media_info = [
                    "1002581,1002601",
                    "1005",
                    "连载",
                    "2",
                ]
            elif mtype == "纪实":
                media_info = [
                    "1002581,1002601",
                    "1002",
                    "连载",
                    "2",
                ]
            elif mtype == "动漫":
                media_info = [
                    "1002581,1003861,1003863,1003866,1002601,1004761,1004121,1004641",
                    "1007",
                    "连载",
                    "",
                ]
            else:
                media_info = [
                    "1002581,1002601",
                    "601382",
                    "",
                    "",
                ]
            params = {
                "page_num": page,
                "page_size": count,
                "packId": str(media_info[0]),
                "contDisplayType": str(media_info[1]),
            }
            if media_info[2]:
                params.update({"mediaShape": str(media_info[2])})
            if media_info[3]:
                params.update({"order": str(media_info[3])})
            if mediaType:
                params.update({"mediaType": mediaType})
            if mediaArea:
                params.update({"mediaArea": mediaArea})
            if mediaYear:
                params.update({"mediaYear": mediaYear})
            if rankingType:
                params.update({"rankingType": rankingType})
            if payType:
                params.update({"payType": payType})
            if gender:
                params.update({"gender": gender})
            if mediaAge:
                params.update({"mediaAge": mediaAge})
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
    def migu_filter_ui() -> List[dict]:
        """
        咪咕视频过滤参数UI配置
        """
        mtype = [
            "电视剧",
            "电影",
            "综艺",
            "纪实",
            "动漫",
            "少儿",
        ]
        mtype_ui = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": value},
                "text": value,
            }
            for value in mtype
        ]

        rankingType = {
            "0": "最热",
            "1": "最新",
            "2": "好评",
        }
        rankingType_ui = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": key},
                "text": value,
            }
            for key, value in rankingType.items()
        ]

        gender = {
            "0": "男",
            "1": "女",
        }
        gender_ui = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": key},
                "text": value,
            }
            for key, value in gender.items()
        ]

        mediaAge = [
            "0~3岁",
            "4~6岁",
            "7~12岁",
        ]
        mediaAge_ui = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": value},
                "text": value,
            }
            for value in mediaAge
        ]

        mediaType = [
            [
                "爱情",
                "古装",
                "战争",
                "悬疑",
                "青春",
                "都市",
                "言情",
                "玄幻",
                "警匪",
                "谍战",
                "喜剧",
                "家庭",
                "军旅",
                "武侠",
                "职场",
                "奇幻",
                "科幻",
                "偶像",
                "历史",
                "年代",
                "农村",
                "剧情",
                "微短剧",
            ],
            [
                "动作",
                "喜剧",
                "惊悚",
                "谍战",
                "悬疑",
                "犯罪",
                "战争",
                "爱情",
                "历史",
                "动画",
                "科幻",
                "奇幻",
                "冒险",
                "灾难",
                "恐怖",
                "剧情",
                "西部",
                "传记",
            ],
            [
                "真人秀",
                "搞笑",
                "情感",
                "音乐",
                "游戏",
                "晚会",
                "生活",
                "职场",
                "美食",
                "文化",
                "旅行",
                "益智",
                "亲子",
            ],
            [
                "军事",
                "社会",
                "自然",
                "历史",
                "刑侦",
                "科技",
                "人物",
                "艺术",
                "动物",
                "文物",
                "美食",
                "旅游",
                "古迹",
                "探秘",
                "其他",
            ],
            [
                "热血",
                "奇幻",
                "青春",
                "爱情",
                "搞笑",
                "悬疑",
                "竞技",
            ],
            [
                "动画",
                "故事",
                "儿歌",
            ],
        ]
        mediaType_list = []
        for i in range(len(mtype)):
            mediaType_list.append(
                [
                    {
                        "component": "VChip",
                        "props": {"filter": True, "tile": True, "value": value},
                        "text": value,
                    }
                    for value in mediaType[i]
                ]
            )
        mediaType_ui = (
            {
                "component": "div",
                "props": {
                    "class": "flex justify-start items-center",
                    "show": "{{mtype == '" + mtype[i] + "'}}",
                },
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "类别"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "mediaType"},
                        "content": mediaType_list[i],
                    },
                ],
            }
            for i in range(len(mtype))
        )

        mediaArea = [
            [
                "内地",
                "香港地区",
                "日本",
                "美国",
                "英国",
                "韩国",
                "泰国",
                "台湾地区",
            ],
            [
                "内地",
                "中国香港",
                "中国台湾",
                "美国",
                "英国",
                "日本",
                "韩国",
                "泰国",
                "印度",
                "德国",
                "巴西",
                "埃及",
                "意大利",
                "俄罗斯",
                "捷克",
                "西班牙",
                "法国",
                "澳大利亚",
                "新加坡",
                "新西兰",
                "瑞典",
                "爱尔兰",
                "丹麦",
                "土耳其",
                "其他",
            ],
            ["内地"],
            [
                "中国",
                "美国",
                "英国",
                "其他",
            ],
            ["内地", "日本"],
            [
                "内地",
                "韩国",
                "日本",
                "爱尔兰",
                "英国",
                "澳大利亚",
                "美国",
                "巴西",
                "俄罗斯",
                "法国",
                "加拿大",
                "西班牙",
                "意大利",
            ],
        ]
        mediaArea_list = []
        for i in range(len(mtype)):
            mediaArea_list.append(
                [
                    {
                        "component": "VChip",
                        "props": {"filter": True, "tile": True, "value": value},
                        "text": value,
                    }
                    for value in mediaArea[i]
                ]
            )
        mediaArea_ui = (
            {
                "component": "div",
                "props": {
                    "class": "flex justify-start items-center",
                    "show": "{{mtype == '" + mtype[i] + "'}}",
                },
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "地区"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "mediaArea"},
                        "content": mediaArea_list[i],
                    },
                ],
            }
            for i in range(len(mtype))
        )

        mediaYear = [
            [
                "2024",
                "2023",
                "2022",
                "2021",
                "2020",
                "2019",
                "2018",
                "2017",
                "2016",
                "2015",
                "2014",
                "2013",
                "2012",
                "2011",
                "2010",
                "2009",
                "2008",
                "2007",
                "2006",
                "2005",
                "2004",
                "2003",
                "2002",
                "2001",
                "2000",
                "90年代",
                "80年代",
            ],
            [
                "2024",
                "2023",
                "2022",
                "2021",
                "2020",
                "2019",
                "2018",
                "2017",
                "2016",
                "2015",
                "2014",
                "2013",
                "2012",
                "2011",
                "2010",
                "2009",
                "2008",
                "2007",
                "2006",
                "2005",
                "2004",
                "2003",
                "更早",
            ],
            [
                "2023",
                "2022",
                "2021",
                "2020",
                "2019",
                "2018",
                "2017",
                "2016",
                "2015",
                "2014",
                "2013",
                "2012",
            ],
            [
                "2023",
                "2022",
                "2021",
                "2020",
                "2019",
                "2018",
                "2017",
                "2016",
                "2015",
                "2014",
                "2013",
                "2012",
                "2011",
                "2010",
                "2009",
                "2008",
                "2007",
                "2006",
                "2005",
                "2004",
                "2003",
            ],
            [
                "2023",
                "2022",
                "2021",
                "2020",
                "2019",
                "2018",
                "2017",
                "2016",
                "2015",
                "2014",
                "2013",
                "2012",
                "更早",
            ],
            [
                "2023",
                "2022",
                "2021",
                "2020",
                "2019",
                "2018",
                "2017",
                "2016",
                "2015",
                "2014",
                "2013",
                "2012",
                "2011",
                "2010",
                "2009",
                "2008",
                "2007",
                "2006",
                "2005",
                "2004",
                "2003",
                "2002",
                "2001",
                "90年代",
                "80年代",
                "更早",
            ],
        ]
        mediaYear_list = []
        for i in range(len(mtype)):
            mediaYear_list.append(
                [
                    {
                        "component": "VChip",
                        "props": {"filter": True, "tile": True, "value": value},
                        "text": value,
                    }
                    for value in mediaYear[i]
                ]
            )
        mediaYear_ui = (
            {
                "component": "div",
                "props": {
                    "class": "flex justify-start items-center",
                    "show": "{{mtype == '" + mtype[i] + "'}}",
                },
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "年代"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "mediaYear"},
                        "content": mediaYear_list[i],
                    },
                ],
            }
            for i in range(len(mtype))
        )

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
            {
                "component": "div",
                "props": {"class": "flex justify-start items-center"},
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "排序类型"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "rankingType"},
                        "content": rankingType_ui,
                    },
                ],
            },
            {
                "component": "div",
                "props": {
                    "class": "flex justify-start items-center",
                    "show": "{{mtype == '少儿'}}",
                },
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "性别"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "channel"},
                        "content": gender_ui,
                    },
                ],
            },
            {
                "component": "div",
                "props": {
                    "class": "flex justify-start items-center",
                    "show": "{{mtype == '少儿'}}",
                },
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "年龄"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "channel"},
                        "content": mediaAge_ui,
                    },
                ],
            },
        ]
        for i in mediaType_ui:
            ui.insert(-3, i)
        for i in mediaArea_ui:
            ui.insert(-3, i)
        for i in mediaYear_ui:
            ui.insert(-3, i)

        return ui

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """
        监听识别事件，使用ChatGPT辅助识别名称
        """
        if not self._enabled:
            return
        event_data: DiscoverSourceEventData = event.event_data
        migu_source = schemas.DiscoverMediaSource(
            name="咪咕视频",
            mediaid_prefix="migu",
            api_path=f"plugin/ExploreServices/migu_discover?apikey={settings.API_TOKEN}",
            filter_params={
                "mtype": "电视剧",
                "mediaType": None,
                "mediaArea": None,
                "mediaYear": None,
                "rankingType": None,
                "payType": None,
                "gender": None,
                "mediaAge": None,
            },
            filter_ui=self.migu_filter_ui(),
            depends={
                "mediaType": ["mtype"],
                "mediaArea": ["mtype"],
                "mediaYear": ["mtype"],
                "rankingType": ["mtype"],
                "payType": ["mtype"],
                "gender": ["mtype"],
                "mediaAge": ["mtype"],
            },
        )
        event_data.extra_sources.append(migu_source)

    def stop_service(self):
        """
        退出插件
        """
        pass
