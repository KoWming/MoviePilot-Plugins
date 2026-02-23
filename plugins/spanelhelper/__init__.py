import time
import zipfile
import shutil
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import base64

from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.utils.http import RequestUtils
from app.db.site_oper import SiteOper
from app.schemas import NotificationType

class SpanelHelper(_PluginBase):
    # 插件名称
    plugin_name = "Sun-Panel助手"
    # 插件描述
    plugin_desc = "同步MP中已启用的站点到Sun-Panel指定分组"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/sun-panel.png"
    # 插件版本
    plugin_version = "1.1"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "spanelhelper_"
    # 加载顺序
    plugin_order = 16
    # 可使用的用户级别
    auth_level = 1

    # 域名/站点名别名映射
    ICON_ALIAS_MAPPING = {
        "totheglory": "ttg",
        "bilibili": "playletpt"
    }

    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _custom_domains = ""
    _cron = "0 0 * * *"
    _spanel_url = ""
    _spanel_token = ""
    _group_name = "MoviePilot"
    _run_now = False
    _use_proxy = True # 默认开启代理
    _notify = True # 默认开启通知
    _force_update = False # 强制更新
    _icon_repo_url = "" # 图标库URL
    _scheduler: Optional[BackgroundScheduler] = None

    def init_plugin(self, config: dict = None):
        # 停止现有任务
        self.stop_service()
        
        if config:
            self._enabled = config.get("enabled")
            self._cron = config.get("cron") or "0 0 * * *"
            self._spanel_url = config.get("spanel_url")
            self._spanel_token = config.get("spanel_token")
            self._group_name = config.get("group_name") or "MoviePilot"
            self._run_now = config.get("run_now")
            self._use_proxy = config.get("use_proxy")   
            self._notify = config.get("notify")
            self._force_update = config.get("force_update")
            self._icon_repo_url = config.get("icon_repo_url")
            self._custom_domains = config.get("custom_domains") or ""

        # 确保数据目录存在
        self._data_path = Path(settings.CONFIG_PATH) / "plugins" / "spanelhelper"
        if not self._data_path.exists():
            self._data_path.mkdir(parents=True, exist_ok=True)
            
        if self._enabled and self._run_now:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)
            logger.info("SunPanel助手服务启动，立即运行一次同步")
            self._scheduler.add_job(func=self.__sync, trigger='date',
                                    run_date=datetime.now(),
                                    name="SunPanel同步(立即)")
            # 启动任务
            if self._scheduler.get_jobs():
                self._scheduler.start()
            
            # 关闭一次性开关
            self._run_now = False
            self.update_config({
                "enabled": self._enabled,
                "cron": self._cron,
                "spanel_url": self._spanel_url,
                "spanel_token": self._spanel_token,
                "group_name": self._group_name,
                "run_now": False,
                "use_proxy": self._use_proxy,
                "notify": self._notify,
                "force_update": self._force_update,
                "icon_repo_url": self._icon_repo_url,
                "custom_domains": self._custom_domains,
            })

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        """
        if self._enabled and self._cron:
            return [{
                "id": "SpanelHelper",
                "name": "SunPanel同步服务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.__sync,
                "kwargs": {}
            }]
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
        """
        version = getattr(settings, "VERSION_FLAG", "v1")
        cron_field_component = "VCronField" if version == "v2" else "VTextField"
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-0'},
                        'content': [
                            {
                                'component': 'VCardTitle',
                                'props': {'class': 'd-flex align-center'},
                                'content': [
                                    {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-cog'},
                                    {'component': 'span', 'text': '基本设置'}
                                ]
                            },
                            {'component': 'VDivider'},
                            {'component': 'VCardText', 'content': [
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 3}, 'content': [{'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件', 'color': 'primary'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 3}, 'content': [{'component': 'VSwitch', 'props': {'model': 'use_proxy', 'label': '使用代理', 'color': 'info'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 3}, 'content': [{'component': 'VSwitch', 'props': {'model': 'notify', 'label': '开启通知', 'color': 'success'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 3}, 'content': [{'component': 'VSwitch', 'props': {'model': 'run_now', 'label': '立即运行一次', 'color': 'warning'}}]},
                                ]}
                            ]}
                        ]
                    },
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-3'},
                        'content': [
                            {
                                'component': 'VCardTitle',
                                'props': {'class': 'd-flex align-center'},
                                'content': [
                                    {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-link-variant'},
                                    {'component': 'span', 'text': '参数配置'}
                                ]
                            },
                            {'component': 'VDivider'},
                            {'component': 'VCardText', 'content': [
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VTextField', 'props': {'model': 'spanel_url', 'label': '接口地址', 'placeholder': 'http://ip:port', 'autocomplete': 'off'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VTextField', 'props': {'model': 'spanel_token', 'label': 'Token', 'type': 'password', 'placeholder': 'OpenAPI Token', 'autocomplete': 'new-password'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VTextField', 'props': {'model': 'group_name', 'label': '同步分组名称', 'placeholder': 'MoviePilot', 'autocomplete': 'off'}}]},
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VTextField', 'props': {'model': 'icon_repo_url', 'label': '图标库URL', 'placeholder': 'https://example.com/icons.zip'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 3}, 'content': [{'component': cron_field_component, 'props': {'model': 'cron', 'label': '同步周期', 'placeholder': '0 * * * *'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 3}, 'content': [{'component': 'VSelect', 'props': {'model': 'force_update', 'label': '强制更新', 'items': [{'title': '关闭', 'value': False}, {'title': '开启', 'value': True}]}}]}
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12}, 'content': [{'component': 'VTextarea', 'props': {'model': 'custom_domains', 'label': '自定义域名设置', 'rows': 3, 'placeholder': '格式：站点名称|域名URL\n例如：馒头|https://kp.m-team.cc/\n用于替换站点URL映射字典功能'}}]}
                                ]}
                            ]}
                        ]
                    },
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-3'},
                        'content': [
                            {
                                'component': 'VCardTitle',
                                'props': {'class': 'd-flex align-center'},
                                'content': [
                                    {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-information'},
                                    {'component': 'span', 'text': '使用说明'}
                                ]
                            },
                            {'component': 'VDivider'},
                            {'component': 'VCardText', 'props': {'class': 'px-6 pb-6'}, 'content': [
                                {
                                    'component': 'VList',
                                    'props': {'lines': 'two', 'density': 'comfortable'},
                                    'content': [
                                        {
                                            'component': 'VListItem',
                                            'props': {'lines': 'two'},
                                            'content': [
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'd-flex align-items-start'},
                                                    'content': [
                                                        {'component': 'VIcon', 'props': {'color': '#FF9800', 'class': 'mt-1 mr-2'}, 'text': 'mdi-lightbulb-on'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '首次使用建议'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'text': '首次使用时不要使用Sun-Panel中已有的分组名称，插件会自动创建分组并同步。若强制使用原有分组，可能因旧项目缺失唯一标识(onlyName)导致后期无法准确识别更新。'
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
                                                        {'component': 'VIcon', 'props': {'color': 'primary', 'class': 'mt-1 mr-2'}, 'text': 'mdi-check-circle'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': 'Sun-Panel 版本要求'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'text': '请确保 Sun-Panel 版本支持 OpenAPI (v1.7.* 版本开始支持)。'
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
                                                        {'component': 'VIcon', 'props': {'color': 'info', 'class': 'mt-1 mr-2'}, 'text': 'mdi-key'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '获取 Token'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'text': '请在 Sun-Panel 设置中启用 OpenAPI 应用并获取 Token。'
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
                                                        {'component': 'VIcon', 'props': {'color': 'success', 'class': 'mt-1 mr-2'}, 'text': 'mdi-sync'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '自动同步'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'text': '插件会自动在 Sun-Panel 中创建指定名称的分组，并将 MoviePilot 中的活跃站点同步到该分组中。'
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
                                                        {'component': 'VIcon', 'props': {'color': 'warning', 'class': 'mt-1 mr-2'}, 'text': 'mdi-image'},
                                                        {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'}, 'text': '图标库支持'}
                                                    ]
                                                },
                                                {
                                                    'component': 'div',
                                                    'props': {'class': 'text-body-2 ml-8'},
                                                    'text': '支持配置 ZIP 格式的图标库 URL，插件会自动下载并解压匹配站点图标。'
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]}
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "cron": "0 0 * * *",
            "spanel_url": "",
            "spanel_token": "",
            "group_name": "MoviePilot",
            "run_now": False,
            "use_proxy": True,
            "notify": True,
            "force_update": False,
            "icon_repo_url": "",
            "custom_domains": ""
        }

    def get_page(self) -> List[dict]:
        pass

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def stop_service(self):
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error(f"停止SunPanel助手服务失败: {e}")

    def __sync(self):
        """
        同步逻辑
        """
        if not self._spanel_url or not self._spanel_token:
            logger.error("未配置Sun-Panel地址或Token，无法同步")
            return

        logger.info("开始同步站点信息到Sun-Panel...")
        
        if self._icon_repo_url:
             self._download_icon_zip()

        try:
            # 1. 获取站点信息
            sites = SiteOper().list_active()
            if not sites:
                logger.info("没有已启用站点，跳过同步")
                return

            # 2. 检查/创建分组
            group_id, group_only_name = self.__get_or_create_group(self._group_name)
            if not group_id and not group_only_name:
                logger.error(f"无法获取或创建分组 {self._group_name}")
                if self._notify:
                    self.post_message(mtype=NotificationType.Plugin, title="【☀️Sun-Panel助手】同步失败", text=f"❌ 无法获取或创建分组: {self._group_name}")
                return

            # 3. 同步站点
            success_count = 0
            fail_count = 0
            total_count = len(sites)
            
            custom_mapping = {}
            if self._custom_domains:
                for line in self._custom_domains.splitlines():
                    line = line.strip()
                    if not line or '|' not in line:
                        continue
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        custom_mapping[parts[0].strip()] = parts[1].strip()
            
            for site in sites:
                if self.__sync_site_item(site, group_id, group_only_name, custom_mapping):
                    success_count += 1
                else:
                    fail_count += 1
            
            logger.info(f"同步完成，共同步 {success_count} 个站点，失败 {fail_count} 个")
            if self._notify:
                notify_lines = []
                notify_lines.append("━━━━━━━━━━━━━━")
                notify_lines.append(f"{'✅' if fail_count == 0 else '⚠️'} SunPanel同步{'完成' if fail_count == 0 else '部分完成'}")
                notify_lines.append("━━━━━━━━━━━━━━")
                notify_lines.append("📦 同步统计：")
                notify_lines.append(f"📁 分组名称：{self._group_name}")
                notify_lines.append(f"🗂️ 活跃站点：{total_count}")
                notify_lines.append(f"✅ 成功同步：{success_count}")
                if fail_count > 0:
                    notify_lines.append(f"❌ 失败数量：{fail_count}")
                notify_lines.append("━━━━━━━━━━━━━━")
                notify_lines.append(f"⏱ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")

                self.post_message(mtype=NotificationType.Plugin, title="【☀️Sun-Panel助手】同步完成：", text="\n".join(notify_lines))

        except Exception as e:
            logger.error(f"SunPanel同步发生异常: {e}")
            if self._notify:
                self.post_message(mtype=NotificationType.Plugin, title="【☀️Sun-Panel助手】同步异常", text=f"❌ 发生未知错误: {str(e)}")

    def __get_request_headers(self):
        return {
            "token": self._spanel_token,
            "Content-Type": "application/json"
        }

    def _get_proxies(self):
        """
        获取代理设置
        """
        if not self._use_proxy:
            return None
            
        try:
            # 获取系统代理设置
            if hasattr(settings, 'PROXY') and settings.PROXY:
                return settings.PROXY
        except Exception as e:
            logger.error(f"获取代理设置出错: {str(e)}")
        return None

    def __get_or_create_group(self, group_title: str) -> Tuple[Optional[int], Optional[str]]:
        """
        获取或创建分组，返回 (itemGroupID, onlyName)
        """
        # 生成唯一标识，简化处理，不依赖title变化
        list_url = f"{self._spanel_url.rstrip('/')}/openapi/v1/itemGroup/getList"
        try:
            res = RequestUtils(headers=self.__get_request_headers()).post_res(list_url, json={})
            if res and res.status_code == 200:
                data = res.json()
                if data.get("code") == 0:
                    groups = data.get("data", {}).get("list", [])
                    for group in groups:
                        if group.get("title") == group_title:
                            return group.get("itemGroupID"), group.get("onlyName")
                else:
                    logger.error(f"获取分组列表失败: {data.get('msg')}")
            else:
                status = res.status_code if res else "Unknown"
                logger.error(f"获取分组列表HTTP错误: {status}")
        except Exception as e:
            logger.error(f"获取分组列表异常: {e}")
            return None, None

        # 创建分组
        create_url = f"{self._spanel_url.rstrip('/')}/openapi/v1/itemGroup/create"
        # 生成一个随机的onlyName
        new_only_name = f"mp_group_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "title": group_title,
            "onlyName": new_only_name
        }
        
        try:
            res = RequestUtils(headers=self.__get_request_headers()).post_res(create_url, json=payload)
            if res and res.status_code == 200:
                data = res.json()
                if data.get("code") == 0:
                    logger.info(f"成功创建分组: {group_title}")
                    return None, new_only_name 
                else:
                    logger.error(f"创建分组失败: {data.get('msg')}")
            else:
                status = res.status_code if res else "Unknown"
                logger.error(f"创建分组HTTP错误: {status}")
        except Exception as e:
            logger.error(f"创建分组异常: {e}")

        return None, None

    def _download_icon_zip(self):
        """
        下载并解压图标库ZIP
        """
        try:
            if not self._icon_repo_url:
                return

            logger.info(f"正在下载图标库ZIP: {self._icon_repo_url}")
            res = RequestUtils(proxies=self._get_proxies()).get_res(self._icon_repo_url)
            if res and res.status_code == 200:
                # 保存 ZIP
                zip_path = self._data_path / "icons.zip"
                with open(zip_path, "wb") as f:
                    f.write(res.content)
                
                # 解压
                extract_path = self._data_path / "icons"
                if extract_path.exists():
                    shutil.rmtree(extract_path)
                extract_path.mkdir(parents=True, exist_ok=True)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                logger.info(f"图标库解压完成: {extract_path}")
            else:
                logger.error(f"图标库下载失败: {res.status_code if res else 'No Response'}")

        except Exception as e:
            logger.error(f"图标库下载/解压异常: {e}")

    def _get_icon_from_repo(self, site) -> str:
        """
        从图标库获取图标 
        (仅支持 ZIP 下载解压后的本地匹配)
        """
        if not self._icon_repo_url:
            return ""

        extract_path = self._data_path / "icons"
        if not extract_path.exists():
            return ""
        
        # 准备匹配候选词
        candidates = []
        if hasattr(site, 'domain') and site.domain and "." in site.domain:
            parts = site.domain.split('.')
            domain_prefix = parts[0]

            if domain_prefix in ['api', 'www', 'pt', 'kp', 'tracker'] and len(parts) > 2:
                domain_prefix = parts[1]
                
            candidates.append(domain_prefix)
            
            if domain_prefix in self.ICON_ALIAS_MAPPING:
                candidates.append(self.ICON_ALIAS_MAPPING[domain_prefix])
            
            if "-" in domain_prefix:
                candidates.append(domain_prefix.replace("-", ""))
                candidates.append(domain_prefix.replace("-", "_"))
            
            candidates.append(site.domain.replace(".", ""))
                
        if hasattr(site, 'domain') and site.domain:
            candidates.append(site.domain)

        if site.name:
            candidates.append(site.name)
        
        # 查找逻辑
        for candidate in candidates:
            for ext in ['.png', '.jpg', '.jpeg', '.ico', '.gif', '.webp']:
                found = list(extract_path.rglob(f"{candidate}{ext}"))
                if found:
                    return str(found[0])
                
                # 遍历所有文件匹配文件名
                for p in extract_path.rglob("*"):
                    if p.is_file() and p.name.lower() == f"{candidate}{ext}".lower():
                        return str(p)
        return ""

    def _get_icon_base64(self, url_or_path: str) -> str:
        """
        获取图标Base64
        """
        try:
            content = b""
            content_type = ""
            
            # 判断是否为本地路径
            is_local = False
            if os.path.isabs(url_or_path) and os.path.exists(url_or_path):
                 is_local = True
            
            if is_local:
                # 本地文件
                try:
                    with open(url_or_path, "rb") as f:
                        content = f.read()
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(url_or_path)
                    if not content_type:
                        content_type = "image/png"
                except Exception as e:
                    logger.warning(f"读取本地图标失败: {e}")
                    return ""
            else:
                # 使用配置的代理下载
                res = RequestUtils(proxies=self._get_proxies()).get_res(url_or_path)
                if res and res.status_code == 200:
                    content = res.content
                    content_type = res.headers.get("Content-Type", "")
                    
                    # 检查是否为 HTML (避免下载到 404 页面等)
                    if "text/html" in content_type:
                        logger.warning(f"图标下载地址疑似非图片(HTML): {url_or_path}")
                        return ""

                    if not content_type or "text/plain" in content_type or "application/octet-stream" in content_type:
                        if url_or_path.lower().endswith(".jpg") or url_or_path.lower().endswith(".jpeg"):
                            content_type = "image/jpeg"
                        elif url_or_path.lower().endswith(".gif"):
                             content_type = "image/gif"
                        elif url_or_path.lower().endswith(".ico"):
                             content_type = "image/x-icon"
                        else:
                            content_type = "image/png"
            
            if content:
                b64_str = base64.b64encode(content).decode("utf-8")
                return f"data:{content_type};base64,{b64_str}"
                
        except Exception as e:
            logger.warning(f"获取图标Base64失败: {e}")
        return ""


    def __sync_site_item(self, site, group_id, group_only_name, custom_mapping: dict = None) -> bool:
        """
        同步单个站点
        """
        # 使用 MP 站点ID作为唯一标识的一部分，确保唯一性
        item_only_name = f"mp_site_{site.id}"
        
        # URL 替换逻辑：使用自定义域名配置
        site_url = site.url
        custom_mapping = custom_mapping or {}
        if site.name in custom_mapping:
            logger.info(f"使用自定义域名: {site.name} {site_url} -> {custom_mapping[site.name]}")
            site_url = custom_mapping[site.name]
        
        # 移除末尾斜杠以更好对比
        site_url = site_url.rstrip('/') if site_url else ""

        # 检查项目是否存在并获取详情
        check_url = f"{self._spanel_url.rstrip('/')}/openapi/v1/item/getInfoByOnlyName"
        remote_item = None
        
        try:
            res = RequestUtils(headers=self.__get_request_headers()).post_res(check_url, json={"onlyName": item_only_name})
            if res and res.status_code == 200:
                data = res.json()
                if data.get("code") == 0:
                    remote_item = data.get("data")
        except Exception as e:
            logger.warning(f"获取项目详情异常: {e}")

        # 准备目标数据
        target_title = site.name
        
        # 判断是否需要更新
        need_update = False
        action = "创建"
        
        if remote_item:
            action = "更新"
            # 对比字段: Title, URL
            remote_url = remote_item.get("url", "").rstrip('/')
            remote_title = remote_item.get("title", "")
            
            # 分组对比
            is_group_diff = False
            remote_group_id = remote_item.get("itemGroupID")
            remote_group_name = remote_item.get("itemGroupOnlyName")
            
            if group_id:
                if remote_group_id != group_id:
                     is_group_diff = True
            elif group_only_name:
                if remote_group_name != group_only_name:
                     is_group_diff = True
            
            # 判断是否需要更新
            if self._force_update:
                need_update = True
                logger.info(f"强制更新开启: {site.name}, 将执行更新")
            elif (remote_title != target_title or 
                remote_url != site_url or 
                is_group_diff):
                need_update = True
                logger.info(f"站点信息变更: {site.name}, 将执行更新")
            else:
                logger.debug(f"站点信息未变更: {site.name}, 跳过更新")
                return True
        else:
            need_update = True
        
        if not need_update:
            return True

        icon_url = ""
        final_base64_icon = ""
        
        # 1. 优先尝试从图标库获取
        if self._icon_repo_url:
             repo_icon_url = self._get_icon_from_repo(site)
             if repo_icon_url:
                 repo_base64 = self._get_icon_base64(repo_icon_url)
                 if repo_base64:
                     final_base64_icon = repo_base64
                     icon_url = repo_icon_url 
                     logger.debug(f"{site.name} 使用图标库图标")

        # 2. 默认逻辑
        if not final_base64_icon:
            site_icon = SiteOper().get_icon_by_domain(site.domain)
            icon_url = site_icon.url if site_icon else ""
            if not icon_url:
                icon_url = f"{site_url}/favicon.ico"

        payload = {
            "onlyName": item_only_name,
            "title": target_title,
            "url": site_url,
            "iconUrl": icon_url,
            "isSaveIcon": True 
        }
        
        # Base64 / 代理逻辑
        if final_base64_icon:
            payload["iconUrl"] = final_base64_icon
            payload["isSaveIcon"] = False
        elif self._use_proxy and icon_url:
            base64_icon = self._get_icon_base64(icon_url)
            if base64_icon:
                payload["iconUrl"] = base64_icon
                payload["isSaveIcon"] = False
        
        # 分组参数
        if group_id:
            payload["itemGroupID"] = group_id
        elif group_only_name:
            payload["itemGroupOnlyName"] = group_only_name

        # 发送请求
        if action == "更新":
            # 更新时不传 lanUrl 和 description，起到保留原有值的作用
            update_url = f"{self._spanel_url.rstrip('/')}/openapi/v1/item/update"
            return self.__send_item_request(update_url, payload, site.name, "更新")
        else:
            create_url = f"{self._spanel_url.rstrip('/')}/openapi/v1/item/create"
            return self.__send_item_request(create_url, payload, site.name, "创建")

    def __send_item_request(self, url: str, payload: dict, site_name: str, action: str) -> bool:
        """
        发送站点创建/更新请求，包含图标重试逻辑
        """
        try:
            res = RequestUtils(headers=self.__get_request_headers()).post_res(url, json=payload)
            res_json = res.json() if res and res.status_code == 200 else {}
            
            if res and res.status_code == 200 and res_json.get("code") == 0:
                logger.info(f"{action}站点成功: {site_name}")
                return True
            
            msg = str(res_json.get("msg", ""))
            if "failed to save icon file" in msg:
                logger.warning(f"{site_name} 图标下载失败({msg})，尝试忽略图标重试")
                payload["isSaveIcon"] = False
                res = RequestUtils(headers=self.__get_request_headers()).post_res(url, json=payload)
                if res and res.status_code == 200 and res.json().get("code") == 0:
                    logger.info(f"{action}站点成功(无图标): {site_name}")
                    return True
                else:
                    logger.error(f"{action}站点重试失败 {site_name}: {res.text if res else 'No Response'}")
            else:
                logger.error(f"{action}站点失败 {site_name}: {res.text if res else 'No Response'}")
                
        except Exception as e:
            logger.error(f"{action}站点异常 {site_name}: {e}")
        
        return False
