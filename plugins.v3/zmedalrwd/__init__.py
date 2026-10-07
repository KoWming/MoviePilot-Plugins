"""织梦勋章套装奖励：MoviePilot V3 专用实现"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from apscheduler.triggers.cron import CronTrigger

from app.db.oper.site import SiteOper
from app.schemas.types import MessageType
from app.sdk import scheduler as scheduler_sdk
from app.sdk.config import settings
from app.sdk.logging import logger
from app.sdk.network import RequestUtils
from app.sdk.plugin import _PluginBase

# 织梦站点与勋章套装奖励接口
SITE_DOMAIN = "zmpt.cc"
SITE_URL = "https://zmpt.cc/"
REWARD_URL = f"{SITE_URL}javaapi/user/drawMedalGroupReward"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"
)

# 勋章系列：配置开关名 -> (显示名称, 站点勋章组ID)
MEDAL_GROUPS: Dict[str, Tuple[str, int]] = {
    "anni": ("周年庆系列", 1),
    "terms": ("二十四节气系列", 2),
    "plum": ("梅兰竹菊系列", 3),
}

# 一次性任务 ID
ONCE_JOB_IDS = ("month_once", "week_once")


@dataclass(frozen=True)
class MedalResult:
    """单个勋章系列的领取结果。"""

    name: str
    icon: str
    detail: str
    power: float = 0.0

    @property
    def line(self) -> str:
        """通知与日志中的单行描述。"""
        return f"{self.name}勋章: {self.icon} {self.detail}"


class ZmedalRwd(_PluginBase):
    # 插件名称
    plugin_name = "织梦勋章套装奖励"
    # 插件描述
    plugin_desc = "领取勋章套装奖励。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/ZmedalRwd.png"
    # 插件版本
    plugin_version = "3.0.0"
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
    _auto_cookie: bool = False

    # 勋章系列开关
    _anni_enabled: bool = False
    _terms_enabled: bool = False
    _plum_enabled: bool = False

    # 勋章套装奖励参数
    _cookie: Optional[str] = None
    _cron_month: Optional[str] = None
    _cron_week: Optional[str] = None

    def init_plugin(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        生效配置信息。

        :param config: 插件配置字典
        """
        # 停止现有任务
        self.stop_service()

        config = config or {}
        # 手动配置的cookie,用于配置回写,避免站点cookie快照污染配置
        manual_cookie = config.get("cookie")
        self._enabled = bool(config.get("enabled", False))
        self._onlyonce = bool(config.get("onlyonce", False))
        self._notify = bool(config.get("notify", True))
        self._auto_cookie = bool(config.get("auto_cookie", False))
        self._cron_month = config.get("cron_month")
        self._cron_week = config.get("cron_week")
        self._anni_enabled = bool(config.get("anni_enabled", False))
        self._terms_enabled = bool(config.get("terms_enabled", False))
        self._plum_enabled = bool(config.get("plum_enabled", False))
        self._cookie = manual_cookie

        if not self._onlyonce:
            return

        # 关闭一次性开关后回写配置，避免重复触发
        self._onlyonce = False
        self.update_config(self._build_config(manual_cookie, onlyonce=False))

        # 分别注册每月和每周任务，由宿主调度器延迟执行
        self._schedule_once("month_once", self._medal_bonus_month_task, 3, "每月任务")
        self._schedule_once("week_once", self._medal_bonus_week_task, 6, "每周任务")

    def medal_bonus(self, medal_types: Tuple[str, ...]) -> List[MedalResult]:
        """
        领取勋章套装奖励。

        :param medal_types: 勋章系列标识，取值见 MEDAL_GROUPS
        :return: 各勋章系列的领取结果
        """
        targets = [mtype for mtype in medal_types if self._group_enabled(mtype)]
        if not targets:
            return []

        # 站点配置每次执行实时读取,避免站点cookie轮换/过期后持续使用旧快照
        site = self._load_site()
        headers = {
            "referer": SITE_URL,
            "user-agent": USER_AGENT,
        }
        cookie = self._resolve_cookie(site)
        if cookie:
            headers["cookie"] = cookie
        proxies = self._resolve_proxies(site)
        return [
            self._draw_medal_group(*MEDAL_GROUPS[mtype], headers=headers, proxies=proxies)
            for mtype in targets
        ]

    def _draw_medal_group(self, name: str, group_id: int, headers: Dict[str, Any],
                          proxies: Optional[Dict[str, str]]) -> MedalResult:
        """
        领取单个勋章系列的套装奖励。

        :param name: 勋章系列显示名称
        :param group_id: 站点勋章组ID
        :param headers: 请求头
        :param proxies: 代理设置
        :return: 该勋章系列的领取结果
        """
        try:
            response = RequestUtils(headers=headers, proxies=proxies, verify=True).get_res(
                REWARD_URL, params={"medalGroupId": group_id}
            )
            response_data = response.json() if response is not None else None
        except Exception as e:
            logger.error(f"领取{name}勋章奖励时发生异常: {str(e)}")
            return MedalResult(name, "❌", "领取异常")

        if not isinstance(response_data, dict):
            return MedalResult(name, "❌", "领取异常")

        if not response_data.get("success", False):
            error_msg = str(response_data.get("errorMsg") or "未知错误")
            if response_data.get("errorCode") == 2004 or "已领取" in error_msg:
                return MedalResult(name, "ℹ️", "已领取")
            if "未收集完成" in error_msg:
                return MedalResult(name, "⚠️", "未收集完成")
            return MedalResult(name, "❌", error_msg)

        result = response_data.get("result")
        if not isinstance(result, dict):
            return MedalResult(name, "❌", "领取失败")

        reward = result.get("rewardAmount")
        seed_bonus = result.get("seedBonus")
        if reward is None or seed_bonus is None:
            return MedalResult(name, "❌", "领取失败")

        return MedalResult(
            name, "✅", f"获得{reward}电力, 总电力:{seed_bonus}", power=self._to_float(reward)
        )

    def _medal_bonus_month_task(self) -> None:
        """
        执行每月勋章套装奖励任务(周年庆系列和二十四节气系列)
        """
        self._run_bonus_task("每月任务", ("anni", "terms"), "【织梦勋章套装奖励】每月任务完成")

    def _medal_bonus_week_task(self) -> None:
        """
        执行每周勋章套装奖励任务(梅兰竹菊系列)
        """
        self._run_bonus_task("每周任务", ("plum",), "【织梦勋章套装奖励】每周任务完成")

    def _run_bonus_task(self, label: str, medal_types: Tuple[str, ...], title: str) -> None:
        """
        执行一次领取并按需发送通知。

        :param label: 日志中的任务名称
        :param medal_types: 需要领取的勋章系列
        :param title: 通知标题
        """
        try:
            names = "、".join(MEDAL_GROUPS[mtype][0] for mtype in medal_types)
            logger.info(f"执行{label}: {names}")

            results = self.medal_bonus(medal_types)
            if not results:
                logger.info("没有可领取的勋章套装奖励")
                return

            report = self.generate_report(results)
            if self._notify:
                self.post_message(
                    mtype=MessageType.SiteMessage,
                    title=title,
                    text=report,
                )
            logger.info(f"{label}勋章套装奖励领取完成：\n{report}")
        except Exception as e:
            logger.error(f"执行{label}勋章套装奖励任务时发生异常: {str(e)}")
            logger.error("异常详情: ", exc_info=True)

    def generate_report(self, results: List[MedalResult]) -> str:
        """
        生成勋章套装奖励领取报告。

        :param results: 奖励领取结果列表
        :return: 格式化的报告文本
        """
        if not results:
            return "没有可领取的勋章套装奖励"

        total_power = sum(result.power for result in results)

        stats = []
        for icon, label in (("✅", "成功"), ("ℹ️", "已领取"), ("⚠️", "未集齐"), ("❌", "失败")):
            count = sum(1 for result in results if result.icon == icon)
            if count > 0:
                stats.append(f"{label}:{count}")

        report = "━━━━━━━━━━━━━━\n"
        report += "🎖️ 勋章套装领取报告\n"
        # 只在有成功领取时显示电力
        if total_power > 0:
            report += f"⚡ 获得电力：{total_power:g}\n"
        # 只显示非零的统计
        if stats:
            report += "📊 " + " | ".join(stats) + "\n"
        report += "\n".join(result.line for result in results)
        report += f"\n⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return report

    def get_state(self) -> bool:
        """
        获取插件状态
        """
        return bool(self._enabled)

    @staticmethod
    def get_command() -> Optional[List[Dict[str, Any]]]:
        """
        获取命令
        """
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取API
        """
        pass

    def get_page(self) -> Optional[List[Dict[str, Any]]]:
        """
        数据页面
        """
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务；停用状态由宿主统一过滤。
        """
        service = []
        schedules = (
            ("Month", "每月执行", self._cron_month, self._medal_bonus_month_task),
            ("Week", "每周执行", self._cron_week, self._medal_bonus_week_task),
        )
        for suffix, label, cron, func in schedules:
            if not cron:
                continue
            try:
                trigger = CronTrigger.from_crontab(cron)
            except (TypeError, ValueError) as e:
                logger.error(f"织梦勋章套装奖励{label}周期配置无效，已跳过：{str(e)}")
                continue
            service.append({
                "id": f"{self.__class__.__name__}{suffix}",
                "name": f"织梦勋章套装奖励 - {label}",
                "trigger": trigger,
                "func": func,
                "kwargs": {}
            })
        return service

    def stop_service(self) -> None:
        """
        退出插件：取消尚未执行的一次性任务。
        """
        for job_id in ONCE_JOB_IDS:
            try:
                scheduler_sdk.remove_plugin_once_job(self.__class__.__name__, job_id)
            except Exception as e:
                logger.error(f"取消一次性任务 {job_id} 失败：{str(e)}")

    def _schedule_once(self, job_id: str, func: Callable[[], None], delay_seconds: int,
                       label: str) -> None:
        """
        向宿主调度器追加一次性任务。

        :param job_id: 插件内唯一的任务ID
        :param func: 要执行的任务方法
        :param delay_seconds: 延迟秒数
        :param label: 任务名称中的描述
        """
        try:
            scheduled = scheduler_sdk.add_plugin_once_job(
                self.__class__.__name__,
                job_id,
                func,
                f"织梦勋章套装奖励-{label}",
                delay_seconds=delay_seconds,
            )
        except Exception as e:
            logger.error(f"注册{label}一次性任务失败: {str(e)}")
            return
        if not scheduled:
            logger.warning(f"{label}一次性任务未注册，调度器可能未运行")

    def _build_config(self, manual_cookie: Optional[str], *, onlyonce: bool) -> Dict[str, Any]:
        """
        生成需要回写的插件配置。

        :param manual_cookie: 手动配置的cookie
        :param onlyonce: 回写的一次性运行开关状态
        :return: 配置字典
        """
        return {
            "enabled": self._enabled,
            "onlyonce": onlyonce,
            "notify": self._notify,
            "auto_cookie": self._auto_cookie,
            "cookie": manual_cookie,
            "cron_month": self._cron_month,
            "cron_week": self._cron_week,
            "anni_enabled": self._anni_enabled,
            "terms_enabled": self._terms_enabled,
            "plum_enabled": self._plum_enabled,
        }

    def _group_enabled(self, mtype: str) -> bool:
        """
        判断某个勋章系列是否启用领取。

        :param mtype: 勋章系列标识
        :return: 是否启用
        """
        return {
            "anni": self._anni_enabled,
            "terms": self._terms_enabled,
            "plum": self._plum_enabled,
        }.get(mtype, False)

    @staticmethod
    def _load_site() -> Optional[Any]:
        """
        读取织梦站点配置；每次调用创建临时 Oper，不跨任务持有。

        :return: 站点记录，读取失败时为 None
        """
        try:
            return SiteOper().get_by_domain(SITE_DOMAIN)
        except Exception as e:
            logger.error(f"获取站点配置出错: {str(e)}")
            return None

    def _resolve_cookie(self, site: Optional[Any]) -> str:
        """
        获取本次领取使用的cookie。

        :param site: 织梦站点配置，未配置时为 None
        :return: 有效cookie，不可用时返回空串
        """
        if not self._auto_cookie:
            return str(self._cookie or "")
        if not site:
            logger.warning(f"未找到站点: {SITE_DOMAIN}")
            return ""
        cookie = site.cookie
        if not cookie or str(cookie).strip().lower() == "cookie":
            logger.warning(f"站点 {SITE_DOMAIN} 的cookie无效")
            return ""
        return str(cookie)

    @staticmethod
    def _resolve_proxies(site: Optional[Any]) -> Optional[Dict[str, str]]:
        """
        获取代理设置(跟随站点配置)。

        :param site: 织梦站点配置，未配置时为 None
        :return: 代理配置，不使用代理时为 None
        """
        if site and site.proxy and settings.PROXY:
            logger.info("站点已启用代理，跟随系统代理")
            return settings.PROXY
        return None

    @staticmethod
    def _to_float(value: Any) -> float:
        """
        把站点返回的电力数值转换为浮点数。

        :param value: 站点返回的原始数值
        :return: 转换结果，无法解析时为 0
        """
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
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
                                                        'component': 'VCronField',
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
                                                        'component': 'VCronField',
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
            "anni_enabled": False,
            "terms_enabled": False,
            "plum_enabled": False,
            "cookie": "",
            "auto_cookie": False,
            "cron_month": "0 0 1 * *",
            "cron_week": "0 0 * * 1",
        }
