from typing import Dict, List
from app.log import logger
from lxml import etree
from .base import BaseMedalSiteHandler
from urllib.parse import urljoin, parse_qs, urlparse

class HHanMedalHandler(BaseMedalSiteHandler):
    """HHan站点勋章处理器"""
    
    # 备用域名列表
    FALLBACK_DOMAINS = ['hhanclub.top']
    
    def match(self, site) -> bool:
        """判断是否为HHan站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "憨憨" in site_name or "憨憨" in site_url

    def _get_medals_page(self, url: str, cookies: str) -> str:
        """获取勋章页面内容，支持域名切换"""
        # 首先尝试原始URL
        res = self._request_with_retry(url=url, cookies=cookies)
        if res:
            return res.text
            
        # 如果原始URL失败，尝试备用域名
        parsed_url = urlparse(url)
        
        for fallback_domain in self.FALLBACK_DOMAINS:
            # 构建新的URL，保持path和query参数不变
            new_url = f"{parsed_url.scheme}://{fallback_domain}{parsed_url.path}"
            if parsed_url.query:
                new_url += f"?{parsed_url.query}"
                
            logger.info(f"尝试使用备用域名访问: {new_url}")
            res = self._request_with_retry(url=new_url, cookies=cookies)
            if res:
                return res.text
                
        return None

    def fetch_medals(self, site) -> List[Dict]:
        """获取HHan站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            # 获取所有页面的勋章数据
            medals = []
            current_page = 0  # 从第0页开始
            
            while True:
                # 构建分页URL
                url = f"{site_url.rstrip('/')}/medal.php"
                logger.info(f"正在获取【{site_name}】站点勋章数据")
                
                if current_page > 0:
                    url = f"{url}?page={current_page}"
                
                logger.info(f"正在获取第 {current_page + 1} 页勋章数据")
                
                # 发送请求获取勋章页面，支持域名切换
                page_content = self._get_medals_page(url, site_cookie)
                
                if not page_content:
                    logger.error(f"请求勋章页面失败！站点：{site_name}")
                    break
                    
                # 使用lxml解析HTML
                html = etree.HTML(page_content)
                
                # 获取勋章列表
                medal_items = html.xpath("//div[contains(@class, 'medal-table') and not(contains(@class, 'bg-[#4F5879]'))]")
                if not medal_items:
                    logger.error("未找到勋章列表！")
                    break
                
                # 处理当前页面的勋章数据
                for item in medal_items:
                    try:
                        medal = self._process_medal_item(item, site_name, site_url)
                        if medal:
                            medals.append(medal)
                    except Exception as e:
                        logger.error(f"处理勋章数据时发生错误：{str(e)}")
                        continue
                
                # 检查是否有下一页
                next_page = html.xpath("//a[contains(@class, 'bg-[#F29D38]') and not(@disabled)]")
                if not next_page:
                    logger.info("未找到下一页链接，已到达最后一页")
                    break
                
                logger.info("找到下一页链接，准备获取下一页数据")
                    
                # 从href中提取页码
                next_href = next_page[0].get('href')
                if not next_href:
                    break
                    
                # 解析URL参数
                try:
                    parsed = urlparse(next_href)
                    params = parse_qs(parsed.query)
                    next_page_num = int(params.get('page', [0])[0])
                    
                    logger.info(f"解析到下一页页码: {next_page_num}")
                    
                    if next_page_num <= current_page:
                        logger.info("下一页页码小于等于当前页码，已到达最后一页")
                        break  # 防止循环
                    current_page = next_page_num
                except (ValueError, IndexError, AttributeError) as e:
                    logger.error(f"解析页码时发生错误: {str(e)}")
                    break
            
            logger.info(f"共获取到 {len(medals)} 个勋章数据")
            return medals
            
        except Exception as e:
            logger.error(f"处理HHan站点勋章数据时发生错误: {str(e)}")
            return []

    def _process_medal_item(self, item, site_name: str, site_url: str) -> Dict:
        """处理单个勋章数据"""
        medal = {}
        
        # 图片
        img = item.xpath(".//img/@src")
        if img:
            img_url = img[0]
            # 如果不是http/https开头，补全为完整站点URL
            if not img_url.startswith('http'):
                img_url = urljoin(site_url, img_url.lstrip('/'))
            medal['imageSmall'] = img_url
            
        # 名称和描述
        name_div = item.xpath(".//div[contains(@class, 'text-[18px]')]")
        if name_div:
            medal['name'] = name_div[0].text.strip()
            
        desc_div = item.xpath(".//div[contains(@class, 'text-[#9B9B9B]')]")
        if desc_div:
            medal['description'] = desc_div[0].text.strip()
            
        # 价格
        price_div = item.xpath(".//div[contains(text(), ',')]")
        if price_div:
            price_text = price_div[0].text.strip().replace(',', '')
            try:
                medal['price'] = int(price_text)
            except ValueError:
                medal['price'] = 0
                
        # 库存
        stock_div = item.xpath(".//div[contains(text(), '无限') or contains(text(), '0') or contains(text(), '1') or contains(text(), '2') or contains(text(), '3') or contains(text(), '4') or contains(text(), '5') or contains(text(), '6') or contains(text(), '7') or contains(text(), '8') or contains(text(), '9')]")
        if stock_div:
            medal['stock'] = stock_div[0].text.strip()
            
        # 魔力加成
        bonus_div = item.xpath(".//div[contains(text(), '%')]")
        if bonus_div:
            medal['bonus_rate'] = bonus_div[0].text.strip()
            
        # 尝试多种方式匹配有效期
        validity_div = item.xpath(".//div[contains(text(), '永久有效') or contains(text(), '天') or (contains(text(), '365') or contains(text(), '180') or contains(text(), '90') or contains(text(), '30'))]")
        
        # 如果上面的方式没找到，尝试更宽泛的匹配
        if not validity_div:
            # 查找所有包含数字的div（可能是有效期）
            all_divs = item.xpath(".//div[text()]")
            for div in all_divs:
                text = div.text.strip() if div.text else ""
                # 检查是否包含"天"、"有效"、或纯数字
                if any(keyword in text for keyword in ['天', '有效', '期限']) or text.isdigit():
                    validity_div = [div]
                    logger.info(f"通过宽泛匹配找到有效期字段: {text}")
                    break
        
        if validity_div:
            validity_text = validity_div[0].text.strip() if validity_div[0].text else ""
            medal['validity'] = validity_text
            logger.debug(f"勋章 {medal.get('name', 'Unknown')} 的有效期: {validity_text}")
        else:
            logger.warning(f"勋章 {medal.get('name', 'Unknown')} 未找到有效期字段")
            
        # 购买状态
        buy_btn = item.xpath(".//input[@type='button']/@value")
        if buy_btn:
            medal['purchase_status'] = buy_btn[0]
            
        # 赠送状态
        gift_btn = item.xpath(".//input[@type='button'][2]/@value")
        if gift_btn:
            medal['gift_status'] = gift_btn[0]
            
        # 站点信息
        medal['site'] = site_name
        
        return self._format_medal_data(medal) 