from typing import Tuple
from lxml import etree
from app.log import logger
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler

class LuckptHandler(NexusPHPHandler):
    """
    LuckPT 站点处理器
    采用非标准的 DIV + Flex 布局，包含左侧聊天区和右侧许愿池
    """

    def match(self) -> bool:
        """
        判断是否为 LuckPT 站点
        """
        return "LuckPT" in self.site_name or "幸运" in self.site_name

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息并获取反馈
        """
        try:
            # 1. 调用父类方法发送消息
            result = ISiteHandler.send_messagebox(self, message, callback)
            if not result[0]:
                return result

            # 2. 获取当前用户名
            username = self.get_username()
            if not username:
                return result

            # 3. 获取最新消息
            response = self._send_get_request(self.shoutbox_url)
            if not response:
                return result

            html = etree.HTML(response.text)
            feedbacks = []

            # 系统反馈示例: "@username 幸运池听到了你的愿望，增加了XXX幸运星"
            wish_contents = html.xpath("//div[contains(@class, 'wish-bubble-system')]//div[contains(@class, 'wish-content')]")
            for content_node in wish_contents:
                text = "".join(content_node.xpath(".//text()")).strip()
                if f"@{username}" in text:
                    feedbacks.append(text)
                    # 找到就退出，因为是从上(新)到下(旧)遍历的
                    break
            
            if feedbacks:
                 # 找到了许愿池反馈
                return self._return_feedback(result, feedbacks[0], callback)

            # 只看前10条，避免性能问题
            chat_containers = html.xpath("//div[contains(@class, 'chat-message-container')][position() <= 10]")
            
            for container in chat_containers:
                # 提取内容
                content_node = container.xpath(".//div[contains(@class, 'chat-content')]")
                if not content_node:
                    continue
                content = "".join(content_node[0].xpath(".//text()")).strip()
                
                # 简单匹配: 包含 @username 或者是 admin 回复的
                if f"@{username}" in content:
                    feedbacks.append(content)
                    break 

            if feedbacks:
                return self._return_feedback(result, feedbacks[0], callback)

            # 没找到特定反馈
            return result

        except Exception as e:
            logger.error(f"LuckPT 获取反馈消息失败: {str(e)}")
            return False, str(e)

    def _return_feedback(self, original_result, feedback_text, callback):
        self._last_message_result = feedback_text
        if callback:
            callback(True, feedback_text)
        return True, feedback_text
