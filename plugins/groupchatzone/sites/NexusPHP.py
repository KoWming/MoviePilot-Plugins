from typing import Dict, Optional, Tuple
from urllib.parse import urljoin
from lxml import etree
import re

from app.log import logger
from app.utils.string import StringUtils
from app.db.site_oper import SiteOper
from . import ISiteHandler

class NexusPHPHandler(ISiteHandler):
    """
    通用NexusPHP站点处理类
    """
    
    def __init__(self, site_info: dict):
        super().__init__(site_info)
        self.shoutbox_url = urljoin(self.site_url, "/shoutbox.php")
        self.messages_url = urljoin(self.site_url, "/messages.php")
        self.siteoper = SiteOper()
        self._last_message_result = None  # 保存最后一次消息发送结果
        
    def match(self) -> bool:
        """
        判断是否为通用NexusPHP站点
        """
        # 如果站点名包含"织梦",则不是通用NexusPHP站点
        if "织梦" in self.site_name.lower():
            return False
        # 如果站点名包含"象站",则不是通用NexusPHP站点
        if "象站" in self.site_name.lower():
            return False
        # 如果站点名包含"青蛙",则不是通用NexusPHP站点
        if "青蛙" in self.site_name.lower():
            return False
        # 如果站点名包含"LongPT",则不是通用NexusPHP站点
        if "LongPT" in self.site_name.lower():
            return False
        
        # 如果其他特定站点处理器都不匹配，则使用此通用处理器
        return True
        
    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息
        :param message: 消息内容
        :param callback: 回调函数
        :return: 发送结果
        """
        try:
            # 调用父类方法
            result = super().send_messagebox(message, callback)

            # 获取当前用户名
            username = self.get_username()
            if not username:
                return result
                
            # 获取最新10条消息
            response = self._send_get_request(self.shoutbox_url)
            if not response:
                return result
                
            # 解析HTML
            html = etree.HTML(response.text)
            
            # 提取前10条消息中的反馈
            feedbacks = []
            rows = html.xpath("//tr[td[@class='shoutrow']][position() <= 10]")
            
            for row in rows:
                # 提取消息内容
                content = "".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
                
                # 检查是否是反馈消息且@当前用户
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
            
    def get_feedback(self, message: str = None) -> Optional[Dict]:
        """
        获取消息反馈
        :param message: 消息内容
        :return: 反馈信息字典
        """
        # 如果有最后一次消息发送结果,使用它
        if self._last_message_result:
            # 分析反馈消息内容,确定奖励类型
            feedback_text = self._last_message_result.lower()
            reward_type = "raw_feedback"  # 默认类型
            
            # 根据关键词匹配奖励类型
            if any(keyword in feedback_text for keyword in ["上传"]):
                reward_type = "上传量"
            elif any(keyword in feedback_text for keyword in ["下载"]):
                reward_type = "下载量"
            elif any(keyword in feedback_text for keyword in ["魔力"]):
                reward_type = "魔力值"
            elif any(keyword in feedback_text for keyword in ["工分"]):
                reward_type = "工分"
            elif any(keyword in feedback_text for keyword in ["vip"]):
                reward_type = "VIP"
            elif any(keyword in feedback_text for keyword in ["彩虹id"]):
                reward_type = "彩虹ID"
                
            return {
                "site": self.site_name,
                "message": message,
                "rewards": [{
                    "type": reward_type,
                    "description": self._last_message_result,
                    "amount": "",
                    "unit": "",
                    "is_negative": False
                }]
            }
            
        # 如果没有消息发送结果,返回默认反馈
        return {
            "site": self.site_name,
            "message": message,
            "rewards": [{
                "type": "raw_feedback",
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

    def get_userid(self) -> Optional[str]:
        """
        获取用户ID
        :return: 用户ID或None
        """
        site_name = self.site_name
        site_domain = StringUtils.get_url_domain(self.site_url)
        
        try:
            user_data_list = self.siteoper.get_userdata_latest()
            for user_data in user_data_list:
                if user_data.domain == site_domain:
                    logger.info(f"站点: {user_data.name}, 用户ID: {user_data.userid}")
                    return user_data.userid
            
            logger.warning(f"未找到站点 {site_name} 的用户信息")
            return None
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的用户信息失败: {str(e)}")
            return None

    def get_user_privileges(self) -> Dict[str, str]:
        """
        获取用户特权信息
        :return: 包含VIP、等级名称和彩虹ID信息的字典
        """
        try:
            # 获取用户ID
            userid = self.get_userid()
            if not userid:
                return {}
                
            # 获取用户详情页面
            user_details_url = urljoin(self.site_url, f"/userdetails.php?id={userid}")
            response = self._send_get_request(user_details_url)
            if not response:
                return {}
            
            # 解析HTML
            html = etree.HTML(response.text)
            
            # 提取等级信息
            vip_info = html.xpath('//tr[td[contains(text(), "等级")]]/td[2]')
            vip_end_time = ""
            level_name = ""

            if vip_info:
                # 首先提取等级名称
                level_img = vip_info[0].xpath('.//img/@title')
                if level_img:
                    level_name = level_img[0]
                    
                    # 如果等级是贵宾,则提取贵宾资格结束时间
                    if level_name == "贵宾":
                        vip_text = vip_info[0].xpath('.//text()')
                        if vip_text:
                            vip_text = "".join(vip_text)
                            vip_match = re.search(r'贵宾资格结束时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', vip_text)
                            if vip_match:
                                vip_end_time = vip_match.group(1)
            
            # 提取彩虹ID信息
            rainbow_info = html.xpath('//tr[td[contains(text(), "道具")]]/td[2]//div/text()')
            rainbow_end_time = ""
            if rainbow_info:
                rainbow_text = rainbow_info[0]
                rainbow_match = re.search(r'截止时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', rainbow_text)
                if rainbow_match:
                    rainbow_end_time = rainbow_match.group(1)
                
            return {
                "vip_end_time": vip_end_time,
                "level_name": level_name,
                "rainbow_end_time": rainbow_end_time
            }
            
        except Exception as e:
            logger.error(f"获取用户特权信息失败: {str(e)}")
            return {}