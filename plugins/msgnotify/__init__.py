# 标准库导入
import random
from typing import Any, Dict, List, Tuple

# 第三方库导入
from pydantic import BaseModel

# 本地模块导入
from app import schemas
from app.core.config import settings
from app.helper.notification import NotificationHelper
from app.helper.message import MessageHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import MessageChannel, Notification, NotificationType
from app.utils.http import RequestUtils

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
    plugin_version = "1.3.7"
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
        self.notification_helper = NotificationHelper()  # 初始化通知帮助类
        self.messagehelper = MessageHelper()  # 初始化消息帮助类

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._msgtype = config.get("msgtype")
            try:
                # 解析文本配置，支持多图片URL和样式，样式以第一行为准
                image_mapping_dict = {}
                config_text = config.get("image_mappings", "").strip()
                if config_text:
                    for line in config_text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) < 2:
                            continue
                        keyword = parts[0]
                        # 判断最后一段是否为样式
                        style_candidate = parts[-1].lower()
                        if style_candidate in ("card", "default"):
                            style = style_candidate
                            url_parts = parts[1:-1]
                        else:
                            style = "default"
                            url_parts = parts[1:]
                        # 处理图片URL，去掉/前缀
                        image_urls = []
                        for url in url_parts:
                            url = url.lstrip('/')
                            if url and url.lower().startswith('http'):
                                image_urls.append(url)
                        # 合并
                        if keyword not in image_mapping_dict:
                            image_mapping_dict[keyword] = {
                                "keyword": keyword,
                                "style": style,
                                "image_urls": image_urls
                            }
                        else:
                            # 样式以第一行为准，只追加图片
                            if image_urls:
                                image_mapping_dict[keyword]["image_urls"].extend(image_urls)
                # 转为列表，每个mapping的image_url*字段
                image_mappings = []
                for mapping in image_mapping_dict.values():
                    mapping_obj = {
                        "keyword": mapping["keyword"],
                        "style": mapping["style"]
                    }
                    for i, url in enumerate(mapping["image_urls"], 1):
                        mapping_obj[f"image_url{i}"] = url
                    image_mappings.append(mapping_obj)
                self._image_mappings = image_mappings
                logger.info(f"加载图片映射配置: {self._image_mappings}")
            except Exception as e:
                logger.error(f"解析图片映射配置失败: {str(e)}")
                self._image_mappings = []

    def _get_matched_image(self, title: str, text: str) -> Tuple[str, str]:
        """
        根据消息标题和内容匹配对应的图片URL和通知样式
        返回: (图片URL, 通知样式)
        """
        if not self._image_mappings:
            return None, "default"
            
        for mapping in self._image_mappings:
            keyword = mapping.get("keyword", "")
            if not keyword:
                continue
                
            # 检查标题和内容是否包含关键词
            if keyword.lower() in title.lower() or keyword.lower() in text.lower():
                # 获取通知样式,默认为default
                style = mapping.get("style", "default")
                logger.info(f"匹配到关键词 '{keyword}', 使用样式: {style}")
                
                if style not in ["default", "card"]:
                    logger.warning(f"无效的通知样式 '{style}', 使用默认样式")
                    style = "default"
                
                # 收集所有image_url开头的字段
                image_urls = []
                for key, value in mapping.items():
                    if key.startswith("image_url") and value and value.strip():
                        image_urls.append(value)
                
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
                    return None, style
        return None, "default"

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

            notification = Notification(
                mtype=mtype,
                title=title,
                text=text if style != "card" else f"{text}\n",
                image=image_url if style == "card" else None,
                channel=MessageChannel.Wechat
            )
            self.post_message(notification)

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

            notification = Notification(
                mtype=mtype,
                title=title,
                text=text if style != "card" else f"{text}\n",
                image=image_url if style == "card" else None,
                channel=MessageChannel.Wechat
            )
            self.post_message(notification)

        return schemas.Response(
            success=True,
            message="发送成功"
        )

    def get_state(self) -> bool:
        return self._enabled

    def get_module(self) -> Dict[str, Any]:
        """
        获取插件模块声明，用于胁持系统模块实现
        """
        return {
            "post_message": self.post_message
        }

    def post_message(self, message: Notification):
        """
        插件重载post_message，支持企业微信card推送
        """
        try:
            channel = getattr(message, "channel", None)
            mtype = getattr(message, "mtype", NotificationType.Manual)  # 获取消息类型
            # 统一用_get_matched_image获取图片和样式
            picurl, style = self._get_matched_image(getattr(message, 'title', ''), getattr(message, 'text', ''))
            
            # 检查是否为微信通知渠道
            if channel == MessageChannel.Wechat:
                # 获取所有通知服务名称
                service_names = self.notification_helper.get_services()
                # 查找企业微信通知服务
                wechat_service = None
                for service_name in service_names:
                    service = self.notification_helper.get_service(name=service_name)
                    if service and service.config.enabled:
                        wechat_service = service
                        break
                
                if wechat_service:
                    if style == "card":
                        try:
                            self._send_wecom_card(message.title, message.text, picurl=picurl)
                        except Exception as e:
                            import traceback
                            logger.error(f"发送企业微信卡片消息失败: {str(e)}\n{traceback.format_exc()}")
                        return
            try:
                # 使用自己的消息处理逻辑
                if hasattr(self, 'messagehelper'):
                    self.messagehelper.put(message, role="user", title=message.title, mtype=mtype)  # 传入消息类型
                
                # 使用wechat_service发送消息
                if channel == MessageChannel.Wechat:
                    # 获取所有通知服务名称
                    service_names = self.notification_helper.get_services()
                    # 查找企业微信通知服务
                    wechat_service = None
                    for service_name in service_names:
                        service = self.notification_helper.get_service(name=service_name)
                        if service and service.config.enabled:
                            wechat_service = service
                            break
                            
                    if wechat_service:
                        wechat_instance = wechat_service.instance
                        if wechat_instance:
                            # 构建消息内容,添加消息类型标识
                            msg_content = f"[{mtype.value}]\n{message.title}\n{message.text}"
                            if message.image:
                                msg_content = f"{msg_content}\n[图片]"
                            # 发送消息
                            wechat_instance.send_msg(msg_content)
            except Exception as e:
                import traceback
                logger.error(f"消息处理异常: {str(e)}\n{traceback.format_exc()}")
                raise
        except Exception as e:
            import traceback
            logger.error(f"消息发送异常: {str(e)}\n{traceback.format_exc()}")
            raise

    def _send_wecom_card(self, title: str, text: str, picurl: str = None, link: str = "") -> bool:
        """
        发送企业微信卡片消息
        """
        try:
            # 获取所有通知服务名称
            service_names = self.notification_helper.get_services()
            # 查找企业微信通知服务
            wechat_service = None
            for service_name in service_names:
                service = self.notification_helper.get_service(name=service_name)
                if service and service.config.enabled:
                    wechat_service = service
                    break
                    
            if not wechat_service:
                logger.error("未找到企业微信通知服务")
                return False
                
            # 获取服务实例
            wechat_instance = wechat_service.instance
            if not wechat_instance:
                logger.error("未找到企业微信服务实例")
                return False
                
            # 获取access_token
            if not wechat_instance._WeChat__get_access_token():
                logger.error("获取微信access_token失败，请检查参数配置")
                return False
                
            # 构建卡片消息（news类型，支持图片）
            article = {
                "title": title,
                "description": text
            }
            if picurl:
                article["picurl"] = picurl
            req_json = {
                "touser": "@all",
                "msgtype": "news",
                "agentid": wechat_instance._appid,
                "news": {
                    "articles": [article]
                },
                "safe": 0,
                "enable_id_trans": 0,
                "enable_duplicate_check": 0
            }
            
            # 拼接代理地址
            base_url = "https://qyapi.weixin.qq.com"
            if wechat_instance._proxy:
                base_url = wechat_instance._proxy
            message_url = f"{base_url}/cgi-bin/message/send?access_token={wechat_instance._access_token}"
            
            # 使用RequestUtils发送请求
            res = RequestUtils().post(message_url, json=req_json)
            if res is None:
                logger.error("发送请求失败，未获取到返回信息")
                return False
            if res.status_code != 200:
                logger.error(f"发送请求失败，错误码：{res.status_code}，错误原因：{res.reason}")
                return False
            ret_json = res.json()
            if ret_json.get("errcode") == 0:
                return True
            else:
                logger.error(f"企业微信消息发送失败: {ret_json.get('errmsg')}")
                return False
        except Exception as e:
            import traceback
            logger.error(f"企业微信文本卡片消息发送异常: {str(e)}\n{traceback.format_exc()}")
            return False

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
                                                            'cols': 12,
                                                            'style': 'margin-bottom: 0px; padding-bottom: 0px;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VTextarea',
                                                                'props': {
                                                                    'model': 'image_mappings',
                                                                    'label': '自定义设置',
                                                                    'height': 400,
                                                                    'auto-grow': False,
                                                                    'hide-details': False,
                                                                    'placeholder': '群辉|https://example.com/1.jpg|/https://example.com/2.jpg|card\n群辉|https://example.com/3.jpg\nLucky|card'
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
                                                                    'style': 'vertical-align: baseline; font-size: inherit; padding: 0 2px; height: 20px; line-height: 20px; background-color: transparent; border: none; border-radius: 0;'
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
                                                                    'style': 'vertical-align: baseline; font-size: inherit; padding: 0 2px; height: 20px; line-height: 20px; background-color: transparent; border: none; border-radius: 0;'
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
                                                                    'style': 'vertical-align: baseline; font-size: inherit; padding: 0 2px; height: 20px; line-height: 20px; background-color: transparent; border: none; border-radius: 0;'
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
                                                                'text': '配置格式为每行一个，支持多图片和多行合并：'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8',
                                                            'style': 'display: flex; align-items: flex-start;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'style': 'width: 65px; text-align: left;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VChip',
                                                                        'props': {
                                                                            'color': 'error',
                                                                            'size': 'default',
                                                                            'class': 'mx-0',
                                                                            'variant': 'text',
                                                                            'style': 'vertical-align: baseline; font-size: inherit; padding: 0 0px; height: 20px; line-height: 20px; background-color: transparent; border: none; border-radius: 0;'
                                                                        },
                                                                        'content': [
                                                                            {
                                                                                'component': 'span',
                                                                                'text': '• 关键词：'
                                                                            }
                                                                        ]
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {},
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '用于匹配消息标题或内容（必填）'
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8',
                                                            'style': 'display: flex; align-items: flex-start;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'style': 'width: 80px; text-align: left;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VChip',
                                                                        'props': {
                                                                            'color': 'error',
                                                                            'size': 'default',
                                                                            'class': 'mx-0',
                                                                            'variant': 'text',
                                                                            'style': 'vertical-align: baseline; font-size: inherit; padding: 0 0px; height: 20px; line-height: 20px; background-color: transparent; border: none; border-radius: 0;'
                                                                        },
                                                                        'content': [
                                                                            {
                                                                                'component': 'span',
                                                                                'text': '• 图片URL：'
                                                                            }
                                                                        ]
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {},
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '支持多个使用|分隔，支持http/https（可选）'
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8',
                                                            'style': 'display: flex; align-items: flex-start;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'style': 'width: 80px; text-align: left;'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VChip',
                                                                        'props': {
                                                                            'color': 'error',
                                                                            'size': 'default',
                                                                            'class': 'mx-0',
                                                                            'variant': 'text',
                                                                            'style': 'vertical-align: baseline; font-size: inherit; padding: 0 0px; height: 20px; line-height: 20px; background-color: transparent; border: none; border-radius: 0;'
                                                                        },
                                                                        'content': [
                                                                            {
                                                                                'component': 'span',
                                                                                'text': '• 通知样式：'
                                                                            }
                                                                        ]
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {},
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'text': 'card（卡片样式）、default（默认样式），样式必须放在最后（可选）'
                                                                    }
                                                                ]
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
                                                                'text': '• 同一关键词配置多行时，所有图片会合并，样式以第一行配置为准'
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
                                                                'text': '• 没有图片URL时只推送文字卡片'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 mt-2 ml-8'
                                                        },
                                                        'text': '示例：'
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'text-body-2 ml-8'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '群辉|https://example.com/1.jpg|/https://example.com/2.jpg|card'
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
                                                                'text': '群辉|https://example.com/3.jpg'
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
                                                                'text': 'Lucky|card'
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
