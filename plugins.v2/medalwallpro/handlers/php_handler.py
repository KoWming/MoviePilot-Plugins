import re
from typing import Dict, List, Optional
from app.log import logger
from app.core.config import settings
from lxml import etree
from .base import BaseMedalSiteHandler
from app.helper.browser import PlaywrightHelper
from urllib.parse import parse_qs, urlparse

class PhpMedalHandler(BaseMedalSiteHandler):
    """PHP站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为PHP站点"""
        # 检查站点是否已被其他处理器匹配
        if hasattr(site, 'name'):
            from . import handler_manager
            if handler_manager.is_site_matched(site.name):
                return False
        return True

    def _get_page_source_via_browser(self, url: str, cookie_str: str, ua: str = None) -> Optional[str]:
        """通过PlaywrightHelper获取页面源码 (支持 FlareSolverr/Playwright)"""

        # 构造代理配置
        proxies = None
        if self._use_proxy and hasattr(settings, 'PROXY') and settings.PROXY:
            try:
                proxy_url = None
                if isinstance(settings.PROXY, dict):
                    proxy_url = settings.PROXY.get('http') or settings.PROXY.get('https')
                elif isinstance(settings.PROXY, str):
                    proxy_url = settings.PROXY
                
                if proxy_url:
                    proxies = {"server": proxy_url}
            except Exception as e:
                logger.warning(f"解析代理配置失败: {e}")

        try:
            return PlaywrightHelper().get_page_source(
                url=url,
                cookies=cookie_str,
                ua=ua,
                proxies=proxies
            )
        except Exception as e:
            logger.error(f"BrowserHelper 请求异常: {e}")
            return None

    def fetch_medals(self, site) -> List[Dict]:
        """获取PHP站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            site_ua = getattr(site, 'ua', None)
            site_render = getattr(site, 'render', False)
            
            # 版本调试日志
            logger.warning(f"正在处理站点: {site_name}")
            
            # 获取所有页面的勋章数据
            medals = []
            current_page = 0
            
            while True:
                # 构建分页URL
                url = f"{site_url.rstrip('/')}/medal.php"
                logger.info(f"正在获取【{site_name}】站点勋章数据")

                if current_page > 0:
                    url = f"{url}?page={current_page}"
                
                logger.info(f"正在获取第 {current_page + 1} 页勋章数据")
                
                # 尝试通过 BrowserHelper 获取
                html_text = None
                if site_render:
                    html_text = self._get_page_source_via_browser(url, site_cookie, site_ua)
                
                # 如果 Helper 失败 (返回 None)，回退到原生请求
                if not html_text:
                    res = self._request_with_retry(
                        url=url,
                        cookies=site_cookie,
                        ua=site_ua
                    )
                    if not res:
                        logger.error(f"请求勋章页面失败！站点：{site_name}")
                        break
                    html_text = res.text
                    
                # 使用lxml解析HTML
                html = etree.HTML(html_text)
                
                # 获取勋章表格
                # 策略 1: 原有 NexusPHP 结构
                medal_tables = html.xpath("//table[@class='main']//table[contains(@border, '1')]")
                
                # 策略 2: 根据表头内容定位 (兼容 HDTime 等)
                if not medal_tables:
                    medal_tables = html.xpath("//table[.//td[contains(text(), '图片')] and .//td[contains(text(), '描述')]]")
                
                if not medal_tables:
                    logger.error("未找到勋章表格！")
                    break
                
                # 过滤掉表头行
                rows = medal_tables[0].xpath(".//tr")
                data_rows = []
                for row in rows:
                    # 如果包含 th 或 class='colhead' 或 第一列包含 '图片'，认为是表头
                    if row.xpath(".//th") or row.xpath(".//*[contains(@class, 'colhead')]") or row.xpath(".//td[contains(text(), '图片')]"):
                        continue
                    data_rows.append(row)

                current_page_count = 0
                for row in data_rows:
                    try:
                        medal = self._process_medal_row(row, site_name, site_url)
                        if medal:
                            medals.append(medal)
                            current_page_count += 1
                    except Exception as e:
                        logger.error(f"处理行数据时发生错误：{str(e)}")
                        continue
                
                logger.info(f"当前页面找到 {current_page_count} 个勋章")
                
                next_page = html.xpath("//p[@class='nexus-pagination']//a[contains(., '下一页')]")
                next_href = None
                if next_page:
                    next_href = next_page[0].get('href')
                else:
                    pagination_nodes = html.xpath("//p[@class='nexus-pagination']/*")
                    found_current = False
                    for node in pagination_nodes:
                        tag = node.tag.lower()
                        if tag == 'font':
                            found_current = True
                        elif found_current and tag == 'a':
                            next_href = node.get('href')
                            break
                if not next_href:
                    logger.info("未找到下一页链接，已到达最后一页")
                    break
                try:
                    parsed = urlparse(next_href)
                    params = parse_qs(parsed.query)
                    next_page_num = int(params.get('page', [0])[0])
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
            logger.error(f"处理PHP站点勋章数据时发生错误: {str(e)}")
            return []

    def fetch_user_medals(self, site) -> List[Dict]:
        """获取用户已拥有的勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            site_ua = getattr(site, 'ua', None)
            site_render = getattr(site, 'render', False)

            # 1. 获取 User ID
            user_id = self._get_user_id(site_url, site_cookie, site_ua, site_render)
            if not user_id:
                logger.error(f"无法获取站点 {site_name} 的用户ID")
                return []
            
            logger.info(f"获取到用户ID: {user_id}")
            
            # 2. 获取详情页
            detail_url = f"{site_url.rstrip('/')}/userdetails.php?id={user_id}"
            logger.info("正在获取用户详情页")
            
            # 优先尝试 BrowserHelper
            html_text = None
            if site_render:
                html_text = self._get_page_source_via_browser(detail_url, site_cookie, site_ua)
            
            if not html_text:
                res = self._request_with_retry(
                    url=detail_url,
                    cookies=site_cookie,
                    ua=site_ua
                )
                if not res:
                    logger.error(f"请求用户详情页失败！站点：{site_name}")
                    return []
                html_text = res.text
                
            # 3. 解析勋章
            html = etree.HTML(html_text)
            medals = self._parse_user_medals(html, site_name, site_url)
            
            logger.info(f"共获取到 {len(medals)} 个用户已拥有勋章")
            return medals
            
        except Exception as e:
            logger.error(f"处理用户勋章数据时发生错误: {str(e)}")
            return []

    def _get_user_id(self, site_url: str, cookies: str, ua: str = None, render: bool = False) -> Optional[str]:
        """从首页获取用户ID"""
        try:
            index_url = f"{site_url.rstrip('/')}/index.php"
            
            # 优先尝试 BrowserHelper
            html_text = None
            if render:
                html_text = self._get_page_source_via_browser(index_url, cookies, ua)
            
            if not html_text:
                res = self._request_with_retry(
                    url=index_url,
                    cookies=cookies,
                    ua=ua
                )
                if not res:
                    return None
                html_text = res.text
            
            match = re.search(r"userdetails\.php\?id=(\d+)", html_text)
            if match:
                return match.group(1)
            
            return None
        except Exception:
            return None

    def _parse_user_medals(self, html, site_name: str, site_url: str) -> List[Dict]:
        """解析用户详情页的勋章"""
        medals = []
        try:
            medal_forms = html.xpath('//form[.//input[@id="save-user-medal-btn"]]//div[contains(@style, "float: left") or contains(@style, "flex-direction: column")]')
            
            if medal_forms:
                logger.debug("使用表单模式解析用户勋章")
                for div in medal_forms:
                    try:
                        medal = {}
                        
                        # 图片
                        imgs = div.xpath('.//img[@class="preview"]')
                        if not imgs:
                            imgs = div.xpath('.//img')
                        if not imgs:
                            continue
                        
                        img_node = imgs[0]
                        img_src = img_node.get('src')
                        if not img_src:
                            continue
                            
                        # 处理图片URL
                        if not img_src.startswith('http'):
                            from urllib.parse import urljoin
                            img_src = urljoin(site_url + '/', img_src.lstrip('/'))
                        
                        medal['imageSmall'] = img_src
                        medal['name'] = img_node.get('title', '')

                        info_texts = div.xpath('.//span/text() | ./div[last()]//text()')
                        texts_str = ' '.join([t.strip() for t in info_texts if t.strip()])
                        
                        # 过期时间
                        expire_match = re.search(r"过期时间[：:]\s*(.+?)(?:\s+魔力|$)", texts_str)
                        if expire_match:
                            medal['validity'] = expire_match.group(1).strip()
                        else:
                            medal['validity'] = "永久有效"
                            
                        # 魔力加成
                        bonus_match = re.search(r"魔力加成(?:系数)?[：:]\s*([\d.]+)", texts_str)
                        if bonus_match:
                            medal['bonus_rate'] = bonus_match.group(1).strip()
                        
                        medal['site'] = site_name
                        medal['purchase_status'] = "已拥有"
                        
                        medals.append(self._format_medal_data(medal))
                    except Exception as e:
                        logger.warning(f"解析单个勋章出错: {e}")
                        continue
            else:
                logger.debug("使用图标模式解析用户勋章")
                medal_imgs = html.xpath('//h1//img[contains(@class, "nexus-username-medal-big")] | //h1//img[contains(@class, "nexus-username-medal")]')
                
                if not medal_imgs:
                     medal_imgs = html.xpath('//h1/following-sibling::*[not(self::table)]//img[contains(@class, "nexus-username-medal")]')
                
                if not medal_imgs:
                    medal_imgs = html.xpath('(//h1/preceding-sibling::span | //h1/following-sibling::span)[not(ancestor::table)]//img[contains(@class, "nexus-username-medal")]')
                
                for img in medal_imgs:
                    try:
                        medal = {}
                        img_src = img.get('src')
                        if not img_src:
                            continue
                            
                        if not img_src.startswith('http'):
                            from urllib.parse import urljoin
                            img_src = urljoin(site_url + '/', img_src.lstrip('/'))
                            
                        medal['imageSmall'] = img_src
                        medal['name'] = img.get('title', '')
                        medal['site'] = site_name
                        medal['purchase_status'] = "已拥有"
                        medal['validity'] = "未知"
                        
                        medals.append(self._format_medal_data(medal))
                    except Exception as e:
                        continue
                        
            return medals
        except Exception as e:
            logger.error(f"解析用户勋章HTML出错: {e}")
            return []

    def _process_medal_row(self, row, site_name: str, site_url: str) -> Dict:
        """处理单个勋章行数据"""
        cells = row.xpath(".//td")
        if len(cells) < 9:
            return None
        
        offset = 0
        first_cell_text = ''.join(cells[0].xpath('.//text()')).strip()
        if first_cell_text.isdigit():
            offset = 1
            if len(cells) < 10:
                return None
            
        medal = {}
        
        # 图片
        img = cells[0 + offset].xpath(".//img/@src")
        if img:
            img_url = img[0]
            if not img_url.startswith('http'):
                from urllib.parse import urljoin
                img_url = urljoin(site_url + '/', img_url.lstrip('/'))
            medal['imageSmall'] = img_url
            
        # 名称和描述
        name = ''
        description = ''
        h1_nodes = cells[1 + offset].xpath('./h1')
        if h1_nodes:
            name = h1_nodes[0].text.strip() if h1_nodes[0].text else ''
            description = h1_nodes[0].tail.strip() if h1_nodes[0].tail and h1_nodes[0].tail.strip() else ''
        else:
            description = ''.join(cells[1 + offset].xpath('.//text()')).strip()
        medal['name'] = name
        medal['description'] = description
        
        # 可购买时间
        time_text = cells[2 + offset].xpath(".//text()")
        if time_text:
            time_text = [t.strip() for t in time_text if t.strip()]
            if len(time_text) >= 2:
                medal['saleBeginTime'] = time_text[0]
                medal['saleEndTime'] = time_text[1]
                
        # 有效期
        validity = cells[3 + offset].xpath(".//text()")
        if validity:
            medal['validity'] = validity[0].strip()
            
        # 魔力加成
        bonus = cells[4 + offset].xpath(".//text()")
        if bonus:
            medal['bonus_rate'] = bonus[0].strip()
            
        # 价格
        price = cells[5 + offset].xpath(".//text()")
        if price:
            price_text = price[0].strip().replace(',', '')
            try:
                medal['price'] = int(price_text)
            except ValueError:
                medal['price'] = 0
                
        # 库存
        stock = cells[6 + offset].xpath(".//text()")
        if stock:
            medal['stock'] = stock[0].strip()
            
        # 购买状态
        buy_btn = cells[7 + offset].xpath(".//input/@value")
        if buy_btn:
            medal['purchase_status'] = buy_btn[0]
            
        # 赠送状态
        gift_btn = cells[8 + offset].xpath(".//input/@value")
        if gift_btn:
            medal['gift_status'] = gift_btn[0]
            
        # 站点信息
        medal['site'] = site_name
        
        return self._format_medal_data(medal) 