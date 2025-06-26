from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from app.utils.http import RequestUtils
from cachetools import cached, TTLCache
from typing import List, Dict
import re

_base_api = "https://api.cntv.cn/newVideoset/getCboxVideoAlbumList"


def get_api(master_plugin):
    _ = master_plugin
    return [
        {
            "path": "/cctv_discover",
            "endpoint": cctv_discover,
            "methods": ["GET"],
            "summary": "CCTV探索数据源",
            "description": "获取CCTV探索数据",
        }
    ]

@cached(cache=TTLCache(maxsize=32, ttl=1800))
def __request(page_num: int, page_size: int, **kwargs) -> Dict:
    api_url = _base_api
    params = {
        "p": str(page_num),
        "n": str(page_size),
        "serviceId": "cbox",
        "sort": "desc",
    }
    if kwargs:
        params.update(kwargs)
    headers = {
        "User-Agent": settings.USER_AGENT,
        "Referer": "https://app.cctv.com/",
    }
    res = RequestUtils(headers=headers).get_res(api_url, params=params)
    if res is None:
        raise Exception("无法连接CCTV，请检查网络连接！")
    if not res.ok:
        raise Exception(f"请求CCTV API失败：{res.text}")
    return res.json()

def cctv_discover(
    fc: str = "电视剧",
    area: str = None,
    sc: str = None,
    year: str = None,
    fl: str = None,
    channel: str = None,
    page: int = 1,
    count: int = 30,
) -> List[MediaInfo]:
    def _parse_response(data: Dict) -> List[Dict]:
        data_body = data.get("data", {})
        return data_body.get("list", [])
    def __movie_to_media(movie_info: dict) -> MediaInfo:
        return MediaInfo(
            type="电影",
            title=re.sub("[《》]", "", movie_info.get("title", "")),
            mediaid_prefix="cctv",
            media_id=movie_info.get("id", ""),
            poster_path=movie_info.get("image", ""),
        )
    def __series_to_media(series_info: dict) -> MediaInfo:
        return MediaInfo(
            type="电视剧",
            title=re.sub("[《》]", "", series_info.get("title", "")),
            mediaid_prefix="cctv",
            media_id=series_info.get("id", ""),
            poster_path=series_info.get("image", ""),
        )
    try:
        params = {"fc": fc}
        if area: params["area"] = area
        if sc: params["sc"] = sc
        if year: params["year"] = year
        if fl: params["fl"] = fl
        if channel: params["channel"] = channel
        result = __request(page, count, **params)
    except Exception as err:
        logger.error(str(err))
        return []
    items = _parse_response(result)
    if not items:
        return []
    if fc == "电影":
        results = [__movie_to_media(movie) for movie in items]
    else:
        results = [__series_to_media(series) for series in items]
    return results

