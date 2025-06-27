import glob
import os
import time
import jwt
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from webdav3.client import Client

from app.core.config import settings
from app.plugins import _PluginBase
from typing import Any, List, Dict, Tuple, Optional
from app.log import logger
from app.schemas import NotificationType
from app.utils.http import RequestUtils


class LuckyHelper(_PluginBase):
    # 插件名称
    plugin_name = "Lucky助手"
    # 插件描述
    plugin_desc = "定时备份Lucky配置文件"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/Lucky_B.png"
    # 插件版本
    plugin_version = "1.2.6"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "luckyhelper_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _host = None
    _openToken = None
    _webdav_client = None
    # 本地备份开关
    _local_backup = False  

    # 任务执行间隔
    _cron = None
    _cnt = None
    _onlyonce = False
    _notify = False
    _back_path = None

    # WebDAV配置
    _webdav_enabled = False
    _webdav_hostname = None
    _webdav_login = None
    _webdav_password = None
    _webdav_digest_auth = False
    _webdav_disable_check = False
    _webdav_max_count = None
    _webdav_dir = ""

    # 定时器
    _scheduler: Optional[BackgroundScheduler] = None

    def init_plugin(self, config: dict = None):
        # 停止现有任务
        self.stop_service()

        if config:
            self._enabled = config.get("enabled")
            self._cron = config.get("cron")
            self._cnt = config.get("cnt")
            self._notify = config.get("notify")
            # 本地备份开关
            self._local_backup = config.get("local_backup", False)
            self._onlyonce = config.get("onlyonce")
            self._back_path = config.get("back_path")
            self._host = config.get("host")
            self._openToken = config.get("openToken")

            # WebDAV配置
            self._webdav_enabled = config.get("webdav_enabled", False)
            self._webdav_hostname = config.get("webdav_hostname")
            self._webdav_login = config.get("webdav_login")
            self._webdav_password = config.get("webdav_password")
            self._webdav_digest_auth = config.get("webdav_digest_auth", False)
            self._webdav_disable_check = config.get("webdav_disable_check", False)
            try:
                self._webdav_max_count = int(config.get("webdav_max_count", 5))
            except (ValueError, TypeError):
                self._webdav_max_count = 5
            self._webdav_dir = (config.get("webdav_dir", "lucky") or "lucky").strip("/")

            # 初始化WebDAV客户端
            if self._webdav_enabled:
                webdav_config = {
                    'webdav_hostname': self._webdav_hostname,
                    'webdav_login': self._webdav_login,
                    'webdav_password': self._webdav_password,
                    'webdav_digest_auth': self._webdav_digest_auth
                }
                if self._webdav_disable_check:
                    webdav_config.update({"disable_check": True})
                self._webdav_client = Client(webdav_config)

            # 加载模块
        if self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)
            logger.info(f"自动备份服务启动，立即运行一次")
            self._scheduler.add_job(func=self.__backup, trigger='date',
                                    run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                    name="自动备份")
            # 关闭一次性开关
            self._onlyonce = False
            self.update_config({
                "onlyonce": False,
                "cron": self._cron,
                "enabled": self._enabled,
                "cnt": self._cnt,
                "notify": self._notify,
                "back_path": self._back_path,
                "host": self._host,
                "openToken": self._openToken,
                "webdav_enabled": self._webdav_enabled,
                "webdav_hostname": self._webdav_hostname,
                "webdav_login": self._webdav_login,
                "webdav_password": self._webdav_password,
                "webdav_digest_auth": self._webdav_digest_auth,
                "webdav_disable_check": self._webdav_disable_check,
                "webdav_max_count": self._webdav_max_count,
                "webdav_dir": self._webdav_dir,
                "local_backup": self._local_backup
            })

            # 启动任务
            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()

    def get_jwt(self) -> str:
        # 减少接口请求直接使用jwt
        payload = {
            "exp": int(time.time()) + 28 * 24 * 60 * 60,
            "iat": int(time.time())
        }
        encoded_jwt = jwt.encode(payload, self._openToken, algorithm="HS256")
        logger.debug(f"LuckyHelper get jwt---》{encoded_jwt}")
        return "Bearer "+encoded_jwt

    def __clean_webdav_backups(self):
        """
        清理旧的WebDAV备份文件，并返回清理前数量、需删除数量、剩余数量
        """
        try:
            remote_dir = self._webdav_dir
            list_path = remote_dir if remote_dir else "/"
            remote_files = self._webdav_client.list(list_path)
            pattern = re.compile(r"lucky_.*_(\d{8,14})\.zip$")
            filtered_files = [f for f in remote_files if pattern.match(os.path.basename(f)) and not f.endswith('/')]
            def extract_time(f):
                m = pattern.match(os.path.basename(f))
                if m:
                    ts = m.group(1)
                    try:
                        if len(ts) == 14:
                            return datetime.strptime(ts, "%Y%m%d%H%M%S")
                        elif len(ts) == 8:
                            return datetime.strptime(ts, "%Y%m%d")
                    except Exception:
                        return datetime.min
                return datetime.min
            sorted_files = sorted(filtered_files, key=extract_time)
            before_count = len(sorted_files)
            excess_count = before_count - self._webdav_max_count
            del_cnt = 0
            if excess_count > 0:
                logger.info(
                    f"WebDAV上备份文件数量为 {before_count}，超出最大保留数 {self._webdav_max_count}，需删除 {excess_count} 个备份文件")
                for file_info in sorted_files[:-self._webdav_max_count]:
                    remote_file_path = f"{remote_dir}/{os.path.basename(file_info)}" if remote_dir else os.path.basename(file_info)
                    try:
                        self._webdav_client.clean(remote_file_path)
                        logger.info(f"WebDAV上的备份文件 {remote_file_path} 已删除")
                        del_cnt += 1
                    except Exception as e:
                        logger.error(f"删除WebDAV文件 {remote_file_path} 失败: {e}")
            left_cnt = before_count - del_cnt
            return before_count, del_cnt, left_cnt
        except Exception as e:
            logger.error(f"获取WebDAV文件列表失败: {e}")
            return 0, 0, 0

    def __backup(self):
        """
        自动备份、删除备份
        """
        logger.info(f"当前时间 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))} 开始备份")

        # 备份保存路径
        bk_path = Path(self._back_path) if self._back_path else self.get_data_path()

        # 检查路径是否存在，如果不存在则创建
        if self._local_backup:
            if not bk_path.exists():
                try:
                    bk_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"创建备份路径: {bk_path}")
                except Exception as e:
                    logger.error(f"创建备份路径失败: {str(e)}")
                    return False, f"创建备份路径失败: {str(e)}"

        # 构造请求URL
        backup_url = f"{self._host}/api/configure?openToken={self._openToken}"

        webdav_bk_cnt_before = webdav_del_cnt = webdav_left_cnt = 'N/A'
        try:
            # 发送GET请求获取ZIP文件
            result = (RequestUtils(headers={"Authorization": self.get_jwt()})
                    .get_res(backup_url))
            
            # 检查响应状态码
            if result.status_code == 200:
                # 获取响应内容（ZIP文件的二进制数据）
                zip_data = result.content
                
                # 定义保存文件的路径，使用原始文件名
                zip_file_name = result.headers.get('Content-Disposition', '').split('filename=')[-1].strip('"')
                zip_file_path = bk_path / zip_file_name if self._local_backup else Path(zip_file_name)
                
                # 保存文件到本地（仅在本地备份开启时）
                if self._local_backup:
                    with open(zip_file_path, 'wb') as zip_file:
                        zip_file.write(zip_data)
                else:
                    # 如果不开本地备份，先写到临时文件再上传
                    with open(zip_file_name, 'wb') as zip_file:
                        zip_file.write(zip_data)
                
                success = True
                msg = f"备份完成 备份文件 {zip_file_path if self._local_backup else zip_file_name}"
                logger.info(msg)

                # 如果启用了WebDAV备份，上传到WebDAV服务器
                if self._webdav_enabled:
                    webdav_success = self.__upload_to_webdav(zip_file_path if self._local_backup else Path(zip_file_name))
                    if webdav_success:
                        msg += "\nWebDAV备份成功"
                        # 清理并统计清理前数量、清理数量和剩余数量
                        webdav_bk_cnt_before, webdav_del_cnt, webdav_left_cnt = self.__clean_webdav_backups()
                    else:
                        msg += "\nWebDAV备份失败"
                # 如果不开本地备份，上传后删除临时文件
                if not self._local_backup and Path(zip_file_name).exists():
                    try:
                        Path(zip_file_name).unlink()
                    except Exception as e:
                        logger.warning(f"删除临时备份文件失败: {e}")
            else:
                success = False
                msg = f"创建备份失败，状态码: {result.status_code}, 原因: {result.json().get('msg', '未知错误')}"
                logger.error(msg)
        except Exception as e:
            success = False
            msg = f"创建备份失败，异常: {str(e)}"
            logger.error(msg)

        # 清理本地备份
        bk_cnt = 0
        del_cnt = 0
        if self._local_backup and self._cnt:
            # 获取指定路径下所有以"lucky"开头的文件，按照创建时间从旧到新排序
            files = sorted(glob.glob(f"{bk_path}/lucky**"), key=os.path.getctime)
            bk_cnt = len(files)
            # 计算需要删除的文件数
            del_cnt = bk_cnt - int(self._cnt)
            if del_cnt > 0:
                logger.info(
                    f"获取到 {bk_path} 路径下备份文件数量 {bk_cnt} 保留数量 {int(self._cnt)} 需要删除备份文件数量 {del_cnt}")

                # 遍历并删除最旧的几个备份
                for i in range(del_cnt):
                    os.remove(files[i])
                    logger.debug(f"删除备份文件 {files[i]} 成功")
            else:
                logger.info(
                    f"获取到 {bk_path} 路径下备份文件数量 {bk_cnt} 保留数量 {int(self._cnt)} 无需删除")

        # 发送通知
        if self._notify:
            notify_lines = []
            notify_lines.append("━━━━━━━━━━━━━━")
            notify_lines.append(f"{'✅' if success else '❌'} LuckyHelper备份{'成功' if success else '失败'}")
            # 本地备份区块
            if self._local_backup:
                notify_lines.append("━━━━━━━━━━━━━━")
                notify_lines.append("📦 本地备份统计：")
                notify_lines.append(f"📁 路径：{bk_path}")
                notify_lines.append(f"🗂️ 备份文件数量：{bk_cnt}")
                notify_lines.append(f"🧹 清理备份数量：{del_cnt}")
                notify_lines.append(f"📦 剩余备份数量：{bk_cnt - del_cnt}")
            # WebDAV备份区块
            if self._webdav_enabled:
                notify_lines.append("━━━━━━━━━━━━━━")
                notify_lines.append("☁️ WebDAV备份统计：")
                notify_lines.append(f"📁 目录：{self._webdav_dir or '/'}")
                notify_lines.append(f"🗂️ 备份文件数量：{webdav_bk_cnt_before}")
                notify_lines.append(f"🧹 清理备份数量：{webdav_del_cnt}")
                notify_lines.append(f"📦 剩余备份数量：{webdav_left_cnt}")
            notify_lines.append("━━━━━━━━━━━━━━")
            notify_lines.append(f"⏱ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")
            self.post_message(
                mtype=NotificationType.Plugin,
                title="【💾 Lucky助手】备份完成：",
                text="\n".join(notify_lines)
            )

        return success, msg

    def __upload_to_webdav(self, local_file_path: Path) -> bool:
        """
        上传文件到WebDAV服务器，自动递归创建父目录
        """
        try:
            if not self._webdav_client:
                logger.error("WebDAV客户端未初始化")
                return False

            file_name = os.path.basename(local_file_path)
            remote_dir = self._webdav_dir
            remote_path = f"{remote_dir}/{file_name}" if remote_dir else file_name
            remote_file_path = urljoin(f'{self._webdav_hostname}/', remote_path)
            logger.info(f"远程备份路径为：{remote_file_path}")

            # 自动递归创建所有父目录
            dir_parts = remote_path.split('/')[:-1]
            current = ""
            for part in dir_parts:
                current = f"{current}/{part}" if current else part
                try:
                    self._webdav_client.mkdir(current)
                except Exception as e:
                    logger.debug(f"创建WebDAV目录{current}时异常(可能已存在): {e}")

            # 上传文件
            self._webdav_client.upload_sync(remote_path=remote_path, local_path=str(local_file_path))

            # 检查文件是否上传成功
            if self._webdav_client.check(remote_path):
                logger.info(f"WebDAV上传成功，远程备份路径：{remote_file_path}")
                return True
            else:
                logger.error(f"WebDAV上传失败，远程备份路径：{remote_file_path}")
                return False

        except Exception as e:
            logger.error(f"上传到WebDAV服务器失败: {e}")
            if hasattr(e, 'response'):
                logger.error(f"服务器响应: {e.response.text}")
            return False

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        if self._enabled and self._cron:
            return [{
                "id": "LuckyHelper",
                "name": "Lucky助手备份定时服务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.__backup,
                "kwargs": {}
            }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        version = getattr(settings, "VERSION_FLAG", "v1")
        cron_field_component = "VCronField" if version == "v2" else "VTextField"
        return [
            {
                'component': 'VForm',
                'content': [
                    # 基础设置卡片
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-0'},
                        'content': [
                            {'component': 'VCardTitle', 'props': {'class': 'd-flex align-center'}, 'content': [
                                {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-cog'},
                                {'component': 'span', 'text': '基础设置'}
                            ]},
                            {'component': 'VDivider'},
                            {'component': 'VCardText', 'content': [
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件', 'color': 'primary'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'notify', 'label': '开启通知', 'color': 'info'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'onlyonce', 'label': '立即运行一次', 'color': 'success'}}]},
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VTextField', 'props': {'model': 'host', 'label': 'Lucky地址', 'placeholder': 'http(s)://ip:port', 'prepend-inner-icon': 'mdi-server-network'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VTextField', 'props': {'model': 'openToken', 'label': 'OpenToken', 'placeholder': 'Lucky openToken 设置里面打开', 'prepend-inner-icon': 'mdi-key', 'type': 'password'}}]},
                                ]},
                            ]}
                        ]
                    },
                    # 本地备份设置卡片
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-3'},
                        'content': [
                            {'component': 'VCardTitle', 'props': {'class': 'd-flex align-center'}, 'content': [
                                {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-folder-home'},
                                {'component': 'span', 'text': '本地备份设置'}
                            ]},
                            {'component': 'VDivider'},
                            {'component': 'VCardText', 'content': [
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'local_backup', 'label': '启用本地备份', 'color': 'primary'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': cron_field_component, 'props': {'model': 'cron', 'label': '备份周期', 'placeholder': '0 8 * * *', 'prepend-inner-icon': 'mdi-clock-outline'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VTextField', 'props': {'model': 'cnt', 'label': '保留份数', 'type': 'number', 'placeholder': '最大保留备份数，默认5份', 'prepend-inner-icon': 'mdi-counter'}}]},
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12}, 'content': [{'component': 'VTextField', 'props': {'model': 'back_path', 'label': '备份保存路径', 'placeholder': '如未映射默认即可', 'prepend-inner-icon': 'mdi-folder'}}]},
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                                        {'component': 'VAlert', 'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '备份文件路径默认为本地映射的config/plugins/LuckyHelper。',
                                            'border': 'start',
                                            'border-color': 'primary',
                                            'icon': 'mdi-information',
                                            'elevation': 1,
                                            'rounded': 'lg',
                                            'density': 'compact'
                                        }}
                                    ]}
                                ]}
                            ]}
                        ]
                    },
                    # WebDAV远程备份设置卡片
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-3'},
                        'content': [
                            {'component': 'VCardTitle', 'props': {'class': 'd-flex align-center'}, 'content': [
                                {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-cloud-sync'},
                                {'component': 'span', 'text': 'WebDAV远程备份设置'}
                            ]},
                            {'component': 'VDivider'},
                            {'component': 'VCardText', 'content': [
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'webdav_enabled', 'label': '启用WebDAV远程备份', 'color': 'primary'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'webdav_digest_auth', 'label': '启用Digest认证', 'color': 'info'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'webdav_disable_check', 'label': '忽略目录校验', 'color': 'warning'}}]},
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VTextField', 'props': {'model': 'webdav_hostname', 'label': 'WebDAV服务器地址', 'placeholder': '例如: https://dav.example.com', 'prepend-inner-icon': 'mdi-cloud'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VTextField', 'props': {'model': 'webdav_dir', 'label': 'WebDAV备份子目录', 'placeholder': '如/lucky', 'prepend-inner-icon': 'mdi-folder-network'}}]},
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VTextField', 'props': {'model': 'webdav_login', 'label': 'WebDAV登录名', 'type': 'password','placeholder': '请输入WebDAV登录名', 'prepend-inner-icon': 'mdi-account-key'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VTextField', 'props': {'model': 'webdav_password', 'label': 'WebDAV密码', 'type': 'password', 'placeholder': '请输入WebDAV密码', 'prepend-inner-icon': 'mdi-lock-check'}}]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VTextField', 'props': {'model': 'webdav_max_count', 'label': 'WebDAV备份保留数量', 'type': 'number', 'placeholder': '例如: 7', 'prepend-inner-icon': 'mdi-counter'}}]},
                                ]},
                            ]}
                        ]
                    },
                    # 说明卡片
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-3'},
                        'content': [
                            {'component': 'VCardTitle', 'props': {'class': 'd-flex align-center'}, 'content': [
                                {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-information'},
                                {'component': 'span', 'text': '使用说明'}
                            ]},
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
                                                {'component': 'div', 'props': {'class': 'd-flex align-items-start'}, 'content': [
                                                    {'component': 'VIcon', 'props': {'color': 'primary', 'class': 'mt-1 mr-2'}, 'text': 'mdi-calendar-clock'},
                                                    {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1', 'style': 'color: #444;'}, 'text': '备份周期说明'}
                                                ]},
                                                {'component': 'div', 'props': {'class': 'text-body-2 ml-8'}, 'text': '支持标准cron表达式，建议每天定时自动备份。'}
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {'lines': 'two'},
                                            'content': [
                                                {'component': 'div', 'props': {'class': 'd-flex align-items-start'}, 'content': [
                                                    {'component': 'VIcon', 'props': {'color': 'warning', 'class': 'mt-1 mr-2'}, 'text': 'mdi-alert'},
                                                    {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1', 'style': 'color: #444;'}, 'text': '注意事项'}
                                                ]},
                                                {'component': 'div', 'props': {'class': 'text-body-2 ml-8'}, 'text': '请确保WebDAV服务器地址、账号、密码等信息填写正确，如果配置正确且有提示错误，请打开【忽略目录校验】在尝试。'}
                                            ]
                                        },
                                        {
                                            'component': 'VListItem',
                                            'props': {'lines': 'two'},
                                            'content': [
                                                {'component': 'div', 'props': {'class': 'd-flex align-items-start'}, 'content': [
                                                    {'component': 'VIcon', 'props': {'color': 'error', 'class': 'mt-1 mr-2'}, 'text': 'mdi-heart'},
                                                    {'component': 'div', 'props': {'class': 'text-subtitle-1 font-weight-regular mb-1', 'style': 'color: #444;'}, 'text': '致谢'}
                                                ]},
                                                {'component': 'div', 'props': {'class': 'text-body-2 ml-8'}, 'text': '参考了 thsrite/MoviePilot-Plugins 项目，特此感谢 thsrite 大佬！'}
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
            "notify": True,
            "onlyonce": False,
            "cron": "0 8 * * *",
            "cnt": 5,
            "host": "",
            "openToken": "",
            "back_path": str(self.get_data_path()),
            "local_backup": True,
            "webdav_enabled": False,
            "webdav_hostname": "",
            "webdav_login": "",
            "webdav_password": "",
            "webdav_dir": "/lucky",
            "webdav_max_count": 5,
            "webdav_digest_auth": False,
            "webdav_disable_check": False
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("退出插件失败：%s" % str(e))