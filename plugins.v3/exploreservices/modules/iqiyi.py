# 聚合自 LLL001a/MoviePilot-Plugins 的 plugins.v3/iqiyidiscover（上游 v2.1.4），保留原生媒体身份与风控处理
import json
import re
import threading
import time
from typing import Any, Dict, List, Optional

from app.schemas import DiscoverMediaSource, DiscoverSourceEventData, Response
from app.schemas.types import MediaSource, MediaType
from app.sdk.config import settings
from app.sdk.events import Event
from app.sdk.logging import logger
from app.sdk.media import MediaInfo, MetaInfo
from app.sdk.network import RequestUtils

from .base import SourceModule

try:
    from cloakbrowser import launch_context
except ImportError:
    launch_context = None

IQIYI_MEDIA_SOURCE = MediaSource("iqiyi")

CHANNEL_PARAMS = {
    "tv": {"channel_id": "2", "name": "电视剧"},
    "movie": {"channel_id": "1", "name": "电影"},
    "anime": {"channel_id": "4", "name": "动漫"},
    "variety": {"channel_id": "6", "name": "综艺"},
}

GROUP_MODEL_MAP = {
    "排序": "mode",
    "类型": "type",
    "地区": "area",
    "时间": "year",
    "资费": "pay",
    "付费": "pay",
    "殿堂": "hall",
    "推荐": "recommend",
    "连载": "serial",
    "版本": "version",
    "风格": "style",
    "明星": "star",
    "奖项": "award",
    "剧场": "theater",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.iqiyi.com/",
}

VIDEOLIB_DATA_URL = "https://mesh.if.iqiyi.com/portal/lw/videolib/data"
VIDEOLIB_TAG_URL = "https://mesh.if.iqiyi.com/portal/lw/videolib/tag"

BASE_PARAMS = {
    "uid": "",
    "passport_id": "",
    "ret_num": "60",
    "pcv": "17.084.26143",
    "version": "17.084.26143",
    "device_id": "4b0c3e7cb568d5e6ccc4bf823293e709",
    "session": "",
    "token": "",
    "os": "10.0",
    "conduit_id": "",
    "vip": "0",
    "auth": "",
    "recent_selected_tag": "",
}

BASE_UI: Optional[List[dict]] = None
_UI_BUILD_LOCK = threading.Lock()
_UI_BUILDING = False
_UI_THREAD: Optional[threading.Thread] = None


def init_base_ui() -> List[dict]:
    """
    初始化爱奇艺筛选 UI

    通过 videolib/tag 接口获取各频道的筛选标签，生成 Vuetify 筛选组件

    :return List: 筛选 UI 配置列表
    """
    ui: List[dict] = []
    for key, value in CHANNEL_PARAMS.items():
        params = {
            "channel_id": value["channel_id"],
            "tagAdd": "",
            "selected_tag_name": "免费",
            "version": "17.084.26143",
            "device": "4b0c3e7cb568d5e6ccc4bf823293e709",
            "uid": "",
        }
        try:
            res = RequestUtils(headers=HEADERS).get_res(VIDEOLIB_TAG_URL, params=params)
            if res is None or not res.ok:
                logger.warning(f"获取爱奇艺筛选标签失败: {key}")
                continue
            tag_groups = res.json()
        except Exception as err:
            logger.warning(f"获取爱奇艺筛选标签异常: {key} {err}")
            continue
        if not isinstance(tag_groups, list):
            continue
        for group in tag_groups:
            if not group.get("display"):
                continue
            group_name = group.get("group")
            tags = group.get("tags", [])
            if not tags:
                continue
            model = GROUP_MODEL_MAP.get(group_name, group_name)
            chip_data = [
                {
                    "component": "VChip",
                    "props": {
                        "filter": True,
                        "tile": True,
                        "value": tag.get("query_value", ""),
                    },
                    "text": tag.get("text", ""),
                }
                for tag in tags
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
                            "content": [{"component": "VLabel", "text": group_name}],
                        },
                        {
                            "component": "VChipGroup",
                            "props": {"model": model},
                            "content": chip_data,
                        },
                    ],
                }
            )
    return ui


