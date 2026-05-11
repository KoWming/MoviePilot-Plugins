from typing import Tuple, Optional, Dict
from lxml import etree
import time
import re

from app.log import logger
from .NexusPHP import NexusPHPHandler
from . import ISiteHandler


class PtlgsHandler(NexusPHPHandler):
    """
    PTLGS 站点处理类
    """

    def match(self) -> bool:
        """
        判断是否为 PTLGS 站点
        """
        return "PTLGS" in self.site_name.upper() or "ptlgs.org" in self.site_url.lower()

    def send_messagebox(self, message: str = None, callback=None) -> Tuple[bool, str]:
        """
        发送群聊区消息并获取黑丝娘反馈
        """
        try:
            result = ISiteHandler.send_messagebox(self, message, callback)
            if not result[0]:
                return result

            username = self.get_username()
            if not username:
                self._last_message_result = result[1]
                return result

            feedback = self._poll_feedback(username, message)
            if feedback:
                logger.info(f"站点 {self.site_name} 获取到反馈消息: {feedback}")
                result = (True, feedback)
            else:
                logger.info(f"站点 {self.site_name} 未获取到相关反馈消息，保留发送结果")

            self._last_message_result = result[1] if result[0] else None
            return result

        except Exception as e:
            logger.error(f"PTLGS 获取反馈消息失败: {str(e)}")
            return result

    def _poll_feedback(self, username: str, message: str = None) -> Optional[str]:
        """
        轮询 shoutbox，获取黑丝娘反馈
        """
        reward_keyword = self._get_reward_keyword(message)

        for attempt in range(5):
            if attempt > 0:
                time.sleep(3)

            response = self._send_get_request(self.shoutbox_url)
            if not response:
                continue

            html = etree.HTML(response.text)
            if html is None:
                continue

            rows = html.xpath("//td[contains(@class, 'shoutrow')][position() <= 20]")
            for row in rows:
                row_content = self._extract_row_text(row)
                feedback = self._match_feedback(row_content, username, reward_keyword)
                if feedback:
                    return feedback

        return None

    def _get_reward_keyword(self, message: str = None) -> Optional[str]:
        """
        根据喊话内容推断奖励关键词
        """
        if not message:
            return None

        if "上传" in message:
            return "上传"
        if "工分" in message:
            return "工分"
        return None

    def _extract_row_text(self, row) -> str:
        """
        提取并清理单条 shoutbox 文本
        """
        row_content = "".join(row.xpath(".//text()[not(ancestor::span[@class='date'])]")).strip()
        return re.sub(r"\s+", " ", row_content)

    def _match_feedback(self, row_content: str, username: str, reward_keyword: Optional[str] = None) -> Optional[str]:
        """
        匹配 PTLGS 的黑丝娘反馈
        """
        if not row_content.startswith("黑丝娘"):
            return None

        if f"@{username}" not in row_content:
            return None

        if reward_keyword and reward_keyword not in row_content and "明天再来吧" not in row_content:
            return None

        feedback_keywords = ["奖赏你", "你获得了", "你损失了", "明天再来吧"]
        if any(keyword in row_content for keyword in feedback_keywords):
            return row_content

        return None

    def get_feedback(self, message: str = None) -> Optional[Dict]:
        """
        获取消息反馈
        """
        result = super().get_feedback(message)
        if not result or not result.get("rewards") or not self._last_message_result:
            return result

        reward = result["rewards"][0]
        reward["is_negative"] = "损失" in self._last_message_result
        return result