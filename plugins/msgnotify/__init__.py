from app.plugins import _PluginBase
from typing import Any, List, Dict, Tuple
from app.log import logger
from app.schemas import NotificationType
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
    plugin_icon = "MsgNotify.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming/MoviePilot-Plugins"
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

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._msgtype = config.get("msgtype")

    def msg_notify(self, request: NotifyRequest) -> schemas.Response:
        """
        发送通知
        """
        title = request.title
        text = request.text
        logger.info(f"收到以下消息:\n{title}\n{text}")
        if self._enabled and self._notify:
            mtype = NotificationType.Manual
            if self._msgtype:
                mtype = NotificationType.__getitem__(str(self._msgtype)) or NotificationType.Manual
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
            "endpoint": self.msg_notify,
            "methods": ["POST"],
            "summary": "外部应用自定义消息接口使用的API",
            "description": "接受自定义消息webhook通知并推送",
        }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        # 编历 NotificationType 枚举，生成消息类型选项
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
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'notify',
                                            'label': '开启通知',
                                        }
                                    }
                                ]
                            },
                        ]
                    },
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
                                            'multiple': False,
                                            'chips': True,
                                            'model': 'msgtype',
                                            'label': '消息类型',
                                            'items': MsgTypeOptions
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
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'success',
                                            'variant': 'tonal'
                                        },
                                        'content': [
                                            {
                                                'component': 'span',
                                                'text': 'API接口地址参考：http://MoviePilot_IP:PORT/api/v1/plugin/MsgNotify/send_json?apikey=api_token'
                                            },
                                        ]
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
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '其中MoviePilot_IP为MoviePilot的IP地址，PORT为MoviePilot的端口号，api_token为MoviePilot的API Token。\n发送POST请求，请求体为JSON格式，包含title和text两个字段，分别为消息的标题和内容。\n示例请求体：\n {"title": "测试消息", "text": "这是一条测试消息"}\n此插件安装完需要重启生效api。消息类型默认为手动处理通知。\n如安装完插件后，消息发送失败，重启MoviePilot即可。\n此项目魔改了@thsrite大佬的"群辉Webhook通知"插件而来，感谢大佬的无私分享。'
                                        }
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
            "msgtype": ""
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        pass
