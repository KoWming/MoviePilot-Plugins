import json
import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

from lxml import etree

from app.core.config import settings
from app.log import logger
from app.utils.http import RequestUtils

from .base import BaseMedalSiteHandler


class City13MedalHandler(BaseMedalSiteHandler):
    """13City 站点勋章处理器"""

    def match(self, site) -> bool:
        """判断是否为 13City 站点"""
        site_name = (site.name or "").lower()
        site_url = (site.url or "").lower()
        return "13city" in site_name or "13city" in site_url

    def fetch_medals(self, site) -> List[Dict]:
        """获取 13City 站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie

            medals: List[Dict] = []
            current_page = 0

            while True:
                url = f"{site_url.rstrip('/')}/medal.php?q=&sort=category"
                logger.info(f"正在获取【{site_name}】站点勋章数据")

                if current_page > 0:
                    url = f"{url}&page={current_page}"

                logger.info(f"正在获取第 {current_page + 1} 页勋章数据")

                res = self._request_with_retry(url=url, cookies=site_cookie)
                if not res:
                    logger.error(f"请求勋章页面失败！站点：{site_name}")
                    break

                html = etree.HTML(res.text)
                category_sections = html.xpath("//div[starts-with(@id, 'category-') and .//h2[contains(@class, 'category-title')]]")
                if not category_sections:
                    logger.error("未找到 13City 勋章分类容器！")
                    break

                page_count = 0
                for section in category_sections:
                    group_name = self._extract_group_name(section)
                    medal_cards = section.xpath(".//div[contains(@class, 'medal-card')]")
                    for card in medal_cards:
                        try:
                            medal = self._process_medal_card(card, site_name, site_url, group_name)
                            if medal:
                                medals.append(medal)
                                page_count += 1
                        except Exception as e:
                            logger.error(f"处理 13City 勋章卡片时发生错误：{e}")

                logger.info(f"当前页面找到 {page_count} 个勋章")

                next_page = html.xpath("//p[@class='nexus-pagination']//a[contains(., '下一页')]")
                if not next_page:
                    logger.info("未找到下一页链接，已到达最后一页")
                    break

                next_href = next_page[0].get("href")
                if not next_href:
                    logger.info("下一页链接为空，已到达最后一页")
                    break

                try:
                    parsed = urlparse(next_href)
                    params = parse_qs(parsed.query)
                    next_page_num = int(params.get("page", [0])[0])
                    if next_page_num <= current_page:
                        logger.info("已到达最后一页")
                        break
                    current_page = next_page_num
                except (ValueError, IndexError, AttributeError) as e:
                    logger.error(f"解析下一页页码失败：{e}")
                    break

            logger.info(f"共获取到 {len(medals)} 个勋章数据")
            return medals
        except Exception as e:
            logger.error(f"处理 13City 站点勋章数据时发生错误: {e}")
            return []

    def fetch_user_medals(self, site) -> List[Dict]:
        """获取 13City 用户已拥有勋章"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie

            user_id = self._get_user_id(site_url, site_cookie)
            if not user_id:
                logger.error(f"无法获取站点 {site_name} 的用户ID")
                return []

            logger.info(f"获取到用户ID: {user_id}")

            detail_url = f"{site_url.rstrip('/')}/userdetails.php?id={user_id}"
            logger.info("正在获取用户详情页")

            res = self._request_with_retry(url=detail_url, cookies=site_cookie)
            if not res:
                logger.error(f"请求用户详情页失败！站点：{site_name}")
                return []

            html = etree.HTML(res.text)
            medals = self._parse_user_medals(html, site_name, site_url)
            logger.info(f"共获取到 {len(medals)} 个用户已拥有勋章")
            return medals
        except Exception as e:
            logger.error(f"获取 13City 用户已拥有勋章失败: {e}")
            return []

    def purchase_medal(self, site, medal: Dict) -> Dict:
        """购买 13City 勋章"""
        site_name = getattr(site, 'name', '')
        site_url = (getattr(site, 'url', '') or '').rstrip('/')
        site_cookie = getattr(site, 'cookie', None)
        site_ua = getattr(site, 'ua', None)
        medal_id = medal.get('medal_id') or medal.get('id')
        medal_name = medal.get('name') or '未知勋章'

        if not medal_id:
            return {
                'success': False,
                'message': f'{medal_name} 缺少勋章ID，无法购买'
            }

        req_kwargs = {
            'headers': {
                'User-Agent': site_ua if site_ua else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': f'{site_url}/medal.php?q=&sort=category',
                'X-Requested-With': 'XMLHttpRequest',
            },
            'timeout': self._timeout,
        }
        if site_cookie:
            req_kwargs['cookies'] = site_cookie
        if self._use_proxy and hasattr(settings, 'PROXY'):
            req_kwargs['proxies'] = settings.PROXY

        ajax_url = f'{site_url}/ajax.php'
        data = {
            'action': 'buyMedal',
            'params[medal_id]': str(medal_id),
        }

        try:
            res = RequestUtils(**req_kwargs).post_res(url=ajax_url, data=data)
            if not res:
                return {
                    'success': False,
                    'message': f'请求购买接口失败：{medal_name}'
                }

            payload = self._parse_ajax_response(res.text)
            if payload is None:
                return {
                    'success': False,
                    'message': f'购买 {medal_name} 响应解析失败'
                }

            success = payload.get('ret') == 0
            message = payload.get('msg') or ('购买成功' if success else '购买失败')
            return {
                'success': success,
                'message': message,
                'data': payload,
            }
        except Exception as e:
            logger.error(f'购买 13City 勋章失败: {site_name} - {medal_name} - {e}')
            return {
                'success': False,
                'message': f'购买失败: {e}'
            }

    def wear_medal(self, site, medal: Dict) -> Dict:
        """佩戴 13City 勋章"""
        return self._save_user_medal_status(site, medal, wear=True)

    def unwear_medal(self, site, medal: Dict) -> Dict:
        """取下 13City 勋章"""
        return self._save_user_medal_status(site, medal, wear=False)

    def _get_user_id(self, site_url: str, cookies: str) -> Optional[str]:
        """从首页获取用户ID"""
        try:
            index_url = f"{site_url.rstrip('/')}/index.php"
            res = self._request_with_retry(url=index_url, cookies=cookies)
            if not res:
                return None

            match = re.search(r"userdetails\.php\?id=(\d+)", res.text)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    def _save_user_medal_status(self, site, medal: Dict, wear: bool) -> Dict:
        """保存 13City 用户勋章佩戴状态"""
        site_name = getattr(site, 'name', '')
        site_url = (getattr(site, 'url', '') or '').rstrip('/')
        site_cookie = getattr(site, 'cookie', None)
        site_ua = getattr(site, 'ua', None)
        medal_name = medal.get('name') or '未知勋章'
        action_text = '佩戴' if wear else '取下'

        try:
            user_id = self._get_user_id(site_url, site_cookie)
            if not user_id:
                return {
                    'success': False,
                    'message': f'无法获取用户ID，无法{action_text}{medal_name}'
                }

            detail_url = f'{site_url}/userdetails.php?id={user_id}'
            res = self._request_with_retry(url=detail_url, cookies=site_cookie, ua=site_ua)
            if not res:
                return {
                    'success': False,
                    'message': f'获取用户勋章页面失败，无法{action_text}{medal_name}'
                }

            html = etree.HTML(res.text)
            entries = self._parse_user_medal_form_entries(html, site_url)
            if not entries:
                return {
                    'success': False,
                    'message': f'未找到用户勋章表单，无法{action_text}{medal_name}'
                }

            target_entry = self._find_target_user_medal_entry(entries, medal)
            if not target_entry:
                return {
                    'success': False,
                    'message': f'未找到勋章 {medal_name} 的用户表单项'
                }

            target_entry['checked'] = wear
            payload = self._build_save_user_medal_payload(entries)

            req_kwargs = {
                'headers': {
                    'User-Agent': site_ua if site_ua else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': detail_url,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                'timeout': self._timeout,
            }
            if site_cookie:
                req_kwargs['cookies'] = site_cookie
            if self._use_proxy and hasattr(settings, 'PROXY'):
                req_kwargs['proxies'] = settings.PROXY

            ajax_url = f'{site_url}/ajax.php'
            post_res = RequestUtils(**req_kwargs).post_res(url=ajax_url, data=payload)
            if not post_res:
                return {
                    'success': False,
                    'message': f'请求{action_text}接口失败：{medal_name}'
                }

            ajax_payload = self._parse_ajax_response(post_res.text)
            if ajax_payload is None:
                return {
                    'success': False,
                    'message': f'{action_text}{medal_name}响应解析失败'
                }

            success = ajax_payload.get('ret') == 0
            message = ajax_payload.get('msg') or (f'{action_text}成功' if success else f'{action_text}失败')
            return {
                'success': success,
                'message': message,
                'data': ajax_payload,
            }
        except Exception as e:
            logger.error(f'13City {action_text}勋章失败: {site_name} - {medal_name} - {e}')
            return {
                'success': False,
                'message': f'{action_text}失败: {e}'
            }

    def _parse_user_medals(self, html, site_name: str, site_url: str) -> List[Dict]:
        """解析 13City 用户详情页中的已拥有勋章"""
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
                '//h1//img[contains(@src, "medals/") or contains(@src, "pic/medals/")]'
                ' | //span//img[contains(@src, "medals/") or contains(@src, "pic/medals/")]'
                ' | //img[contains(@class, "nexus-username-medal") or contains(@class, "nexus-username-medal-big")]'
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
            logger.error(f"解析 13City 用户勋章HTML出错: {e}")
            return []

    def _parse_user_medal_form_entries(self, html, site_url: str) -> List[Dict]:
        """解析用户勋章表单项，用于保存佩戴状态"""
        entries: List[Dict] = []
        blocks = html.xpath('//form[.//input[@id="save-user-medal-btn"]]//div[contains(@style, "flex-direction: column") or contains(@style, "float: left")]')

        for block in blocks:
            img_nodes = block.xpath('.//img[@class="preview"] | .//img')
            priority_input = block.xpath('.//input[starts-with(@name, "priority_")]')
            if not img_nodes or not priority_input:
                continue

            img = img_nodes[0]
            priority = priority_input[0]
            status_input = block.xpath('.//input[starts-with(@name, "status_")]')

            image_url = img.get('src', '').strip()
            if image_url and not image_url.startswith(("http://", "https://")):
                image_url = urljoin(f'{site_url.rstrip("/")}/', image_url.lstrip('/'))

            entry = {
                'name': (img.get('title') or img.get('alt') or '').strip(),
                'imageSmall': image_url,
                'priority_name': priority.get('name', '').strip(),
                'priority_value': priority.get('value', '0').strip() or '0',
                'status_name': status_input[0].get('name', '').strip() if status_input else '',
                'status_value': status_input[0].get('value', '1').strip() if status_input else '1',
                'checked': bool(status_input and status_input[0].get('checked') is not None),
            }
            entries.append(entry)

        return entries

    def _find_target_user_medal_entry(self, entries: List[Dict], medal: Dict) -> Optional[Dict]:
        """根据勋章信息匹配用户表单项"""
        medal_name = self._normalize_medal_name(medal.get('name'))
        medal_image = (medal.get('imageSmall') or '').strip().lower()

        for entry in entries:
            if medal_name and self._normalize_medal_name(entry.get('name')) == medal_name:
                return entry

        for entry in entries:
            if medal_image and (entry.get('imageSmall') or '').strip().lower() == medal_image:
                return entry

        return None

    def _build_save_user_medal_payload(self, entries: List[Dict]) -> Dict:
        """构造 saveUserMedal 请求参数"""
        payload: Dict[str, str] = {}
        index = 0

        for entry in entries:
            payload[f'params[{index}][name]'] = entry['priority_name']
            payload[f'params[{index}][value]'] = entry['priority_value']
            index += 1

            if entry.get('checked') and entry.get('status_name'):
                payload[f'params[{index}][name]'] = entry['status_name']
                payload[f'params[{index}][value]'] = entry.get('status_value', '1')
                index += 1

        payload['action'] = 'saveUserMedal'
        return payload

    def _build_user_medal_from_block(self, block, site_name: str, site_url: str) -> Optional[Dict]:
        imgs = block.xpath('.//img[@class="preview"] | .//img')
        if not imgs:
            return None

        medal = self._build_user_medal_from_image(imgs[0], site_name, site_url)
        if not medal:
            return None

        info_texts = block.xpath('.//span/text() | .//table//text() | ./div[last()]//text()')
        info_text = ' '.join([text.strip() for text in info_texts if text.strip()])

        expire_match = re.search(r"过期时间[：:]\s*(.+?)(?:\s+(?:魔力|啤酒瓶)加成|$)", info_text)
        if expire_match:
            medal['validity'] = expire_match.group(1).strip()

        bonus_match = re.search(r"(?:魔力|啤酒瓶)加成(?:系数)?[：:]\s*([\d.]+%?)", info_text)
        if bonus_match:
            medal['bonus_rate'] = bonus_match.group(1).strip()

        status_input = block.xpath('.//input[starts-with(@name, "status_")]')
        if status_input:
            medal['wear_status'] = '已佩戴' if status_input[0].get('checked') is not None else '未佩戴'

        wear_text = ''.join(block.xpath('.//*[contains(text(), "已佩戴")]/text() | .//*[contains(text(), "未佩戴")]/text()')).strip()
        if wear_text:
            medal['wear_status'] = wear_text

        return self._format_medal_data(medal)

    def _build_user_medal_from_image(self, img, site_name: str, site_url: str) -> Optional[Dict]:
        img_src = img.get('src')
        if not img_src:
            return None

        if not img_src.startswith(("http://", "https://")):
            img_src = urljoin(f"{site_url.rstrip('/')}/", img_src.lstrip('/'))

        medal = {
            'imageSmall': img_src,
            'original_image_url': img_src,
            'name': (img.get('title') or img.get('alt') or '').strip(),
            'site': site_name,
            'purchase_status': '已拥有',
            'currency': '啤酒瓶',
        }

        parent_text = ' '.join([text.strip() for text in img.xpath('./ancestor::*[1]//text()') if text.strip()])
        if '已佩戴' in parent_text:
            medal['wear_status'] = '已佩戴'
        elif '未佩戴' in parent_text:
            medal['wear_status'] = '未佩戴'

        return self._format_medal_data(medal)

    def _build_user_medal_key(self, medal: Dict) -> str:
        name = (medal.get('name') or '').strip().lower()
        image = (medal.get('imageSmall') or '').strip().lower()
        return f"{name}|{image}"

    def _normalize_medal_name(self, name: str) -> str:
        return ''.join(str(name or '').split()).strip().lower()

    def _parse_ajax_response(self, response_text: str) -> Optional[dict]:
        """解析 13City ajax 返回"""
        try:
            return json.loads(response_text)
        except Exception:
            logger.error(f"13City Ajax响应解析失败: {response_text}")
            return None

    def _extract_group_name(self, section) -> str:
        title = section.xpath(".//h2[contains(@class, 'category-title')]/text()")
        if title:
            return title[0].strip()
        section_id = section.get("id") or ""
        if section_id.startswith("category-"):
            return section_id.replace("category-", "").strip()
        return "默认分组"

    def _process_medal_card(self, card, site_name: str, site_url: str, group_name: str) -> Dict:
        medal: Dict = {
            "site": site_name,
            "group": group_name,
            "currency": "啤酒瓶",
        }

        medal_id = card.xpath(".//div[contains(@class, 'medal-action')]//button[contains(@class, 'buy')]/@data-id")
        if medal_id:
            medal["medal_id"] = medal_id[0].strip()

        img = card.xpath(".//div[contains(@class, 'medal-image-container')]//img/@src")
        if img:
            img_url = img[0].strip()
            if not img_url.startswith(("http://", "https://")):
                img_url = urljoin(f"{site_url.rstrip('/')}/", img_url.lstrip('/'))
            medal["imageSmall"] = img_url
            medal["original_image_url"] = img_url

        name = card.xpath(".//div[contains(@class, 'medal-name')]/text()")
        if name:
            medal["name"] = name[0].strip()

        info_div = card.xpath(".//div[contains(@class, 'medal-info')]")
        if info_div:
            self._parse_medal_info(info_div[0], medal)

        action_div = card.xpath(".//div[contains(@class, 'medal-action')]")
        if action_div:
            self._parse_medal_action(action_div[0], medal)

        return self._format_medal_data(medal)

    def _parse_medal_info(self, info_div, medal: Dict) -> None:
        description_parts: List[str] = []
        current_label = None

        for div in info_div.xpath("./div"):
            text_parts = [text.strip() for text in div.xpath(".//text()") if text.strip()]
            if not text_parts:
                continue

            strong_text = "".join(div.xpath("./strong/text()")).strip()
            full_text = " ".join(text_parts)

            if strong_text:
                label = strong_text.rstrip("：:")
                value = full_text[len(strong_text):].strip() if full_text.startswith(strong_text) else full_text
                current_label = label
                self._assign_info_field(label, value, medal)
            elif current_label == "可购买时间":
                self._assign_info_field(current_label, full_text, medal)
                current_label = None
            else:
                description_parts.append(full_text)

        if description_parts:
            medal["description"] = "\n".join(description_parts)

    def _assign_info_field(self, label: str, value: str, medal: Dict) -> None:
        value = value.strip()
        if not value:
            return

        if "可购买时间" in label:
            if " 至 " in value:
                start_time, end_time = value.split(" 至 ", 1)
                medal["saleBeginTime"] = start_time.strip()
                medal["saleEndTime"] = end_time.strip()
            else:
                medal["saleBeginTime"] = value
        elif "有效期" in label:
            medal["validity"] = value
        elif "加成" in label:
            medal["bonus_rate"] = value
        elif "价格" in label:
            price_text = value.replace(",", "").replace("，", "")
            try:
                medal["price"] = int(price_text)
            except ValueError:
                medal["price"] = 0
        elif "库存" in label:
            medal["stock"] = value

    def _parse_medal_action(self, action_div, medal: Dict) -> None:
        buttons = action_div.xpath(".//button[contains(@class, 'buy')]")
        if buttons:
            buy_btn = buttons[0]
            purchase_status = "".join(buy_btn.xpath(".//text()")).strip()
            if purchase_status:
                medal["purchase_status"] = purchase_status
            if buy_btn.get("disabled") is not None and buy_btn.get("title"):
                medal["stock_status"] = buy_btn.get("title").strip()
