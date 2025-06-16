import time
import jwt
import websockets
import json
import asyncio
import uuid
from typing import Any, List, Dict, Tuple
from app.plugins import _PluginBase
from app.log import logger
from app.core.config import settings
from fastapi import Query


class NATdetect(_PluginBase):
    # 插件名称
    plugin_name = "NAT类型检测"
    # 插件描述
    plugin_desc = "使用Lucky服务检测NAT类型"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/natdetect.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "natdetect_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _host = None
    _openToken = None
    _logs = {}  # 全局日志缓存: {task_id: [log1, log2, ...]}
    _tasks = {} # 任务状态: {task_id: bool} True表示任务完成
    _servers = [
        "stun.miwifi.com:3478",
        "stun.avigora.fr:3478",
        "stun.imp.ch:3478",
        "stun.root-1.de:3478",
        "stun.axialys.net:3478",
        "stun.sonetel.net:3478",
        "stun.skydrone.aero:3478",
        "stun.dcalling.de:3478",
        "stun.telnyx.com:3478",
        "stun.siptrunk.com:3478",
        "stun.romaaeterna.nl:3478",
        "stun.voipia.net:3478",
        "stun.nextcloud.com:443",
        "stun.m-online.net:3478",
        "stun.ringostat.com:3478",
        "stun.fitauto.ru:3478",
        "stun.cope.es:3478",
        "stun.nanocosmos.de:3478",
        "stun.streamnow.ch:3478",
        "stun.hot-chilli.net:3478",
        "stun.pure-ip.com:3478",
        "stun.radiojar.com:3478",
        "stun.sip.us:3478"
    ]

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._host = config.get("host")
            self._openToken = config.get("openToken")

    def get_jwt(self) -> str:
        payload = {
            "exp": int(time.time()) + 28 * 24 * 60 * 60,
            "iat": int(time.time())
        }
        encoded_jwt = jwt.encode(payload, self._openToken, algorithm="HS256")
        logger.debug(f"LuckyHelper get jwt---》{encoded_jwt}")
        return "Bearer "+encoded_jwt

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [{
            "path": "/natdetect/start",
            "endpoint": self.nat_detect_start,
            "methods": ["GET"],
            "summary": "启动NAT检测任务",
            "description": "启动检测任务，返回task_id"
        }, {
            "path": "/natdetect/logs",
            "endpoint": self.nat_detect_logs,
            "methods": ["GET"],
            "summary": "获取NAT检测任务日志",
            "description": "轮询获取检测日志"
        }]

    def get_service(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """拼装插件配置页面"""
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
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    # 服务设置
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
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-3',
                                                    'size': 'default'
                                                },
                                                'text': 'mdi-server'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '服务设置'
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
                                                    'md': 6
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'host',
                                                            'label': 'Lucky地址',
                                                            'hint': 'Lucky服务反代域名(可加端口域名前面无需添加https://)',
                                                            'persistent-hint': True,
                                                            'color': 'primary',
                                                            'variant': 'outlined',
                                                            'density': 'comfortable',
                                                            'prepend-inner-icon': 'mdi-web'
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
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'openToken',
                                                            'label': 'OpenToken',
                                                            'hint': 'Lucky openToken 设置里面打开(复制过来)',
                                                            'persistent-hint': True,
                                                            'color': 'primary',
                                                            'variant': 'outlined',
                                                            'density': 'comfortable',
                                                            'prepend-inner-icon': 'mdi-key',
                                                            'type': 'password'
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
                                                    'style': 'color: #16b1ff;',
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
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '本工具通过Lucky服务检测NAT类型。\n注意：由于wss通信要求，Lucky地址必须为https安全连接，否则检测无法正常进行。',
                                            'border': 'start',
                                            'border-color': 'primary',
                                            'icon': 'mdi-information',
                                            'elevation': 1,
                                            'rounded': 'lg'
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
            "host": "",
            "openToken": "",
            "server": "stun.miwifi.com:3478"
        }

    def get_page(self) -> List[dict]:
        """拼装插件详情页面"""
        server_options = [{"label": s, "value": s} for s in self._servers]
        js_safe_api_token = json.dumps(settings.API_TOKEN)
        js_onclick = f"""
        (async (button) => {{
            const select = document.querySelector('#natdetect-server-select');
            if (!select || !select.value) {{
                const logBox = document.getElementById('natdetect-log-box');
                if (logBox) {{
                    logBox.innerHTML = '<span style=\"color:#d32f2f\">请选择服务器</span>';
                    logBox.style.display = 'block';
                }}
                return;
            }}
            button.disabled = true;
            const originalText = button.textContent;
            button.textContent = '检测中...';

            // 清空日志框
            const logBox = document.getElementById('natdetect-log-box');
            if (logBox) {{
                logBox.innerHTML = '';
                logBox.style.display = 'block';
            }}
            if (window.natdetectTimer) {{
                clearInterval(window.natdetectTimer);
                window.natdetectTimer = null;
            }}
            window.natdetectLastLogIndex = 0;

            try {{
                const apiKey = {js_safe_api_token};
                // 1. 启动检测任务
                const startUrl = `/api/v1/plugin/NATdetect/natdetect/start?server=${{encodeURIComponent(select.value)}}&apikey=${{encodeURIComponent(apiKey)}}`;
                const startResp = await fetch(startUrl, {{
                    method: 'GET',
                    headers: {{ 'Content-Type': 'application/json' }}
                }});
                const startData = await startResp.json();
                if (!startData.task_id) {{
                    if (logBox) {{
                        logBox.innerHTML = startData.message || '启动检测任务失败';
                        logBox.style.display = 'block';
                    }}
                    button.disabled = false;
                    button.textContent = originalText;
                    return;
                }}
                const taskId = startData.task_id;
                window.natdetectLastLogIndex = 0;
                if (logBox) logBox.style.display = 'block';

                // 2. 定时轮询日志
                window.natdetectTimer = setInterval(async () => {{
                    try {{
                        const logUrl = `/api/v1/plugin/NATdetect/natdetect/logs?task_id=${{encodeURIComponent(taskId)}}&from_idx=${{window.natdetectLastLogIndex}}&apikey=${{encodeURIComponent(apiKey)}}`;
                        const logResp = await fetch(logUrl, {{
                            method: 'GET',
                            headers: {{ 'Content-Type': 'application/json' }}
                        }});
                        const logData = await logResp.json();
                        if (logData.logs && logData.logs.length) {{
                            if (logBox) {{
                                logBox.innerHTML += logData.logs.map(log => log + '<br>').join('');
                                logBox.style.display = 'block';
                                setTimeout(() => {{ logBox.scrollTop = logBox.scrollHeight; }}, 0);
                            }}
                            window.natdetectLastLogIndex += logData.logs.length;
                        }}
                        if (logData.status === 'done' || logData.status === 'error') {{
                            clearInterval(window.natdetectTimer);
                            window.natdetectTimer = null;
                            button.disabled = false;
                            button.textContent = originalText;
                            if (logBox) {{
                                logBox.innerHTML += '<br><br>检测' + (logData.status === 'done' ? '完成' : '失败');
                                setTimeout(() => {{ logBox.scrollTop = logBox.scrollHeight; }}, 0);
                            }}
                        }}
                    }} catch (e) {{
                        if (logBox) {{
                            logBox.innerHTML += '<br>[日志拉取失败] ' + (e.message || e);
                        }}
                        clearInterval(window.natdetectTimer);
                        window.natdetectTimer = null;
                        button.disabled = false;
                        button.textContent = originalText;
                    }}
                }}, 500);
            }} catch (error) {{
                if (logBox) {{
                    logBox.innerHTML = '[检测任务启动失败] ' + error;
                    logBox.style.display = 'block';
                }}
                button.disabled = false;
                button.textContent = originalText;
            }}
        }})(this)
        """
        page = [
            {
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12},
                        'content': [
                            {
                                'component': 'VCard',
                                'props': {
                                    'elevation': 2,
                                    'rounded': 'lg',
                                    'border': True,
                                    'style': 'background: linear-gradient(to bottom right, #ffffff, #f8f9fa);'
                                },
                                'content': [
                                    {
                                        'component': 'VCardItem',
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {'class': 'd-flex flex-column align-center justify-center py-4'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-center mb-2'},
                                                        'content': [
                                                            {'component': 'VIcon', 'props': {'color': 'info', 'size': '48', 'class': 'mr-2'}, 'text': 'mdi-lan-connect'},
                                                            {'component': 'span', 'props': {'class': 'text-h4 font-weight-bold'}, 'text': 'NAT类型检测'}
                                                        ]
                                                    },
                                                    {'component': 'span', 'props': {'class': 'text-body-1 text-grey-darken-1'}, 'text': '检测当前网络的NAT类型，辅助排查内网穿透/端口映射问题'}
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VCol',
                                        'props': {'cols': 12, 'md': 8, 'class': 'mx-auto'},
                                        'content': [
                                            {
                                                # 信息提示
                                                'component': 'VAlert',
                                                'props': {
                                                    'type': 'info',
                                                    'variant': 'tonal',
                                                    'text': '依赖Lucky服务确保Lucky在需要检测的环境中正常运行(没什么用的工具，你可以直接使用Lucky检测😂)。',
                                                    'class': 'mb-6',
                                                    'density': 'comfortable',
                                                    'border': 'start',
                                                    'border-color': 'primary',
                                                    'icon': 'mdi-information',
                                                    'elevation': 1,
                                                    'rounded': 'lg'
                                                }
                                            },
                                            {
                                                'component': 'VSheet',
                                                'props': {
                                                    'elevation': 0,
                                                    'rounded': 'lg',
                                                    'class': 'pa-6 mb-4',
                                                    'style': 'background: #f8f9fa; border: 1px solid #e0e0e0;'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'label': '选择服务器',
                                                            'items': server_options,
                                                            'item-title': 'label',
                                                            'item-value': 'value',
                                                            'id': 'natdetect-server-select',
                                                            'variant': 'outlined',
                                                            'density': 'comfortable',
                                                            'clearable': False,
                                                            'persistent-hint': True,
                                                            'hint': '请选择NAT检测服务器',
                                                            'model': 'server',
                                                            'class': 'mb-4',
                                                            'bg-color': 'white',
                                                            'prepend-inner-icon': 'mdi-server'
                                                        }
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'id': 'natdetect-log-box',
                                                            'style': 'height: 300px; max-height: 400px; overflow-y: auto; font-family: "JetBrains Mono", monospace; color: #43a047; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; font-size: 0.9rem; line-height: 1.5;'
                                                        }
                                                    },
                                                    {
                                                        'component': 'VBtn',
                                                        'props': {
                                                            'color': 'primary',
                                                            'block': True,
                                                            'size': 'large',
                                                            'onclick': js_onclick,
                                                            'id': 'natdetect-detect-btn',
                                                            'elevation': 2,
                                                            'rounded': 'lg',
                                                            'class': 'text-none font-weight-bold mt-4',
                                                            'prepend-icon': 'mdi-radar'
                                                        },
                                                        'text': '开始检测NAT类型'
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
        return page

    async def nat_detect_start(self, server: str = Query(...), apikey: str = Query(...)):
        """
        启动NAT检测任务，返回task_id
        """
        if apikey != settings.API_TOKEN:
            return {"code": 401, "message": "API令牌错误!"}
        if not self._host or not self._openToken or not server:
            return {"code": 400, "message": "配置不完整"}
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = False
        self._logs[task_id] = []
        # 启动异步检测任务
        asyncio.create_task(self._run_natdetect_task(task_id, server))
        return {"code": 200, "task_id": task_id}

    async def _run_natdetect_task(self, task_id, server):
        try:
            ws_url = f"wss://{self._host}/api/natdetect/ws?openToken={self._openToken}&server={server}"
            async with websockets.connect(ws_url) as websocket:
                while True:
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=10)
                        try:
                            msg_obj = json.loads(msg)
                            if isinstance(msg_obj, dict) and "result" in msg_obj:
                                self._logs[task_id].append(str(msg_obj["result"]))
                            elif isinstance(msg_obj, dict) and "log" in msg_obj:
                                self._logs[task_id].append(str(msg_obj["log"]))
                            else:
                                self._logs[task_id].append(str(msg))
                        except Exception:
                            self._logs[task_id].append(str(msg))
                    except asyncio.TimeoutError:
                        break
                    except websockets.ConnectionClosed:
                        break
            self._tasks[task_id] = True
        except Exception as e:
            logger.error(f"NAT类型检测任务失败: {e}")
            self._logs[task_id].append(f"NAT类型检测失败: {e}")
            self._tasks[task_id] = True
        finally:
            # 任务结束后延迟清理
            asyncio.create_task(self._cleanup_task(task_id))

    async def _cleanup_task(self, task_id: str, delay: int = 300):
        """延迟清理任务数据"""
        await asyncio.sleep(delay)
        if task_id in self._logs:
            del self._logs[task_id]
        if task_id in self._tasks:
            del self._tasks[task_id]

    async def nat_detect_logs(self, task_id: str = Query(...), from_idx: int = Query(0), apikey: str = Query(...)):
        """
        拉取检测任务日志
        """
        if apikey != settings.API_TOKEN:
            return {"code": 401, "message": "API令牌错误!"}
        logs = self._logs.get(task_id, [])[from_idx:]
        status = 'done' if self._tasks.get(task_id, False) else 'running'
        return {"code": 200, "logs": logs, "status": status, "total": len(logs)}
    
    def stop_service(self):
        """停止插件服务"""
        self._enabled = False
        logger.info("插件已停止")