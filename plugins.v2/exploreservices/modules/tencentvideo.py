import requests
import re
from typing import List
from cachetools import cached, TTLCache
from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger

CHANNEL_PARAMS = {
    "tv": {"Id": "100113", "Name": "电视剧"},
    "movie": {"Id": "100173", "Name": "电影"},
    "variety": {"Id": "100109", "Name": "综艺"},
    "anime": {"Id": "100119", "Name": "动漫"},
    "children": {"Id": "100150", "Name": "少儿"},
    "documentary": {"Id": "100105", "Name": "纪录片"},
}

PARAMS = {
    "video_appid": "1000005",
    "vplatform": "2",
    "vversion_name": "8.9.10",
    "new_mark_label_enabled": "1",
}

HEADERS = {
    "User-Agent": settings.USER_AGENT,
    "Referer": "https://v.qq.com/",
}

# 全局 UI 缓存
BASE_UI = None

def get_api(master_plugin):
    _ = master_plugin
    return [
        {
            "path": "/tencentvideo_discover",
            "endpoint": tencentvideo_discover,
            "methods": ["GET"],
            "summary": "腾讯视频探索数据源",
            "description": "获取腾讯视频探索数据",
        }
    ]

def init_base_ui():
    def get_page_data(channel_id):
        body = {
            "page_params": {
                "channel_id": channel_id,
                "page_type": "channel_operation",
                "page_id": "channel_list_second_page",
            }
        }
        body["page_context"] = {
            "data_src_647bd63b21ef4b64b50fe65201d89c6e_page": "0",
        }
        url = "https://pbaccess.video.qq.com/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData"
        try:
            response = requests.post(url, params=PARAMS, json=body, headers=HEADERS)
            response.raise_for_status()
            data = response.json().get("data")
            if not data:
                logger.error(f"No data returned for channel_id {channel_id}")
                return []
            module_list_datas = data.get("module_list_datas", [])
            if len(module_list_datas) < 2:
                logger.error(f"module_list_datas has insufficient length for channel_id {channel_id}: {module_list_datas}")
                return []
            module_datas = module_list_datas[1].get("module_datas", [])
            if not module_datas:
                logger.error(f"No module_datas for channel_id {channel_id}")
                return []
            item_data_lists = module_datas[0].get("item_data_lists", {})
            item_datas = item_data_lists.get("item_datas", [])
            if not item_datas:
                logger.warning(f"No item_datas for channel_id {channel_id}")
            return item_datas
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data for channel_id {channel_id}: {str(e)}")
            return []
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid response structure for channel_id {channel_id}: {str(e)}")
            return []
    ui = []
    for _key, _ in CHANNEL_PARAMS.items():
        data = []
        all_index = {}
        for item in get_page_data(CHANNEL_PARAMS[_key]["Id"]):
            if str(item.get("item_type")) == "11":
                if item.get("item_params", {}).get("index_name") not in all_index:
                    all_index[item["item_params"]["index_name"]] = []
                    all_index[item["item_params"]["index_name"]].append(item)
                else:
                    all_index[item["item_params"]["index_name"]].append(item)
        for _, value in all_index.items():
            data = [
                {
                    "component": "VChip",
                    "props": {
                        "filter": True,
                        "tile": True,
                        "value": j["item_params"]["option_value"],
                    },
                    "text": j["item_params"]["option_name"],
                }
                for j in value
                if str(j["item_params"].get("option_value", "")) != "-1"
            ]
            if str(value[0]["item_params"].get("option_value", "")) == "-1":
                text = value[0]["item_params"]["option_name"]
            else:
                text = value[0]["item_params"]["index_name"]
            ui.append(
                {
                    "component": "div",
                    "props": {
                        "class": "flex justify-start items-center",
                        "show": "{{mtype == '" + _key + "'}}",
                    },
                    "content": [
                        {
                            "component": "div",
                            "props": {"class": "mr-5"},
                            "content": [
                                {"component": "VLabel", "text": text} ],
                        },
                        {
                            "component": "VChipGroup",
                            "props": {"model": value[0]["item_params"]["index_item_key"]},
                            "content": data,
                        },
                    ],
                }
            )
    return ui

