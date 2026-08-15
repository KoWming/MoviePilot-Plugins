"""
MoviePilot-Tools 扩展服务端同步插件。

为 Chrome 扩展 MoviePilot-Tools-2.0 提供插件数据目录文件读写端点：
  POST /api/v1/plugin/MoviePilotTools/upload
  GET  /api/v1/plugin/MoviePilotTools/download

落盘：settings.PLUGIN_DATA_PATH / MoviePilotTools / {user}/...
敏感项（Token/PIN/密钥）由扩展侧过滤，本插件不做业务识别。
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

from fastapi import Body, Query
from fastapi.responses import JSONResponse

from app.chain.download import DownloadChain  # pyright: ignore[reportMissingImports]
from app.core.config import settings  # pyright: ignore[reportMissingImports]
from app.helper.directory import validate_download_save_path  # pyright: ignore[reportMissingImports]
from app.log import logger  # pyright: ignore[reportMissingImports]
from torrentool.api import Torrent  # pyright: ignore[reportMissingImports]
from app.plugins import _PluginBase  # pyright: ignore[reportMissingImports]

# 相对路径：Unicode 字母数字、下划线、短横、点、斜杠；禁止绝对路径与 ..
_SAFE_PATH_RE = re.compile(r"^[\w\-.\/]+$", re.UNICODE)
# 默认允许的后缀（MoviePilot-Tools 2.0 备份文件）
_DEFAULT_SUFFIXES = {
    ".mpt2",  # 2.0 加密备份主文件（backup.mpt2）
    ".json",  # 备份清单 manifest.json
}
# 路径中禁止出现的敏感文件名片段（扩展本就不该同步，双保险）
_BLOCKED_NAME_PARTS = (
    "token",
    "password",
    "passwd",
    "secret",
    "pin",
    "master_key",
    "private",
    "credential_key",
)

# 备份快照目录名（扩展生成，UTC 紧凑 ISO：YYYYMMDDTHHmmssSSSZ）
_SNAPSHOT_DIR_RE = re.compile(r"^\d{8}T\d{9}Z$")
# 备份内容中文标签（与扩展 services/backup-snapshot.ts BACKUP_CONTENT_LABELS 对齐）
_BACKUP_CONTENT_LABELS = {
    "authAccounts": "MoviePilot 账号",
    "totp": "两步验证",
    "credentials": "凭据",
    "ocrCorrections": "OCR 纠错词表",
    "publicSettings": "公共设置",
    "webdavSettings": "WebDAV 备份设置",
    "background": "自定义背景",
    "iconPack": "高清图标包",
    "ocrOfflinePack": "离线 OCR 模型包",
}


class MoviePilotTools(_PluginBase):
    # 插件名称
    plugin_name = "MoviePilot Tools 同步"
    # 插件描述
    plugin_desc = "为 MoviePilot-Tools 扩展提供服务端文件同步与直接下载能力。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/LocalPluginInstall.png"
    # 插件版本
    plugin_version = "1.1.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "moviepilottools_"
    # 加载顺序
    plugin_order = 5
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enabled = False
    _max_file_size = 150 * 1024 * 1024  # 150MB
    _allowed_suffixes: List[str] = list(_DEFAULT_SUFFIXES)
    _direct_download_enabled = False
    _max_torrent_size = 10 * 1024 * 1024  # 10MB

    def init_plugin(self, config: Optional[Dict[str, Any]] = None) -> None:
        """初始化插件配置。"""
        cfg = config or {}
        self._enabled = bool(cfg.get("enabled", False))
        try:
            size_mb = float(cfg.get("max_file_size_mb", 150) or 150)
        except (TypeError, ValueError):
            size_mb = 150
        self._max_file_size = max(1, int(size_mb * 1024 * 1024))

        self._direct_download_enabled = bool(cfg.get("direct_download_enabled", False))
        try:
            torrent_size_mb = float(cfg.get("max_torrent_size_mb", 10) or 10)
        except (TypeError, ValueError):
            torrent_size_mb = 10
        self._max_torrent_size = max(1, int(torrent_size_mb * 1024 * 1024))

        raw_suffix = cfg.get("allowed_suffixes") or ""
        if isinstance(raw_suffix, str) and raw_suffix.strip():
            suffixes = []
            for item in raw_suffix.replace("\n", ",").split(","):
                s = item.strip().lower()
                if not s:
                    continue
                if not s.startswith("."):
                    s = f".{s}"
                suffixes.append(s)
            self._allowed_suffixes = suffixes or list(_DEFAULT_SUFFIXES)
        else:
            self._allowed_suffixes = list(_DEFAULT_SUFFIXES)

        # 确保数据目录存在
        data_path = self.get_data_path()
        logger.info(
            f"{self.plugin_name}: {'已启用' if self._enabled else '未启用'}，"
            f"数据目录={data_path}，单文件上限={self._max_file_size} bytes，"
            f"直接下载={'已启用' if self._direct_download_enabled else '未启用'}，"
            f"种子上限={self._max_torrent_size} bytes"
        )

    def get_state(self) -> bool:
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_page(self) -> List[dict]:
        """拼装备份管理详情页面（列表直接内联展示，不使用弹窗）。"""
        api_token_value = settings.API_TOKEN
        js_safe_api_token = json.dumps(api_token_value)

        load_backup_js = f"""
        (async () => {{
            const container = document.getElementById('mpt2-backup-list');
            const errorAlert = document.getElementById('mpt2-backup-error');
            const successAlert = document.getElementById('mpt2-backup-success');
            if (!container || container.dataset.loaded === '1') return;
            container.dataset.loaded = '1';

            const apiKey = {js_safe_api_token};
            const apiBase = '/api/v1/plugin/MoviePilotTools';

            const formatSize = (size) => {{
                if (size === null || size === undefined) return '-';
                const units = ['B', 'KB', 'MB', 'GB'];
                let value = size;
                let index = 0;
                while (value >= 1024 && index < units.length - 1) {{
                    value /= 1024;
                    index += 1;
                }}
                return `${{value.toFixed(index === 0 ? 0 : 2)}} ${{units[index]}}`;
            }};

            const formatTime = (iso) => {{
                if (!iso) return '-';
                const d = new Date(iso);
                if (Number.isNaN(d.getTime())) return String(iso);
                const pad = (n) => String(n).padStart(2, '0');
                return `${{d.getFullYear()}}-${{pad(d.getMonth() + 1)}}-${{pad(d.getDate())}} ${{pad(d.getHours())}}:${{pad(d.getMinutes())}}`;
            }};

            const contentLabels = (contents) => {{
                if (!contents || !contents.length) return '未识别';
                const labels = {{
                    'authAccounts': 'MoviePilot 账号',
                    'totp': '两步验证',
                    'credentials': '凭据',
                    'ocrCorrections': 'OCR 纠错词表',
                    'publicSettings': '公共设置',
                    'webdavSettings': 'WebDAV 备份设置',
                    'background': '自定义背景',
                    'iconPack': '高清图标包',
                    'ocrOfflinePack': '离线 OCR 模型包'
                }};
                return contents.map((c) => labels[c] || c).join('、');
            }};

            const showConfirm = (message, okText = '确认', color = '#ef4444') => new Promise((resolve) => {{
                const confirmModal = document.getElementById('mpt2-backup-confirm-modal');
                const confirmText = document.getElementById('mpt2-backup-confirm-text');
                const confirmCancelBtn = document.getElementById('mpt2-backup-confirm-cancel');
                const confirmOkBtn = document.getElementById('mpt2-backup-confirm-ok');
                if (!confirmModal || !confirmText || !confirmCancelBtn || !confirmOkBtn) {{
                    resolve(false);
                    return;
                }}
                confirmText.textContent = message;
                confirmOkBtn.textContent = okText;
                confirmOkBtn.style.background = color;
                confirmModal.style.display = 'flex';
                const cleanup = () => {{
                    confirmModal.style.display = 'none';
                    confirmCancelBtn.onclick = null;
                    confirmOkBtn.onclick = null;
                }};
                confirmCancelBtn.onclick = () => {{
                    cleanup();
                    resolve(false);
                }};
                confirmOkBtn.onclick = () => {{
                    cleanup();
                    resolve(true);
                }};
            }});

            const bindEvents = () => {{
                container.querySelectorAll('.mpt2-backup-manifest').forEach((item) => {{
                    item.addEventListener('click', () => {{
                        const modal = document.getElementById('mpt2-backup-files-modal');
                        const list = document.getElementById('mpt2-backup-files-list');
                        const snapshotIdEl = document.getElementById('mpt2-backup-files-snapshot');
                        if (!modal || !list) return;
                        let files = [];
                        try {{
                            files = JSON.parse(decodeURIComponent(item.getAttribute('data-files') || '[]'));
                        }} catch (error) {{
                            files = [];
                        }}
                        if (snapshotIdEl) snapshotIdEl.textContent = item.getAttribute('data-id') || '';
                        list.innerHTML = files.map((file) => {{
                            const name = file.name || '未知';
                            const size = formatSize(file.size);
                            const typeLabel = file.type === 'encrypted' ? '加密数据' : (file.type === 'json' ? 'JSON 元信息' : (file.type || '文件'));
                            const canRestore = name === 'backup.mpt2';
                            const badge = canRestore
                                ? '<span style="display:inline-flex;align-items:center;height:20px;padding:0 8px;border-radius:999px;background:rgba(34,197,94,.12);color:#16a34a;font-size:12px;font-weight:700;line-height:1;">完整备份</span>'
                                : '<span style="display:inline-flex;align-items:center;height:20px;padding:0 8px;border-radius:999px;background:rgba(148,163,184,.15);color:#64748b;font-size:12px;font-weight:700;line-height:1;">元信息</span>';
                            return `
                                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-top:1px solid rgba(128,128,128,.15);">
                                    <div style="min-width:0;flex:1;">
                                        <div style="font-weight:600;word-break:break-all;">${{name}}</div>
                                        <div style="font-size:12px;color:rgba(128,128,128,.9);margin-top:2px;">${{typeLabel}} ｜ 大小：${{size}}</div>
                                    </div>
                                    ${{badge}}
                                </div>
                            `;
                        }}).join('');
                        if (!files.length) {{
                            list.innerHTML = '<div class="text-medium-emphasis" style="padding:16px;text-align:center;">该快照暂无可用的文件清单信息。</div>';
                        }}
                        modal.style.display = 'flex';
                    }});
                }});

                container.querySelectorAll('.mpt2-backup-delete').forEach((item) => {{
                    item.addEventListener('click', async (event) => {{
                        const btn = event.currentTarget;
                        const user = btn.getAttribute('data-user');
                        const id = btn.getAttribute('data-id');
                        const confirmed = await showConfirm(`确认删除用户 ${{user}} 的备份快照 ${{id}} 吗？删除后不可恢复。`, '确认删除', '#ef4444');
                        if (!confirmed) return;
                        btn.disabled = true;
                        const original = btn.textContent;
                        btn.textContent = '删除中...';
                        try {{
                            const response = await fetch(`${{apiBase}}/backup/delete?apikey=${{encodeURIComponent(apiKey)}}`, {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ user: user, id: id }})
                            }});
                            const result = await response.json();
                            if (response.ok && result.code === 200) {{
                                if (successAlert) {{
                                    successAlert.textContent = result.message || '备份快照已删除';
                                    successAlert.style.display = 'block';
                                }}
                                await loadList();
                            }} else {{
                                if (errorAlert) {{
                                    errorAlert.textContent = result.message || '删除失败';
                                    errorAlert.style.display = 'block';
                                }}
                            }}
                        }} catch (error) {{
                            if (errorAlert) {{
                                errorAlert.textContent = '删除失败: ' + error;
                                errorAlert.style.display = 'block';
                            }}
                            console.error('Delete backup error:', error);
                        }} finally {{
                            btn.disabled = false;
                            btn.textContent = original;
                        }}
                    }});
                }});
            }};

            const loadList = async () => {{
                container.innerHTML = '<div class="text-medium-emphasis" style="padding:16px;text-align:center;">正在加载备份快照...</div>';
                try {{
                    const response = await fetch(`${{apiBase}}/backup/list?apikey=${{encodeURIComponent(apiKey)}}`);
                    const result = await response.json();
                    if (!(response.ok && result.code === 200)) {{
                        throw new Error(result.message || '获取备份快照列表失败');
                    }}
                    const data = result.data || {{}};
                    const groups = data.groups || [];
                    if (!groups.length) {{
                        container.innerHTML = '<div class="text-medium-emphasis" style="padding:16px;text-align:center;">暂无备份快照。请先在 MoviePilot-Tools 扩展中执行「MoviePilot 服务端备份」。</div>';
                        return;
                    }}
                    const html = groups.map((group) => {{
                        const rows = (group.snapshots || []).map((snap, index) => {{
                            const latestTag = index === 0 ? '<span style="display:inline-flex;align-items:center;height:22px;padding:0 8px;border-radius:999px;background:rgba(34,197,94,.12);color:#16a34a;font-size:12px;font-weight:700;line-height:1;">最新</span>' : '';
                            const manifestBtn = snap.has_manifest
                                ? `<button type="button" class="mpt2-backup-manifest" data-id="${{snap.id}}" data-files="${{encodeURIComponent(JSON.stringify(snap.files || []))}}" style="border:1px solid rgba(148,163,184,.4);border-radius:8px;padding:5px 14px;background:#fff;color:#475569;cursor:pointer;font-weight:600;font-size:13px;line-height:1.2;">清单</button>`
                                : '';
                            return `
                                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-top:1px solid rgba(128,128,128,.15);flex-wrap:wrap;">
                                    <div style="min-width:260px;flex:1;">
                                        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-weight:600;word-break:break-all;">
                                            <span>${{snap.id}}</span>
                                            ${{latestTag}}
                                        </div>
                                        <div style="font-size:12px;color:rgba(128,128,128,.9);margin-top:4px;">
                                            创建时间：${{formatTime(snap.created_at)}} ｜ 扩展版本：${{snap.app_version || '-'}} ｜ 大小：${{formatSize(snap.size)}}
                                        </div>
                                        <div style="font-size:12px;color:rgba(128,128,128,.9);margin-top:2px;">
                                            内容：${{snap.contents_label}}
                                            ${{snap.key_id ? ` ｜ 密钥 ID：${{snap.key_id}}` : ''}}
                                        </div>
                                    </div>
                                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                                        ${{manifestBtn}}
                                        <button type="button" class="mpt2-backup-delete" data-user="${{snap.user}}" data-id="${{snap.id}}" style="border:1px solid rgba(239,68,68,.32);border-radius:8px;padding:5px 14px;background:#fff;color:#ef4444;cursor:pointer;font-weight:600;font-size:13px;line-height:1.2;">删除</button>
                                    </div>
                                </div>
                            `;
                        }}).join('');
                        return `
                            <details class="mpt2-backup-group" open style="border:1px solid rgba(128,128,128,.2);border-radius:12px;padding:12px 16px;background:rgba(22,177,255,.04);overflow:hidden;">
                                <summary style="cursor:pointer;font-weight:700;outline:none;">用户 ${{group.user}} <span style="color:rgba(128,128,128,.9);font-weight:400;">(${{group.count}} 个快照)</span></summary>
                                <div class="mpt2-backup-scroll" style="margin-top:12px;padding-right:4px;box-sizing:border-box;max-height:300px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:rgba(148,163,184,.5) transparent;">${{rows}}</div>
                            </details>
                        `;
                    }}).join('');
                    container.innerHTML = html;
                    bindEvents();
                }} catch (error) {{
                    container.innerHTML = '<div style="color:#ff5252;padding:16px;text-align:center;">' + error + '</div>';
                    if (errorAlert) {{
                        errorAlert.textContent = '获取备份快照列表失败: ' + error;
                        errorAlert.style.display = 'block';
                    }}
                    console.error('Load backup list error:', error);
                }}
            }};

            try {{
                if (errorAlert) errorAlert.style.display = 'none';
                if (successAlert) successAlert.style.display = 'none';
                await loadList();
            }} catch (error) {{
                if (errorAlert) {{
                    errorAlert.textContent = '加载备份快照列表失败: ' + error;
                    errorAlert.style.display = 'block';
                }}
            }}
        }})()
        """

        page_structure = [
            {
                "component": "VRow",
                "content": [
                    {
                        "component": "VCol",
                        "props": {"cols": 12},
                        "content": [
                            {
                                "component": "VCard",
                                "props": {"variant": "flat", "class": "mb-4"},
                                "content": [
                                    {
                                        "component": "VCardTitle",
                                        "props": {"class": "d-flex align-center"},
                                        "content": [
                                            {
                                                "component": "VIcon",
                                                "props": {"style": "color: #16b1ff;", "class": "mr-2"},
                                                "text": "mdi-backup-restore",
                                            },
                                            {"component": "span", "text": "备份管理"},
                                        ],
                                    },
                                    {"component": "VDivider"},
                                    {
                                        "component": "VCardText",
                                        "content": [
                                            {
                                                "component": "VAlert",
                                                "props": {
                                                    "type": "info",
                                                    "variant": "tonal",
                                                    "density": "comfortable",
                                                    "icon": "mdi-information",
                                                    "class": "mb-4",
                                                },
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-body-2"},
                                                        "text": "备份由 MoviePilot-Tools 扩展加密生成并同步到本插件数据目录（用户名/backups/快照ID/）。服务端仅存储。恢复时在扩展设置中选择 MoviePilot 服务端备份快照即可直接还原。manifest.json 仅为元信息清单，不是完整备份数据。",
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VAlert",
                                                "props": {
                                                    "type": "success",
                                                    "variant": "tonal",
                                                    "class": "mb-2",
                                                    "density": "comfortable",
                                                    "border": "start",
                                                    "icon": "mdi-check-circle",
                                                    "elevation": 1,
                                                    "rounded": "lg",
                                                    "id": "mpt2-backup-success",
                                                    "style": "display: none;",
                                                },
                                                "content": [
                                                    {"component": "div", "props": {"class": "text-body-1"}}
                                                ],
                                            },
                                            {
                                                "component": "VAlert",
                                                "props": {
                                                    "type": "error",
                                                    "variant": "tonal",
                                                    "class": "mb-2",
                                                    "density": "comfortable",
                                                    "border": "start",
                                                    "icon": "mdi-alert",
                                                    "elevation": 1,
                                                    "rounded": "lg",
                                                    "id": "mpt2-backup-error",
                                                    "style": "display: none;",
                                                },
                                                "content": [
                                                    {"component": "div", "props": {"class": "text-body-1"}}
                                                ],
                                            },
                                            # 备份快照列表（直接内联展示，打开页面自动加载）
                                            {
                                                "component": "div",
                                                "props": {
                                                    "id": "mpt2-backup-list",
                                                    "style": "border:1px solid rgba(128,128,128,.2);border-radius:12px;padding:16px;background:rgba(22,177,255,.03);",
                                                },
                                                "content": [
                                                    {
                                                        "component": "div",
                                                        "props": {"class": "text-medium-emphasis"},
                                                        "text": "正在加载备份快照...",
                                                    }
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
            # 深色主题适配
            {
                "component": "style",
                "text": ".mpt2-backup-group .mpt2-backup-scroll::-webkit-scrollbar{width:6px;}.mpt2-backup-group .mpt2-backup-scroll::-webkit-scrollbar-thumb{background:rgba(148,163,184,.5);border-radius:3px;}.mpt2-backup-group .mpt2-backup-scroll::-webkit-scrollbar-track{background:transparent;}.mpt2-backup-group + .mpt2-backup-group{margin-top:12px;}.v-theme--dark .mpt2-backup-group,[data-theme=\"dark\"] .mpt2-backup-group{background:rgba(37,99,235,.12) !important;border-color:rgba(71,85,105,.55) !important;}.v-theme--dark #mpt2-backup-list,[data-theme=\"dark\"] #mpt2-backup-list{border-color:rgba(71,85,105,.55) !important;background:rgba(37,99,235,.08) !important;}.v-theme--dark #mpt2-backup-files-modal,[data-theme=\"dark\"] #mpt2-backup-files-modal{background:rgba(15,23,42,.62) !important;}.v-theme--dark #mpt2-backup-files-card,[data-theme=\"dark\"] #mpt2-backup-files-card{background:#111827 !important;border-color:rgba(71,85,105,.55) !important;box-shadow:0 18px 42px rgba(0,0,0,.45) !important;}.v-theme--dark #mpt2-backup-files-title,[data-theme=\"dark\"] #mpt2-backup-files-title{color:#f9fafb !important;}.v-theme--dark #mpt2-backup-confirm-modal,[data-theme=\"dark\"] #mpt2-backup-confirm-modal{background:rgba(15,23,42,.62) !important;}.v-theme--dark #mpt2-backup-confirm-card,[data-theme=\"dark\"] #mpt2-backup-confirm-card{background:#111827 !important;border-color:rgba(71,85,105,.55) !important;box-shadow:0 18px 42px rgba(0,0,0,.45) !important;}.v-theme--dark #mpt2-backup-confirm-card div,[data-theme=\"dark\"] #mpt2-backup-confirm-card div{color:#f9fafb !important;}.v-theme--dark #mpt2-backup-confirm-cancel,[data-theme=\"dark\"] #mpt2-backup-confirm-cancel{background:#1f2937 !important;color:#e5e7eb !important;border-color:rgba(148,163,184,.3) !important;}.v-theme--dark .mpt2-backup-manifest,[data-theme=\"dark\"] .mpt2-backup-manifest{background:#1f2937 !important;color:#e5e7eb !important;border-color:rgba(148,163,184,.3) !important;}.v-theme--dark .mpt2-backup-delete,[data-theme=\"dark\"] .mpt2-backup-delete{background:#1f2937 !important;color:#ef4444 !important;border-color:rgba(239,68,68,.4) !important;}",
            },
            # 备份文件清单弹窗（内部拟态弹窗）
            {
                "component": "div",
                "props": {
                    "id": "mpt2-backup-files-modal",
                    "onclick": "if (event.target === this) this.style.display='none'",
                    "style": "display:none;position:fixed;inset:0;z-index:3000;background:rgba(15,23,42,.5);align-items:center;justify-content:center;padding:24px;",
                },
                "content": [
                    {
                        "component": "div",
                        "props": {
                            "id": "mpt2-backup-files-card",
                            "style": "width:min(620px,100%);max-height:70vh;background:#ffffff;border:1px solid rgba(226,232,240,1);border-radius:16px;box-shadow:0 12px 32px rgba(15,23,42,.16);overflow:hidden;display:flex;flex-direction:column;",
                        },
                        "content": [
                            {
                                "component": "div",
                                "props": {
                                    "style": "display:flex;align-items:center;justify-content:space-between;padding:16px 22px;border-bottom:1px solid rgba(128,128,128,.18);flex:0 0 auto;",
                                },
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"style": "display:flex;align-items:center;min-width:0;flex:1;"},
                                        "content": [
                                            {
                                                "component": "span",
                                                "props": {"id": "mpt2-backup-files-title", "style": "font-size:17px;font-weight:700;color:#111827;"},
                                                "text": "备份文件清单",
                                            },
                                            {
                                                "component": "span",
                                                "props": {
                                                    "id": "mpt2-backup-files-snapshot",
                                                    "style": "margin-left:10px;font-size:12px;color:rgba(128,128,128,.85);font-weight:500;word-break:break-all;",
                                                },
                                                "text": "",
                                            },
                                        ],
                                    },
                                    {
                                        "component": "button",
                                        "props": {
                                            "type": "button",
                                            "onclick": "this.closest('#mpt2-backup-files-modal').style.display='none'",
                                            "style": "border:none;background:transparent;font-size:24px;line-height:1;cursor:pointer;color:#6b7280;padding:0 4px;",
                                        },
                                        "text": "×",
                                    },
                                ],
                            },
                            {
                                "component": "div",
                                "props": {"style": "padding:16px 22px;overflow-y:auto;flex:1;min-height:0;"},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {
                                            "style": "font-size:12px;line-height:1.6;color:rgba(128,128,128,.9);background:rgba(22,177,255,.07);border:1px solid rgba(22,177,255,.2);border-radius:8px;padding:10px 12px;margin-bottom:12px;",
                                        },
                                        "text": "提示：backup.mpt2 是完整加密备份数据；manifest.json 仅为元信息清单，不是完整备份数据。恢复时在 MoviePilot-Tools 扩展设置中选择 MoviePilot 服务端备份快照直接还原。",
                                    },
                                    {
                                        "component": "div",
                                        "props": {"id": "mpt2-backup-files-list", "style": "min-height:40px;"},
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            # 删除确认弹窗（内部拟态弹窗）
            {
                "component": "div",
                "props": {
                    "id": "mpt2-backup-confirm-modal",
                    "style": "display:none;position:fixed;inset:0;z-index:3002;background:rgba(15,23,42,.5);align-items:center;justify-content:center;padding:24px;",
                },
                "content": [
                    {
                        "component": "div",
                        "props": {
                            "id": "mpt2-backup-confirm-card",
                            "style": "min-width:320px;max-width:min(460px,100%);background:#ffffff;border:1px solid rgba(226,232,240,1);border-radius:16px;box-shadow:0 12px 32px rgba(15,23,42,.18);padding:22px 22px 18px 22px;",
                        },
                        "content": [
                            {
                                "component": "div",
                                "props": {"style": "display:flex;align-items:flex-start;gap:14px;"},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"style": "display:flex;align-items:center;justify-content:center;flex:0 0 auto;width:28px;height:28px;color:#ef4444;font-size:20px;font-weight:700;"},
                                        "content": [
                                            {
                                                "component": "VIcon",
                                                "props": {"color": "#ef4444", "size": "22"},
                                                "text": "mdi-alert",
                                            }
                                        ],
                                    },
                                    {
                                        "component": "div",
                                        "props": {"style": "flex:1;min-width:0;"},
                                        "content": [
                                            {
                                                "component": "div",
                                                "props": {"style": "font-size:16px;font-weight:700;color:#1f2937;margin-bottom:8px;"},
                                                "text": "请确认操作",
                                            },
                                            {
                                                "component": "div",
                                                "props": {
                                                    "id": "mpt2-backup-confirm-text",
                                                    "style": "font-size:14px;line-height:1.6;color:#4b5563;word-break:break-word;",
                                                },
                                                "text": "",
                                            },
                                        ],
                                    },
                                ],
                            },
                            {
                                "component": "div",
                                "props": {"style": "display:flex;justify-content:flex-end;gap:10px;margin-top:18px;"},
                                "content": [
                                    {
                                        "component": "button",
                                        "props": {
                                            "id": "mpt2-backup-confirm-cancel",
                                            "type": "button",
                                            "style": "border:1px solid rgba(148,163,184,.4);border-radius:10px;padding:7px 16px;background:#fff;color:#475569;font-size:13px;line-height:1.2;font-weight:700;cursor:pointer;",
                                        },
                                        "text": "取消",
                                    },
                                    {
                                        "component": "button",
                                        "props": {
                                            "id": "mpt2-backup-confirm-ok",
                                            "type": "button",
                                            "style": "border:none;border-radius:10px;padding:7px 16px;background:#ef4444;color:#fff;font-size:13px;line-height:1.2;font-weight:700;cursor:pointer;",
                                        },
                                        "text": "确认",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            # 自动触发加载的隐藏图片（data URI 立即加载成功触发 onload）
            {
                "component": "img",
                "props": {
                    "src": "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
                    "alt": "",
                    "style": "display:none;width:0;height:0;",
                    "onload": load_backup_js,
                    "onerror": load_backup_js,
                },
            },
        ]
        return page_structure

    def get_service(self) -> List[Dict[str, Any]]:
        return []

    def stop_service(self):
        """无后台任务，无需清理。"""
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册扩展同步 API。
        auth=bear：扩展携带登录 JWT（Authorization: Bearer），亦可回退 API Token。
        最终路径：
          /api/v1/plugin/MoviePilotTools/upload
          /api/v1/plugin/MoviePilotTools/download
          /api/v1/plugin/MoviePilotTools/list
          /api/v1/plugin/MoviePilotTools/delete
          /api/v1/plugin/MoviePilotTools/download/direct
          /api/v1/plugin/MoviePilotTools/health
        """
        return [
            {
                "path": "/upload",
                "endpoint": self.api_upload,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "上传/覆盖同步文件",
                "description": "将扩展数据文件写入插件数据目录，body: {path, content, encoding?}",
            },
            {
                "path": "/upload_chunk",
                "endpoint": self.api_upload_chunk,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "分块上传同步文件",
                "description": "逐块上传并在最后一块原子合并，body: {path, upload_id, index, total, content}",
            },
            {
                "path": "/download",
                "endpoint": self.api_download,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "下载同步文件",
                "description": "从插件数据目录读取文件，query: path=相对路径",
            },
            {
                "path": "/download_chunk",
                "endpoint": self.api_download_chunk,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "分块下载同步文件",
                "description": "按字节偏移读取文件，query: path, offset, size",
            },
            {
                "path": "/list",
                "endpoint": self.api_list,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "列出同步文件",
                "description": "列出数据目录文件，query: prefix=可选子路径",
            },
            {
                "path": "/delete",
                "endpoint": self.api_delete,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "删除同步文件",
                "description": "删除数据目录中的文件，body: {path}",
            },
            {
                "path": "/download/direct",
                "endpoint": self.api_download_direct,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "直接添加下载任务",
                "description": "跳过媒体识别，提交磁力链接或 base64 种子文件到 MoviePilot 下载器",
            },
            {
                "path": "/backup/list",
                "endpoint": self.api_backup_list,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "备份快照列表",
                "description": "按用户分组列出扩展同步的备份快照（解析 manifest.json），query: user=可选用户名",
            },
            {
                "path": "/backup/download",
                "endpoint": self.api_backup_download,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "下载备份快照文件",
                "description": "下载指定快照的 backup.mpt2 或 manifest.json，query: user, id, file",
            },
            {
                "path": "/backup/delete",
                "endpoint": self.api_backup_delete,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "删除备份快照",
                "description": "删除指定用户的备份快照目录，body: {user, id}",
            },
            {
                "path": "/health",
                "endpoint": self.api_health,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "健康检查",
                "description": "检查插件启用状态、数据目录与直接下载能力",
            },
        ]

    # ------------------------------------------------------------------
    # API handlers
    # ------------------------------------------------------------------

    async def api_health(self) -> JSONResponse:
        data_path = self.get_data_path()
        return self._ok(
            {
                "enabled": self.get_state(),
                "data_path": str(data_path),
                "max_file_size": self._max_file_size,
                "allowed_suffixes": self._allowed_suffixes,
                "plugin_version": self.plugin_version,
                "capabilities": {
                    "direct_download": self._direct_download_enabled,
                    "direct_download_types": ["magnet", "torrent"],
                    "max_torrent_size": self._max_torrent_size,
                },
            }
        )

    async def api_download_direct(
        self, payload: Dict[str, Any] = Body(...)
    ) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")
        if not self._direct_download_enabled:
            return self._err(403, "直接下载功能未启用")

        body = payload or {}
        content_type = str(body.get("type") or "").strip().lower()
        content = body.get("content")
        downloader = str(body.get("downloader") or "").strip() or None
        save_path = str(body.get("save_path") or "").strip()
        labels = self._merge_download_labels(body.get("labels") or body.get("label"))

        if content_type not in ("magnet", "torrent"):
            return self._err(400, "type 仅支持 magnet 或 torrent")
        if not isinstance(content, str) or not content.strip():
            return self._err(400, "缺少 content 参数")
        if not save_path:
            return self._err(400, "缺少 save_path，请从 MoviePilot 可用下载路径中选择")

        try:
            download_dir = Path(validate_download_save_path(save_path))
        except (TypeError, ValueError) as e:
            return self._err(400, f"下载保存路径无效: {e}")

        if content_type == "magnet":
            direct_content: str | bytes = content.strip()
            if not re.match(
                r"^magnet:\?[^#]*\bxt=urn:btih:(?:[A-Fa-f0-9]{40}|[A-Za-z2-7]{32})(?:&|$)",
                direct_content,
                re.IGNORECASE,
            ):
                return self._err(400, "磁力链接无效或缺少合法 BTIH")
        else:
            try:
                direct_content = base64.b64decode(content, validate=True)
            except Exception:
                return self._err(400, "种子文件 base64 解码失败")
            if not direct_content:
                return self._err(400, "种子文件内容为空")
            if len(direct_content) > self._max_torrent_size:
                return self._err(
                    413,
                    f"种子文件超过大小限制：{self._max_torrent_size / 1024 / 1024:.1f}MB",
                )
            try:
                torrent = Torrent.from_string(direct_content)  # pyright: ignore[reportArgumentType]
                if not torrent.name:
                    return self._err(400, "种子文件缺少有效名称")
            except Exception as e:
                return self._err(400, f"种子文件格式无效: {e}")

        try:
            result = await asyncio.to_thread(
                DownloadChain().download,
                content=direct_content,
                download_dir=download_dir,
                cookie=None,  # pyright: ignore[reportArgumentType]
                label=labels,
                downloader=downloader,
            )
            if not result:
                return self._err(502, "未找到可用下载器")

            downloader_name, download_id, layout, error_message = result
            if not download_id:
                return self._err(502, error_message or "下载器未返回任务标识")

            logger.info(
                f"{self.plugin_name}: 直接下载任务添加成功 "
                f"type={content_type}, downloader={downloader_name}, id={download_id}"
            )
            return self._ok(
                {
                    "success": True,
                    "download_id": download_id,
                    "downloader": downloader_name,
                    "layout": layout,
                    "save_path": str(download_dir),
                },
                message="任务添加成功",
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 直接下载失败: {e}", exc_info=True)
            return self._err(500, f"直接下载失败: {e}")

    async def api_upload(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        body = payload or {}
        rel_path = str(body.get("path") or "").strip()
        content = body.get("content")
        encoding = str(body.get("encoding") or "utf-8").strip().lower()
        updated_at = body.get("updatedAt") or body.get("updated_at")

        if content is None:
            return self._err(400, "缺少 content 参数")
        if not isinstance(content, str):
            return self._err(400, "content 必须为字符串（文本或 base64）")

        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)

        try:
            if encoding in ("base64", "b64"):
                try:
                    raw = base64.b64decode(content, validate=False)
                except Exception as e:
                    return self._err(400, f"base64 解码失败: {e}")
            else:
                raw = content.encode("utf-8")

            if len(raw) > self._max_file_size:
                return self._err(
                    400,
                    f"文件超过大小限制：{self._max_file_size / 1024 / 1024:.1f}MB",
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            # 原子写：先写临时文件再替换
            tmp = target.with_suffix(target.suffix + f".tmp.{int(time.time() * 1000)}")
            tmp.write_bytes(raw)
            tmp.replace(target)

            # 可选：按客户端 updatedAt 回写 mtime（秒）
            if updated_at is not None:
                try:
                    ts = float(updated_at)
                    # 兼容毫秒时间戳
                    if ts > 1e12:
                        ts = ts / 1000.0
                    import os

                    os.utime(target, (ts, ts))
                except (TypeError, ValueError, OSError):
                    pass

            stat = target.stat()
            logger.info(f"{self.plugin_name}: 上传成功 {rel_path} ({stat.st_size} bytes)")
            return self._ok(
                {
                    "path": self._to_posix(rel_path),
                    "size": stat.st_size,
                    "updatedAt": int(stat.st_mtime * 1000),
                },
                message="上传成功",
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 上传失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"上传失败: {e}")

    async def api_upload_chunk(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        """分块上传：每块独立小请求，最后一块到达后原子合并为目标文件。"""
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        body = payload or {}
        rel_path = str(body.get("path") or "").strip()
        upload_id = str(body.get("upload_id") or "").strip()
        content = body.get("content")
        updated_at = body.get("updatedAt") or body.get("updated_at")
        raw_index = body.get("index")
        raw_total = body.get("total")
        if raw_index is None or raw_total is None:
            return self._err(400, "缺少 index/total 参数")
        try:
            index = int(raw_index)
            total = int(raw_total)
        except (TypeError, ValueError):
            return self._err(400, "index/total 必须为整数")

        if not upload_id or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", upload_id):
            return self._err(400, "upload_id 无效")
        if not isinstance(content, str):
            return self._err(400, "content 必须为 base64 字符串")
        if total < 1 or index < 0 or index >= total or total > 10000:
            return self._err(400, "分块序号无效")

        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)

        try:
            raw = base64.b64decode(content, validate=False)
            if len(raw) > min(self._max_file_size, 1024 * 1024):
                return self._err(400, "单个分块不能超过 1MB")

            chunk_dir = self.get_data_path() / ".chunks" / upload_id
            chunk_dir.mkdir(parents=True, exist_ok=True)
            meta_file = chunk_dir / "meta.txt"
            expected_meta = f"{self._to_posix(rel_path)}\n{total}"
            if meta_file.exists() and meta_file.read_text("utf-8") != expected_meta:
                return self._err(409, "upload_id 已被其他上传任务占用")
            meta_file.write_text(expected_meta, encoding="utf-8")
            (chunk_dir / f"{index:06d}.part").write_bytes(raw)

            parts = [chunk_dir / f"{i:06d}.part" for i in range(total)]
            if not all(part.exists() for part in parts):
                return self._ok({"path": self._to_posix(rel_path), "index": index, "total": total})

            size = sum(part.stat().st_size for part in parts)
            if size > self._max_file_size:
                self._remove_tree(chunk_dir)
                return self._err(
                    400,
                    f"文件超过大小限制：{self._max_file_size / 1024 / 1024:.1f}MB",
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + f".tmp.{int(time.time() * 1000)}")
            with tmp.open("wb") as output:
                for part in parts:
                    with part.open("rb") as source:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            output.write(block)
            tmp.replace(target)
            self._remove_tree(chunk_dir)

            if updated_at is not None:
                try:
                    import os
                    ts = float(updated_at)
                    if ts > 1e12:
                        ts = ts / 1000.0
                    os.utime(target, (ts, ts))
                except (TypeError, ValueError, OSError):
                    pass

            stat = target.stat()
            logger.info(f"{self.plugin_name}: 分块上传成功 {rel_path} ({stat.st_size} bytes)")
            return self._ok(
                {
                    "path": self._to_posix(rel_path),
                    "size": stat.st_size,
                    "updatedAt": int(stat.st_mtime * 1000),
                    "completed": True,
                },
                message="上传成功",
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 分块上传失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"分块上传失败: {e}")

    async def api_download(
        self,
        path: str = Query(..., description="相对路径，如 user/settings.json"),
        encoding: str = Query("utf-8", description="utf-8 或 base64"),
    ) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        rel_path = unquote(str(path or "").strip())
        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)

        if not target.exists() or not target.is_file():
            return self._err(404, "文件不存在")

        try:
            raw = target.read_bytes()
            enc = (encoding or "utf-8").strip().lower()
            if enc in ("base64", "b64"):
                content = base64.b64encode(raw).decode("ascii")
                content_encoding = "base64"
            else:
                # 文本优先 utf-8，失败回退 latin-1 保真
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    content = base64.b64encode(raw).decode("ascii")
                    content_encoding = "base64"
                else:
                    content_encoding = "utf-8"

            stat = target.stat()
            # 顶层 content 字段兼容扩展 core/mp-backend.ts 的 res.data?.content
            return JSONResponse(
                status_code=200,
                content={
                    "code": 200,
                    "message": "ok",
                    "content": content,
                    "encoding": content_encoding,
                    "path": self._to_posix(rel_path),
                    "size": stat.st_size,
                    "updatedAt": int(stat.st_mtime * 1000),
                    "data": {
                        "content": content,
                        "encoding": content_encoding,
                        "path": self._to_posix(rel_path),
                        "size": stat.st_size,
                        "updatedAt": int(stat.st_mtime * 1000),
                    },
                },
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 下载失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"下载失败: {e}")

    async def api_download_chunk(
        self,
        path: str = Query(..., description="相对路径"),
        offset: int = Query(0, ge=0, description="字节偏移"),
        size: int = Query(256 * 1024, ge=1, le=1024 * 1024, description="读取字节数"),
    ) -> JSONResponse:
        """分块下载：避免大文件响应体触发代理限制。"""
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        rel_path = unquote(str(path or "").strip())
        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)
        if not target.exists() or not target.is_file():
            return self._err(404, "文件不存在")

        try:
            total = target.stat().st_size
            with target.open("rb") as file:
                file.seek(min(offset, total))
                raw = file.read(size)
            next_offset = min(offset + len(raw), total)
            return self._ok(
                {
                    "path": self._to_posix(rel_path),
                    "content": base64.b64encode(raw).decode("ascii"),
                    "offset": offset,
                    "next_offset": next_offset,
                    "total": total,
                    "done": next_offset >= total,
                }
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 分块下载失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"分块下载失败: {e}")

    async def api_list(
        self,
        prefix: str = Query("", description="可选子目录前缀，如 username"),
    ) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        base = self.get_data_path()
        prefix = unquote(str(prefix or "").strip()).lstrip("/").replace("\\", "/")

        if prefix:
            ok, root, message = self._resolve_safe_path(prefix, allow_dir=True)
            if not ok or root is None:
                return self._err(400, message)
        else:
            root = base

        if not root.exists():
            return self._ok({"files": [], "prefix": prefix})

        files: List[Dict[str, Any]] = []
        try:
            if root.is_file():
                rel = root.relative_to(base).as_posix()
                stat = root.stat()
                files.append(
                    {
                        "path": rel,
                        "size": stat.st_size,
                        "updatedAt": int(stat.st_mtime * 1000),
                        "is_dir": False,
                    }
                )
            else:
                for p in sorted(root.rglob("*")):
                    if not p.is_file():
                        continue
                    # 跳过临时文件
                    if ".tmp." in p.name:
                        continue
                    try:
                        rel = p.relative_to(base).as_posix()
                        stat = p.stat()
                        files.append(
                            {
                                "path": rel,
                                "size": stat.st_size,
                                "updatedAt": int(stat.st_mtime * 1000),
                                "is_dir": False,
                            }
                        )
                    except ValueError:
                        continue
            return self._ok({"files": files, "prefix": prefix, "count": len(files)})
        except Exception as e:
            logger.error(f"{self.plugin_name}: 列表失败: {e}", exc_info=True)
            return self._err(500, f"列表失败: {e}")

    async def api_delete(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")

        rel_path = str((payload or {}).get("path") or "").strip()
        ok, target, message = self._resolve_safe_path(rel_path)
        if not ok or target is None:
            return self._err(400, message)

        if not target.exists():
            return self._err(404, "文件不存在")
        if not target.is_file():
            return self._err(400, "仅支持删除文件")

        try:
            target.unlink()
            # 清理空父目录（不越过数据根）
            self._cleanup_empty_parents(target.parent)
            logger.info(f"{self.plugin_name}: 已删除 {rel_path}")
            return self._ok({"path": self._to_posix(rel_path)}, message="删除成功")
        except Exception as e:
            logger.error(f"{self.plugin_name}: 删除失败 {rel_path}: {e}", exc_info=True)
            return self._err(500, f"删除失败: {e}")

    async def api_backup_list(
        self,
        user: str = Query("", description="可选用户名，留空返回全部"),
    ) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")
        try:
            groups = self._list_backup_snapshots(str(user or "").strip() or None)
            return self._ok({"groups": groups, "count": sum(g["count"] for g in groups)})
        except Exception as e:
            logger.error(f"{self.plugin_name}: 备份快照列表失败: {e}", exc_info=True)
            return self._err(500, f"备份快照列表失败: {e}")

    async def api_backup_download(
        self,
        user: str = Query(..., description="用户名"),
        id: str = Query(..., description="快照 ID，如 20260815T000000000Z"),
        file: str = Query("backup.mpt2", description="文件名：backup.mpt2 或 manifest.json"),
    ) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")
        user_name = unquote(str(user or "")).strip()
        snapshot_id = unquote(str(id or "")).strip()
        file_name = str(file or "").strip()
        if not _SAFE_PATH_RE.match(user_name) or not _SNAPSHOT_DIR_RE.match(snapshot_id):
            return self._err(400, "user/id 参数无效")
        if file_name not in ("backup.mpt2", "manifest.json"):
            return self._err(400, "file 仅支持 backup.mpt2 或 manifest.json")

        base = self.get_data_path()
        target = (base / user_name / "backups" / snapshot_id / file_name).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            return self._err(400, "路径越界，拒绝访问")
        if not target.exists() or not target.is_file():
            return self._err(404, "文件不存在")

        try:
            raw = target.read_bytes()
            stat = target.stat()
            return self._ok(
                {
                    "content": base64.b64encode(raw).decode("ascii"),
                    "encoding": "base64",
                    "size": stat.st_size,
                    "filename": file_name,
                    "user": user_name,
                    "snapshot": snapshot_id,
                    "updatedAt": int(stat.st_mtime * 1000),
                }
            )
        except Exception as e:
            logger.error(f"{self.plugin_name}: 下载备份文件失败 {target}: {e}", exc_info=True)
            return self._err(500, f"下载失败: {e}")

    async def api_backup_delete(self, payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        if not self.get_state():
            return self._err(403, "插件未启用，请在插件设置中启用后重试")
        body = payload or {}
        user_name = str(body.get("user") or "").strip()
        snapshot_id = str(body.get("id") or "").strip()
        if not user_name or not snapshot_id:
            return self._err(400, "缺少 user 或 id 参数")
        if not _SAFE_PATH_RE.match(user_name) or not _SNAPSHOT_DIR_RE.match(snapshot_id):
            return self._err(400, "user/id 参数无效")

        base = self.get_data_path()
        folder = (base / user_name / "backups" / snapshot_id).resolve()
        try:
            folder.relative_to(base)
        except ValueError:
            return self._err(400, "路径越界，拒绝访问")
        if not folder.is_dir():
            return self._err(404, "备份快照不存在")

        try:
            self._remove_tree(folder)
            self._cleanup_empty_parents(folder.parent)
            logger.info(f"{self.plugin_name}: 已删除备份快照 {user_name}/{snapshot_id}")
            return self._ok({"user": user_name, "id": snapshot_id}, message="备份快照已删除")
        except Exception as e:
            logger.error(
                f"{self.plugin_name}: 删除备份快照失败 {user_name}/{snapshot_id}: {e}", exc_info=True
            )
            return self._err(500, f"删除备份快照失败: {e}")

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _list_user_dirs(self) -> List[str]:
        """列出插件数据根目录下的一级用户目录（跳过内部临时目录）。"""
        base = self.get_data_path()
        if not base.is_dir():
            return []
        ignored = {".chunks", "backups"}
        return sorted(
            (p.name for p in base.iterdir() if p.is_dir() and p.name not in ignored),
            key=str.lower,
        )

    def _list_backup_snapshots(
        self, user: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """按用户分组返回备份快照列表（解析 manifest.json 提取元信息）。"""
        groups: List[Dict[str, Any]] = []
        for u in self._list_user_dirs():
            if user and u != user:
                continue
            snapshot_root = self.get_data_path() / u / "backups"
            if not snapshot_root.is_dir():
                continue
            items: List[Dict[str, Any]] = []
            folders = [
                p
                for p in snapshot_root.iterdir()
                if p.is_dir() and _SNAPSHOT_DIR_RE.match(p.name)
            ]
            # 快照 ID 为 UTC 紧凑时间，字典序即时间序（新在前）
            for folder in sorted(folders, key=lambda p: p.name, reverse=True):
                backup_path = folder / "backup.mpt2"
                if not backup_path.is_file():
                    continue
                manifest: Optional[Dict[str, Any]] = None
                manifest_path = folder / "manifest.json"
                if manifest_path.is_file():
                    try:
                        parsed = json.loads(manifest_path.read_text("utf-8"))
                        if (
                            isinstance(parsed, dict)
                            and parsed.get("format") == "mpt2-backup-manifest"
                            and parsed.get("id") == folder.name
                        ):
                            manifest = parsed
                    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                        manifest = None
                contents = manifest.get("contents", []) if manifest else []
                label_parts: List[str] = []
                for c in contents:
                    c = str(c)
                    label_parts.append(_BACKUP_CONTENT_LABELS.get(c, c))
                contents_label = "、".join(label_parts) if label_parts else "未识别"
                size = backup_path.stat().st_size
                # 完整文件列表：扫描快照目录内的实际文件（含 backup.mpt2 与 manifest.json）
                files: List[Dict[str, Any]] = []
                try:
                    for f in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
                        if not f.is_file() or ".tmp." in f.name:
                            continue
                        ftype = (
                            "encrypted"
                            if f.name == "backup.mpt2"
                            else "json"
                            if f.name == "manifest.json"
                            else "file"
                        )
                        files.append({"name": f.name, "type": ftype, "size": f.stat().st_size})
                except OSError:
                    files = []
                if not files:
                    files = [{"name": "backup.mpt2", "type": "encrypted", "size": size}]
                items.append(
                    {
                        "user": u,
                        "id": folder.name,
                        "created_at": manifest.get("createdAt") if manifest else None,
                        "app_version": manifest.get("appVersion") if manifest else None,
                        "key_id": manifest.get("keyId") if manifest else None,
                        "size": size,
                        "contents": contents,
                        "contents_label": contents_label,
                        "has_manifest": manifest is not None,
                        "files": files,
                    }
                )
            if items:
                groups.append({"user": u, "count": len(items), "snapshots": items})
        return groups

    @staticmethod
    def _merge_download_labels(labels: Any) -> Optional[str]:
        if isinstance(labels, list):
            items = [str(item).strip() for item in labels if str(item).strip()]
        else:
            items = [
                item.strip()
                for item in str(labels or "").replace("\n", ",").split(",")
                if item.strip()
            ]
        system_tag = str(settings.TORRENT_TAG or "").strip()
        if system_tag and system_tag not in items:
            items.append(system_tag)
        return ",".join(dict.fromkeys(items)) if items else None

    def _resolve_safe_path(
        self, rel_path: str, allow_dir: bool = False
    ) -> Tuple[bool, Optional[Path], str]:
        """
        将相对路径解析到插件数据目录内，防目录穿越。
        返回 (ok, absolute_path, error_message)
        """
        if not rel_path:
            return False, None, "缺少 path 参数"

        # 统一分隔符、去掉前导 /
        cleaned = unquote(rel_path).replace("\\", "/").strip()
        cleaned = cleaned.lstrip("/")
        if not cleaned:
            return False, None, "path 无效"
        if cleaned.startswith("..") or "/../" in f"/{cleaned}/" or cleaned.endswith("/.."):
            return False, None, "path 不允许包含 .."
        if cleaned.startswith("~") or ":" in cleaned.split("/")[0]:
            return False, None, "path 不允许为绝对路径"
        if not _SAFE_PATH_RE.match(cleaned):
            return False, None, "path 含非法字符，仅允许字母数字 _ - . /"

        # 敏感名拦截
        lower_parts = [p.lower() for p in cleaned.split("/") if p]
        for part in lower_parts:
            for blocked in _BLOCKED_NAME_PARTS:
                if blocked in part:
                    return False, None, f"禁止同步敏感路径片段: {part}"

        base = self.get_data_path().resolve()
        target = (base / cleaned).resolve()

        # 必须在 base 内
        try:
            target.relative_to(base)
        except ValueError:
            return False, None, "path 越界，拒绝访问"

        if not allow_dir:
            # 文件必须有后缀，且在白名单
            suffix = target.suffix.lower()
            if not suffix:
                return False, None, "path 必须包含合法文件后缀"
            if suffix not in self._allowed_suffixes:
                return False, None, f"不支持的文件类型: {suffix}"

        return True, target, ""

    @staticmethod
    def _remove_tree(directory: Path) -> None:
        if not directory.exists():
            return
        for path in sorted(directory.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        directory.rmdir()

    def _cleanup_empty_parents(self, directory: Path) -> None:
        base = self.get_data_path().resolve()
        try:
            current = directory.resolve()
            while current != base and base in current.parents:
                if current.exists() and current.is_dir() and not any(current.iterdir()):
                    current.rmdir()
                    current = current.parent
                else:
                    break
        except Exception:
            pass

    @staticmethod
    def _to_posix(path: str) -> str:
        return str(path or "").replace("\\", "/").lstrip("/")

    @staticmethod
    def _ok(data: Any = None, message: str = "ok") -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"code": 200, "message": message, "data": data},
        )

    @staticmethod
    def _err(code: int, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={"code": code, "message": message, "data": None},
        )

    # ------------------------------------------------------------------
    # 配置页
    # ------------------------------------------------------------------

    def get_form(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """拼装插件配置页面。"""
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VCard",
                        "props": {"variant": "flat", "class": "mb-4"},
                        "content": [
                            {
                                "component": "VCardTitle",
                                "props": {"class": "d-flex align-center"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "style": "color: #16b1ff;",
                                            "class": "mr-2",
                                        },
                                        "text": "mdi-cloud-sync",
                                    },
                                    {"component": "span", "text": "基本设置"},
                                ],
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "enabled",
                                                            "label": "启用插件",
                                                            "color": "primary",
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "max_file_size_mb",
                                                            "label": "单文件上限(MB)",
                                                            "type": "number",
                                                            "min": 1,
                                                            "hint": "默认 150MB，覆盖浏览器扩展完整备份",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "allowed_suffixes",
                                                        "label": "允许后缀(逗号分隔)",
                                                        "hint": "留空使用默认：mpt2,json",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VCard",
                        "props": {"variant": "flat", "class": "mb-4"},
                        "content": [
                            {
                                "component": "VCardTitle",
                                "props": {"class": "d-flex align-center"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "style": "color: #16b1ff;",
                                            "class": "mr-2",
                                        },
                                        "text": "mdi-download-network-outline",
                                    },
                                    {"component": "span", "text": "直接下载设置"},
                                ],
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": "direct_download_enabled",
                                                            "label": "允许直接下载",
                                                            "color": "primary",
                                                            "hint": "跳过媒体识别提交磁力或种子任务",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "md": 6},
                                                "content": [
                                                    {
                                                        "component": "VTextField",
                                                        "props": {
                                                            "model": "max_torrent_size_mb",
                                                            "label": "种子大小上限(MB)",
                                                            "type": "number",
                                                            "min": 1,
                                                            "hint": "仅限制直接上传的 .torrent 文件；保存路径由扩展从 MoviePilot 可用路径中提交",
                                                            "persistent-hint": True,
                                                        },
                                                    }
                                                ],
                                            },
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VCard",
                        "props": {"variant": "flat", "class": "mb-4"},
                        "content": [
                            {
                                "component": "VCardTitle",
                                "props": {"class": "d-flex align-center"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {
                                            "style": "color: #16b1ff;",
                                            "class": "mr-2",
                                        },
                                        "text": "mdi-information-outline",
                                    },
                                    {"component": "span", "text": "使用说明"},
                                ],
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "text-body-2"},
                                        "content": [
                                            {
                                                "component": "p",
                                                "text": "📦 本插件为 MoviePilot-Tools 浏览器扩展提供「服务端文件同步」能力。"
                                                        "数据以文件形式落在插件数据目录。",
                                            },
                                            {
                                                "component": "p",
                                                "props": {"class": "mt-2"},
                                                "text": "🔌 插件暴露 API 接口：",
                                            },
                                            {
                                                "component": "ul",
                                                "props": {"class": "ml-4"},
                                                "content": [
                                                    {
                                                        "component": "li",
                                                        "text": "⬆️ 上传：POST /api/v1/plugin/MoviePilotTools/upload  body: {path, content, encoding?}",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "⬇️ 下载：GET  /api/v1/plugin/MoviePilotTools/download?path=user/backup.mpt2",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "📂 列表：GET  /api/v1/plugin/MoviePilotTools/list?prefix=user",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "🗑️ 删除：POST /api/v1/plugin/MoviePilotTools/delete  body: {path}",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "🧲 直接下载：POST /api/v1/plugin/MoviePilotTools/download/direct",
                                                    },
                                                    {
                                                        "component": "li",
                                                        "text": "💓 健康检查：GET  /api/v1/plugin/MoviePilotTools/health",
                                                    },
                                                ],
                                            },
                                            {
                                                "component": "p",
                                                "props": {"class": "mt-2"},
                                                "text": "🗃️ 备份仅生成两个文件：加密主文件 backup.mpt2 与清单 manifest.json，"
                                                        "按用户隔离存放于插件目录，真实路径如 "
                                                        "/config/plugins/MoviePilotTools/{username}/backups/{snapshot}。"
                                            },
                                            {
                                                "component": "p",
                                                "props": {"class": "mt-2"},
                                                "text": "⚙️ 上传限制：单文件默认 ≤ 150MB；允许后缀默认仅 .mpt2 / .json"
                                                        "（可在本页「单文件上限」与「允许后缀」中调整）。",
                                            },
                                            {
                                                "component": "p",
                                                "props": {"class": "mt-2"},
                                                "text": "🔒 Token / PIN / 密钥等敏感项由扩展本地加密存储，永不同步到本插件。",
                                            },
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            }
        ], {
            "enabled": False,
            "max_file_size_mb": 150,
            "allowed_suffixes": "",
            "direct_download_enabled": False,
            "max_torrent_size_mb": 10,
        }
