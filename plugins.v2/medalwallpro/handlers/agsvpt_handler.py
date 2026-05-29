import json
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

from lxml import etree

from app.core.config import settings
from app.log import logger
from app.utils.http import RequestUtils

from .base import BaseMedalSiteHandler


class AgsvptMedalHandler(BaseMedalSiteHandler):
    """AGSVPT 站点勋章处理器"""

    def match(self, site) -> bool:
        """判断是否为 AGSVPT 站点"""
        site_name = (site.name or "").lower()
        site_url = (site.url or "").lower()
        return "agsv" in site_name or "agsvpt.com" in site_url or "pt.agsvpt.cn" in site_url

    def fetch_medals(self, site) -> List[Dict]:
        """获取 AGSVPT 站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            site_ua = getattr(site, "ua", None)

            url = f"{site_url.rstrip('/')}/medal.php"
            logger.info(f"正在获取【{site_name}】站点勋章数据")

            res = self._request_with_retry(url=url, cookies=site_cookie, ua=site_ua)
            if not res:
                logger.error(f"请求 AGSVPT 勋章页面失败！站点：{site_name}")
                return []

            html = etree.HTML(res.text)
            containers = html.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-type-container ')]")
            if not containers:
                logger.error("未找到 AGSVPT 勋章分组容器！")
                return []

            medals: List[Dict] = []
            for container in containers:
                group_name = (container.get("data-type") or "").strip() or self._extract_group_name(container)
                medal_cards = container.xpath(".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-item ')]")
                logger.info(f"AGSVPT 分组 {group_name or '默认分组'} 找到 {len(medal_cards)} 个勋章")

                for card in medal_cards:
                    try:
                        medal = self._process_medal_card(card, site_name, site_url, group_name)
                        if medal:
                            medals.append(medal)
                    except Exception as e:
                        logger.error(f"处理 AGSVPT 勋章卡片时发生错误：{e}")

            logger.info(f"共获取到 {len(medals)} 个 AGSVPT 勋章数据")
            return medals
        except Exception as e:
            logger.error(f"处理 AGSVPT 站点勋章数据时发生错误: {e}")
            return []

    def fetch_user_medals(self, site) -> List[Dict]:
        """获取 AGSVPT 用户已拥有勋章"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            site_ua = getattr(site, "ua", None)

            user_id = self._get_user_id(site_url, site_cookie, site_ua)
            if not user_id:
                logger.error(f"无法获取站点 {site_name} 的用户ID")
                return []

            detail_url = f"{site_url.rstrip('/')}/userdetails.php?id={user_id}"
            logger.info("正在获取 AGSVPT 用户详情页")

            res = self._request_with_retry(url=detail_url, cookies=site_cookie, ua=site_ua)
            if not res:
                logger.error(f"请求 AGSVPT 用户详情页失败！站点：{site_name}")
                return []

            html = etree.HTML(res.text)
            medals = self._parse_user_medals(html, site_name, site_url)
            logger.info(f"共获取到 {len(medals)} 个 AGSVPT 用户已拥有勋章")
            return medals
        except Exception as e:
            logger.error(f"获取 AGSVPT 用户已拥有勋章失败: {e}")
            return []

    def purchase_medal(self, site, medal: Dict) -> Dict:
        """购买 AGSVPT 勋章"""
        site_name = getattr(site, "name", "")
        site_url = (getattr(site, "url", "") or "").rstrip("/")
        site_cookie = getattr(site, "cookie", None)
        site_ua = getattr(site, "ua", None)
        medal_id = medal.get("medal_id") or medal.get("id")
        medal_name = medal.get("name") or "未知勋章"

        if not medal_id:
            return {"success": False, "message": f"{medal_name} 缺少勋章ID，无法购买"}

        req_kwargs = {
            "headers": self._build_ajax_headers(site_url, site_ua, referer=f"{site_url}/medal.php"),
            "timeout": self._timeout,
        }
        if site_cookie:
            req_kwargs["cookies"] = site_cookie
        if self._use_proxy and hasattr(settings, "PROXY"):
            req_kwargs["proxies"] = settings.PROXY

        data = {
            "action": "buyMedal",
            "params[medal_id]": str(medal_id),
        }

        try:
            res = RequestUtils(**req_kwargs).post_res(url=f"{site_url}/ajax.php", data=data)
            if not res:
                return {"success": False, "message": f"请求购买接口失败：{medal_name}"}

            payload = self._parse_ajax_response(res.text)
            if payload is None:
                return {"success": False, "message": f"购买 {medal_name} 响应解析失败"}

            success = payload.get("ret") == 0
            message = payload.get("msg") or ("购买成功" if success else "购买失败")
            return {"success": success, "message": message, "data": payload}
        except Exception as e:
            logger.error(f"购买 AGSVPT 勋章失败: {site_name} - {medal_name} - {e}")
            return {"success": False, "message": f"购买失败: {e}"}

    def wear_medal(self, site, medal: Dict) -> Dict:
        """佩戴 AGSVPT 勋章"""
        return self._save_user_medal_status(site, medal, wear=True)

    def unwear_medal(self, site, medal: Dict) -> Dict:
        """取下 AGSVPT 勋章"""
        return self._save_user_medal_status(site, medal, wear=False)

    def _process_medal_card(self, card, site_name: str, site_url: str, group_name: str) -> Dict:
        medal: Dict = {
            "site": site_name,
            "group": group_name,
            "currency": "冰晶",
        }

        buy_btn = self._first_node(card.xpath(".//input[contains(concat(' ', normalize-space(@class), ' '), ' buy-btn ') or contains(concat(' ', normalize-space(@class), ' '), ' buy ')]"))
        if buy_btn is not None:
            medal_id = (buy_btn.get("data-id") or "").strip()
            if medal_id:
                medal["medal_id"] = medal_id

            purchase_status = (buy_btn.get("value") or "").strip()
            if purchase_status:
                medal["purchase_status"] = purchase_status
                if buy_btn.get("disabled") is not None and purchase_status not in ("购买", "已拥有"):
                    medal["stock_status"] = purchase_status

        gift_btn = self._first_node(card.xpath(".//input[contains(concat(' ', normalize-space(@class), ' '), ' gift-btn ') or contains(concat(' ', normalize-space(@class), ' '), ' gift ')]"))
        if gift_btn is not None:
            gift_status = (gift_btn.get("value") or "").strip()
            if gift_status:
                medal["gift_status"] = gift_status
            gift_title = (gift_btn.get("title") or "").strip()
            if gift_title:
                medal["gift_fee"] = gift_title

        img = self._first_node(card.xpath("./img[1] | .//h2/img[1] | .//img[contains(concat(' ', normalize-space(@class), ' '), ' preview ')][1]"))
        if img is not None:
            img_url = (img.get("src") or "").strip()
            if img_url:
                img_url = self._absolute_url(site_url, img_url)
                medal["imageSmall"] = img_url
                medal["original_image_url"] = img_url

            img_class = img.get("class") or ""
            if "grayscale" not in img_class and medal.get("purchase_status") in ("不可购买", "仅授予", ""):
                medal["purchase_status"] = "已拥有"

            img_name = (img.get("alt") or img.get("title") or "").strip()
            if img_name:
                medal["name"] = img_name

        name_text = " ".join(text.strip() for text in card.xpath(".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-info ')]/h2/text()") if text.strip())
        if name_text:
            medal["name"] = name_text

        paragraphs = [
            " ".join(text.strip() for text in p.xpath(".//text()") if text.strip())
            for p in card.xpath(".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-info ')]/p")
        ]
        paragraphs = [text for text in paragraphs if text]
        for text in paragraphs:
            if "~" in text and not medal.get("saleBeginTime"):
                start_time, end_time = text.split("~", 1)
                medal["saleBeginTime"] = start_time.strip()
                medal["saleEndTime"] = end_time.strip()
            elif not medal.get("description"):
                medal["description"] = text

        for row in card.xpath(".//table[contains(concat(' ', normalize-space(@class), ' '), ' medal-details ')]//tr"):
            cells = [" ".join(text.strip() for text in td.xpath(".//text()") if text.strip()) for td in row.xpath("./td")]
            if len(cells) >= 2:
                self._assign_detail_field(cells[0], cells[1], medal)

        return self._format_medal_data(medal)

    def _assign_detail_field(self, label: str, value: str, medal: Dict) -> None:
        label = (label or "").strip()
        value = (value or "").strip()
        if not value:
            return

        if "加成" in label:
            medal["bonus_rate"] = value
        elif "有效期" in label:
            medal["validity"] = value
        elif "价格" in label:
            try:
                medal["price"] = int(value.replace(",", "").replace("，", ""))
            except ValueError:
                medal["price"] = 0
        elif "库存" in label:
            medal["stock"] = value

    def _get_user_id(self, site_url: str, cookies: str, ua: str = None) -> Optional[str]:
        """从首页获取用户ID"""
        try:
            res = self._request_with_retry(
                url=f"{site_url.rstrip('/')}/index.php",
                cookies=cookies,
                ua=ua,
            )
            if not res:
                return None

            match = re.search(r"userdetails\.php\?id=(\d+)", res.text)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    def _parse_user_medals(self, html, site_name: str, site_url: str) -> List[Dict]:
        """解析 AGSVPT 用户详情页中的已拥有勋章"""
        medals: List[Dict] = []
        seen_keys = set()

        try:
            medal_blocks = html.xpath('//form[.//input[@id="save-user-medal-btn"]]//div[contains(@style, "float: left") or contains(@style, "flex-direction: column")]')
            if medal_blocks:
                for block in medal_blocks:
                    medal = self._build_user_medal_from_block(block, site_name, site_url)
                    if not medal:
                        continue
                    key = self._build_user_medal_key(medal)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    medals.append(medal)
                return medals

            medal_images = html.xpath(
                '//h1//img[contains(@class, "nexus-username-medal")]'
                ' | //h1//img[contains(@class, "nexus-username-medal-big")]'
                ' | //span//img[contains(@class, "nexus-username-medal")]'
            )
            for img in medal_images:
                medal = self._build_user_medal_from_image(img, site_name, site_url)
                if not medal:
                    continue
                key = self._build_user_medal_key(medal)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                medals.append(medal)

            return medals
        except Exception as e:
            logger.error(f"解析 AGSVPT 用户勋章HTML出错: {e}")
            return []

    def _save_user_medal_status(self, site, medal: Dict, wear: bool) -> Dict:
        """保存 AGSVPT 用户勋章佩戴状态"""
        site_name = getattr(site, "name", "")
        site_url = (getattr(site, "url", "") or "").rstrip("/")
        site_cookie = getattr(site, "cookie", None)
        site_ua = getattr(site, "ua", None)
        medal_name = medal.get("name") or "未知勋章"
        action_text = "佩戴" if wear else "取下"

        try:
            user_id = self._get_user_id(site_url, site_cookie, site_ua)
            if not user_id:
                return {"success": False, "message": f"无法获取用户ID，无法{action_text}{medal_name}"}

            detail_url = f"{site_url}/userdetails.php?id={user_id}"
            res = self._request_with_retry(url=detail_url, cookies=site_cookie, ua=site_ua)
            if not res:
                return {"success": False, "message": f"获取用户勋章页面失败，无法{action_text}{medal_name}"}

            entries = self._parse_user_medal_form_entries(etree.HTML(res.text), site_url)
            if not entries:
                return {"success": False, "message": f"未找到用户勋章表单，无法{action_text}{medal_name}"}

            target_entry = self._find_target_user_medal_entry(entries, medal)
            if not target_entry:
                return {"success": False, "message": f"未找到勋章 {medal_name} 的用户表单项"}

            target_entry["checked"] = wear
            payload = self._build_save_user_medal_payload(entries)

            req_kwargs = {
                "headers": self._build_ajax_headers(site_url, site_ua, referer=detail_url),
                "timeout": self._timeout,
            }
            if site_cookie:
                req_kwargs["cookies"] = site_cookie
            if self._use_proxy and hasattr(settings, "PROXY"):
                req_kwargs["proxies"] = settings.PROXY

            post_res = RequestUtils(**req_kwargs).post_res(url=f"{site_url}/ajax.php", data=payload)
            if not post_res:
                return {"success": False, "message": f"请求{action_text}接口失败：{medal_name}"}

            ajax_payload = self._parse_ajax_response(post_res.text)
            if ajax_payload is None:
                return {"success": False, "message": f"{action_text}{medal_name}响应解析失败"}

            success = ajax_payload.get("ret") == 0
            message = ajax_payload.get("msg") or (f"{action_text}成功" if success else f"{action_text}失败")
            return {"success": success, "message": message, "data": ajax_payload}
        except Exception as e:
            logger.error(f"AGSVPT {action_text}勋章失败: {site_name} - {medal_name} - {e}")
            return {"success": False, "message": f"{action_text}失败: {e}"}

    def _parse_user_medal_form_entries(self, html, site_url: str) -> List[Dict]:
        entries: List[Dict] = []
        blocks = html.xpath('//form[.//input[@id="save-user-medal-btn"]]//div[contains(@style, "flex-direction: column") or contains(@style, "float: left")]')

        for block in blocks:
            img_nodes = block.xpath('.//img[contains(@class, "preview")] | .//img')
            priority_input = block.xpath('.//input[starts-with(@name, "priority_")]')
            if not img_nodes or not priority_input:
                continue

            status_input = block.xpath('.//input[starts-with(@name, "status_")]')
            img = img_nodes[0]
            priority = priority_input[0]
            image_url = self._absolute_url(site_url, (img.get("src") or "").strip())

            entries.append({
                "name": (img.get("title") or img.get("alt") or "").strip(),
                "imageSmall": image_url,
                "priority_name": (priority.get("name") or "").strip(),
                "priority_value": (priority.get("value") or "0").strip() or "0",
                "status_name": (status_input[0].get("name") or "").strip() if status_input else "",
                "status_value": (status_input[0].get("value") or "1").strip() if status_input else "1",
                "checked": bool(status_input and status_input[0].get("checked") is not None),
            })

        return entries

    def _find_target_user_medal_entry(self, entries: List[Dict], medal: Dict) -> Optional[Dict]:
        medal_name = self._normalize_medal_name(medal.get("name"))
        medal_image = (medal.get("imageSmall") or "").strip().lower()

        for entry in entries:
            if medal_name and self._normalize_medal_name(entry.get("name")) == medal_name:
                return entry

        for entry in entries:
            if medal_image and (entry.get("imageSmall") or "").strip().lower() == medal_image:
                return entry

        return None

    def _build_save_user_medal_payload(self, entries: List[Dict]) -> Dict:
        payload: Dict[str, str] = {}
        index = 0

        for entry in entries:
            payload[f"params[{index}][name]"] = entry["priority_name"]
            payload[f"params[{index}][value]"] = entry["priority_value"]
            index += 1

            if entry.get("checked") and entry.get("status_name"):
                payload[f"params[{index}][name]"] = entry["status_name"]
                payload[f"params[{index}][value]"] = entry.get("status_value", "1")
                index += 1

        payload["action"] = "saveUserMedal"
        return payload

    def _build_user_medal_from_block(self, block, site_name: str, site_url: str) -> Optional[Dict]:
        imgs = block.xpath('.//img[contains(@class, "preview")] | .//img')
        if not imgs:
            return None

        medal = self._build_user_medal_from_image(imgs[0], site_name, site_url)
        if not medal:
            return None

        info_texts = block.xpath(".//span/text() | .//table//text() | ./div[last()]//text()")
        info_text = " ".join(text.strip() for text in info_texts if text.strip())

        expire_match = re.search(r"过期时间[：:]\s*(.+?)(?:\s+冰晶加成|$)", info_text)
        if expire_match:
            medal["validity"] = expire_match.group(1).strip()

        bonus_match = re.search(r"冰晶加成(?:系数)?[：:]\s*([\d.]+%?)", info_text)
        if bonus_match:
            medal["bonus_rate"] = bonus_match.group(1).strip()

        status_input = block.xpath('.//input[starts-with(@name, "status_")]')
        if status_input:
            medal["wear_status"] = "已佩戴" if status_input[0].get("checked") is not None else "未佩戴"

        wear_text = "".join(block.xpath('.//*[contains(text(), "已佩戴")]/text() | .//*[contains(text(), "未佩戴")]/text()')).strip()
        if wear_text:
            medal["wear_status"] = wear_text

        return self._format_medal_data(medal)

    def _build_user_medal_from_image(self, img, site_name: str, site_url: str) -> Optional[Dict]:
        img_src = (img.get("src") or "").strip()
        if not img_src:
            return None

        img_src = self._absolute_url(site_url, img_src)
        medal = {
            "imageSmall": img_src,
            "original_image_url": img_src,
            "name": (img.get("title") or img.get("alt") or "").strip(),
            "site": site_name,
            "purchase_status": "已拥有",
            "currency": "冰晶",
        }

        parent_text = " ".join(text.strip() for text in img.xpath("./ancestor::*[1]//text()") if text.strip())
        if "已佩戴" in parent_text:
            medal["wear_status"] = "已佩戴"
        elif "未佩戴" in parent_text:
            medal["wear_status"] = "未佩戴"

        return self._format_medal_data(medal)

    def _extract_group_name(self, container) -> str:
        title = container.xpath("./preceding-sibling::div[contains(concat(' ', normalize-space(@class), ' '), ' medal-type-header ')][1]/@data-type")
        if title:
            return title[0].strip()
        return "默认分组"

    def _absolute_url(self, site_url: str, value: str) -> str:
        if not value:
            return ""
        if value.startswith(("http://", "https://")):
            return value
        return urljoin(f"{site_url.rstrip('/')}/", value.lstrip("/"))

    def _build_user_medal_key(self, medal: Dict) -> str:
        name = (medal.get("name") or "").strip().lower()
        image = (medal.get("imageSmall") or "").strip().lower()
        return f"{name}|{image}"

    def _parse_ajax_response(self, response_text: str) -> Optional[dict]:
        try:
            return json.loads(response_text)
        except Exception:
            logger.error(f"AGSVPT Ajax响应解析失败: {response_text}")
            return None

    @staticmethod
    def _build_ajax_headers(site_url: str, ua: str = None, referer: str = None) -> Dict:
        return {
            "User-Agent": ua if ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": referer or f"{site_url.rstrip('/')}/medal.php",
            "X-Requested-With": "XMLHttpRequest",
        }

    @staticmethod
    def _first_node(nodes):
        return nodes[0] if nodes else None

    @staticmethod
    def _normalize_medal_name(name: str) -> str:
        return "".join(str(name or "").split()).strip().lower()