def tencentvideo_discover(
    mtype: str = "tv",
    recommend_3: str = None,
    itrailer: str = None,
    exclusive: str = None,
    child_ip: str = None,
    characteristic: str = None,
    anime_status: str = None,
    recommend: str = None,
    language: str = None,
    iregion: str = None,
    iyear: str = None,
    all: str = None,
    sort: str = None,
    ipay: str = None,
    producer: str = None,
    iarea: str = None,
    pay: str = None,
    attr: str = None,
    item: str = None,
    itype: str = None,
    recommend_2: str = None,
    recommend_1: str = None,
    award: str = None,
    theater: str = None,
    gender: str = None,
    page: int = 1,
    count: int = 10,
) -> List[MediaInfo]:
    """
    获取腾讯视频探索数据
    """
    @cached(cache=TTLCache(maxsize=32, ttl=1800))
    def __request(page, mtype, **kwargs):
        body = {
            "page_params": {
                "channel_id": CHANNEL_PARAMS[mtype]["Id"],
                "page_type": "channel_operation",
                "page_id": "channel_list_second_page",
            }
        }
        if kwargs:
            body["page_params"]["filter_params"] = "&".join(
                [f"{k}={v}" for k, v in kwargs.items()]
            )
        if str(page) != "1":
            body["page_context"] = {
                "data_src_647bd63b21ef4b64b50fe65201d89c6e_page": str(int(page) - 1),
            }
        url = "https://pbaccess.video.qq.com/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData"
        try:
            response = requests.post(url, params=PARAMS, json=body, headers=HEADERS)
            response.raise_for_status()
            data = response.json().get("data")
            if not data:
                logger.error(f"No data returned for mtype {mtype}, page {page}")
                return []
            module_list_datas = data.get("module_list_datas", [])
            if len(module_list_datas) < 2:
                logger.error(f"module_list_datas has insufficient length for mtype {mtype}, page {page}: {module_list_datas}")
                return []
            module_datas = module_list_datas[1].get("module_datas", [])
            if not module_datas:
                logger.error(f"No module_datas for mtype {mtype}, page {page}")
                return []
            item_data_lists = module_datas[0].get("item_data_lists", {})
            item_datas = item_data_lists.get("item_datas", [])
            if not item_datas:
                logger.warning(f"No item_datas for mtype {mtype}, page {page}")
            return item_datas
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data for mtype {mtype}, page {page}: {str(e)}")
            return []
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid response structure for mtype {mtype}, page {page}: {str(e)}")
            return []
    def __movie_to_media(movie_info: dict) -> MediaInfo:
        poster_url = movie_info.get("new_pic_vt", "")
        if not poster_url or not poster_url.startswith(("http://", "https://")):
            logger.warning(f"Invalid or missing poster URL for {movie_info.get('title')}: {poster_url}")
            poster_url = (
                movie_info.get("item_params", {}).get("pic_url")
                or movie_info.get("item_params", {}).get("image_url")
                or "https://v.qq.com/assets/default_poster.jpg"
            )
        else:
            poster_url = re.sub(r"/350", "", poster_url)
            if not poster_url.startswith(("http://", "https://")):
                logger.warning(f"Processed poster URL invalid for {movie_info.get('title')}: {poster_url}")
                poster_url = "https://v.qq.com/assets/default_poster.jpg"
        return MediaInfo(
            type="电影",
            title=movie_info.get("title"),
            year=movie_info.get("year"),
            title_year=f"{movie_info.get('title')} ({movie_info.get('year')})",
            mediaid_prefix="tencentvideo",
            media_id=str(movie_info.get("cid")),
            poster_path=poster_url,
        )
    def __series_to_media(series_info: dict) -> MediaInfo:
        poster_url = series_info.get("new_pic_vt", "")
        if not poster_url or not poster_url.startswith(("http://", "https://")):
            logger.warning(f"Invalid or missing poster URL for {series_info.get('title')}: {poster_url}")
            poster_url = (
                series_info.get("item_params", {}).get("pic_url")
                or series_info.get("item_params", {}).get("image_url")
                or "https://v.qq.com/assets/default_poster.jpg"
            )
        else:
            poster_url = re.sub(r"/350", "", poster_url)
            if not poster_url.startswith(("http://", "https://")):
                logger.warning(f"Processed poster URL invalid for {series_info.get('title')}: {poster_url}")
                poster_url = "https://v.qq.com/assets/default_poster.jpg"
        return MediaInfo(
            type="电视剧",
            title=series_info.get("title"),
            year=series_info.get("year"),
            title_year=f"{series_info.get('title')} ({series_info.get('year')})",
            mediaid_prefix="tencentvideo",
            media_id=str(series_info.get("cid")),
            poster_path=poster_url,
        )
    try:
        params = {}
        if recommend_3: params.update({"recommend_3": recommend_3})
        if itrailer: params.update({"itrailer": itrailer})
        if exclusive: params.update({"exclusive": exclusive})
        if child_ip: params.update({"child_ip": child_ip})
        if characteristic: params.update({"characteristic": characteristic})
        if anime_status: params.update({"anime_status": anime_status})
        if recommend: params.update({"recommend": recommend})
        if language: params.update({"language": language})
        if iregion: params.update({"iregion": iregion})
        if iyear: params.update({"iyear": iyear})
        if all: params.update({"all": all})
        if sort: params.update({"sort": sort})
        if ipay: params.update({"ipay": ipay})
        if producer: params.update({"producer": producer})
        if iarea: params.update({"iarea": iarea})
        if pay: params.update({"pay": pay})
        if attr: params.update({"attr": attr})
        if item: params.update({"item": item})
        if itype: params.update({"itype": itype})
        if recommend_2: params.update({"recommend_2": recommend_2})
        if recommend_1: params.update({"recommend_1": recommend_1})
        if award: params.update({"award": award})
        if theater: params.update({"theater": theater})
        if gender: params.update({"gender": gender})
        result = __request(page, mtype, **params)
    except Exception as err:
        logger.error(f"Error fetching Tencent Video data: {str(err)}")
        return []
    if not result:
        return []
    if mtype == "movie":
        results = [
            __movie_to_media(movie.get("item_params", {}))
            for movie in result
            if str(movie.get("item_type", "")) == "2"
        ]
    else:
        results = [
            __series_to_media(series.get("item_params", {}))
            for series in result
            if str(series.get("item_type", "")) == "2"
        ]
    return results

