from typing import Tuple, Optional, Dict
from urllib.parse import urljoin
from lxml import etree
import time
import re

from app.log import logger
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler

class CangBaoHandler(NexusPHPHandler):
    """
    藏宝阁站点处理类
    """
    
    def match(self) -> bool:
        """
        判断是否为藏宝阁站点
        """
        return "藏宝阁" in self.site_name

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息
        :param message: 消息内容
        :param callback: 回调函数
        :return: 发送结果
        """
        try:
            result = ISiteHandler.send_messagebox(self, message, callback)

            # 获取当前用户名
            username = self.get_username()
            if not username:
                return result
                
            # 藏宝阁站点，消息发送后等待65秒再获取消息（适应站点缓存或刷新机制）
            logger.info(f"站点: {self.site_name}, 等待65秒获取反馈消息...")
            time.sleep(65)

            # 获取最新消息
            response = self._send_get_request(self.shoutbox_url)
            if not response:
                return result
                
            # 解析HTML
            html = etree.HTML(response.text)
            
            # 提取前10条消息中的反馈
            feedbacks = []
            rows = html.xpath("//tr[td[@class='shoutrow']][position() <= 10]")
            
            for row in rows:
                row_content = "".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
                
                if f"响应了 {username} 的请求" in row_content:
                    feedbacks.append(row_content)
                    continue
                    
                if f"系统: {username} 您今天" in row_content:
                    feedbacks.append(row_content)
                    continue
                    
            if feedbacks:
                logger.info(f"获取到反馈消息: {feedbacks[0]}")
                result = (result[0], feedbacks[0])
            else:
                logger.info("未获取到相关反馈消息")
                
            self._last_message_result = result[1] if result[0] else None
            return result
            
        except Exception as e:
            logger.error(f"获取反馈消息失败: {str(e)}")
            return result

    def get_feedback(self, message: str = None) -> Optional[Dict]:
        """
        获取消息反馈
        """
        return super().get_feedback(message)
