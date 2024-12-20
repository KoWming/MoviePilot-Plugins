import requests, json
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
    plugin_desc = "test外部应用消息推送。"
    # 插件图标
    plugin_icon = "forward.png"
    # 插件版本
    plugin_version = "0.3"
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

    def send_json(self, apikey: str, data="") -> schemas.Response:
        """
        解析接收到的POST请求中的JSON数据，然后调用post_message方法发送消息。
        """
        if apikey != settings.API_TOKEN:
            return schemas.Response(success=False, message="API密钥错误")
            
        # 将接收到的数据转换为字符串,并解析JSON数据
        # data_str = data.decode('utf-8')
        json_data = json.loads(data)
        if not json_data:
            logger.warn("请求体为空或格式不正确")
            return schemas.Response(success=False, message="请求体为空或格式不正确")
            
        # 提取title和text字段
        title = json_data.get('title')
        content = json_data.get('content')
        if not title or not content:
            logger.warn("缺少必要的字段title或content")
            return schemas.Response(success=False, message="缺少必要的字段title或content")
            
        # 记录title和text到日志
        logger.info(f"Received title: {title}, text: {content}")

        # 调用post_message方法发送消息
        self.post_message(
            mtype=NotificationType.Plugin,
            title=title,
            content=content
            )
        return schemas.Response(success=True, message="消息接收成功", data={"title": title, "content": content})
        
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
        """
        pass
    
    def stop_service(self):
        """
        退出插件
        """
        pass
