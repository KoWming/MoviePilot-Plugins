from typing import Tuple
from app.log import logger
from lxml import etree
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler

class DubheHandler(NexusPHPHandler):
    """
    天枢 (Dubhe) 站点处理器
    反馈消息通常包含 "神明"、"奇迹" 等关键词，且不使用 @提醒
    """

    def match(self) -> bool:
        """
        判断是否为天枢站点
        """
        return "天枢" in self.site_name

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息并获取非标准格式的反馈
        """
        try:
            # 1. 调用父类方法发送消息
            # 这里的 result 是 (bool, str)
            result = ISiteHandler.send_messagebox(self, message, callback)
            if not result[0]:
                return result
                 
            # 2. 获取反馈
            # 获取当前用户名
            username = self.get_username()
            if not username:
                return result

            # 获取最新消息用于解析
            response = self._send_get_request(self.shoutbox_url)
            if not response:
                return result
                
            html = etree.HTML(response.text)
            feedbacks = []
            # 获取前15条，因为有时候刷得快
            rows = html.xpath("//tr[td[@class='shoutrow']][position() <= 15]")
            
            for row in rows:
                # 获取纯文本内容
                content = "".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
                
                # 匹配逻辑: 
                # 1. 包含用户名
                # 2. 包含系统反馈关键词 (神明, 奇迹, 赐予, 获得, 送出, 感动, 回应)
                # 3. 包含奖励类型 (魔力, 上传)
                
                if username in content:
                    keywords_system = ["神明", "奇迹", "赐予", "获得", "送出", "感动", "回应"]
                    keywords_reward = ["魔力", "上传"]
                    
                    is_system_msg = any(k in content for k in keywords_system)
                    has_reward = any(k in content for k in keywords_reward)
                    
                    if is_system_msg and has_reward:
                        feedbacks.append(content)
                        break
            
            if feedbacks:
                self._last_message_result = feedbacks[0]
                if callback:
                    callback(True, feedbacks[0])
                return True, feedbacks[0]
            
            # 没找到反馈，返回默认发送结果
            return result

        except Exception as e:
            logger.error(f"Dubhe 获取反馈消息失败: {str(e)}")
            return False, str(e)
