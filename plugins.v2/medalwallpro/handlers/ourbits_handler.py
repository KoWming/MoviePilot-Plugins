from typing import Dict, List
import re
from urllib.parse import urljoin

from lxml import etree

from app.log import logger
from .base import BaseMedalSiteHandler

class OurbitsMedalHandler(BaseMedalSiteHandler):
    """OurBits站点勋章处理器"""

    def should_use_image_proxy(self) -> bool:
        return True
    
    def match(self, site) -> bool:
        """判断是否为OurBits站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "ourbits" in site_name or "ourbits" in site_url or "我堡" in site_name

    def fetch_medals(self, site) -> List[Dict]:
        """
        OurBits没有勋章商店，只有勋章管理页面
        直接返回用户已拥有的勋章作为勋章列表
        """
        return self.fetch_user_medals(site)

    def fetch_user_medals(self, site) -> List[Dict]:
        """获取用户已拥有的勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            # 访问勋章管理页面
            badges_url = f"{site_url.rstrip('/')}/badges.php"
            logger.info(f"正在获取【{site_name}】站点勋章数据")
            
            res = self._request_with_retry(
                url=badges_url,
                cookies=site_cookie
            )
            
            if not res:
                logger.error(f"请求勋章管理页面失败！站点：{site_name}")
                return []
                
            # 使用lxml解析HTML
            html = etree.HTML(res.text)
            
            # 解析勋章表格
            medals = self._parse_badges(html, site_name, site_url, site)
            
            logger.info(f"共获取到 {len(medals)} 个用户已拥有勋章")
            return medals
            
        except Exception as e:
            logger.error(f"处理OurBits勋章数据时发生错误: {str(e)}")
            return []

    def _parse_badges(self, html, site_name: str, site_url: str, site) -> List[Dict]:
        """解析badges.php页面的勋章表格"""
        medals = []
        try:
            # 查找包含勋章的表格行
            badge_rows = html.xpath("//form[@method='post']//table//tr[td]")
            
            if not badge_rows:
                logger.error("未找到勋章表格行")
                return []
            
            logger.info(f"找到 {len(badge_rows)} 行数据")
            
            for row in badge_rows:
                try:
                    cells = row.xpath("./td")
                    if len(cells) < 4:
                        continue
                    
                    # 第一列：徽章说明
                    name_text = ''.join(cells[0].xpath('.//text()')).strip()
                    if not name_text or name_text == "徽章说明":
                        continue
                    
                    # 第二列：徽章图片
                    img_src = cells[1].xpath('.//img/@src')
                    if not img_src:
                        continue
                    
                    img_url = img_src[0]
                    # 补全图片URL
                    if not img_url.startswith('http'):
                        img_url = urljoin(site_url + '/', img_url.lstrip('/'))
                    
                    # 第三列：徽章类型（大徽章/小徽章）
                    badge_type = ''.join(cells[2].xpath('.//text()')).strip()
                    
                    image_url = img_url
                    
                    # 第四列：徽章位置
                    selected_option = cells[3].xpath('.//select/option[@selected]')
                    if selected_option:
                        position_text = ''.join(selected_option[0].xpath('.//text()')).strip()
                    else:
                        position_text = "未佩戴"
                    
                    medal = {
                        'name': name_text,
                        'description': f"{badge_type} - {position_text}",
                        'imageSmall': image_url,
                        'original_image_url': img_url,  # 记录原始URL用于缓存
                        'site': site_name,
                        'purchase_status': '已拥有',
                        'validity': '永久有效',
                        'bonus_rate': '',
                        'price': 0,
                        'stock': '',
                        'currency': '魔力'
                    }
                    
                    medals.append(self._format_medal_data(medal))
                    
                except Exception as e:
                    logger.warning(f"解析单个勋章行时出错: {e}")
                    continue
            
            return medals
            
        except Exception as e:
            logger.error(f"解析勋章表格时发生错误: {e}")
            return []
