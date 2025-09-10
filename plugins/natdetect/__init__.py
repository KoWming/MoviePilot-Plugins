import time
import asyncio
import uuid
import socket
import struct
import random
import json
from typing import Any, List, Dict, Tuple, Optional
from app.plugins import _PluginBase
from app.log import logger
from app.core.config import settings
from fastapi import Query


class STUNClient:
    """
    STUN协议客户端实现 (参考RFC 3489和Lucky工具实现)
    """
    # STUN消息类型
    STUN_BINDING_REQUEST = 0x0001
    STUN_BINDING_RESPONSE = 0x0101
    STUN_BINDING_ERROR_RESPONSE = 0x0111
    
    # STUN属性类型
    MAPPED_ADDRESS = 0x0001
    USERNAME = 0x0006
    MESSAGE_INTEGRITY = 0x0008
    ERROR_CODE = 0x0009
    UNKNOWN_ATTRIBUTES = 0x000A
    REALM = 0x0014
    NONCE = 0x0015
    XOR_MAPPED_ADDRESS = 0x0020
    SOFTWARE = 0x8022
    ALTERNATE_SERVER = 0x8023
    FINGERPRINT = 0x8028
    CHANGE_REQUEST = 0x0003
    CHANGED_ADDRESS = 0x0005
    
    # 地址族
    IPV4 = 0x01
    IPV6 = 0x02
    
    # 魔数
    MAGIC_COOKIE = 0x2112A442

    def __init__(self):
        self.transaction_id = None

    def create_binding_request(self, change_ip: bool = False, change_port: bool = False) -> bytes:
        """
        创建STUN绑定请求消息
        """
        # 生成随机事务ID (96位)
        self.transaction_id = random.getrandbits(96).to_bytes(12, 'big')
        
        # 构造CHANGE-REQUEST属性
        change_request_attr = b''
        if change_ip or change_port:
            change_flag = (0x04 if change_ip else 0x00) | (0x02 if change_port else 0x00)
            change_request_attr = struct.pack('>HHI', self.CHANGE_REQUEST, 4, change_flag)
        
        # STUN消息头 (20字节)
        message_length = len(change_request_attr)
        message_type = self.STUN_BINDING_REQUEST
        magic_cookie = self.MAGIC_COOKIE
        
        # 组合消息: 消息类型(2) + 消息长度(2) + 魔术字(4) + 事务ID(12) + 属性
        message = struct.pack('>HHI', message_type, message_length, magic_cookie) + self.transaction_id + change_request_attr
        return message

    def parse_stun_response(self, data: bytes) -> Optional[Dict]:
        """
        解析STUN响应消息
        """
        if len(data) < 20:
            return None
            
        # 解析消息头
        try:
            msg_type, msg_length, magic_cookie = struct.unpack('>HHI', data[:8])
            transaction_id = data[8:20]
        except struct.error:
            return None
        
        # 验证魔术字和事务ID
        if magic_cookie != self.MAGIC_COOKIE:
            return None
            
        if msg_type != self.STUN_BINDING_RESPONSE:
            return None
            
        # 验证消息长度
        if len(data) < 20 + msg_length:
            logger.warning(f"STUN响应数据长度不足，期望: {20 + msg_length}, 实际: {len(data)}")
            return None
            
        # 解析属性
        attributes = {}
        offset = 20
        while offset < len(data):
            if offset + 4 > len(data):
                break
                
            try:
                attr_type, attr_length = struct.unpack('>HH', data[offset:offset+4])
            except struct.error:
                break
                
            offset += 4
            
            if offset + attr_length > len(data):
                break
                
            attr_value = data[offset:offset+attr_length]
            offset += attr_length
            
            # 对齐到4字节边界
            offset = (offset + 3) & ~3
            
            if attr_type == self.MAPPED_ADDRESS:
                parsed = self._parse_address(attr_value)
                if parsed:
                    attributes['mapped_address'] = parsed
            elif attr_type == self.XOR_MAPPED_ADDRESS:
                parsed = self._parse_xor_address(attr_value, magic_cookie, transaction_id)
                if parsed:
                    attributes['xor_mapped_address'] = parsed
            elif attr_type == self.CHANGED_ADDRESS:
                parsed = self._parse_address(attr_value)
                if parsed:
                    attributes['changed_address'] = parsed
            elif attr_type == self.ERROR_CODE:
                parsed = self._parse_error_code(attr_value)
                if parsed:
                    attributes['error_code'] = parsed
            elif attr_type == self.SOFTWARE:
                try:
                    attributes['software'] = attr_value.decode('utf-8')
                except:
                    pass
            elif attr_type == self.ALTERNATE_SERVER:
                parsed = self._parse_address(attr_value)
                if parsed:
                    attributes['alternate_server'] = parsed
        return attributes

    def _parse_address(self, data: bytes) -> str:
        """
        解析地址属性
        """
        if len(data) < 8:
            return None
            
        try:
            reserved, family, port = struct.unpack('>BBH', data[:4])
        except struct.error:
            return None
            
        # 验证保留字段应该为0
        if reserved != 0:
            logger.warning(f"地址属性中的保留字段不为0: {reserved}")
            
        if family == self.IPV4:
            try:
                ip = socket.inet_ntoa(data[4:8])
                return f"{ip}:{port}"
            except:
                return None
        return None

    def _parse_xor_address(self, data: bytes, magic_cookie: int, transaction_id: bytes) -> str:
        """
        解析XOR地址属性
        """
        if len(data) < 8:
            return None
            
        try:
            reserved, family, xport = struct.unpack('>BBH', data[:4])
        except struct.error:
            return None
            
        # 验证保留字段应该为0
        if reserved != 0:
            logger.warning(f"XOR地址属性中的保留字段不为0: {reserved}")
            
        port = xport ^ (magic_cookie >> 16)
        
        if family == self.IPV4:
            try:
                xip = data[4:8]
                ip_bytes = struct.pack('>I', magic_cookie)
                ip = socket.inet_ntoa(bytes(a ^ b for a, b in zip(xip, ip_bytes)))
                return f"{ip}:{port}"
            except:
                return None
        return None

    def _parse_error_code(self, data: bytes) -> Tuple[int, str]:
        """
        解析错误代码属性
        """
        if len(data) < 4:
            return None
            
        try:
            reserved, code_class, code_number = struct.unpack('>BBB', data[:3])
        except struct.error:
            return None
            
        # 验证保留字段应该为0
        if reserved != 0:
            logger.warning(f"错误代码属性中的保留字段不为0: {reserved}")
            
        error_code = code_class * 100 + code_number
        reason = data[4:].decode('utf-8', errors='ignore')
        return error_code, reason


