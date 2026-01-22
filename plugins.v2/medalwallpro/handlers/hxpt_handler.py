from typing import Dict, List
from app.log import logger
from lxml import etree
from .base import BaseMedalSiteHandler
from urllib.parse import urljoin

class HxptMedalHandler(BaseMedalSiteHandler):
    """好学站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为好学站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "hxpt" in site_name or "hxpt" in site_url or "好学" in site_name

    def fetch_medals(self, site) -> List[Dict]:
        """获取好学站点勋章数据"""
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
            
            # 获取所有分组section
            sections = html.xpath("//div[@class='category-section']")
            if not sections:
                logger.error("未找到勋章分组section！")
                return []
            
            logger.info(f"找到 {len(sections)} 个勋章分组")
            
            # 处理所有勋章数据
            medals = []
            
            # 遍历所有分组
            for section in sections:
                try:
                    # 获取分组名称
                    group_title = section.xpath(".//h2[@class='category-title']/text()")
                    group_name = "默认分组"
                    if group_title:
                        group_name = group_title[0].strip()
                        logger.info(f"处理勋章分组: {group_name}")
                    
                    # 获取勋章网格（可能包含hidden类）
                    medal_grids = section.xpath(".//div[contains(@class, 'medal-grid')]")
                    if not medal_grids:
                        continue
                    
                    # 获取该分组下的所有勋章卡片
                    medal_cards = medal_grids[0].xpath(".//div[@class='medal-card']")
                    logger.info(f"找到 {len(medal_cards)} 个勋章")
                    
                    for card in medal_cards:
                        try:
                            medal = self._process_medal_card(card, site_name, site_url, group_name)
                            if medal:
                                medals.append(medal)
                        except Exception as e:
                            logger.error(f"处理勋章卡片时发生错误：{str(e)}")
                            continue
                            
                except Exception as e:
                    logger.error(f"处理勋章分组时发生错误：{str(e)}")
                    continue
            
            logger.info(f"共获取到 {len(medals)} 个勋章数据")
            return medals
            
        except Exception as e:
            logger.error(f"处理好学站点勋章数据时发生错误: {str(e)}")
            return []

    def _process_medal_card(self, card, site_name: str, site_url: str, group_name: str = "") -> Dict:
        """处理单个勋章卡片数据"""
        medal = {}
        
        try:
            # 从 view-detail 按钮获取完整数据（data-* 属性）
            detail_btns = card.xpath(".//button[contains(@class, 'view-detail')]")
            if not detail_btns:
                logger.warning("未找到详情按钮，跳过该勋章")
                return None
                
            detail_btn = detail_btns[0]
            
            # 提取所有 data-* 属性
            medal_id = detail_btn.get('data-id')
            if medal_id:
                medal['id'] = medal_id
                
            name = detail_btn.get('data-name')
            if name:
                medal['name'] = name.strip()
                
            description = detail_btn.get('data-description')
            if description:
                medal['description'] = description.strip()
                
            # 图片URL
            img_url = detail_btn.get('data-image')
            if img_url:
                # 如果不是http/https开头，补全为完整站点URL
                if not img_url.startswith(('http://', 'https://')):
                    img_url = urljoin(site_url, img_url.lstrip('/'))
                medal['imageSmall'] = img_url
                
            # 价格
            price = detail_btn.get('data-price')
            if price:
                try:
                    medal['price'] = int(price.replace(',', ''))
                except ValueError:
                    medal['price'] = 0
                    
            # 有效期/时长
            duration = detail_btn.get('data-duration')
            if duration:
                medal['validity'] = duration.strip()
                
            # 加成比例
            bonus = detail_btn.get('data-bonus')
            if bonus:
                medal['bonus_rate'] = bonus.strip()
                
            # 赠送手续费
            gift_fee = detail_btn.get('data-gift-fee')
            if gift_fee:
                medal['gift_fee'] = gift_fee.strip()
                
            # 可购买开始时间
            sale_begin = detail_btn.get('data-sale-begin')
            if sale_begin:
                medal['saleBeginTime'] = sale_begin.strip()
                
            # 可购买结束时间
            sale_end = detail_btn.get('data-sale-end')
            if sale_end:
                medal['saleEndTime'] = sale_end.strip()
                
            # 库存
            inventory = detail_btn.get('data-inventory')
            if inventory:
                medal['stock'] = inventory.strip()
            
            # 从购买按钮获取购买状态
            buy_btns = card.xpath(".//button[contains(@class, 'buy')]")
            if buy_btns:
                buy_btn = buy_btns[0]
                # 获取按钮的值或文本作为状态
                status = buy_btn.get('value')
                if not status:
                    status = buy_btn.text
                if status:
                    medal['purchase_status'] = status.strip()
                    
            # 站点信息
            medal['site'] = site_name
            # 货币单位
            medal['currency'] = '火花'
            # 分组信息
            if group_name:
                medal['group'] = group_name
            
            return self._format_medal_data(medal)
            
        except Exception as e:
            logger.error(f"处理勋章卡片数据时发生错误: {str(e)}")
            return None
