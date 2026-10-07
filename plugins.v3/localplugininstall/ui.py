"""本地插件安装的配置表单与数据页面（Vuetify JSON）"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

# 宿主前端客户端的请求适配器：把统一 envelope 归一为原页面使用的 code/message/data
_REQUEST_SHIM = """
                    async (path, body) => {
                        const api = window.MoviePilotAPI;
                        if (!api) {
                            return { ok: false, body: { code: 500, message: '未获取到宿主前端客户端，请刷新页面后重试' } };
                        }
                        try {
                            const payload = body
                                ? await api.post('plugin/__PLUGIN_ID__' + path, body)
                                : await api.get('plugin/__PLUGIN_ID__' + path);
                            const ok = !!(payload && payload.success);
                            return {
                                ok: ok,
                                body: {
                                    code: ok ? 200 : 500,
                                    message: (payload && payload.message) || '',
                                    data: payload && payload.data,
                                },
                            };
                        } catch (error) {
                            return { ok: false, body: { code: 500, message: (error && error.message) || '请求失败' } };
                        }
                    }
"""


class _PageConfig(dict):
    """页面配置容器：get 返回具体值，保持正文里的取值写法不出现可选类型。"""

    def get(self, key: Any, default: Any = None) -> Any:
        """
        读取配置项。

        :param key: 配置名
        :param default: 缺省值
        :return: 配置值
        """
        return super().get(key, default)


class PluginUI:
    """插件配置表单与数据页面，保持与 V2 版相同的外观和交互。"""

    def __init__(self, data_path: Path, max_file_size: int = 20 * 1024 * 1024) -> None:
        """
        保存页面渲染需要的插件配置。

        :param data_path: 当前插件实例的数据目录
        :param max_file_size: 上传体积上限（字节），用于页面内预检
        """
        self._data_path = data_path
        self._config: _PageConfig = _PageConfig(max_file_size=max_file_size)

    def get_data_path(self) -> Path:
        """
        返回插件数据目录，保持原表单文案中的路径展示一致。

        :return: 插件数据目录
        """
        return self._data_path

    def _request_shim(self, plugin_id: str) -> str:
        """
        返回绑定实例 ID 的请求助手源码。

        :param plugin_id: 运行期插件 ID
        :return: JavaScript 源码
        """
        return _REQUEST_SHIM.replace("__PLUGIN_ID__", plugin_id)


    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """拼装插件配置页面"""
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
                                'props': {'class': 'px-6 pb-0'},
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {'class': 'd-flex align-center text-h6'},
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
                                'props': {'class': 'mx-4 my-2'}
                            },
                            {
                                'component': 'VCardText',
                                'props': {'class': 'px-6 pb-6'},
                                'content': [
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 4},
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
                                                'props': {'cols': 12, 'sm': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'backup_enabled',
                                                            'label': '安装时启用备份',
                                                            'color': 'info',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 4},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'backup_retention',
                                                            'label': '备份保留份数(默认10)',
                                                            'type': 'number',
                                                            'min': 1,
                                                            'step': 1,
                                                            'active': True,
                                                            'persistent-hint': True,
                                                            'placeholder': '默认保留10份'
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
                                                'props': {'cols': 12},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'local_repo_path',
                                                            'label': '本地插件仓库路径',
                                                            'active': True,
                                                            'persistent-hint': True,
                                                            'prepend-inner-icon': 'mdi-folder',
                                                            'placeholder': '留空则使用配置目录下的 plugin-repo',
                                                            'hint': '插件包会写入该目录并按宿主的本地插件仓库布局登记，安装后由宿主建立本地来源'
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
                                'props': {'class': 'px-6 pb-0'},
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {'class': 'd-flex align-center text-h6 mb-0'},
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
                                                'text': '备份说明'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider',
                                'props': {'class': 'mx-4 my-2'}
                            },
                            {
                                'component': 'VCardText',
                                'props': {'class': 'px-6 py-0'},
                                'content': [
                                    {
                                        'component': 'VList',
                                        'props': {
                                            'lines': 'two',
                                            'density': 'comfortable'
                                        }
                                        ,
                                        'content': [
                                            {
                                                'component': 'VListItem',
                                                'props': {'lines': 'two'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-items-start'},
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'primary',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-folder-zip'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '备份保存位置'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': f"备份压缩包统一保存到目录：{self.get_data_path() / 'backups'}"
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {'lines': 'two'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-items-start'},
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'success',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-archive-arrow-down'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '备份命名规则'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '备份文件名格式为“插件目录名_YYYY.MM.DD_HH-MM-SS.zip”，压缩包内部目录名保持为原插件目录名。'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {'lines': 'two'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-items-start'},
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'warning',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-broom'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '自动清理规则'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '备份时会自动跳过 __pycache__ 目录，并在超过保留份数后删除最旧的同名插件备份压缩包。'
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VListItem',
                                                'props': {'lines': 'two'},
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'd-flex align-items-start'},
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'error',
                                                                    'class': 'mt-1 mr-2'
                                                                },
                                                                'text': 'mdi-archive-refresh'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '安装失败自动回滚'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '如果新插件安装过程中发生异常，系统会自动使用刚生成的备份压缩包回滚恢复原有插件目录。'
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                ]
            }
        ], {
            "enabled": True,
            "backup_enabled": True,
            "backup_retention": 10,
            "local_repo_path": ""
        }

    def get_page(self, plugin_id: str) -> List[dict]:
        """拼装插件详情页面"""
        request_shim = self._request_shim(plugin_id)

        # 构建上传插件的JavaScript代码
        onclick_js = f"""
        (async (button) => {{
            const request = {request_shim};
            const fileInput = document.querySelector('#localupload-file-input');
            const noticeModal = document.getElementById('localupload-notice-modal');
            const noticeText = document.getElementById('localupload-notice-text');
            const showNotice = (message) => {{
                if (noticeText) noticeText.textContent = message;
                if (noticeModal) noticeModal.style.display = 'flex';
            }};
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {{
                showNotice('请先选择一个ZIP文件！');
                return;
            }}
            const file = fileInput.files[0];
            const maxSize = {self._config.get('max_file_size', 20*1024*1024)};
            if (file.size > maxSize) {{
                 showNotice(`文件大小超过限制 (${{(maxSize / 1024 / 1024).toFixed(1)}}MB)`);
                 return;
            }}

            const formData = new FormData();
            formData.append('file', file);
            button.disabled = true;
            const originalText = button.textContent;
            button.textContent = '安装中...';
            const errorAlert = document.getElementById('localupload-error-alert');
            const successAlert = document.getElementById('localupload-success-alert');
            if (errorAlert) errorAlert.style.display = 'none';
            if (successAlert) successAlert.style.display = 'none';

            try {{
                const response = await request('/localupload', formData);
                const result = response.body;
                if (response.ok && result.code === 200) {{
                    if (successAlert) {{
                        let successMessage = result.data?.plugin_display_name || result.message || '插件安装成功！';
                        successMessage = `插件 "${{successMessage}}" 已成功安装到系统。请刷新页面在插件管理页面手动启用。`;
                        
                        if (result.data && result.data.dependencies) {{
                            const deps = result.data.dependencies;
                            if (deps.total_count > 0) {{
                                successMessage += '<br><br><strong>依赖安装详情：</strong>';
                                successMessage += '<br>• 总依赖数量：' + deps.total_count + ' 个';
                                successMessage += '<br>• 成功安装：' + deps.success_count + ' 个';
                                successMessage += '<br>• 安装失败：' + deps.failed_count + ' 个';
                                successMessage += '<br>• 安装状态：' + (deps.status === 'success' ? '✅ 成功' : '❌ 失败');
                                if (deps.message) {{
                                    successMessage += '<br>• 详细信息：' + deps.message;
                                }}
                                if (deps.details && deps.details.length > 0) {{
                                    const lastDetail = deps.details[deps.details.length - 1];
                                    if (lastDetail.installed_packages && lastDetail.installed_packages.length > 0) {{
                                        successMessage += '<br>• 已安装包：' + lastDetail.installed_packages.join(', ');
                                    }}
                                }}
                            }} else {{
                                successMessage += '<br><br><strong>依赖安装：</strong>无需安装依赖';
                            }}
                        }}
                        successAlert.innerHTML = successMessage;
                        successAlert.style.whiteSpace = 'pre-line';
                        successAlert.style.display = 'block';
                    }} else {{
                        alert('成功: ' + (result.message || '插件安装成功！'));
                    }}
                    if (fileInput) fileInput.value = '';
                }} else if (response.status === 429) {{
                    const errorMsg = result.message || '检测到其他插件正在安装中，请等待当前安装完成后再试';
                    if (errorAlert) {{
                        errorAlert.innerHTML = errorMsg;
                        errorAlert.style.display = 'block';
                    }} else {{
                        alert('提示: ' + errorMsg);
                    }}
                }} else {{
                    const errorMsg = result.message || '安装失败，状态码: ' + response.status;
                    if (errorAlert) {{
                        let errorMessage = errorMsg;
                        if (result.data && result.data.dependencies) {{
                            const deps = result.data.dependencies;
                            errorMessage += '<br><br><strong>依赖安装详情：</strong>';
                            if (deps.total_count > 0) {{
                                errorMessage += '<br>• 总依赖数量：' + deps.total_count + ' 个';
                                errorMessage += '<br>• 成功安装：' + deps.success_count + ' 个';
                                errorMessage += '<br>• 安装失败：' + deps.failed_count + ' 个';
                                errorMessage += '<br>• 安装状态：' + (deps.status === 'success' ? '✅ 成功' : '❌ 失败');
                            }} else {{
                                errorMessage += '<br>• 无需安装依赖';
                            }}
                            if (deps.message) {{
                                errorMessage += '<br>• 详细信息：' + deps.message;
                            }}
                        }}
                        errorAlert.innerHTML = errorMessage;
                        errorAlert.style.whiteSpace = 'pre-line';
                        errorAlert.style.display = 'block';
                    }} else {{
                        alert('失败: ' + errorMsg);
                    }}
                }}

            }} catch (error) {{
                const errorMsg = '请求发送失败: ' + error;
                if (errorAlert) {{
                    errorAlert.textContent = errorMsg;
                    errorAlert.style.display = 'block';
                }} else {{
                    alert(errorMsg);
                }}
                console.error("Fetch error:", error);

            }} finally {{
                button.disabled = false;
                button.textContent = originalText;
            }}
        }})(this)
        """

        restore_onclick_js = f"""
        (async (button) => {{
            const request = {request_shim};
            const errorAlert = document.getElementById('localupload-error-alert');
            const successAlert = document.getElementById('localupload-success-alert');
            const modal = document.getElementById('localupload-backup-modal');
            const backupContainer = document.getElementById('localupload-backup-list-container');
            const confirmModal = document.getElementById('localupload-confirm-modal');
            const confirmText = document.getElementById('localupload-confirm-text');
            const confirmIconWrap = document.getElementById('localupload-confirm-icon-wrap');
            const confirmCancelBtn = document.getElementById('localupload-confirm-cancel');
            const confirmOkBtn = document.getElementById('localupload-confirm-ok');
            const confirmIconPathMap = {{
                'mdi-alert': 'M13 14H11V9H13M13 18H11V16H13M1 21H23L12 2L1 21Z',
                'mdi-delete-alert': 'M9 3V4H4V6H5V19A2 2 0 0 0 7 21H17A2 2 0 0 0 19 19V6H20V4H15V3H9M7 6H17V19H7V6M9 8V17H11V8H9M13 8V17H15V8H13Z',
                'mdi-backup-restore': 'M12 3A9 9 0 0 0 3 12H0L4 16L8 12H5A7 7 0 1 1 12 19C10.39 19 8.9 18.45 7.72 17.53L6.29 18.96A8.96 8.96 0 0 0 12 21A9 9 0 0 0 12 3Z'
            }};
            const renderConfirmIcon = (iconName, iconColor) => {{
                if (!confirmIconWrap) {{
                    return;
                }}

                confirmIconWrap.replaceChildren();
                confirmIconWrap.style.color = iconColor;

                const svgNs = 'http://www.w3.org/2000/svg';
                const svg = document.createElementNS(svgNs, 'svg');
                svg.setAttribute('viewBox', '0 0 24 24');
                svg.setAttribute('width', '22');
                svg.setAttribute('height', '22');
                svg.setAttribute('fill', 'currentColor');
                svg.setAttribute('aria-hidden', 'true');

                const path = document.createElementNS(svgNs, 'path');
                path.setAttribute('d', confirmIconPathMap[iconName] || confirmIconPathMap['mdi-alert']);
                svg.appendChild(path);
                confirmIconWrap.appendChild(svg);
            }};
            const closeModal = () => {{
                if (modal) modal.style.display = 'none';
            }};
            const openModal = () => {{
                if (modal) modal.style.display = 'flex';
            }};
            const showConfirm = (message, confirmTextValue = '确认', confirmButtonColor = '#ef4444', confirmIconName = 'mdi-alert', confirmIconColor = '#ef4444') => new Promise((resolve) => {{
                if (!confirmModal || !confirmText || !confirmCancelBtn || !confirmOkBtn) {{
                    resolve(false);
                    return;
                }}

                confirmText.textContent = message;
                confirmOkBtn.textContent = confirmTextValue;
                confirmOkBtn.style.background = confirmButtonColor;
                renderConfirmIcon(confirmIconName, confirmIconColor);
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

            if (errorAlert) errorAlert.style.display = 'none';
            if (successAlert) successAlert.style.display = 'none';

            const formatSize = (size) => {{
                if (!size) return '0 B';
                const units = ['B', 'KB', 'MB', 'GB'];
                let value = size;
                let index = 0;
                while (value >= 1024 && index < units.length - 1) {{
                    value /= 1024;
                    index += 1;
                }}
                return `${{value.toFixed(index === 0 ? 0 : 2)}} ${{units[index]}}`;
            }};

            const renderDependencies = (deps) => {{
                if (!deps) return '';
                if (!deps.total_count) return '<br><br><strong>依赖安装：</strong>无需安装依赖';
                let html = '<br><br><strong>依赖安装详情：</strong>';
                html += '<br>• 总依赖数量：' + (deps.total_count || 0) + ' 个';
                html += '<br>• 成功安装：' + (deps.success_count || 0) + ' 个';
                html += '<br>• 安装失败：' + (deps.failed_count || 0) + ' 个';
                html += '<br>• 安装状态：' + (deps.status === 'success' ? '✅ 成功' : '❌ 失败');
                if (deps.message) {{
                    html += '<br>• 详细信息：' + deps.message;
                }}
                return html;
            }};

            const loadBackupList = async () => {{
                backupContainer.innerHTML = '<div class="text-medium-emphasis">正在加载备份列表...</div>';

                const response = await request('/backup_list');
                const result = response.body;

                if (!(response.ok && result.code === 200)) {{
                    throw new Error(result.message || '获取备份列表失败');
                }}

                const groups = result.data || [];
                if (!groups.length) {{
                    backupContainer.innerHTML = '<div class="text-medium-emphasis">暂无可用备份。</div>';
                    return;
                }}

                const modalTitle = document.getElementById('localupload-backup-modal-title');
                if (modalTitle) {{
                    const modalTitleText = modalTitle.querySelector('.localupload-backup-modal-title-text');
                    if (modalTitleText) {{
                        modalTitleText.textContent = '备份管理 - 共 ' + groups.reduce((sum, group) => sum + (group.backups ? group.backups.length : 0), 0) + ' 个备份';
                    }}
                }}

                const html = groups.map((group, groupIndex) => {{
                    const backups = group.backups || [];
                    const rows = backups.map((backup, backupIndex) => `
                        <div class="localupload-backup-row" style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-top:1px solid rgba(128,128,128,.15);flex-wrap:wrap;">
                            <div style="min-width:260px;flex:1;">
                                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-weight:600;word-break:break-all;">
                                    <span>${{backup.filename}}</span>
                                    ${{backupIndex === 0 ? '<span class="localupload-backup-latest-tag" style="display:inline-flex;align-items:center;height:22px;padding:0 8px;border-radius:999px;background:rgba(34,197,94,.12);color:#16a34a;font-size:12px;font-weight:700;line-height:1;">最新</span>' : ''}}
                                </div>
                                <div class="localupload-backup-meta" style="font-size:12px;color:rgba(128,128,128,.9);margin-top:4px;">
                                    备份时间：${{backup.modified_time}} ｜ 文件大小：${{formatSize(backup.size)}}
                                </div>
                            </div>
                            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                                <button
                                    type="button"
                                    class="localupload-delete-backup-btn"
                                    data-plugin-id="${{group.plugin_id}}"
                                    data-plugin-name="${{group.plugin_name}}"
                                    data-backup-file="${{backup.filename}}"
                                    style="border:1px solid rgba(239,68,68,.32);border-radius:8px;padding:5px 14px;background:#fff;color:#ef4444;cursor:pointer;font-weight:600;font-size:13px;line-height:1.2;"
                                >删除</button>
                                <button
                                    type="button"
                                    class="localupload-restore-btn"
                                    data-plugin-id="${{group.plugin_id}}"
                                    data-plugin-name="${{group.plugin_name}}"
                                    data-backup-file="${{backup.filename}}"
                                    style="border:none;border-radius:8px;padding:5px 14px;background:#16b1ff;color:#fff;cursor:pointer;font-weight:600;font-size:13px;line-height:1.2;"
                                >恢复</button>
                            </div>
                        </div>
                    `).join('');

                    return `
                        <details class="localupload-backup-group" ${{groupIndex === 0 ? 'open' : ''}} style="border:1px solid rgba(128,128,128,.2);border-radius:12px;padding:12px 16px;background:rgba(22,177,255,.04);margin-bottom:12px;overflow:hidden;">
                            <summary class="localupload-backup-summary" style="cursor:pointer;font-weight:700;outline:none;">${{group.plugin_name}} <span class="localupload-backup-summary-count" style="color:rgba(128,128,128,.9);font-weight:400;">(${{backups.length}} 个备份)</span></summary>
                            <div class="localupload-backup-group-body" style="margin-top:12px;max-height:320px;overflow-y:auto;padding-right:4px;box-sizing:border-box;">${{rows}}</div>
                        </details>
                    `;
                }}).join('');

                backupContainer.innerHTML = html;
                bindBackupAccordions();
                bindDeleteButtons();
                bindRestoreButtons();
            }};

            const bindDeleteButtons = () => {{
                backupContainer.querySelectorAll('.localupload-delete-backup-btn').forEach((item) => {{
                    item.addEventListener('click', async (event) => {{
                        const actionButton = event.currentTarget;
                        const pluginId = actionButton.getAttribute('data-plugin-id');
                        const pluginName = actionButton.getAttribute('data-plugin-name') || pluginId;
                        const backupFile = actionButton.getAttribute('data-backup-file');
                        if (!pluginId || !backupFile) return;

                        const confirmed = await showConfirm(`确认删除插件 ${{pluginName}} 的备份文件：${{backupFile}} 吗？`, '确认删除', '#ef4444', 'mdi-delete-alert', '#ef4444');
                        if (!confirmed) {{
                            return;
                        }}

                        actionButton.disabled = true;
                        const originalText = actionButton.textContent;
                        actionButton.textContent = '删除中...';

                        try {{
                            const response = await request('/delete_backup', {{ plugin_id: pluginId, backup_file: backupFile }});
                            const result = response.body;

                            if (response.ok && result.code === 200) {{
                                if (successAlert) {{
                                    successAlert.textContent = result.message || '删除成功';
                                    successAlert.style.display = 'block';
                                }}
                                await loadBackupList();
                            }} else {{
                                if (errorAlert) {{
                                    errorAlert.textContent = result.message || '删除失败';
                                    errorAlert.style.display = 'block';
                                }}
                            }}
                        }} catch (error) {{
                            if (errorAlert) {{
                                errorAlert.textContent = '删除请求发送失败: ' + error;
                                errorAlert.style.display = 'block';
                            }}
                            console.error('Delete backup error:', error);
                        }} finally {{
                            actionButton.disabled = false;
                            actionButton.textContent = originalText;
                        }}
                    }});
                }});
            }};

            const bindRestoreButtons = () => {{
                backupContainer.querySelectorAll('.localupload-restore-btn').forEach((item) => {{
                    item.addEventListener('click', async (event) => {{
                        const actionButton = event.currentTarget;
                        const pluginId = actionButton.getAttribute('data-plugin-id');
                        const pluginName = actionButton.getAttribute('data-plugin-name') || pluginId;
                        const backupFile = actionButton.getAttribute('data-backup-file');
                        if (!pluginId || !backupFile) return;

                        const confirmed = await showConfirm(`确认恢复插件 ${{pluginName}} 的备份文件：${{backupFile}} 吗？`, '确认恢复', '#16b1ff', 'mdi-backup-restore', '#16b1ff');
                        if (!confirmed) {{
                            return;
                        }}

                        actionButton.disabled = true;
                        const originalText = actionButton.textContent;
                        actionButton.textContent = '恢复中...';

                        try {{
                            const response = await request('/restore_backup', {{ plugin_id: pluginId, backup_file: backupFile }});
                            const result = response.body;

                            if (response.ok && result.code === 200) {{
                                if (successAlert) {{
                                    successAlert.innerHTML = (result.message || '恢复成功') + renderDependencies(result.data?.dependencies);
                                    successAlert.style.whiteSpace = 'pre-line';
                                    successAlert.style.display = 'block';
                                }}
                                closeModal();
                            }} else {{
                                if (errorAlert) {{
                                    errorAlert.innerHTML = (result.message || '恢复失败') + renderDependencies(result.data?.dependencies);
                                    errorAlert.style.whiteSpace = 'pre-line';
                                    errorAlert.style.display = 'block';
                                }}
                            }}
                        }} catch (error) {{
                            if (errorAlert) {{
                                errorAlert.textContent = '恢复请求发送失败: ' + error;
                                errorAlert.style.display = 'block';
                            }}
                            console.error('Restore backup error:', error);
                        }} finally {{
                            actionButton.disabled = false;
                            actionButton.textContent = originalText;
                        }}
                    }});
                }});
            }};

            const bindBackupAccordions = () => {{
                const detailItems = backupContainer.querySelectorAll('.localupload-backup-group');
                detailItems.forEach((detail) => {{
                    detail.addEventListener('toggle', () => {{
                        if (!detail.open) return;
                        detailItems.forEach((other) => {{
                            if (other !== detail) {{
                                other.open = false;
                            }}
                        }});
                    }});
                }});
            }};

            try {{
                button.disabled = true;
                button.textContent = '加载中...';
                openModal();
                await loadBackupList();
            }} catch (error) {{
                backupContainer.innerHTML = '<div style="color:#ff5252;">' + error + '</div>';
                if (errorAlert) {{
                    errorAlert.textContent = '获取备份列表失败: ' + error;
                    errorAlert.style.display = 'block';
                }}
                console.error('Load backup list error:', error);
            }} finally {{
                button.disabled = false;
                button.textContent = '从备份恢复';
            }}
        }})(this)
        """

        page_structure = [
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
                                    'elevation': 3,
                                    'class': 'mx-auto rounded-lg',
                                    'border': True
                                },
                                'content': [
                                    {
                                        'component': 'VCardItem',
                                        'props': {
                                            'class': 'pb-0 d-flex flex-column align-center justify-center'
                                        },
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'class': 'mb-2'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VCardTitle',
                                                        'props': {
                                                            'class': 'text-h5 font-weight-bold d-flex align-center justify-center'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'color': 'info',
                                                                    'size': 'large',
                                                                    'class': 'mr-2'
                                                                },
                                                                'text': 'mdi-upload'
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'text': '上传插件'
                                                            }
                                                        ]
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'class': 'text-center mb-2'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VCardSubtitle',
                                                        'props': {
                                                            'class': 'text-medium-emphasis'
                                                        },
                                                        'text': '上传本地ZIP插件包进行安装'
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
                                        'component': 'VContainer',
                                        'props': {
                                            'class': 'px-md-10 py-4',
                                            'max-width': '800'
                                        },
                                        'content': [
                                            {
                                                'component': 'VCardText',
                                                'content': [
                                                    { # 信息提示
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'info',
                                                            'variant': 'tonal',
                                                            'text': '请确保插件包包含__init__.py文件且继承_PluginBase类。如果插件有依赖，请确保包含requirements.txt文件。',
                                                            'class': 'mb-6',
                                                            'density': 'comfortable',
                                                            'icon': 'mdi-information',
                                                            'elevation': 1,
                                                            'rounded': 'lg'
                                                        }
                                                    },
                                                    { # 成功提示
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'success',
                                                            'variant': 'tonal',
                                                            'class': 'mb-6',
                                                            'density': 'comfortable',
                                                            'border': 'start',
                                                            'icon': 'mdi-check-circle',
                                                            'elevation': 1,
                                                            'rounded': 'lg',
                                                            'id': 'localupload-success-alert',
                                                            'style': 'display: none;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-1'
                                                                }
                                                            }
                                                        ]
                                                    },
                                                    { # 错误提示
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'error',
                                                            'variant': 'tonal',
                                                            'class': 'mb-6',
                                                            'density': 'comfortable',
                                                            'border': 'start',
                                                            'icon': 'mdi-alert',
                                                            'elevation': 1,
                                                            'rounded': 'lg',
                                                            'id': 'localupload-error-alert',
                                                            'style': 'display: none;'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-1'
                                                                }
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VSheet',
                                                        'props': {
                                                            'class': 'pa-6',
                                                            'rounded': 'lg',
                                                            'elevation': 0,
                                                            'border': True,
                                                            'color': 'background'
                                                        },
                                                        'content': [
                                                            { # 文件输入框
                                                                'component': 'VFileInput',
                                                                'props': {
                                                                    'model': 'file',
                                                                    'label': '选择插件ZIP包',
                                                                    'hint': f'最大文件大小：{self._config.get("max_file_size") / 1024 / 1024:.1f}MB',
                                                                    'persistent-hint': True,
                                                                    'chips': True,
                                                                    'multiple': False,
                                                                    'show-size': True,
                                                                    'accept': '.zip',
                                                                    'prepend-icon': 'mdi-folder-zip',
                                                                    'size': 'x-large',
                                                                    'height': '64',
                                                                    'variant': 'outlined',
                                                                    'class': 'mb-6 custom-file-input',
                                                                    'style': 'font-size: 24px;',
                                                                    'id': 'localupload-file-input',
                                                                    'density': 'default',
                                                                    'color': 'primary',
                                                                    'bg-color': 'surface'
                                                                }
                                                            },
                                                            { # 按钮
                                                                'component': 'VRow',
                                                                'props': {
                                                                    'class': 'mt-2'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'VCol',
                                                                        'props': {'cols': 12, 'md': 6},
                                                                        'content': [
                                                                            {
                                                                                'component': 'VBtn',
                                                                                'props': {
                                                                                    'color': 'primary',
                                                                                    'block': True,
                                                                                    'size': 'large',
                                                                                    'onclick': onclick_js,
                                                                                    'id': 'localupload-install-button',
                                                                                    'elevation': 2,
                                                                                    'rounded': 'lg',
                                                                                    'class': 'text-none font-weight-bold'
                                                                                },
                                                                                'content': [
                                                                                    {'component': 'span', 'text': '安装插件'}
                                                                                ]
                                                                            }
                                                                        ]
                                                                    },
                                                                    {
                                                                        'component': 'VCol',
                                                                        'props': {'cols': 12, 'md': 6},
                                                                        'content': [
                                                                            {
                                                                                'component': 'VBtn',
                                                                                'props': {
                                                                                    'color': 'info',
                                                                                    'variant': 'outlined',
                                                                                    'block': True,
                                                                                    'size': 'large',
                                                                                    'onclick': restore_onclick_js,
                                                                                    'id': 'localupload-show-backup-button',
                                                                                    'elevation': 0,
                                                                                    'rounded': 'lg',
                                                                                    'class': 'text-none font-weight-bold'
                                                                                },
                                                                                'content': [
                                                                                    {'component': 'span', 'text': '从备份恢复'}
                                                                                ]
                                                                            }
                                                                        ]
                                                                    },
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
                ]
            },
            { # 添加提示信息卡片
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12},
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
                                        'props': {'class': 'px-6 pb-0'},
                                        'content': [
                                            {
                                                'component': 'VCardTitle',
                                                'props': {'class': 'd-flex align-center text-h6 mb-0'},
                                                'content': [
                                                    {
                                                        'component': 'VIcon',
                                                        'props': {
                                                            'style': 'color: #16b1ff;',
                                                            'class': 'mr-3',
                                                            'size': 'default',
                                                        },
                                                        'text': 'mdi-information'
                                                    },
                                                    {
                                                        'component': 'span',
                                                        'text': '插件安装说明'
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
                                        'props': {'class': 'px-6 py-0'},
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
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'primary',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-cog'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '首次安装'
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
                                                                        'text': '首次安装请点击右下角设置打开 启用插件 保存，如果安装提示'
                                                                    },
                                                                    {
                                                                        'component': 'VChip',
                                                                        'props': {
                                                                            'color': 'error',
                                                                            'size': 'small',
                                                                            'class': 'mx-1'
                                                                        },
                                                                        'text': '安装失败，状态码: 404'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '请重新打开设置页面保存一下以生效安装API'
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'success',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-folder-zip'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': 'ZIP文件结构'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '插件包必须包含以下内容：- 插件目录（如 myplugin/）- __init__.py 文件（必须继承 _PluginBase）- requirements.txt（可选，用于声明依赖）- 其他插件相关文件'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'success',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-vuejs'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': 'Vue联邦插件结构'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '支持安装 Vue 联邦插件。ZIP 可直接以文件为根目录打包，至少包含 __init__.py，以及前端构建产物目录 dist/（通常为 dist/assets/...）；如有 Python 依赖，可同时包含 requirements.txt。'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
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
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '注意事项'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '1. 确保插件包大小不超过限制 2. 插件ID必须与目录名一致 3. 安装前请确保插件代码安全可靠 4. 安装失败时请检查错误信息'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'warning',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-help-circle'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '常见问题'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '1. 安装失败？检查插件包结构是否正确 2. 依赖安装失败？确保requirements.txt格式正确，或尝试手动安装依赖 3. 插件不工作？检查日志获取详细信息 4. 提示"没有找到继承_PluginBase的插件类"？可能是依赖缺失，请检查requirements.txt文件'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'info',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-folder-information'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '备份路径说明'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': f'所有插件的备份文件将保存到此目录：{self.get_data_path() / "backups"}。请勿手动删除此目录下的文件，除非您确定不再需要这些备份。'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'VListItem',
                                                        'props': {'lines': 'two'},
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'd-flex align-items-start'},
                                                                'content': [
                                                                    {
                                                                        'component': 'VIcon',
                                                                        'props': {
                                                                            'color': 'info',
                                                                            'class': 'mt-1 mr-2'
                                                                        },
                                                                        'text': 'mdi-backup-restore'
                                                                    },
                                                                    {
                                                                        'component': 'div',
                                                                        'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                        'text': '恢复功能说明'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'text-body-2 ml-8'
                                                                },
                                                                'text': '点击“从备份恢复”可打开备份列表，列表会按插件名称分组显示历史备份 ZIP。展开对应插件后，选择需要的备份文件并点击“恢复”即可重新安装该版本插件。恢复时不会额外创建一次新备份，请确认所选版本无误后再执行。'
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
                'component': 'div',
                'props': {
                    'id': 'localupload-backup-modal',
                    'style': 'display:none;position:fixed;inset:0;z-index:3000;background:#3A354180;align-items:center;justify-content:center;padding:24px;'
                },
                'content': [
                    {
                        'component': 'div',
                        'props': {
                            'id': 'localupload-backup-modal-card',
                            'style': 'width:min(720px,100%);height:min(70vh,640px);background:#ffffff;border:1px solid rgba(226,232,240,1);border-radius:16px;box-shadow:0 12px 32px rgba(15,23,42,.16);overflow:hidden;display:flex;flex-direction:column;position:relative;'
                        },
                        'content': [
                            {
                                'component': 'div',
                                'props': {
                                    'id': 'localupload-backup-modal-header',
                                    'style': 'display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid rgba(128,128,128,.18);flex:0 0 auto;'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'id': 'localupload-backup-modal-title',
                                            'style': 'font-size:18px;font-weight:700;color:#111827;display:flex;align-items:center;'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'color': '#16b1ff',
                                                    'size': '20',
                                                    'class': 'mr-2'
                                                },
                                                'text': 'mdi-folder-download'
                                            },
                                            {
                                                'component': 'span',
                                                'props': {
                                                    'class': 'localupload-backup-modal-title-text'
                                                },
                                                'text': '选择备份并恢复安装'
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'button',
                                        'props': {
                                            'id': 'localupload-backup-modal-close',
                                            'type': 'button',
                                            'onclick': "document.getElementById('localupload-backup-modal').style.display='none'",
                                            'style': 'border:none;background:transparent;font-size:24px;line-height:1;cursor:pointer;color:#6b7280;padding:0 4px;'
                                        },
                                        'text': '×'
                                    }
                                ]
                            },
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'padding:18px 22px;overflow:hidden;flex:1;min-height:0;'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'id': 'localupload-backup-list-container',
                                            'style': 'height:100%;overflow-y:auto;overflow-x:hidden;scrollbar-width:none;-ms-overflow-style:none;padding-right:2px;'
                                        }
                                    },
                                    {
                                        'component': 'style',
                                        'text': '#localupload-backup-list-container::-webkit-scrollbar{width:0;height:0;display:none;}'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'div',
                'props': {
                    'id': 'localupload-notice-modal',
                    'style': 'display:none;position:fixed;inset:0;z-index:3001;background:#3A354180;align-items:center;justify-content:center;padding:24px;pointer-events:none;'
                },
                'content': [
                    {
                        'component': 'div',
                        'props': {
                            'id': 'localupload-notice-card',
                            'style': 'min-width:320px;max-width:min(440px,100%);background:#ffffff;border:1px solid rgba(226,232,240,1);border-radius:16px;box-shadow:0 12px 32px rgba(15,23,42,.18);padding:22px 22px 18px 22px;pointer-events:auto;'
                        },
                        'content': [
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'display:flex;align-items:flex-start;gap:14px;'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'style': 'display:flex;align-items:center;justify-content:center;flex:0 0 auto;width:28px;height:28px;color:#ef4444;font-size:20px;font-weight:700;'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'color': '#ef4444',
                                                    'size': '22'
                                                },
                                                'text': 'mdi-alert'
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'style': 'flex:1;min-width:0;'
                                        },
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'id': 'localupload-notice-title',
                                                    'style': 'font-size:16px;font-weight:700;color:#1f2937;margin-bottom:8px;'
                                                },
                                                'text': '错误提示：'
                                            },
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'id': 'localupload-notice-text',
                                                    'style': 'font-size:14px;line-height:1.6;color:#4b5563;word-break:break-word;'
                                                },
                                                'text': ''
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'display:flex;justify-content:flex-end;margin-top:18px;'
                                },
                                'content': [
                                    {
                                        'component': 'button',
                                        'props': {
                                            'id': 'localupload-notice-ok',
                                            'type': 'button',
                                            'onclick': "document.getElementById('localupload-notice-modal').style.display='none'",
                                            'style': 'border:none;border-radius:10px;padding:7px 16px;background:#16b1ff;color:#fff;font-size:13px;line-height:1.2;font-weight:700;cursor:pointer;'
                                        },
                                        'text': '知道了'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'div',
                'props': {
                    'id': 'localupload-confirm-modal',
                    'style': 'display:none;position:fixed;inset:0;z-index:3002;background:#3A354180;align-items:center;justify-content:center;padding:24px;pointer-events:none;'
                },
                'content': [
                    {
                        'component': 'div',
                        'props': {
                            'id': 'localupload-confirm-card',
                            'style': 'min-width:320px;max-width:min(460px,100%);background:#ffffff;border:1px solid rgba(226,232,240,1);border-radius:16px;box-shadow:0 12px 32px rgba(15,23,42,.18);padding:22px 22px 18px 22px;pointer-events:auto;'
                        },
                        'content': [
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'display:flex;align-items:flex-start;gap:14px;'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'id': 'localupload-confirm-icon-wrap',
                                            'style': 'display:flex;align-items:center;justify-content:center;flex:0 0 auto;width:28px;height:28px;color:#ef4444;font-size:20px;font-weight:700;'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'color': '#ef4444',
                                                    'size': '22'
                                                },
                                                'text': 'mdi-alert'
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'style': 'flex:1;min-width:0;'
                                        },
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'id': 'localupload-confirm-title',
                                                    'style': 'font-size:16px;font-weight:700;color:#1f2937;margin-bottom:8px;'
                                                },
                                                'text': '请确认操作'
                                            },
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'id': 'localupload-confirm-text',
                                                    'style': 'font-size:14px;line-height:1.6;color:#4b5563;word-break:break-word;'
                                                },
                                                'text': ''
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'div',
                                'props': {
                                    'style': 'display:flex;justify-content:flex-end;gap:10px;margin-top:18px;'
                                },
                                'content': [
                                    {
                                        'component': 'button',
                                        'props': {
                                            'id': 'localupload-confirm-cancel',
                                            'type': 'button',
                                            'style': 'border:1px solid rgba(148,163,184,.4);border-radius:10px;padding:7px 16px;background:#fff;color:#475569;font-size:13px;line-height:1.2;font-weight:700;cursor:pointer;'
                                        },
                                        'text': '取消'
                                    },
                                    {
                                        'component': 'button',
                                        'props': {
                                            'id': 'localupload-confirm-ok',
                                            'type': 'button',
                                            'style': 'border:none;border-radius:10px;padding:7px 16px;background:#ef4444;color:#fff;font-size:13px;line-height:1.2;font-weight:700;cursor:pointer;'
                                        },
                                        'text': '确认'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'style',
                'text': '.v-theme--dark #localupload-backup-modal,[data-theme="dark"] #localupload-backup-modal,.v-theme--dark #localupload-notice-modal,[data-theme="dark"] #localupload-notice-modal,.v-theme--dark #localupload-confirm-modal,[data-theme="dark"] #localupload-confirm-modal{background:rgba(15,23,42,.62) !important;}.v-theme--dark #localupload-backup-modal-card,[data-theme="dark"] #localupload-backup-modal-card,.v-theme--dark #localupload-notice-card,[data-theme="dark"] #localupload-notice-card,.v-theme--dark #localupload-confirm-card,[data-theme="dark"] #localupload-confirm-card{background:#111827 !important;border-color:rgba(71,85,105,.55) !important;box-shadow:0 18px 42px rgba(0,0,0,.45) !important;}.v-theme--dark #localupload-backup-modal-header,[data-theme="dark"] #localupload-backup-modal-header{border-bottom-color:rgba(71,85,105,.55) !important;}.v-theme--dark #localupload-backup-modal-title,[data-theme="dark"] #localupload-backup-modal-title,.v-theme--dark #localupload-notice-title,[data-theme="dark"] #localupload-notice-title,.v-theme--dark #localupload-confirm-title,[data-theme="dark"] #localupload-confirm-title{color:#f9fafb !important;}.v-theme--dark #localupload-backup-modal-close,[data-theme="dark"] #localupload-backup-modal-close{color:#cbd5e1 !important;}.v-theme--dark .localupload-backup-group,[data-theme="dark"] .localupload-backup-group{background:rgba(37,99,235,.12) !important;border-color:rgba(71,85,105,.55) !important;}.v-theme--dark .localupload-backup-summary,[data-theme="dark"] .localupload-backup-summary{color:#f9fafb !important;}.v-theme--dark .localupload-backup-summary-count,[data-theme="dark"] .localupload-backup-summary-count,.v-theme--dark .localupload-backup-meta,[data-theme="dark"] .localupload-backup-meta{color:#94a3b8 !important;}.v-theme--dark .localupload-backup-row,[data-theme="dark"] .localupload-backup-row{border-top-color:rgba(71,85,105,.4) !important;color:#e5e7eb !important;}.v-theme--dark .localupload-backup-group-body,[data-theme="dark"] .localupload-backup-group-body{color:#e5e7eb !important;}.v-theme--dark .localupload-delete-backup-btn,[data-theme="dark"] .localupload-delete-backup-btn{background:#1f2937 !important;color:#f87171 !important;border-color:rgba(248,113,113,.4) !important;}.v-theme--dark .localupload-restore-btn,[data-theme="dark"] .localupload-restore-btn{background:#0ea5e9 !important;color:#ffffff !important;}.v-theme--dark .localupload-backup-latest-tag,[data-theme="dark"] .localupload-backup-latest-tag{background:rgba(34,197,94,.18) !important;color:#86efac !important;}.v-theme--dark #localupload-notice-text,[data-theme="dark"] #localupload-notice-text,.v-theme--dark #localupload-confirm-text,[data-theme="dark"] #localupload-confirm-text{color:#cbd5e1 !important;}.v-theme--dark #localupload-confirm-cancel,[data-theme="dark"] #localupload-confirm-cancel{background:#1f2937 !important;color:#e5e7eb !important;border-color:rgba(148,163,184,.3) !important;}.v-theme--dark #localupload-notice-ok,[data-theme="dark"] #localupload-notice-ok{box-shadow:none !important;}@media (prefers-color-scheme: dark){#localupload-backup-modal,#localupload-notice-modal,#localupload-confirm-modal{background:rgba(15,23,42,.62) !important;}#localupload-backup-modal-card,#localupload-notice-card,#localupload-confirm-card{background:#111827 !important;border-color:rgba(71,85,105,.55) !important;box-shadow:0 18px 42px rgba(0,0,0,.45) !important;}#localupload-backup-modal-header{border-bottom-color:rgba(71,85,105,.55) !important;}#localupload-backup-modal-title,#localupload-notice-title,#localupload-confirm-title{color:#f9fafb !important;}#localupload-backup-modal-close{color:#cbd5e1 !important;} .localupload-backup-group{background:rgba(37,99,235,.12) !important;border-color:rgba(71,85,105,.55) !important;} .localupload-backup-summary{color:#f9fafb !important;} .localupload-backup-summary-count,.localupload-backup-meta{color:#94a3b8 !important;} .localupload-backup-row{border-top-color:rgba(71,85,105,.4) !important;color:#e5e7eb !important;} .localupload-backup-group-body{color:#e5e7eb !important;} .localupload-delete-backup-btn{background:#1f2937 !important;color:#f87171 !important;border-color:rgba(248,113,113,.4) !important;} .localupload-restore-btn{background:#0ea5e9 !important;color:#ffffff !important;} .localupload-backup-latest-tag{background:rgba(34,197,94,.18) !important;color:#86efac !important;}#localupload-notice-text,#localupload-confirm-text{color:#cbd5e1 !important;}#localupload-confirm-cancel{background:#1f2937 !important;color:#e5e7eb !important;border-color:rgba(148,163,184,.3) !important;}#localupload-notice-ok{box-shadow:none !important;}'
            }
        ]
        return page_structure
