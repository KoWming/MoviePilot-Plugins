from typing import Tuple
from app.log import logger
import re
from .NexusPHP import NexusPHPHandler

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
        try:
            # 构造请求参数
            params = {
                'shbox_text': message,
                'sent': 'yes',
                'type': 'shoutbox'
            }
            
            # 发送 GET 请求
            response = self._send_get_request(self.shoutbox_url, params=params)
            
            if not response:
                return False, "请求失败"
                
            content = response.text
            
            # 解析 alert 弹窗内容
            match = re.search(r"alert\s*\(\s*(['\"])(.*?)\1\s*\)", content, re.DOTALL | re.IGNORECASE)
            
            if match:
                feedback = match.group(2)
                feedback = feedback.replace("\\'", "'").replace('\\"', '"').replace("\\n", "\n")
                
                if callback:
                    callback(True, feedback)
                return True, feedback
            
            return True, "消息已发送 (无弹窗反馈)"

        except Exception as e:
            logger.error(f"Ptskit 发送消息失败: {str(e)}")
            return False, str(e)
