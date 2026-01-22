from typing import Dict, List
from app.log import logger
from lxml import etree
from .base import BaseMedalSiteHandler

class AudiencesMedalHandler(BaseMedalSiteHandler):
    """观众站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为观众站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "观众" in site_name or "观众" in site_url

    def fetch_medals(self, site) -> List[Dict]:
        """获取观众站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            # 构建勋章页面URL
            url = f"{site_url.rstrip('/')}/medal_center.php"
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
            
            # 获取所有勋章项
            medal_items = html.xpath("//form[contains(@action, '?')]")
            if not medal_items:
                logger.error("未找到勋章数据！")
                return []
            
            logger.info(f"找到 {len(medal_items)} 个勋章数据")
            
            # 处理勋章数据
            medals = []
            for item in medal_items:
                try:
                    medal = self._process_medal_item(item, site_name, site_url)
                    if medal:
                        medals.append(medal)
                except Exception as e:
                    logger.error(f"处理勋章数据时发生错误：{str(e)}")
                    continue
            
            logger.info(f"共获取到 {len(medals)} 个勋章数据")
            return medals
            
        except Exception as e:
            logger.error(f"处理Audiences站点勋章数据时发生错误: {str(e)}")
            return []

    def _process_medal_item(self, item, site_name: str, site_url: str) -> Dict:
        """处理单个勋章项数据"""
        medal = {}
        
        # 获取所有 td.colfollow 单元格
        cells = item.xpath(".//td[@class='colfollow']")
        
        if len(cells) < 9:
            logger.warning(f"勋章数据格式异常,列数不足: {len(cells)}")
            return {}
        
        # 第1列: 勋章图片
        img = cells[0].xpath(".//img/@src")
        if img:
            img_url = img[0]
            if not img_url.startswith('http'):
                from urllib.parse import urljoin
                img_url = urljoin(site_url + '/', img_url.lstrip('/'))
            medal['imageSmall'] = img_url
        
        # 从图片中也尝试获取勋章名称 (作为备用)
        img_title = cells[0].xpath(".//img/@title")
        if img_title:
            medal['name'] = img_title[0].strip()
            
        # 第2列: 勋章名称和描述
        # 名称在 h1 标签中
        name = cells[1].xpath(".//h1/text()")
        if name:
            medal['name'] = name[0].strip()
        
        # 描述在文本节点中,需要排除h1中的名称
        desc_parts = []
        for node in cells[1].xpath(".//text()"):
            text = node.strip()
            if text and text != medal.get('name', ''):
                desc_parts.append(text)
        if desc_parts:
            medal['description'] = ' '.join(desc_parts)
            
        # 第3列: 价格
        price_text = cells[2].xpath("./text()")
        if price_text:
            try:
                medal['price'] = int(price_text[0].replace(',', '').strip())
            except ValueError:
                medal['price'] = 0
                
        # 第4列: 库存
        stock_text = cells[3].xpath("./text()")
        if stock_text:
            medal['stock'] = stock_text[0].strip()
            
        # 第5列: 限购
        limit_text = cells[4].xpath("./text()")
        if limit_text:
            medal['limit'] = limit_text[0].strip()
            
        # 第6列: 爆米花加成百分比
        bonus_rate = cells[5].xpath("./text()")
        if bonus_rate:
            medal['bonus_rate'] = bonus_rate[0].strip()
            
        # 第7列: 加成天数
        validity = cells[6].xpath("./text()")
        if validity:
            medal['validity'] = validity[0].strip()
            
        # 第8列: 购买类型
        purchase_type = cells[7].xpath("./text()")
        if purchase_type:
            medal['purchase_type'] = purchase_type[0].strip()
            
        # 第9列: 购买按钮状态
        buy_btn = cells[8].xpath(".//input[@type='submit']")
        if buy_btn:
            # 检查按钮是否被禁用
            disabled = buy_btn[0].get('disabled')
            value = buy_btn[0].get('value', '购买')
            
            if disabled:
                # 根据库存判断状态
                stock = medal.get('stock', '0')
                if stock == '0':
                    medal['purchase_status'] = '售罄'
                else:
                    medal['purchase_status'] = '已购买'
            else:
                medal['purchase_status'] = value
        
        # 站点信息
        medal['site'] = site_name
        medal['currency'] = '爆米花'
        
        return self._format_medal_data(medal)

    def fetch_user_medals(self, site) -> List[Dict]:
        """获取用户已拥有的勋章"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            url = f"{site_url.rstrip('/')}/medal_center.php"
            
            logger.info("正在获取用户已拥有勋章数据")
            
            res = self._request_with_retry(
                url=url,
                cookies=site_cookie
            )
            
            if not res:
                logger.error(f"请求勋章页面失败! 站点: {site_name}")
                return []
                
            html = etree.HTML(res.text)
            
            # 查找已拥有勋章的区域 - 高度为150px的tr
            owned_medals_row = html.xpath("//tr[@style='height: 150px;']")
            if not owned_medals_row:
                logger.info("未找到已拥有勋章区域")
                return []
                
            # 检查是否显示"暂无任何勋章"
            td_content = owned_medals_row[0].xpath(".//td")
            if td_content:
                text_content = ''.join(td_content[0].xpath(".//text()")).strip()
                if '暂无' in text_content:
                    logger.info("用户暂无任何勋章")
                    return []
                
            # 提取已拥有的勋章图片
            medal_images = owned_medals_row[0].xpath(".//span[@class='medalcontainer']//img")
            
            if not medal_images:
                logger.info("用户暂无任何勋章")
                return []
            
            user_medals = []
            for img_elem in medal_images:
                medal = {}
                
                # 勋章名称 (从 title 属性获取)
                name = img_elem.get('title') or img_elem.get('alt', '')
                if name:
                    medal['name'] = name.strip()
                    
                # 勋章图片
                img_url = img_elem.get('src', '')
                if img_url:
                    if not img_url.startswith('http'):
                        from urllib.parse import urljoin
                        img_url = urljoin(site_url + '/', img_url.lstrip('/'))
                    medal['imageSmall'] = img_url
                
                # 设置为已拥有状态
                medal['purchase_status'] = '已拥有'
                medal['site'] = site_name
                
                user_medals.append(self._format_medal_data(medal))
                
            logger.info(f"共获取到 {len(user_medals)} 个用户已拥有勋章")
            return user_medals
            
        except Exception as e:
            logger.error(f"获取用户已拥有勋章失败: {str(e)}")
            return [] 