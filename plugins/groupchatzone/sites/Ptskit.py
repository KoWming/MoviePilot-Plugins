from typing import Tuple
from app.log import logger
from lxml import etree
from .NexusPHP import NexusPHPHandler

class PtskitHandler(NexusPHPHandler):
    """
    Ptskit (PTS) 站点处理器
    """

    def match(self) -> bool:
        """
        判断是否为PTS站点
        """
        return "PTS" in self.site_name

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送消息并获取反馈
        """
        try:
            # 构造请求参数
            params = {
                'shbox_text': message,
                'shout': '我喊',
                'sent': 'yes',
                'type': 'shoutbox'
            }
            
            # 发送 GET 请求
            response = self._send_get_request(self.shoutbox_url, params=params)
            
            if not response:
                return False, "请求失败"
                
            content = response.text
            username = self.get_username()
            
            # 解析 HTML
            try:
                html = etree.HTML(content)
                if html is None:
                    return False, "页面解析失败"
                    
                # 提取所有消息行
                rows = html.xpath("//table//tr/td[contains(@class, 'shoutrow')]")
                
                for row in rows:
                    row_text = "".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
                    
                    # 1. 检查是否包含系统奖励信息 (针对当前用户)
                    if username and f"用户「{username}」" in row_text:
                        if "获得" in row_text and "魔力值" in row_text:
                            feedback = row_text.replace("[系统]", "").strip()
                            self._last_message_result = feedback
                            if callback:
                                callback(True, feedback)
                            return True, feedback

                        if "今日已领取过" in row_text:
                            feedback = row_text.replace("[系统]", "").strip()
                            self._last_message_result = feedback
                            if callback:
                                callback(True, feedback)
                            return True, feedback

                    # 2. 检查是否包含自己发送的消息
                    if username and username in row_text and message and message in row_text:
                        return True, "消息已发送"

                if 'name="shbox_text"' in content or 'id="shbox_text"' in content:
                     return True, "消息已发送 (未检测到特定反馈)"
                     
            except Exception as e:
                logger.error(f"Ptskit 解析HTML失败: {str(e)}")
                return True, "消息已发送 (解析反馈失败)"

            return True, "消息已发送 (未获得反馈)"

        except Exception as e:
            logger.error(f"Ptskit 发送消息失败: {str(e)}")
            return False, str(e)
