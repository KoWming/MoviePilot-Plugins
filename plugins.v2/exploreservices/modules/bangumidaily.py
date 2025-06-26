from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from app.utils.http import RequestUtils
from datetime import datetime
from typing import List
from cachetools import cached, TTLCache

class Option:
    def __init__(self, value: int, text: str):
        self.value = value
        self.text = text

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

def get_api(master_plugin):
    _ = master_plugin
    return [
        {
            "path": "/bangumidaily_discover",
            "endpoint": bangumidaily_discover,
            "methods": ["GET"],
            "summary": "Bangumi每日放送探索数据源",
            "description": "获取Bangumi每日放送探索数据",
        }
    ]

@cached(cache=TTLCache(maxsize=32, ttl=1800))
def __request():
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
    weekday: str = "0",
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取Bangumi每日放送探索数据
    """
    def __series_to_media(series_info: dict) -> MediaInfo:
        vote_average = None
        rating_info = series_info.get("rating", None)
        if rating_info is not None:
            vote_average = rating_info.get("score", None)
        title = series_info.get("name_cn") or series_info.get("name")
        return MediaInfo(
            type="电视剧",
            source="bangumi",
            title=title,
            mediaid_prefix="bangumidaily",
            media_id=series_info.get("id"),
            bangumi_id=series_info.get("id"),
            poster_path=series_info.get("images", {}).get("large"),
            vote_average=vote_average,
            first_air_date=series_info.get("air_date", None)
        )
    try:
        result = __request()
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

def bangumidaily_filter_ui():
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

def discover_source(master_plugin, event_data):
    _ = master_plugin
    bangumidaily_source = DiscoverMediaSource(
        name="Bangumi每日放送",
        mediaid_prefix="bangumidaily",
        api_path=f"plugin/ExploreServices/bangumidaily_discover?apikey={settings.API_TOKEN}",
        filter_params={"weekday": "0"},
        filter_ui=bangumidaily_filter_ui(),
    )
    if not event_data.extra_sources:
        event_data.extra_sources = [bangumidaily_source]
    else:
        event_data.extra_sources.append(bangumidaily_source)