@staticmethod
def cctv_filter_ui() -> List[dict]:
    """
    CCTV过滤参数UI配置
    """

    # 媒体类型
    fc = ["电视剧", "电影", "动画片", "纪录片", "特别节目"]
    fc_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in fc
    ]

    # 地区分类（电视剧，动画片）
    all_area = [
        "内地（大陆）",
        "港澳台",
        "欧美",
        "日韩",
        "其他",
        "中国大陆",
        "香港",
        "美国",
        "欧洲",
        "泰国",
    ]
    tv_area_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in all_area
    ]
    cartoon_area_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in all_area[0:5]
    ]

    # fc分类
    tv_sc = [
        "谍战",
        "悬疑",
        "刑侦",
        "历史",
        "古装",
        "武侠",
        "军事",
        "战争",
        "喜剧",
        "青春",
        "言情",
        "偶像",
        "家庭",
        "年代",
        "革命",
        "农村",
        "都市",
        "其他",
    ]
    tv_sc_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in tv_sc
    ]
    movie_sc = [
        "全部",
        "偶像",
        "古装",
        "喜剧",
        "农村",
        "军旅",
        "惊悚",
        "爱情",
        "文艺",
        "战争",
        "历史",
        "谍战",
        "传记",
        "军事",
        "生活",
        "现代",
        "其他",
    ]
    movie_sc_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in movie_sc
    ]
    cartoon_sc = [
        "亲子",
        "搞笑",
        "冒险",
        "动作",
        "宠物",
        "体育",
        "益智",
        "历史",
        "教育",
        "校园",
        "言情",
        "武侠",
        "经典",
        "未来",
        "古代",
        "神话",
        "真人",
        "励志",
        "热血",
        "奇幻",
        "童话",
        "剧情",
        "夺宝",
        "其他",
    ]
    cartoon_sc_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in cartoon_sc
    ]
    documentary_sc = [
        "人文历史",
        "人物",
        "军事",
        "探索",
        "社会",
        "自然",
        "时政",
        "经济",
        "科技",
    ]
    documentary_sc_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in documentary_sc
    ]
    special_programs_sc = [
        "新闻",
        "经济",
        "综艺",
        "体育",
        "军事",
        "影视",
        "科教",
        "戏曲",
        "青少",
        "音乐",
        "社会",
        "文化",
        "公益",
        "其他",
    ]
    special_programs_sc_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in special_programs_sc
    ]

    # 年份分类（电视剧，电影，纪录片）
    year = [str(i) for i in range(2025, 1996, -1)]
    year_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in year
    ]

    # 字母排序（全部）
    fl = [chr(i) for i in range(ord("A"), ord("Z") + 1)]
    fl_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": value,
        }
        for value in fl
    ]

    # 频道分类（纪录片，特别节目）
    channel = {
        "CCTV-1综合,CCTV-1高清,CCTV-1综合高清": "CCTV-1 综合",
        "CCTV-2财经,CCTV-2高清,CCTV-2财经高清": "CCTV-2 财经",
        "CCTV-3综艺,CCTV-3高清,CCTV-3综艺高清": "CCTV-3 综艺",
        "CCTV-4中文国际,CCTV-4高清,CCTV-4中文国际(亚)高清": "CCTV-4 中文国际",
        "CCTV-5体育,CCTV-5高清,CCTV-5体育高清": "CCTV-5 体育",
        "CCTV-6电影,CCTV-6高清,CCTV-6电影高清": "CCTV-6 电影",
        "CCTV-7军事农业,CCTV-7高清,CCTV-7军事农业高清,CCTV-7国防军事高清": "CCTV-7 国防军事",
        "CCTV-8电视剧,CCTV-8高清,CCTV-8电视剧高清": "CCTV-8 电视剧",
        "CCTV-9纪录,CCTV-9高清,CCTV-9纪录高清": "CCTV-9 纪录",
        "CCTV-10科教,CCTV-10高清,CCTV-10科教高清": "CCTV-10 科教",
        "CCTV-11戏曲,CCTV-11高清": "CCTV-11 戏曲",
        "CCTV-12社会与法,CCTV-12高清,CCTV-12社会与法高清": "CCTV-12 社会与法",
        "CCTV-13新闻,CCTV-13高清": "CCTV-13 新闻",
        "CCTV-14少儿,CCTV-14高清,CCTV-14少儿高清": "CCTV-14 少儿",
        "CCTV-15音乐,CCTV-15高清,CCTV-15音乐高清": "CCTV-15 音乐",
        "CCTV-17农业农村高清": "CCTV-17农业农村",
    }
    channel_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": key},
            "text": value,
        }
        for key, value in channel.items()
    ]

    return [
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
                    "props": {"model": "fc"},
                    "content": fc_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '纪录片' || fc == '特别节目'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "频道"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "channel"},
                    "content": channel_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '电视剧'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "地区"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "area"},
                    "content": tv_area_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '动画片'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "地区"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "area"},
                    "content": cartoon_area_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '电视剧'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "类型"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "sc"},
                    "content": tv_sc_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '电影'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "类型"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "sc"},
                    "content": movie_sc_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '动画片'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "类型"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "sc"},
                    "content": cartoon_sc_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '纪录片'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "类型"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "sc"},
                    "content": documentary_sc_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '特别节目'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "类型"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "sc"},
                    "content": special_programs_sc_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{fc == '电视剧' || fc == '电影' || fc == '纪录片'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "年份"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "year"},
                    "content": year_ui,
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
                    "content": [{"component": "VLabel", "text": "字母顺序"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "fl"},
                    "content": fl_ui,
                },
            ],
        },
    ]

def discover_source(master_plugin, event_data):
    _ = master_plugin
    cctv_source = DiscoverMediaSource(
        name="CCTV",
        mediaid_prefix="cctv",
        api_path=f"plugin/ExploreServices/cctv_discover?apikey={settings.API_TOKEN}",
        filter_params={
            "fc": "电视剧",
            "area": None,
            "sc": None,
            "year": None,
            "fl": None,
            "channel": None,
        },
        filter_ui=cctv_filter_ui(),
        depends={
            "area": ["fc"],
            "sc": ["fc"],
            "year": ["fc"],
            "fl": ["fc"],
            "channel": ["fc"],
        },
    )
    if not event_data.extra_sources:
        event_data.extra_sources = [cctv_source]
    else:
        event_data.extra_sources.append(cctv_source)
