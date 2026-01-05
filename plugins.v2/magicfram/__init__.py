import re
import time
import base64
import requests
from pathlib import Path
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

class MagicFram(_PluginBase):
    # 插件名称
    plugin_name = "Vue-好学农场"
    # 插件描述
    plugin_desc = "支持一键收获、种植、养殖，定时自动化任务。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/magicfram.png"
    # 插件版本
    plugin_version = "1.0.2"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "magicfram_"
    # 加载顺序
    plugin_order = 27
    # 可使用的用户级别
    auth_level = 2

    # 配置与状态
    _enabled: bool = False
    _notify: bool = True
    _cron: Optional[str] = None
    _cookie: Optional[str] = None
    _auto_plant: bool = False  # 自动种植
    _auto_sell: bool = False   # 自动出售
    _auto_sell_threshold: float = 0.0 # 自动出售阈值
    _expiry_sale_enabled: bool = False # 临期自动出售
    _use_proxy: bool = False   # 使用代理
    _retry_count: int = 3      # 重试次数
    _retry_interval: int = 5   # 重试间隔(秒)
    
    _siteoper = None

    def __init__(self):
        super().__init__()

    @staticmethod
    def _to_bool(val: Any) -> bool:
        """转换布尔值"""
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() == 'true'
        return bool(val)

    @staticmethod
    def _to_float(val: Any, default: float = 0.0) -> float:
        """转换浮点数"""
        try:
            return float(val)
        except:
            return default

    @staticmethod
    def _to_int(val: Any, default: int = 0) -> int:
        """转换整数"""
        try:
            return int(val)
        except:
            return default

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """初始化插件，加载配置并注册定时任务"""
        try:
            self.stop_service()
            self._siteoper = SiteOper()

            if config:
                self._enabled = self._to_bool(config.get("enabled", False))
                self._cron = config.get("cron") or "0 */4 * * *"
                self._cookie = config.get("cookie")
                self._notify = self._to_bool(config.get("notify", False))
                self._auto_plant = self._to_bool(config.get("auto_plant", False))
                self._auto_sell = self._to_bool(config.get("auto_sell", False))
                self._auto_sell_threshold = self._to_float(config.get("auto_sell_threshold"), 0.0)
                self._expiry_sale_enabled = self._to_bool(config.get("expiry_sale_enabled", False))
                self._use_proxy = self._to_bool(config.get("use_proxy", False))
                self._retry_count = self._to_int(config.get("retry_count"), 3)
                self._retry_interval = self._to_int(config.get("retry_interval"), 5)
                
            # 初始化站点URL
            site_info = self._get_site_info()
            if site_info and site_info[0]:
                self._site_url = site_info[0]
            else:
                self._site_url = "https://www.hxpt.org"
                logger.warning(f"{self.plugin_name}: 未找到站点配置，使用默认URL: {self._site_url}")
                
            if not self._enabled:
                logger.info(f"{self.plugin_name} 服务未启用")
                return
            if self._enabled and self._cron:
                logger.info(f"{self.plugin_name}: 已配置 CRON '{self._cron}'，任务将通过公共服务注册。")
            else:
                logger.info(f"{self.plugin_name}: 未配置定时任务。启动时配置: Enable={self._enabled}, Cron='{self._cron}'")
        except Exception as e:
            logger.error(f"{self.plugin_name} 服务启动失败: {str(e)}")

    def get_state(self) -> bool:
        """获取插件状态"""
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取命令"""
        pass

    def __get_cookie(self):
        """获取站点cookie"""
        try:
            if self._cookie and str(self._cookie).strip().lower() != "cookie":
                return {"success": True, "cookie": self._cookie}
                
            site = self._siteoper.get_by_domain('hxpt.org')
            if not site:
                return {"success": False, "msg": "未添加好学站点！"}
                
            cookie = site.cookie
            if not cookie or str(cookie).strip().lower() == "cookie":
                return {"success": False, "msg": "站点cookie为空或无效，请在站点管理中配置！"}
                
            self._cookie = cookie
            return {"success": True, "cookie": cookie}
            
        except Exception as e:
            logger.error(f"获取站点cookie失败: {e}")
            return {"success": False, "msg": f"获取站点cookie失败: {e}"}
    def get_api(self) -> List[dict]:
        """获取插件API配置"""
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
                "summary": "获取插件状态"
            },
            {
                "path": "/plant",
                "endpoint": self._plant_item,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "种植/养殖"
            },
            {
                "path": "/plant-all",
                "endpoint": self._plant_all,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "一键种植/养殖"
            },
            {
                "path": "/harvest",
                "endpoint": self._harvest_item,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "收获"
            },
            {
                "path": "/harvest-all",
                "endpoint": self._harvest_all,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "一键收获"
            },
            {
                "path": "/cookie",
                "endpoint": self.__get_cookie,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取站点Cookie"
            },
            {
                "path": "/sell",
                "endpoint": self._sell_item,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "出售物品"
            },
            {
                "path": "/sell-all",
                "endpoint": self._sell_all,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "一键出售"
            },
            {
                "path": "/refresh",
                "endpoint": self._refresh_data,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "强制刷新农场数据"
            }
        ]

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """Vue模式下必须实现，返回None和初始配置数据"""
        return None, self._get_config()

    def get_render_mode(self) -> Tuple[str, Optional[str]]:
        """返回Vue渲染模式和组件路径"""
        return "vue", "dist/assets"

    def get_page(self) -> List[dict]:
        """Vue模式下必须实现，返回空列表"""
        return []
    
    def _get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        config = {
            "enabled": self._enabled,
            "notify": self._notify,
            "cron": self._cron or "",
            "cookie": self._cookie or "",
            "auto_plant": self._auto_plant,
            "auto_sell": self._auto_sell,
            "auto_sell_threshold": self._auto_sell_threshold,
            "expiry_sale_enabled": self._expiry_sale_enabled,
            "use_proxy": self._use_proxy,
            "retry_count": self._retry_count,
            "retry_interval": self._retry_interval
        }
        return config

    def _get_status(self) -> Dict[str, Any]:
        """API接口: 返回当前插件状态和历史记录"""
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
            "use_proxy": self._use_proxy,
            "next_run_time": next_run_time,
            "time_until_next": time_until_next,
            "task_status": task_status,
            "farm_status": self.get_data("farm_status"),
            "last_run": self.get_data("last_run")
        }

    def get_service(self) -> List[Dict[str, Any]]:
        """注册插件公共服务"""
        services = []
        
        if self._enabled and self._cron:
            services.append({
                "id": "magicfram",
                "name": "好学农场 - 定时任务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self._farm_task,
                "kwargs": {}
            })
            
        return services

    def stop_service(self):
        """停止服务"""
        try:
            Scheduler().remove_plugin_job(self.__class__.__name__.lower())
            logger.info(f"{self.plugin_name}: 插件服务已停止")
        except Exception as e:
            logger.debug(f"{self.plugin_name} 停止服务失败: {str(e)}")

    def _get_site_info(self) -> Tuple[Optional[str], Optional[str]]:
        try:
            if not self._siteoper:
                logger.warning("SiteOper 未初始化")
                return None, None
            
            site = self._siteoper.get_by_domain('hxpt.org')
            
            if not site:
                logger.warning("未找到好学PT站点配置（hxpt.org），请在站点管理中添加")
                return None, None
            
            site_url = site.url if hasattr(site, 'url') else None
            user_agent = site.ua if hasattr(site, 'ua') else None
            
            return site_url, user_agent
            
        except Exception as e:
            logger.error(f"获取站点信息失败: {str(e)}")
            return None, None

    def _farm_task(self):
        """定时任务"""
        logger.info(f"{self.plugin_name} 定时任务开始执行")
        self.save_data("last_run", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        logs = {'harvest': [], 'plant': [], 'sell': [], 'expiry_sell': []}
        
        try:
            # 1. 自动种植/养殖 (包含收获)
            if self._auto_plant:
                plant_logs = self._run_auto_plant()
                if plant_logs.get('harvest'):
                    logs['harvest'].extend(plant_logs['harvest'])
                if plant_logs.get('plant'):
                    logs['plant'].extend(plant_logs['plant'])
            
            # 2. 自动出售
            if self._auto_sell:
                sell_logs = self._run_auto_sell()
                if sell_logs:
                    logs['sell'].extend(sell_logs)

            # 3. 临期自动出售
            if self._expiry_sale_enabled:
                expiry_logs = self._run_expiry_sale()
                if expiry_logs:
                    logs['expiry_sell'].extend(expiry_logs)

            # 4. 更新状态数据
            data = self.get_farm_data()
            if data:
                self.save_data("farm_status", data)
                
            # 发送通知: 只要通知开启，就发送 (包含由 logs 决定的任务日志 和 farm_data 决定的状态报告)
            if self._notify:
                self._send_message(logs, data)
                
        except Exception as e:
            logger.error(f"{self.plugin_name} 定时任务执行失败: {str(e)}")

    def _run_auto_plant(self) -> Dict[str, List[str]]:
        """执行自动种植流程"""
        logs = {'harvest': [], 'plant': []}
        try:
            # 1. 识别成熟作物 (以便记录日志)
            pre_data = self.get_farm_data()
            if pre_data:
                for c in pre_data.get("crops", []):
                    if c.get("state") == "ripe": logs['harvest'].append(c.get("name"))
                for a in pre_data.get("animals", []):
                    if a.get("state") == "ripe": logs['harvest'].append(a.get("name"))
            
            # 2. 一键收获
            harvest_msg = self.harvest_all()
            if harvest_msg:
                logger.info(f"{self.plugin_name}: {harvest_msg}")
            else:
                logs['harvest'] = []
            
            # 3. 获取最新数据 (准备种植)
            data = self.get_farm_data()
            if not data:
                return logs

            # 4. 种植农作物
            for crop in data.get("crops", []):
                if crop.get("state") == "empty":
                    crop_id = crop.get("id")
                    # 尝试种植
                    if crop_id and self.plant("crop", crop_id):
                        name = crop.get("name", "未知作物")
                        msg = f"{name}"
                        logger.info(f"{self.plugin_name}: 种植 {name} 成功")
                        logs['plant'].append(msg)
                    else:
                         logger.warning(f"{self.plugin_name}: 种植作物 ID={crop_id} 失败")
            
            # 5. 养殖动物
            for animal in data.get("animals", []):
                if animal.get("state") == "empty":
                    animal_id = animal.get("id")
                    if animal_id and self.plant("animal", animal_id):
                         name = animal.get("name", "未知动物")
                         msg = f"{name}"
                         logger.info(f"{self.plugin_name}: 养殖 {name} 成功")
                         logs['plant'].append(msg)
                    else:
                         logger.warning(f"{self.plugin_name}: 养殖动物 ID={animal_id} 失败")

        except Exception as e:
            logger.error(f"{self.plugin_name}: 自动种植执行异常: {e}")
            
        return logs

    def _run_auto_sell(self) -> List[str]:
        """执行自动出售"""
        msgs = []
        try:
            result = self._sell_all()
            if result.get("success"):
                 msg = result.get('msg')
                 logger.info(f"{self.plugin_name}: 自动出售成功 - {msg}")
                 if result.get("success_count", 0) > 0:
                     msgs.append(f"{msg}")
        except Exception as e:
             logger.error(f"{self.plugin_name}: 自动出售执行异常: {e}")
        return msgs

    def _run_expiry_sale(self) -> List[str]:
        """执行临期出售"""
        msgs = []
        try:
            data = self.get_farm_data()
            if not data or "warehouse" not in data:
                return msgs
            
            warehouse = data["warehouse"]
            for item in warehouse:
                # 解析剩余时间
                remaining = item.get("remaining_time", "")
                should_sell = False
                
                if "天" in remaining:
                    continue
                
                # 提取小时
                hours = 0
                match_h = re.search(r'(\d+)小时', remaining)
                if match_h:
                    hours = int(match_h.group(1))
                
                # 如果小于1小时
                if hours < 1:
                    should_sell = True
                
                if should_sell:
                    key = item.get("key")
                    if key:
                        self._sell_item({"key": key})
                        msg = f"临期: {item.get('name')}"
                        logger.info(f"{self.plugin_name}: 临期物品 {item.get('name')} 已自动出售")
                        msgs.append(msg)
                        
        except Exception as e:
            logger.error(f"{self.plugin_name}: 临期出售执行异常: {e}")
        return msgs

    def _get_proxies(self):
        """获取代理配置"""
        return settings.PROXY if self._use_proxy else None

    def _request(self, url: str, method: str = "GET", data: dict = None, params: dict = None) -> Optional[requests.Response]:
        """发送请求"""
        try:
            if not self._cookie:
                logger.error(f"{self.plugin_name}: 未配置Cookie")
                return None
            
            site_url, user_agent = self._get_site_info()
            
            if not site_url:
                site_url = "https://www.hxpt.org"
                logger.warning(f"未找到站点配置，使用默认URL: {site_url}")
            
            if not user_agent:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
                logger.warning("未找到站点UA配置，使用默认UA")
                
            headers = {
                "cookie": self._cookie,
                "referer": site_url,
                "user-agent": user_agent
            }
            
            proxies = self._get_proxies()
            
            retry_count = 0
            max_retries = self._retry_count
            
            while retry_count <= max_retries:
                try:
                    if method.upper() == "POST":
                        response = requests.post(url, headers=headers, data=data, proxies=proxies, timeout=30)
                    else:
                        response = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=30)
                        
                    if response.status_code == 200:
                        return response
                    else:
                        logger.warning(f"{self.plugin_name}: 请求失败 {url} - {response.status_code}，重试 {retry_count + 1}/{max_retries}")
                except Exception as e:
                    logger.warning(f"{self.plugin_name}: 请求异常 {url} - {str(e)}，重试 {retry_count + 1}/{max_retries}")
                
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(self._retry_interval)
            
            logger.error(f"{self.plugin_name}: 请求失败，已达到最大重试次数")
            return None
        except Exception as e:
            logger.error(f"{self.plugin_name}: 请求异常 {url} - {str(e)}")
            return None
    
    def _get_image_base64(self, name: str) -> str:
        """将本地图片转换为 base64 编码的 data URI"""
        
        name_to_file = {
            "小麦": "小麦.webp",
            "玉米": "玉米.webp",
            "土豆": "土豆.webp",
            "花生": "花生.webp",
            "鸡": "鸡.webp",
            "猪": "猪.webp",
            "牛": "牛.webp",
            "羊": "羊.webp"
        }
        
        filename = name_to_file.get(name)
        if not filename:
            return ""
        
        try:
            # 获取图片文件路径
            plugin_dir = Path(__file__).parent
            image_path = plugin_dir / "dist" / "public" / filename
            
            if not image_path.exists():
                logger.warning(f"图片文件不存在: {image_path}")
                return ""
            
            # 读取图片并转换为 base64
            with open(image_path, 'rb') as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/webp;base64,{base64_data}"
        except Exception as e:
            logger.error(f"转换图片为 base64 失败: {str(e)}")
            return ""

    def _parse_warehouse_table(self, table) -> List[Dict[str, Any]]:
        """解析仓库表格数据"""
        items = []
        rows = table.xpath('.//tr[position()>1]')
        for row in rows:
            cells = row.xpath('.//td/text()')
            link = row.xpath('.//a/@href')
            
            if len(cells) >= 4:
                item = {
                    "name": cells[0].strip(),
                    "quantity": cells[1].strip(),
                    "harvest_time": cells[2].strip(),
                    "remaining_time": cells[3].strip() if len(cells) > 3 else "",
                    "key": ""
                }
                
                # 提取 key 从链接
                if link:
                    match = re.search(r'key=([^&]+)', link[0])
                    if match:
                        item["key"] = match.group(1)
                
                items.append(item)
        return items

    def _parse_farm_item(self, item_element, item_type="crop"):
        """解析农场物品通用逻辑"""
        data = {}
        # 名称
        name_el = item_element.xpath('.//h3/text()')
        data["name"] = name_el[0].strip() if name_el else "未知"
        # 图片
        data["image"] = self._get_image_base64(data["name"])
        
        # 详细信息
        data["price"] = ""
        data["grow_time"] = ""
        data["double_chance"] = ""
        data["valid_days"] = ""
        
        info_el = item_element.xpath('.//div[@class="item-info"]//p/text()')
        for info in info_el:
            info = info.strip()
            if "价格:" in info:
                data["price"] = info.replace("价格:", "").strip()
            elif "成长时间:" in info:
                data["grow_time"] = info.replace("成长时间:", "").strip()
            elif "双倍收获:" in info or "概率" in info:
                data["double_chance"] = info.replace("双倍收获:", "").strip()
            elif "有效期:" in info:
                data["valid_days"] = info.replace("有效期:", "").strip()
        
        # 状态
        status_el = item_element.xpath('.//p[contains(@class, "growing-status")]/text()')
        if status_el:
            data["status"] = status_el[0].strip()
            # 提取纯剩余时间
            if "剩余时间" in data["status"]:
                data["remaining_time"] = data["status"].replace("剩余时间:", "").strip()
            data["state"] = "growing"
        else:
            btn_el = item_element.xpath('.//a[contains(@class, "btn")]')
            if btn_el:
                btn_href = btn_el[0].get("href", "")
                target_action = "plant" if item_type == "crop" else "breed"
                
                if f"action={target_action}" in btn_href:
                    data["state"] = "empty"
                    match = re.search(r'id=(\d+)', btn_href)
                    if match:
                        data["id"] = match.group(1)
                elif "action=harvest" in btn_href:
                    data["state"] = "ripe"
                    match = re.search(r'id=(\d+)', btn_href)
                    if match:
                        data["id"] = match.group(1)
                else:
                    data["state"] = "unknown"
            else:
                data["state"] = "unknown"
                
        return data

    def get_farm_data(self):
        """获取农场数据 (用于前端展示)"""
        site_url, _ = self._get_site_info()
        if not site_url:
            site_url = "https://www.hxpt.org"
        url = f"{site_url}/magic_fram.php"
        response = self._request(url)
        if not response:
            return None
            
        html = etree.HTML(response.text)
        data = {
           "bonus": "0",
           "crops": [],
           "animals": [],
           "warehouse": [],
           "market": []
        }
        
        try:
            # 1. 获取火花
            bonus_el = html.xpath('//div[contains(@class, "points-display")]/text()')
            if bonus_el:
                 data["bonus"] = bonus_el[0].replace("当前火花:", "").strip()

            # 2. 遍历各个区域
            sections = html.xpath('//div[contains(@class, "farm-section")]')
            for section in sections:
                title_el = section.xpath('.//h2/text()')
                if not title_el:
                    continue
                title = title_el[0].strip()
                
                # 农作物种植区
                if "农作物种植区" in title:
                    items = section.xpath('.//div[contains(@class, "farm-item")]')
                    for item in items:
                        data["crops"].append(self._parse_farm_item(item, "crop"))

                # 动物养殖区
                elif "动物养殖区" in title:
                    items = section.xpath('.//div[contains(@class, "farm-item")]')
                    for item in items:
                        data["animals"].append(self._parse_farm_item(item, "animal"))
                        
                # 仓库
                elif "仓库" in title:
                    warehouse_items = []
                    # 1. 解析当前页（第一页）表格
                    table = section.xpath('.//table[@class="warehouse-table"]')
                    if table:
                        warehouse_items.extend(self._parse_warehouse_table(table[0]))
                    
                    # 2. 检查分页并获取剩余数据
                    try:
                        pagination_info = section.xpath('.//div[@class="pagination-info"]/text()')
                        if pagination_info:
                            # 提取 "页 1 共 2" 中的总页数
                            match = re.search(r'共\s*(\d+)', pagination_info[0])
                            if match:
                                total_pages = int(match.group(1))
                                if total_pages > 1:
                                    logger.info(f"{self.plugin_name}: 仓库共有 {total_pages} 页，开始获取剩余分页数据")
                                    # 遍历剩余页面
                                    for page in range(2, total_pages + 1):
                                        try:
                                            # 注意：URL 可能会根据排序不同而变化，这里假设默认排序或沿用 expire_asc
                                            page_url = f"{url}?sort=expire_asc&page={page}"
                                            page_resp = self._request(page_url)
                                            if page_resp:
                                                page_html = etree.HTML(page_resp.text)
                                                page_tables = page_html.xpath('//table[@class="warehouse-table"]')
                                                if page_tables:
                                                    items = self._parse_warehouse_table(page_tables[0])
                                                    if items:
                                                        warehouse_items.extend(items)
                                                        logger.debug(f"{self.plugin_name}: 第 {page} 页获取到 {len(items)} 个物品")
                                            
                                            # 避免请求过快
                                            time.sleep(1)
                                        except Exception as page_error:
                                            logger.error(f"{self.plugin_name}: 获取第 {page} 页失败: {page_error}")
                    except Exception as e:
                        logger.error(f"{self.plugin_name}: 处理仓库分页异常: {e}")
                    
                    data["warehouse"] = warehouse_items
                
                # 菜市场
                elif "菜市场" in title or "市场" in title:
                    market_items = []
                    # 查找市场表格（有两个：农作物和动物）
                    categories = section.xpath('.//div[@class="market-category"]')
                    
                    for category in categories:
                        category_title = category.xpath('.//h3/text()')
                        item_type = "crop" if "农作物" in str(category_title) else "animal"
                        
                        rows = category.xpath('.//table[@class="market-table"]//tr[position()>1]')
                        for row in rows:
                            cells = row.xpath('.//td/text()')
                            if len(cells) >= 2:
                                market_item = {
                                    "name": cells[0].strip(),
                                    "price": cells[1].strip(),
                                    "type": item_type
                                }
                                market_items.append(market_item)
                    
                    data["market"] = market_items
                    
                    # --- 记录基础价格 (用于计算波动) ---
                    cost_map = {}
                    for c in data["crops"]:
                        if c.get("name") and c.get("price"):
                            cost_map[c["name"]] = c["price"]
                    for a in data["animals"]:
                        if a.get("name") and a.get("price"):
                            cost_map[a["name"]] = a["price"]
                    
                    # --- 记录价格趋势 (滚动存储最近6个点) ---
                    try:
                        today_str = datetime.now().strftime('%Y-%m-%d')
                        current_hour = datetime.now().hour
                        slot = (current_hour // 4) * 4
                        key = f"{today_str}-{slot}"
                        
                        market_trends = self.get_data("market_trends") or {}
                        
                        # 兼容旧数据重置
                        if "date" in market_trends:
                            market_trends = {"version": 2, "data": {}}
                        
                        if "data" not in market_trends:
                            market_trends["data"] = {}
                            
                        trends_data = market_trends["data"]
                        
                        for item in market_items:
                            name = item["name"]
                            price_str = re.sub(r'[^\d.]', '', str(item["price"]))
                            price = float(price_str) if price_str else 0
                            
                            if name not in trends_data:
                                trends_data[name] = []
                            
                            history = trends_data[name]
                            
                            record = {
                                "slot": slot,
                                "price": price,
                                "key": key,
                                "label": f"{slot}:00"
                            }
                            
                            # 更新或追加
                            if history and history[-1].get("key") == key:
                                history[-1] = record
                            else:
                                history.append(record)
                            
                            # 保持最近 6 条
                            if len(history) > 6:
                                history.pop(0)
                        
                        self.save_data("market_trends", market_trends)
                        data["market_trends"] = market_trends
                    except Exception as e:
                        logger.error(f"{self.plugin_name}: 记录价格趋势失败: {e}")

                    # 计算价格波动 (基于成本价)
                    for item in data["market"]:
                        try:
                            # 解析当前价格 (移除可能的非数字字符)
                            price_str = re.sub(r'[^\d.]', '', str(item["price"]))
                            current_price = float(price_str) if price_str else 0
                            
                            item_name = item["name"]
                            
                            # 获取成本价
                            cost_price_str = cost_map.get(item_name, "0")
                            cost_price_clean = re.sub(r'[^\d.]', '', str(cost_price_str))
                            cost_price = float(cost_price_clean) if cost_price_clean else 0
                            
                            # "last_price" 字段现在用于显示成本价
                            item["last_price"] = cost_price if cost_price > 0 else "未知"
                            item["change_pct"] = 0
                            item["change"] = 0
                            
                            if cost_price > 0:
                                change = current_price - cost_price
                                change_pct = (change / cost_price) * 100
                                item["change"] = change
                                item["change_pct"] = round(change_pct, 2)
                                
                        except Exception as e:
                            logger.error(f"计算价格波动出错: {e}")
                            item["last_price"] = "未知"
                            item["change_pct"] = 0      
            return data
            
        except Exception as e:
            logger.error(f"{self.plugin_name} 解析数据失败: {str(e)}")
            return None

    def harvest_all(self) -> Optional[str]:
        """一键收获
        :return: 成功返回成功消息，失败返回None
        """
        url = f"{self._site_url}/magic_fram.php"
        params = {"action": "harvest_all"}
        response = self._request(url, params=params)
        if response and "收获成功" in response.text:
            msg = "一键收获成功"
            # 尝试提取收获统计信息
            if "共收获" in response.text:
                match = re.search(r'共收获\s*(\d+)\s*项', response.text)
                if match:
                    msg += f"，共 {match.group(1)} 项"
            
            logger.info(f"{self.plugin_name}: {msg}")
            return msg
        return None

    def plant(self, type_name: str, id: int):
        """种植/养殖"""
        url = f"{self._site_url}/magic_fram.php"
        action = "plant" if type_name == "crop" else "breed"
        params = {
            "action": action,
            "type": type_name,
            "id": id
        }
        response = self._request(url, params=params)
        return response is not None

    def harvest(self, type_name: str, id: int):
        """单独收获"""
        site_url, _ = self._get_site_info()
        if not site_url:
            site_url = "https://www.hxpt.org"
        url = f"{site_url}/magic_fram.php"
        params = {
            "action": "harvest",
            "type": type_name,
            "id": id
        }
        response = self._request(url, params=params)
        return response is not None

    def _sell_item(self, payload: dict = None):
        """出售物品"""
        if payload is None:
            payload = {}
        
        key = payload.get('key')
        if not key:
            return {"success": False, "msg": "缺少参数 key"}
            
        site_url, _ = self._get_site_info()
        if not site_url:
            site_url = "https://www.hxpt.org"
        url = f"{site_url}/magic_fram.php"
        params = {
            "action": "sell",
            "key": key
        }
        response = self._request(url, params=params)
        if response and "出售成功" in response.text:
            return {"success": True, "msg": "出售成功"}
        return {"success": False, "msg": "出售失败"}

    def _sell_all(self):
        """一键出售"""
        # 1. 获取最新仓库数据
        data = self.get_farm_data()
        if not data or "warehouse" not in data:
            return {"success": False, "msg": "获取仓库数据失败"}
        
        warehouse = data["warehouse"]
        if not warehouse:
            return {"success": True, "msg": "仓库为空，无需出售"}
            
        success_count = 0
        fail_count = 0
        skip_count = 0
        start_time = time.time()
        timeout_limit = 25 # 25秒超时保护
        
        # 构建市场价格映射 (用于计算利润)
        market_map = {}
        if self._auto_sell_threshold > 0:
            for m in data.get("market", []):
                market_map[m["name"]] = m

        # 2. 遍历出售
        for item in warehouse:
            # 超时检查
            if time.time() - start_time > timeout_limit:
                logger.warning(f"{self.plugin_name}: 一键出售执行超时，已中断。")
                break

            key = item.get("key")
            name = item.get("name")
            if not key:
                continue
            
            # 盈利检查
            if self._auto_sell_threshold > 0 and name in market_map:
                m_item = market_map[name]
                try:
                    # 获取当前价格
                    price_str = re.sub(r'[^\d.]', '', str(m_item.get("price", "0")))
                    current_price = float(price_str) if price_str else 0
                    
                    # 获取成本价 (在 get_farm_data 中已处理并存入 last_price)
                    cost_str = str(m_item.get("last_price", "0"))
                    if cost_str == "未知":
                        cost_price = 0
                    else:
                        cost_price = float(cost_str)
                    
                    if cost_price > 0:
                        profit_pct = (current_price - cost_price) / cost_price * 100
                        if profit_pct < self._auto_sell_threshold:
                            logger.info(f"{self.plugin_name}: {name} 盈利 {profit_pct:.2f}% < 阈值 {self._auto_sell_threshold}%，跳过出售")
                            skip_count += 1
                            continue
                except Exception as e:
                    logger.warning(f"{self.plugin_name}: 计算 {name} 盈利出错: {e}，默认出售")

            res = self._sell_item({"key": key})
            if res and res.get("success"):
                success_count += 1
                # 缩短延时到 0.2s
                time.sleep(0.2)
            else:
                fail_count += 1
                
        msg = f"一键出售完成: 成功 {success_count} 个, 失败 {fail_count} 个"
        if skip_count > 0:
            msg += f", 跳过 {skip_count} 个(未达盈利阈值)"
        if time.time() - start_time > timeout_limit:
            msg += " (超时中断)"
            
        return {
            "success": True, 
            "msg": msg,
            "success_count": success_count,
            "fail_count": fail_count,
            "skip_count": skip_count
        }

    def _plant_all(self, payload: dict = None):
        """API: 一键种植/养殖"""
        if payload is None:
            payload = {}
        
        item_type = payload.get('type', '')
        if item_type not in ['crop', 'animal']:
             return {"success": False, "msg": "参数 type 错误 (crop/animal)"}
        
        type_cn = "种植" if item_type == "crop" else "养殖"

        # 1. 获取最新农场数据
        data = self.get_farm_data()
        if not data:
            return {"success": False, "msg": "获取农场数据失败"}
        
        items = data.get("crops", []) if item_type == "crop" else data.get("animals", [])
        if not items:
            return {"success": True, "msg": f"{type_cn}区数据为空"}
            
        success_count = 0
        fail_count = 0
        start_time = time.time()
        timeout_limit = 25 # 25秒超时保护
        
        # 2. 遍历种植
        for item in items:
            # 超时检查
            if time.time() - start_time > timeout_limit:
                logger.warning(f"{self.plugin_name}: 一键{type_cn}执行超时，已中断。")
                break

            if item.get("state") == "empty":
                item_id = item.get("id")
                if item_id:
                     # 复用 plant 方法
                     if self.plant(item_type, item_id):
                         success_count += 1
                         logger.info(f"{self.plugin_name}: 自动{type_cn} {item.get('name')} 成功")
                         time.sleep(0.5) # 避免请求过快
                     else:
                         fail_count += 1
                         logger.warning(f"{self.plugin_name}: 自动{type_cn} {item.get('name')} 失败")
        
        # 刷新数据
        if success_count > 0:
            try:
                new_data = self.get_farm_data()
                if new_data:
                    self.save_data("farm_status", new_data)
                    self.save_data("last_run", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            except Exception as e:
                logger.error(f"{self.plugin_name}: 刷新数据失败 - {e}")

        msg = f"一键{type_cn}完成: 成功 {success_count} 个, 失败 {fail_count} 个"
        if time.time() - start_time > timeout_limit:
            msg += " (超时中断)"
            
        return {
            "success": True, 
            "msg": msg,
            "success_count": success_count,
            "fail_count": fail_count
        }
    
    def _save_config(self, config_payload: dict):
        """API: 保存配置"""
        logger.info(f"{self.plugin_name}: _save_config 接收到 payload: {config_payload}")
        try:
            # 更新配置
            self._enabled = self._to_bool(config_payload.get("enabled", self._enabled))
            logger.info(f"{self.plugin_name}: _save_config 转换后 enabled={self._enabled}, type={type(self._enabled)}")
            self._notify = self._to_bool(config_payload.get("notify", self._notify))
            self._cron = config_payload.get("cron", self._cron)
            self._cookie = config_payload.get("cookie", self._cookie)
            self._auto_plant = self._to_bool(config_payload.get("auto_plant", self._auto_plant))
            self._auto_sell = self._to_bool(config_payload.get("auto_sell", self._auto_sell))
            self._auto_sell_threshold = self._to_float(config_payload.get("auto_sell_threshold"), self._auto_sell_threshold)
            self._expiry_sale_enabled = self._to_bool(config_payload.get("expiry_sale_enabled", self._expiry_sale_enabled))
            self._use_proxy = self._to_bool(config_payload.get("use_proxy", self._use_proxy))
            self._retry_count = self._to_int(config_payload.get("retry_count"), self._retry_count)
            self._retry_interval = self._to_int(config_payload.get("retry_interval"), self._retry_interval)

            config_to_save = {
                "enabled": self._enabled,
                "notify": self._notify,
                "cron": self._cron,
                "cookie": self._cookie,
                "auto_plant": self._auto_plant,
                "auto_sell": self._auto_sell,
                "auto_sell_threshold": self._auto_sell_threshold,
                "expiry_sale_enabled": self._expiry_sale_enabled,
                "use_proxy": self._use_proxy,
                "retry_count": self._retry_count,
                "retry_interval": self._retry_interval
            }
            
            self.update_config(config_to_save)
            
            # 重新初始化插件
            self.stop_service()
            self.init_plugin(config_to_save)
            
            logger.info(f"{self.plugin_name}: 配置已保存并重新初始化")
            
            return {"message": "配置已成功保存", "saved_config": self._get_config()}
        except Exception as e:
            logger.error(f"更新配置失败: {str(e)}")
            return {
                "message": f"保存配置失败: {e}",
                "error": True
            }
    
    def _refresh_data(self):
        """API: 强制刷新农场数据"""
        try:
            logger.info(f"{self.plugin_name}: 开始强制刷新农场数据")
            # 从站点获取最新数据
            new_data = self.get_farm_data()
            
            if new_data:
                # 保存新数据
                self.save_data("farm_status", new_data)
                self.save_data("last_run", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                logger.info(f"{self.plugin_name}: 农场数据刷新成功")
                
                return {
                    "success": True,
                    "farm_status": new_data,
                    "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "message": "数据刷新成功"
                }
            else:
                logger.error(f"{self.plugin_name}: 获取农场数据失败")
                return {
                    "success": False,
                    "message": "获取农场数据失败"
                }
        except Exception as e:
            logger.error(f"{self.plugin_name}: 刷新农场数据异常 - {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def _get_state(self):
        """API: 获取农场状态 - 优先返回历史数据"""
        try:
            # 1. 尝试获取历史数据
            saved_data = self.get_data("farm_status")
            last_update = self.get_data("last_run")
            
            if saved_data:
                # 返回历史数据
                logger.info(f"返回历史农场数据，最后更新时间: {last_update}")
                return {
                    "farm_status": saved_data,
                    "last_update": last_update
                }
            else:
                # 如果没有历史数据，返回空数据结构
                logger.info("暂无历史数据，返回空数据结构")
                return {
                    "farm_status": {
                        "bonus": "0",
                        "crops": [],
                        "animals": [],
                        "warehouse": [],
                        "market": []
                    },
                    "last_update": None
                }
        except Exception as e:
            logger.error(f"获取农场状态失败: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def _plant_item(self, payload: dict = None):
        """API: 种植/养殖"""
        if payload is None:
            payload = {}
        
        item_type = payload.get('item_type', '')
        item_id = payload.get('item_id', '')
        try:
            url = f"{self._site_url}/magic_fram.php"
            action = "plant" if item_type == "crop" else "breed"
            action_name = "种植" if item_type == "crop" else "养殖"
            params = {
                "action": action,
                "type": item_type,
                "id": item_id
            }

            response = self._request(url, params=params)
            if response and response.status_code == 200:
                # 检查响应内容判断是否成功
                if "成功" in response.text or "种植" in response.text or "养殖" in response.text:
                    logger.info(f"{self.plugin_name}: {action_name}成功 - type={item_type}, id={item_id}")
                    
                    # 刷新并保存新数据
                    try:
                        from datetime import datetime
                        new_data = self.get_farm_data()
                        if new_data:
                            self.save_data("farm_status", new_data)
                            self.save_data("last_run", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            logger.info(f"{self.plugin_name}: {action_name}后数据已保存")
                    except Exception as save_error:
                        logger.warning(f"{self.plugin_name}: 保存数据失败 - {str(save_error)}")
                        
                    return {
                        "success": True,
                        "message": f"{action_name}成功"
                    }
                else:
                    error_msg = "操作失败"
                    # 尝试从响应中提取错误信息
                    if "火花不足" in response.text:
                        error_msg = "火花不足"
                    elif "已" in response.text:
                        error_msg = "该位置已有作物/动物"
                    
                    logger.warning(f"{self.plugin_name}: {action_name}失败 - {error_msg}")
                    return {
                        "success": False,
                        "message": error_msg
                    }
            else:
                logger.error(f"{self.plugin_name}: 请求失败")
                return {
                    "success": False,
                    "message": "请求失败"
                }
        except Exception as e:
            logger.error(f"{self.plugin_name}: 种植/养殖异常 - {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def _harvest_item(self, payload: dict = None):
        """API: 收获"""
        if payload is None:
            payload = {}
        
        item_type = payload.get('item_type', '')
        item_id = payload.get('item_id', '')
        
        try:
            url = f"{self._site_url}/magic_fram.php"
            params = {
                "action": "harvest",
                "type": item_type,
                "id": item_id
            }
            
            response = self._request(url, params=params)
            if response and response.status_code == 200:
                # 检查响应内容判断是否成功
                if "收获成功" in response.text or "获得" in response.text:
                    logger.info(f"{self.plugin_name}: 收获成功 - type={item_type}, id={item_id}")
                    
                    # 尝试提取收获信息（火花数量等）
                    reward_info = ""
                    if "火花" in response.text:
                        # 简单提取火花信息
                        import re
                        match = re.search(r'(\d+)\s*火花', response.text)
                        if match:
                            reward_info = f"，获得 {match.group(1)} 火花"
                    
                    # 刷新并保存新数据
                    try:
                        from datetime import datetime
                        new_data = self.get_farm_data()
                        if new_data:
                            self.save_data("farm_status", new_data)
                            self.save_data("last_run", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            logger.info(f"{self.plugin_name}: 收获后数据已保存")
                    except Exception as save_error:
                        logger.warning(f"{self.plugin_name}: 保存数据失败 - {str(save_error)}")
                    
                    return {
                        "success": True,
                        "message": f"收获成功{reward_info}"
                    }
                else:
                    error_msg = "收获失败"
                    if "未成熟" in response.text:
                        error_msg = "作物/动物未成熟"
                    elif "不存在" in response.text:
                        error_msg = "该位置没有可收获的内容"
                    
                    logger.warning(f"{self.plugin_name}: 收获失败 - {error_msg}")
                    return {
                        "success": False,
                        "message": error_msg
                    }
            else:
                logger.error(f"{self.plugin_name}: 请求失败")
                return {
                    "success": False,
                    "message": "请求失败"
                }
        except Exception as e:
            logger.error(f"{self.plugin_name}: 收获异常 - {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def _harvest_all(self):
        """API: 一键收获"""
        try:
            url = f"{self._site_url}/magic_fram.php"
            params = {"action": "harvest_all"}
            
            response = self._request(url, params=params)
            if response and response.status_code == 200:
                # 检查响应内容判断是否成功
                if "收获成功" in response.text or "收获" in response.text:
                    logger.info(f"{self.plugin_name}: 一键收获成功")
                    
                    # 尝试提取收获统计信息
                    harvest_info = ""
                    if "共收获" in response.text:
                        import re
                        match = re.search(r'共收获\s*(\d+)\s*项', response.text)
                        if match:
                            harvest_info = f"，共收获 {match.group(1)} 项"
                    
                    # 刷新并保存新数据
                    try:
                        from datetime import datetime
                        new_data = self.get_farm_data()
                        if new_data:
                            self.save_data("farm_status", new_data)
                            self.save_data("last_run", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            logger.info(f"{self.plugin_name}: 一键收获后数据已保存")
                    except Exception as save_error:
                        logger.warning(f"{self.plugin_name}: 保存数据失败 - {str(save_error)}")
                    
                    return {
                        "success": True,
                        "message": f"一键收获成功{harvest_info}"
                    }
                else:
                    # 即使没有可收获的也算成功
                    logger.info(f"{self.plugin_name}: 一键收获完成（可能无可收获项）")
                    return {
                        "success": True,
                        "message": "一键收获完成，暂无可收获项"
                    }
            else:
                logger.error(f"{self.plugin_name}: 请求失败")
                return {
                    "success": False,
                    "message": "请求失败"
                }
        except Exception as e:
            logger.error(f"{self.plugin_name}: 一键收获异常 - {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }

    def generate_farm_report(self, farm_info: dict, logs: dict = None) -> str:
        """生成格式化的农场状态报告"""
        try:
            if logs is None:
                logs = {}
                
            # 基础数据
            bonus = farm_info.get("bonus", "0")
            crops = farm_info.get("crops", [])
            animals = farm_info.get("animals", [])
            warehouse = farm_info.get("warehouse", [])
            
            # 统计作物状态
            crop_lines = []
            for c in crops:
                name = c.get("name", "未知")
                state = c.get("state")
                status_text = ""
                if state == "growing":
                    # 优先使用提取的剩余时间
                    rem_time = c.get("remaining_time")
                    if rem_time:
                        status_text = f"剩余时间: {rem_time}"
                    else:
                        status_text = c.get("status", "生长中")
                elif state == "ripe":
                    status_text = "已成熟 (需收获)"
                elif state == "empty":
                    status_text = "空闲"
                else:
                    status_text = "未知状态"
                
                crop_lines.append(f"{name}：{status_text}")
            
            # 统计动物状态
            animal_lines = []
            for a in animals:
                name = a.get("name", "未知")
                state = a.get("state")
                status_text = ""
                if state == "growing":
                    # 优先使用提取的剩余时间
                    rem_time = a.get("remaining_time")
                    if rem_time:
                        status_text = f"剩余时间: {rem_time}"
                    else:
                        status_text = a.get("status", "生长中")
                elif state == "ripe":
                    status_text = "已成熟 (需收获)"
                elif state == "empty":
                    status_text = "空闲"
                else:
                    status_text = "未知状态"
                animal_lines.append(f"{name}：{status_text}")

            # 生成报告
            report = f"━━━━━━━━━━━━━━\n"
            report += f"🌿 火花余额：{bonus}\n"
            
            report += f"━━━━━━━━━━━━━━\n"
            report += f"🏡 农场概况：\n"
            report += f"🌾 农作物种植区：共{len(crops)}块\n"
            report += "\n".join(crop_lines) + "\n\n\n"
            
            report += f"🐂 动物养殖区：共{len(animals)}个\n"
            report += "\n".join(animal_lines) + "\n\n\n"
            
            report += f"📦 仓库：共{len(warehouse)}类物品\n"

            plant_names = ["小麦", "玉米", "花生", "土豆"]
            animal_names = ["鸡", "猪", "牛", "羊"]
            p_count = 0
            a_count = 0
            for w in warehouse:
                w_name = w.get("name", "")
                if any(p in w_name for p in plant_names):
                    p_count += 1
                elif any(a in w_name for a in animal_names):
                    a_count += 1
            
            if p_count > 0 or a_count > 0:
                report += f"植物：{p_count}类\n"
                report += f"动物：{a_count}类\n"
            
            # 自动任务日志
            # logs: {'harvest': [], 'plant': [], 'sell': [], 'expiry_sell': []}
            task_log_str = ""
            
            if logs.get('harvest'):
                task_log_str += "\n自动收获成功：\n"
                for item in logs['harvest']:
                    task_log_str += f"✅{item}\n"
            
            if logs.get('plant'):
                task_log_str += "\n自动种植/养殖成功：\n"
                for item in logs['plant']:
                    task_log_str += f"✅{item}\n"
            
            if logs.get('sell'):
                task_log_str += "\n自动出售成功：\n"
                for item in logs['sell']:
                    task_log_str += f"✅{item}\n"

            if logs.get('expiry_sell'):
                task_log_str += "\n临期自动出售：\n"
                for item in logs['expiry_sell']:
                    task_log_str += f"✅{item}\n"

            if task_log_str:
                report += f"━━━━━━━━━━━━━━\n"
                report += f"🤖 自动任务日志：{task_log_str}"
            
            # 添加时间戳
            report += f"\n\n⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return report
        except Exception as e:
            logger.error(f"{self.plugin_name}: 生成农场报告时发生异常: {e}")
            return f"生成报告失败: {str(e)}"

    def _send_message(self, logs: dict, farm_data: dict = None):
        """发送通知消息"""
        if not logs and not farm_data:
            return
            
        title = f"【好学农场】任务报告"
        
        # 如果有农场数据，生成富文本报告
        if farm_data:
            report_text = self.generate_farm_report(farm_data, logs)
        else:
            report_text = "本次任务无详细农场数据。"
            
        try:
            self.post_message(
                mtype=NotificationType.SiteMessage,
                title=title,
                text=report_text,
                image=""
            )
            logger.info(f"{self.plugin_name}: 发送通知成功")
        except Exception as e:
            logger.error(f"{self.plugin_name}: 发送通知失败: {str(e)}")
