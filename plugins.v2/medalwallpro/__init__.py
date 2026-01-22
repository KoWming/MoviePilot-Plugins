from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.cache import Cache
from app.db.site_oper import SiteOper
from app.helper.sites import SitesHelper
from app.log import logger
from app.plugins import _PluginBase
from app.scheduler import Scheduler
from app.schemas import NotificationType
from .handlers import handler_manager

class MedalWallPro(_PluginBase):
    # 插件名称
    plugin_name = "Vue-勋章墙Pro"
    # 插件描述
    plugin_desc = "站点勋章购买提醒、统计、展示。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/Medal.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "medalwallpro_"
    # 加载顺序
    plugin_order = 28
    # 可使用的用户级别
    auth_level = 2
    
    # 过滤的站点列表
    FILTERED_SITES = ['星空', '聆音', '朱雀', '馒头', '家园', '朋友', '彩虹岛', '天空', '听听歌', '皇后']

    # 私有属性
    _enabled: bool = False
    _cron: Optional[str] = "0 9 * * *"
    _notify: bool = False
    _chat_sites: List[str] = []
    _use_proxy: bool = True
    _retry_times: int = 3
    _retry_interval: int = 5

    sites: SitesHelper = None
    siteoper: SiteOper = None
    _cache: Cache = None

    @staticmethod
    def _to_bool(val: Any) -> bool:
        """转换布尔值"""
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() == 'true'
        return bool(val)

    @staticmethod
    def _to_int(val: Any, default: int = 0) -> int:
        """转换整数"""
        try:
            return int(val)
        except:
            return default

    def __init__(self):
        super().__init__()
        self.sites = SitesHelper()
        self.siteoper = SiteOper()
        # 初始化缓存，TTL 24小时 (86400秒)
        self._cache = Cache(ttl=86400)

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """初始化插件"""
        try:
            self.stop_service()
            
            if config:
                self._enabled = self._to_bool(config.get("enabled", False))
                self._notify = self._to_bool(config.get("notify", False))
                self._use_proxy = self._to_bool(config.get("use_proxy", True))
                self._retry_times = self._to_int(config.get("retry_times"), 3)
                self._retry_interval = self._to_int(config.get("retry_interval"), 5)
                self._chat_sites = config.get("chat_sites", [])
                
                # 验证 Cron 表达式
                cron = config.get("cron") or "0 9 * * *"
                try:
                    CronTrigger.from_crontab(cron)
                    self._cron = cron
                except (ValueError, Exception) as e:
                    logger.warning(f"{self.plugin_name}: Cron表达式无效 '{cron}'，使用默认值 '0 9 * * *' - {str(e)}")
                    self._cron = "0 9 * * *"

                # 过滤掉已删除的站点
                all_sites = [site.id for site in self.siteoper.list_order_by_pri()] + [site.get("id") for site in self.__custom_sites()]
                self._chat_sites = [site_id for site_id in self._chat_sites if site_id in all_sites]
            
            # 初始化状态日志
            if not self._enabled:
                logger.info(f"{self.plugin_name} 服务未启用")
                return
            if self._enabled and self._cron:
                logger.info(f"{self.plugin_name}: 已配置 CRON '{self._cron}'，任务将通过公共服务注册")
        except Exception as e:
            logger.error(f"{self.plugin_name} 服务启动失败: {str(e)}")
            self._enabled = False
            
    def get_service(self) -> List[Dict[str, Any]]:
        """注册插件公共服务"""
        
        services = []
        if self._enabled and self._cron:
            services.append({
                "id": "medalwallpro",
                "name": "勋章墙Pro - 定时任务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.__process_all_sites,
                "kwargs": {}
            })
        return services

    def get_api(self) -> List[dict]:
        """
        注册插件API
        """
        return [
            {
                "path": "/config",
                "endpoint": self._get_config,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取插件配置"
            },
            {
                "path": "/config",
                "endpoint": self._save_config,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "保存插件配置"
            },
            {
                "path": "/sites",
                "endpoint": self._get_sites,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取可用站点"
            },
            {
                "path": "/medals",
                "endpoint": self._get_medals_api,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取勋章数据"
            },
            {
                "path": "/run",
                "endpoint": self._run_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "立即运行任务"
            },
            {
                "path": "/refresh_site",
                "endpoint": self._refresh_single_site,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "刷新单个站点勋章"
            },
            {
                "path": "/clear_cache",
                "endpoint": self._clear_cache,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "清理插件缓存"
            }
        ]

    def _clear_cache(self) -> Dict[str, Any]:
        """
        清理插件缓存
        """
        try:
            # 清理处理后的数据缓存
            self._cache.clear(region="medalwallpro")
            # 清理HTTP请求缓存 (handlers/base.py 中定义)
            self._cache.clear(region="medalwallpro_request")
            
            # 为了兼容性，也清理旧的持久化数据
            self.save_data('medals', [], 'zmmedalprog')
            return {"success": True, "message": "缓存已清理"}
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return {"success": False, "message": f"清理缓存失败: {e}"}

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """
        Vue模式下返回None和初始配置
        """
        return None, self._get_config()

    def get_render_mode(self) -> Tuple[str, str]:
        """
        获取插件渲染模式
        """
        return "vue", "dist/assets"

    def get_state(self) -> bool:
        """
        获取插件状态
        """
        return self._enabled

    def get_page(self) -> List[dict]:
        """
        Vue模式下返回空列表
        """
        return []

    def stop_service(self):
        """
        停止插件服务
        """
        try:
            Scheduler().remove_plugin_job("medalwallpro")
            logger.debug(f"{self.plugin_name}: 插件服务已停止")
        except Exception as e:
            logger.debug(f"{self.plugin_name} 停止服务失败: {str(e)}")

    def _get_config(self) -> Dict[str, Any]:
        """
        获取配置
        """
        return {
            "enabled": self._enabled,
            "cron": self._cron,
            "notify": self._notify,
            "chat_sites": self._chat_sites,
            "use_proxy": self._use_proxy,
            "retry_times": self._retry_times,
            "retry_interval": self._retry_interval
        }

    def _save_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """保存配置"""
        try:
            self._enabled = self._to_bool(config.get("enabled", False))
            self._notify = self._to_bool(config.get("notify", False))
            self._use_proxy = self._to_bool(config.get("use_proxy", True))
            self._retry_times = self._to_int(config.get("retry_times"), 3)
            self._retry_interval = self._to_int(config.get("retry_interval"), 5)
            self._chat_sites = config.get("chat_sites", [])
            
            # 验证 Cron 表达式
            cron = config.get("cron") or "0 9 * * *"
            try:
                CronTrigger.from_crontab(cron)
                self._cron = cron
            except (ValueError, Exception) as e:
                logger.warning(f"{self.plugin_name}: Cron表达式无效 '{cron}'，使用默认值 '0 9 * * *' - {str(e)}")
                self._cron = "0 9 * * *"

            config_to_save = {
                "enabled": self._enabled,
                "cron": self._cron,
                "notify": self._notify,
                "chat_sites": self._chat_sites,
                "use_proxy": self._use_proxy,
                "retry_times": self._retry_times,
                "retry_interval": self._retry_interval
            }
            
            self.update_config(config_to_save)
            
            # 重新初始化插件
            self.stop_service()
            self.init_plugin(config_to_save)
            
            logger.info(f"{self.plugin_name}: 配置已保存并重新初始化")
            
            return {
                "success": True,
                "message": "配置已保存",
                "saved_config": self._get_config()
            }
        except Exception as e:
            logger.error(f"{self.plugin_name}: 保存配置失败 - {str(e)}")
            return {
                "success": False,
                "message": f"保存配置失败: {str(e)}"
            }

    def _get_sites(self) -> List[Dict[str, Any]]:
        """
        获取可用站点列表
        """
        all_sites = [site for site in self.sites.get_indexers() 
                     if not site.get("public") and site.get("name") not in self.FILTERED_SITES] + self.__custom_sites()
        return [{"title": site.get("name"), "value": site.get("id")} for site in all_sites]
    
    def _fetch_site_data(self, site_id: str) -> List[Dict]:
        """
        尝试从缓存获取数据，如果没有则抓取
        """
        # 尝试从缓存获取
        cached_data = self._cache.get(str(site_id), region="medalwallpro")
        if cached_data is not None:
            return cached_data
            
        # 获取站点名称用于日志
        site_name = site_id
        try:
            site = self.siteoper.get(site_id)
            if not site:
                 custom_sites = self.__custom_sites()
                 site = next((s for s in custom_sites if s.get('id') == site_id), None)
            if site:
                site_name = site.name if hasattr(site, 'name') else site.get('name')
        except:
            pass

        # 缓存未命中，进行抓取
        logger.info(f"站点 【{site_name}】 缓存未命中，开始抓取...")
        data = self.get_medal_data(site_id)
        
        # 写入缓存
        if data is not None:
             self._cache.set(str(site_id), data, region="medalwallpro")
             
        return data or []

    def _get_medals_api(self) -> List[Dict[str, Any]]:
        """
        API获取勋章数据 - 聚合所有站点
        """
        if not self._chat_sites:
             # 如果未配置站点，尝试返回空或者之前可能存在的持久化数据(如果需要兼容)
             return []
             
        all_medals = []
        for site_id in self._chat_sites:
            medals = self._fetch_site_data(site_id)
            if medals:
                all_medals.extend(medals)
                
        logger.info(f"API 获取勋章数据(缓存聚合): {len(all_medals)} 个")
        return all_medals

    def _run_task(self) -> Dict[str, Any]:
        """
        立即运行任务
        """
        try:
            # 强制刷新所有站点
            self.__process_all_sites(force_refresh=True)
            return {"success": True, "message": "任务执行完成"}
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            return {"success": False, "message": f"任务执行失败: {e}"}
    
    def _refresh_single_site(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        刷新单个站点的勋章数据
        """
        try:
            site_id = data.get('site_id')
            if not site_id:
                return {"success": False, "message": "站点ID不能为空"}
            
            # 获取站点名称用于日志
            site = self.siteoper.get(site_id)
            if not site:
                # 尝试从自定义站点获取
                custom_sites = self.__custom_sites()
                site = next((s for s in custom_sites if s.get('id') == site_id), None)
            
            site_name = site.name if site else site_id
            
            logger.info(f"开始强制刷新单个站点: {site_name}")
            
            # 强制重新抓取
            medals = self.get_medal_data(site_id)
            
            # 更新缓存
            self._cache.set(str(site_id), medals, region="medalwallpro")
            
            logger.info(f"站点 {site_name} 刷新完成: 获取 {len(medals)} 条新数据")
            
            return {
                "success": True,
                "message": f"已刷新站点: {site_name}",
                "medals": medals,
                "site_name": site_name
            }
        except Exception as e:
            logger.error(f"刷新单个站点失败: {str(e)}")
            return {"success": False, "message": f"刷新失败: {str(e)}"}


    def __custom_sites(self) -> list:
        """获取自定义站点列表"""
        custom_sites = []
        custom_sites_config = self.get_config("CustomSites")
        if custom_sites_config and custom_sites_config.get("enabled"):
            custom_sites = custom_sites_config.get("sites", [])
        return custom_sites

    def __process_all_sites(self, force_refresh: bool = False):
        """
        处理所有选中的站点
        :param force_refresh: 是否强制刷新缓存
        """
        logger.info(f"开始处理所有站点的勋章数据 (强制刷新: {force_refresh})")
        try:
            if not self._chat_sites:
                logger.error("未选择站点")
                return

            # 加载历史记录
            history_medals = self.get_data('history_medals') or []
            is_first_run = not bool(history_medals)
            
            # 统计变量
            total_sites_count = len(self._chat_sites)
            valid_sites_count = 0
            total_medals_count = 0
            owned_count = 0
            purchasable_count = 0
            failed_sites = []
            
            # 新上架勋章列表
            new_arrivals = []
            # 本次运行的所有勋章ID集合 (用于更新历史)
            current_medals_ids = set(history_medals) if history_medals else set()

            for site_id in self._chat_sites:
                try:
                    site = self.siteoper.get(site_id)
                    if not site:
                        continue
                        
                    site_name = site.name
                    valid_sites_count += 1
                    
                    if force_refresh:
                        medals = self.get_medal_data(site_id)
                        self._cache.set(str(site_id), medals, region="medalwallpro")
                    else:
                        medals = self.get_medal_data(site_id)
                        self._cache.set(str(site_id), medals, region="medalwallpro")

                    if not medals:
                        continue
                     
                    current_site_medals_count = len(medals)
                    total_medals_count += current_site_medals_count
                    
                    for medal in medals:
                        # 统计已拥有
                        if (medal.get('purchase_status') or '').strip() == '已拥有':
                            owned_count += 1
                        
                        # 统计可购买 (仅限当前有效时间段)
                        is_purchasable = False
                        if (medal.get('purchase_status') or '').strip() in ['购买', '赠送']:
                            if self.is_current_time_in_range(medal.get('saleBeginTime', ''), medal.get('saleEndTime', '')):
                                purchasable_count += 1
                                is_purchasable = True
                        
                        # 生成唯一ID: 站点名_勋章名
                        medal_id = f"{site_name}_{medal.get('name', '')}"
                        
                        # 如果是新出现的勋章，且当前可购买
                        if medal_id not in current_medals_ids and is_purchasable:
                            # 只有非首次运行才记录为“上新”
                            if not is_first_run:
                                new_arrivals.append(medal)
                        
                        # 更新当前ID集合
                        if is_purchasable:
                             current_medals_ids.add(medal_id)

                except Exception as e:
                    logger.error(f"处理站点 {site_id} 时发生错误: {str(e)}")
                    # 尝试获取站点名称失败的情况
                    site_name_err = site_id
                    try:
                        s = self.siteoper.get(site_id)
                        if s: site_name_err = s.name
                    except: pass
                    failed_sites.append(site_name_err)
                    continue
            
            # 保存最新的勋章历史
            self.save_data('history_medals', list(current_medals_ids))
            
            # 准备统计数据
            stats = {
                'enabled_sites': valid_sites_count,
                'total_medals': total_medals_count,
                'owned': owned_count,
                'purchasable': purchasable_count,
                'failed_sites': failed_sites
            }

            # 发送通知 (如果开启了通知)
            if self._notify:
                self.__send_notification(stats, new_arrivals)
                    
            logger.info(f"处理完成，缓存 {total_medals_count} 个勋章，新发现 {len(new_arrivals)} 个")
            
        except Exception as e:
            logger.error(f"处理所有站点时发生错误: {str(e)}")


    def get_medal_data(self, site_id: str) -> List[Dict]:
        """
        获取站点勋章数据 (无缓存，直接抓取)
        """
        try:
            site = self.siteoper.get(site_id)
            if not site:
                return []
                
            handler = handler_manager.get_handler(site)
            # 配置handler
            if handler:
                handler._use_proxy = self._use_proxy
                
                # 注入图片缓存 (Base64)
                # 从旧的缓存数据中提取 {original_image_url: base64_image}
                cached_data = self._cache.get(str(site_id), region="medalwallpro")
                if cached_data:
                    img_cache = {}
                    for m in cached_data:
                        orig_url = m.get('original_image_url')
                        img_small = m.get('imageSmall')
                        # 只有当包含 Base64 数据且有原始 URL 时才缓存
                        if orig_url and img_small and img_small.startswith('data:'):
                            img_cache[orig_url] = img_small
                    
                    if img_cache:
                        handler.image_cache = img_cache
                        logger.debug(f"注入 {len(img_cache)} 个图片缓存到 {site.name} 处理器")
                
            if not handler:
                logger.error(f"未找到适配的站点处理器: {site.name}")
                return []
                
            medals = handler.fetch_medals(site)
            
            # 获取用户已拥有的勋章
            try:
                user_medals = handler.fetch_user_medals(site)
                if user_medals:
                    logger.info(f"获取到 {len(user_medals)} 个用户已拥有勋章，开始合并数据...")
                    # 创建名称到勋章的映射，方便查找
                    user_medal_map = {m['name']: m for m in user_medals if m.get('name')}
                    
                    # 遍历商店勋章，更新状态
                    for medal in medals:
                        medal_name = medal.get('name')
                        if medal_name and medal_name in user_medal_map:
                            # 更新状态为已拥有
                            medal['purchase_status'] = "已拥有"
                            
                            # 从映射中移除，标记为已匹配
                            del user_medal_map[medal_name]
                    
                    # 将剩余的用户勋章（商店未列出的）添加到列表
                    if user_medal_map:
                        logger.info(f"添加 {len(user_medal_map)} 个商店未列出的用户勋章")
                        medals.extend(user_medal_map.values())
                        
            except Exception as e:
                logger.error(f"合并用户勋章数据失败: {str(e)}")
            
            return medals
        except Exception as e:
            logger.error(f"获取勋章数据失败: {str(e)}")
            return []

    def is_current_time_in_range(self, start_time, end_time):
        """
        判断当前时间是否在给定的时间范围内
        """
        try:
            if start_time is None or end_time is None:
                return False
            if not start_time.strip() or not end_time.strip():
                return False
            # 处理"不限""长期"等特殊时间标记
            if "不限" in start_time or "不限" in end_time:
                return True
            if "长期" in end_time or "长期" in start_time:
                return True
            if "~" in start_time:
                start_time = start_time.split("~")[0].strip()
            if "~" in end_time:
                end_time = end_time.split("~")[0].strip()
                
            current_time = datetime.now()
            
            # 尝试两种时间格式
            time_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
            start_datetime = None
            end_datetime = None
            
            for fmt in time_formats:
                try:
                    start_datetime = datetime.strptime(start_time, fmt)
                    break
                except ValueError:
                    continue
            
            for fmt in time_formats:
                try:
                    end_datetime = datetime.strptime(end_time, fmt)
                    break
                except ValueError:
                    continue
            
            if start_datetime is None or end_datetime is None:
                logger.warning(f"无法解析时间格式: start={start_time}, end={end_time}")
                return False
                
            return start_datetime <= current_time <= end_datetime
        except Exception as e:
            logger.error(f"解析时间范围时发生错误: {e}")
            return False

    def __format_time(self, time_str):
        if not time_str:
            return ""
        return time_str.split(" ")[0]

    def __send_notification(self, stats: Dict, new_arrivals: List[Dict]):
        """发送通知"""
        # 1. 统计部分
        text_message = "──────────\n"
        text_message += "📈 勋章统计：\n"
        text_message += f"🌐 站点数量：已启用 {stats.get('enabled_sites', 0)} 个站点\n"
        text_message += f"🏅 勋章总数：{stats.get('total_medals', 0)}\n"
        text_message += f"✅ 已拥有：{stats.get('owned', 0)}\n"
        text_message += f"🛒 可购买：{stats.get('purchasable', 0)}\n"
        text_message += "──────────\n"
        
        # 2. 上新部分 (按站点分组)
        if new_arrivals:
            site_medals = {}
            for medal in new_arrivals:
                site = medal.get('site', '')
                if site not in site_medals:
                    site_medals[site] = []
                site_medals[site].append(medal)
            
            for site, medals in site_medals.items():
                text_message += f"【{site}】站点勋章上新：\n"
                for medal in medals:
                    text_message += f"🏅 勋章名称：{medal.get('name', '')}\n"
                    text_message += f"💰 价格：{medal.get('price', 0):,}\n"
                    
                    begin_time = self.__format_time(medal.get('saleBeginTime', '不限'))
                    end_time = self.__format_time(medal.get('saleEndTime', '长期'))
                    
                    text_message += f"⏰ 开售：{begin_time}\n"
                    text_message += f"⛔ 截止：{end_time}\n"
                    text_message += f"📅 有效期：{medal.get('validity', '')}\n"
                    text_message += f"📦 库存：{medal.get('stock', '未知')}\n"
                    text_message += "\n"
                text_message += "──────────\n"
        
        # 3. 失败站点部分
        failed_sites = stats.get('failed_sites', [])
        if failed_sites:
            text_message += f"❌ 失败站点：{', '.join(failed_sites)}\n"
            text_message += "──────────\n"
            
        text_message += f"⏰ 推送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        self.post_message(
            mtype=NotificationType.SiteMessage,
            title="【🎯 勋章墙Pro】勋章日报",
            text=text_message)