def _build_base_ui() -> None:
    """
    后台构建爱奇艺筛选 UI
    """
    global BASE_UI, _UI_BUILDING
    try:
        BASE_UI = init_base_ui()
    except Exception as err:
        logger.warning(f"构建爱奇艺筛选 UI 失败：{err}")
        BASE_UI = []
    finally:
        _UI_BUILDING = False


def ensure_base_ui(timeout: float = 0.0) -> List[dict]:
    """
    返回爱奇艺筛选 UI

    缓存缺失时在后台构建，探索页请求不等待网络，只有插件初始化阶段允许短时等待

    :param timeout (float): 初始化阶段等待构建完成的最长秒数

    :return List: 筛选 UI 配置列表
    """
    global BASE_UI, _UI_BUILDING, _UI_THREAD
    if BASE_UI is not None:
        return BASE_UI
    with _UI_BUILD_LOCK:
        if BASE_UI is not None:
            return BASE_UI
        if not _UI_BUILDING:
            _UI_BUILDING = True
            _UI_THREAD = threading.Thread(
                target=_build_base_ui,
                daemon=True,
                name="iqiyi-filter-ui",
            )
            _UI_THREAD.start()
    if timeout > 0 and _UI_THREAD is not None:
        _UI_THREAD.join(timeout)
    return BASE_UI or []


