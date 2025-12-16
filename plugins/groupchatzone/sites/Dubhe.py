from typing import Tuple
from lxml import etree
from app.log import logger
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler

class DubheHandler(NexusPHPHandler):
    """
    天枢 (Dubhe) 站点处理器
    反馈消息通常由系统(admin)发出，包含 "神明"、"奇迹" 等关键词，且包含用户名
    """

    def match(self) -> bool:
        """
        判断是否为天枢站点
        """
        return "天枢" in self.site_name

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息并获取非标准格式的反馈
        :param message: 消息内容
        :param callback: 回调函数
        :return: (是否成功, 反馈消息内容)
        """
        try:
            # 1. 调用父类方法发送消息
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
            
            # 获取前15条消息，因为群聊滚动可能较快
            rows = html.xpath("//tr[td[@class='shoutrow']][position() <= 15]")
            
            # 定义匹配关键词
            keywords_system = ["神明", "奇迹", "赐予", "获得", "送出", "感动", "回应"]
            keywords_reward = ["魔力", "上传"]

            for row in rows:
                # 获取纯文本内容，排除日期标签
                # 注意：Dubhe 的 admin 用户名和其他头衔可能包含在文本中，所以这里提取整行文本
                content = "".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
                
                # 匹配逻辑: 
                # 1. 内容中必须包含当前用户名 (admin 发出的消息会提到用户名)
                # 2. 包含系统反馈关键词
                # 3. 包含奖励类型关键词
                
                if username in content:
                    is_system_msg = any(k in content for k in keywords_system)
                    has_reward = any(k in content for k in keywords_reward)
                    
                    if is_system_msg and has_reward:
                        feedbacks.append(content)
                        break
            
            if feedbacks:
                feedback_msg = feedbacks[0]
                self._last_message_result = feedback_msg
                # 更新 result
                result = (True, feedback_msg)
                
                if callback:
                    callback(True, feedback_msg)
                return result
            
            # 没找到反馈，返回默认发送结果 (True, "")
            return result

        except Exception as e:
            logger.error(f"Dubhe 获取反馈消息失败: {str(e)}")
            return False, str(e)
