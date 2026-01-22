from typing import Dict, List
import re
from lxml import etree
from datetime import datetime, timedelta
import pytz
from app.log import logger
from app.core.config import settings
from .base import BaseMedalSiteHandler

class ZmMedalHandler(BaseMedalSiteHandler):
    """织梦站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为织梦站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "zm" in site_name or "织梦" in site_name or "zm" in site_url

    def fetch_medals(self, site) -> List[Dict]:
        """获取织梦站点勋章数据"""
        try:
            site_name = site.name
            site_url = site.url.rstrip('/')
            site_cookie = site.cookie
            
            logger.info(f"正在获取【{site_name}】站点勋章数据")
            # 发送请求获取勋章数据
            res = self._request_with_retry(
                url=f"{site_url}/javaapi/user/queryAllMedals",
                cookies=site_cookie
            )
            
            if not res:
                logger.error(f"请求勋章接口失败！站点：{site_name}")
                return []
                
            # 处理勋章数据
            data = res.json().get('result', {})
            medal_groups = data.get('medalGroups', [])
            medals = data.get('medals', [])
            
            # 尝试通过爬取用户页面获取确切的已拥有状态
            # API返回的 status 字段可能不准确或者有延迟
            real_owned_names = set()
            user_points = 0.0
            try:
                user_id = self._get_user_id(site_url, site_cookie)
                if user_id:
                    real_owned_names, user_points = self._get_user_info_from_page(site_url, site_cookie, user_id)
                    logger.info(f"从用户详情页爬取到 {len(real_owned_names)} 个已拥有勋章，电力值: {user_points}")
            except Exception as e:
                logger.warning(f"尝试爬取用户详情页失败: {e}")
            
            # 用于去重的集合
            processed_medals = set()
            all_medals = []
            
            # 处理分组勋章
            for group in medal_groups:
                group_name = group.get('groupName', '默认分组')
                for medal in group.get('medalList', []):
                    medal_data = self._process_medal(medal, site_name, group_name, real_owned_names, user_points)

                    medal_key = f"{medal_data['name']}_{site_name}"
                    if medal_key not in processed_medals:
                        processed_medals.add(medal_key)
                        all_medals.append(medal_data)

            # 处理独立勋章 - 归类为 "其他勋章"
            # 将未分组的勋章放到最后
            for medal in medals:
                medal_data = self._process_medal(medal, site_name, "其他勋章", real_owned_names, user_points)
                     
                medal_key = f"{medal_data['name']}_{site_name}"
                if medal_key not in processed_medals:
                    processed_medals.add(medal_key)
                    all_medals.append(medal_data)
            
            return all_medals
            
        except Exception as e:
            logger.error(f"处理织梦站点勋章数据时发生错误: {str(e)}")
            return []

    def _get_user_id(self, site_url: str, cookies: str) -> str:
        """获取用户ID"""
        try:
            res = self._request_with_retry(
                url=f"{site_url}/index.php",
                cookies=cookies
            )
            if not res:
                return ""

            match = re.search(r'userdetails\.php\?id=(\d+)', res.text)
            if match:
                return match.group(1)
            return ""
        except Exception as e:
            logger.error(f"获取用户ID失败: {str(e)}")
            return ""

    def _get_user_info_from_page(self, site_url: str, cookies: str, user_id: str) -> tuple[set, float]:
        """从用户详情页获取已拥有的勋章和电力值"""
        owned_medals = set()
        user_points = 0.0
        try:
            res = self._request_with_retry(
                url=f"{site_url}/userdetails.php?id={user_id}",
                cookies=cookies
            )
            if not res:
                return owned_medals, user_points
                
            html = etree.HTML(res.text)
            if html is None:
                return owned_medals, user_points

            # 解析电力值
            try:
                bonus_nodes = html.xpath('//a[@id="self_bonus"]')
                if bonus_nodes:
                    full_text = bonus_nodes[0].xpath('string(.)').strip()
                    import re
                    match = re.search(r'([\d,]+\.?\d*)', full_text.replace(' ', '').replace('\\n', '').replace('\\r', ''))
                    if match:
                        points_str = match.group(1).replace(',', '')
                        user_points = float(points_str)
                    else:
                         cleaned_text = full_text.replace('电力值', '').replace(',', '').strip()
                         match = re.search(r'(\d+(\.\d+)?)', cleaned_text)
                         if match:
                             user_points = float(match.group(1))
            except Exception as e:
                logger.warning(f"解析用户电力值失败: {e}")

            # 策略1: 查找勋章管理表单 (更详细)
            medal_forms = html.xpath('//form[.//input[@id="save-user-medal-btn"]]//div[contains(@style, "float: left") or contains(@style, "flex-direction: column")]')
            
            if medal_forms:
                logger.info("使用表单模式解析用户勋章")
                for div in medal_forms:
                    try:
                        imgs = div.xpath('.//img[@class="preview"]')
                        if not imgs:
                            imgs = div.xpath('.//img')
                        if not imgs:
                            continue
                        
                        img_node = imgs[0]
                        name = img_node.get('title', '') or img_node.get('alt', '')
                        if name:
                            owned_medals.add(name.strip())
                    except Exception as e:
                        continue
            else:
                # 策略2：解析顶部勋章图标 (备选)
                logger.info("使用图标模式解析用户勋章")
                # 优先匹配 h1 标签内的勋章
                medal_imgs = html.xpath('//h1//img[contains(@class, "nexus-username-medal-big")] | //h1//img[contains(@class, "nexus-username-medal")]')
                
                if not medal_imgs:
                     medal_imgs = html.xpath('//h1/following-sibling::*[not(self::table)]//img[contains(@class, "nexus-username-medal")]')
                
                if not medal_imgs:
                    medal_imgs = html.xpath('(//h1/preceding-sibling::span | //h1/following-sibling::span)[not(ancestor::table)]//img[contains(@class, "nexus-username-medal")]')
                
                # 如果还是没找到，尝试查找通常勋章所在的 td (用户提供的HTML结构暗示可能在某个td里，虽未明确class)
                # 作为一个兜底，我们可以保留之前的whitelist机制，但结合更具体的上下文
                if not medal_imgs:
                     # 尝试查找包含 'medal.php' 链接附近的图片
                     medal_imgs = html.xpath('//a[contains(@href, "medal.php")]/preceding::img[contains(@class, "nexus-username-medal")]')

                for img in medal_imgs:
                    name = img.get('title', '') or img.get('alt', '')
                    if name:
                        owned_medals.add(name.strip())
            
            return owned_medals, user_points
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return owned_medals, user_points

    def _process_medal(self, medal: Dict, site_name: str, group_name: str = "", owned_names: set = None, user_points: float = 0) -> Dict:
        """处理单个勋章数据"""
        try:
            has_medal = medal.get('hasMedal', False)
            image_small = medal.get('imageSmall', '')
            price = medal.get('price', 0)
            name = medal.get('name', '')
            item_description = medal.get('description', '')
            sale_begin_time = medal.get('saleBeginTime') or medal.get('createdAt', '')
            sale_end_time = medal.get('saleEndTime') or medal.get('updatedAt', '')
            
            # 额外字段解析
            bonus = medal.get('bonusAdditionFactor', 0)
            duration = medal.get('duration', 0)
            inventory = medal.get('inventory')
            
            if owned_names is None:
                owned_names = set()

            # 确定购买状态
            if has_medal and name in owned_names: 
                purchase_status = '已经购买'
            elif self._is_current_time_in_range(sale_begin_time, sale_end_time):
                if inventory is not None and int(inventory) <= 0:
                     purchase_status = '库存不足'
                elif user_points > 0 and float(user_points) < float(price):
                     purchase_status = '电力不足'
                else:
                    purchase_status = '购买'
            else:
                purchase_status = '未到可购买时间'
            
            # 加成显示 (+20%, -100%)
            bonus_val = float(bonus)
            if bonus_val > 0:
                bonus_str = f"+{int(bonus_val * 100)}%"
            elif bonus_val < 0:
                bonus_str = f"{int(bonus_val * 100)}%"
            else:
                bonus_str = ""

            # 格式化数据
            formatted_data = {
                'name': name,
                'description': item_description,
                'imageSmall': image_small,
                'saleBeginTime': sale_begin_time,
                'saleEndTime': sale_end_time,
                'price': price,
                'site': site_name,
                'purchase_status': purchase_status,
                'currency': '电力',
                'bonus_rate': bonus_str,
                'validity': f"{duration}天" if duration and int(duration) > 0 else "永久有效",
                'stock': str(inventory) if inventory is not None else "无限",
                'stock_status': '库存紧张' if inventory is not None and 0 < int(inventory) < 10 else ""
            }
            
            if group_name:
                formatted_data['group'] = group_name
                
            return self._format_medal_data(formatted_data)
            
        except Exception as e:
            logger.error(f"处理勋章数据时发生错误: {str(e)}")
            return self._format_medal_data({
                'name': medal.get('name', '未知勋章'),
                'imageSmall': medal.get('imageSmall', ''),
                'site': site_name,
                'purchase_status': '未知状态',
                'currency': '电力',
                'group': group_name
            })

    def _is_current_time_in_range(self, start_time: str, end_time: str) -> bool:
        """判断当前时间是否在给定的时间范围内"""
        try:
            # 处理空值
            if not start_time or not end_time:
                # logger.debug(f"时间值为空: start_time={start_time}, end_time={end_time}")
                return True
                
            # 处理"~"分隔符
            if "~" in start_time:
                start_time = start_time.split("~")[0].strip()
            if "~" in end_time:
                end_time = end_time.split("~")[1].strip()
                
            # 处理"不限"的情况
            if "不限" in start_time or "不限" in end_time:
                # logger.debug(f"时间包含'不限': start_time={start_time}, end_time={end_time}")
                return True
                
            # 清理时间字符串
            start_time = start_time.strip()
            end_time = end_time.strip()
            
            # 处理空字符串
            if not start_time or not end_time:
                # logger.debug(f"清理后时间值为空: start_time={start_time}, end_time={end_time}")
                return True
                
            # 尝试解析时间
            try:
                # 使用系统时区
                current_time = datetime.now(pytz.timezone(settings.TZ))
                start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.timezone(settings.TZ))
                end_datetime = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.timezone(settings.TZ))
                
                # 添加时间容差(5分钟)
                time_tolerance = timedelta(minutes=5)
                return (start_datetime - time_tolerance) <= current_time <= (end_datetime + time_tolerance)
                
            except ValueError as e:
                # logger.warning(f"时间格式解析失败: {e}, start_time={start_time}, end_time={end_time}")
                return True
                
        except Exception as e:
            logger.error(f"解析时间范围时发生错误: {e}, start_time={start_time}, end_time={end_time}")
            return True 