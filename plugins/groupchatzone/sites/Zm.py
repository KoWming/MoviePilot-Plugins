from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
from lxml import etree
import time
import re

from app.log import logger
from app.utils.string import StringUtils
from app.db.site_oper import SiteOper
from . import ISiteHandler

class ZmHandler(ISiteHandler):
    """
    Zm站点处理类
    """
    
    def __init__(self, site_info: dict):
        super().__init__(site_info)
        self.shoutbox_url = urljoin(self.site_url, "/shoutbox.php")
        self.messages_url = urljoin(self.site_url, "/messages.php")
        self.siteoper = SiteOper()
        self._feedback_timeout = site_info.get("feedback_timeout", 5)  # 从配置中获取反馈超时时间，默认5秒
        self._last_message_result = None  # 初始化最后一次消息发送结果
        
    def match(self) -> bool:
        """
        判断是否为Zm站点
        :return: 是否匹配
        """
        return "织梦" in self.site_name.lower()

    def send_messagebox(self, messages: List[str] = None, callback=None, zm_stats: Dict = None) -> Tuple[bool, str]:
        """
        发送消息到喊话区并获取反馈
        :param messages: 消息内容列表
        :param callback: 回调函数
        :param zm_stats: 上传量历史记录
        :return: (是否成功, 结果信息)
        """
        try:
            if not messages:
                messages = []
            elif isinstance(messages, str):
                messages = [messages]
                
            result_list = []
            success_count = 0
            
            for message in messages:
                # 发送消息
                result = super().send_messagebox(message, lambda response: "")
                if not result[0]:
                    logger.error(f"发送消息失败: {message}")
                    continue
                    
                success_count += 1
                logger.info(f"消息发送成功: {message}")
                
                # 等待消息发送完成
                time.sleep(self._feedback_timeout)
                
                # 获取群聊区反馈
                feedback = self._get_messagebox_feedback(message)
                if feedback:
                    result_list.append(feedback)
                    logger.info(f"获取到反馈: {feedback}")
                else:
                    logger.warning(f"未获取到反馈: {message}")
                    
            # 保存结果
            self._last_message_result = "\n".join(result_list) if result_list else None
            
            # 只有当所有消息都发送成功时才返回True
            if success_count == len(messages):
                return True, self._last_message_result if self._last_message_result else "消息发送成功"
            else:
                return False, f"部分消息发送失败，成功: {success_count}/{len(messages)}"
            
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return False, str(e)
            
    def get_feedback(self, message: str = None) -> Optional[Dict]:
        """
        获取消息反馈
        :param message: 消息内容
        :return: 反馈信息字典
        """
        # 如果有最后一次消息发送结果,使用它
        if self._last_message_result:
            return {
                "site": self.site_name,
                "message": message,
                "rewards": [{
                    "type": "电力",
                    "description": self._last_message_result,
                    "amount": "",
                    "unit": "",
                    "is_negative": False
                }]
            }
            
        # 如果没有反馈结果，返回None，避免喊话失败重试逻辑失效
        return None
    
    def get_latest_message_time(self) -> Optional[str]:
        """
        获取最新电力赠送邮件的完整时间值,优先获取未读邮件,如果没有则获取已读邮件
        :return: 最新邮件的时间字符串，格式如"2025-04-20 20:55:49"，如果获取失败则返回None
        """
        try:
            logger.info(f"开始获取站点 {self.site_name} 的最新电力赠送邮件时间...")
            
            # 自定义回调函数，提取邮件时间的title属性
            def extract_message_time(response):
                try:
                    logger.debug(f"开始解析响应内容...")
                    
                    # 解析HTML
                    html = etree.HTML(response.text)
                    
                    # 查找所有邮件行
                    message_rows = html.xpath("//tr[td[@class='rowfollow']]")
                    logger.debug(f"找到 {len(message_rows)} 个邮件")
                    
                    # 遍历邮件行,查找符合条件的邮件
                    for row in message_rows:
                        # 检查是否为电力赠送邮件
                        content = row.xpath(".//a[contains(text(), '收到来自 zmpt 赠送的')]")
                        if not content:
                            continue
                            
                        # 提取时间值
                        time_span = row.xpath(".//span[@title]")
                        if time_span:
                            time_value = time_span[0].get("title")
                            if time_value:
                                # 检查是否为未读邮件
                                unread = row.xpath(".//img[@class='unreadpm']")
                                if unread:
                                    logger.debug(f"找到未读电力赠送邮件时间: {time_value}")
                                    return time_value
                                else:
                                    # 如果是已读邮件,保存时间值
                                    return time_value
                    
                    logger.debug("未找到符合条件的邮件")
                    return None
                    
                except Exception as e:
                    logger.error(f"提取邮件时间失败: {str(e)}")
                    return None
            
            # 调用基类方法获取邮件列表
            latest_time = super().get_message_list(rt_method=extract_message_time)
            
            if latest_time:
                return latest_time
                
            logger.warning("未获取到符合条件的邮件时间")
            return None
            
        except Exception as e:
            logger.error(f"获取最新电力赠送邮件时间失败: {str(e)}")
            return None

    def _get_messagebox_feedback(self, message: str) -> Optional[str]:
        """
        从群聊区获取反馈消息
        :param message: 发送的消息
        :return: 反馈消息或None
        """
        try:
            # 获取用户名
            username = self.get_username()
            if not username:
                logger.error("获取用户名失败")
                return None

            # 先刷新页面
            refresh_response = self._send_get_request(self.shoutbox_url)
            if not refresh_response:
                logger.error("刷新群聊区页面失败")
                return None

            # 等待页面刷新完成
            time.sleep(5)

            # 获取群聊区页面内容
            response = self._send_get_request(self.shoutbox_url)
            if not response:
                logger.error("获取群聊区页面失败")
                return None

            # 解析HTML
            html = etree.HTML(response.text)
            if not html:
                logger.error("解析群聊区HTML失败")
                return None

            # 获取所有消息行
            message_rows = html.xpath("//td[@class='shoutrow']")
            if not message_rows:
                logger.warning("未找到任何消息")
                return None

            # 确定消息类型
            message_type = None
            if "求上传" in message:
                message_type = ("上传量", "没有理你")
                logger.debug(f"识别到上传量请求消息,将匹配'上传量'或'没有理你'")
            elif "求电力" in message:
                message_type = ("电力", "没有理你")
                logger.debug(f"识别到电力请求消息,将匹配'电力'或'没有理你'")

            if not message_type:
                logger.debug("未识别到有效的消息类型")
                return None

            # 存储匹配的消息及其时间
            matched_messages = []

            # 遍历消息行查找反馈
            for row in message_rows:
                try:
                    # 提取时间前缀
                    time_span = row.xpath(".//span[@class='date']/text()")
                    if not time_span:
                        continue
                    time_prefix = time_span[0].strip()
                    
                    # 提取消息内容
                    content = row.xpath("string(.)").strip()
                    if not content:
                        continue

                    # 检查是否包含@用户名
                    if f"@{username}：" not in content:
                        continue

                    # 检查是否包含皮总
                    if "皮总" not in content:
                        continue

                    # 检查消息类型是否匹配
                    if not (message_type[0] in content or message_type[1] in content):
                        logger.debug(f"消息类型不匹配: 期望匹配'{message_type[0]}'或'{message_type[1]}', 实际内容={content}")
                        continue

                    # 提取反馈内容
                    feedback = content.split(f"@{username}：")[-1].strip()
                    
                    # 验证反馈消息格式
                    if any(keyword in feedback for keyword in ["赠送", "扣减", "没有理你"]):
                        # 根据时间前缀确定优先级
                        priority = 0
                        
                        # 处理时间前缀
                        if "< 1分钟前" in time_prefix:
                            # 小于1分钟的情况，给予最高优先级
                            priority = 100
                        else:
                            # 提取数字部分
                            time_match = re.search(r'\[(\d+)分钟前\]', time_prefix)
                            if time_match:
                                minutes = int(time_match.group(1))
                                # 数字越小优先级越高，使用100减去分钟数
                                priority = 100 - minutes
                        
                        if priority > 0:
                            matched_messages.append((priority, feedback, time_prefix))
                            logger.debug(f"找到匹配消息: 时间={time_prefix}, 优先级={priority}, 内容={feedback}")

                except Exception as e:
                    logger.error(f"解析消息行失败: {str(e)}")
                    continue

            if not matched_messages:
                logger.debug("未找到符合条件的反馈消息")
                return None

            # 按优先级排序，取最新的消息
            matched_messages.sort(key=lambda x: x[0], reverse=True)
            latest_feedback = matched_messages[0][1]
            latest_time = matched_messages[0][2]
            
            logger.debug(f"找到最新反馈消息: {latest_time} - {latest_feedback}")
            return latest_feedback

        except Exception as e:
            logger.error(f"获取群聊区反馈失败: {str(e)}")
            return None

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