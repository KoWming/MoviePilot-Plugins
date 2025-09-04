from typing import Dict, Optional, Tuple
import json

from app.log import logger
from app.utils.string import StringUtils
from app.db.site_oper import SiteOper
from . import ISiteHandler

class LongPTHandler(ISiteHandler):
    """
    LongPT站点处理类
    """
    
    def __init__(self, site_info: dict):
        super().__init__(site_info)
        # LongPT使用API接口
        self.api_url = "https://longpt.org/pt-api/v1/nexus/shoutbox/shout"
        self.siteoper = SiteOper()
        self._last_message_result = None  # 保存最后一次消息发送结果
        
    def match(self) -> bool:
        """
        判断是否为LongPT站点
        """
        site_name = self.site_name.lower()
        return "longpt" in site_name
        
    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息
        :param message: 消息内容
        :param callback: 回调函数
        :return: 发送结果
        """
        try:
            if not message:
                return False, "消息内容不能为空"
            
            # 构建请求数据
            data = {
                "text": message
            }
            
            # 设置请求头
            headers = {
                "Content-Type": "application/json",
                "User-Agent": self.ua,
                "Cookie": self.site_cookie,
                "Referer": self.site_url
            }
            
            # 发送POST请求
            response = self.session.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("code") == 0:
                        # 发送成功
                        msg_text = result.get("msg", "")
                        logger.info(f"LongPT站点消息发送成功: {msg_text}")
                        self._last_message_result = msg_text
                        return True, msg_text
                    else:
                        # API返回错误
                        error_msg = result.get("msg", "发送失败")
                        logger.warning(f"LongPT站点消息发送失败: {error_msg}")
                        return False, error_msg
                except json.JSONDecodeError:
                    logger.error("LongPT站点响应不是有效的JSON格式")
                    return False, "响应格式错误"
            else:
                error_msg = f"请求失败，状态码: {response.status_code}"
                logger.error(f"LongPT站点消息发送失败: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"发送消息时发生异常: {str(e)}"
            logger.error(f"LongPT站点消息发送异常: {error_msg}")
            return False, error_msg
            
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
            if any(keyword in feedback_text for keyword in ["魔力"]):
                reward_type = "魔力值"
            elif any(keyword in feedback_text for keyword in ["上传"]):
                reward_type = "上传量"
            elif any(keyword in feedback_text for keyword in ["下载"]):
                reward_type = "下载量"
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

    def daily_lottery(self) -> Tuple[bool, str]:
        """
        参加每日抽奖
        :return: (是否成功, 消息)
        """
        try:
            # 抽奖API地址
            lottery_url = "https://longpt.org/pt-api/v1/lucky/pluginsPrizeReceiptRecord/join"
            
            # 设置请求头
            headers = {
                "User-Agent": self.ua,
                "Cookie": self.site_cookie,
                "Referer": self.site_url
            }
            
            # 发送GET请求
            response = self.session.get(
                lottery_url,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    code = result.get("code")
                    msg = result.get("msg", "")
                    
                    if code == 0:
                        # 抽奖成功
                        logger.info(f"LongPT每日抽奖成功: {msg}")
                        return True, msg
                    elif code == -1:
                        # 已经参与过抽奖
                        logger.info(f"LongPT每日抽奖: {msg}")
                        return True, msg
                    else:
                        # 其他错误
                        logger.warning(f"LongPT每日抽奖失败: {msg}")
                        return False, msg
                        
                except json.JSONDecodeError:
                    logger.error("LongPT抽奖响应不是有效的JSON格式")
                    return False, "响应格式错误"
            else:
                error_msg = f"请求失败，状态码: {response.status_code}"
                logger.error(f"LongPT每日抽奖失败: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"参加抽奖时发生异常: {str(e)}"
            logger.error(f"LongPT每日抽奖异常: {error_msg}")
            return False, error_msg
