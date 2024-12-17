from typing import Any, List, Dict, Tuple, Optional
from pathlib import Path

from app.log import logger
from app.chain.dashboard import DashboardChain
from app.core.config import settings
from app.db.subscribe_oper import SubscribeOper
from app.helper.directory import DirectoryHelper
from app.plugins import _PluginBase
from app.core.event import eventmanager, Event
from app.schemas.types import EventType, NotificationType
from app import schemas
from app.utils.system import SystemUtils
from app.utils.http import RequestUtils


class ExternalMessage(_PluginBase):
    # 插件名称
    plugin_name = "External Message"
    # 插件描述
    plugin_desc = "外部应用消息推送。"
    # 插件图标
    plugin_icon = "forward.png"
    # 插件版本
    plugin_version = "0.1"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming/MoviePilot-Plugins"
    # 插件配置项ID前缀
    plugin_config_prefix = "externalmessage_"
    # 加载顺序
    plugin_order = 30
    # 可使用的用户级别
    auth_level = 1

    # 任务执行间隔
    _enabled = False

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")

    def get_state(self) -> bool:
        return self._enabled

    def send_json(self, apikey: str) -> Any:
        """
        外部应用自定义消息接口使用的API
        """
        try:
            if apikey != settings.API_TOKEN:
                return schemas.Response(success=False, message="API密钥错误")
            
            # 解析请求体中的JSON数据
            data = RequestUtils.get_json_request()
            if not data:
                logger.warn("请求体为空或格式不正确")
                return schemas.Response(success=False, message="请求体为空或格式不正确")
            
            # 提取title和text字段
            title = data.get('title')
            content = data.get('content')

            if not title or not content:
                logger.warn("缺少必要的字段title或content")
                return schemas.Response(success=False, message="缺少必要的字段title或content")
            
            # 记录title和text到日志
            logger.info(f"Received title: {title}, text: {content}")

            # 调用post_message方法发送消息
            self.post_message(
                mtype=NotificationType.Plugin,
                title=f"{title}\n",
                text=f"{title}\n内容: {content}"
            )

            return schemas.Response(success=True, message="消息接收成功", data={"title": title, "content": content})

        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}")
            return schemas.Response(success=False, message=f"处理消息时发生错误: {e}")
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
            "endpoint": self.send_json,
            "methods": ["POST"],
            "summary": "外部应用自定义消息接口使用的API",
            "description": "接收外部应用的json自定义消息接口",
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
                                                'text': 'API接口地址参考：http://MoviePilot_IP:PORT/api/v1/plugin/ExternalMessage/send_json?apikey=api_token'
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
                                            'text': '如安装完启用插件后回调地址无响应，重启MoviePilot即可。'
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
        }

    def get_page(self) -> List[dict]:
        """
        拼装插件详情页面，需要返回页面配置，同时附带数据
        
        pass
        
    @eventmanager.register(EventType.NoticeMessage)
    def send(self, event: Event):
        """
        消息发送事件
        """
        if not self.get_state():
            return

        if not event.event_data:
            return

        msg_body = event.event_data
        # 渠道
        channel = msg_body.get("channel")
        if channel:
            return
        # 类型
        msg_type: NotificationType = msg_body.get("type")
        # 标题
        title = msg_body.get("title")
        # 文本
        text = msg_body.get("text")

        if not title and not text:
            logger.warn("标题和内容不能同时为空")
            return

        if (msg_type and self._msgtypes
                and msg_type.name not in self._msgtypes):
            logger.info(f"消息类型 {msg_type.value} 未开启消息发送")
            return

        try:
            if not self._server or not self._port or not self._topic:
                return False, "参数未配置"
            mqtt_client = MqttClient(server=self._server, port=self._port, topic=self._topic, user=self._user, password=self._password)
            mqtt_client.send(title=title, message=text, format_as_markdown=True)

        except Exception as msg_e:
            logger.error(f"MQTT消息发送失败，错误信息：{str(msg_e)}")
"""

    def stop_service(self):
        """
        退出插件
        """
        pass