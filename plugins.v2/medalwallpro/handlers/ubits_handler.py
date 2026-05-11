from typing import Dict, List
import re
from urllib.parse import urljoin

from lxml import etree

from app.log import logger
from .base import BaseMedalSiteHandler

class UbitsMedalHandler(BaseMedalSiteHandler):
    """UBits站点勋章处理器"""

    def should_use_image_proxy(self) -> bool:
        return True
    
    def match(self, site) -> bool:
        """判断是否为UBits站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "ubits" in site_name or "ubits" in site_url or "ubits.club" in site_url

    def fetch_medals(self, site) -> List[Dict]:
        """获取UBits站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            all_medals = []
            page = 0  # UBits分页从0开始
            
            logger.info(f"正在获取【{site_name}】站点勋章数据")

            while True:
                # 构建勋章页面URL
                if page == 0:
                    url = f"{site_url.rstrip('/')}/medal.php"
                else:
                    url = f"{site_url.rstrip('/')}/medal.php?page={page}"
                
                logger.info(f"正在获取第 {page + 1} 页勋章数据")
                
                # 发送请求获取勋章页面
                res = self._request_with_retry(
                    url=url,
                    cookies=site_cookie
                )
                
                if not res:
                    logger.error(f"请求勋章页面失败! 站点: {site_name}")
                    break
                    
                # 使用lxml解析HTML
                html = etree.HTML(res.text)
                
                # 获取所有勋章卡片
                medal_cards = html.xpath("//div[@class='medal-cards']//div[contains(@class, 'medal-card')]")
                if not medal_cards:
                    # 没有找到勋章卡片,说明已经到最后一页
                    logger.info(f"第 {page + 1} 页没有勋章数据,停止分页")
                    break
                
                logger.info(f"第 {page + 1} 页找到 {len(medal_cards)} 个勋章数据")
                
                # 处理当前页勋章数据
                for card in medal_cards:
                    try:
                        medal = self._process_medal_item(card, site_name, site_url, site)
                        if medal:
                            all_medals.append(medal)
                    except Exception as e:
                        logger.error(f"处理勋章数据时发生错误: {str(e)}")
                        continue
                
                # 检查是否还有下一页
                pagination_script = html.xpath("//script[contains(text(), 'var maxpage')]/text()")
                if pagination_script:
                    match = re.search(r'var maxpage=(\d+)', pagination_script[0])
                    if match:
                        max_page = int(match.group(1))
                        if page >= max_page:
                            logger.info(f"已达到最大页数 {max_page + 1},停止分页")
                            break
                
                page += 1
                
                # 防止无限循环,最多获取10页
                if page >= 10:
                    logger.warning("已达到最大分页限制(10页),停止分页")
                    break
            
            logger.info(f"共获取到 {len(all_medals)} 个勋章数据")
            return all_medals
            
        except Exception as e:
            logger.error(f"处理UBits站点勋章数据时发生错误: {str(e)}")
            return []

    def _process_medal_item(self, card, site_name: str, site_url: str, site) -> Dict:
        """处理单个勋章项数据"""
        medal = {}
        
        # 勋章图片
        img = card.xpath('.//img[@class="medal-image"]/@src')
        if img:
            img_url = img[0]
            if not img_url.startswith('http'):
                img_url = urljoin(site_url + '/', img_url.lstrip('/'))
            
            medal['imageSmall'] = img_url
        
        # 记录原始URL用于缓存
        medal['original_image_url'] = img_url
        
        # 从图片alt属性获取名称(备用)
        img_alt = card.xpath('.//img[@class="medal-image"]/@alt')
        if img_alt:
            medal['name'] = img_alt[0].strip()
        
        # 勋章名称
        name = card.xpath('.//div[@class="medal-name"]/text()')
        if name:
            medal['name'] = name[0].strip()
        
        # 获取信息字段
        info_divs = card.xpath('.//div[@class="medal-info"]/div')
        
        if len(info_divs) >= 5:
            # 第1个字段: 可购买时间
            time_texts = info_divs[0].xpath('.//text()[normalize-space()]')
            if len(time_texts) > 1:
                time_value = ''.join(time_texts[1:]).strip()
                if ' 至 ' in time_value:
                    times = time_value.split(' 至 ')
                    if len(times) >= 2:
                        medal['saleBeginTime'] = times[0].strip()
                        medal['saleEndTime'] = times[1].strip()
            
            # 第2个字段: 购买后有效期
            validity_texts = info_divs[1].xpath('.//text()[normalize-space()]')
            if len(validity_texts) > 1:
                medal['validity'] = ''.join(validity_texts[1:]).strip()
            
            # 第3个字段: 魔力加成
            bonus_texts = info_divs[2].xpath('.//text()[normalize-space()]')
            if len(bonus_texts) > 1:
                medal['bonus_rate'] = ''.join(bonus_texts[1:]).strip()
            
            # 第4个字段: 价格
            price_texts = info_divs[3].xpath('.//text()[normalize-space()]')
            if len(price_texts) > 1:
                price_value = ''.join(price_texts[1:]).strip()
                try:
                    medal['price'] = int(price_value.replace(',', '').strip())
                except ValueError:
                    medal['price'] = 0
            
            # 第5个字段: 手续费(可选,暂不使用)
            # fee_texts = info_divs[4].xpath('.//text()[normalize-space()]')
        
        
        # 购买状态判断
        card_class = card.get('class', '')
        
        # 检查是否有库存紧张标签
        limited_tag = card.xpath('.//div[@class="limited-tag"]')
        if limited_tag:
            medal['stock_status'] = '库存紧张'
        
        # 判断拥有状态
        if 'purchased' in card_class and 'unpurchased' not in card_class:
            medal['purchase_status'] = '已拥有'
        else:
            # 从购买按钮获取详细状态
            buy_btn = card.xpath('.//input[contains(@class, "btn") and contains(@class, "buy")]')
            if buy_btn:
                button_value = buy_btn[0].get('value', '')
                button_disabled = buy_btn[0].get('disabled') is not None
                
                # 根据按钮文本设置状态
                if '需要更多魔力值' in button_value:
                    medal['purchase_status'] = '需要更多魔力值'
                elif '仅授予' in button_value:
                    medal['purchase_status'] = '仅授予'
                elif '已过可购买时间' in button_value:
                    medal['purchase_status'] = '已过可购买时间'
                elif '购买' in button_value and not button_disabled:
                    medal['purchase_status'] = '购买'
                elif '售罄' in button_value or '售完' in button_value:
                    medal['purchase_status'] = '售罄'
                else:
                    # 其他未知状态，保留按钮文本
                    medal['purchase_status'] = button_value if button_value else '售罄'
            else:
                medal['purchase_status'] = '购买'
        
        # 站点信息
        medal['site'] = site_name
        # UBits使用魔力值
        
        return self._format_medal_data(medal)

    def fetch_user_medals(self, site) -> List[Dict]:
        """获取用户已拥有的勋章"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            logger.info("正在获取用户已拥有勋章数据")
            
            # 先访问首页获取用户ID
            index_url = f"{site_url.rstrip('/')}/index.php"
            index_res = self._request_with_retry(
                url=index_url,
                cookies=site_cookie
            )
            
            if not index_res:
                logger.error(f"请求首页失败! 站点: {site_name}")
                return []
            
            # 解析用户ID
            html = etree.HTML(index_res.text)
            user_link = html.xpath("//a[contains(@href, 'userdetails.php?id=')]/@href")
            
            if not user_link:
                logger.error("无法获取用户ID!")
                return []
            
            # 提取用户ID
            import re
            match = re.search(r'id=(\d+)', user_link[0])
            if not match:
                logger.error("无法解析用户ID!")
                return []
            
            user_id = match.group(1)
            logger.info(f"获取到用户ID: {user_id}")
            
            # 访问用户详情页
            user_url = f"{site_url.rstrip('/')}/userdetails.php?id={user_id}"
            user_res = self._request_with_retry(
                url=user_url,
                cookies=site_cookie
            )
            
            if not user_res:
                logger.error(f"请求用户详情页失败!")
                return []
            
            # 解析用户详情页
            user_html = etree.HTML(user_res.text)
            
            # 获取用户已拥有的勋章卡片
            medal_cards = user_html.xpath("//form[@id='medal-form']//div[@class='medal-card']")
            
            if not medal_cards:
                logger.info(f"用户暂无已拥有勋章")
                return []
            
            logger.info(f"找到 {len(medal_cards)} 个用户已拥有勋章数据")
            
            # 处理勋章数据
            user_medals = []
            for card in medal_cards:
                try:
                    medal = self._process_user_medal_item(card, site_name, site_url, site)
                    if medal:
                        user_medals.append(medal)
                except Exception as e:
                    logger.error(f"处理用户勋章数据时发生错误: {str(e)}")
                    continue
            
            logger.info(f"共获取到 {len(user_medals)} 个用户已拥有勋章")
            return user_medals
            
        except Exception as e:
            logger.error(f"获取UBits用户已拥有勋章失败: {str(e)}")
            return []
    
    def _process_user_medal_item(self, card, site_name: str, site_url: str, site) -> Dict:
        """处理用户详情页的单个勋章项"""
        medal = {}
        
        # 勋章图片
        img = card.xpath('.//img[@class="preview"]/@src')
        if not img:
            img = card.xpath('.//img/@src')
        
        if img:
            img_url = img[0]
            if not img_url.startswith('http'):
                from urllib.parse import urljoin
                img_url = urljoin(site_url + '/', img_url.lstrip('/'))
            
            medal['imageSmall'] = img_url
                
        # 记录原始URL用于缓存
        medal['original_image_url'] = img_url
        
        # 勋章名称
        img_title = card.xpath('.//img/@title')
        if img_title:
            medal['name'] = img_title[0].strip()
        else:
            # 从文本节点获取
            name_div = card.xpath('.//div[contains(@style, "font-weight: 600")]/text()')
            if name_div:
                medal['name'] = name_div[0].strip()
        
        # 从表格中获取信息
        table_rows = card.xpath('.//table//tr')
        
        for row in table_rows:
            cells = row.xpath('./td')
            if len(cells) >= 2:
                label = ''.join(cells[0].xpath('.//text()')).strip()
                value = ''.join(cells[1].xpath('.//text()')).strip()
                
                if '过期时间' in label:
                    medal['validity'] = value
                elif '魔力加成' in label or '加成系数' in label:
                    medal['bonus_rate'] = value
        
        # 设置购买状态为已拥有
        medal['purchase_status'] = '已拥有'
        medal['site'] = site_name
        
        return self._format_medal_data(medal)