class NATdetect(_PluginBase):
    # 插件名称
    plugin_name = "NAT类型检测"
    # 插件描述
    plugin_desc = "检测MP所在环境的网络NAT类型。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/natdetect.png"
    # 插件版本
    plugin_version = "2.1"
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

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册API接口
        """
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
                                        'component': 'div',
                                        'props': {'class': 'info-section'},
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {'class': 'info-card'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'info-icon', 'data-icon': 'info'}
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'info-content'},
                                                        'text': '本工具直接使用STUN协议检测NAT类型。支持检测：开放互联网、完全锥形NAT、地址限制锥形NAT、端口限制锥形NAT、对称NAT等类型。'
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
                const statusIndicator = document.getElementById('natdetect-status');
                if (statusIndicator) {{
                    statusIndicator.innerHTML = '<div class="status-content"><div class="status-icon" data-icon="warning"></div><span>状态: 请选择服务器</span></div>';
                    statusIndicator.style.backgroundColor = '#fff3e0';
                    statusIndicator.style.color = '#f57c00';
                }}
                return;
            }}
            button.disabled = true;
            const originalText = button.textContent;
            
            // 切换到加载状态
            button.setAttribute('data-icon', 'loading');
            button.textContent = '检测中...';

            // 清空日志框和结果框
            const logBox = document.getElementById('natdetect-log-box');
            const resultBox = document.getElementById('natdetect-result-box');
            if (logBox) {{
                logBox.innerHTML = '';
                logBox.style.display = 'block';
            }}
            if (resultBox) {{
                // 重置为初始状态，直接操作现有元素
                const placeholder = resultBox.querySelector('.result-placeholder');
                if (placeholder) {{
                    // 如果存在placeholder，直接显示
                    placeholder.style.display = 'flex';
                }} else {{
                    // 如果不存在，创建新的
                    resultBox.innerHTML = '<div class="result-placeholder"><div class="result-placeholder-icon" data-icon="question"></div><div class="text-h6 mt-3 text-grey">等待检测结果</div></div>';
                }}
            }}
            if (window.natdetectTimer) {{
                clearInterval(window.natdetectTimer);
                window.natdetectTimer = null;
            }}
            if (window.natdetectRenderTimer) {{
                clearInterval(window.natdetectRenderTimer);
                window.natdetectRenderTimer = null;
            }}
            window.natdetectLastLogIndex = 0;
            window.natdetectCurrentTaskId = null;
            
            // 重置状态指示器
            const statusIndicator = document.getElementById('natdetect-status');
            if (statusIndicator) {{
                statusIndicator.innerHTML = '<div class="status-content"><div class="status-icon" data-icon="loading"></div><span>检测中...</span></div>';
                statusIndicator.style.backgroundColor = '#e3f2fd';
                statusIndicator.style.color = '#1976d2';
            }}

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
                window.natdetectCurrentTaskId = taskId;
                window.natdetectLastLogIndex = 0;
                window.natdetectRenderedCount = 0;
                window.natdetectPolling = false;
                window.natdetectFinishedShown = false;
                window.natdetectPendingLogs = [];
                window.natdetectDoneStatus = null;
                if (logBox) logBox.style.display = 'block';

                // 2.a 渲染定时器：每100ms从队列取1条渲染，形成逐条刷新
                if (window.natdetectRenderTimer) {{
                    clearInterval(window.natdetectRenderTimer);
                }}
                window.natdetectRenderTimer = setInterval(() => {{
                    try {{
                        const q = window.natdetectPendingLogs || [];
                        if (q.length > 0) {{
                            const next = q.shift();
                            if (next && logBox) {{
                                const timestamp = new Date().toLocaleTimeString();
                                logBox.innerHTML += `[${{timestamp}}] ${{next}}<br>`;
                                setTimeout(() => {{ logBox.scrollTop = logBox.scrollHeight; }}, 0);
                            }}
                            return;
                        }}
                        // 队列为空且任务结束，则显示完成提示并停止渲染
                        if (window.natdetectDoneStatus && !window.natdetectFinishedShown) {{
                            if (logBox) {{
                                const timestamp = new Date().toLocaleTimeString();
                                logBox.innerHTML += `[${{timestamp}}] 检测${{window.natdetectDoneStatus === 'done' ? '完成' : '失败'}}<br>`;
                                window.natdetectFinishedShown = true;
                                setTimeout(() => {{ logBox.scrollTop = logBox.scrollHeight; }}, 0);
                            }}
                        }}
                        if (window.natdetectDoneStatus && window.natdetectFinishedShown) {{
                            clearInterval(window.natdetectRenderTimer);
                            window.natdetectRenderTimer = null;
                        }}
                    }} catch (_) {{}}
                }}, 100);

                // 2.b 长轮询：递归请求，服务端在有新日志或超时才返回
                const longPoll = async () => {{
                    try {{
                        // 任务是否仍然有效
                        if (!window.natdetectCurrentTaskId || window.natdetectCurrentTaskId !== taskId) return;
                        const logUrl = `/api/v1/plugin/NATdetect/natdetect/logs?task_id=${{encodeURIComponent(taskId)}}&from_idx=${{window.natdetectLastLogIndex}}&wait=3000&apikey=${{encodeURIComponent(apiKey)}}`;
                        const logResp = await fetch(logUrl, {{
                            method: 'GET',
                            headers: {{ 'Content-Type': 'application/json' }}
                        }});
                        const logData = await logResp.json();
                        if (logData.logs && logData.logs.length) {{
                            if (!window.natdetectPendingLogs) window.natdetectPendingLogs = [];
                            window.natdetectPendingLogs.push(...logData.logs);
                            logBox.style.display = 'block';
                        }}
                        if (typeof logData.total === 'number') {{
                            window.natdetectLastLogIndex = logData.total;
                        }} else {{
                            window.natdetectLastLogIndex += (logData.logs ? logData.logs.length : 0);
                        }}
                        if (logData.status === 'done' || logData.status === 'error') {{
                            // 更新状态指示器
                            const statusIndicator = document.getElementById('natdetect-status');
                            if (statusIndicator) {{
                                if (logData.status === 'done') {{
                                    statusIndicator.innerHTML = '<div class="status-content"><div class="status-icon" data-icon="success"></div><span>检测完成</span></div>';
                                    statusIndicator.style.backgroundColor = '#e8f5e8';
                                    statusIndicator.style.color = '#2e7d32';
                                }} else {{
                                    statusIndicator.innerHTML = '<div class="status-content"><div class="status-icon" data-icon="error"></div><span>检测失败</span></div>';
                                    statusIndicator.style.backgroundColor = '#ffebee';
                                    statusIndicator.style.color = '#c62828';
                                }}
                            }}
                            // 显示结果
                            if (logData.logs && logData.logs.length && logData.status === 'done') {{
                                const resultBox = document.getElementById('natdetect-result-box');
                                if (resultBox) {{
                                    // 查找包含"检测结果"的日志
                                    const resultLog = logData.logs.find(log => log.includes('检测结果'));
                                    if (resultLog) {{
                                        const natType = resultLog.split('：')[1] || resultLog.split(':')[1] || '未知类型';
                                        resultBox.innerHTML = `
                                            <div class="result-container">
                                                <div class="result-details">
                                                    <div class="detail-item">
                                                        <div class="detail-label">NAT类型</div>
                                                        <div class="detail-value">${{natType}}</div>
                                                    </div>
                                                    <div class="detail-item">
                                                        <div class="detail-label">检测服务器</div>
                                                        <div class="detail-value">${{select.value}}</div>
                                                    </div>
                                                    <div class="detail-item">
                                                        <div class="detail-label">检测时间</div>
                                                        <div class="detail-value">${{new Date().toLocaleString()}}</div>
                                                    </div>
                                                </div>
                                                <div class="result-suggestions">
                                                    <div class="suggestion-title">优化建议</div>
                                                    <div class="suggestion-content">${{getNatSuggestions(natType)}}</div>
                                                </div>
                                            </div>
                                        `;
                                    }}
                                }}
                            }}
                            window.natdetectCurrentTaskId = null;
                            button.disabled = false;
                            button.textContent = originalText;
                            // 恢复检测图标
                            button.setAttribute('data-icon', 'detect');
                            window.natdetectDoneStatus = logData.status;
                            return;
                        }}
                    }} catch (e) {{
                        if (logBox) {{
                            const timestamp = new Date().toLocaleTimeString();
                            logBox.innerHTML += `[${{timestamp}}] [日志拉取失败] ${{e.message || e}}<br>`;
                        }}
                        // 更新状态指示器为错误状态
                        const statusIndicator = document.getElementById('natdetect-status');
                        if (statusIndicator) {{
                            statusIndicator.innerHTML = '<div class="status-content"><div class="status-icon" data-icon="network"></div><span>连接错误</span></div>';
                            statusIndicator.style.backgroundColor = '#fff3e0';
                            statusIndicator.style.color = '#f57c00';
                        }}
                        window.natdetectCurrentTaskId = null;
                        button.disabled = false;
                        button.textContent = originalText;
                        // 恢复检测图标
                        button.setAttribute('data-icon', 'detect');
                        return;
                    }}
                    // 下一轮
                    setTimeout(longPoll, 0);
                }};
                longPoll();
            }} catch (error) {{
                if (logBox) {{
                    const timestamp = new Date().toLocaleTimeString();
                    logBox.innerHTML = `[${{timestamp}}] [检测任务启动失败] ${{error}}<br>`;
                    logBox.style.display = 'block';
                }}
                // 更新状态指示器为启动失败状态
                const statusIndicator = document.getElementById('natdetect-status');
                if (statusIndicator) {{
                    statusIndicator.innerHTML = '<div class="status-content"><div class="status-icon" data-icon="error"></div><span>启动失败</span></div>';
                    statusIndicator.style.backgroundColor = '#ffebee';
                    statusIndicator.style.color = '#c62828';
                }}
                button.disabled = false;
                button.textContent = originalText;
                // 恢复检测图标
                button.setAttribute('data-icon', 'detect');
            }}
            
            // 根据NAT类型获取建议
            function getNatSuggestions(natType) {{
                if (natType.includes('开放互联网') || natType.includes('Open Internet')) {{
                    return '您的网络处于开放互联网环境，无需特殊配置即可获得最佳P2P连接效果。';
                }} else if (natType.includes('全锥型') || natType.includes('Full Cone')) {{
                    return '您的网络使用全锥型NAT，P2P连接效果良好。建议：<br>1. 启用UPnP或NAT-PMP功能<br>2. 如有需要，可配置端口转发';
                }} else if (natType.includes('限制锥型') || natType.includes('Restricted Cone')) {{
                    return '您的网络使用限制锥型NAT，P2P连接效果中等。建议：<br>1. 启用UPnP或NAT-PMP功能<br>2. 配置端口转发<br>3. 检查防火墙设置';
                }} else if (natType.includes('端口限制') || natType.includes('Port-Restricted')) {{
                    return '您的网络使用端口限制锥型NAT，P2P连接效果较差。建议：<br>1. 配置端口转发<br>2. 检查防火墙设置<br>3. 考虑使用中继服务器';
                }} else if (natType.includes('对称型') || natType.includes('Symmetric')) {{
                    return '您的网络使用对称型NAT，P2P连接困难。建议：<br>1. 使用中继服务器<br>2. 考虑使用VPN<br>3. 联系网络服务提供商';
                }} else {{
                    return '无法确定网络类型，请尝试使用不同的检测服务器或检查网络配置。';
                }}
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
                                'component': 'div',
                                'props': {'class': 'modern-container'},
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {'class': 'header-section'},
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {'class': 'header-icon'},
                                                'content': [
                                                    {'component': 'VIcon', 'props': {'size': '32', 'color': 'info'}, 'text': 'mdi-lan-connect'}
                                                ]
                                            },
                                                    {
                                                        'component': 'div',
                                                'props': {'class': 'header-content'},
                                                        'content': [
                                                    {'component': 'h1', 'props': {'class': 'header-title'}, 'text': 'NAT类型检测'},
                                                    {'component': 'p', 'props': {'class': 'header-subtitle'}, 'text': '检测当前网络的NAT类型，辅助排查内网穿透/端口映射问题'}
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'div',
                                        'props': {'class': 'content-grid'},
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {'class': 'log-section'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'card'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'card-header'},
                                                                'content': [
                                                                    {'component': 'h2', 'props': {'class': 'card-title'}, 'text': '检测日志'}
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'card-body'},
                                                                'content': [
                                                                    {
                                                                        'component': 'div',
                                                'props': {
                                                                            'id': 'natdetect-status',
                                                                            'class': 'status-indicator'
                                                },
                                                'content': [
                                                                            {
                                                                                'component': 'div',
                                                                                'props': {'class': 'status-content'},
                                                                                'content': [
                                                                                    {'component': 'div', 'props': {'class': 'status-icon', 'data-icon': 'info'}},
                                                                                    {'component': 'span', 'text': '状态: 等待开始检测'}
                                                                                ]
                                                                            }
                                                                        ]
                                                                    },
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'label': "选择服务器",
                                                            'items': server_options,
                                                            'item-title': 'label',
                                                            'item-value': 'value',
                                                            'id': 'natdetect-server-select',
                                                            'variant': 'outlined',
                                                            'density': 'comfortable',
                                                            'clearable': False,
                                                            'class': 'server-select',
                                                            'prepend-inner-icon': 'mdi-server',
                                                            'height': '56px'
                                                        }
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'id': 'natdetect-log-box',
                                                            'class': 'log-container'
                                                        }
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'card-actions'},
                                                        'content': [
                                                    {
                                                        'component': 'VBtn',
                                                        'props': {
                                                            'color': 'primary',
                                                            'onclick': js_onclick,
                                                            'id': 'natdetect-detect-btn',
                                                                    'class': 'detect-btn',
                                                                    'data-icon': 'detect'
                                                                },
                                                                'text': '开始检测'
                                                            },
                                                            {
                                                                'component': 'VBtn',
                                                                'props': {
                                                                    'color': 'secondary',
                                                                    'class': 'clear-btn',
                                                                    'onclick': "document.getElementById('natdetect-log-box').innerHTML = '';",
                                                                    'prepend-icon': 'mdi-delete'
                                                                },
                                                                'text': '清空日志'
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
                                                'component': 'div',
                                                'props': {'class': 'result-section'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'card'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'card-header'},
                                                                'content': [
                                                                    {'component': 'h2', 'props': {'class': 'card-title'}, 'text': '检测结果'}
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'id': 'natdetect-result-box',
                                                                    'class': 'result-container'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'result-placeholder'},
                                                                        'content': [
                                                                            {
                                                                                'component': 'div',
                                                                                'props': {'class': 'result-placeholder-icon', 'data-icon': 'question'},
                                                                                'text': ''
                                                                            },
                                                                            {
                                                                                'component': 'div',
                                                                                'props': {'class': 'text-h6 mt-3 text-grey'},
                                                                                'text': '等待检测结果'
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
                                        'component': 'div',
                                        'props': {'class': 'info-section'},
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {'class': 'info-card'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'info-icon', 'data-icon': 'info'}
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'info-content'},
                                                        'text': '提示：NAT类型检测可能需要30-60秒，请耐心等待。检测过程中请不要关闭页面。'
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
        
        # 添加内联CSS样式
        page.append({
            'component': 'style',
            'text': """
                /* 整体布局 */
                .modern-container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 24px;
                }
                
                .header-section {
                    display: flex;
                    align-items: center;
                    margin-bottom: 24px;
                    padding-bottom: 12px;
                    border-bottom: 1px solid #e0e0e0;
                }
                
                .header-icon {
                    width: 48px;
                    height: 48px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-right: 16px;
                }
                
                .header-content {
                    flex: 1;
                }
                
                .header-title {
                    font-size: 22px;
                    font-weight: 600;
                    color: #333;
                    margin: 0;
                    line-height: 1.2;
                }
                
                .header-subtitle {
                    font-size: 14px;
                    color: #666;
                    margin: 4px 0 0;
                    line-height: 1.4;
                }
                
                .content-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 24px;
                    margin-bottom: 32px;
                }
                
                @media (max-width: 960px) {
                    .content-grid {
                        grid-template-columns: 1fr;
                    }
                }
                
                /* 卡片样式 */
                .card {
                    background: #fff;
                    border-radius: 16px;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
                    overflow: hidden;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                }
                
                .card-header {
                    padding: 12px 24px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #e0e0e0;
                }
                
                .card-title {
                    font-size: 16px;
                    font-weight: 600;
                    color: #333;
                    margin: 0;
                }
                
                .card-body {
                    padding: 24px;
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                }
                
                /* 状态指示器 */
                .status-indicator {
                    padding: 12px 16px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    background: #f5f5f5;
                    color: #333;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                    transition: all 0.3s ease;
                    border: 1px solid #e0e0e0;
                }
                
                .status-content {
                    display: flex;
                    align-items: center;
                }
                
                .status-icon {
                    margin-right: 8px;
                    position: relative;
                }
                
                /* 状态图标样式 - SVG方案 */
                .status-icon::before {
                    content: '';
                    display: inline-block;
                    width: 16px;
                    height: 16px;
                    margin-right: 4px;
                    vertical-align: middle;
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                }
                
                .status-icon[data-icon="info"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23666' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'%3E%3C/circle%3E%3Cline x1='12' y1='16' x2='12' y2='12'%3E%3C/line%3E%3Cline x1='12' y1='8' x2='12.01' y2='8'%3E%3C/line%3E%3C/svg%3E");
                }
                
                .status-icon[data-icon="loading"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%232196F3' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='12' y1='2' x2='12' y2='6'%3E%3C/line%3E%3Cline x1='12' y1='18' x2='12' y2='22'%3E%3C/line%3E%3Cline x1='4.93' y1='4.93' x2='7.76' y2='7.76'%3E%3C/line%3E%3Cline x1='16.24' y1='16.24' x2='19.07' y2='19.07'%3E%3C/line%3E%3Cline x1='2' y1='12' x2='6' y2='12'%3E%3C/line%3E%3Cline x1='18' y1='12' x2='22' y2='12'%3E%3C/line%3E%3Cline x1='4.93' y1='19.07' x2='7.76' y2='16.24'%3E%3C/line%3E%3Cline x1='16.24' y1='7.76' x2='19.07' y2='4.93'%3E%3C/line%3E%3C/svg%3E");
                    animation: spin 1s linear infinite;
                }
                
                .status-icon[data-icon="warning"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23ff9800' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'%3E%3C/path%3E%3Cline x1='12' y1='9' x2='12' y2='13'%3E%3C/line%3E%3Cline x1='12' y1='17' x2='12.01' y2='17'%3E%3C/line%3E%3C/svg%3E");
                }
                
                .status-icon[data-icon="success"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%234caf50' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M22 11.08V12a10 10 0 1 1-5.93-9.14'%3E%3C/path%3E%3Cpolyline points='22 4 12 14.01 9 11.01'%3E%3C/polyline%3E%3C/svg%3E");
                }
                
                .status-icon[data-icon="error"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23f44336' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'%3E%3C/circle%3E%3Cline x1='15' y1='9' x2='9' y2='15'%3E%3C/line%3E%3Cline x1='9' y1='9' x2='15' y2='15'%3E%3C/line%3E%3C/svg%3E");
                }
                
                .status-icon[data-icon="network"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23ff9800' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 12.55a11 11 0 0 1 14.08 0'%3E%3C/path%3E%3Cpath d='M1.42 9a16 16 0 0 1 21.16 0'%3E%3C/path%3E%3Cpath d='M8.53 16.11a6 6 0 0 1 6.95 0'%3E%3C/path%3E%3Cline x1='12' y1='20' x2='12.01' y2='20'%3E%3C/line%3E%3C/svg%3E");
                }
                
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                /* 按钮图标样式 - 参考状态指示器方法 */
                .detect-btn::before {
                    content: '';
                    display: inline-block;
                    width: 16px;
                    height: 16px;
                    margin-right: 8px;
                    vertical-align: middle;
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                }
                
                .detect-btn[data-icon="detect"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z'%3E%3C/path%3E%3Cpolyline points='3.27 6.96 12 12.01 20.73 6.96'%3E%3C/polyline%3E%3Cline x1='12' y1='22.08' x2='12' y2='12'%3E%3C/line%3E%3C/svg%3E");
                }
                
                .detect-btn[data-icon="loading"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='12' y1='2' x2='12' y2='6'%3E%3C/line%3E%3Cline x1='12' y1='18' x2='12' y2='22'%3E%3C/line%3E%3Cline x1='4.93' y1='4.93' x2='7.76' y2='7.76'%3E%3C/line%3E%3Cline x1='16.24' y1='16.24' x2='19.07' y2='19.07'%3E%3C/line%3E%3Cline x1='2' y1='12' x2='6' y2='12'%3E%3C/line%3E%3Cline x1='18' y1='12' x2='22' y2='12'%3E%3C/line%3E%3Cline x1='4.93' y1='19.07' x2='7.76' y2='16.24'%3E%3C/line%3E%3Cline x1='16.24' y1='7.76' x2='19.07' y2='4.93'%3E%3C/line%3E%3C/svg%3E");
                    animation: spin 1s linear infinite;
                }
                
                /* 服务器选择 */
                .server-select {
                    margin-bottom: 20px;
                    height: 56px !important;
                    min-height: 56px !important;
                    max-height: 56px !important;
                }
                
                .server-select .v-field {
                    height: 56px !important;
                    min-height: 56px !important;
                    max-height: 56px !important;
                }
                
                .server-select .v-field__input {
                    height: 56px !important;
                    min-height: 56px !important;
                    max-height: 56px !important;
                }
                
                /* 日志容器 */
                .log-container {
                    height: 195px !important;
                    min-height: 195px !important;
                    max-height: 195px !important;
                    overflow-y: auto;
                    background: #f8fafc;
                    border-radius: 12px;
                    padding: 16px;
                    border: 1px solid #e2e8f0;
                    flex: 1;
                    margin-bottom: 20px;
                    box-sizing: border-box;
                    clip-path: inset(0 round 12px);
                }
                
                /* 按钮样式 */
                .card-actions {
                    display: flex;
                    gap: 12px;
                }
                
                .detect-btn, .clear-btn {
                    flex: 1;
                    border-radius: 12px;
                    font-weight: 500;
                    text-transform: none;
                    letter-spacing: normal;
                }
                
                /* 结果区域 */
                .result-container {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                }
                
                .result-placeholder {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    color: #9e9e9e;
                }
                
                .result-placeholder-icon {
                    width: 64px;
                    height: 64px;
                    margin-bottom: 16px;
                    opacity: 0.5;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .result-placeholder-icon::before {
                    content: '';
                    width: 48px;
                    height: 48px;
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                }
                
                .result-placeholder-icon[data-icon="question"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%239e9e9e'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z'/%3E%3C/svg%3E");
                }
                
                .result-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }
                
                .result-badge {
                    background: linear-gradient(135deg, #4CAF50, #81C784);
                    color: white;
                    padding: 6px 16px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 16px;
                }
                
                .result-details {
                    background: #f8fafc;
                    border-radius: 12px;
                    padding: 16px;
                    margin: 20px 24px 24px 24px;
                }
                
                .detail-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #e2e8f0;
                }
                
                .detail-item:last-child {
                    border-bottom: none;
                }
                
                .detail-label {
                    color: #78909c;
                    font-weight: 500;
                }
                
                .detail-value {
                    color: #37474f;
                    font-weight: 500;
                }
                
                .result-suggestions {
                    background: #e3f2fd;
                    border-radius: 12px;
                    padding: 16px;
                    margin: 0 24px;
                }
                
                .suggestion-title {
                    font-weight: 600;
                    color: #2196F3;
                    margin-bottom: 12px;
                }
                
                .suggestion-content {
                    color: #37474f;
                    line-height: 1.6;
                }
                
                /* 信息卡片 */
                .info-section {
                    margin-top: 24px;
                }
                
                .info-card {
                    display: flex;
                    background: #e3f2fd;
                    border-radius: 12px;
                    padding: 8px 16px;
                    border: 1px solid #e1f5fe;
                    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.1);
                    margin-top: 20px;
                }
                
                .info-icon {
                    background: linear-gradient(135deg, #2196F3, #1976d2);
                    color: white;
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-right: 10px;
                    font-weight: bold;
                    flex-shrink: 0;
                    position: relative;
                    box-shadow: 0 1px 4px rgba(33, 150, 243, 0.3);
                }
                
                /* 信息图标矢量样式 */
                .info-icon::before {
                    content: '';
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                }
                
                .info-icon[data-icon="info"]::before {
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'%3E%3C/circle%3E%3Cline x1='12' y1='16' x2='12' y2='12'%3E%3C/line%3E%3Cline x1='12' y1='8' x2='12.01' y2='8'%3E%3C/line%3E%3C/svg%3E");
                }
                
                .info-content {
                    color: #1976d2;
                    font-weight: 500;
                    line-height: 1.4;
                    font-size: 13px;
                    display: flex;
                    align-items: center;
                }
                
                /* 深色模式适配 - 使用Vuetify主题系统 */
                .v-theme--dark {
                    .modern-container {
                        color: #B6BEE3 !important;
                    }
                    
                    .header-section {
                        border-bottom: 1px solid #3d4459 !important;
                    }
                    
                    .header-title {
                        color: #CFD3EC !important;
                    }
                    
                    .header-subtitle {
                        color: #8692D0 !important;
                    }
                    
                    .card {
                        background: #1a1d2e !important;
                        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
                        border: 1px solid #3d4459 !important;
                    }
                    
                    .card-header {
                        background: #2a2e42 !important;
                        border-bottom: 1px solid #4a5072 !important;
                    }
                    
                    .card-title {
                        color: #CFD3EC !important;
                    }
                    
                    /* 强制覆盖Vuetify卡片样式 */
                    .v-card {
                        background: #1e1e1e !important;
                        color: #e0e0e0 !important;
                    }
                    
                    .v-card.v-card--variant-outlined {
                        border: 1px solid #333 !important;
                    }
                    
                    .status-indicator {
                        background: #2a2e42 !important;
                        color: #B6BEE3 !important;
                        border: 1px solid #4a5072 !important;
                    }
                    
                    .server-select {
                        color: #B6BEE3 !important;
                    }
                    
                    .server-select .v-field {
                        background: #2a2e42 !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .server-select .v-field__input {
                        color: #B6BEE3 !important;
                    }
                    
                    .log-container {
                        background: #1f2335 !important;
                        border: 1px solid #3d4459 !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .result-container {
                        background: #1f2335 !important;
                    }
                    
                    .result-placeholder {
                        color: #8692D0 !important;
                    }
                    
                    .result-details {
                        background: #2a2e42 !important;
                        border: 1px solid #3d4459 !important;
                    }
                    
                    .detail-item {
                        border-bottom: 1px solid #4a5072 !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .detail-label {
                        color: #8692D0 !important;
                    }
                    
                    .detail-value {
                        color: #CFD3EC !important;
                    }
                    
                    .result-suggestions {
                        background: #2a2e42 !important;
                        border: 1px solid #3d4459 !important;
                    }
                    
                    .suggestion-title {
                        color: #CFD3EC !important;
                    }
                    
                    .suggestion-content {
                        color: #B6BEE3 !important;
                    }
                    
                    .detect-btn {
                        background: linear-gradient(135deg, #6E66ED, #5A52D5) !important;
                        color: white !important;
                    }
                    
                    .detect-btn:hover {
                        background: linear-gradient(135deg, #5A52D5, #4A42C7) !important;
                    }
                    
                    .clear-btn {
                        background: #3d4459 !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .clear-btn:hover {
                        background: #4a5072 !important;
                    }
                    
                    .info-card {
                        background: linear-gradient(135deg, #2a2e42, #3d4459) !important;
                        border: 1px solid #4a5072 !important;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
                    }
                    
                    .info-icon {
                        background: linear-gradient(135deg, #6E66ED, #5A52D5) !important;
                    }
                    
                    .info-content {
                        color: #42A5F5 !important;
                    }
                    
                    /* 状态指示器深色模式颜色 - 更柔和的颜色 */
                    .status-indicator[style*="background-color: #e3f2fd"] {
                        background: #2a2e42 !important;
                        color: #42A5F5 !important;
                    }
                    
                    .status-indicator[style*="background-color: #e8f5e8"] {
                        background: #1b5e20 !important;
                        color: #66BB6A !important;
                    }
                    
                    .status-indicator[style*="background-color: #ffebee"] {
                        background: #b71c1c !important;
                        color: #EF5350 !important;
                    }
                    
                    .status-indicator[style*="background-color: #fff3e0"] {
                        background: #e65100 !important;
                        color: #FFA726 !important;
                    }
                    
                    .status-indicator[style*="background-color: #f3e5f5"] {
                        background: #4a148c !important;
                        color: #AB47BC !important;
                    }
                    
                    /* Vuetify组件深色模式适配 - 使用更柔和的颜色 */
                    .v-card {
                        background: #1a1d2e !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-card-item {
                        background: #1a1d2e !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-card-text {
                        background: #1a1d2e !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-card-title {
                        color: #CFD3EC !important;
                    }
                    
                    .v-field {
                        background: #2a2e42 !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-field__input {
                        color: #B6BEE3 !important;
                    }
                    
                    .v-field__outline {
                        color: #4a5072 !important;
                    }
                    
                    .v-field__outline__start {
                        color: #4a5072 !important;
                    }
                    
                    .v-field__outline__end {
                        color: #4a5072 !important;
                    }
                    
                    .v-field__outline__notch {
                        color: #4a5072 !important;
                    }
                    
                    .v-label {
                        color: #8692D0 !important;
                    }
                    
                    .v-btn {
                        color: #B6BEE3 !important;
                    }
                    
                    .v-btn--variant-elevated {
                        background: #3d4459 !important;
                    }
                    
                    .v-btn--variant-elevated:hover {
                        background: #4a5072 !important;
                    }
                    
                    .v-btn--variant-flat,
                    .v-btn--variant-outlined {
                        background: transparent !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-btn--variant-flat:hover,
                    .v-btn--variant-outlined:hover {
                        background: rgba(182, 190, 227, 0.1) !important;
                    }
                    
                    .v-btn--variant-outlined {
                        border: 1px solid #4a5072 !important;
                    }
                    
                    /* 强制覆盖所有可能的Vuetify样式 */
                    .v-theme--light .v-card,
                    .v-application .v-card,
                    .v-card[class*="card"] {
                        background: #1a1d2e !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-theme--light .v-card-item,
                    .v-application .v-card-item,
                    .v-card[class*="card"] .v-card-item {
                        background: #1a1d2e !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-theme--light .v-card-text,
                    .v-application .v-card-text,
                    .v-card[class*="card"] .v-card-text {
                        background: #1a1d2e !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-theme--light .v-card-title,
                    .v-application .v-card-title,
                    .v-card[class*="card"] .v-card-title {
                        color: #CFD3EC !important;
                    }
                    
                    .v-application .v-field {
                        background: #2a2e42 !important;
                        color: #B6BEE3 !important;
                    }
                    
                    .v-application .v-field__input {
                        color: #B6BEE3 !important;
                    }
                    
                    .v-application .v-label {
                        color: #8692D0 !important;
                    }
                    
                    .v-application .v-btn {
                        color: #B6BEE3 !important;
                    }
                }
                
                /* 移动端响应式设计 - 所有模式通用 */
                @media (max-width: 768px) {
                    .modern-container {
                        padding: 16px !important;
                        max-width: 100% !important;
                    }
                    
                    .header-section {
                        flex-direction: row !important;
                        align-items: center !important;
                        gap: 12px !important;
                        margin-bottom: 20px !important;
                    }
                    
                    .header-icon {
                        width: 40px !important;
                        height: 40px !important;
                    }
                    
                    .header-title {
                        font-size: 20px !important;
                        line-height: 1.2 !important;
                    }
                    
                    .header-subtitle {
                        font-size: 13px !important;
                        line-height: 1.3 !important;
                    }
                    
                    .main-content {
                        flex-direction: column !important;
                        gap: 16px !important;
                    }
                    
                    .log-section, .result-section {
                        width: 100% !important;
                        flex: none !important;
                    }
                    
                    .card {
                        margin-bottom: 16px !important;
                    }
                    
                    .card-header {
                        padding: 12px 16px !important;
                    }
                    
                    .card-title {
                        font-size: 14px !important;
                    }
                    
                    .card-content {
                        padding: 16px !important;
                    }
                    
                    .status-indicator {
                        padding: 12px 16px !important;
                        font-size: 13px !important;
                    }
                    
                    .server-select {
                        margin-bottom: 12px !important;
                    }
                    
                    .log-container {
                        height: 160px !important;
                        min-height: 160px !important;
                        max-height: 160px !important;
                        padding: 12px !important;
                    }
                    
                    .card-actions {
                        flex-direction: row !important;
                        gap: 12px !important;
                    }
                    
                    .detect-btn, .clear-btn {
                        flex: 1 !important;
                        height: 35px !important;
                        font-size: 14px !important;
                    }
                    
                    .result-placeholder {
                        padding: 20px !important;
                    }
                    
                    .result-placeholder-icon {
                        width: 40px !important;
                        height: 40px !important;
                    }
                    
                    .info-card {
                        padding: 10px 12px !important;
                        margin-top: 12px !important;
                    }
                    
                    .info-icon {
                        width: 20px !important;
                        height: 20px !important;
                        margin-right: 8px !important;
                    }
                    
                    .info-content {
                        font-size: 12px !important;
                        line-height: 1.3 !important;
                    }
                }
                
                /* 超小屏幕适配 - 所有模式通用 */
                @media (max-width: 480px) {
                    .modern-container {
                        padding: 12px !important;
                    }
                    
                    .header-section {
                        flex-direction: row !important;
                        align-items: center !important;
                        gap: 10px !important;
                        margin-bottom: 16px !important;
                    }
                    
                    .header-icon {
                        width: 36px !important;
                        height: 36px !important;
                    }
                    
                    .header-title {
                        font-size: 18px !important;
                    }
                    
                    .header-subtitle {
                        font-size: 12px !important;
                    }
                    
                    .card-header {
                        padding: 10px 12px !important;
                    }
                    
                    .card-content {
                        padding: 12px !important;
                    }
                    
                    .status-indicator {
                        padding: 10px 12px !important;
                        font-size: 12px !important;
                    }
                    
                    .log-container {
                        height: 140px !important;
                        min-height: 140px !important;
                        max-height: 140px !important;
                        padding: 10px !important;
                    }
                    
                    .card-actions {
                        flex-direction: row !important;
                        gap: 10px !important;
                    }
                    
                    .detect-btn, .clear-btn {
                        flex: 1 !important;
                        height: 35px !important;
                        font-size: 13px !important;
                    }
                    
                    .result-placeholder {
                        padding: 16px !important;
                    }
                    
                    .result-placeholder-icon {
                        width: 36px !important;
                        height: 36px !important;
                    }
                    
                    .info-card {
                        padding: 8px 10px !important;
                    }
                    
                    .info-icon {
                        width: 18px !important;
                        height: 18px !important;
                        margin-right: 6px !important;
                    }
                    
                    .info-content {
                        font-size: 11px !important;
                    }
                }
            """
        })
        
        return page

    async def nat_detect_start(self, server: str = Query(...), apikey: str = Query(...)):
        """
        启动NAT检测任务，返回task_id
        """
        if apikey != settings.API_TOKEN:
            return {"code": 401, "message": "API令牌错误!"}
        if not server:
            return {"code": 400, "message": "请选择STUN服务器"}
            
        task_id = str(uuid.uuid4())
        # 确保任务ID在日志和任务列表中
        self._tasks[task_id] = False
        self._logs[task_id] = []
        # 启动异步检测任务
        asyncio.create_task(self._run_natdetect_task(task_id, server))
        return {"code": 200, "task_id": task_id}

    async def _run_natdetect_task(self, task_id, server):
        """
        运行NAT检测任务
        """
        # 检查任务是否已经存在
        if task_id not in self._tasks or task_id not in self._logs:
            return
            
        # 确保任务开始时没有重复的日志
        if task_id in self._logs:
            # 清空该任务之前的日志，防止重复执行时出现历史日志
            self._logs[task_id] = []
            
        try:
            self._logs[task_id].append(f"开始检测NAT类型，使用服务器: {server}")
            nat_type = await self._detect_nat_type(task_id, server)
            self._logs[task_id].append(f"检测结果：{nat_type}")
        except Exception as e:
            logger.error(f"NAT类型检测任务失败: {e}")
            if task_id in self._logs:
                self._logs[task_id].append(f"NAT类型检测失败: {e}")
        finally:
            if task_id in self._tasks:
                self._tasks[task_id] = True
            # 任务结束后延迟清理
            asyncio.create_task(self._cleanup_task(task_id))


    async def _detect_nat_type(self, task_id: str, server: str) -> str:
        """
        执行NAT类型检测 (参考Lucky工具的RFC 3489实现)
        """
        try:
            # 解析服务器地址
            if ':' in server:
                host, port = server.split(':', 1)
                port = int(port)
            else:
                host = server
                port = 3478
                
            self._logs[task_id].append(f"连接STUN服务器: {host}:{port}")
            
            # 创建UDP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)  # 设置3秒超时时间
            
            try:
                # 验证服务器地址是否可解析
                try:
                    socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
                except socket.gaierror as e:
                    return f"无法解析服务器地址: {str(e)}"
                
                # 创建STUN客户端
                stun_client = STUNClient()
                
                # 步骤1: 发送标准绑定请求 (映射行为检测)
                self._logs[task_id].append("[NAT映射行为检测] 连接到STUN服务器")
                self._logs[task_id].append("[NAT映射行为检测] 【步骤1】标准绑定请求")
                request = stun_client.create_binding_request()
                sock.sendto(request, (host, port))
                
                # 接收响应
                try:
                    data, addr = sock.recvfrom(1024)
                    self._logs[task_id].append(f"[NAT映射行为检测] 收到来自 {addr} 的响应")
                except socket.timeout:
                    return "连接STUN服务器超时"
                
                # 解析响应
                response = stun_client.parse_stun_response(data)
                if not response:
                    error_msg = "无法解析STUN响应"
                    return error_msg
                    
                # 记录服务器软件信息（如果有的话）
                if 'software' in response:
                    self._logs[task_id].append(f"[NAT映射行为检测] 服务器软件: {response['software']}")
                
                mapped_address = response.get('xor_mapped_address') or response.get('mapped_address')
                if not mapped_address:
                    error_msg = "响应中未包含映射地址"
                    return error_msg
                    
                changed_address = response.get('changed_address')
                
                mapped_addr_info = f"[NAT映射行为检测] 服务器返回的公网地址（XOR-MAPPED-ADDRESS）：{mapped_address}"
                self._logs[task_id].append(mapped_addr_info)
                
                # 如果没有changed_address，则尝试推断OTHER-ADDRESS（类似Lucky的做法）
                if not changed_address:
                    # 尝试推断OTHER-ADDRESS
                    server_ip, server_port = addr
                    other_port = server_port + 1 if server_port < 65535 else server_port - 1
                    changed_address = f"{server_ip}:{other_port}"
                    other_addr_info = f"[NAT映射行为检测] 推断的服务器OTHER-ADDRESS：{changed_address}"
                    self._logs[task_id].append(other_addr_info)
                else:
                    other_addr_info = f"[NAT映射行为检测] 服务器OTHER-ADDRESS：{changed_address}"
                    self._logs[task_id].append(other_addr_info)
                
                mapped_ip, mapped_port = mapped_address.split(':')
                mapped_port = int(mapped_port)
                
                local_ip, local_port = sock.getsockname()
                local_addr_info = f"[NAT映射行为检测] 比较本地地址[{local_ip}:{local_port}] <-> 服务器映射地址[{mapped_address}]"
                self._logs[task_id].append(local_addr_info)
                
                # 继续执行完整的RFC 3489检测流程
                changed_ip, changed_port = changed_address.split(':')
                changed_port = int(changed_port)
                
                # 步骤2: 映射行为检测 - 发送到其他IP但相同端口
                self._logs[task_id].append(f"[NAT映射行为检测] 【步骤2】发送到OTHER-ADDRESS的新IP但原端口：{changed_ip}:{port}")
                other_addr = (changed_ip, port)
                request = stun_client.create_binding_request()
                sock.sendto(request, other_addr)
                
                try:
                    data, addr = sock.recvfrom(1024)
                    response2 = stun_client.parse_stun_response(data)
                    if response2:
                        mapped_address2 = response2.get('xor_mapped_address') or response2.get('mapped_address')
                        self._logs[task_id].append(f"[NAT映射行为检测] 【步骤2】映射地址：{mapped_address2}")
                        
                        # 比较两个映射地址
                        if mapped_address == mapped_address2:
                            self._logs[task_id].append("[NAT映射行为检测] 结论：端点独立映射")
                            mapping_behavior = 1  # 端点独立映射
                        else:
                            self._logs[task_id].append("[NAT映射行为检测] 结论：端点依赖映射")
                            mapping_behavior = 2  # 端点依赖映射
                    else:
                        self._logs[task_id].append("[NAT映射行为检测] 【步骤2】无法解析响应")
                        mapping_behavior = 0  # 未知
                except socket.timeout:
                    self._logs[task_id].append("[NAT映射行为检测] 【步骤2】请求超时")
                    mapping_behavior = 0  # 未知
                
                mapping_behavior_info = f"[NAT类型检测] NAT映射行为：{mapping_behavior}"
                self._logs[task_id].append(mapping_behavior_info)
                
                # 步骤3: 过滤行为检测
                filter_behavior_info = "[NAT过滤行为检测] 连接到STUN服务器"
                self._logs[task_id].append(filter_behavior_info)
                self._logs[task_id].append("[NAT过滤行为检测] 【步骤1】标准绑定请求")
                
                # 测试1: 发送CHANGE-REQUEST要求改变IP和端口
                self._logs[task_id].append("[NAT过滤行为检测] 【步骤2】请求服务器更换IP和端口")
                request = stun_client.create_binding_request(change_ip=True, change_port=True)
                sock.sendto(request, (host, port))
                
                try:
                    data, addr = sock.recvfrom(1024)
                    received_info = "收到响应，NAT允许来自任何地址和端口的数据包"
                    self._logs[task_id].append(received_info)
                    filtering_behavior = 1  # 端点独立过滤
                except socket.timeout:
                    self._logs[task_id].append("[STUN请求] 等待响应超时")
                    
                    # 测试2: 发送CHANGE-REQUEST要求只改变端口
                    self._logs[task_id].append("[NAT过滤行为检测] 【步骤3】请求服务器只更换端口")
                    request = stun_client.create_binding_request(change_port=True, change_ip=False)
                    sock.sendto(request, (host, port))
                    
                    try:
                        data, addr = sock.recvfrom(1024)
                        received_info2 = "收到响应，NAT允许来自相同IP不同端口的数据包"
                        self._logs[task_id].append(received_info2)
                        filtering_behavior = 2  # 地址依赖过滤
                    except socket.timeout:
                        self._logs[task_id].append("[STUN请求] 等待响应超时")
                        self._logs[task_id].append("[NAT过滤行为检测] 结论：地址和端口依赖过滤")
                        filtering_behavior = 3  # 地址和端口依赖过滤
                
                self._logs[task_id].append(f"[NAT类型检测] NAT过滤行为：{filtering_behavior}")
                
                # 根据RFC 3489确定NAT类型
                self._logs[task_id].append("[NAT类型检测] 【NAT类型判定】")
                
                # 如果本地地址和映射地址相同，则在公网
                if local_ip == mapped_ip and local_port == mapped_port:
                    if filtering_behavior == 1:
                        return "Open Internet (开放互联网)"
                    elif filtering_behavior == 2:
                        return "Firewall (防火墙)"
                    else:
                        return "Symmetric UDP Firewall (对称UDP防火墙)"
                else:
                    # 在NAT后
                    if mapping_behavior == 1:  # 端点独立映射
                        if filtering_behavior == 1:  # 端点独立过滤
                            return "NAT1 - 全锥型NAT"
                        elif filtering_behavior == 2:  # 地址依赖过滤
                            return "NAT2 - 地址限制锥型NAT"
                        else:  # 地址和端口依赖过滤
                            return "NAT3 - 端口限制锥型NAT"
                    else:  # 端点依赖映射
                        return "NAT4 - 对称型NAT"
                        
            finally:
                sock.close()
                
        except socket.timeout:
            return "连接STUN服务器超时"
        except socket.gaierror as e:
            return f"DNS解析错误: {str(e)}"
        except Exception as e:
            return f"检测过程中发生错误: {str(e)}"

    async def _cleanup_task(self, task_id: str, delay: int = 60):
        """延迟清理任务数据"""
        await asyncio.sleep(delay)
        if task_id in self._logs:
            del self._logs[task_id]
        if task_id in self._tasks:
            del self._tasks[task_id]

    async def nat_detect_logs(self, task_id: str = Query(...), from_idx: int = Query(0), apikey: str = Query(...), wait: int = Query(0)):
        """
        拉取检测任务日志
        """
        if apikey != settings.API_TOKEN:
            return {"code": 401, "message": "API令牌错误!"}
        if task_id not in self._tasks:
            return {"code": 404, "message": "任务不存在或已过期"}
        # Ensure from_idx is treated as integer and slice safely
        timeout_ms = max(0, int(wait))
        start_time = time.time()
        while True:
            logs = self._logs.get(task_id, [])
            status = 'done' if self._tasks.get(task_id, False) else 'running'
            start_idx = max(0, min(int(from_idx), len(logs)))
            if start_idx < len(logs) or status != 'running' or timeout_ms == 0:
                sliced_logs = logs[start_idx:]
                return {"code": 200, "logs": sliced_logs, "status": status, "total": len(logs)}
            # 长轮询等待新日志或超时
            if (time.time() - start_time) * 1000 >= timeout_ms:
                return {"code": 200, "logs": [], "status": status, "total": len(logs)}
            await asyncio.sleep(0.1)
    
    def stop_service(self):
        """停止插件服务"""
        self._enabled = False
        logger.info("插件已停止")
