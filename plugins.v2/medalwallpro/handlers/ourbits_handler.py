from typing import Dict, List
import base64
import re
from io import BytesIO
from urllib.parse import urljoin

from PIL import Image
from lxml import etree

from app.log import logger
from .base import BaseMedalSiteHandler

class OurbitsMedalHandler(BaseMedalSiteHandler):
    """OurBits站点勋章处理器"""
    
    def match(self, site) -> bool:
        """判断是否为OurBits站点"""
        site_name = site.name.lower()
        site_url = site.url.lower()
        return "ourbits" in site_name or "ourbits" in site_url or "我堡" in site_name

    def _download_image_to_base64(self, img_url: str, site, badge_type: str = "") -> str:
        """
        下载图片并转换为 Base64 Data URI
        支持 GIF 转 WebP 动画以减小体积
        :param img_url: 图片URL
        :param site: 站点对象（用于获取 Cookie）
        :param badge_type: 勋章类型（大徽章/小徽章），用于确定缩放尺寸
        :return: Base64 Data URI 或空字符串
        """
        # 1. 优先检查缓存
        if img_url in self.image_cache:
            return self.image_cache[img_url]

        # 根据勋章类型确定缩放尺寸
        if "大" in badge_type:
            max_size = (260, 260)  # 大徽章保持原始尺寸
        elif "小" in badge_type:
            max_size = (60, 60)    # 小徽章
        else:
            max_size = (150, 150)  # 默认尺寸
        
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
                
                # 如果是 GIF，转换为 WebP 动画（体积减少 50-70%）
                if content_type == 'image/gif' or img_url.lower().endswith('.gif'):
                    try:
                        # 获取所有帧
                        frames = []
                        durations = []
                        
                        # 提取 GIF 的所有帧
                        try:
                            while True:
                                # 调整尺寸（根据勋章类型）
                                frame = img.copy()
                                frame.thumbnail(max_size, Image.Resampling.LANCZOS)
                                
                                # 转换为 RGBA 以保留透明通道
                                if frame.mode in ('P', 'PA'):
                                    # 调色板模式,转换为RGBA
                                    frame = frame.convert('RGBA')
                                elif frame.mode not in ('RGBA', 'RGB'):
                                    frame = frame.convert('RGBA')
                                
                                frames.append(frame)
                                # 获取帧延迟时间（毫秒）
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
                            # 如果没有提取到帧，使用原图
                            img_base64 = base64.b64encode(res.content).decode('utf-8')
                            
                    except Exception as gif_error:
                        logger.warning(f"GIF 转 WebP 失败，使用原图: {str(gif_error)}")
                        img_base64 = base64.b64encode(res.content).decode('utf-8')
                else:
                    # 静态图片:生成缩略图(根据勋章类型,保持比例)
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
                logger.warning(f"压缩图片失败，使用原图: {str(img_error)}")
                img_base64 = base64.b64encode(res.content).decode('utf-8')
            
            data_uri = f"data:{content_type};base64,{img_base64}"
            return data_uri
            
        except Exception as e:
            logger.error(f"转换图片为 Base64 失败: {img_url}, 错误: {str(e)}")
            return ""

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
            logger.info("正在转换勋章图片...")
            
            converted_count = 0
            
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
                    
                    # 第三列：徽章类型（大徽章/小徽章）- 先获取类型再转换图片
                    badge_type = ''.join(cells[2].xpath('.//text()')).strip()
                    
                    # 下载图片并转换为 Base64（避免前端跨域问题）
                    base64_image = self._download_image_to_base64(img_url, site, badge_type)
                    if not base64_image:
                        # 降级：如果下载失败，仍然使用原始 URL
                        logger.warning(f"图片转 Base64 失败，使用原始 URL: {img_url}")
                        base64_image = img_url
                    else:
                        converted_count += 1
                    
                    # 第四列：徽章位置
                    selected_option = cells[3].xpath('.//select/option[@selected]')
                    if selected_option:
                        position_text = ''.join(selected_option[0].xpath('.//text()')).strip()
                    else:
                        position_text = "未佩戴"
                    
                    medal = {
                        'name': name_text,
                        'description': f"{badge_type} - {position_text}",
                        'imageSmall': base64_image,
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
            
            logger.debug(f"成功将 {converted_count} 个勋章图片转换为 Base64")
            return medals
            
        except Exception as e:
            logger.error(f"解析勋章表格时发生错误: {e}")
            return []
