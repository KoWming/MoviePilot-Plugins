from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from app.utils.http import RequestUtils
from typing import List
from cachetools import cached, TTLCache

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

def get_api(master_plugin):
    _ = master_plugin
    return [
        {
            "path": "/mangguo_discover",
            "endpoint": mangguo_discover,
            "methods": ["GET"],
            "summary": "芒果TV探索数据源",
            "description": "获取芒果TV探索数据",
        }
    ]

def init_base_ui():
    """
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
        try:
            res = RequestUtils(headers=HEADERS).get_res(
                "https://pianku.api.mgtv.com/rider/config/channel/v1",
                params=params_ui,
            )
            if res is None or not res.ok:
                logger.warning(f"获取芒果TV UI失败: {key}")
                continue
            for item in res.json().get("data", {}).get("listItems", []):
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
        except Exception as e:
            logger.warning(f"芒果TV UI初始化异常: {key} {e}")
            continue
    return ui

@cached(cache=TTLCache(maxsize=32, ttl=1800))
def __request(**kwargs) -> List[dict]:
    api_url = "https://pianku.api.mgtv.com/rider/list/pcweb/v3"
    res = RequestUtils(headers=HEADERS).get_res(api_url, params=kwargs)
    if res is None:
        raise Exception("无法连接芒果TV，请检查网络连接！")
    if not res.ok:
        raise Exception(f"请求芒果TV API失败：{res.text}")
    return res.json().get("data", {}).get("hitDocs", [])

def mangguo_discover(
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
) -> List[MediaInfo]:
    """
    获取芒果TV探索数据
    """
    def __movie_to_media(movie_info: dict) -> MediaInfo:
        return MediaInfo(
            type="电影",
            title=movie_info.get("title"),
            year=movie_info.get("year"),
            title_year=f"{movie_info.get('title')} ({movie_info.get('year')})",
            mediaid_prefix="mangguo",
            media_id=str(movie_info.get("clipId")),
            poster_path=movie_info.get("img"),
        )
    def __series_to_media(series_info: dict) -> MediaInfo:
        return MediaInfo(
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
            "channelId": CHANNEL_PARAMS.get(mtype, "2"),
            "pn": str(page),
            "pc": str(count),
            "hudong": "1",
            "_support": "10000000",
        }
        if chargeInfo:
            params["chargeInfo"] = chargeInfo
        if sort:
            params["sort"] = sort
        if kind:
            params["kind"] = kind
        if edition:
            params["edition"] = edition
        if area:
            params["area"] = area
        if fitAge:
            params["fitAge"] = fitAge
        if year:
            params["year"] = year
        if feature:
            params["feature"] = feature
        result = __request(**params)
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

def mangguo_filter_ui():
    global BASE_UI
    if BASE_UI is None:
        BASE_UI = init_base_ui()
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
    if BASE_UI:
        for i in BASE_UI:
            ui.append(i)
    return ui

def discover_source(master_plugin, event_data):
    _ = master_plugin
    mangguo_source = DiscoverMediaSource(
        name="芒果TV",
        mediaid_prefix="mangguo",
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
        filter_ui=mangguo_filter_ui(),
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
    if not event_data.extra_sources:
        event_data.extra_sources = [mangguo_source]
    else:
        event_data.extra_sources.append(mangguo_source)
