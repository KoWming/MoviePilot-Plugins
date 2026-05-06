from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import pytz
import random
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.scheduler import Scheduler
from app.schemas import NotificationType


class JuyingSignin(_PluginBase):
    # 插件名称
    plugin_name = "聚影签到"
    # 插件描述
    plugin_desc = "聚影站点自动登录并执行每日签到。"
    # 插件图标
    plugin_icon = "https://s3.bmp.ovh/2026/05/05/TEY2AZ6K.png"
    # 插件版本
    plugin_version = "1.1.0"
    # 插件作者
    plugin_author = "sunxing"
    # 作者主页
    author_url = "https://github.com"
    # 插件配置项ID前缀
    plugin_config_prefix = "juyingsignin_"
    # 加载顺序
    plugin_order = 26
    # 可使用的用户级别
    auth_level = 1

    _enabled: bool = False
    _notify: bool = True
    _onlyonce: bool = False
    _cron: Optional[str] = None
    _username: str = ""
    _password: str = ""
    _use_proxy: bool = False
    _history_count: int = 30
    _random_time_range: str = ""
    _retry_count: int = 0
    _retry_interval: int = 5

    _base_url: str = "https://share.huamucang.top"
    _scheduler: Optional[BackgroundScheduler] = None

    def __init__(self):
        super().__init__()

    @staticmethod
    def _to_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() == "true"
        return bool(val)

    @staticmethod
    def _to_int(val: Any, default: int = 0) -> int:
        try:
            return int(val)
        except Exception:
            return default

    def init_plugin(self, config: Optional[dict] = None) -> None:
        try:
            self.stop_service()

            if self.plugin_icon and str(self.plugin_icon).startswith(("http://", "https://")):
                parsed_icon = urlparse(str(self.plugin_icon))
                icon_domain = f"{parsed_icon.scheme}://{parsed_icon.netloc}" if parsed_icon.scheme and parsed_icon.netloc else None
                if icon_domain and icon_domain not in settings.SECURITY_IMAGE_DOMAINS:
                    settings.SECURITY_IMAGE_DOMAINS.append(icon_domain)

            self._enabled = False
            self._notify = True
            self._onlyonce = False
            self._cron = "0 10 * * *"
            self._username = ""
            self._password = ""
            self._use_proxy = False
            self._history_count = 30
            self._random_time_range = ""
            self._retry_count = 0
            self._retry_interval = 5

            if config:
                self._enabled = self._to_bool(config.get("enabled", False))
                self._notify = self._to_bool(config.get("notify", True))
                self._onlyonce = self._to_bool(config.get("onlyonce", False))
                self._cron = config.get("cron") or "0 10 * * *"
                self._username = (config.get("username") or "").strip()
                self._password = config.get("usr_password") or ""
                self._use_proxy = self._to_bool(config.get("use_proxy", False))
                self._history_count = self._to_int(config.get("history_count", 30), 30)
                self._random_time_range = (config.get("random_time_range") or "").strip()
                self._retry_count = self._to_int(config.get("retry_count", 0), 0)
                self._retry_interval = self._to_int(config.get("retry_interval", 5), 5)

            if self._onlyonce:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                logger.info(f"{self.plugin_name}: 立即执行一次签到任务")
                self._scheduler.add_job(
                    func=self._signin,
                    trigger='date',
                    run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                    name="聚影签到"
                )
                self._onlyonce = False
                self.update_config(self._get_config())

                if self._scheduler.get_jobs():
                    self._scheduler.print_jobs()
                    self._scheduler.start()

            if not self._enabled:
                logger.info(f"{self.plugin_name}: 插件未启用")
                return

            if self._enabled and self._cron:
                logger.info(f"{self.plugin_name}: 已配置 CRON '{self._cron}'，任务将通过公共服务注册")
        except Exception as err:
            logger.error(f"{self.plugin_name}: 初始化失败 - {err}")
            self._enabled = False

    def get_state(self) -> bool:
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        services = []
        if self._enabled and self._cron:
            services.append({
                "id": "juyingsignin",
                "name": "聚影签到 - 定时任务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self._schedule_signin_with_random_delay,
                "kwargs": {},
            })
        return services

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        version = getattr(settings, "VERSION_FLAG", "v1")
        cron_field_component = "VCronField" if version == "v2" else "VTextField"
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VCard",
                        "props": {
                            "variant": "flat",
                            "class": "mb-6",
                            "color": "surface"
                        },
                        "content": [
                            {
                                "component": "VCardItem",
                                "props": {"class": "px-6 pb-0"},
                                "content": [
                                    {
                                        "component": "VCardTitle",
                                        "props": {"class": "d-flex align-center text-h6"},
                                        "content": [
                                            {
                                                "component": "VIcon",
                                                "props": {
                                                    "style": "color: #16b1ff;",
                                                    "class": "mr-3",
                                                    "size": "default"
                                                },
                                                "text": "mdi-calendar-check"
                                            },
                                            {
                                                "component": "span",
                                                "text": "基本设置"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "component": "VDivider",
                                "props": {"class": "mx-4 my-2"}
                            },
                            {
                                "component": "VCardText",
                                "props": {"class": "px-6 pb-6"},
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 3},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "enabled",
                                                            "label": "启用插件",
                                                            "color": "primary",
                                                            "hide-details": True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 3},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "use_proxy",
                                                            "label": "启用代理",
                                                            "color": "success",
                                                            "hide-details": True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 3},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "notify",
                                                            "label": "开启通知",
                                                            "color": "info",
                                                            "hide-details": True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 3},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "onlyonce",
                                                            "label": "立即执行一次",
                                                            "color": "warning",
                                                            "hide-details": True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "username",
                                                            "label": "用户名",
                                                            "placeholder": "聚影用户名",
                                                            "autocomplete": "off",
                                                            "name": "juying-signin-username",
                                                            "prepend-inner-icon": "mdi-account"
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "usr_password",
                                                            "label": "密码",
                                                            "type": "password",
                                                            "placeholder": "聚影密码",
                                                            "autocomplete": "new-password",
                                                            "name": "juying-signin-password",
                                                            "prepend-inner-icon": "mdi-lock-outline"
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 4},
                                                "content": [
                                                    {
                                                        "component": cron_field_component,
                                                        "props": {
                                                            "model": "cron",
                                                            "label": "Cron 表达式",
                                                            "placeholder": "0 10 * * *",
                                                            "prepend-inner-icon": "mdi-clock-outline",
                                                            "persistent-hint": True,
                                                            "hint": "默认每天 10:00 执行签到"
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "history_count",
                                                            "label": "历史保留条数",
                                                            "type": "number",
                                                            "min": 1,
                                                            "step": 1,
                                                            "active": True,
                                                            "persistent-hint": True,
                                                            "hint": "默认保留最近 30 条签到记录",
                                                            "placeholder": "默认保留30条",
                                                            "prepend-inner-icon": "mdi-counter"
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "random_time_range",
                                                            "label": "随机时间范围(分钟)",
                                                            "placeholder": "例如: 0-30",
                                                            "prepend-inner-icon": "mdi-timer-outline",
                                                            "persistent-hint": True,
                                                            "hint": "定时任务将在该范围内随机延迟执行，留空则不随机"
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "retry_count",
                                                            "label": "失败重试次数",
                                                            "type": "number",
                                                            "min": 0,
                                                            "step": 1,
                                                            "active": True,
                                                            "persistent-hint": True,
                                                            "hint": "签到失败后额外重试次数，默认不重试",
                                                            "placeholder": "默认0次",
                                                            "prepend-inner-icon": "mdi-refresh"
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "retry_interval",
                                                            "label": "重试间隔(分钟)",
                                                            "type": "number",
                                                            "min": 1,
                                                            "step": 1,
                                                            "active": True,
                                                            "persistent-hint": True,
                                                            "hint": "每次失败重试之间的等待时间",
                                                            "placeholder": "默认5分钟",
                                                            "prepend-inner-icon": "mdi-timer-refresh-outline"
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
                        "component": "VCard",
                        "props": {
                            "variant": "flat",
                            "class": "mb-6",
                            "color": "surface"
                        },
                        "content": [
                            {
                                "component": "VCardItem",
                                "props": {"class": "px-6 pb-0"},
                                "content": [
                                    {
                                        "component": "VCardTitle",
                                        "props": {"class": "d-flex align-center text-h6 mb-0"},
                                        "content": [
                                            {
                                                "component": "VIcon",
                                                "props": {
                                                    "style": "color: #16b1ff;",
                                                    "class": "mr-3",
                                                    "size": "default"
                                                },
                                                "text": "mdi-information"
                                            },
                                            {
                                                "component": "span",
                                                "text": "使用说明"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "component": "VDivider",
                                "props": {"class": "mx-4 my-2"}
                            },
                            {
                                "component": "VCardText",
                                "props": {"class": "px-6 py-0"},
                                "content": [
                                    {
                                        "component": "VList",
                                        "props": {
                                            "lines": "two",
                                            "density": "comfortable"
                                        },
                                        "content": [
                                            {
                                                "component": "VListItem",
                                                "props": {"lines": "two"},
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "d-flex align-items-start"},
                                                        "content": [
                                                            {
                                                                "component": "VIcon",
                                                                "props": {"color": "primary", "class": "mt-1 mr-2"},
                                                                "text": "mdi-account-key"
                                                            },
                                                            {
                                                                "component": "div",
                                                                "props": {"class": "text-subtitle-1 font-weight-regular mb-1"},
                                                                "text": "登录方式"
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-body-2 ml-8"},
                                                        "text": "使用聚影站点账号密码登录接口，不依赖浏览器 Cookie。"
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VListItem",
                                                "props": {"lines": "two"},
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "d-flex align-items-start"},
                                                        "content": [
                                                            {
                                                                "component": "VIcon",
                                                                "props": {"color": "success", "class": "mt-1 mr-2"},
                                                                "text": "mdi-shield-key"
                                                            },
                                                            {
                                                                "component": "div",
                                                                "props": {"class": "text-subtitle-1 font-weight-regular mb-1"},
                                                                "text": "鉴权方式"
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-body-2 ml-8"},
                                                        "text": "登录后自动使用 X-App-User-Token 调用状态和签到接口。"
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VListItem",
                                                "props": {"lines": "two"},
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "d-flex align-items-start"},
                                                        "content": [
                                                            {
                                                                "component": "VIcon",
                                                                "props": {"color": "warning", "class": "mt-1 mr-2"},
                                                                "text": "mdi-run-fast"
                                                            },
                                                            {
                                                                "component": "div",
                                                                "props": {"class": "text-subtitle-1 font-weight-regular mb-1"},
                                                                "text": "立即执行一次"
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-body-2 ml-8"},
                                                        "text": "保存配置时勾选后会立刻执行一次签到，完成后自动取消勾选。"
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "VListItem",
                                                "props": {"lines": "two"},
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "d-flex align-items-start"},
                                                        "content": [
                                                            {
                                                                "component": "VIcon",
                                                                "props": {"color": "error", "class": "mt-1 mr-2"},
                                                                "text": "mdi-history"
                                                            },
                                                            {
                                                                "component": "div",
                                                                "props": {"class": "text-subtitle-1 font-weight-regular mb-1"},
                                                                "text": "历史记录"
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-body-2 ml-8"},
                                                        "text": "每次执行结果都会写入插件历史，并在详情页中展示最近记录。"
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
        ], self._get_config()

    def get_page(self) -> List[dict]:
        latest = self.get_data("latest_result") or {}
        history = self.get_data("history") or []
        profile = self.get_data("profile") or {}
        user = (profile or {}).get("user") or {}

        configured = bool(self._username and self._password)
        status_text = "已启用" if self._enabled else "未启用"
        last_message = latest.get("message") or "暂无执行记录"
        last_time = latest.get("timestamp") or "--"
        username = user.get("username") or latest.get("username") or self._username or "--"
        user_id = user.get("id") or "--"
        level = user.get("level")
        current_points = user.get("points", latest.get("points"))
        checkin_days = user.get("checkin_days", latest.get("checkin_days"))
        points_awarded = latest.get("points_awarded")
        level_name = user.get("level_name") or "--"
        reward_points = latest.get("points_awarded")
        email = user.get("email") or "--"
        joined_at = user.get("date_joined") or "--"
        favorite_count = user.get("favorite_count")
        upload_count = user.get("upload_count")

        registered_days = "--"
        if joined_at and joined_at != "--":
            try:
                joined_dt = datetime.fromisoformat(joined_at.replace("Z", "+00:00"))
                registered_days = max((datetime.now(joined_dt.tzinfo) - joined_dt).days, 0)
            except Exception:
                registered_days = "--"

        status_color = "success" if latest.get("success") else ("warning" if latest else "info")
        action_map = {
            "signed": "签到成功",
            "already_signed": "今日已签到",
            "failed": "执行失败",
            "config_required": "待配置",
        }
        action_text = action_map.get(latest.get("action"), "暂无状态")

        history_rows = []
        for item in history[:10]:
            success = item.get("success")
            action = item.get("action")
            action_text_row = action_map.get(action, action or "--")
            action_color = "success" if success else ("warning" if action == "already_signed" else "error")
            action_icon = "mdi-check-circle" if success else ("mdi-alert-circle" if action == "already_signed" else "mdi-close-circle")
            history_rows.append({
                "component": "tr",
                "props": {
                    "class": "text-sm"
                },
                "content": [
                    {
                        "component": "td",
                        "props": {
                            "class": "text-center text-high-emphasis"
                        },
                        "content": [
                            {"component": "VIcon", "props": {"color": "info", "size": "x-small", "class": "mr-1"}, "text": "mdi-clock-time-four-outline"},
                            {"component": "span", "text": item.get("timestamp") or "--"}
                        ]
                    },
                    {
                        "component": "td",
                        "props": {
                            "class": "text-center text-high-emphasis"
                        },
                        "content": [
                            {
                                "component": "VChip",
                                "props": {
                                    "color": action_color,
                                    "size": "small",
                                    "variant": "tonal"
                                },
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "size": "small",
                                            "start": True
                                        },
                                        "text": action_icon
                                    },
                                    {
                                        "component": "span",
                                        "text": action_text_row
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "td",
                        "props": {
                            "class": "text-center text-high-emphasis"
                        },
                        "content": [
                            {"component": "VIcon", "props": {"color": "info", "size": "x-small", "class": "mr-1"}, "text": "mdi-counter"},
                            {"component": "span", "text": f"{item.get('checkin_days', '-') or '-'}天"}
                        ]
                    },
                    {
                        "component": "td",
                        "props": {
                            "class": "text-center text-high-emphasis"
                        },
                        "content": [
                            {"component": "VIcon", "props": {"color": "warning", "size": "x-small", "class": "mr-1"}, "text": "mdi-star-circle-outline"},
                            {"component": "span", "text": str(item.get("points_awarded", "-"))}
                        ]
                    },
                    {
                        "component": "td",
                        "props": {
                            "class": "text-center text-high-emphasis"
                        },
                        "content": [
                            {
                                "component": "VChip",
                                "props": {
                                    "color": "warning" if item.get("is_retry_task") else "default",
                                    "size": "small",
                                    "variant": "tonal"
                                },
                                "text": "是" if item.get("is_retry_task") else "否"
                            }
                        ]
                    },
                    {
                        "component": "td",
                        "props": {
                            "class": "text-center text-high-emphasis"
                        },
                        "content": [
                            {"component": "VIcon", "props": {"color": "primary", "size": "x-small", "class": "mr-1"}, "text": "mdi-text-box-outline"},
                            {"component": "span", "text": item.get("message") or "--"}
                        ]
                    },
                ]
            })

        if not history_rows:
            history_rows.append({
                "component": "tr",
                "content": [
                    {
                        "component": "td",
                        "props": {"colspan": 5, "class": "text-center text-medium-emphasis"},
                        "text": "暂无签到历史"
                    }
                ]
            })

        return [
            {
                "component": "VRow",
                "content": [
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 6},
                        "content": [
                            {
                                "component": "VCard",
                                "props": {"variant": "flat", "class": "mb-6 h-100", "color": "surface"},
                                "content": [
                                    {
                                        "component": "VCardItem",
                                        "props": {"class": "px-6 pb-0"},
                                        "content": [
                                            {
                                                "component": "VCardTitle",
                                                "props": {"class": "d-flex align-center text-h6"},
                                                "content": [
                                                    {
                                                        "component": "VIcon",
                                                        "props": {"class": "mr-3", "style": "color: #2196F3;", "size": "default"},
                                                        "text": "mdi-movie-check-outline"
                                                    },
                                                    {"component": "span", "text": "设置状态"}
                                                ]
                                            }
                                        ]
                                    },
                                    {"component": "VDivider", "props": {"class": "mx-4 my-2"}},
                                    {
                                        "component": "VCardText",
                                        "props": {"class": "px-6 pb-6"},
                                        "content": [
                                            {
                                                "component": "VRow",
                                                "content": [
                                                    {
                                                        "component": "VCol",
                                                        "props": {"cols": 12, "md": 3},
                                                        "content": [
                                                            {
                                                                "component": "div",
                                                                "props": {"class": "d-flex flex-column justify-space-between", "style": "min-height: 64px;"},
                                                                "content": [
                                                                    {
                                                                        "component": "div",
                                                                        "props": {"class": "text-subtitle-2 text-medium-emphasis"},
                                                                        "text": "插件状态"
                                                                    },
                                                                    {
                                                                        "component": "VChip",
                                                                        "props": {"color": "success" if self._enabled else "grey", "class": "mt-2 align-self-start"},
                                                                        "text": status_text
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "VCol",
                                                        "props": {"cols": 12, "md": 3},
                                                        "content": [
                                                            {
                                                                "component": "div",
                                                                "props": {"class": "d-flex flex-column justify-space-between", "style": "min-height: 64px;"},
                                                                "content": [
                                                                    {
                                                                        "component": "div",
                                                                        "props": {"class": "text-subtitle-2 text-medium-emphasis"},
                                                                        "text": "账号配置"
                                                                    },
                                                                    {
                                                                        "component": "VChip",
                                                                        "props": {"color": "success" if configured else "warning", "class": "mt-2 align-self-start"},
                                                                        "text": "已配置" if configured else "未配置"
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "VCol",
                                                        "props": {"cols": 12, "md": 3},
                                                        "content": [
                                                            {
                                                                "component": "div",
                                                                "props": {"class": "d-flex flex-column justify-space-between", "style": "min-height: 64px;"},
                                                                "content": [
                                                                    {
                                                                        "component": "div",
                                                                        "props": {"class": "text-subtitle-2 text-medium-emphasis"},
                                                                        "text": "调度周期"
                                                                    },
                                                                    {
                                                                        "component": "div",
                                                                        "props": {"class": "text-body-1 mt-2"},
                                                                        "text": self._cron or "--"
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "VCol",
                                                        "props": {"cols": 12, "md": 3},
                                                        "content": [
                                                            {
                                                                "component": "div",
                                                                "props": {"class": "d-flex flex-column justify-space-between", "style": "min-height: 64px;"},
                                                                "content": [
                                                                    {
                                                                        "component": "div",
                                                                        "props": {"class": "text-subtitle-2 text-medium-emphasis"},
                                                                        "text": "最近状态"
                                                                    },
                                                                    {
                                                                        "component": "VChip",
                                                                        "props": {"color": status_color, "class": "mt-2 align-self-start"},
                                                                        "text": action_text
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
                        ]
                    },
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 6},
                        "content": [
                            {
                                "component": "VCard",
                                "props": {"variant": "flat", "class": "mb-6 h-100", "color": "surface"},
                                "content": [
                                    {
                                        "component": "VCardItem",
                                        "props": {"class": "px-6 pb-0"},
                                        "content": [
                                            {
                                                "component": "VCardTitle",
                                                "props": {"class": "d-flex align-center text-h6"},
                                                "content": [
                                                    {"component": "VIcon", "props": {"class": "mr-3", "style": "color: #4CAF50;", "size": "default"}, "text": "mdi-account-circle-outline"},
                                                    {"component": "span", "text": "用户信息"}
                                                ]
                                            }
                                        ]
                                    },
                                    {"component": "VDivider", "props": {"class": "mx-4 my-2"}},
                                    {
                                        "component": "VCardText",
                                        "props": {"class": "px-6 pb-6"},
                                        "content": [
                                            {
                                                "component": "div",
                                                "props": {"class": "d-flex flex-wrap align-center justify-space-between mb-3 ga-2"},
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-h6 font-weight-bold"},
                                                        "text": username
                                                    },
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "d-flex flex-wrap ga-2"},
                                                        "content": [
                                                            {
                                                                "component": "VChip",
                                                                "props": {"color": "primary", "variant": "tonal", "class": "ma-1"},
                                                                "text": f"等级：Lv.{level if level is not None else '--'} {level_name}"
                                                            },
                                                            {
                                                                "component": "VChip",
                                                                "props": {"color": "secondary", "variant": "tonal", "class": "ma-1"},
                                                                "text": f"ID：{user_id}"
                                                            },
                                                            {
                                                                "component": "VChip",
                                                                "props": {"color": "success", "variant": "tonal", "class": "ma-1"},
                                                                "text": f"积分：{current_points if current_points is not None else '--'}"
                                                            },
                                                            {
                                                                "component": "VChip",
                                                                "props": {"color": "info", "variant": "tonal", "class": "ma-1"},
                                                                "text": f"签到天数：{checkin_days if checkin_days is not None else '--'}"
                                                            }
                                                        ]
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "div",
                                                "props": {"class": "d-flex flex-wrap align-center justify-space-between ga-2 text-body-2 text-medium-emphasis"},
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "content": [
                                                            {
                                                                "component": "VIcon",
                                                                "props": {"color": "info", "size": "x-small", "class": "mr-1"},
                                                                "text": "mdi-email-outline"
                                                            },
                                                            {
                                                                "component": "span",
                                                                "text": email
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "d-flex flex-wrap ga-2"},
                                                        "content": [
                                                            {
                                                                "component": "VChip",
                                                                "props": {"color": "secondary", "variant": "tonal", "class": "ma-1"},
                                                                "text": f"收藏数量：{favorite_count if favorite_count is not None else '--'}"
                                                            },
                                                            {
                                                                "component": "VChip",
                                                                "props": {"color": "secondary", "variant": "tonal", "class": "ma-1"},
                                                                "text": f"上传数量：{upload_count if upload_count is not None else '--'}"
                                                            },
                                                            {
                                                                "component": "VChip",
                                                                "props": {"color": "deep-purple", "variant": "tonal", "class": "ma-1"},
                                                                "text": f"已注册：{registered_days}天"
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
                    },
                    {
                        "component": "VCol",
                        "props": {"cols": 12},
                        "content": [
                            {
                                "component": "VCard",
                                "props": {"variant": "flat", "class": "mb-4 elevation-2", "color": "surface", "style": "border-radius: 16px;"},
                                "content": [
                                    {
                                        "component": "VCardItem",
                                        "props": {"class": "pa-6"},
                                        "content": [
                                            {
                                                "component": "VCardTitle",
                                                "props": {"class": "d-flex align-center text-h6"},
                                                "content": [
                                                    {"component": "VIcon", "props": {"class": "mr-3", "style": "color: #9C27B0;", "size": "default"}, "text": "mdi-table-clock"},
                                                    {"component": "span", "text": "最近签到历史"}
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "component": "VCardText",
                                        "props": {"class": "pa-6"},
                                        "content": [
                                            {
                                                "component": "VTable",
                                                "props": {"hover": True, "density": "comfortable", "class": "rounded-lg"},
                                                "content": [
                                                    {
                                                        "component": "thead",
                                                        "content": [
                                                            {
                                                                "component": "tr",
                                                                "content": [
                                                                    {
                                                                        "component": "th",
                                                                        "props": {"class": "text-center text-body-1 font-weight-bold"},
                                                                        "content": [
                                                                            {"component": "VIcon", "props": {"color": "info", "size": "small", "class": "mr-1"}, "text": "mdi-clock-time-four-outline"},
                                                                            {"component": "span", "text": "签到时间"}
                                                                        ]
                                                                    },
                                                                    {
                                                                        "component": "th",
                                                                        "props": {"class": "text-center text-body-1 font-weight-bold"},
                                                                        "content": [
                                                                            {"component": "VIcon", "props": {"color": "success", "size": "small", "class": "mr-1"}, "text": "mdi-check-circle"},
                                                                            {"component": "span", "text": "签到状态"}
                                                                        ]
                                                                    },
                                                                    {
                                                                        "component": "th",
                                                                        "props": {"class": "text-center text-body-1 font-weight-bold"},
                                                                        "content": [
                                                                            {"component": "VIcon", "props": {"color": "info", "size": "small", "class": "mr-1"}, "text": "mdi-counter"},
                                                                            {"component": "span", "text": "签到天数"}
                                                                        ]
                                                                    },
                                                                    {
                                                                        "component": "th",
                                                                        "props": {"class": "text-center text-body-1 font-weight-bold"},
                                                                        "content": [
                                                                            {"component": "VIcon", "props": {"color": "warning", "size": "small", "class": "mr-1"}, "text": "mdi-star-circle-outline"},
                                                                            {"component": "span", "text": "奖励积分"}
                                                                        ]
                                                                    },
                                                                    {
                                                                        "component": "th",
                                                                        "props": {"class": "text-center text-body-1 font-weight-bold"},
                                                                        "content": [
                                                                            {"component": "VIcon", "props": {"color": "warning", "size": "small", "class": "mr-1"}, "text": "mdi-refresh-auto"},
                                                                            {"component": "span", "text": "重试任务"}
                                                                        ]
                                                                    },
                                                                    {
                                                                        "component": "th",
                                                                        "props": {"class": "text-center text-body-1 font-weight-bold"},
                                                                        "content": [
                                                                            {"component": "VIcon", "props": {"color": "primary", "size": "small", "class": "mr-1"}, "text": "mdi-text-box-outline"},
                                                                            {"component": "span", "text": "结果说明"}
                                                                        ]
                                                                    },
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        "component": "tbody",
                                                        "content": history_rows
                                                    }
                                                ]
                                            },
                                            {
                                                "component": "div",
                                                "props": {
                                                    "class": "text-caption text-grey mt-2",
                                                    "style": "background: #f5f5f7; border-radius: 8px; padding: 6px 12px; display: inline-block;"
                                                },
                                                "content": [
                                                    {"component": "VIcon", "props": {"size": "x-small", "class": "mr-1"}, "text": "mdi-format-list-bulleted"},
                                                    {"component": "span", "text": f"共显示 {len(history[:10])} 条签到记录"}
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
        ]

    def _get_config(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "notify": self._notify,
            "onlyonce": self._onlyonce,
            "cron": self._cron or "",
            "username": self._username,
            "usr_password": self._password,
            "use_proxy": self._use_proxy,
            "history_count": self._history_count,
            "random_time_range": self._random_time_range,
            "retry_count": self._retry_count,
            "retry_interval": self._retry_interval,
        }

    def _save_config(self, config: dict) -> Dict[str, Any]:
        new_config = {
            "enabled": self._to_bool(config.get("enabled", False)),
            "notify": self._to_bool(config.get("notify", False)),
            "onlyonce": self._to_bool(config.get("onlyonce", False)),
            "cron": config.get("cron") or "0 10 * * *",
            "username": (config.get("username") or "").strip(),
            "usr_password": config.get("usr_password") or "",
            "use_proxy": self._to_bool(config.get("use_proxy", False)),
            "history_count": self._to_int(config.get("history_count", 30), 30),
            "random_time_range": (config.get("random_time_range") or "").strip(),
            "retry_count": self._to_int(config.get("retry_count", 0), 0),
            "retry_interval": self._to_int(config.get("retry_interval", 5), 5),
        }
        self.update_config(new_config)
        self.init_plugin(new_config)
        return {"success": True, "message": "配置保存成功", "data": self._get_config()}

    def _parse_random_time_range(self) -> Tuple[int, int]:
        raw_value = (self._random_time_range or "").strip()
        if not raw_value:
            return 0, 0

        try:
            if "-" in raw_value:
                start_text, end_text = raw_value.split("-", 1)
                start_min = max(0, int(start_text.strip() or 0))
                end_min = max(0, int(end_text.strip() or 0))
            else:
                start_min = 0
                end_min = max(0, int(raw_value))

            if end_min < start_min:
                start_min, end_min = end_min, start_min
            return start_min, end_min
        except Exception:
            logger.warning(f"{self.plugin_name}: 随机时间范围格式无效，已忽略 - {raw_value}")
            return 0, 0

    def _schedule_signin_with_random_delay(self) -> None:
        start_min, end_min = self._parse_random_time_range()
        delay_minutes = random.randint(start_min, end_min) if end_min > 0 else 0

        if delay_minutes <= 0:
            logger.info(f"{self.plugin_name}: 未设置随机延迟，立即执行签到任务")
            self._signin()
            return

        if not self._scheduler:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)

        run_time = datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(minutes=delay_minutes)
        logger.info(f"{self.plugin_name}: 定时任务触发，已安排在 {delay_minutes} 分钟后执行签到")
        self._scheduler.add_job(
            func=self._signin,
            trigger='date',
            run_date=run_time,
            name=f"{self.plugin_name} 随机签到"
        )

        if self._scheduler.get_jobs() and not self._scheduler.running:
            self._scheduler.start()

    def _schedule_retry_signin(self, retry_index: int) -> Optional[str]:
        if retry_index > self._retry_count:
            return None

        retry_interval = max(self._retry_interval, 1)
        if not self._scheduler:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)

        run_time = datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(minutes=retry_interval)
        self._scheduler.add_job(
            func=self._signin,
            kwargs={"retry_index": retry_index},
            trigger='date',
            run_date=run_time,
            name=f"{self.plugin_name} 失败重试 {retry_index}/{self._retry_count}"
        )

        if self._scheduler.get_jobs() and not self._scheduler.running:
            self._scheduler.start()

        return run_time.strftime("%Y-%m-%d %H:%M:%S")

    def _get_status(self) -> Dict[str, Any]:
        latest = self.get_data("latest_result") or {}
        history = self.get_data("history") or []
        return {
            "enabled": self._enabled,
            "cron": self._cron,
            "notify": self._notify,
            "use_proxy": self._use_proxy,
            "configured": bool(self._username and self._password),
            "latest_result": latest,
            "history_count": len(history),
        }

    def _get_history_api(self) -> Dict[str, Any]:
        return {"success": True, "data": self.get_data("history") or []}

    def _run_once(self) -> Dict[str, Any]:
        result = self._signin()
        return {"success": result.get("success", False), "data": result, "message": result.get("message", "")}

    def stop_service(self):
        try:
            Scheduler().remove_plugin_job(self.__class__.__name__.lower())
        except Exception as err:
            logger.debug(f"{self.plugin_name}: 停止服务时忽略错误 - {err}")

        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as err:
            logger.debug(f"{self.plugin_name}: 停止内部调度器时忽略错误 - {err}")

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "Accept": "application/json, text/plain, */*",
        })
        if self._use_proxy:
            proxy = getattr(settings, "PROXY", None)
            if proxy:
                session.proxies.update(proxy)
        return session

    def _get_csrf_token(self, session: requests.Session) -> str:
        token = session.cookies.get("csrftoken") or session.cookies.get("XSRF-TOKEN")
        if token:
            return token

        urls = [f"{self._base_url}/login", f"{self._base_url}/"]
        for url in urls:
            try:
                response = session.get(url, timeout=20)
                response.raise_for_status()
                token = session.cookies.get("csrftoken") or session.cookies.get("XSRF-TOKEN")
                if token:
                    return token
            except Exception as err:
                logger.warning(f"{self.plugin_name}: 获取 CSRF 失败 {url} - {err}")
        return ""

    def _login(self, session: requests.Session) -> Tuple[str, str]:
        csrf_token = self._get_csrf_token(session)
        headers = {
            "Content-Type": "application/json",
            "Origin": self._base_url,
            "Referer": f"{self._base_url}/login",
            "X-Requested-With": "XMLHttpRequest",
        }
        if csrf_token:
            headers["X-CSRFToken"] = csrf_token

        response = session.post(
            f"{self._base_url}/api/app/login/",
            json={"username": self._username, "password": self._password},
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "success" or not data.get("token"):
            raise ValueError(data.get("message") or data.get("detail") or "登录失败")
        return data["token"], csrf_token

    def _request_authed(
        self,
        session: requests.Session,
        method: str,
        path: str,
        token: str,
        csrf_token: str = "",
        referer: str = "/profile",
    ) -> Dict[str, Any]:
        headers = {
            "X-App-User-Token": token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self._base_url}{referer}",
        }
        if method.upper() != "GET":
            headers["Origin"] = self._base_url
        if csrf_token:
            headers["X-CSRFToken"] = csrf_token

        response = session.request(
            method=method.upper(),
            url=f"{self._base_url}{path}",
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()

        refreshed_token = response.headers.get("X-Refreshed-Token")
        if refreshed_token:
            token = refreshed_token

        data = response.json()
        data["_token"] = token
        return data

    def _record_history(self, record: Dict[str, Any]) -> None:
        history = self.get_data("history") or []
        history.append(record)
        history = sorted(history, key=lambda x: x.get("timestamp") or "", reverse=True)
        if len(history) > self._history_count:
            history = history[:self._history_count]
        self.save_data("history", history)
        self.save_data("latest_result", record)

    def _notify_result(self, title: str, text: str) -> None:
        if self._notify:
            self.post_message(
                mtype=NotificationType.SiteMessage,
                title=title,
                text=text,
            )

    def _signin(self, retry_index: int = 0) -> Dict[str, Any]:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self._username or not self._password:
            result = {
                "success": False,
                "timestamp": timestamp,
                "message": "未配置用户名或密码",
                "action": "config_required",
            }
            self._record_history(result)
            return result

        try:
            session = self._build_session()
            token, csrf_token = self._login(session)

            stats = self._request_authed(
                session=session,
                method="GET",
                path="/api/app/checkin/stats/",
                token=token,
                csrf_token=csrf_token,
                referer="/profile",
            )
            token = stats.get("_token", token)

            if stats.get("status") != "success":
                raise ValueError(stats.get("message") or "获取签到状态失败")

            profile = self._request_authed(
                session=session,
                method="GET",
                path="/api/app/profile/",
                token=token,
                csrf_token=csrf_token,
                referer="/profile",
            )
            token = profile.get("_token", token)
            user = (profile or {}).get("user") or {}
            self.save_data("profile", profile)

            if stats.get("checked_today"):
                result = {
                    "success": True,
                    "timestamp": timestamp,
                    "message": "今日已签到",
                    "action": "already_signed",
                    "checked_today": True,
                    "today": stats.get("today"),
                    "reward_points": stats.get("reward_points"),
                    "my_total_days": stats.get("my_total_days"),
                    "today_checkin_count": stats.get("today_checkin_count"),
                    "username": user.get("username") or self._username,
                    "points": user.get("points"),
                    "checkin_days": user.get("checkin_days"),
                }
                self._record_history(result)
                self._notify_result(
                    title="【🎬聚影签到】任务完成",
                    text=(
                        f"━━━━━━━━━━━━━━\n"
                        f"✨ 状态：ℹ️今日已签到\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"📊 数据统计\n"
                        f"👤 用户：{result['username']}\n"
                        f"⭐ 当前积分：{result.get('points')}\n"
                        f"📆 累计签到：{result.get('checkin_days')}天\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"🕐 签到时间：{timestamp}"
                    ),
                )
                return result

            signin = self._request_authed(
                session=session,
                method="POST",
                path="/api/app/checkin/do/",
                token=token,
                csrf_token=csrf_token,
                referer="/profile",
            )

            if signin.get("status") != "success":
                raise ValueError(signin.get("message") or "签到失败")

            profile_after = self._request_authed(
                session=session,
                method="GET",
                path="/api/app/profile/",
                token=signin.get("_token", token),
                csrf_token=csrf_token,
                referer="/profile",
            )
            user_after = (profile_after or {}).get("user") or {}
            self.save_data("profile", profile_after)

            result = {
                "success": True,
                "timestamp": timestamp,
                "message": signin.get("message") or "签到成功",
                "action": "signed",
                "points_awarded": signin.get("points_awarded"),
                "today_checkin_count": signin.get("today_checkin_count"),
                "my_total_days": signin.get("my_total_days"),
                "username": user_after.get("username") or self._username,
                "points": user_after.get("points"),
                "checkin_days": user_after.get("checkin_days"),
            }
            self._record_history(result)
            self._notify_result(
                title="【🎬聚影签到】任务完成",
                text=(
                    f"━━━━━━━━━━━━━━\n"
                    f"✨ 状态：✅已签到\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"📊 数据统计\n"
                    f"👤 用户：{result['username']}\n"
                    f"🎁 奖励积分：{result.get('points_awarded')}\n"
                    f"⭐ 当前积分：{result.get('points')}\n"
                    f"📆 累计签到：{result.get('checkin_days')}天\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"🕐 签到时间：{timestamp}"
                ),
            )
            return result
        except Exception as err:
            logger.error(f"{self.plugin_name}: 执行签到失败 - {err}")
            next_retry_time = None
            if retry_index < self._retry_count:
                next_retry_time = self._schedule_retry_signin(retry_index + 1)

            result = {
                "success": False,
                "timestamp": timestamp,
                "message": str(err),
                "action": "failed",
                "retry_index": retry_index,
                "next_retry_time": next_retry_time,
                "is_retry_task": retry_index > 0,
            }
            self._record_history(result)
            self._notify_result(
                title="【🎬聚影签到】任务完成",
                text=(
                    f"━━━━━━━━━━━━━━\n"
                    f"✨ 状态：❌签到失败\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"📊 数据统计\n"
                    f"👤 用户：{self._username or '--'}\n"
                    f"💬 失败原因：{err}\n"
                    f"🔁 当前重试：{retry_index}/{self._retry_count}\n"
                    f"⏰ 下次重试：{next_retry_time or '无'}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"🕐 签到时间：{timestamp}"
                ),
            )
            return result
