from typing import Dict, List
import base64
import re
from io import BytesIO
from urllib.parse import urljoin

from PIL import Image
from lxml import etree

from app.log import logger
from .base import BaseMedalSiteHandler


class HddolbyMedalHandler(BaseMedalSiteHandler):
    """高清杜比站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为高清杜比站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "hddolby" in site_name or "hddolby" in site_url or "hddolby.com" in site_url
    
    def _download_image_to_base64(self, img_url: str, site) -> str:
        """
        下载图片并转换为 Base64 Data URI
        支持 GIF 转 WebP 动画以减小体积
        :param img_url: 图片URL
        :param site: 站点对象(用于获取 Cookie)
        :return: Base64 Data URI 或空字符串
        """
        # 1. 优先检查缓存
        if img_url in self.image_cache:
            return self.image_cache[img_url]

        try:
            
            # 使用站点 Cookie 下载图片
            res = self._request_with_retry(url=img_url, cookies=site.cookie)
            
            if not res or res.status_code != 200:
                logger.warning(f"下载图片失败: {img_url}, 状态码: {res.status_code if res else 'None'}")
                return ""
            
            # 获取图片内容类型
            content_type = res.headers.get('Content-Type', 'image/png')
            
            # 压缩图片以减小 Base64 大小
            try:
                img = Image.open(BytesIO(res.content))
                
                # 如果是 GIF,转换为 WebP 动画(体积减少 50-70%)
                if content_type == 'image/gif' or img_url.lower().endswith('.gif'):
                    try:
                        # 获取所有帧
                        frames = []
                        durations = []
                        
                        # 提取 GIF 的所有帧
                        try:
                            while True:
                                # 调整尺寸(最大 150x150)
                                frame = img.copy()
                                frame.thumbnail((150, 150), Image.Resampling.LANCZOS)
                                
                                # 转换为 RGBA 以保留透明通道
                                if frame.mode in ('P', 'PA'):
                                    # 调色板模式,转换为RGBA
                                    frame = frame.convert('RGBA')
                                elif frame.mode not in ('RGBA', 'RGB'):
                                    frame = frame.convert('RGBA')
                                
                                frames.append(frame)
                                # 获取帧延迟时间(毫秒)
                                duration = img.info.get('duration', 100)
                                durations.append(duration)
                                
                                img.seek(img.tell() + 1)
                        except EOFError:
                            pass  # 所有帧已处理完
                        
                        if frames:
                            # 保存为 WebP 动画
                            output = BytesIO()
                            frames[0].save(
                                output,
                                format='WEBP',
                                save_all=True,
                                append_images=frames[1:],
                                duration=durations,
                                loop=0,  # 无限循环
                                quality=85,
                                method=6  # 最佳压缩
                            )
                            img_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
                            content_type = 'image/webp'
                            logger.debug(f"GIF 转 WebP 成功: {img_url[:50]}... (帧数: {len(frames)})")
                        else:
                            # 如果没有提取到帧,使用原图
                            img_base64 = base64.b64encode(res.content).decode('utf-8')
                            
                    except Exception as gif_error:
                        logger.warning(f"GIF 转 WebP 失败,使用原图: {str(gif_error)}")
                        img_base64 = base64.b64encode(res.content).decode('utf-8')
                else:
                    # 静态图片:生成缩略图(最大 150x150,保持比例)
                    max_size = (150, 150)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # 检查是否有透明通道
                    has_transparency = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
                    
                    if has_transparency:
                        # 有透明通道:转换为 WebP 以保留透明度
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                        
                        output = BytesIO()
                        img.save(output, format='WEBP', quality=90, method=6)
                        img_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
                        content_type = 'image/webp'
                    else:
                        # 无透明通道:转换为 RGB 并保存为 JPEG
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        output = BytesIO()
                        img.save(output, format='JPEG', quality=85, optimize=True)
                        img_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
                        content_type = 'image/jpeg'
                    
            except Exception as img_error:
                logger.warning(f"压缩图片失败,使用原图: {str(img_error)}")
                img_base64 = base64.b64encode(res.content).decode('utf-8')
            
            data_uri = f"data:{content_type};base64,{img_base64}"
            return data_uri
            
        except Exception as e:
            logger.error(f"转换图片为 Base64 失败: {img_url}, 错误: {str(e)}")
            return ""
    
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
            
            # 获取所有勋章行 (在购买、赠送勋章表格中)
            medal_rows = html.xpath("//table[@border='1']//tbody/tr[position()>1]")
            
            if not medal_rows:
                logger.warning(f"没有找到勋章数据")
                return []
            
            logger.info(f"找到 {len(medal_rows)} 个勋章数据")
        
            logger.info("正在转换勋章图片...")
            all_medals = []
            converted_count = 0
            for row in medal_rows:
                try:
                    medal = self._process_medal_item(row, site_name, site_url, site)
                    if medal:
                        all_medals.append(medal)
                        if medal.get('imageSmall', '').startswith('data:'):
                            converted_count += 1
                except Exception as e:
                    logger.error(f"处理勋章数据时发生错误: {str(e)}")
                    continue
            
            logger.debug(f"成功将 {converted_count} 个勋章图片转换为 Base64")
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
            
            # 下载图片并转换为 Base64
            base64_image = self._download_image_to_base64(img_url, site)
            if base64_image:
                medal['imageSmall'] = base64_image
            else:
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
            medal_imgs = user_html.xpath("//img[contains(@src, '/medals/')]")
            
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
                        
                        # 下载图片并转换为 Base64
                        base64_image = self._download_image_to_base64(img_url, site)
                        if base64_image:
                            medal['imageSmall'] = base64_image
                        else:
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
