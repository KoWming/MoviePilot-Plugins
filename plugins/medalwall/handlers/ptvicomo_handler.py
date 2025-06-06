from typing import Dict, List
from app.log import logger
from lxml import etree
from .base import BaseMedalSiteHandler
from urllib.parse import parse_qs, urlparse

class PtvicomoMedalHandler(BaseMedalSiteHandler):
    """象站站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为ptvicomo.net站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "ptvicomo" in site_name or "ptvicomo" in site_url or "象站" in site_name or "象站" in site_url

    def fetch_medals(self, site) -> List[Dict]:
        """获取象站站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            # 获取所有页面的勋章数据
            medals = []
            current_page = 0
            
            while True:
                # 构建分页URL
                url = f"{site_url.rstrip('/')}/medal.php"
                if current_page > 0:
                    url = f"{url}?page={current_page}"
                
                logger.info(f"正在获取第 {current_page + 1} 页勋章数据，URL: {url}")
                
                # 发送请求获取勋章页面
                res = self._request_with_retry(
                    url=url,
                    cookies=site_cookie
                )
                
                if not res:
                    logger.error(f"请求勋章页面失败！站点：{site_name}")
                    break
                    
                # 使用lxml解析HTML
                html = etree.HTML(res.text)
                
                # 获取所有勋章项
                medal_items = html.xpath("//div[@class='medalItem']")
                if not medal_items:
                    logger.error("未找到勋章数据！")
                    break
                
                logger.info(f"当前页面找到 {len(medal_items)} 个勋章")
                
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
                next_page = html.xpath("//p[@class='nexus-pagination']//a[contains(., '下一页')]")
                if not next_page:
                    logger.info("未找到下一页链接，已到达最后一页")
                    break
                
                logger.info("找到下一页链接，准备获取下一页数据")
                    
                # 从href中提取页码
                next_href = next_page[0].get('href')
                if not next_href:
                    logger.error("下一页链接没有href属性")
                    break
                
                logger.info(f"下一页链接: {next_href}")
                    
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
            logger.error(f"处理象站站点勋章数据时发生错误: {str(e)}")
            return []

    def _process_medal_item(self, item, site_name: str, site_url: str) -> Dict:
        """处理单个勋章项数据"""
        medal = {}
        
        # 图片
        img = item.xpath(".//img[@class='medalPic']/@src")
        if img:
            img_url = img[0]
            # 如果不是http/https开头，补全为完整站点URL
            if not img_url.startswith('http'):
                from urllib.parse import urljoin
                img_url = urljoin(site_url + '/', img_url.lstrip('/'))
            medal['imageSmall'] = img_url
            
        # 名称
        name = item.xpath(".//div[contains(@style, 'font-size: 14px') and contains(@style, 'font-weight: 700')]/text()")
        if name:
            medal['name'] = name[0].strip()
            
        # 描述
        description = item.xpath(".//div[@class='medalText']/text()")
        if description:
            medal['description'] = description[0].strip()
            
        # 购买状态
        buy_btn = item.xpath(".//input[@type='button']/@value")
        if buy_btn:
            medal['purchase_status'] = buy_btn[0]
            
        # 解析其他属性
        medal_text = item.xpath(".//div[@class='medalText']")[0]
        for line in medal_text.xpath(".//text()"):
            line = line.strip()
            if not line:
                continue
                
            if "开售时间" in line:
                medal['saleBeginTime'] = line.replace("开售时间", "").strip()
            elif "停售时间" in line:
                medal['saleEndTime'] = line.replace("停售时间", "").strip()
            elif "有效期" in line:
                medal['validity'] = line.replace("有效期", "").strip()
            elif "象草加成" in line:
                medal['bonus_rate'] = line.replace("象草加成", "").strip()
            elif "价格" in line:
                price_text = line.replace("价格", "").strip().replace(',', '')
                try:
                    medal['price'] = int(price_text)
                except ValueError:
                    medal['price'] = 0
            elif "库存" in line:
                medal['stock'] = line.replace("库存", "").strip()
                
        # 站点信息
        medal['site'] = site_name
        
        return self._format_medal_data(medal) 