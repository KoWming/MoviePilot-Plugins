import re
import time
import requests
import socket

from lxml import etree
from datetime import datetime
from typing import Any, List, Dict, Tuple, Optional
from apscheduler.triggers.cron import CronTrigger

from app.log import logger
from app.core.config import settings
from app.plugins import _PluginBase
from app.scheduler import Scheduler
from app.schemas import NotificationType
from app.db.site_oper import SiteOper

class VicomoFarm(_PluginBase):
    # 插件名称
    plugin_name = "Vue-象岛农场"
    # 插件描述
    plugin_desc = "监听象岛农场相关信息，我在PT学卖菜。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/Vicomofarm.png"
    # 插件版本
    plugin_version = "1.2.9"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "vicomofarm_"
    # 加载顺序
    plugin_order = 26
    # 可使用的用户级别
    auth_level = 2

    # 配置与状态
    _enabled: bool = False
    _notify: bool = True
    _use_proxy: bool = True
    _retry_count: int = 2
    _cron: Optional[str] = None
    _cookie: Optional[str] = None
    _history_count: Optional[int] = None

    # 自动交易配置
    _auto_purchase_enabled: bool = False
    _purchase_price_threshold: float = 0
    _purchase_quantity_ratio: float = 0.5
    _auto_sale_enabled: bool = False
    _sale_price_threshold: float = 0
    _sale_quantity_ratio: float = 1
    _sale_profit_percentage: float = 0
    _expiry_sale_enabled: bool = False  # 新增：到期出售开关

    # 其他参数
    _farm_interval: int = 15
    _site_url: str = "https://ptvicomo.net/"
    _siteoper = None

    def __init__(self):
        super().__init__()

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """初始化插件，加载配置并注册定时任务"""
        try:
            self.stop_service()
            self._siteoper = SiteOper()

            if config:
                self._enabled = config.get("enabled", False)
                self._cron = config.get("cron")
                self._cookie = config.get("cookie")
                self._notify = config.get("notify", False)
                self._history_count = int(config.get("history_count", 10))
                self._farm_interval = int(config.get("farm_interval", 15))
                self._use_proxy = config.get("use_proxy", True)
                self._retry_count = int(config.get("retry_count", 2))
                # 自动交易配置
                self._auto_purchase_enabled = config.get("auto_purchase_enabled", False)
                self._purchase_price_threshold = float(config.get("purchase_price_threshold", 0))
                self._purchase_quantity_ratio = float(config.get("purchase_quantity_ratio", 0.5))
                self._auto_sale_enabled = config.get("auto_sale_enabled", False)
                self._sale_price_threshold = float(config.get("sale_price_threshold", 0))
                self._sale_quantity_ratio = float(config.get("sale_quantity_ratio", 1))
                self._sale_profit_percentage = float(config.get("sale_profit_percentage", 0))
                self._expiry_sale_enabled = config.get("expiry_sale_enabled", False)  # 新增：到期出售开关
            if not self._enabled:
                logger.info("象岛农场服务未启用")
                return
            if self._enabled and self._cron:
                logger.info(f"{self.plugin_name}: 已配置 CRON '{self._cron}'，任务将通过公共服务注册。")
            else:
                logger.info(f"{self.plugin_name}: 未配置定时任务。启动时配置: Enable={self._enabled}, Cron='{self._cron}'")
        except Exception as e:
            logger.error(f"象岛农场服务启动失败: {str(e)}")
            self._enabled = False

    @staticmethod
    def parse_farm_info(title, subtitle):
        """解析农场信息，返回结构化数据"""
        result = {"名称": "", "类型": "", "状态": "", "剩余配货量": "", "说明": "", "价格": ""}
        # 从title提取名称和状态
        m = re.search(r'【([^】]+)】', title)
        if m:
            name_status = m.group(1)
            if ' - ' in name_status:
                name, status = name_status.split(' - ', 1)
                result["名称"] = name.strip()
                result["状态"] = status.strip()
            else:
                result["名称"] = name_status.strip()
        # 提取剩余时间（如"剩余110小时"）并拼接到状态
        m_time = re.search(r'剩余[\d]+小时', title)
        if m_time:
            if result["状态"]:
                result["状态"] += f"（{m_time.group(0)}）"
            else:
                result["状态"] = m_time.group(0)
        # 剩余配货量
        m = re.search(r'剩余配货量为(\d+)kg', subtitle)
        if m:
            result["剩余配货量"] = m.group(1)
        # 类型
        m = re.search(r'类型[：: ]*([\u4e00-\u9fa5A-Za-z0-9]+)', subtitle)
        if m:
            result["类型"] = m.group(1)
        # 价格
        m = re.search(r'价格是([\d.]+)', subtitle)
        if m:
            result["价格"] = m.group(1)
        # 说明
        first_line = re.search(r'农作物已成熟', subtitle)
        second_line = re.search(r'保质期至下周六晚24:00，要马上进货吗？', subtitle)
        if first_line and second_line:
            result["说明"] = f"{first_line.group(0)}，{second_line.group(0)}"
        else:
            new_desc = re.search(r'每周日新的流行农作物成熟后，小象蔬菜店可以来这里批发进货，记得在下一波农作物成熟前卖出哦', subtitle)
            if new_desc:
                result["说明"] = new_desc.group(0)
            else:
                result["说明"] = "无"
        return result

    @staticmethod
    def parse_vegetable_shop_info(title, desc_text, full_text):
        """解析蔬菜店信息，返回结构化数据"""
        result = {"名称": "", "市场单价": "", "库存": "", "成本": "", "开店累计盈利": "", "盈利目标": "", "可卖数量": "", "说明": ""}
        m = re.search(r'【([^】]+)】', title)
        if m:
            name_block = m.group(1)
            name = name_block.split(' 市场单价')[0].strip()
            result["名称"] = name
            m2 = re.search(r'市场单价[：: ]*([\d.]+)', name_block)
            if m2:
                result["市场单价"] = m2.group(1)
            m3 = re.search(r'库存[：: ]*([\d]+)', name_block)
            if m3:
                result["库存"] = m3.group(1)
            m4 = re.search(r'成本[：: ]*([\d.]+)', name_block)
            if m4:
                result["成本"] = m4.group(1)
        if not result["库存"]:
            m = re.search(r'库存[：: ]*([\d]+)', title)
            if m:
                result["库存"] = m.group(1)
        if not result["成本"]:
            m = re.search(r'成本[：: ]*([\d.]+)', title)
            if m:
                result["成本"] = m.group(1)
        m = re.search(r'开店累计盈利[：: ]*([\-\d.]+)', full_text)
        if m:
            result["开店累计盈利"] = m.group(1)
        m = re.search(r'盈利目标[：: ]*([\d]+)', full_text)
        if m:
            result["盈利目标"] = m.group(1)
        m = re.search(r'可卖数量[为: ]*([\d]+)', full_text)
        if m:
            result["可卖数量"] = m.group(1)
        result["说明"] = desc_text.strip() if desc_text.strip() else "无"
        return result

    @staticmethod
    def parse_section_info(title: str, desc_text: str, full_text: str = None) -> dict:
        """根据标题类型解析不同区域的信息"""
        if '农庄' in title:
            return VicomoFarm.parse_farm_info(title, desc_text)
        elif '蔬菜店' in title:
            return VicomoFarm.parse_vegetable_shop_info(title, desc_text, full_text or desc_text)
        else:
            return {"名称": "", "类型": "", "状态": "", "剩余配货量": "", "说明": desc_text}

    def __farm_and_vegetable(self) -> dict:
        """
        解析象岛农庄、象岛新鲜蔬菜店的标题和副标题说明，并提取当前象草余额。
        返回格式：
        {
            "farm": {...结构化字段...},
            "vegetable_shop": {...结构化字段...},
            "bonus": "象草余额"
        }
        """
        retry_count = 0
        max_retries = self._retry_count

        while retry_count <= max_retries:
            try:
                url = f"{self._site_url}/customgame.php"
                headers = {
                    "cookie": self._cookie,
                    "referer": self._site_url,
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"
                }
                proxies = self._get_proxies()
                
                # 尝试带代理的请求
                try:
                    response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
                except requests.exceptions.ProxyError as proxy_error:
                    logger.warning(f"代理连接失败: {proxy_error}")
                    if proxies:
                        logger.info("尝试不使用代理直接连接...")
                        try:
                            response = requests.get(url, headers=headers, proxies=None, timeout=30)
                        except Exception as direct_error:
                            logger.error(f"直接连接也失败: {direct_error}")
                            raise direct_error
                    else:
                        raise proxy_error
                except Exception as request_error:
                    logger.error(f"请求失败: {request_error}")
                    raise request_error
                html = etree.HTML(response.text)

                result = {}
                # 解析象岛农庄（兼容id="buyTurnipSunday"和id="buyTurnip"）
                farm_td = html.xpath('//td[@id="buyTurnipSunday" or @id="buyTurnip"]')
                if farm_td:
                    farm_h1 = farm_td[0].xpath('.//h1')[0] if farm_td[0].xpath('.//h1') else None
                    farm_title = farm_h1.xpath('string(.)').strip() if farm_h1 is not None else ""
                    
                    # 获取所有文本内容，包括输入框的提示文本
                    farm_subtitle = ""
                    if farm_h1 is not None:
                        all_texts = []
                        current = farm_h1
                        while current is not None:
                            if current.tail and current.tail.strip():
                                all_texts.append(current.tail.strip())
                            if current.text and current.text.strip():
                                all_texts.append(current.text.strip())
                            current = current.getnext()
                        farm_subtitle = " ".join(all_texts)
                    
                    result["farm"] = self.parse_section_info(farm_title, farm_subtitle)
                else:
                    result["farm"] = {"名称": "", "类型": "", "状态": "", "剩余配货量": "", "说明": ""}

                # 解析象岛新鲜蔬菜店
                veg_td = html.xpath('//td[@id="saleTurnip"]')
                if veg_td:
                    veg_h1 = veg_td[0].xpath('.//h1')[0] if veg_td[0].xpath('.//h1') else None
                    veg_title = veg_h1.xpath('string(.)').strip() if veg_h1 is not None else ""
                    # 获取说明字段
                    veg_subtitle = ""
                    if veg_h1 is not None:
                        if veg_h1.tail and veg_h1.tail.strip():
                            veg_subtitle = veg_h1.tail.strip()
                        else:
                            next_node = veg_h1.getnext()
                            while next_node is not None:
                                text = next_node.text or ''
                                if text.strip():
                                    veg_subtitle = text.strip()
                                    break
                                if next_node.tail and next_node.tail.strip():
                                    veg_subtitle = next_node.tail.strip()
                                    break
                                next_node = next_node.getnext()
                    # 获取数值字段
                    veg_extra_text = []
                    if veg_h1 is not None:
                        sib = veg_h1.getnext()
                        while sib is not None:
                            # 拼接<b>标签文本和所有兄弟节点的text、tail
                            if sib.tag == 'b':
                                b_text = sib.xpath('string(.)').strip()
                                if b_text:
                                    veg_extra_text.append(b_text)
                            if sib.text and sib.text.strip():
                                veg_extra_text.append(sib.text.strip())
                            if sib.tail and sib.tail.strip():
                                veg_extra_text.append(sib.tail.strip())
                            sib = sib.getnext()
                    # 合成subtitle用于正则提取
                    veg_full_subtitle = veg_subtitle + '\n' + '\n'.join(veg_extra_text) if veg_extra_text else veg_subtitle
                    result["vegetable_shop"] = self.parse_section_info(veg_title, veg_subtitle, veg_full_subtitle)
                else:
                    result["vegetable_shop"] = {"名称": "", "市场单价": "", "库存": "", "成本": "", "开店累计盈利": "", "盈利目标": "", "可卖数量": "", "说明": ""}

                # 提取当前象草余额
                bonus = html.xpath('//div[contains(@class, "info-container-mybonus-1")]//div[normalize-space(text())="当前象草余额"]/following-sibling::div[1]/text()')
                result["bonus"] = bonus[0].strip() if bonus else ""

                return result

            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    logger.warning(f"解析农庄、蔬菜店和象草余额信息失败，正在进行第 {retry_count} 次重试: {e}")
                    time.sleep(self._farm_interval)
                else:
                    logger.error(f"解析农庄、蔬菜店和象草余额信息失败，已重试 {max_retries} 次: {e}")
                    return {"farm": {"名称": "", "类型": "", "状态": "", "剩余配货量": "", "说明": ""}, "vegetable_shop": {"名称": "", "市场单价": "", "库存": "", "成本": "", "开店累计盈利": "", "盈利目标": "", "可卖数量": "", "说明": ""}, "bonus": ""}

    def __purchase_task(self, buy_num: int):
        """进货任务：自动提交进货表单，跟随重定向并解析进货结果"""
        try:
            url = self._site_url + "/customgame.php?action=exchange"
            headers = {
                "cookie": self._cookie,
                "referer": self._site_url,
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
                "content-type": "application/x-www-form-urlencoded",
                "pragma": "no-cache",
            }
            proxies = self._get_proxies()

            # 构造POST参数
            data = {
                "option": 5,
                "buyTurnipNum": str(buy_num),
                "submit": "进货"
            }

            # 提交进货请求
            try:
                response = requests.post(url, headers=headers, data=data, proxies=proxies, timeout=30)
            except requests.exceptions.ProxyError as proxy_error:
                logger.warning(f"进货请求代理连接失败: {proxy_error}")
                if proxies:
                    logger.info("尝试不使用代理直接连接...")
                    try:
                        response = requests.post(url, headers=headers, data=data, proxies=None, timeout=30)
                    except Exception as direct_error:
                        logger.error(f"直接连接也失败: {direct_error}")
                        raise direct_error
                else:
                    raise proxy_error
            except Exception as request_error:
                logger.error(f"进货请求失败: {request_error}")
                raise request_error

            # 提取重定向URL（window.location.href）
            redirect_url = None
            pattern = r"window.location.href\s*=\s*['\"]([^'\"]*buy[^'\"]*)['\"]"
            match = re.search(pattern, response.text, re.DOTALL)
            if match:
                redirect_url = match.group(1)
                logger.info(f"提取到的进货结果重定向 URL: {redirect_url}")
            else:
                logger.error("未找到进货结果重定向 URL")
                return {"success": False, "msg": "未找到进货结果重定向 URL", "quantity": buy_num}

            # 访问重定向URL，获取进货结果页面
            try:
                result_response = requests.get(redirect_url, headers=headers, proxies=proxies, timeout=30)
            except requests.exceptions.ProxyError as proxy_error:
                logger.warning(f"进货结果页面代理连接失败: {proxy_error}")
                if proxies:
                    logger.info("尝试不使用代理直接连接...")
                    try:
                        result_response = requests.get(redirect_url, headers=headers, proxies=None, timeout=30)
                    except Exception as direct_error:
                        logger.error(f"直接连接也失败: {direct_error}")
                        raise direct_error
                else:
                    raise proxy_error
            except Exception as request_error:
                logger.error(f"获取进货结果页面失败: {request_error}")
                raise request_error
            logger.info(f"进货结果页面状态码: {result_response.status_code}")

            # 解析进货结果页面，优先用class=striking的div
            html = etree.HTML(result_response.text)
            striking_texts = html.xpath("//div[@class='striking']/text()")
            result_text = " ".join([t.strip() for t in striking_texts if t.strip()])
            if not result_text:
                # 模糊查找
                result_texts = html.xpath("//*[contains(text(), '进货成功') or contains(text(), '进货失败') or contains(text(), '获得')]/text()")
                result_text = " ".join([t.strip() for t in result_texts if t.strip()])
            if not result_text:
                # 取页面所有文本，找包含"进货"字样的句子
                all_text = " ".join(html.xpath('//text()'))
                for line in all_text.split():
                    if '进货' in line:
                        result_text = line
                        break
            if result_text:
                logger.info(f"进货结果: {result_text}")
                return {"success": True, "msg": result_text, "quantity": buy_num}
            else:
                logger.error("未能解析到进货结果")
                return {"success": False, "msg": "未能解析到进货结果", "quantity": buy_num}
        except Exception as e:
            logger.error(f"进货任务异常: {e}")
            return {"success": False, "msg": str(e), "quantity": buy_num}

    def __sale_task(self, sale_num: int):
        """出售任务：自动提交出售表单，跟随重定向并解析出售结果"""
        try:
            url = self._site_url + "/customgame.php?action=exchange"
            headers = {
                "cookie": self._cookie,
                "referer": self._site_url,
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
                "content-type": "application/x-www-form-urlencoded",
                "pragma": "no-cache",
            }
            proxies = self._get_proxies()

            # 构造POST参数
            data = {
                "option": 6,
                "saleTurnipNum": str(sale_num),
                "submit": "出售"
            }

            # 提交出售请求
            try:
                response = requests.post(url, headers=headers, data=data, proxies=proxies, timeout=30)
            except requests.exceptions.ProxyError as proxy_error:
                logger.warning(f"出售请求代理连接失败: {proxy_error}")
                if proxies:
                    logger.info("尝试不使用代理直接连接...")
                    try:
                        response = requests.post(url, headers=headers, data=data, proxies=None, timeout=30)
                    except Exception as direct_error:
                        logger.error(f"直接连接也失败: {direct_error}")
                        raise direct_error
                else:
                    raise proxy_error
            except Exception as request_error:
                logger.error(f"出售请求失败: {request_error}")
                raise request_error

            # 提取重定向URL（window.location.href）
            redirect_url = None
            pattern = r"window.location.href\s*=\s*['\"]([^'\"]*sale[^'\"]*)['\"]"
            match = re.search(pattern, response.text, re.DOTALL)
            if match:
                redirect_url = match.group(1)
                logger.info(f"提取到的出售结果重定向 URL: {redirect_url}")
            else:
                logger.error("未找到出售结果重定向 URL")
                return {"success": False, "msg": "未找到出售结果重定向 URL"}

            # 访问重定向URL，获取出售结果页面
            try:
                result_response = requests.get(redirect_url, headers=headers, proxies=proxies, timeout=30)
            except requests.exceptions.ProxyError as proxy_error:
                logger.warning(f"出售结果页面代理连接失败: {proxy_error}")
                if proxies:
                    logger.info("尝试不使用代理直接连接...")
                    try:
                        result_response = requests.get(redirect_url, headers=headers, proxies=None, timeout=30)
                    except Exception as direct_error:
                        logger.error(f"直接连接也失败: {direct_error}")
                        raise direct_error
                else:
                    raise proxy_error
            except Exception as request_error:
                logger.error(f"获取出售结果页面失败: {request_error}")
                raise request_error
            logger.info(f"出售结果页面状态码: {result_response.status_code}")

            # 解析出售结果页面，优先用class=striking的div
            html = etree.HTML(result_response.text)
            striking_texts = html.xpath("//div[@class='striking']/text()")
            result_text = " ".join([t.strip() for t in striking_texts if t.strip()])
            if not result_text:
                # 模糊查找
                result_texts = html.xpath("//*[contains(text(), '出售成功') or contains(text(), '出售失败') or contains(text(), '获得')]/text()")
                result_text = " ".join([t.strip() for t in result_texts if t.strip()])
            if not result_text:
                # 取页面所有文本，找包含"出售"字样的句子
                all_text = " ".join(html.xpath('//text()'))
                for line in all_text.split():
                    if '出售' in line:
                        result_text = line
                        break
            if result_text:
                logger.info(f"出售结果: {result_text}")
                return {"success": True, "msg": result_text, "quantity": sale_num}
            else:
                logger.error("未能解析到出售结果")
                return {"success": False, "msg": "未能解析到出售结果", "quantity": sale_num}
        except Exception as e:
            logger.error(f"出售任务异常: {e}")
            return {"success": False, "msg": str(e), "quantity": sale_num}

    def _calculate_purchase_quantity(self, farm_info: dict) -> int:
        """计算进货数量，基于价格阈值、余额和剩余配货量"""
        try:
            # 如果阈值为0或负数，不进行自动进货
            if self._purchase_price_threshold <= 0:
                logger.info("进货价格阈值未设置或无效，不执行自动进货")
                return 0
                
            # 获取农场价格和象草余额,增加空值检查
            farm_price_str = farm_info.get("farm", {}).get("价格", "0")
            bonus_str = farm_info.get("bonus", "0").replace("象草", "").strip()
            remaining_supply_str = farm_info.get("farm", {}).get("剩余配货量", "0")
            
            # 检查是否为空字符串
            if not farm_price_str or not bonus_str or not remaining_supply_str:
                logger.warning(f"农场价格、象草余额或剩余配货量为空: 价格={farm_price_str}, 余额={bonus_str}, 剩余配货量={remaining_supply_str}")
                return 0
                
            try:
                # 去除字符串中的逗号后再转换
                bonus_str = bonus_str.replace(",", "")
                remaining_supply_str = remaining_supply_str.replace(",", "")
                farm_price = float(farm_price_str)
                bonus = float(bonus_str)
                remaining_supply = int(remaining_supply_str)
                logger.debug(f"转换后的数值: 价格={farm_price}, 余额={bonus}, 剩余配货量={remaining_supply}")
            except ValueError as e:
                logger.error(f"转换价格、余额或剩余配货量为数值时出错: {e}, 价格={farm_price_str}, 余额={bonus_str}, 剩余配货量={remaining_supply_str}")
                return 0
            
            # 如果价格高于阈值或余额不足或剩余配货量为0,返回0
            if farm_price > self._purchase_price_threshold or bonus <= 0 or remaining_supply <= 0:
                logger.info(f"价格({farm_price})高于阈值({self._purchase_price_threshold})或余额({bonus})不足或剩余配货量({remaining_supply})为0,不执行进货")
                return 0
                
            # 计算可购买数量(考虑余额和剩余配货量)
            max_quantity_by_bonus = int(bonus / farm_price)
            max_quantity = min(max_quantity_by_bonus, remaining_supply)
            if max_quantity <= 0:
                logger.info(f"计算出的最大可购买数量({max_quantity})小于等于0,不执行进货")
                return 0
                
            # 根据比例计算实际购买数量
            purchase_quantity = int(max_quantity * self._purchase_quantity_ratio)
            
            # 确保不超过最大可购买数量
            final_quantity = min(purchase_quantity, max_quantity)
            logger.info(f"计算进货数量: 最大可买(余额)={max_quantity_by_bonus}, 剩余配货量={remaining_supply}, 比例={self._purchase_quantity_ratio}, 最终数量={final_quantity}")
            return final_quantity
            
        except Exception as e:
            logger.error(f"计算进货数量时发生错误: {e}")
            return 0

    def _should_expiry_sale(self) -> bool:
        """检查是否应该执行到期出售（每周六14点前）"""
        try:
            if not self._expiry_sale_enabled:
                return False
                
            # 获取当前时间
            now = datetime.now()
            current_weekday = now.weekday()  # 0=周一, 6=周日
            
            # 检查是否是周六（weekday=5）且时间在14:00前
            if current_weekday == 5:  # 周六
                current_hour = now.hour
                
                # 如果是周六且时间在14:00前（即13:59及之前），执行到期出售
                if current_hour < 14:  # 14点前执行
                    logger.info(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}，周六14点前，满足到期出售条件")
                    return True
                    
            logger.info(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}，不满足到期出售条件（需要周六14点前）")
            return False
            
        except Exception as e:
            logger.error(f"检查到期出售条件时发生错误: {e}")
            return False

    def _calculate_expiry_sale_quantity(self, farm_info: dict) -> int:
        """计算到期出售数量（全部出售）"""
        try:
            # 获取蔬菜店信息
            shop = farm_info.get("vegetable_shop", {})
            stock_str = shop.get("库存", "0")
            
            # 检查是否为空字符串
            if not stock_str:
                logger.warning(f"库存为空: 库存={stock_str}")
                return 0
                
            try:
                # 去除字符串中的逗号后再转换
                stock_str = stock_str.replace(",", "")
                stock = int(stock_str)
                logger.debug(f"转换后的库存数值: 库存={stock}")
            except ValueError as e:
                logger.error(f"转换库存为数值时出错: {e}, 库存={stock_str}")
                return 0
            
            # 如果库存为0,返回0
            if stock <= 0:
                logger.info(f"库存({stock})为0,不执行到期出售")
                return 0
                
            # 到期出售：全部出售
            logger.info(f"到期出售：库存={stock}，全部出售")
            return stock
            
        except Exception as e:
            logger.error(f"计算到期出售数量时发生错误: {e}")
            return 0

    def _calculate_sale_quantity(self, farm_info: dict) -> int:
        """计算出售数量，基于盈利百分比和价格阈值"""
        try:
            # 获取蔬菜店信息,增加空值检查
            shop = farm_info.get("vegetable_shop", {})
            market_price_str = shop.get("市场单价", "0")
            stock_str = shop.get("库存", "0")
            cost_str = shop.get("成本", "0")
            
            # 检查是否为空字符串
            if not market_price_str or not stock_str or not cost_str:
                logger.warning(f"市场单价、库存或成本为空: 单价={market_price_str}, 库存={stock_str}, 成本={cost_str}")
                return 0
                
            try:
                # 去除字符串中的逗号后再转换
                market_price_str = market_price_str.replace(",", "")
                stock_str = stock_str.replace(",", "")
                cost_str = cost_str.replace(",", "")
                market_price = float(market_price_str)
                stock = int(stock_str)
                cost = float(cost_str)
                logger.debug(f"转换后的数值: 市场单价={market_price}, 库存={stock}, 成本={cost}")
            except ValueError as e:
                logger.error(f"转换市场单价、库存或成本为数值时出错: {e}, 单价={market_price_str}, 库存={stock_str}, 成本={cost_str}")
                return 0
            
            # 如果库存为0,返回0
            if stock <= 0:
                logger.info(f"库存({stock})为0,不执行出售")
                return 0
            
            # 计算盈利百分比
            if cost > 0:
                profit_percentage = ((market_price - cost) / cost) * 100
                logger.debug(f"盈利百分比计算: 市场单价={market_price}, 成本={cost}, 盈利百分比={profit_percentage:.2f}%")
            else:
                profit_percentage = 0
                logger.warning("成本为0，无法计算盈利百分比")
            
            # 判断是否满足出售条件
            should_sell = False
            sell_reason = ""
            
            # 检查盈利百分比阈值
            if self._sale_profit_percentage > 0 and profit_percentage >= self._sale_profit_percentage:
                should_sell = True
                sell_reason = f"盈利百分比({profit_percentage:.2f}%)达到阈值({self._sale_profit_percentage}%)"
            # 检查价格阈值（如果盈利百分比未设置或未达到）
            elif self._sale_price_threshold > 0 and market_price >= self._sale_price_threshold:
                should_sell = True
                sell_reason = f"市场单价({market_price})达到阈值({self._sale_price_threshold})"
            
            if not should_sell:
                logger.info(f"不满足出售条件: 盈利百分比={profit_percentage:.2f}%, 盈利阈值={self._sale_profit_percentage}%, 市场单价={market_price}, 价格阈值={self._sale_price_threshold}")
                return 0
                
            # 根据比例计算实际出售数量
            sale_quantity = int(stock * self._sale_quantity_ratio)
            
            # 确保不超过库存
            final_quantity = min(sale_quantity, stock)
            logger.info(f"计算出售数量: 库存={stock}, 比例={self._sale_quantity_ratio}, 最终数量={final_quantity}, 原因={sell_reason}")
            return final_quantity
            
        except Exception as e:
            logger.error(f"计算出售数量时发生错误: {e}")
            return 0

    def _expiry_sale_task(self):
        """专门执行到期出售任务"""
        logger.info("开始执行到期出售任务")
        
        try:
            # 检查是否启用到期出售
            if not self._expiry_sale_enabled:
                logger.info("到期出售功能未启用，跳过执行")
                return {"success": True, "msg": "到期出售功能未启用"}
            
            # 检查是否满足到期出售条件
            if not self._should_expiry_sale():
                logger.info("不满足到期出售条件，跳过执行")
                return {"success": True, "msg": "不满足到期出售条件"}
            
            # 获取农场和蔬菜店信息
            logger.info("开始获取农场和蔬菜店信息...")
            farm_info = self.__farm_and_vegetable()
            
            # 检查是否成功获取信息
            if not farm_info:
                msg = "😵‍💫获取农场信息失败！"
                logger.error(msg)
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【🐘象岛农场】到期出售任务失败",
                        text=f"━━━━━━━━━━━━━━\n"
                             f"⚠️ 错误提示：\n"
                             f"😵‍💫 获取农场信息失败！\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"📊 状态信息：\n"
                             f"🌿 当前象草余额：{farm_info.get('bonus', '未知')}")
                return {"success": False, "msg": "获取农场信息失败"}

            # 执行到期出售
            auto_trade_results = []
            expiry_sale_quantity = self._calculate_expiry_sale_quantity(farm_info)
            
            if expiry_sale_quantity > 0:
                logger.info(f"开始到期出售,数量: {expiry_sale_quantity}")
                expiry_sale_result = self.__sale_task(expiry_sale_quantity)
                if expiry_sale_result.get("success"):
                    auto_trade_results.append(f"🕐 到期出售成功: {expiry_sale_result.get('msg')} (数量: {expiry_sale_quantity}kg)")
                else:
                    auto_trade_results.append(f"❌ 到期出售失败: {expiry_sale_result.get('msg')} (尝试数量: {expiry_sale_quantity}kg)")
            else:
                logger.info("到期出售：库存为0，无需出售")
                auto_trade_results.append("🕐 到期出售：库存为0，无需出售")

            # 重新获取农场和蔬菜店信息以更新状态
            logger.info("到期出售完成，重新获取农场和蔬菜店信息以更新状态...")
            farm_info = self.__farm_and_vegetable()
            if not farm_info:
                logger.error("到期出售后未能重新获取农场信息！")

            # 生成报告
            logger.info("开始生成到期出售报告...")
            rich_text_report = self.generate_farm_report(farm_info)
            
            # 添加到期出售结果到报告末尾
            rich_text_report += "\n\n━━━━━━━━━━━━━━\n"
            rich_text_report += "🕐 到期出售结果：\n"
            rich_text_report += "\n".join(auto_trade_results)
                
            logger.info(f"到期出售报告生成完成：\n{rich_text_report}")

            # 保存历史记录
            farm_dict = {
                "date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                "farm_info": farm_info,
                "auto_trade_results": auto_trade_results if auto_trade_results else None,
                "task_type": "expiry_sale"  # 标记为到期出售任务
            }

            # 读取历史记录
            history = self.get_data('sign_dict') or []
            history.append(farm_dict)
            # 始终按时间降序排序，确保最新的在前
            history = sorted(history, key=lambda x: x.get("date") or "", reverse=True)
            # 只保留最新的N条记录
            if len(history) > self._history_count:
                history = history[:self._history_count]
            self.save_data(key="sign_dict", value=history)

            # 发送通知
            if self._notify:
                self.post_message(
                    mtype=NotificationType.SiteMessage,
                    title="【🐘象岛农场】到期出售任务完成",
                    text=rich_text_report)
                    
            # 成功时返回结构化响应
            return {
                "success": True, 
                "msg": "到期出售任务已执行",
                "auto_trade_results": auto_trade_results if auto_trade_results else None
            }
                
        except Exception as e:
            logger.error(f"执行到期出售任务时发生异常: {e}")
            return {"success": False, "msg": f"执行到期出售任务异常: {e}"}

    def _battle_task(self):
        """执行农场任务，包括获取信息、自动交易和生成报告"""
        logger.info("开始执行农场任务")
        
        try:
            # 获取农场和蔬菜店信息
            logger.info("开始获取农场和蔬菜店信息...")
            farm_info = self.__farm_and_vegetable()
            
            # 检查是否成功获取信息
            if not farm_info:
                msg = "😵‍💫获取农场信息失败！"
                logger.error(msg)
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【🐘象岛农场】任务失败",
                        text=f"━━━━━━━━━━━━━━\n"
                             f"⚠️ 错误提示：\n"
                             f"😵‍💫 获取农场信息失败！\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"📊 状态信息：\n"
                             f"🌿 当前象草余额：{farm_info.get('bonus', '未知')}")
                return {"success": False, "msg": "获取农场信息失败"}

            # 自动交易处理
            auto_trade_results = []
            
            # 自动进货
            if self._auto_purchase_enabled:
                purchase_quantity = self._calculate_purchase_quantity(farm_info)
                if purchase_quantity > 0:
                    logger.info(f"开始自动进货,数量: {purchase_quantity}")
                    purchase_result = self.__purchase_task(purchase_quantity)
                    if purchase_result.get("success"):
                        auto_trade_results.append(f"✅ 自动进货成功: {purchase_result.get('msg')} (数量: {purchase_quantity}kg)")
                    else:
                        auto_trade_results.append(f"❌ 自动进货失败: {purchase_result.get('msg')} (尝试数量: {purchase_quantity}kg)")
                        
            # 自动出售
            if self._auto_sale_enabled:
                sale_quantity = self._calculate_sale_quantity(farm_info)
                if sale_quantity > 0:
                    logger.info(f"开始自动出售,数量: {sale_quantity}")
                    sale_result = self.__sale_task(sale_quantity)
                    if sale_result.get("success"):
                        auto_trade_results.append(f"✅ 自动出售成功: {sale_result.get('msg')} (数量: {sale_quantity}kg)")
                    else:
                        auto_trade_results.append(f"❌ 自动出售失败: {sale_result.get('msg')} (尝试数量: {sale_quantity}kg)")

            # 到期出售（优先级高于普通自动出售）
            if self._should_expiry_sale():
                expiry_sale_quantity = self._calculate_expiry_sale_quantity(farm_info)
                if expiry_sale_quantity > 0:
                    logger.info(f"开始到期出售,数量: {expiry_sale_quantity}")
                    expiry_sale_result = self.__sale_task(expiry_sale_quantity)
                    if expiry_sale_result.get("success"):
                        auto_trade_results.append(f"🕐 到期出售成功: {expiry_sale_result.get('msg')} (数量: {expiry_sale_quantity}kg)")
                    else:
                        auto_trade_results.append(f"❌ 到期出售失败: {expiry_sale_result.get('msg')} (尝试数量: {expiry_sale_quantity}kg)")
                else:
                    logger.info("到期出售：库存为0，无需出售")

            # 重新获取农场和蔬菜店信息以更新状态
            logger.info("自动交易完成，重新获取农场和蔬菜店信息以更新状态...")
            farm_info = self.__farm_and_vegetable()
            if not farm_info:
                logger.error("自动交易后未能重新获取农场信息！")

            # 生成报告
            logger.info("开始生成报告...")
            rich_text_report = self.generate_farm_report(farm_info)
            
            # 如果有自动交易结果,添加到报告末尾
            if auto_trade_results:
                rich_text_report += "\n\n━━━━━━━━━━━━━━\n"
                rich_text_report += "🤖 自动交易结果：\n"
                rich_text_report += "\n".join(auto_trade_results)
                
            logger.info(f"报告生成完成：\n{rich_text_report}")

            # 保存历史记录
            farm_dict = {
                "date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                "farm_info": farm_info,
                "auto_trade_results": auto_trade_results if auto_trade_results else None
            }

            # 读取历史记录
            history = self.get_data('sign_dict') or []
            history.append(farm_dict)
            # 始终按时间降序排序，确保最新的在前
            history = sorted(history, key=lambda x: x.get("date") or "", reverse=True)
            # 只保留最新的N条记录
            if len(history) > self._history_count:
                history = history[:self._history_count]
            self.save_data(key="sign_dict", value=history)

            # 发送通知
            if self._notify:
                self.post_message(
                    mtype=NotificationType.SiteMessage,
                    title="【🐘象岛农场】任务完成",
                    text=rich_text_report)
                    
            # 成功时返回结构化响应
            return {
                "success": True, 
                "msg": "任务已执行",
                "auto_trade_results": auto_trade_results if auto_trade_results else None
            }
                
        except Exception as e:
            logger.error(f"执行农场任务时发生异常: {e}")
            return {"success": False, "msg": f"执行农场任务异常: {e}"}

    def generate_farm_report(self, farm_info: dict) -> str:
        """生成格式化的农场状态报告"""
        try:
            # 获取农场和蔬菜店信息
            farm = farm_info.get("farm", {})
            vegetable_shop = farm_info.get("vegetable_shop", {})
            bonus = farm_info.get("bonus", "未知")
            
            # 计算盈利百分比
            profit_percentage = "未知"
            try:
                market_price_str = vegetable_shop.get("市场单价", "0").replace(",", "")
                cost_str = vegetable_shop.get("成本", "0").replace(",", "")
                if market_price_str and cost_str:
                    market_price = float(market_price_str)
                    cost = float(cost_str)
                    if cost > 0:
                        profit_percentage = f"{((market_price - cost) / cost) * 100:.2f}%"
                    else:
                        profit_percentage = "成本为0"
            except (ValueError, ZeroDivisionError):
                profit_percentage = "计算失败"
            
            # 生成报告
            report = f"━━━━━━━━━━━━━━\n"
            report += f"🌿 象草余额：\n"
            report += f"{bonus}\n\n"
            
            report += f"━━━━━━━━━━━━━━\n"
            report += f"🏡 农场信息：\n"
            report += f"📝 名称：{farm.get('名称', '未知')}\n"
            report += f"📊 类型：{farm.get('类型', '未知')}\n"
            report += f"📈 状态：{farm.get('状态', '未知')}\n"
            report += f"💰 价格：{farm.get('价格', '未知')}\n"
            report += f"📦 剩余配货量：{farm.get('剩余配货量', '未知')}kg\n"
            report += f"📄 说明：{farm.get('说明', '无')}\n\n"
            
            report += f"━━━━━━━━━━━━━━\n"
            report += f"🥬 蔬菜店信息：\n"
            report += f"📝 名称：{vegetable_shop.get('名称', '未知')}\n"
            report += f"💰 市场单价：{vegetable_shop.get('市场单价', '未知')}\n"
            report += f"📦 库存：{vegetable_shop.get('库存', '未知')}\n"
            report += f"💵 成本：{vegetable_shop.get('成本', '未知')}\n"
            report += f"📈 盈利百分比：{profit_percentage}\n"
            report += f"📈 开店累计盈利：{vegetable_shop.get('开店累计盈利', '未知')}\n"
            report += f"🎯 盈利目标：{vegetable_shop.get('盈利目标', '未知')}\n"
            report += f"📦 可卖数量：{vegetable_shop.get('可卖数量', '未知')}\n"
            report += f"📄 说明：{vegetable_shop.get('说明', '无')}\n"
            
            # 添加时间戳
            report += f"\n⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return report
        except Exception as e:
            logger.error(f"生成农场报告时发生异常: {e}")
            return "象岛农场\n生成报告时发生错误，请检查日志以获取更多信息。"

    def _get_proxies(self):
        """获取代理设置"""
        if not self._use_proxy:
            logger.info("未启用代理")
            return None
            
        try:
            # 获取系统代理设置
            if hasattr(settings, 'PROXY') and settings.PROXY:
                logger.info(f"使用系统代理: {settings.PROXY}")
                
                # 测试代理连接（可选，但会增加延迟）
                # 如果代理测试失败，可以记录警告但继续使用
                try:
                    proxy_host = settings.PROXY.get('http', '').replace('http://', '').split(':')[0]
                    proxy_port = int(settings.PROXY.get('http', '').replace('http://', '').split(':')[1])
                    
                    # 简单测试代理端口是否可达
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)  # 3秒超时
                    result = sock.connect_ex((proxy_host, proxy_port))
                    sock.close()
                    
                    if result != 0:
                        logger.warning(f"代理服务器 {proxy_host}:{proxy_port} 连接测试失败，但将继续尝试使用")
                except Exception as proxy_test_error:
                    logger.warning(f"代理连接测试失败: {proxy_test_error}，但将继续尝试使用")
                
                return settings.PROXY
            else:
                logger.warning("系统代理未配置")
                return None
        except Exception as e:
            logger.error(f"获取代理设置出错: {str(e)}")
            return None

    def get_state(self) -> bool:
        """获取插件状态"""
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取命令"""
        pass

    def _get_config(self) -> Dict[str, Any]:
        """API接口: 返回当前插件配置"""
        return {
            "enabled": self._enabled,
            "notify": self._notify,
            "cookie": self._cookie,
            "cron": self._cron,
            "farm_interval": self._farm_interval,
            "use_proxy": self._use_proxy,
            "retry_count": self._retry_count,
            # 自动交易配置
            "auto_purchase_enabled": self._auto_purchase_enabled,
            "purchase_price_threshold": self._purchase_price_threshold,
            "purchase_quantity_ratio": self._purchase_quantity_ratio,
            "auto_sale_enabled": self._auto_sale_enabled,
            "sale_price_threshold": self._sale_price_threshold,
            "sale_quantity_ratio": self._sale_quantity_ratio,
            "sale_profit_percentage": self._sale_profit_percentage,
            "expiry_sale_enabled": self._expiry_sale_enabled  # 新增：到期出售开关
        }

    def _save_config(self, config_payload: dict) -> Dict[str, Any]:
        """API接口: 保存插件配置"""
        logger.info(f"{self.plugin_name}: 收到配置保存请求: {config_payload}")
        try:
            # 布尔类型兼容处理
            def to_bool(val):
                if isinstance(val, bool):
                    return val
                if isinstance(val, str):
                    return val.lower() == 'true'
                return bool(val)

            self._enabled = to_bool(config_payload.get('enabled', self._enabled))
            self._notify = to_bool(config_payload.get('notify', self._notify))
            self._cookie = config_payload.get('cookie', self._cookie)
            self._use_proxy = to_bool(config_payload.get('use_proxy', self._use_proxy))
            self._cron = config_payload.get('cron', self._cron)
            self._farm_interval = int(config_payload.get('farm_interval', self._farm_interval))
            self._retry_count = int(config_payload.get('retry_count', self._retry_count))
            
            # 自动交易配置
            self._auto_purchase_enabled = to_bool(config_payload.get('auto_purchase_enabled', self._auto_purchase_enabled))
            self._purchase_price_threshold = float(config_payload.get('purchase_price_threshold', self._purchase_price_threshold))
            self._purchase_quantity_ratio = float(config_payload.get('purchase_quantity_ratio', self._purchase_quantity_ratio))
            self._auto_sale_enabled = to_bool(config_payload.get('auto_sale_enabled', self._auto_sale_enabled))
            self._sale_price_threshold = float(config_payload.get('sale_price_threshold', self._sale_price_threshold))
            self._sale_quantity_ratio = float(config_payload.get('sale_quantity_ratio', self._sale_quantity_ratio))
            self._sale_profit_percentage = float(config_payload.get('sale_profit_percentage', self._sale_profit_percentage))
            self._expiry_sale_enabled = to_bool(config_payload.get('expiry_sale_enabled', self._expiry_sale_enabled))  # 新增：到期出售开关

            # 准备保存的配置
            config_to_save = {
                "enabled": self._enabled,
                "notify": self._notify,
                "cookie": self._cookie,
                "cron": self._cron,
                "farm_interval": self._farm_interval,
                "use_proxy": self._use_proxy,
                "retry_count": self._retry_count,
                # 自动交易配置
                "auto_purchase_enabled": self._auto_purchase_enabled,
                "purchase_price_threshold": self._purchase_price_threshold,
                "purchase_quantity_ratio": self._purchase_quantity_ratio,
                "auto_sale_enabled": self._auto_sale_enabled,
                "sale_price_threshold": self._sale_price_threshold,
                "sale_quantity_ratio": self._sale_quantity_ratio,
                "sale_profit_percentage": self._sale_profit_percentage,
                "expiry_sale_enabled": self._expiry_sale_enabled  # 新增：到期出售开关
            }
            
            # 保存配置
            self.update_config(config_to_save)
            
            # 重新初始化插件
            self.stop_service()
            self.init_plugin(config_to_save)
            
            logger.info(f"{self.plugin_name}: 配置已保存并通过 init_plugin 重新初始化。当前内存状态: enabled={self._enabled}")
            
            # 返回最终状态
            return {"message": "配置已成功保存", "saved_config": self._get_config()}

        except Exception as e:
            logger.error(f"{self.plugin_name}: 保存配置时发生错误: {e}", exc_info=True)
            # 返回当前内存配置
            return {"message": f"保存配置失败: {e}", "error": True, "saved_config": self._get_config()}

    def _get_status(self) -> Dict[str, Any]:
        """API接口: 返回当前插件状态和历史记录"""
        last_run = self.get_data('last_run_results') or []
        history = self.get_data('sign_dict') or []
        
        # 获取公共定时任务信息
        next_run_time = "未配置定时任务"
        time_until_next = None
        task_status = "未启用"
        
        if self._enabled and self._cron:
            try:
                scheduler = Scheduler()
                
                # 获取所有定时任务
                schedule_list = scheduler.list()
                
                # 查找当前插件的任务
                plugin_task = None
                for task in schedule_list:
                    if task.provider == self.plugin_name:
                        plugin_task = task
                        break
                
                if plugin_task:
                    # 获取任务状态
                    task_status = plugin_task.status
                    
                    # 获取下次执行时间
                    if hasattr(plugin_task, 'next_run') and plugin_task.next_run:
                        next_run_time = plugin_task.next_run
                        time_until_next = plugin_task.next_run
                        if isinstance(next_run_time, str) and re.match(r'^(\d+小时)?(\d+分钟)?(\d+秒)?$', next_run_time):
                            next_run_time += "后"
                    else:
                        if plugin_task.status == "正在运行":
                            next_run_time = "正在运行中"
                            time_until_next = "正在运行中"
                        else:
                            next_run_time = "等待执行"
                            time_until_next = "等待执行"
                else:
                    task_status = "未找到任务"
                    next_run_time = f"按配置执行: {self._cron}"
                    
            except Exception as e:
                logger.warning(f"获取公共定时任务信息失败: {e}")
                task_status = "获取失败"
                next_run_time = f"按配置执行: {self._cron}"

        return {
            "enabled": self._enabled,
            "cron": self._cron,
            "cookie": self._cookie,
            "farm_interval": self._farm_interval,
            "use_proxy": self._use_proxy,
            "retry_count": self._retry_count,
            "next_run_time": next_run_time,
            "time_until_next": time_until_next,
            "task_status": task_status,
            "last_run_results": last_run,
            "sign_dict": history
        }

    def get_render_mode(self) -> Tuple[str, Optional[str]]:
        """返回Vue渲染模式和组件路径"""
        return "vue", "dist/assets"

    def get_api(self) -> List[Dict[str, Any]]:
        """注册插件API"""
        return [
            {
                "path": "/config",
                "endpoint": self._get_config,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取配置"
            },
            {
                "path": "/config",
                "endpoint": self._save_config,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "保存配置"
            },
            {
                "path": "/status",
                "endpoint": self._get_status,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取状态"
            },
            {
                "path": "/purchase",
                "endpoint": self.__purchase_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "进货"
            },
            {
                "path": "/sale",
                "endpoint": self.__sale_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "出售"
            },
            {
                "path": "/task",
                "endpoint": self._battle_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "执行任务"
            },
            {
                "path": "/expiry_sale",
                "endpoint": self._expiry_sale_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "执行到期出售任务"
            },
            {
                "path": "/cookie",
                "endpoint": self.__get_cookie,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "使用已配置站点cookie"
            }
        ]

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """Vue模式下必须实现，返回None和初始配置数据"""
        return None, self._get_config()

    def get_page(self) -> List[dict]:
        """Vue模式下必须实现，返回空列表"""
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """注册插件公共服务"""
        services = []
        
        # 主定时任务（用户配置的Cron）
        if self._enabled and self._cron:
            services.append({
                "id": "VicomoFarm",
                "name": "象岛农场 - 定时任务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self._battle_task,
                "kwargs": {}
            })
        
        # 到期出售定时任务（每周六13:50执行，确保在14点前完成）
        if self._enabled and self._expiry_sale_enabled:
            services.append({
                "id": "VicomoFarm_ExpirySale",
                "name": "象岛农场 - 到期出售任务",
                "trigger": CronTrigger(day_of_week=5, hour=13, minute=50),  # 每周六13:50
                "func": self._expiry_sale_task,
                "kwargs": {}
            })
        
        return services

    def __get_cookie(self):
        """获取站点cookie"""
        try:
            if self._cookie and str(self._cookie).strip().lower() != "cookie":
                return {"success": True, "cookie": self._cookie}
                
            site = self._siteoper.get_by_domain('ptvicomo.net')
            if not site:
                return {"success": False, "msg": "未添加象岛站点！"}
                
            cookie = site.cookie
            if not cookie or str(cookie).strip().lower() == "cookie":
                return {"success": False, "msg": "站点cookie为空或无效，请在站点管理中配置！"}
                
            self._cookie = cookie
            return {"success": True, "cookie": cookie}
            
        except Exception as e:
            logger.error(f"获取站点cookie失败: {e}")
            return {"success": False, "msg": f"获取站点cookie失败: {e}"}
        
    def stop_service(self) -> None:
        """退出插件，注销定时任务并释放资源"""
        try:
            # 注销定时任务
            Scheduler().remove_plugin_job(self.__class__.__name__.lower())
            logger.info(f"{self.plugin_name}: 插件服务已停止")
        except Exception as e:
            logger.error(f"{self.plugin_name}: stop_service 执行异常: {e}")