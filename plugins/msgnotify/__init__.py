from app.plugins import _PluginBase
from typing import Any, List, Dict, Tuple
from app.log import logger
from app.schemas import NotificationType
from app.core.config import settings
from app import schemas
from pydantic import BaseModel

class NotifyRequest(BaseModel):
    title: str
    text: str

class MsgNotify(_PluginBase):
    # 插件名称
    plugin_name = "外部消息转发"
    # 插件描述
    plugin_desc = "接收外部应用自定义消息并推送。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/MsgNotify.png"
    # 插件版本
    plugin_version = "1.3.3"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "msgnotify_"
    # 加载顺序
    plugin_order = 30
    # 可使用的用户级别
    auth_level = 1

    # 任务执行间隔
    _enabled = False
    _notify = False
    _msgtype = None
    _notify_style = None

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._msgtype = config.get("msgtype")
            self._notify_style = config.get("notify_style")

    def msg_notify_json(self, apikey: str, request: NotifyRequest) -> schemas.Response:
        """
        post 方式发送通知
        """
        if apikey != settings.API_TOKEN:
            return schemas.Response(success=False, message="API令牌错误!")

        title = request.title
        text = request.text
        logger.info(f"收到以下消息:\n{title}\n{text}")
        if self._enabled and self._notify:
            mtype = NotificationType.Manual
            if self._msgtype:
                mtype = NotificationType.__getitem__(str(self._msgtype)) or NotificationType.Manual
            
            if self._notify_style == "card":
                # 使用卡片样式发送通知，正文合并标题和内容
                card_text = f"{text}\n"
                self.post_message(mtype=mtype,
                                title=title,
                                text=card_text,
                                image=self.plugin_icon)
            else:
                # 使用默认样式发送通知
                self.post_message(mtype=mtype,
                                title=title,
                                text=text)

        return schemas.Response(
            success=True,
            message="发送成功"
        )

    
    def msg_notify_form(self, apikey: str, title: str, text: str) -> schemas.Response:
        """
        get 方式发送通知
        """
        if apikey != settings.API_TOKEN:
            return schemas.Response(success=False, message="API令牌错误!")

        logger.info(f"收到以下消息:\n{title}\n{text}")
        if self._enabled and self._notify:
            mtype = NotificationType.Manual
            if self._msgtype:
                mtype = NotificationType.__getitem__(str(self._msgtype)) or NotificationType.Manual
            
            if self._notify_style == "card":
                # 使用卡片样式发送通知，正文合并标题和内容
                card_text = f"{text}\n"
                self.post_message(mtype=mtype,
                                title=title,
                                text=card_text,
                                image=self.plugin_icon)
            else:
                # 使用默认样式发送通知
                self.post_message(mtype=mtype,
                                title=title,
                                text=text)

        return schemas.Response(
            success=True,
            message="发送成功"
        )

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件API
        [{
            "path": "/xx",
            "endpoint": self.xxx,
            "methods": ["GET", "POST"],
            "summary": "API说明"
        }]
        """
        return [{
            "path": "/send_json",
            "endpoint": self.msg_notify_json,
            "methods": ["POST"],
            "summary": "外部应用自定义消息接口使用的API",
            "description": "接受自定义消息webhook通知并推送",
        },
        {
            "path": "/send_form",
            "endpoint": self.msg_notify_form,
            "methods": ["GET"],
            "summary": "外部应用自定义消息接口使用的API",
            "description": "接受自定义消息webhook通知并推送",
        }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        MsgTypeOptions = []
        for item in NotificationType:
            MsgTypeOptions.append({
                "title": item.value,
                "value": item.name
            })
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
                                    'class': 'px-6 pb-0'
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
                                                    'style': 'color: #16b1ff;',
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
                                'component': 'VDivider',
                                'props': {
                                    'class': 'mx-4 my-2'
                                }
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
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'multiple': False,
                                                            'chips': True,
                                                            'model': 'notify_style',
                                                            'label': '通知样式',
                                                            'items': [
                                                                {
                                                                    'title': '默认样式',
                                                                    'value': 'default'
                                                                },
                                                                {
                                                                    'title': '卡片样式',
                                                                    'value': 'card'
                                                                }
                                                            ],
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
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'multiple': False,
                                                            'chips': True,
                                                            'model': 'msgtype',
                                                            'label': '消息类型',
                                                            'items': MsgTypeOptions,
                                                            'hint': '如不选择，消息类型默认为[手动处理]。',
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
                                    'class': 'px-6 pb-0'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6 mb-0'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-3',
                                                    'size': 'default'
                                                },
                                                'text': 'mdi-information'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '插件使用说明'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider',
                                'props': {
                                    'class': 'mx-4 my-2'
                                }
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6 pb-6'
                                },
                                'content': [
                                    {
                                        'component': 'VList',
                                        'props': {
                                            'lines': 'two',
                                            'density': 'comfortable'
                                        },
                                        'content': [
                                            {
                                                'component': 'VListItem',
                                                'props': {
                                                    'title': 'API接口说明'
                                                },
                                                'slots': {
                                                    'prepend': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'primary'
                                                            },
                                                            'text': 'mdi-api'
                                                        }
                                                    ]
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2'
                                                        },
                                                        'text': 'GET接口地址：http://moviepilot_ip:port/api/v1/plugin/MsgNotify/send_form?apikey=api_token'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2'
                                                        },
                                                        'text': 'POST接口地址：http://moviepilot_ip:port/api/v1/plugin/MsgNotify/send_json?apikey=api_token'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {
                                                    'title': '请求参数说明'
                                                },
                                                'slots': {
                                                    'prepend': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'success'
                                                            },
                                                            'text': 'mdi-format-list-bulleted'
                                                        }
                                                    ]
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2',
                                                            'style': 'line-height: 1.2; padding: 0; margin: 0;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': 'GET请求：必要参数'
                                                            },
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'size': 'default',
                                                                    'class': 'mx-1',
                                                                    'variant': 'text',
                                                                    'style': 'padding: 0 4px; height: 20px; min-height: 0; line-height: 20px;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'style': 'text-decoration: underline;'
                                                                        },
                                                                        'text': 'apikey={API_TOKEN}；title=消息标题；text=消息内容'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'br'
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': 'POST请求：请求类型'
                                                            },
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'size': 'default',
                                                                    'class': 'mx-1',
                                                                    'variant': 'text',
                                                                    'style': 'padding: 0 4px; height: 20px; min-height: 0; line-height: 20px;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'style': 'text-decoration: underline;'
                                                                        },
                                                                        'text': 'application/json'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': '，请求体'
                                                            },
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'size': 'default',
                                                                    'class': 'mx-1',
                                                                    'variant': 'text',
                                                                    'style': 'padding: 0 4px; height: 20px; min-height: 0; line-height: 20px;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'style': 'text-decoration: underline;'
                                                                        },
                                                                        'text': '{"title": "{title}", "text": "{content}"}'
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {
                                                    'title': '特别说明'
                                                },
                                                'slots': {
                                                    'prepend': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'warning'
                                                            },
                                                            'text': 'mdi-alert'
                                                        }
                                                    ]
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2'
                                                        },
                                                        'text': '启用插件后如果API未生效需要重启MoviePilot使生API效。'
                                                    },
                                                    {
                                                        'component': 'div'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2'
                                                        },
                                                        'text': '其中moviepilot_ip:port为MoviePilot的IP地址和端口号，api_token为MoviePilot的API令牌。'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {
                                                    'title': '使用示列'
                                                },
                                                'slots': {
                                                    'prepend': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'info'
                                                            },
                                                            'text': 'mdi-information'
                                                        }
                                                    ]
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '必要参数或请求体可用变量请根据你使用的第三方应用要求填写！使用示列：'
                                                            },
                                                            {
                                                                'component': 'a',
                                                                'props': {
                                                                    'href': 'https://github.com/KoWming/MoviePilot-Plugins/blob/main/plugins/README.md',
                                                                    'target': '_blank',
                                                                    'style': 'text-decoration: underline;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'u',
                                                                        'props': {
                                                                            'style': 'color: #16b1ff;'
                                                                        },
                                                                        'text': 'README.md'
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {
                                                    'title': '致谢'
                                                },
                                                'slots': {
                                                    'prepend': [
                                                        {
                                                            'component': 'VIcon',
                                                            'props': {
                                                                'color': 'error'
                                                            },
                                                            'text': 'mdi-heart'
                                                        }
                                                    ]
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '参考了 '
                                                            },
                                                            {
                                                                'component': 'a',
                                                                'props': {
                                                                    'href': 'https://github.com/thsrite/MoviePilot-Plugins/',
                                                                    'target': '_blank',
                                                                    'style': 'text-decoration: underline;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'u',
                                                                        'text': 'thsrite/MoviePilot-Plugins'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': ' 项目，实现了插件的相关功能。特此感谢 '
                                                            },
                                                            {
                                                                'component': 'a',
                                                                'props': {
                                                                    'href': 'https://github.com/thsrite',
                                                                    'target': '_blank',
                                                                    'style': 'text-decoration: underline;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'u',
                                                                        'text': 'thsrite'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': ' 大佬！'
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
            }
        ], {
            "enabled": False,
            "notify": False,
            "notify_style": "default",
            "msgtype": "Manual"
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        pass
