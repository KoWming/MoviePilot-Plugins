import re
from typing import Dict, List
from urllib.parse import parse_qs, urljoin, urlparse

from lxml import etree

from app.log import logger
from .base import BaseMedalSiteHandler


class SiqiMedalHandler(BaseMedalSiteHandler):
    """思齐站点勋章处理器"""

    def match(self, site) -> bool:
        """判断是否为思齐站点"""
        site_name = (site.name or "").lower()
        site_url = (site.url or "").lower()
        return (
            "si-qi" in site_name
            or "siqi" in site_name
            or "si-qi.xyz" in site_url
            or "img.si-qi.xyz" in site_url
        )

    def fetch_medals(self, site) -> List[Dict]:
        """获取思齐站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            site_ua = getattr(site, 'ua', None)

            medals = []
            current_page = 0

            while True:
                url = f"{site_url.rstrip('/')}/medal.php"
                if current_page > 0:
                    url = f"{url}?page={current_page}"

                logger.info(f"正在获取【{site_name}】站点勋章数据，第 {current_page + 1} 页")

                res = self._request_with_retry(
                    url=url,
                    cookies=site_cookie,
                    ua=site_ua
                )

                if not res:
                    logger.error(f"请求勋章页面失败！站点：{site_name}")
                    break

                html = etree.HTML(res.text)
                medal_sections = html.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-section ')]")
                if not medal_sections:
                    logger.error(f"未找到思齐勋章分组！站点：{site_name}")
                    break

                current_page_count = 0
                for section in medal_sections:
                    group_name = self._parse_group_name(section)
                    medal_cards = section.xpath(
                        ".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-grid ')]"
                        "//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card ')]"
                    )

                    logger.info(f"分组 [{group_name}] 找到 {len(medal_cards)} 个勋章")

                    for card in medal_cards:
                        try:
                            medal = self._process_medal_card(card, site_name, site_url, group_name)
                            if medal:
                                medals.append(medal)
                                current_page_count += 1
                        except Exception as e:
                            logger.error(f"处理思齐勋章卡片时发生错误：{str(e)}")
                            continue

                logger.info(f"第 {current_page + 1} 页共获取 {current_page_count} 个勋章")

                next_page = html.xpath("//p[contains(@class, 'nexus-pagination')]//a[contains(., '下一页')]/@href")
                if not next_page:
                    break

                next_href = next_page[0]
                try:
                    parsed = urlparse(next_href)
                    params = parse_qs(parsed.query)
                    next_page_num = int(params.get('page', [current_page])[0])
                    if next_page_num <= current_page:
                        break
                    current_page = next_page_num
                except Exception:
                    break

            logger.info(f"共获取到 {len(medals)} 个思齐勋章数据")
            return medals

        except Exception as e:
            logger.error(f"处理思齐站点勋章数据时发生错误: {str(e)}")
            return []

    def _parse_group_name(self, section) -> str:
        """解析分组名称"""
        title = ''.join(
            section.xpath(".//h2[contains(concat(' ', normalize-space(@class), ' '), ' section-title ')][1]//text()")
        ).strip()
        if not title:
            return "默认分组"
        title = re.sub(r'（\d+/\d+）$', '', title).strip()
        title = re.sub(r'\(\d+/\d+\)$', '', title).strip()
        return title or "默认分组"

    def _process_medal_card(self, card, site_name: str, site_url: str, group_name: str) -> Dict:
        """处理单个思齐勋章卡片"""
        medal = {
            'site': site_name,
            'group': group_name,
        }

        card_class = card.get('class', '')
        if 'owned' in card_class.split():
            medal['purchase_status'] = '已拥有'

        img = card.xpath(
            ".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card__image ')]//img/@src"
        )
        if img:
            img_url = img[0].strip()
            if img_url and not img_url.startswith('http'):
                img_url = urljoin(site_url + '/', img_url.lstrip('/'))
            medal['imageSmall'] = img_url

        img_alt = card.xpath(
            ".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card__image ')]//img/@alt"
        )
        if img_alt and img_alt[0].strip():
            medal['name'] = img_alt[0].strip()

        title = ''.join(
            card.xpath(".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card__title ')]//h2[1]//text()")
        ).strip()
        if title:
            id_match = re.search(r'#(\d+)', title)
            if id_match:
                medal['medal_id'] = id_match.group(1)
            clean_title = re.sub(r'\s*\(#\d+\)', '', title).strip()
            if clean_title:
                medal['name'] = clean_title

        description = ''.join(
            card.xpath(".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card__desc ')][1]//text()")
        ).strip()
        if description:
            medal['description'] = description

        meta_items = card.xpath(".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card__meta ')]/div")
        for item in meta_items:
            label = ''.join(item.xpath(".//span[contains(concat(' ', normalize-space(@class), ' '), ' meta-label ')][1]//text()")).strip()
            value = ''.join(item.xpath(".//span[contains(concat(' ', normalize-space(@class), ' '), ' meta-value ')][1]//text()")).strip()
            if not label:
                continue
            self._map_meta_field(medal, label, value)

        input_ids = card.xpath(
            ".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card__actions ')]//input[@data-id]/@data-id"
        )
        if input_ids and not medal.get('medal_id'):
            medal['medal_id'] = input_ids[0].strip()

        action_values = [
            v.strip()
            for v in card.xpath(
                ".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card__actions ')]//input[@type='button']/@value"
            )
            if v.strip()
        ]
        action_texts = [
            t.strip()
            for t in card.xpath(
                ".//div[contains(concat(' ', normalize-space(@class), ' '), ' medal-card__actions ')]//text()"
            )
            if t.strip()
        ]

        if not medal.get('purchase_status'):
            medal['purchase_status'] = self._resolve_purchase_status(action_values, action_texts)

        if medal.get('stock', '').isdigit():
            stock_num = int(medal['stock'])
            if 0 < stock_num <= 10:
                medal['stock_status'] = '库存紧张'

        return self._format_medal_data(medal)

    def _map_meta_field(self, medal: Dict, label: str, value: str) -> None:
        """映射元信息字段"""
        if label == '可购买时间':
            if ' ~ ' in value:
                begin, end = value.split(' ~ ', 1)
                medal['saleBeginTime'] = begin.strip()
                medal['saleEndTime'] = end.strip()
            else:
                medal['saleBeginTime'] = value
        elif label == '购买后有效期(天)':
            medal['validity'] = value
        elif label == '魔力加成':
            medal['bonus_rate'] = value
        elif label == '价格':
            try:
                medal['price'] = int(value.replace(',', '').strip())
            except Exception:
                medal['price'] = 0
        elif label == '库存':
            medal['stock'] = value
        elif label == '手续费':
            medal['gift_fee'] = value

    def _resolve_purchase_status(self, action_values: List[str], action_texts: List[str]) -> str:
        """解析购买状态"""
        if any('仅授予' in text for text in action_texts):
            return '仅授予'
        if any('已过可购买时间' in value for value in action_values):
            return '已过可购买时间'
        if any('需要更多魔力值' in value for value in action_values):
            return '需要更多魔力值'
        if any('售罄' in value or '售完' in value for value in action_values):
            return '售罄'
        if any('购买' == value or '立即购买' in value for value in action_values):
            return '购买'
        if action_values:
            return action_values[0]
        return ''