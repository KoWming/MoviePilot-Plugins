from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from app.utils.http import RequestUtils
from datetime import datetime
from typing import List, Dict
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

def __fetch_raw_bangumi_data() -> List[dict] | None:
    api_url = "https://api.bgm.tv/calendar"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://api.bgm.tv/",
    }
    try:
        res = RequestUtils(headers=headers).get_res(api_url)
        if res is None:
            logger.error("无法连接Bangumi每日放送，请检查网络连接！")
            return None
        if not res.ok:
            logger.error(f"请求Bangumi每日放送 API失败：{res.text}")
            return None
        return res.json()
    except Exception as e:
        logger.error(f"请求Bangumi数据时发生异常: {str(e)}")
        return None

def __convert_to_media_info(series_info: dict) -> MediaInfo:
    rating_info = series_info.get("rating", {})
    title = series_info.get("name_cn") or series_info.get("name", "")
    images = series_info.get("images", {}) or {}

    return MediaInfo(
        type="电视剧",
        source="bangumi",
        title=title,
        mediaid_prefix="bangumidaily",
        media_id=str(series_info.get("id", "")),
        bangumi_id=series_info.get("id", None),
        poster_path=images.get("large", ""),
        vote_average=rating_info.get("score", 0),
        first_air_date=series_info.get("air_date", ""),
    )

@cached(cache=TTLCache(maxsize=1, ttl=1800))
def __get_processed_bangumi_data() -> Dict[str, List[MediaInfo]] | None:
    raw_data = __fetch_raw_bangumi_data()
    if not raw_data:
        return None

    processed_data: Dict[str, List[MediaInfo]] = {
        str(day[0]): [] for day in weekdays
    }

    all_items = []

    for day_entry in raw_data:
        weekday_id_num = day_entry.get("weekday", {}).get("id")
        if weekday_id_num is None:
            continue

        weekday_id = str(weekday_id_num)

        converted_items = [
            __convert_to_media_info(item)
            for item in day_entry.get("items", [])
        ]

        if weekday_id in processed_data:
            processed_data[weekday_id].extend(converted_items)

        all_items.extend(converted_items)

    processed_data["0"] = all_items
    return processed_data

def bangumidaily_discover(
    weekday: str = "0",
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取Bangumi每日放送探索数据
    """
    try:
        processed_data = __get_processed_bangumi_data()
        if not processed_data:
            return []

        results = processed_data.get(str(weekday), [])

        start_idx = (page - 1) * count
        end_idx = start_idx + count
        return results[start_idx:end_idx]

    except Exception as e:
        logger.error(f"获取Bangumi每日放送数据失败: {str(e)}", exc_info=True)
        return []

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