def tencentvideo_filter_ui():
    global BASE_UI
    if BASE_UI is None:
        BASE_UI = init_base_ui()
    mtype_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": key},
            "text": value["Name"],
        }
        for key, value in CHANNEL_PARAMS.items()
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
        }
    ]
    if BASE_UI:
        for i in BASE_UI:
            ui.append(i)
    return ui

def discover_source(master_plugin, event_data):
    _ = master_plugin
    tencentvideo_source = DiscoverMediaSource(
        name="腾讯视频",
        mediaid_prefix="tencentvideo",
        api_path=f"plugin/ExploreServices/tencentvideo_discover?apikey={settings.API_TOKEN}",
        filter_params={
            "mtype": "tv",
            "recommend_3": None,
            "itrailer": None,
            "exclusive": None,
            "child_ip": None,
            "characteristic": None,
            "anime_status": None,
            "recommend": None,
            "language": None,
            "iregion": None,
            "iyear": None,
            "all": None,
            "sort": None,
            "ipay": None,
            "producer": None,
            "iarea": None,
            "pay": None,
            "attr": None,
            "item": None,
            "itype": None,
            "recommend_2": None,
            "recommend_1": None,
            "award": None,
            "theater": None,
            "gender": None,
        },
        filter_ui=tencentvideo_filter_ui(),
        depends={
            "recommend_3": ["mtype"],
            "itrailer": ["mtype"],
            "exclusive": ["mtype"],
            "child_ip": ["mtype"],
            "characteristic": ["mtype"],
            "anime_status": ["mtype"],
            "recommend": ["mtype"],
            "language": ["mtype"],
            "iregion": ["mtype"],
            "iyear": ["mtype"],
            "all": ["mtype"],
            "sort": ["mtype"],
            "ipay": ["mtype"],
            "producer": ["mtype"],
            "iarea": ["mtype"],
            "pay": ["mtype"],
            "attr": ["mtype"],
            "item": ["mtype"],
            "itype": ["mtype"],
            "recommend_2": ["mtype"],
            "recommend_1": ["mtype"],
            "award": ["mtype"],
            "theater": ["mtype"],
            "gender": ["mtype"],
        },
    )
    if not event_data.extra_sources:
        event_data.extra_sources = [tencentvideo_source]
    else:
        event_data.extra_sources.append(tencentvideo_source)
        