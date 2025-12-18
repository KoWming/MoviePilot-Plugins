from typing import Tuple, Optional
from lxml import etree
import time
from app.log import logger
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler

class HxptHandler(NexusPHPHandler):
    """
    好学(Hxpt)站点处理类
    """
    
    def match(self) -> bool:
        """
        判断是否为好学站点
        """
        return "好学" in self.site_name

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
            
            response = self._send_get_request(self.shoutbox_url, params={
                'ajax_chat': '1',
                'type': '',
                't': str(int(time.time() * 1000))
            })
            if response:
                # 解析HTML
                html = etree.HTML(response.text)
                
                # 提取前10条消息行
                rows = html.xpath("//tr[td[@class='shoutrow']][position() <= 10]")
                
                feedback_content = None
                
                # 遍历行查找用户消息
                for i, row in enumerate(rows):
                    content = " ".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
                    content = " ".join(content.split())
                    
                    # 找到用户发送的消息
                    if f"@{username}" in content or username in content:
                        # 检查是否存在上一行
                        if i > 0:
                            prev_row = rows[i-1]
                            prev_content = " ".join(prev_row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
                            prev_content = " ".join(prev_content.split())
                            
                            # 检查上一行是否为系统提示
                            if "系统提示：" in prev_content:
                                feedback_content = prev_content
                                break

                # 如果有反馈消息
                if feedback_content:
                    logger.info(f"站点 {self.site_name} 收到精确匹配的反馈: {feedback_content}")
                    self._last_message_result = feedback_content
                    result = (result[0], feedback_content)
                    return result

            return result
            
        except Exception as e:
            logger.error(f"发送消息并获取反馈失败: {str(e)}")
            return result

    def get_feedback(self, message: str = None) -> Optional[dict]:
        """
        获取消息反馈
        :param message: 消息内容
        :return: 反馈信息字典
        """
        try:
            # 直接使用send_messagebox通过轮询获取并缓存的结果
            result = super().get_feedback(message)
            
            # 补充处理 "火花" 奖励类型
            if result and "rewards" in result and self._last_message_result:
                if "火花" in self._last_message_result:
                    result["rewards"][0]["type"] = "火花"
            
            return result
            
        except Exception as e:
            logger.error(f"解析反馈消息失败: {str(e)}")
            return None
