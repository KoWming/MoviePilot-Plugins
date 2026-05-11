from typing import Dict, List
import re
from urllib.parse import urljoin

from lxml import etree

from app.log import logger
from .base import BaseMedalSiteHandler


class HddolbyMedalHandler(BaseMedalSiteHandler):
    """高清杜比站点勋章处理器"""

    def should_use_image_proxy(self) -> bool:
        return True
    
    def match(self, site) -> bool:
        """判断是否为高清杜比站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "hddolby" in site_name or "hddolby" in site_url or "hddolby.com" in site_url
    
    def fetch_medals(self, site) -> List[Dict]:
        """获取高清杜比站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url
            site_cookie = site.cookie
            
            # 构建勋章页面URL
            url = f"{site_url.rstrip('/')}/medals.php"
            logger.info(f"正在获取【{site_name}】站点勋章数据")
            
            # 发送请求获取勋章页面
            res = self._request_with_retry(
                url=url,
                cookies=site_cookie
            )
            
            if not res:
                logger.error(f"请求勋章页面失败! 站点: {site_name}")
                return []
            
            # 使用lxml解析HTML
            html = etree.HTML(res.text)
            
            # 优先基于“购买、赠送勋章”标题后的数据表定位，避免页面结构调整导致失配
            medal_rows = html.xpath(
                "//h3[contains(normalize-space(.), '购买、赠送勋章')]/following::table[1]"
                "//tr[count(./td) >= 9 and ./td[1]//img and ./td[2]//h1]"
            )

            if not medal_rows:
                # 兜底：基于表头列名定位勋章表
                medal_rows = html.xpath(
                    "//table[.//td[contains(@class, 'colhead') and normalize-space(.)='图片']"
                    " and .//td[contains(@class, 'colhead') and contains(normalize-space(.), '描述')]]"
                    "//tr[count(./td) >= 9 and ./td[1]//img and ./td[2]//h1]"
                )

            if not medal_rows:
                # 最后兜底：全局按列结构抓取
                medal_rows = html.xpath(
                    "//tr[count(./td) >= 9 and ./td[1]//img and ./td[2]//h1]"
                )
            
            if not medal_rows:
                title = ''.join(html.xpath('//title/text()')).strip()
                logger.warning(f"没有找到勋章数据，页面标题: {title}")
                return []
            
            logger.info(f"找到 {len(medal_rows)} 个勋章数据")

            all_medals = []
            for row in medal_rows:
                try:
                    medal = self._process_medal_item(row, site_name, site_url, site)
                    if medal:
                        all_medals.append(medal)
                except Exception as e:
                    logger.error(f"处理勋章数据时发生错误: {str(e)}")
                    continue

            logger.info(f"共获取到 {len(all_medals)} 个勋章数据")
            return all_medals
            
        except Exception as e:
            logger.error(f"处理高清杜比站点勋章数据时发生错误: {str(e)}")
            return []
    
    def _process_medal_item(self, row, site_name: str, site_url: str, site) -> Dict:
        """处理单个勋章项数据"""
        medal = {}
        
        # 获取所有td列
        cols = row.xpath('./td')
        if len(cols) < 10:
            logger.warning(f"勋章数据列数不足: {len(cols)}")
            return None
        
        # 第1列: 图片
        img = cols[0].xpath('.//img/@src')
        if img:
            img_url = img[0]
            if not img_url.startswith('http'):
                img_url = urljoin(site_url + '/', img_url.lstrip('/'))
            
            medal['imageSmall'] = img_url
        
        # 记录原始URL用于缓存
        medal['original_image_url'] = img_url
        
        # 第2列: 描述 (包含名称)
        name_elem = cols[1].xpath('.//h1/text()')
        if name_elem:
            medal['name'] = name_elem[0].strip()
        
        # 描述文本
        desc_texts = cols[1].xpath('.//text()[not(parent::h1)]')
        desc = ''.join([t.strip() for t in desc_texts if t.strip()])
        if desc:
            medal['description'] = desc
        
        # 第3列: 可购买时间
        time_text = ''.join(cols[2].xpath('.//text()')).strip()
        if ' ~ ' in time_text or '~' in time_text:
            # 分割开始和结束时间
            times = re.split(r'\s*~\s*', time_text)
            if len(times) >= 2:
                medal['saleBeginTime'] = times[0].strip()
                medal['saleEndTime'] = times[1].strip()
        
        # 第4列: 购买后有效期
        validity_text = ''.join(cols[3].xpath('.//text()')).strip()
        medal['validity'] = validity_text
        
        # 第5列: 魔力加成
        bonus_text = ''.join(cols[4].xpath('.//text()')).strip()
        if bonus_text:
            medal['bonus_rate'] = bonus_text
        
        # 第6列: 赠送税率 (可选,暂不使用)
        
        # 第7列: 价格
        price_text = ''.join(cols[6].xpath('.//text()')).strip()
        try:
            medal['price'] = int(price_text.replace(',', ''))
        except ValueError:
            medal['price'] = 0
        
        # 第8列: 库存
        stock_text = ''.join(cols[7].xpath('.//text()')).strip()
        if stock_text and stock_text != '无限量':
            try:
                stock_num = int(stock_text)
                if stock_num < 100:
                    medal['stock_status'] = '库存紧张'
            except ValueError:
                pass
        
        # 第9列: 购买状态
        buy_status = ''.join(cols[8].xpath('.//span/text()')).strip()
        if '已过购买时限' in buy_status or '已过' in buy_status:
            medal['purchase_status'] = '已过可购买时间'
        elif '仅可授予' in buy_status or '不能购买' in buy_status:
            medal['purchase_status'] = '仅授予'
        else:
            medal['purchase_status'] = '购买'
        
        # 站点信息
        medal['site'] = site_name
        medal['currency'] = '鲸币'  # 高清杜比使用鲸币
        
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
            
            # 解析用户详情页的勋章
            user_html = etree.HTML(user_res.text)
            
            # 查找勋章区域 (可能需要根据实际HTML结构调整)
            medal_imgs = user_html.xpath("//img[contains(@src, 'medals/')]")
            
            if not medal_imgs:
                logger.info(f"用户暂无已拥有勋章")
                return []
            
            logger.info(f"找到 {len(medal_imgs)} 个用户已拥有勋章")
            
            user_medals = []
            for img in medal_imgs:
                try:
                    medal = {}
                    
                    # 勋章图片
                    img_url = img.get('src')
                    if img_url:
                        if not img_url.startswith('http'):
                            img_url = urljoin(site_url + '/', img_url.lstrip('/'))
                        
                        medal['imageSmall'] = img_url
                    
                    # 记录原始URL用于缓存
                    if img_url:
                        medal['original_image_url'] = img_url
                    
                    # 勋章名称 (从title或alt属性获取)
                    name = img.get('title') or img.get('alt') or ''
                    if name:
                        medal['name'] = name.strip()
                    
                    # 设置购买状态为已拥有
                    medal['purchase_status'] = '已拥有'
                    medal['site'] = site_name
                    medal['currency'] = '鲸币'
                    
                    user_medals.append(self._format_medal_data(medal))
                    
                except Exception as e:
                    logger.error(f"处理用户勋章数据时发生错误: {str(e)}")
                    continue
            
            logger.info(f"共获取到 {len(user_medals)} 个用户已拥有勋章")
            return user_medals
            
        except Exception as e:
            logger.error(f"获取高清杜比用户已拥有勋章失败: {str(e)}")
            return []
