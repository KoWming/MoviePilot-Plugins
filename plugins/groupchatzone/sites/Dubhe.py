from typing import Tuple, Dict, Optional
from lxml import etree
from app.log import logger
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler

class DubheHandler(NexusPHPHandler):
    """
    天枢 (Dubhe) 站点处理类
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
            return ISiteHandler.send_messagebox(self, message, callback)

        except Exception as e:
            logger.error(f"Dubhe 发送消息失败: {str(e)}")
            return False, str(e)

    def get_feedback(self, message: str = None) -> Optional[Dict]:
        """
        获取消息反馈
        :param message: 消息内容
        :return: 反馈信息字典
        """
        try:
            # 获取当前用户名
            username = self.get_username()
            if not username:
                return super().get_feedback(message)

            # 清空之前的反馈结果，防止在该次未找到匹配反馈时使用了上一次的结果
            self._last_message_result = None

            # 获取最新消息用于解析
            response = self._send_get_request(self.shoutbox_url)
            if not response:
                return super().get_feedback(message)
                
            html = etree.HTML(response.text)
            
            # 获取前10条消息
            rows = html.xpath("//tr[td[@class='shoutrow']][position() <= 10]")
            
            for row in rows:
                # 获取发送者信息 (位于 span.nowrap 中)
                sender_node = row.xpath(".//span[@class='nowrap']")
                sender_text = "".join(sender_node[0].xpath(".//text()")) if sender_node else ""
                
                # 获取纯文本内容，排除日期标签和发送者信息(admin及图标)
                content = "".join(row.xpath(".//text()[not(ancestor::span[@class='date']) and not(ancestor::span[@class='nowrap'])]")).strip()
                
                # 匹配逻辑:
                if username not in sender_text and username in content:
                    # 验证回复内容与请求类型是否匹配
                    if message:
                        if "求魔力" in message and "魔力值" not in content:
                            continue
                        elif "求上传" in message and "上传量" not in content:
                            continue

                    self._last_message_result = content
                    break
            
            return super().get_feedback(message)

        except Exception as e:
            logger.error(f"Dubhe get_feedback 获取反馈失败: {str(e)}")
            return super().get_feedback(message)
