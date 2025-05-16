import pytz
import requests

from datetime import datetime, timedelta
from typing import Any, List, Dict, Tuple, Optional

from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler

from app.log import logger
from app.core.config import settings
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.db.site_oper import SiteOper

class ZmedalRwd(_PluginBase):
    # 插件名称
    plugin_name = "织梦勋章套装奖励"
    # 插件描述
    plugin_desc = "领取勋章套装奖励。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/ZmedalRwd.png"
    # 插件版本
    plugin_version = "1.2"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "zmedalrwd_"
    # 加载顺序
    plugin_order = 25
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enabled: bool = False
    _onlyonce: bool = False
    _notify: bool = True
    _use_proxy: bool = True
    _auto_cookie: bool = False

    # 勋章系列开关
    _anni_enabled: bool = False
    _terms_enabled: bool = False
    _plum_enabled: bool = False

    # 勋章套装奖励参数
    _cookie: Optional[str] = None
    _cron_month: Optional[str] = None
    _cron_week: Optional[str] = None
    _site_url: str = "https://zmpt.cc/"
    
    # 定时器
    _scheduler: Optional[BackgroundScheduler] = None

    # 站点操作实例
    _siteoper = None

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """
        初始化插件
        """
        # 停止现有任务
        self.stop_service()

        # 创建站点操作实例
        self._siteoper = SiteOper()

        if config:
            self._enabled = config.get("enabled", False)
            self._cron_month = config.get("cron_month")
            self._cron_week = config.get("cron_week")
            self._cookie = config.get("cookie")
            self._notify = config.get("notify", True)
            self._onlyonce = config.get("onlyonce", False)
            self._use_proxy = config.get("use_proxy", True)
            self._anni_enabled = config.get("anni_enabled", False)
            self._terms_enabled = config.get("terms_enabled", False)
            self._plum_enabled = config.get("plum_enabled", False)
            self._auto_cookie = config.get("auto_cookie", False)

            # 处理自动获取cookie
            if self._auto_cookie:
                self._cookie = self.get_site_cookie()
            else:
                self._cookie = config.get("cookie")

        if self._onlyonce:
            try:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                logger.info(f"织梦勋章套装奖励服务启动，立即运行一次")
                
                # 分别执行每月和每周任务
                self._scheduler.add_job(func=self._medal_bonus_month_task, trigger='date',
                                     run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                     name="织梦勋章套装奖励-每月任务")
                                     
                self._scheduler.add_job(func=self._medal_bonus_week_task, trigger='date',
                                     run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=6),
                                     name="织梦勋章套装奖励-每周任务")
                
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "onlyonce": False,
                    "cron_month": self._cron_month,
                    "cron_week": self._cron_week,
                    "enabled": self._enabled,
                    "cookie": self._cookie,
                    "notify": self._notify,
                    "use_proxy": self._use_proxy,
                    "anni_enabled": self._anni_enabled,
                    "terms_enabled": self._terms_enabled,
                    "plum_enabled": self._plum_enabled,
                    "auto_cookie": self._auto_cookie
                })

                # 启动任务
                if self._scheduler.get_jobs():
                   self._scheduler.print_jobs()
                   self._scheduler.start()
            except Exception as e:
                logger.error(f"织梦勋章套装奖励服务启动失败: {str(e)}")

    def medal_bonus(self, medal_type: str = "all"):
        """
        领取勋章套装奖励
        :param medal_type: 勋章类型,可选值: all(全部), anni(周年庆), terms(二十四节气), plum(梅兰竹菊)
        """
        # 勋章系列名称映射
        medal_names = {
            "anni": "周年庆系列",
            "terms": "二十四节气系列",
            "plum": "梅兰竹菊系列"
        }
        
        # 勋章系列URL映射
        medal_urls = {
            "anni": self._site_url + "/javaapi/user/drawMedalGroupReward?medalGroupId=1",
            "terms": self._site_url + "/javaapi/user/drawMedalGroupReward?medalGroupId=2",
            "plum": self._site_url + "/javaapi/user/drawMedalGroupReward?medalGroupId=3"
        }
        
        self.headers = {
            "cookie": self._cookie,
            "referer": self._site_url,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"
        }

        results = []
        
        # 获取代理设置
        proxies = self._get_proxies()
        # 根据类型执行对应的奖励领取
        for mtype in ["anni", "terms", "plum"]:
            if medal_type in ["all", mtype]:
                # 检查对应的开关是否启用
                if mtype == "anni" and not self._anni_enabled:
                    continue
                if mtype == "terms" and not self._terms_enabled:
                    continue
                if mtype == "plum" and not self._plum_enabled:
                    continue
                    
                try:
                    response = requests.get(medal_urls[mtype], headers=self.headers, proxies=proxies)
                    response_data = response.json()
                    
                    if not response_data.get("success", False):
                        error_msg = response_data.get("errorMsg", "未知错误")
                        if "未收集完成" in error_msg:
                            results.append(f"{medal_names[mtype]}勋章: ⚠️ 未收集完成")
                        else:
                            results.append(f"{medal_names[mtype]}勋章: ❌ {error_msg}")
                        continue
                        
                    result = response_data.get("result", None)
                    if result is None:
                        results.append(f"{medal_names[mtype]}勋章: ❌ 领取失败")
                    else:
                        reward = result['rewardAmount']
                        seed_bonus = result['seedBonus']
                        results.append(f"{medal_names[mtype]}勋章: ✅ 获得{reward}电力, 总电力:{seed_bonus}")
                except Exception as e:
                    logger.error(f"领取{medal_names[mtype]}勋章奖励时发生异常: {str(e)}")
                    results.append(f"{medal_names[mtype]}勋章: ❌ 领取异常")

        return results

    def _medal_bonus_month_task(self):
        """
        执行每月勋章套装奖励任务(周年庆系列和二十四节气系列)
        """
        try:
            logger.info("执行每月任务: 周年庆系列和二十四节气系列")
            results = self.medal_bonus(medal_type="anni")  # 周年庆系列
            results.extend(self.medal_bonus(medal_type="terms"))  # 二十四节气系列
            
            # 生成报告
            if results:
                report = self.generate_report(results)
                
                # 发送通知
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【织梦勋章套装奖励】每月任务完成",
                        text=report)
                
                logger.info(f"每月勋章套装奖励领取完成：\n{report}")
            else:
                logger.info("没有可领取的勋章套装奖励")

        except Exception as e:
            logger.error(f"执行每月勋章套装奖励任务时发生异常: {str(e)}")
            logger.error("异常详情: ", exc_info=True)

    def _medal_bonus_week_task(self):
        """
        执行每周勋章套装奖励任务(梅兰竹菊系列)
        """
        try:
            logger.info("执行每周任务: 梅兰竹菊系列")
            results = self.medal_bonus(medal_type="plum")  # 梅兰竹菊系列
            
            # 生成报告
            if results:
                report = self.generate_report(results)
                
                # 发送通知
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【织梦勋章套装奖励】每周任务完成",
                        text=report)
                
                logger.info(f"每周勋章套装奖励领取完成：\n{report}")
            else:
                logger.info("没有可领取的勋章套装奖励")

        except Exception as e:
            logger.error(f"执行每周勋章套装奖励任务时发生异常: {str(e)}")
            logger.error("异常详情: ", exc_info=True)

    def generate_report(self, results: List[str]) -> str:
        """
        生成勋章套装奖励领取报告
        :param results: 奖励领取结果列表
        :return: 格式化的报告文本
        """
        try:
            if not results:
                return "没有可领取的勋章套装奖励"

            # 统计总电力
            total_power = 0
            success_count = 0
            incomplete_count = 0
            failed_count = 0
            
            for result in results:
                if "✅" in result:
                    success_count += 1
                    try:
                        power = int(result.split("总电力:")[1].strip())
                        total_power += power
                    except:
                        continue
                elif "⚠️" in result:
                    incomplete_count += 1
                elif "❌" in result:
                    failed_count += 1

            # 生成简化的报告
            report = "━━━━━━━━━━━━━━\n"
            report += "🎖️ 勋章套装领取报告\n"
            
            # 只在有成功领取时显示电力
            if total_power > 0:
                report += f"⚡ 获得电力：{total_power}\n"
            
            # 只显示非零的统计
            stats = []
            if success_count > 0:
                stats.append(f"成功:{success_count}")
            if incomplete_count > 0:
                stats.append(f"未集齐:{incomplete_count}")
            if failed_count > 0:
                stats.append(f"失败:{failed_count}")
            
            if stats:
                report += "📊 " + " | ".join(stats) + "\n"
            
            # 详细结果
            if results:
                report += "\n".join(results)
            
            # 添加时间戳
            report += f"\n⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            return report

        except Exception as e:
            logger.error(f"生成报告时发生异常: {str(e)}")
            return "生成报告时发生错误，请检查日志以获取更多信息。"
        
    def _get_proxies(self):
        """
        获取代理设置
        """
        if not self._use_proxy:
            logger.info("未启用代理")
            return None
            
        try:
            # 获取系统代理设置
            if hasattr(settings, 'PROXY') and settings.PROXY:
                logger.info(f"使用系统代理: {settings.PROXY}")
                return settings.PROXY
            else:
                logger.warning("系统代理未配置")
                return None
        except Exception as e:
            logger.error(f"获取代理设置出错: {str(e)}")
            return None
        
    def get_site_cookie(self, domain: str = 'zmpt.cc') -> str:
        """
        获取站点cookie
        
        Args:
            domain: 站点域名,默认为织梦站点
            
        Returns:
            str: 有效的cookie字符串,如果获取失败则返回空字符串
        """
        try:
            # 优先使用手动配置的cookie
            if self._cookie:
                if str(self._cookie).strip().lower() == "cookie":
                    logger.warning("手动配置的cookie无效")
                    return ""
                return self._cookie
                
            # 如果手动配置的cookie无效,则从站点配置获取
            site = self._siteoper.get_by_domain(domain)
            if not site:
                logger.warning(f"未找到站点: {domain}")
                return ""
                
            cookie = site.cookie
            if not cookie or str(cookie).strip().lower() == "cookie":
                logger.warning(f"站点 {domain} 的cookie无效")
                return ""
                
            # 将获取到的cookie保存到实例变量
            self._cookie = cookie
            return cookie
            
        except Exception as e:
            logger.error(f"获取站点cookie失败: {str(e)}")
            return ""

    def get_state(self) -> bool:
        """获取插件状态"""
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取命令"""
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """获取API"""
        pass

    def get_page(self) -> List[dict]:
        """数据页面"""
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        """
        service = []
        if self._cron_month:
            service.append({
                "id": "ZmedalRwdMonth",
                "name": "织梦勋章套装奖励 - 每月执行",
                "trigger": CronTrigger.from_crontab(self._cron_month),
                "func": self._medal_bonus_month_task
            })
        if self._cron_week:
            service.append({
                "id": "ZmedalRwdWeek",
                "name": "织梦勋章套装奖励 - 每周执行",
                "trigger": CronTrigger.from_crontab(self._cron_week),
                "func": self._medal_bonus_week_task
            })

        if service:
            return service

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        # 动态判断MoviePilot版本，决定定时任务输入框组件类型
        version = getattr(settings, "VERSION_FLAG", "v1")
        cron_field_component = "VCronField" if version == "v2" else "VTextField"
        return [
            {
                'component': 'VForm',
                'content': [
                    # 基本设置
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
                                                            'model': 'use_proxy',
                                                            'label': '使用代理',
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
                    # 功能设置
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
                                                'text': 'mdi-tools'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '功能设置'
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
                                                            'model': 'auto_cookie',
                                                            'label': '使用站点Cookie',
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
                                                            'model': 'anni_enabled',
                                                            'label': '周年庆系列',
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
                                                            'model': 'terms_enabled',
                                                            'label': '二十四节气系列',
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
                                                            'model': 'plum_enabled',
                                                            'label': '梅兰竹菊系列',
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
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'cookie',
                                                            'label': '站点Cookie',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'class': 'mt-2',
                                                            'disabled': 'auto_cookie'
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
                                                        'component': cron_field_component,  # 动态切换
                                                        'props': {
                                                            'model': 'cron_month',
                                                            'label': '每月执行周期(cron)',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'placeholder': '默认每月1号执行',
                                                            'class': 'mt-2'
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
                                                        'component': cron_field_component,  # 动态切换
                                                        'props': {
                                                            'model': 'cron_week',
                                                            'label': '每周执行周期(cron)',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'placeholder': '默认每周一执行',
                                                            'class': 'mt-2'
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
                    # 使用说明
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
                                                'text': 'mdi-treasure-chest'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '领取说明'
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
                                                        'text': '⚙️ 启用【使用站点Cookie】功能后，插件会自动获取已配置站点的cookie，请确保cookie有效。'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'mb-4'}
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'text-subtitle-1 font-weight-bold mb-2',
                                                        'text': '🎉 周年庆系列领取规则：'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '📅 时间范围：2024-11-12 ~ 2030-12-31'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '⏰ 领取频率：每个自然月可领取一次'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '⚡ 奖励内容：每次 1000 电力'
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
                                                        'text': '🌿 二十四节气系列领取规则(站点暂未开放领取)：'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '📅 时间范围：2024-11-12 ~ 2030-12-31'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '⏰ 领取频率：每个自然月可领取一次'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '⚡ 奖励内容：每次 1000 电力'
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
                                                        'text': '🎋 梅兰竹菊系列领取规则：'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '📅 时间范围：2024-12-06 ~ 2030-12-31'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '⏰ 领取频率：每个自然周可领取一次'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'class': 'ml-4',
                                                        'text': '⚡ 奖励内容：每次 15000 电力'
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
        ], {
            "enabled": False,
            "onlyonce": False,
            "notify": True,
            "use_proxy": False,
            "anni_enabled": False,
            "terms_enabled": False,
            "plum_enabled": False,
            "cookie": "",
            "auto_cookie": False,
            "cron_month": "0 0 1 * *",
            "cron_week": "0 0 * * 1",
        }

    def stop_service(self) -> None:
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("退出插件失败：%s" % str(e))
