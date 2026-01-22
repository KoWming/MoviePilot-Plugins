from typing import List, Optional
from .base import BaseMedalSiteHandler
from .zm_handler import ZmMedalHandler
from .php_handler import PhpMedalHandler
from .qingwa_handler import QingwaMedalHandler
from .audiences_handler import AudiencesMedalHandler
from .ubits_handler import UbitsMedalHandler
from .off_handler import OffMedalHandler
from .hhan_handler import HHanMedalHandler
from .ourbits_handler import OurbitsMedalHandler
from .hddolby_handler import HddolbyMedalHandler
from .longpt_handler import LongptMedalHandler
from .playlet_handler import PlayletMedalHandler
from .moment_handler import MomentMedalHandler
from .hxpt_handler import HxptMedalHandler
from .dubhe_handler import DubheMedalHandler


class MedalHandlerManager:
    """勋章处理器管理器"""
    
    def __init__(self):
        # 注册所有处理器
        self._handlers: List[BaseMedalSiteHandler] = [
            AudiencesMedalHandler(),  # 优先处理观众站点
            UbitsMedalHandler(),  # 优先处理UBits站点
            QingwaMedalHandler(),  # 优先处理qingwa站点
            LongptMedalHandler(),  # 优先处理LongPT站点
            PlayletMedalHandler(),  # 优先处理PlayLet站点
            MomentMedalHandler(),  # 优先处理Moment站点
            HxptMedalHandler(),  # 优先处理好学站点
            DubheMedalHandler(),  # 优先处理天枢站点
            OffMedalHandler(),  # 优先处理自由农场站点
            HHanMedalHandler(),  # 优先处理憨憨站点
            HddolbyMedalHandler(),  # 优先处理高清杜比站点
            OurbitsMedalHandler(),  # 优先处理OurBits站点
            ZmMedalHandler(),  # 优先处理织梦站点
            PhpMedalHandler(),  # 最后使用PHP通用处理器
        ]
        # 记录已匹配的站点
        self._matched_sites = set()
    
    def get_handler(self, site) -> Optional[BaseMedalSiteHandler]:
        """获取适配的处理器"""
        # 清空已匹配站点记录
        self._matched_sites.clear()
        
        # 遍历所有处理器
        for handler in self._handlers:
            if handler.match(site):
                # 记录已匹配的站点
                if hasattr(site, 'name'):
                    self._matched_sites.add(site.name.lower())
                return handler
        return None
    
    def register_handler(self, handler: BaseMedalSiteHandler):
        """注册新的处理器"""
        if handler not in self._handlers:
            self._handlers.append(handler)
    
    def unregister_handler(self, handler: BaseMedalSiteHandler):
        """注销处理器"""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def is_site_matched(self, site_name: str) -> bool:
        """检查站点是否已被其他处理器匹配"""
        return site_name.lower() in self._matched_sites

# 创建全局管理器实例
handler_manager = MedalHandlerManager() 