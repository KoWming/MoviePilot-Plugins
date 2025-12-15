from typing import Tuple
from lxml import etree

from app.log import logger
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler

class ThirteenCityHandler(NexusPHPHandler):
    """
    13City站点处理类
    """
    
    def match(self) -> bool:
        """
        判断是否为13City站点
        """
        return "13City" in self.site_name

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息
        :param message: 消息内容
        :param callback: 回调函数
        :return: 发送结果
        """
        try:
            # 调用父类方法发送消息
            result = ISiteHandler.send_messagebox(self, message, callback)

            # 获取当前用户名
            username = self.get_username()
            if not username:
                return result

            # 获取最新消息
            response = self._send_get_request(self.shoutbox_url)
            if not response:
                return result
                
            # 解析HTML
            html = etree.HTML(response.text)
            
            # 13City 特殊布局: 右侧栏 (shout-box-right) 显示系统/Bot反馈
            # 提取右侧栏的前10条消息
            feedbacks = []
            
            # 定位右侧栏的表格行
            # 路径: div class='shout-box-right' -> div -> table -> tr -> td class='shoutrow'
            rows = html.xpath("//div[contains(@class, 'shout-box-right')]//tr[td[@class='shoutrow']][position() <= 10]")
            
            for row in rows:
                # 提取消息内容
                content = "".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
                
                # 检查是否包含 @username
                if f"@{username}" in content:
                    feedbacks.append(content)
                    
            # 如果有反馈消息,更新结果
            if feedbacks:
                result = (result[0], feedbacks[0])
                
            # 保存结果
            self._last_message_result = result[1] if result[0] else None
            return result
            
        except Exception as e:
            logger.error(f"获取反馈消息失败: {str(e)}")
            return result
