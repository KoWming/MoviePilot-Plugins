from typing import Tuple
from app.log import logger
import re
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler

class PtskitHandler(NexusPHPHandler):
    """
    Ptskit (PTS) 站点处理器
    反馈消息通过 JavaScript alert() 弹窗返回
    """

    def match(self) -> bool:
        """
        判断是否为PTS站点
        """
        return "PTS" in self.site_name

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
    """
    发送消息并获取反馈，专门处理 alert 弹窗
    """
    def parse_alert(response):
        content = response.text
        match = re.search(r"(?:window\.|)alert\((['\"])(.*?)\1\)", content)

        if match:
            return match.group(2)

        # 如果没找到 alert，尝试回退到标准解析
        try:
            from lxml import etree
            html = etree.HTML(content)
            text = " ".join(html.xpath("//tr[1]/td//text()")).strip()
            if text:
                return text
        except:
            pass

        logger.warning(f"Ptskit: 未在响应中找到 alert 弹窗。响应片段: {content[:100]}")
        return "发送成功，但无法解析反馈 (未发现弹窗)"

    try:
        # 关键字参数传递，避免参数重复赋值
        return ISiteHandler.send_messagebox(self, message=message, callback=callback, rt_method=parse_alert)

    except Exception as e:
        logger.error(f"Ptskit 发送消息失败: {str(e)}")
        return False, str(e)