import re
from typing import Dict, List
from app.log import logger
from lxml import etree
from .base import BaseMedalSiteHandler
from urllib.parse import parse_qs, urlparse

class LongptMedalHandler(BaseMedalSiteHandler):
    """LongPT 站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为 LongPT 站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "longpt" in site_name or "longpt" in site_url

    def fetch_medals(self, site) -> List[Dict]:
        """获取 LongPT 站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            medals = []
            current_page = 0
            
            while True:
                # 构建分页 URL
                url = f"{site_url.rstrip('/')}/medal.php"
                logger.info(f"正在获取【{site_name}】站点勋章数据")

                if current_page > 0:
                    url = f"{url}?page={current_page}"
                
                logger.info(f"正在获取第 {current_page + 1} 页勋章数据")
                
                # 发送请求获取勋章页面
                res = self._request_with_retry(
                    url=url,
                    cookies=site_cookie
                )
                
                if not res:
                    logger.error(f"请求勋章页面失败！站点：{site_name}")
                    break
                    
                # 使用 lxml 解析 HTML
                html = etree.HTML(res.text)
                
                # 获取勋章卡片容器
                medal_cards = html.xpath("//div[@class='medal-card']")
                if not medal_cards:
                    logger.error("未找到勋章卡片！")
                    break
                
                logger.info(f"当前页面找到 {len(medal_cards)} 个勋章")
                
                # 处理当前页面的勋章数据
                for card in medal_cards:
                    try:
                        medal = self._process_medal_card(card, site_name, site_url)
                        if medal:
                            medals.append(medal)
                    except Exception as e:
                        logger.error(f"处理勋章卡片时发生错误：{str(e)}")
                        continue
                
                # 检查是否有下一页
                next_page = html.xpath("//p[@class='nexus-pagination']//a[contains(., '下一页')]")
                if not next_page:
                    logger.info("未找到下一页链接，已到达最后一页")
                    break
                
                logger.info("找到下一页链接，准备获取下一页数据")
                    
                # 从 href 中提取页码
                next_href = next_page[0].get('href')
                if not next_href:
                    logger.error("下一页链接没有 href 属性")
                    break
                
                logger.info(f"下一页链接: {next_href}")
                    
                # 解析 URL 参数
                try:
                    parsed = urlparse(next_href)
                    params = parse_qs(parsed.query)
                    next_page_num = int(params.get('page', [0])[0])
                    
                    logger.info(f"解析到下一页页码: {next_page_num}")
                    
                    if next_page_num <= current_page:
                        logger.info("已到达最后一页")
                        break
                    current_page = next_page_num
                except (ValueError, IndexError, AttributeError) as e:
                    logger.error(f"解析页码时发生错误: {str(e)}")
                    break
            
            logger.info(f"共获取到 {len(medals)} 个勋章数据")
            return medals
            
        except Exception as e:
            logger.error(f"处理 LongPT 站点勋章数据时发生错误: {str(e)}")
            return []

    def _process_medal_card(self, card, site_name: str, site_url: str) -> Dict:
        """处理单个勋章卡片数据"""
        medal = {}
        
        # 图片
        img = card.xpath(".//img[@class='medal-image']/@src")
        if img:
            img_url = img[0]
            # 如果不是 http/https 开头，补全为完整站点 URL
            if not img_url.startswith('http'):
                from urllib.parse import urljoin
                img_url = urljoin(site_url + '/', img_url.lstrip('/'))
            medal['imageSmall'] = img_url
            
        # 名称
        name = card.xpath(".//h2[@class='medal-name']/text()")
        if name:
            medal['name'] = name[0].strip()
            
        # 描述
        description = card.xpath(".//div[@class='medal-description']/text()")
        if description:
            medal['description'] = description[0].strip()
            
        # 解析详细信息
        detail_items = card.xpath(".//div[@class='detail-item']")
        for item in detail_items:
            label_elem = item.xpath(".//span[@class='detail-label']/text()")
            value_elem = item.xpath(".//span[@class='detail-value']")
            
            if not label_elem or not value_elem:
                continue
                
            label = label_elem[0].strip()
            # 获取 value 的所有文本内容（包括 <br> 分隔的）
            value_texts = value_elem[0].xpath(".//text()")
            value = ' '.join([v.strip() for v in value_texts if v.strip()])
            
            # 根据标签分配字段
            if "可购买时间" in label:
                # 解析时间范围 "2026-01-01 00:00:01 ~ 不限"
                time_parts = value.split('~')
                if len(time_parts) >= 2:
                    medal['saleBeginTime'] = time_parts[0].strip()
                    medal['saleEndTime'] = time_parts[1].strip()
                else:
                    medal['saleBeginTime'] = value
                    medal['saleEndTime'] = ''
                    
            elif "购买后有效期" in label or "有效期" in label:
                medal['validity'] = value
                
            elif "魔力加成" in label or "加成" in label:
                # 提取百分比或数字
                medal['bonus_rate'] = value
                
            elif "价格" in label:
                # 移除逗号并转换为整数
                price_text = value.replace(',', '').replace('，', '')
                try:
                    medal['price'] = int(price_text)
                except ValueError:
                    medal['price'] = 0
                    
            elif "库存" in label:
                medal['stock'] = value
                
            elif "手续费" in label:
                # 暂时不使用手续费字段
                pass
                
        # 购买状态 - 从按钮判断
        buy_btn = card.xpath(".//input[@type='button' and contains(@class, 'buy')]/@value")
        if buy_btn:
            medal['purchase_status'] = buy_btn[0]
        else:
            # 检查是否有已购买或禁用状态
            disabled_btn = card.xpath(".//input[@type='button' and @disabled]/@value")
            if disabled_btn:
                medal['purchase_status'] = disabled_btn[0]
            else:
                medal['purchase_status'] = '可购买'
            
        # 站点信息
        medal['site'] = site_name
        
        return self._format_medal_data(medal)
