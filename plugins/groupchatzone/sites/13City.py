from typing import Tuple, Optional
from urllib.parse import urljoin
import json
from lxml import etree

from app.log import logger
from .NexusPHP import NexusPHPHandler

class ThirteenCityHandler(NexusPHPHandler):
    """
    13City站点处理类
    """

    BLESSING_MEDAL_NAME = "诸神赐福"
    BLESSING_MEDAL_ID = "11"
    BLESSING_BOT_NAME = "掌管啤酒瓶的神"

    def __init__(self, site_info: dict):
        super().__init__(site_info)
        self.index_url = urljoin(self.site_url, "/index.php")
        self.shoutbox_url = urljoin(self.site_url, "/shoutbox.php?type=shoutbox")
        self._blessing_status = {
            "auto_buy_enabled": bool(site_info.get("thirteencity_auto_buy_blessing", False)),
            "medal_status": "未检查",
            "purchase_status": "未触发"
        }
    
    def match(self) -> bool:
        """
        判断是否为13City站点
        """
        return "13City" in self.site_name

    def get_feedback(self, message: str = None) -> Optional[dict]:
        """
        获取消息反馈
        :param message: 消息内容
        :return: 反馈信息字典
        """
        try:
            if not self._last_message_result:
                return {
                    "site": self.site_name,
                    "message": message,
                    "blessing_status": self._blessing_status,
                    "rewards": [{
                        "type": "raw_feedback",
                        "description": "消息已发送",
                        "amount": "",
                        "unit": "",
                        "is_negative": False
                    }]
                }

            # 调用父类方法处理反馈结果
            result = super().get_feedback(message)
            if result is not None:
                result["blessing_status"] = self._blessing_status
            
            # 补充处理 "啤酒瓶" 奖励类型
            if result and "rewards" in result and self._last_message_result:
                if "啤酒瓶" in self._last_message_result:
                    result["rewards"][0]["type"] = "啤酒瓶"
            
            return result
        except Exception as e:
            logger.error(f"解析反馈消息失败: {str(e)}")
            return None

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息
        :param message: 消息内容
        :param callback: 回调函数
        :return: 发送结果
        """
        try:
            blessing_check = self._ensure_blessing_medal()
            if not blessing_check[0]:
                self._last_message_result = blessing_check[1]
                return blessing_check

            # 获取当前用户名
            username = self.get_username()
            if not username:
                return False, "获取13City用户名失败"

            result = self._send_shout_message(message)
            if not result[0]:
                self._last_message_result = result[1]
                return result

            if not self._message_exists_in_shoutbox(username, message):
                logger.warning(f"13City喊话请求已返回成功，但群聊区未发现用户消息: {username} {message}")
                return False, "13City群聊区未显示发送的喊话消息"

            # 获取最新消息
            response = self._send_get_request(self.shoutbox_url)
            if not response:
                return result
                
            # 解析HTML
            html = etree.HTML(response.text)
            
            # 13City 实际反馈与用户消息都在 shoutrow 行内
            # 提取前20条消息，查找掌管啤酒瓶的神对当前用户的回复
            feedbacks = []
            
            rows = html.xpath("//tr[td[contains(@class, 'shoutrow')]][position() <= 20]")
            
            for row in rows:
                content = self._extract_row_text(row)

                if self._is_feedback_message(content, username):
                    feedbacks.append(content)
                    
            # 如果有反馈消息,更新结果
            if feedbacks:
                result = (result[0], feedbacks[0])
            else:
                result = (result[0], "消息已发送")
                
            # 保存结果
            self._last_message_result = result[1] if result[0] else None
            return result
            
        except Exception as e:
            logger.error(f"获取反馈消息失败: {str(e)}")
            return result

    def _send_shout_message(self, message: str) -> Tuple[bool, str]:
        """
        按13City首页表单行为发送喊话
        """
        try:
            response = self.session.get(
                urljoin(self.site_url, "/shoutbox.php"),
                params={
                    "shbox_text": message,
                    "shout": "我喊",
                    "sent": "yes",
                    "type": "shoutbox"
                },
                headers={
                    "Referer": self.index_url
                },
                timeout=(3.05, 10)
            )
            response.raise_for_status()
            return True, response.text
        except Exception as e:
            logger.error(f"13City发送喊话失败: {str(e)}")
            return False, "发送13City喊话失败"

    def _message_exists_in_shoutbox(self, username: str, message: str) -> bool:
        """
        校验群聊区中是否已出现用户刚发送的喊话
        """
        response = self._send_get_request(self.shoutbox_url)
        if not response:
            return False

        html = etree.HTML(response.text)
        if html is None:
            return False

        rows = html.xpath("//tr[td[contains(@class, 'shoutrow')]][position() <= 20]")
        expected_text = f"{username} {message}"

        for row in rows:
            content = self._extract_row_text(row)
            normalized = " ".join(content.split())
            if expected_text in normalized:
                return True

        return False

    def _extract_row_text(self, row) -> str:
        """
        提取单条群聊记录文本，排除时间戳
        """
        return "".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()

    def _is_feedback_message(self, content: str, username: str) -> bool:
        """
        判断是否为13City祈福系统反馈
        """
        if not content or f"@{username}" not in content:
            return False

        return self.BLESSING_BOT_NAME in content and any(keyword in content for keyword in ["听到了你的愿望", "你今天求过啤酒瓶了", "啤酒瓶"])

    def _ensure_blessing_medal(self) -> Tuple[bool, str]:
        """
        确保用户拥有诸神赐福勋章
        """
        auto_buy_enabled = self.site_info.get("thirteencity_auto_buy_blessing", False)
        self._blessing_status = {
            "auto_buy_enabled": bool(auto_buy_enabled),
            "medal_status": "检查中",
            "purchase_status": "未触发"
        }
        medal_page = self._fetch_medal_page()
        if medal_page is None:
            if not auto_buy_enabled:
                self._blessing_status["medal_status"] = "无法确认"
                self._blessing_status["purchase_status"] = "未开启自动购买"
                logger.warning("13City未开启诸神赐福勋章自动购买，且无法确认勋章状态，继续执行喊话，可能会扣除啤酒瓶")
                return True, "未校验勋章状态，继续执行喊话"
            self._blessing_status["medal_status"] = "检查失败"
            self._blessing_status["purchase_status"] = "检查失败"
            return False, "获取13City勋章页面失败"

        if self._has_blessing_medal(medal_page):
            self._blessing_status["medal_status"] = "已拥有诸神赐福"
            self._blessing_status["purchase_status"] = "无需购买"
            return True, f"已拥有{self.BLESSING_MEDAL_NAME}勋章"

        if not auto_buy_enabled:
            self._blessing_status["medal_status"] = "未拥有诸神赐福"
            self._blessing_status["purchase_status"] = "未开启自动购买"
            logger.warning(f"13City未开启{self.BLESSING_MEDAL_NAME}勋章自动购买，继续执行喊话，可能会扣除啤酒瓶")
            return True, f"未拥有{self.BLESSING_MEDAL_NAME}勋章，继续执行喊话"

        self._blessing_status["medal_status"] = "未拥有诸神赐福"
        self._blessing_status["purchase_status"] = "尝试自动购买"
        buy_result = self._buy_blessing_medal(medal_page)
        if not buy_result[0]:
            self._blessing_status["purchase_status"] = f"购买失败: {buy_result[1]}"
            return buy_result

        medal_page = self._fetch_medal_page()
        if medal_page is None:
            self._blessing_status["purchase_status"] = "已购买，复检失败"
            return False, f"购买{self.BLESSING_MEDAL_NAME}后校验失败"

        if not self._has_blessing_medal(medal_page):
            self._blessing_status["purchase_status"] = "已购买，未检测到勋章"
            return False, f"购买{self.BLESSING_MEDAL_NAME}后未检测到勋章"

        self._blessing_status["medal_status"] = "已拥有诸神赐福"
        self._blessing_status["purchase_status"] = "自动购买成功"
        return True, buy_result[1]

    def _fetch_medal_page(self) -> Optional[str]:
        """
        获取勋章页源码
        """
        medal_url = urljoin(self.site_url, "/medal.php?q=&sort=category")
        response = self._send_get_request(medal_url)
        if not response:
            return None
        return response.text

    def _has_blessing_medal(self, page_text: str) -> bool:
        """
        判断是否已拥有诸神赐福勋章
        """
        html = etree.HTML(page_text)
        if html is None:
            return False

        cards = self._find_blessing_medal_cards(html)
        for card in cards:
            class_name = card.xpath("string(@class)")
            if "purchased" in class_name.split():
                return True

            buy_text = "".join(card.xpath(".//div[contains(@class, 'medal-action')]//button[contains(@class, 'buy')]//text()")).strip()
            if buy_text in ["已经购买", "已购买"]:
                return True

        return False

    def _buy_blessing_medal(self, page_text: str) -> Tuple[bool, str]:
        """
        购买诸神赐福勋章
        """
        if not self._can_buy_blessing_medal(page_text):
            return False, f"{self.BLESSING_MEDAL_NAME}当前不可购买"

        response = self._send_post_request(
            self.url_ajax,
            data={
                "action": "buyMedal",
                "params[medal_id]": self.BLESSING_MEDAL_ID
            }
        )
        if not response:
            return False, f"购买{self.BLESSING_MEDAL_NAME}失败"

        payload = self._parse_ajax_response(response.text)
        if payload is None:
            return False, f"购买{self.BLESSING_MEDAL_NAME}响应解析失败"

        if payload.get("ret") != 0:
            return False, payload.get("msg") or f"购买{self.BLESSING_MEDAL_NAME}失败"

        return True, payload.get("msg") or f"已自动购买{self.BLESSING_MEDAL_NAME}勋章"

    def _can_buy_blessing_medal(self, page_text: str) -> bool:
        """
        判断诸神赐福勋章当前是否可购买
        """
        html = etree.HTML(page_text)
        if html is None:
            return False

        cards = self._find_blessing_medal_cards(html)
        buttons = []
        for card in cards:
            buttons.extend(card.xpath(f".//button[contains(@class, 'buy') and @data-id='{self.BLESSING_MEDAL_ID}']"))

        if not buttons:
            return False

        button = buttons[0]
        if button.xpath("@disabled"):
            return False

        return "购买" in "".join(button.xpath(".//text()")).strip()

    def _find_blessing_medal_cards(self, html) -> list:
        """
        精确定位诸神赐福勋章卡片，优先按 medal_id，其次按名称兜底
        """
        cards = html.xpath(
            f"//div[contains(@class, 'medal-card')][.//button[contains(@class, 'buy') and @data-id='{self.BLESSING_MEDAL_ID}']]"
        )
        if cards:
            exact_cards = []
            for card in cards:
                medal_name = "".join(card.xpath(".//div[contains(@class, 'medal-name')]//text()")).strip()
                if medal_name == self.BLESSING_MEDAL_NAME:
                    exact_cards.append(card)
            if exact_cards:
                return exact_cards
            return cards

        return html.xpath(
            f"//div[contains(@class, 'medal-card')][.//div[contains(@class, 'medal-name') and normalize-space(text())='{self.BLESSING_MEDAL_NAME}']]"
        )

    def _parse_ajax_response(self, response_text: str) -> Optional[dict]:
        """
        解析13City ajax返回
        """
        try:
            return json.loads(response_text)
        except Exception:
            logger.error(f"13City Ajax响应解析失败: {response_text}")
            return None
