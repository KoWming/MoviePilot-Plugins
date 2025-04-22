from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

from lxml import etree

from app.log import logger
from app.utils.string import StringUtils
from app.db.site_oper import SiteOper
from . import ISiteHandler

class QingwaHandler(ISiteHandler):
    """
    青蛙站点处理类
    """
    
    def __init__(self, site_info: dict):
        super().__init__(site_info)
        self.shoutbox_url = urljoin(self.site_url, "/shoutbox.php")
        self.siteoper = SiteOper()
        
    def match(self) -> bool:
        """
        判断是否为青蛙站点
        """
        site_name = self.site_name.lower()
        return "青蛙" in site_name
        
    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息
        :param message: 消息内容
        :param callback: 回调函数
        :return: 发送结果
        """
        # 调用父类方法
        result = super().send_messagebox(message, 
                                       lambda response: " ".join(etree.HTML(response.text).xpath("//ul[1]/li/text()")))

        # 保存结果
        self._last_message_result = result[1] if result[0] else None
        return result
            
    def get_feedback(self, message: str = None) -> Optional[Dict]:
        """
        获取消息反馈
        :param message: 消息内容
        :return: 反馈信息字典
        """
        # 如果有最后一次消息发送结果,使用它
        if self._last_message_result:
            # 判断消息是否为"发了！"
            feedback_text = self._last_message_result
            if feedback_text == "发了！":
                feedback_text = f"{feedback_text}一般为10G！"
                
            return {
                "site": self.site_name,
                "message": message,
                "rewards": [{
                    "type": "青蛙",
                    "description": feedback_text,
                    "amount": "",
                    "unit": "",
                    "is_negative": False
                }]
            }
            
        # 如果都没有,返回默认反馈
        return {
            "site": self.site_name,
            "message": message,
            "rewards": [{
                "type": "青蛙",
                "description": "消息已发送",
                "amount": "",
                "unit": "",
                "is_negative": False
            }]
        }
        
    def get_username(self) -> Optional[str]:
        """
        获取用户名
        :return: 用户名或None
        """
        site_name = self.site_name
        site_domain = StringUtils.get_url_domain(self.site_url)
        
        try:
            user_data_list = self.siteoper.get_userdata_latest()
            for user_data in user_data_list:
                if user_data.domain == site_domain:
                    logger.info(f"站点: {user_data.name}, 用户名: {user_data.username}")
                    return user_data.username
            
            logger.warning(f"未找到站点 {site_name} 的用户信息")
            return None
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的用户信息失败: {str(e)}")
            return None