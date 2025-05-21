from app.plugins import _PluginBase
from typing import Any, List, Dict, Tuple
from app.log import logger
from app.schemas import NotificationType
from app.core.config import settings
from app import schemas
from pydantic import BaseModel
import json
import random

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
    plugin_version = "1.3.5"
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
    _image_mappings = None
    _image_history = {}  # 用于记录每个关键词的图片使用历史

    def __init__(self):
        super().__init__()
        self._image_history = {}  # 用于记录每个关键词的图片使用历史

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._msgtype = config.get("msgtype")
            try:
                self._image_mappings = json.loads(config.get("image_mappings", "[]"))
            except:
                self._image_mappings = []

    def _get_matched_image(self, title: str, text: str) -> Tuple[str, str]:
        """
        根据消息标题和内容匹配对应的图片URL和通知样式
        返回: (图片URL, 通知样式)
        """
        if not self._image_mappings:
            logger.debug("没有配置图片映射,使用默认图标")
            return self.plugin_icon, "default"
            
        for mapping in self._image_mappings:
            keyword = mapping.get("keyword", "")
            if not keyword:
                continue
                
            # 检查标题和内容是否包含关键词
            if keyword.lower() in title.lower() or keyword.lower() in text.lower():
                # 收集所有image_url开头的字段
                image_urls = []
                for key, value in mapping.items():
                    if key.startswith("image_url") and value and value.strip():
                        image_urls.append(value)
                        logger.debug(f"找到图片URL: {key}={value}")
                
                # 获取通知样式,默认为default
                style = mapping.get("style", "default")
                if style not in ["default", "card"]:
                    logger.warning(f"无效的通知样式 '{style}', 使用默认样式")
                    style = "default"
                
                # 如果找到图片URL,使用历史记录避免重复
                if image_urls:
                    # 获取该关键词的历史记录
                    history = self._image_history.get(keyword, [])
                    
                    # 过滤掉最近使用过的图片
                    available_urls = [url for url in image_urls if url not in history]
                    
                    # 如果所有图片都使用过了,清空历史记录
                    if not available_urls:
                        available_urls = image_urls
                        history = []
                    
                    # 随机选择一张图片
                    selected_url = random.choice(available_urls)
                    
                    # 更新历史记录,保持最近3次的记录
                    history.append(selected_url)
                    if len(history) > 3:
                        history.pop(0)
                    self._image_history[keyword] = history
                    
                    logger.info(f"为关键词 '{keyword}' 选择图片: {selected_url}, 使用样式: {style}")
                    return selected_url, style
                else:
                    logger.debug(f"关键词 '{keyword}' 没有找到任何有效的图片URL,使用默认图标")
                    return self.plugin_icon, style
        logger.debug("没有匹配到任何关键词,使用默认图标")
        return self.plugin_icon, "default"

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
            
            # 获取匹配的图片URL和通知样式
            image_url, style = self._get_matched_image(title, text)
            
            if style == "card":
                # 使用卡片样式发送通知，正文合并标题和内容
                card_text = f"{text}\n"
                self.post_message(mtype=mtype,
                                title=title,
                                text=card_text,
                                image=image_url)
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
            
            # 获取匹配的图片URL和通知样式
            image_url, style = self._get_matched_image(title, text)
            
            if style == "card":
                # 使用卡片样式发送通知，正文合并标题和内容
                card_text = f"{text}\n"
                self.post_message(mtype=mtype,
                                title=title,
                                text=card_text,
                                image=image_url)
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
                                                    'sm': 4
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
                                                    'sm': 4
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
                                                    'sm': 4
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
                                                        'text': 'mdi-pencil'
                                                    },
                                                    {
                                                        'component': 'span',
                                                        'text': '自定义通知样式'
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
                                            'class': 'px-6 pb-0'
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
                                                                'component': 'VTextarea',
                                                                'props': {
                                                                    'model': 'image_mappings',
                                                                    'label': '自定义设置',
                                                                    'hint': 'JSON格式配置,例如: [{"keyword": "群辉", "image_url1": "https://example.com/synology1.jpg", "image_url2": "https://example.com/synology2.jpg", "style": "card"}]',
                                                                    'height': 450,
                                                                    'auto-grow': False,
                                                                    'hide-details': False,
                                                                    'persistent-hint': True,
                                                                    'placeholder': '[\n  {\n    "keyword": "群辉",\n    "image_url1": "https://example.com/synology1.jpg",\n    "image_url2": "https://example.com/synology2.jpg",\n    "style": "card"\n  },\n  {\n    "keyword": "Lucky",\n    "image_url": "https://example.com/Lucky.jpg",\n    "style": "default"\n  }\n]'
                                                                }
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
                                                    'lines': 'two'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-items-start'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'primary',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-api'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-regular mb-1'
                                                                },
                                                                'text': 'API接口说明'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'text': 'GET接口地址：http://moviepilot_ip:port/api/v1/plugin/MsgNotify/send_form?apikey=api_token'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'text': 'POST接口地址：http://moviepilot_ip:port/api/v1/plugin/MsgNotify/send_json?apikey=api_token'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {
                                                    'lines': 'two'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-items-start'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'success',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-format-list-bulleted'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-regular mb-1'
                                                                },
                                                                'text': '请求参数说明'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8',
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
                                                                    'style': 'padding: 0 4px; height: auto; min-height: 0; line-height: 20px; white-space: normal; word-break: break-all; background-color: transparent; border: none; border-radius: 0;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
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
                                                                    'style': 'padding: 0 4px; height: 20px; min-height: 0; line-height: 20px; background-color: transparent; border: none; border-radius: 0;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
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
                                                                    'style': 'padding: 0 4px; height: auto; min-height: 0; line-height: 20px; white-space: normal; word-break: break-all; background-color: transparent; border: none; border-radius: 0;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
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
                                                    'lines': 'two'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-items-start'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'warning',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-alert'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-regular mb-1'
                                                                },
                                                                'text': '特别说明'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'text': '启用插件后如果API未生效需要重启MoviePilot或重新保存插件配置使API生效。'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'ml-8'
                                                        }
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'text': '其中moviepilot_ip:port为MoviePilot的IP地址和端口号，api_token为MoviePilot的API令牌。'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {
                                                    'lines': 'two'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-items-start'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': '#66BB6A',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-puzzle'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-regular mb-1'
                                                                },
                                                                'text': '自定义说明'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '配置格式为JSON数组，每个元素包含以下字段：'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '• '
                                                            },
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'size': 'default',
                                                                    'class': 'mx-1',
                                                                    'variant': 'text',
                                                                    'style': 'padding: 0 4px; height: auto; min-height: 0; line-height: 20px; white-space: normal; word-break: break-all; background-color: transparent; border: none; border-radius: 0;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': 'keyword'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': ': 关键词，用于匹配消息标题或内容'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '• '
                                                            },
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'size': 'default',
                                                                    'class': 'mx-1',
                                                                    'variant': 'text',
                                                                    'style': 'padding: 0 4px; height: auto; min-height: 0; line-height: 20px; white-space: normal; word-break: break-all; background-color: transparent; border: none; border-radius: 0;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': 'image_url/image_url1/image_url2'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': ': 图片URL，支持配置多个URL随机选择'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '• '
                                                            },
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'size': 'default',
                                                                    'class': 'mx-1',
                                                                    'variant': 'text',
                                                                    'style': 'padding: 0 4px; height: auto; min-height: 0; line-height: 20px; white-space: normal; word-break: break-all; background-color: transparent; border: none;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': 'style'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': ': 通知样式，可选值：'
                                                            },
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'size': 'default',
                                                                    'class': 'mx-1',
                                                                    'variant': 'text',
                                                                    'style': 'padding: 0 4px; height: auto; min-height: 0; line-height: 20px; white-space: normal; word-break: break-all; background-color: transparent; border: none;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': 'default'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': '(默认样式)、'
                                                            },
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'size': 'default',
                                                                    'class': 'mx-1',
                                                                    'variant': 'text',
                                                                    'style': 'padding: 0 4px; height: auto; min-height: 0; line-height: 20px; white-space: normal; word-break: break-all; background-color: transparent; border: none;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': 'card'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': '(卡片样式)'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 mt-2 ml-8'
                                                        },
                                                        'text': '注意事项：'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '• 关键词匹配不区分大小写'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '• 图片URL为空时将使用默认封面(封面尺寸建议1068*455)'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '• 系统会自动避免连续使用相同的图片'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 mt-2 ml-8'
                                                        },
                                                        'text': '示例：当消息包含"群辉"关键词时，将随机使用配置的群辉图片作为通知封面，并使用卡片样式显示。'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {
                                                    'lines': 'two'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-items-start'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'info',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-information'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-regular mb-1'
                                                                },
                                                                'text': '使用示列'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '必要参数或请求体可用变量请根据你使用的第三方应用要求填写！不会使用请点击查看使用示列：'
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
                                                    'lines': 'two'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-items-start'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-heart'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-regular mb-1'
                                                                },
                                                                'text': '致谢'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
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
            "msgtype": "Manual",
            "image_mappings": ""
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        pass
