from typing import Dict, List
from app.log import logger
from lxml import etree
from .base import BaseMedalSiteHandler
from urllib.parse import urljoin

class DubheMedalHandler(BaseMedalSiteHandler):
    """天枢站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为dubhe.site站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "dubhe" in site_name or "dubhe" in site_url or "天枢" in site_name or "天枢" in site_url

    def fetch_medals(self, site) -> List[Dict]:
        """获取天枢站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            # 获取勋章页面数据
            url = f"{site_url.rstrip('/')}/medal.php"
            logger.info(f"正在获取【{site_name}】站点勋章数据")
            
            # 发送请求获取勋章页面
            res = self._request_with_retry(
                url=url,
                cookies=site_cookie
            )
            
            if not res:
                logger.error(f"请求勋章页面失败！站点：{site_name}")
                return []
                
            # 使用lxml解析HTML
            html = etree.HTML(res.text)
            
            # 处理所有勋章数据
            medals = []
            
            # 1. 处理"最近上新"区域的勋章（作为默认分组）
            new_medals_section = html.xpath("//div[@class='medal-new-section']")
            if new_medals_section:
                logger.info("处理最近上新勋章...")
                new_medal_cards = new_medals_section[0].xpath(".//a[@class='medal-new-card']")
                logger.info(f"找到 {len(new_medal_cards)} 个最近上新勋章")
                
                for card in new_medal_cards:
                    try:
                        medal = self._process_new_medal_item(card, site_name, site_url, "最近上新")
                        if medal:
                            medals.append(medal)
                    except Exception as e:
                        logger.error(f"处理最近上新勋章时发生错误：{str(e)}")
                        continue
            
            # 2. 处理勋章系列区域
            medal_series = html.xpath("//section[@class='medal-series-card ']")
            if not medal_series:
                # 尝试匹配不带空格的类名
                medal_series = html.xpath("//section[contains(@class, 'medal-series-card')]")
            
            logger.info(f"找到 {len(medal_series)} 个勋章系列")
            
            # 遍历所有勋章系列
            for series in medal_series:
                try:
                    # 获取系列名称
                    series_name_elem = series.xpath(".//div[@class='medal-series-info']//h2/text()")
                    group_name = "默认分组"
                    if series_name_elem:
                        group_name = series_name_elem[0].strip()
                        logger.info(f"处理勋章系列: {group_name}")
                    
                    # 获取该系列下的所有勋章卡片
                    medal_cards = series.xpath(".//div[@class='medal-grid']//div[@class='medal-card locked']")
                    if not medal_cards:
                        # 尝试匹配所有medal-card（包括已拥有的）
                        medal_cards = series.xpath(".//div[@class='medal-grid']//div[contains(@class, 'medal-card')]")
                    
                    logger.info(f"找到 {len(medal_cards)} 个勋章")
                    
                    for card in medal_cards:
                        try:
                            medal = self._process_medal_item(card, site_name, site_url, group_name)
                            if medal:
                                medals.append(medal)
                        except Exception as e:
                            logger.error(f"处理勋章数据时发生错误：{str(e)}")
                            continue
                            
                except Exception as e:
                    logger.error(f"处理勋章系列时发生错误：{str(e)}")
                    continue
            
            logger.info(f"共获取到 {len(medals)} 个勋章数据")
            return medals
            
        except Exception as e:
            logger.error(f"处理天枢站点勋章数据时发生错误: {str(e)}")
            return []

    def _process_new_medal_item(self, card, site_name: str, site_url: str, group_name: str = "") -> Dict:
        """处理最近上新区域的勋章项数据"""
        medal = {}
        
        try:
            # 图片
            img = card.xpath(".//img[@class='preview']/@src")
            if img:
                img_url = img[0]
                # 如果不是http/https开头，补全为完整站点URL
                if not img_url.startswith(('http://', 'https://')):
                    img_url = urljoin(site_url, img_url.lstrip('/'))
                medal['imageSmall'] = img_url
            
            # 名称
            name = card.xpath(".//h4/text()")
            if name:
                medal['name'] = name[0].strip()
            
            # 拥有状态
            ownership_tag = card.xpath(".//span[@class='medal-new-tag ']/text()")
            if ownership_tag:
                status = ownership_tag[0].strip()
                if status == "未拥有":
                    medal['purchase_status'] = "未拥有"
                elif status == "owned":
                    medal['purchase_status'] = "已拥有"
            
            # 价格和有效期 - 从medal-new-meta区域提取
            meta_divs = card.xpath(".//div[@class='medal-new-meta']/div/text()")
            for meta in meta_divs:
                meta = meta.strip()
                if meta.startswith("价格："):
                    try:
                        price_str = meta.replace("价格：", "").replace(",", "")
                        medal['price'] = int(price_str)
                    except ValueError:
                        medal['price'] = 0
                elif meta.startswith("有效期："):
                    medal['validity'] = meta.replace("有效期：", "")
            
            # 上新时间 - 从medal-new-footer区域提取
            new_time = card.xpath(".//div[@class='medal-new-footer']/text()")
            if new_time:
                # 格式：上新：2026-01-09
                time_text = new_time[0].strip()
                if time_text.startswith("上新："):
                    medal['new_time'] = time_text.replace("上新：", "")
            
            # 站点信息
            medal['site'] = site_name
            # 货币单位
            medal['currency'] = '魔力值'
            # 分组信息
            if group_name:
                medal['group'] = group_name
            
            return self._format_medal_data(medal)
            
        except Exception as e:
            logger.error(f"处理最近上新勋章项数据时发生错误: {str(e)}")
            return None

    def _process_medal_item(self, card, site_name: str, site_url: str, group_name: str = "") -> Dict:
        """处理勋章系列区域的勋章项数据"""
        medal = {}
        
        try:
            # 获取medal-card-image区域
            image_div = card.xpath(".//div[@class='medal-card-image']")
            if not image_div:
                logger.warning("未找到medal-card-image区域")
                return None
            image_div = image_div[0]
            
            # 图片
            img = image_div.xpath(".//img[@class='preview']/@src")
            if img:
                img_url = img[0]
                # 如果不是http/https开头，补全为完整站点URL
                if not img_url.startswith(('http://', 'https://')):
                    img_url = urljoin(site_url, img_url.lstrip('/'))
                medal['imageSmall'] = img_url
            
            # 魔力加成
            bonus_chip = image_div.xpath(".//span[@class='medal-card-chip']/text()")
            if bonus_chip:
                medal['bonus_rate'] = bonus_chip[0].strip()
            
            # 拥有状态
            ownership_badge = image_div.xpath(".//span[@class='medal-card-badge unowned']/text()")
            if ownership_badge:
                medal['purchase_status'] = ownership_badge[0].strip()
            else:
                # 检查是否已拥有
                ownership_owned = image_div.xpath(".//span[@class='medal-card-badge owned']/text()")
                if ownership_owned:
                    medal['purchase_status'] = ownership_owned[0].strip()
            
            # 获取medal-card-body区域
            body_div = card.xpath(".//div[@class='medal-card-body']")
            if not body_div:
                logger.warning("未找到medal-card-body区域")
                return None
            body_div = body_div[0]
            
            # 名称
            title = body_div.xpath(".//h3[@class='medal-card-title']/text()")
            if title:
                medal['name'] = title[0].strip()
            
            # 描述
            description = body_div.xpath(".//div[@class='medal-card-description']/text()")
            if description:
                medal['description'] = description[0].strip()
            
            # 解析属性表格 (medal-meta-item)
            meta_items = body_div.xpath(".//div[@class='medal-card-meta']//div[@class='medal-meta-item']")
            for item in meta_items:
                label = item.xpath(".//span/text()")
                value = item.xpath(".//strong/text()")
                
                if label and value:
                    label_text = label[0].strip()
                    value_text = value[0].strip()
                    
                    if label_text == "价格":
                        try:
                            medal['price'] = int(value_text.replace(',', ''))
                        except ValueError:
                            medal['price'] = 0
                    elif label_text == "购买后有效期(天)":
                        medal['validity'] = value_text
                    elif label_text == "库存":
                        medal['stock'] = value_text
                    elif label_text == "可购买时间":
                        # 解析销售时间，格式：不限 ~ 不限 或 2024-01-01 ~ 2024-12-31
                        if "~" in value_text:
                            times = value_text.split("~")
                            if len(times) == 2:
                                medal['saleBeginTime'] = times[0].strip()
                                medal['saleEndTime'] = times[1].strip()
            
            # 获取购买状态按钮
            action_div = card.xpath(".//div[@class='medal-card-actions']")
            if action_div:
                buy_btn = action_div[0].xpath(".//input[@type='button']/@value")
                if buy_btn:
                    # 如果之前没有从badge获取到状态，从按钮获取
                    if 'purchase_status' not in medal or not medal['purchase_status']:
                        medal['purchase_status'] = buy_btn[0]
            
            # 站点信息
            medal['site'] = site_name
            # 货币单位
            medal['currency'] = '魔力值'
            # 分组信息
            if group_name:
                medal['group'] = group_name
            
            return self._format_medal_data(medal)
            
        except Exception as e:
            logger.error(f"处理勋章项数据时发生错误: {str(e)}")
            return None
