from typing import Dict, Type

from .base import SourceModule
from .bangumidaily import BangumiDailyDiscover
from .bilibili import BilibiliDiscover
from .cctv import CCTVDiscover
from .iqiyi import IqiyiDiscover
from .mangguo import MangGuoDiscover
from .migu import MiGuDiscover
from .tencentvideo import TencentVideoDiscover

MODULE_ORDER = (
    "tencentvideo",
    "bilibili",
    "cctv",
    "mangguo",
    "bangumidaily",
    "migu",
    "iqiyi",
)

MODULE_LABELS: Dict[str, str] = {
    "tencentvideo": "腾讯视频",
    "bilibili": "哔哩哔哩",
    "cctv": "CCTV",
    "mangguo": "芒果TV",
    "bangumidaily": "Bangumi每日放送",
    "migu": "咪咕视频",
    "iqiyi": "爱奇艺",
}

MODULE_CLASSES: Dict[str, Type[SourceModule]] = {
    "tencentvideo": TencentVideoDiscover,
    "bilibili": BilibiliDiscover,
    "cctv": CCTVDiscover,
    "mangguo": MangGuoDiscover,
    "bangumidaily": BangumiDailyDiscover,
    "migu": MiGuDiscover,
    "iqiyi": IqiyiDiscover,
}


def build_module(owner: object, module_key: str) -> SourceModule:
    """
    构建指定探索源模块实例

    :param owner (object): 所属聚合插件实例
    :param module_key (str): 模块标识

    :return SourceModule: 探索源模块实例
    """
    return MODULE_CLASSES[module_key](owner, module_key)