class IqiyiDiscover(SourceModule):
    """
    爱奇艺探索模块，让聚合插件提供爱奇艺数据浏览
    """

    plugin_name = "爱奇艺"

    MEDIA_IDENTITY_KEY = "media_identity"
    COOKIE_KEY = "iqiyi_cookie"

    def __init__(self, owner: Any, module_key: str) -> None:
        super().__init__(owner, module_key)
        self._cookie = ""
        self._cookie_refresh_time = 0.0
        self._refresh_cron = ""
        self._cookie_lock = threading.Lock()

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """
        根据配置初始化爱奇艺探索模块

        :param config (dict): 模块配置，包含 enabled、cookie、refresh_cron
        """
        config = config or {}
        self._enabled = bool(config.get("enabled", False))
        self._cookie = self._parse_cookie(config.get("cookie") or "")
        self._refresh_cron = config.get("refresh_cron") or ""
        if "iqiyipic.com" not in settings.SECURITY_IMAGE_DOMAINS:
            settings.SECURITY_IMAGE_DOMAINS.append("iqiyipic.com")
        if not self._enabled:
            return
        if not self._cookie:
            self._cookie = self.get_data(self.COOKIE_KEY) or ""
        ensure_base_ui(timeout=2.0)

    def get_state(self) -> bool:
        """
        返回模块是否已启用

        :return bool: 启用状态
        """
        return bool(self._enabled)

    def get_media_source(self) -> List[Dict[str, Any]]:
        """
        返回爱奇艺媒体数据源声明

        :return List: 媒体数据源声明列表
        """
        return [
            {
                "name": "爱奇艺",
                "media_source": IQIYI_MEDIA_SOURCE,
                "media_types": [MediaType.MOVIE, MediaType.TV],
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        """
        返回爱奇艺探索数据源 API

        :return List: API 端点列表
        """
        return [
            {
                "path": "/iqiyi_discover",
                "endpoint": self.iqiyi_discover,
                "methods": ["GET"],
                "summary": "爱奇艺探索数据源",
                "description": "获取爱奇艺探索数据",
                "response_model": Response[List[MediaInfo]],
            }
        ]

    def get_service(self) -> List[Dict[str, Any]]:
        """
        返回爱奇艺 Cookie 定时刷新服务

        :return List: 定时服务列表
        """
        if not self.get_state() or not self._refresh_cron:
            return []
        from apscheduler.triggers.cron import CronTrigger

        try:
            trigger = CronTrigger.from_crontab(self._refresh_cron)
        except Exception as err:
            logger.warning(
                f"爱奇艺探索定时刷新周期配置无效：{self._refresh_cron} - {err}"
            )
            return []
        return [
            {
                "id": "IqiyiDiscover.RefreshCookie",
                "name": "爱奇艺探索Cookie定时刷新",
                "trigger": trigger,
                "func": self.refresh_cookie,
                "kwargs": {},
            }
        ]

    def refresh_cookie(self) -> bool:
        """
        刷新爱奇艺 Cookie，供宿主定时服务调用

        :return bool: 是否刷新成功
        """
        return self._auto_refresh_cookie()

    @staticmethod
    def _parse_cookie(raw: str) -> str:
        """
        解析用户提供的 Cookie，转换为标准请求头格式

        支持标准格式、浏览器开发者工具表格格式与 JSON 数组格式

        :param raw (str): 用户提供的原始 Cookie 字符串

        :return str: 标准 Cookie 字符串
        """
        if not raw:
            return ""
        text = raw.strip()
        if text.startswith("[") and text.endswith("]"):
            try:
                items = json.loads(text)
                pairs = [
                    f"{item.get('name')}={item.get('value')}"
                    for item in items
                    if isinstance(item, dict)
                    and item.get("name")
                    and item.get("value") is not None
                ]
                if pairs:
                    return "; ".join(pairs)
            except (ValueError, TypeError):
                pass
        if "\t" in text:
            pairs = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                cols = line.split("\t")
                if len(cols) >= 2 and cols[0].strip() and cols[1].strip():
                    pairs.append(f"{cols[0].strip()}={cols[1].strip()}")
            if pairs:
                return "; ".join(pairs)
        return " ".join(text.split())

    @staticmethod
    def _extract_device_id(cookie: str) -> Optional[str]:
        """
        从 Cookie 中提取设备 ID

        :param cookie (str): Cookie 字符串

        :return str: 设备 ID，未找到时返回 None
        """
        if not cookie:
            return None
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("QC005="):
                return part.split("=", 1)[1].strip()
        return None

    @staticmethod
    def _launch_browser() -> Any:
        """
        启动浏览器上下文

        优先使用 cloakbrowser 生成设备指纹，缺失时回退到宿主浏览器 SDK

        :return Any: 浏览器上下文
        """
        if launch_context is not None:
            return launch_context(headless=True)
        from app.sdk.browser import launch_browser_context

        return launch_browser_context(headless=True)

    def _auto_refresh_cookie(self) -> bool:
        """
        通过浏览器访问爱奇艺片库页面获取 Cookie

        爱奇艺接口有风控，需要携带 __dfp 设备指纹；并发锁保证同一时间只有一个刷新任务

        :return bool: 是否成功获取 Cookie
        """
        if not self._cookie_lock.acquire(blocking=False):
            logger.info("已有爱奇艺 Cookie 获取任务在运行，跳过本次刷新")
            return bool(self._cookie)
        context = None
        page = None
        try:
            logger.info("正在通过浏览器自动获取爱奇艺 Cookie")
            context = self._launch_browser()
            page = context.new_page()
            page.goto("https://www.iqiyi.com/list/tv/", timeout=120000)
            page.wait_for_load_state("networkidle", timeout=60000)
            time.sleep(3)
            cookies = context.cookies()
            if not cookies:
                logger.warning("未获取到爱奇艺 Cookie")
                return False
            cookie_str = "; ".join(
                f"{item.get('name')}={item.get('value')}"
                for item in cookies
                if item.get("name") and item.get("value")
            )
            if not cookie_str:
                logger.warning("爱奇艺 Cookie 为空")
                return False
            self._cookie = cookie_str
            self._cookie_refresh_time = time.time()
            self.save_data(self.COOKIE_KEY, cookie_str)
            logger.info(f"成功获取爱奇艺 Cookie（{len(cookies)} 项）")
            return True
        except Exception as err:
            logger.error(f"自动获取爱奇艺 Cookie 失败: {err}", exc_info=True)
            return False
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            try:
                self._cookie_lock.release()
            except RuntimeError:
                pass

    def _ensure_cookie(self) -> None:
        """
        确保请求前存在可用 Cookie，缺失时同步获取
        """
        if not self._cookie:
            self._cookie = self.get_data(self.COOKIE_KEY) or ""
        if not self._cookie:
            self._auto_refresh_cookie()

    def _request(self, channel_id: str, page: int, filter_params: str) -> List[dict]:
        """
        请求爱奇艺筛选数据接口

        :param channel_id (str): 频道 ID
        :param page (int): 页码
        :param filter_params (str): 筛选参数 JSON 字符串

        :return List: 媒体数据列表
        """
        params = dict(BASE_PARAMS)
        params["channel_id"] = channel_id
        params["page_id"] = str(page)
        params["filter"] = filter_params or '{"mode":"11"}'
        headers = dict(HEADERS)
        self._ensure_cookie()
        device_id = self._extract_device_id(self._cookie)
        if self._cookie:
            headers["Cookie"] = self._cookie
        if device_id:
            params["device_id"] = device_id
        res = RequestUtils(headers=headers).get_res(VIDEOLIB_DATA_URL, params=params)
        if res is None:
            raise ConnectionError("无法连接爱奇艺，请检查网络连接！")
        if not res.ok:
            raise ValueError(f"请求爱奇艺 API失败：{res.text}")
        data = res.json()
        if data.get("code") == 0 and not data.get("data"):
            logger.warning("爱奇艺接口返回空数据，可能被风控拦截，尝试刷新 Cookie")
            if self._auto_refresh_cookie():
                device_id = self._extract_device_id(self._cookie)
                headers["Cookie"] = self._cookie
                if device_id:
                    params["device_id"] = device_id
                res = RequestUtils(headers=headers).get_res(
                    VIDEOLIB_DATA_URL, params=params
                )
                if res is not None and res.ok:
                    data = res.json()
        return data.get("data") or []

    def _save_media_identities(self, items: List[dict]) -> None:
        """
        保存媒体身份缓存，供后续媒体识别使用

        :param items (List): 爱奇艺媒体数据列表
        """
        identities = self.get_data(self.MEDIA_IDENTITY_KEY) or {}
        for item in items:
            media_id = str(item.get("album_id") or item.get("entity_id") or "")
            title = item.get("display_name") or item.get("title")
            if not media_id or not title:
                continue
            identities[media_id] = {"title": title, "year": self._get_year(item)}
        self.save_data(
            self.MEDIA_IDENTITY_KEY, dict(list(identities.items())[-2000:])
        )

    def _get_media_identity(self, media_id: str) -> Dict[str, Any]:
        """
        获取媒体身份缓存

        :param media_id (str): 爱奇艺媒体 ID

        :return Dict: 媒体身份字典
        """
        identities = self.get_data(self.MEDIA_IDENTITY_KEY) or {}
        return identities.get(str(media_id)) or {}

    def _remember_media_identity(
        self, media_id: str, title: str, year: Optional[str]
    ) -> None:
        """
        记录媒体身份

        :param media_id (str): 爱奇艺媒体 ID
        :param title (str): 标题
        :param year (str): 年份
        """
        identities = self.get_data(self.MEDIA_IDENTITY_KEY) or {}
        identities[str(media_id)] = {"title": title, "year": year}
        self.save_data(
            self.MEDIA_IDENTITY_KEY, dict(list(identities.items())[-2000:])
        )

    @staticmethod
    def _normalize_media_type(mtype: Any) -> Optional[MediaType]:
        """
        规范化媒体类型

        :param mtype (Any): 媒体类型

        :return MediaType: 媒体类型枚举，无法识别时返回 None
        """
        if isinstance(mtype, MediaType):
            return mtype
        try:
            return MediaType(mtype) if mtype else None
        except (TypeError, ValueError):
            return None

    def recognize_media(
        self,
        meta: Any = None,
        mtype: Any = None,
        media_source: Optional[MediaSource] = None,
        media_id: Optional[str] = None,
        episode_group: Optional[str] = None,
        cache: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        通过爱奇艺媒体 ID 识别媒体信息

        :param meta (Any): 已知媒体元数据
        :param mtype (MediaType): 媒体类型
        :param media_source (MediaSource): 媒体来源
        :param media_id (str): 爱奇艺媒体 ID
        :param episode_group (str): 剧集组
        :param cache (bool): 是否使用 MoviePilot 识别缓存
        :param kwargs (Any): 兼容 MoviePilot 模块参数

        :return Any: 识别成功返回媒体信息，否则返回 None
        """
        if str(media_source or "").lower() not in {"iqiyi", "iqiyidiscover"}:
            return None
        if not media_id:
            return None
        media_type = self._normalize_media_type(mtype or getattr(meta, "type", None))
        source_media = self._get_media_identity(str(media_id))
        title = source_media.get("title") or getattr(meta, "title", None)
        year = source_media.get("year") or getattr(meta, "year", None)
        if not title:
            return None
        self._remember_media_identity(
            str(media_id), title, str(year) if year else None
        )
        recognize_meta = MetaInfo(title=title)
        recognize_meta.year = str(year) if year else None
        recognize_meta.type = media_type
        mediainfo = self.chain.run_module(
            "recognize_media",
            meta=recognize_meta,
            mtype=media_type,
            media_source=MediaSource.TMDB,
            media_id=None,
            episode_group=episode_group,
            cache=cache,
        )
        if not mediainfo:
            return None
        mediainfo.media_source = IQIYI_MEDIA_SOURCE
        mediainfo.media_id = str(media_id)
        return mediainfo

    async def async_recognize_media(
        self,
        meta: Any = None,
        mtype: Any = None,
        media_source: Optional[MediaSource] = None,
        media_id: Optional[str] = None,
        episode_group: Optional[str] = None,
        cache: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        异步通过爱奇艺媒体 ID 识别媒体信息

        :param meta (Any): 已知媒体元数据
        :param mtype (MediaType): 媒体类型
        :param media_source (MediaSource): 媒体来源
        :param media_id (str): 爱奇艺媒体 ID
        :param episode_group (str): 剧集组
        :param cache (bool): 是否使用 MoviePilot 识别缓存
        :param kwargs (Any): 兼容 MoviePilot 模块参数

        :return Any: 识别成功返回媒体信息，否则返回 None
        """
        if str(media_source or "").lower() not in {"iqiyi", "iqiyidiscover"}:
            return None
        if not media_id:
            return None
        media_type = self._normalize_media_type(mtype or getattr(meta, "type", None))
        source_media = self._get_media_identity(str(media_id))
        title = source_media.get("title") or getattr(meta, "title", None)
        year = source_media.get("year") or getattr(meta, "year", None)
        if not title:
            return None
        identities = await self.async_get_data(self.MEDIA_IDENTITY_KEY) or {}
        identities[str(media_id)] = {
            "title": title,
            "year": str(year) if year else None,
        }
        await self.async_save_data(
            self.MEDIA_IDENTITY_KEY, dict(list(identities.items())[-2000:])
        )
        recognize_meta = MetaInfo(title=title)
        recognize_meta.year = str(year) if year else None
        recognize_meta.type = media_type
        mediainfo = await self.chain.async_run_module(
            "async_recognize_media",
            meta=recognize_meta,
            mtype=media_type,
            media_source=MediaSource.TMDB,
            media_id=None,
            episode_group=episode_group,
            cache=cache,
        )
        if not mediainfo:
            return None
        mediainfo.media_source = IQIYI_MEDIA_SOURCE
        mediainfo.media_id = str(media_id)
        return mediainfo

    @staticmethod
    def _clean_param(value: Optional[str]) -> Optional[str]:
        """
        清理探索页传入的空参数

        :param value (str): 原始参数

        :return str: 清理后的参数，空值返回 None
        """
        if value is None or value == "None" or value == "null" or value == "":
            return None
        return value

    def iqiyi_discover(
        self,
        mtype: str = "tv",
        mode: Optional[str] = None,
        type: Optional[str] = None,
        area: Optional[str] = None,
        year: Optional[str] = None,
        pay: Optional[str] = None,
        hall: Optional[str] = None,
        recommend: Optional[str] = None,
        award: Optional[str] = None,
        theater: Optional[str] = None,
        page: int = 1,
        count: int = 60,
    ) -> Response[List[MediaInfo]]:
        """
        获取爱奇艺探索数据

        :param mtype (str): 频道类型，tv/movie/anime/variety
        :param mode (str): 排序方式
        :param type (str): 类型筛选
        :param area (str): 地区筛选
        :param year (str): 年份筛选
        :param pay (str): 资费筛选
        :param hall (str): 殿堂筛选
        :param recommend (str): 推荐筛选
        :param award (str): 奖项筛选
        :param theater (str): 剧场筛选
        :param page (int): 页码
        :param count (int): 每页数量

        :return Response: 探索数据响应
        """
        if mtype not in CHANNEL_PARAMS:
            logger.warning(f"未知的爱奇艺频道类型: {mtype}")
            return Response(success=True, data=[])

        mode = self._clean_param(mode)
        type = self._clean_param(type)
        area = self._clean_param(area)
        year = self._clean_param(year)
        pay = self._clean_param(pay)
        hall = self._clean_param(hall)
        recommend = self._clean_param(recommend)
        award = self._clean_param(award)
        theater = self._clean_param(theater)

        filter_params: Dict[str, str] = {}
        if mode:
            filter_params["mode"] = mode
        if type:
            filter_params["three_category_id_v2"] = type
        if area:
            filter_params["three_category_id_v2"] = area
        if year:
            filter_params["market_release_date_level"] = year
        if pay:
            filter_params["is_purchase"] = pay
        if hall:
            filter_params["smart_tag_v2"] = hall
        if recommend:
            filter_params["smart_tag_v2"] = recommend
        if award:
            filter_params["structure_id"] = award
        if theater:
            filter_params["smart_tag_v2"] = theater
        if not filter_params:
            filter_params = {"mode": "11"}

        try:
            result = self._request(
                CHANNEL_PARAMS[mtype]["channel_id"],
                page,
                json.dumps(filter_params, ensure_ascii=False),
            )
        except Exception as err:
            logger.error(str(err))
            return Response(success=True, data=[])

        if not result:
            return Response(success=True, data=[])
        target_channel_id = CHANNEL_PARAMS[mtype]["channel_id"]
        result = [
            item for item in result if str(item.get("channel_id")) == target_channel_id
        ]
        self._save_media_identities(result)
        if mtype == "movie":
            results = [self._movie_to_media(item) for item in result]
        else:
            results = [self._series_to_media(item) for item in result]
        return Response(success=True, data=results[:count])

    def _movie_to_media(self, movie_info: dict) -> MediaInfo:
        """
        爱奇艺电影数据转换为 MediaInfo

        :param movie_info (dict): 爱奇艺媒体数据

        :return MediaInfo: 媒体信息
        """
        return MediaInfo(
            type=MediaType.MOVIE,
            media_source=IQIYI_MEDIA_SOURCE,
            title=movie_info.get("display_name") or movie_info.get("title"),
            year=self._get_year(movie_info),
            media_id=str(movie_info.get("album_id") or movie_info.get("entity_id")),
            poster_path=self._get_poster(movie_info),
        )

    def _series_to_media(self, series_info: dict) -> MediaInfo:
        """
        爱奇艺剧集数据转换为 MediaInfo

        :param series_info (dict): 爱奇艺媒体数据

        :return MediaInfo: 媒体信息
        """
        return MediaInfo(
            type=MediaType.TV,
            media_source=IQIYI_MEDIA_SOURCE,
            title=series_info.get("display_name") or series_info.get("title"),
            year=self._get_year(series_info),
            media_id=str(series_info.get("album_id") or series_info.get("entity_id")),
            poster_path=self._get_poster(series_info),
        )

    @staticmethod
    def _get_year(media_info: dict) -> Optional[str]:
        """
        从媒体数据中提取年份

        :param media_info (dict): 爱奇艺媒体数据

        :return str: 年份字符串
        """
        date = media_info.get("date") or {}
        if isinstance(date, dict) and date.get("year"):
            return str(date.get("year"))
        if media_info.get("showDate"):
            return str(media_info.get("showDate")).split("-")[0]
        return None

    @staticmethod
    def _get_poster(media_info: dict) -> Optional[str]:
        """
        获取高清海报地址

        优先使用接口返回的高清字段，其次从封面基础地址构造 300x450 竖版海报

        :param media_info (dict): 爱奇艺媒体数据

        :return str: 海报地址
        """
        poster = media_info.get("image_url_2x") or media_info.get("image_url_normal")
        if poster:
            return poster
        cover = media_info.get("image_cover")
        if cover:
            base = re.sub(r"_\d+_\d+\.\w+$", "", cover)
            base = re.sub(r"\.\w+$", "", base)
            if base:
                return f"{base}_300_450.jpg"
        return cover

    @staticmethod
    def iqiyi_filter_ui() -> List[dict]:
        """
        爱奇艺过滤参数 UI 配置

        :return List: 前端表单组件列表
        """
        mtype_ui = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": key},
                "text": value["name"],
            }
            for key, value in CHANNEL_PARAMS.items()
        ]
        ui: List[dict] = [
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
        ui.extend(ensure_base_ui())
        return ui

    def discover_source(self, event: Event) -> None:
        """
        向探索事件注册爱奇艺数据源

        :param event (Event): 探索数据源事件
        """
        if not self._enabled:
            return
        event_data: DiscoverSourceEventData = event.event_data
        iqiyi_source = DiscoverMediaSource(
            name="爱奇艺",
            media_source=IQIYI_MEDIA_SOURCE,
            mediaid_prefix="iqiyi",
            api_path=f"plugin/{self.plugin_id}/iqiyi_discover?apikey={settings.API_TOKEN}",
            filter_params={
                "mtype": "tv",
                "mode": None,
                "type": None,
                "area": None,
                "year": None,
                "pay": None,
                "hall": None,
                "recommend": None,
                "award": None,
                "theater": None,
                "page": 1,
                "count": 60,
            },
            filter_ui=self.iqiyi_filter_ui(),
            depends={
                "mode": ["mtype"],
                "type": ["mtype"],
                "area": ["mtype"],
                "year": ["mtype"],
                "pay": ["mtype"],
                "hall": ["mtype"],
                "recommend": ["mtype"],
                "award": ["mtype"],
                "theater": ["mtype"],
                "page": ["mtype"],
                "count": ["mtype"],
            },
        )
        if not event_data.extra_sources:
            event_data.extra_sources = [iqiyi_source]
        else:
            event_data.extra_sources.append(iqiyi_source)

    def stop_service(self) -> None:
        """
        停止爱奇艺探索模块，当前无后台线程需要释放
        """
        self._cookie = ""
