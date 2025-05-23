# 标准库
import io
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 第三方库
import pytz
from PIL import Image
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 应用程序
from app.core.config import settings
from app.core.event import eventmanager
from app.db.site_oper import SiteOper
from app.helper.sites import SitesHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.schemas.types import EventType
from app.utils.http import RequestUtils
from app.utils.security import SecurityUtils

# 模块化处理器
from .handlers import handler_manager

class MedalWall(_PluginBase):
    # 插件名称
    plugin_name = "勋章墙"
    # 插件描述
    plugin_desc = "站点勋章购买提醒、统计、展示。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/Medal.png"
    # 插件版本
    plugin_version = "1.1"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "medalwall_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enabled: bool = False
    # 任务执行间隔
    _cron: Optional[str] = None
    _onlyonce: bool = False
    _notify: bool = False
    _chat_sites: List[str] = []     # 选择的站点列表
    _use_proxy: bool = True
    _timeout: int = 15              # 固定请求超时时间
    _retry_times: int = 3           # 重试次数
    _retry_interval: int = 5        # 重试间隔(秒)

    # 定时器
    _scheduler: Optional[BackgroundScheduler] = None
    # 私有属性
    sites: SitesHelper = None      # 站点助手实例
    siteoper: SiteOper = None      # 站点操作实例

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """
            初始化插件
        """
        # 停止现有任务
        self.stop_service()
        self._scheduler = BackgroundScheduler(timezone=settings.TZ)
        self.sites = SitesHelper()
        self.siteoper = SiteOper()
        
        if config:
            self._enabled = config.get("enabled", False)
            self._cron = config.get("cron")
            self._notify = config.get("notify", False)
            self._onlyonce = config.get("onlyonce", False)
            self._chat_sites = config.get("chat_sites", [])
            self._use_proxy = config.get("use_proxy", True)
            self._retry_times = config.get("retry_times", 3)
            self._retry_interval = config.get("retry_interval", 5)

            # 过滤掉已删除的站点
            all_sites = [site.id for site in self.siteoper.list_order_by_pri()] + [site.get("id") for site in self.__custom_sites()]
            self._chat_sites = [site_id for site_id in self._chat_sites if site_id in all_sites]

            # 保存配置
            self.update_config({
                "enabled": self._enabled,
                "onlyonce": self._onlyonce,
                "notify": self._notify,
                "use_proxy": self._use_proxy,
                "chat_sites": self._chat_sites,
                "cron": self._cron,
                "retry_times": self._retry_times,
                "retry_interval": self._retry_interval
            })

        if self._onlyonce:
            try:
                logger.info("勋章墙，立即运行一次")       
                self._scheduler.add_job(func=self.__process_all_sites, trigger='date',
                                    run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                    name="勋章墙")
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "onlyonce": False,
                    "cron": self._cron,
                    "enabled": self._enabled,
                    "notify": self._notify,
                    "chat_sites": self._chat_sites,
                    "retry_times": self._retry_times,
                    "retry_interval": self._retry_interval,
                    "use_proxy": self._use_proxy,
                })

                # 启动任务
                if self._scheduler and self._scheduler.get_jobs():
                    self._scheduler.print_jobs()
                    self._scheduler.start()
            except Exception as e:
                logger.error(f"勋章墙服务启动失败: {str(e)}")

    def get_service(self) -> List[Dict[str, Any]]:
        """
            注册插件公共服务
        """
        if self._enabled and self._cron:      
            return [
                {
                    "id": "Medal",
                    "name": "勋章墙 - 定时任务",
                    "trigger": CronTrigger.from_crontab(self._cron),
                    "func": self.__process_all_sites,
                    "kwargs":{}
                }
            ]
        return []

    def __process_all_sites(self):
        """
        处理所有选中的站点
        """
        logger.info("开始处理所有站点的勋章数据")
        try:
            if not self._chat_sites:
                logger.error("未选择站点")
                return

            # 存储所有可购买的勋章
            all_buy_medals = []
            # 存储需要推送的勋章
            notify_medals = []
            
            # 遍历所有选中的站点
            for site_id in self._chat_sites:
                try:
                    # 获取站点勋章数据
                    medals = self.get_medal_data(site_id)
                    if not medals:
                        continue
                        
                    # 获取站点信息
                    site = self.siteoper.get(site_id)
                    if not site:
                        continue
                        
                    # 筛选可购买的勋章
                    buy_medals = []
                    for medal in medals:
                        if self.is_current_time_in_range(medal.get('saleBeginTime', ''), medal.get('saleEndTime', '')):
                            buy_medals.append(medal)
                            
                    if buy_medals:
                        all_buy_medals.extend(buy_medals)
                        # 只将可购买的勋章加入推送列表
                        notify_medals.extend([m for m in buy_medals if (m.get('purchase_status') or '').strip() in ['购买', '赠送']])
                        
                except Exception as e:
                    logger.error(f"处理站点 {site_id} 时发生错误: {str(e)}")
                    continue
                    
            # 发送通知 - 只推送可购买的勋章
            if self._notify and notify_medals:
                # 按站点分组
                site_medals = {}
                for medal in notify_medals:
                    site = medal.get('site', '')
                    if site not in site_medals:
                        site_medals[site] = []
                    site_medals[site].append(medal)
                
                # 生成报告
                text_message = ""
                for site, medals in site_medals.items():
                    # 站点分隔线
                    text_message += "  ──────────\n"
                    # 站点名称
                    text_message += f"🌐 站点：{site}\n"
                    # 该站点的所有勋章
                    for medal in medals:
                        # 勋章名称和价格
                        text_message += f"《{medal.get('name', '')}》──价格: {medal.get('price', 0):,}\n"
                        # 购买时间
                        begin_time = self.__format_time(medal.get('saleBeginTime', '不限'))
                        end_time = self.__format_time(medal.get('saleEndTime', '不限'))
                        text_message += f" 购买时间：{begin_time}~{end_time}\n"
                        text_message += " \n"
                
                # 添加推送时间
                text_message += "──────────\n"
                text_message += f"⏰推送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                self.post_message(
                    mtype=NotificationType.SiteMessage,
                    title="【🎯 勋章墙】可购买勋章提醒：",
                    text=text_message)
                    
            # 保存所有勋章数据
            self.save_data('medals', all_buy_medals, 'zmmedal')
            
        except Exception as e:
            logger.error(f"处理所有站点时发生错误: {str(e)}")

    def get_medal_data(self, site_id: str) -> List[Dict]:
        """
        统一入口：获取站点勋章数据
        
        Args:
            site_id: 站点ID
            
        Returns:
            List[Dict]: 勋章数据列表
        """
        try:
            # 获取站点信息
            site = self.siteoper.get(site_id)
            if not site:
                logger.error(f"未找到站点信息: {site_id}")
                return []
                
            # 获取适配的处理器
            handler = handler_manager.get_handler(site)
            if not handler:
                logger.error(f"未找到适配的站点处理器: {site.name}")
                return []
                
            # 获取勋章数据
            medals = handler.fetch_medals(site)
            
            # 保存数据到缓存
            self.save_data(f'medals_{site_id}', medals, 'zmmedal')
            
            return medals
                
        except Exception as e:
            logger.error(f"获取勋章数据失败: {str(e)}")
            return []

    def __cache_img(self, url, site_name):
        """
        图片缓存功能(预留)
        用于将远程图片下载到本地缓存,目前未被使用
        """
        if not settings.GLOBAL_IMAGE_CACHE:
            logger.warning("全局图片缓存未启用")
            return
        if not url:
            logger.warning("图片URL为空")
            return
        
        logger.info(f"开始缓存图片: {url}")
        # 生成缓存路径
        sanitized_path = SecurityUtils.sanitize_url_path(url)
        # 使用插件数据目录作为基础路径
        base_path = self.get_data_path()
        # 使用站点名称作为缓存目录
        cache_path = base_path / site_name / sanitized_path
        logger.info(f"缓存路径: {cache_path}")
        
        # 没有文件类型，则添加后缀，在恶意文件类型和实际需求下的折衷选择
        if not cache_path.suffix:
            cache_path = cache_path.with_suffix(".jpg")
        # 确保缓存路径和文件类型合法
        if not SecurityUtils.is_safe_path(base_path, cache_path, settings.SECURITY_IMAGE_SUFFIXES):
            logger.warning(f"缓存路径或文件类型不合法: {url}, sanitized path: {sanitized_path}")
            return
        # 本地存在缓存图片，则直接跳过
        if cache_path.exists():
            logger.info(f"图片已缓存: {cache_path}")
            return

        # 请求远程图片
        response = RequestUtils(ua=settings.USER_AGENT).get_res(url=url)
        if not response:
            logger.warning(f"获取图片失败: {url}")
            return
        # 验证下载的内容是否为有效图片
        try:
            Image.open(io.BytesIO(response.content)).verify()
        except Exception as e:
            logger.warning(f"图片格式无效: {url}, 错误: {e}")
            return

        if not cache_path:
            return

        try:
            if not cache_path.parent.exists():
                logger.info(f"创建缓存目录: {cache_path.parent}")
                cache_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=cache_path.parent, delete=False) as tmp_file:
                tmp_file.write(response.content)
                temp_path = Path(tmp_file.name)
            temp_path.replace(cache_path)
            logger.info(f"图片缓存成功: {cache_path}")

        except Exception as e:
            logger.error(f"缓存图片失败: {cache_path}, 错误: {e}")
            return

    def is_current_time_in_range(self,start_time,end_time):
        """
            判断当前时间是否在给定的时间范围内。
        """
        try:
            # 处理None值的情况
            if start_time is None or end_time is None:
                return False
                
            # 处理空字符串的情况
            if not start_time.strip() or not end_time.strip():
                return False
                
            # 处理"不限"的情况
            if "不限" in start_time or "不限" in end_time:
                return True
                
            # 处理包含"~"的情况
            if "~" in start_time:
                start_time = start_time.split("~")[0].strip()
            if "~" in end_time:
                end_time = end_time.split("~")[0].strip()
                
            # 尝试解析时间
            current_time = datetime.now()
            start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end_datetime = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            return start_datetime <= current_time <= end_datetime
        except Exception as e:
            logger.error(f"解析时间范围时发生错误: {e}")
            return False

    def __custom_sites(self) -> list:
        """获取自定义站点列表，结构需包含name和domain"""
        custom_sites = []
        custom_sites_config = self.get_config("CustomSites")
        if custom_sites_config and custom_sites_config.get("enabled"):
            custom_sites = custom_sites_config.get("sites", [])
        return custom_sites

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
            拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        # 动态判断MoviePilot版本，决定定时任务输入框组件类型
        version = getattr(settings, "VERSION_FLAG", "v1")
        cron_field_component = "VCronField" if version == "v2" else "VTextField"
        # 需要过滤没有勋章的站点名称列表
        filtered_sites = ['星空', '高清杜比', '聆音', '朱雀', '馒头', '家园', '朋友', '我堡', '彩虹岛', '天空', '听听歌']
        # 获取站点列表并过滤
        all_sites = [site for site in self.sites.get_indexers() if not site.get("public") and site.get("name") not in filtered_sites] + self.__custom_sites()
        # 构建站点选项
        site_options = [{"title": site.get("name"), "value": site.get("id")} for site in all_sites]
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mb-6',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {
                                    'class': 'pa-6'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff',
                                                    'class': 'mr-3',
                                                    'size': 'default'
                                                },
                                                'text': 'mdi-cog'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '基本设置'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6 pb-6'
                                },
                                'content': [
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'enabled',
                                                            'label': '启用插件',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'notify',
                                                            'label': '开启通知',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'use_proxy',
                                                            'label': '启用代理',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'onlyonce',
                                                            'label': '立即运行一次',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mb-6',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {
                                    'class': 'pa-6'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff',
                                                    'class': 'mr-3',
                                                    'size': 'default'
                                                },
                                                'text': 'mdi-web'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '站点设置'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6 pb-6'
                                },
                                'content': [
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'chips': True,
                                                            'multiple': True,
                                                            'model': 'chat_sites',
                                                            'label': '选择站点',
                                                            'items': site_options,
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 4
                                                },
                                                'content': [
                                                    {
                                                        'component': cron_field_component,
                                                        'props': {
                                                            'model': 'cron',
                                                            'label': '执行周期(Cron)',
                                                            'placeholder': '5位cron表达式，默认每天9点执行',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 4
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'retry_times',
                                                            'label': '重试次数',
                                                            'items': [
                                                                {'title': '1次', 'value': 1},
                                                                {'title': '2次', 'value': 2},
                                                                {'title': '3次', 'value': 3}
                                                            ],
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 4
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'retry_interval',
                                                            'label': '重试间隔(秒)',
                                                            'items': [
                                                                {'title': '5秒', 'value': 5},
                                                                {'title': '10秒', 'value': 10},
                                                                {'title': '15秒', 'value': 15}
                                                            ],
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mb-6',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {
                                    'class': 'pa-6'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff',
                                                    'class': 'mr-3',
                                                    'size': 'default'
                                                },
                                                'text': 'mdi-help-circle'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '使用说明'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6 pb-6'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1'
                                        },
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'class': 'mb-4'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'class': 'text-subtitle-1 font-weight-bold mb-2',
                                                        'text': '🎯 插件功能：'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '1. 自动监控站点的勋章购买情况'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '2. 支持多个站点同时监控'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '3. 可设置定时任务自动执行'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '4. 支持代理和重试机制'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'class': 'mb-4'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'class': 'text-subtitle-1 font-weight-bold mb-2',
                                                        'text': '⚙️ 配置说明：'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '1. 启用插件：开启插件功能'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '2. 开启通知：接收勋章购买提醒'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '3. 启用代理：使用代理访问站点'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '4. 选择站点：选择要监控的站点'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '5. 执行周期：设置定时任务的执行时间'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'class': 'mb-4'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'class': 'text-subtitle-1 font-weight-bold mb-2',
                                                        'text': '💡 使用提示：'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '1. 建议设置合理的执行周期，避免频繁请求'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '2. 如遇到访问问题，可尝试开启代理'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '3. 建议开启通知，及时获取勋章购买提醒'
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ],{
            "enabled": False,
            "onlyonce": False,
            "notify": False,
            "use_proxy": True,
            "chat_sites": [],
            "cron": "0 9 * * *",
            "retry_times": 1,
            "retry_interval": 5
        }

    def get_page(self) -> list:
        """
        获取勋章页面数据，严格还原截图样式：顶部统计、站点分组标签、可展开详情。
        """
        try:
            # 1. 汇总全局统计数据
            site_ids = self._chat_sites
            all_medals = []
            site_medal_map = {}
            site_name_map = {}
            for site_id in site_ids:
                medals = self.get_data(f'medals_{site_id}', 'zmmedal') or []
                unhas_medals = self.get_data(f'unhas_medals_{site_id}', 'zmmedal') or []
                has_medals = self.get_data(f'has_medals_{site_id}', 'zmmedal') or []
                # 合并去重
                site_medals = []
                processed = set()
                for medal_list in [medals, unhas_medals, has_medals]:
                    for medal in medal_list:
                        key = f"{medal.get('name')}|{medal.get('site')}"
                        if key not in processed:
                            processed.add(key)
                            site_medals.append(medal)
                            all_medals.append(medal)
                site_medal_map[site_id] = site_medals
                # 获取站点名
                site = self.siteoper.get(site_id)
                site_name_map[site_id] = site.name if site else f"站点{site_id}"

            # 全局统计
            site_count = len(site_ids)
            medal_total = len(all_medals)
            buy_count = sum(1 for m in all_medals if (m.get('purchase_status') or '').strip() in ['购买', '赠送'])
            owned_count = sum(1 for m in all_medals if (m.get('purchase_status') or '').strip() in ['已经购买', '已拥有'])
            not_buy_count = sum(1 for m in all_medals if (m.get('purchase_status') or '').strip() in ['已过可购买时间', '未到可购买时间', '需要更多工分', '需要更多魔力值', '需要更多蝌蚪', '库存不足', '仅授予'])
            unknown_count = sum(1 for m in all_medals if not (m.get('purchase_status') or '').strip())

            # 2. 顶部统计信息（用一个大VCard包裹，内部VRow平铺，风格与下方卡片对齐）
            top_stats = [
                {'icon': 'mdi-office-building', 'color': '#16b1ff', 'value': site_count, 'label': '站点数量'},
                {'icon': 'mdi-medal', 'color': '#16b1ff', 'value': medal_total, 'label': '勋章总数'},
                {'icon': 'mdi-cart-check', 'color': '#a259e6', 'value': buy_count, 'label': '可购买'},
                {'icon': 'mdi-badge-account', 'color': '#ff357a', 'value': owned_count, 'label': '已拥有'},
                {'icon': 'mdi-cancel', 'color': '#ffb300', 'value': not_buy_count, 'label': '不可购买'},
                {'icon': 'mdi-help-circle-outline', 'color': '#ff5c5c', 'value': unknown_count, 'label': '未知状态'},
            ]
            top_row = {
                'component': 'VCard',
                'props': {'variant': 'flat', 'color': 'surface', 'class': 'mb-4', 'style': 'border-radius: 14px; box-shadow: 0 1px 4px rgba(22,177,255,0.04); padding: 12px 12px 6px 12px;'},
                'content': [
                    {
                        'component': 'VRow',
                        'props': {},
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 2, 'class': 'text-center px-1'},
                                'content': [
                                    {'component': 'VIcon', 'props': {'size': '40', 'color': v['color'], 'class': 'mb-1'}, 'text': v['icon']},
                                    {'component': 'div', 'props': {'class': 'font-weight-bold', 'style': 'font-size: 2rem; color: #222;'}, 'text': str(v['value'])},
                                    {'component': 'div', 'props': {'class': 'text-body-2', 'style': 'color: #b0b0b0; font-size: 1rem; margin-top: 2px;'}, 'text': v['label']}
                                ]
                            } for v in top_stats
                        ]
                    }
                ]
            }

            # 3. 站点分组标签（优化标签icon、颜色、间距、卡片圆角阴影等）
            site_rows = []
            for site_id in site_ids:
                medals = site_medal_map[site_id]
                site_name = site_name_map[site_id]
                total = len(medals)
                owned = sum(1 for m in medals if (m.get('purchase_status') or '').strip() in ['已经购买', '已拥有'])
                buy = sum(1 for m in medals if (m.get('purchase_status') or '').strip() in ['购买', '赠送'])
                not_buy = sum(1 for m in medals if (m.get('purchase_status') or '').strip() in ['已过可购买时间', '未到可购买时间', '需要更多工分', '需要更多魔力值', '需要更多蝌蚪', '库存不足', '仅授予'])
                # 站点行（只显示站点名，底色更浅、加底边线、padding更紧凑）
                site_row = {
                    'component': 'VRow',
                    'props': {'class': 'align-center mb-1', 'style': 'background:#fafbfc; border-radius:10px; border-bottom:1px solid #ececec; padding:6px 14px 6px 14px;'},
                    'content': [
                        {'component': 'VCol', 'props': {'cols': 'auto', 'class': 'text-left d-flex align-center'}, 'content': [
                            {'component': 'VIcon', 'props': {'color': '#a259e6', 'size': '22', 'class': 'mr-2'}, 'text': 'mdi-crown'},
                            {'component': 'span', 'props': {'class': 'font-weight-bold', 'style': 'font-size:1.05rem; color:#222;'}, 'text': site_name}
                        ]},
                        *([
                            {'component': 'VCol', 'props': {'cols': 'auto', 'class': 'text-right d-flex align-center justify-end', 'style': 'flex:1;'}, 'content': [
                                {'component': 'span', 'props': {'style': 'font-size:0.95rem; color:#888; font-weight:normal;'}, 'text': 'By：smallMing120'}
                            ]}
                        ] if site_name == '织梦' else [])
                    ]
                }
                # 标签行（chip高度增大，圆角更大，颜色更淡，icon和文字更紧凑，间距收紧）
                chips_row = {
                    'component': 'VRow',
                    'props': {'class': 'justify-center mb-1'},
                    'content': [
                        {'component': 'VCol', 'props': {'cols': 'auto', 'class': 'd-flex justify-center align-center'}, 'content': [
                            {'component': 'VChip', 'props': {'color': '#e5e9fa', 'variant': 'flat', 'size': 'large', 'class': 'mr-14', 'style': 'font-size:0.92rem; font-weight:500; border-radius:18px; padding:6px 18px; min-height:36px;'}, 'content': [
                                {'component': 'VIcon', 'props': {'size': '20', 'color': '#a259e6', 'class': 'mr-1'}, 'text': 'mdi-medal'},
                                {'component': 'span', 'props': {}, 'text': f'勋章总数: {total}'}
                            ]},
                            {'component': 'VChip', 'props': {'color': '#e6f7ea', 'variant': 'flat', 'size': 'large', 'class': 'mr-14', 'style': 'font-size:0.92rem; font-weight:500; border-radius:18px; padding:6px 18px; min-height:36px;'}, 'content': [
                                {'component': 'VIcon', 'props': {'size': '20', 'color': '#43c04b', 'class': 'mr-1'}, 'text': 'mdi-badge-account'},
                                {'component': 'span', 'props': {}, 'text': f'已拥有: {owned}'}
                            ]},
                            {'component': 'VChip', 'props': {'color': '#e6f7ea', 'variant': 'flat', 'size': 'large', 'class': 'mr-14', 'style': 'font-size:0.92rem; font-weight:500; border-radius:18px; padding:6px 18px; min-height:36px;'}, 'content': [
                                {'component': 'VIcon', 'props': {'size': '20', 'color': '#43c04b', 'class': 'mr-1'}, 'text': 'mdi-cart-check'},
                                {'component': 'span', 'props': {}, 'text': f'可购买: {buy}'}
                            ]},
                            {'component': 'VChip', 'props': {'color': '#ffeaea', 'variant': 'flat', 'size': 'large', 'class': '', 'style': 'font-size:0.92rem; font-weight:500; border-radius:18px; padding:6px 18px; min-height:36px;'}, 'content': [
                                {'component': 'VIcon', 'props': {'size': '20', 'color': '#ff5c5c', 'class': 'mr-1'}, 'text': 'mdi-cancel'},
                                {'component': 'span', 'props': {}, 'text': f'不可购买: {not_buy}'}
                            ]}
                        ]}
                    ]
                }
                # 详情展开（添加标签分类排序）
                # 分类分组
                buyable_medals = [m for m in medals if (m.get('purchase_status') or '').strip() in ['购买', '赠送']]
                owned_medals = [m for m in medals if (m.get('purchase_status') or '').strip() in ['已经购买', '已拥有']]
                unavailable_medals = [m for m in medals if (m.get('purchase_status') or '').strip() in ['已过可购买时间', '未到可购买时间', '需要更多工分', '需要更多魔力值', '需要更多蝌蚪', '库存不足', '仅授予']]
                unknown_medals = [m for m in medals if not (m.get('purchase_status') or '').strip()]
                # 分类分组内容（用标题而非标签）
                detail_content = []
                if buyable_medals:
                    detail_content.append({'component': 'VCardTitle', 'props': {'class': 'mb-1', 'style': 'color:#43c04b; font-size:1rem; font-weight:600; text-align:left;'}, 'text': f'可购买（{len(buyable_medals)}）'})
                    detail_content.append({'component': 'VRow', 'content': self.__get_medal_elements(buyable_medals)})
                if owned_medals:
                    detail_content.append({'component': 'VCardTitle', 'props': {'class': 'mb-1', 'style': 'color:#43c04b; font-size:1rem; font-weight:600; text-align:left;'}, 'text': f'已拥有（{len(owned_medals)}）'})
                    detail_content.append({'component': 'VRow', 'content': self.__get_medal_elements(owned_medals)})
                if unavailable_medals:
                    def get_unavailable_priority(medal):
                        status = (medal.get('purchase_status') or '').strip()
                        if '已过可购买时间' in status:
                            return 1
                        elif '未到可购买时间' in status:
                            return 2
                        elif '需要更多' in status:
                            return 3
                        elif '库存不足' in status:
                            return 4
                        elif '仅授予' in status:
                            return 5
                        else:
                            return 99
                    unavailable_medals = sorted(unavailable_medals, key=get_unavailable_priority)
                    detail_content.append({'component': 'VCardTitle', 'props': {'class': 'mb-1', 'style': 'color:#ff5c5c; font-size:1rem; font-weight:600; text-align:left;'}, 'text': f'不可购买（{len(unavailable_medals)}）'})
                    detail_content.append({'component': 'VRow', 'content': self.__get_medal_elements(unavailable_medals)})
                if unknown_medals:
                    detail_content.append({'component': 'VCardTitle', 'props': {'class': 'mb-1', 'style': 'color:#b0b0b0; font-size:1rem; font-weight:600; text-align:left;'}, 'text': f'未知状态（{len(unknown_medals)}）'})
                    detail_content.append({'component': 'VRow', 'content': self.__get_medal_elements(unknown_medals)})
                detail_row = {
                    'component': 'VRow',
                    'content': [
                        {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                            {'component': 'VExpansionPanels', 'props': {'variant': 'accordion', 'class': 'elevation-0', 'style': 'background:transparent;'}, 'content': [
                                {
                                    'component': 'VExpansionPanel',
                                    'props': {'class': 'elevation-0', 'style': 'background:transparent;'},
                                    'content': [
                                        {'component': 'VExpansionPanelTitle', 'props': {'class': 'py-2', 'style': 'font-weight:500; font-size:1rem; color:#666;'}, 'content': [
                                            {'component': 'span', 'props': {'class': 'font-weight-bold'}, 'text': '勋章详情'}
                                        ]},
                                        {'component': 'VExpansionPanelText', 'props': {'class': 'py-2', 'style': 'background:#f7f8fa; border-radius:12px; padding:18px 12px 12px 12px;'}, 'content': detail_content}
                                    ]
                                }
                            ]}
                        ]}
                    ]
                }
                # 用VCard包裹
                site_rows.append({
                    'component': 'VCard',
                    'props': {'variant': 'flat', 'color': 'surface', 'class': 'mb-3', 'style': 'border-radius: 14px; box-shadow: 0 1px 4px rgba(22,177,255,0.04); padding: 12px 12px 6px 12px;'},
                    'content': [site_row, chips_row, detail_row]
                })
            # 统计卡片间距缩小，圆角更柔和
            top_row['props']['class'] = 'mb-4'
            for col in top_row['content']:
                col['props']['class'] = 'text-center px-1'
                for card in col['content']:
                    card['props']['style'] = 'border-radius: 14px; box-shadow: 0 1px 4px rgba(22,177,255,0.04); min-height: 100px;'
                    card['props']['class'] = 'pa-3 d-flex flex-column align-center justify-center'

            # 4. 页面结构
            return [top_row] + site_rows
        except Exception as e:
            logger.error(f"生成勋章页面时发生错误: {str(e)}")
            return [{
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12, 'md': 12},
                        'content': [
                            {'component': 'VAlert', 'props': {'type': 'error', 'variant': 'tonal', 'text': f'生成勋章页面时发生错误: {str(e)}'}}
                        ]
                    }
                ]
            }]

    def __get_medal_elements(self, medals: List[Dict]) -> List[Dict]:
        """生成贴合参考图样式的勋章卡片元素（优化描述和状态chip溢出问题）"""
        elements = []
        for medal in medals:
            status = (medal.get('purchase_status') or '').strip()
            chip_color = '#b0b0b0'  # 默认灰色
            chip_text = status or '未知'

            # 智能判断烧包乐园的购买状态
            site = medal.get('site', '')
            if site == '烧包乐园' and (not status or status == '未知'):
                stock = str(medal.get('stock', '')).strip()
                begin = medal.get('saleBeginTime', '').strip()
                end = medal.get('saleEndTime', '').strip()
                now = datetime.now()
                try:
                    if begin and end:
                        begin_dt = datetime.strptime(begin, "%Y-%m-%d %H:%M:%S")
                        end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                        if now > end_dt:
                            chip_text = '已过可购买时间'
                            chip_color = '#ffb300'
                        elif stock == '0' and begin_dt <= now <= end_dt:
                            chip_text = '库存不足'
                            chip_color = '#ffb300'
                except Exception as e:
                    pass  # 时间格式异常时忽略，保持原chip_text

            # 其余原有逻辑...
            if chip_text in ['购买', '赠送']:
                chip_color = '#43c04b'
            elif chip_text in ['已经购买', '已拥有']:
                chip_color = '#43c04b'
                chip_text = '已拥有'
            elif chip_text in ['已过可购买时间', '未到可购买时间', '需要更多工分', '需要更多魔力值', '需要更多蝌蚪', '仅授予', '库存不足']:
                chip_color = '#ffb300'
            else:
                chip_color = '#b0b0b0'
                chip_text = chip_text or '未知'

            price = medal.get('price', 0)
            price_str = f"价格：{price:,}" if price else ""

            # 属性区
            attrs = [
                {
                    'component': 'VCol',
                    'props': {'cols': 12, 'class': 'py-0'},
                    'content': [
                        {'component': 'div', 'props': {'class': 'text-caption', 'style': 'color:#666;'}, 'text': f"站点：{medal.get('site','')}"}
                    ]
                }
            ]
            site = medal.get('site','')
            if site == '织梦':
                attrs.append({
                    'component': 'VCol',
                    'props': {'cols': 12, 'class': 'py-0'},
                    'content': [
                        {'component': 'div', 'props': {'class': 'text-caption', 'style': 'color:#666;'}, 'text': f"开始时间：{medal.get('saleBeginTime','')}"}
                    ]
                })
                attrs.append({
                    'component': 'VCol',
                    'props': {'cols': 12, 'class': 'py-0'},
                    'content': [
                        {'component': 'div', 'props': {'class': 'text-caption', 'style': 'color:#666;'}, 'text': f"结束时间：{medal.get('saleEndTime','')}"}
                    ]
                })
            elif site == '烧包乐园':
                attrs.append({
                    'component': 'VCol',
                    'props': {'cols': 12, 'class': 'py-0'},
                    'content': [
                        {'component': 'div', 'props': {'class': 'text-caption', 'style': 'color:#666;'}, 'text': f"库存：{medal.get('stock','')}"}
                    ]
                })
                attrs.append({
                    'component': 'VCol',
                    'props': {'cols': 12, 'class': 'py-0'},
                    'content': [
                        {'component': 'div', 'props': {'class': 'text-caption', 'style': 'color:#666;'}, 'text': f"可购买时间：{medal.get('saleBeginTime','')} ~ {medal.get('saleEndTime','')}"}
                    ]
                })
            else:
                attrs.append({
                    'component': 'VCol',
                    'props': {'cols': 12, 'class': 'py-0'},
                    'content': [
                        {'component': 'div', 'props': {'class': 'text-caption', 'style': 'color:#666;'}, 'text': f"有效期：{medal.get('validity','')}"}
                    ]
                })
                attrs.append({
                    'component': 'VCol',
                    'props': {'cols': 12, 'class': 'py-0'},
                    'content': [
                        {'component': 'div', 'props': {'class': 'text-caption', 'style': 'color:#666;'}, 'text': f"魔力加成：{medal.get('bonus_rate','')}"}
                    ]
                })
            # 主标题栏
            title_content = [
                {
                    'component': 'div',
                    'props': {
                        'style': 'max-width:240px; box-sizing:border-box; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; word-break:break-all; overflow-wrap:break-word; white-space:normal; font-size:1.1rem; text-align:center; height:2.2em; line-height:1.1em; position:relative; margin:auto;'
                    },
                    'text': f"《{medal.get('name','')}》"
                }
            ]
            # 底部价格+状态
            {
                'component': 'VRow',
                'props': {'class': 'mt-0 align-center', 'style': 'width:100%'},
                'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12, 'class': 'py-0', 'style': 'display:flex; align-items:center;'},
                        'content': [
                            {'component': 'div', 'props': {'class': 'text-body-2 font-weight-bold', 'style': 'color:#43c04b; font-size:0.9rem;'}, 'text': price_str},
                            {'component': 'div', 'props': {'style': 'margin-left:auto;'}, 'content': [
                                {
                                    'component': 'VChip',
                                    'props': {
                                        'color': chip_color,
                                        'variant': 'flat',
                                        'size': 'small',
                                        'class': 'font-weight-bold',
                                        'style': 'color:#fff; border-radius:12px; padding:2px 10px; white-space:nowrap; font-size:0.75rem; display:inline-block; line-height:1.9; min-width:unset; max-width:unset; width:auto;'
                                    },
                                    'text': chip_text
                                }
                            ]}
                        ]
                    }
                ]
            }
            card = {
                'component': 'VCol',
                'props': {'cols': 12, 'sm': 6, 'md': 4, 'lg': 3, 'class': 'mb-3 d-flex justify-center'},
                'content': [
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'pa-4 d-flex flex-column align-center',
                            'style': 'border-radius: 16px; box-shadow: 0 2px 8px rgba(22,177,255,0.08); min-width:220px; max-width:270px; min-height:340px; display:flex; flex-direction:column; justify-content:center; align-items:center;'
                        },
                        'content': [
                            # 顶部名称
                            {
                                'component': 'VCardTitle',
                                'props': {'class': 'text-center font-weight-bold', 'style': 'margin-top:0; padding-top:0px; margin-bottom:2px;'},
                                'content': title_content
                            },
                            # 描述（多行省略）
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'color:#888; margin:0 0 4px 0; padding:0; width:100%; max-width:100%; box-sizing:border-box; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; word-break:break-all; font-size:0.7rem; text-align:center;'
                                },
                                'text': medal.get('description','')
                            },
                            # 图片
                            {
                                'component': 'VImg',
                                'props': {
                                    'src': medal.get('imageSmall',''),
                                    'alt': medal.get('name',''),
                                    'width': '90',
                                    'height': '90',
                                    'class': 'my-2 mx-auto',
                                    'style': 'border-radius:50%; background:#f7f8fa; box-shadow:0 1px 4px rgba(22,177,255,0.04);'
                                }
                            },
                            # 属性区
                            {
                                'component': 'VRow',
                                'props': {'class': 'mt-2 mb-1', 'style': 'width:100%'},
                                'content': attrs
                            },
                            # 底部价格+状态
                            {
                                'component': 'VRow',
                                'props': {'class': 'mt-0 align-center', 'style': 'width:100%'},
                                'content': [
                                    {
                                        'component': 'VCol',
                                        'props': {'cols': 12, 'class': 'py-0', 'style': 'display:flex; align-items:center;'},
                                        'content': [
                                            {'component': 'div', 'props': {'class': 'text-body-2 font-weight-bold', 'style': 'color:#43c04b; font-size:0.9rem;'}, 'text': price_str},
                                            {'component': 'div', 'props': {'style': 'margin-left:auto;'}, 'content': [
                                                {
                                                    'component': 'VChip',
                                                    'props': {
                                                        'color': chip_color,
                                                        'variant': 'flat',
                                                        'size': 'small',
                                                        'class': 'font-weight-bold',
                                                        'style': 'color:#fff; border-radius:12px; padding:2px 10px; white-space:nowrap; font-size:0.75rem; display:inline-block; line-height:1.9; min-width:unset; max-width:unset; width:auto;'
                                                    },
                                                    'text': chip_text
                                                }
                                            ]}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            elements.append(card)
        return elements

    def get_state(self) ->bool:
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取命令"""
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """获取API"""
        pass

    @eventmanager.register(EventType.SiteDeleted)
    def site_deleted(self, event):
        """
        删除对应站点选中
        """
        site_id = event.event_data.get("site_id")
        config = self.get_config()
        if config:
            self._chat_sites = self.__remove_site_id(config.get("chat_sites") or [], site_id)
            # 保存配置
            self.update_config({
                "chat_sites": self._chat_sites,
            })

    def __remove_site_id(self, do_sites, site_id):
        if do_sites:
            if isinstance(do_sites, str):
                do_sites = [do_sites]
            # 删除对应站点
            if site_id:
                do_sites = [site for site in do_sites if int(site) != int(site_id)]
            else:
                # 清空
                do_sites = []
            # 若无站点，则停止
            if len(do_sites) == 0:
                self._enabled = False
        return do_sites

    def stop_service(self) -> None:
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("退出插件失败：%s" % str(e))

    def __format_time(self, time_str: str) -> str:
        """
        格式化时间字符串，只保留日期部分
        """
        if not time_str or time_str == '不限':
            return time_str
        try:
            # 尝试不同的时间格式
            formats = [
                "%Y-%m-%d %H:%M:%S",  # 标准格式
                "%Y-%m-%d",           # 只有日期
                "%Y/%m/%d %H:%M:%S",  # 斜杠分隔
                "%Y/%m/%d"            # 斜杠分隔只有日期
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
                    
            # 如果所有格式都不匹配，尝试直接提取日期部分
            if " " in time_str:
                return time_str.split(" ")[0]
                
            return time_str
        except Exception as e:
            logger.error(f"格式化时间出错: {str(e)}, 时间字符串: {time_str}")
            return time_str
