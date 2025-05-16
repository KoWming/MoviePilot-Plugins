import re
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional, Any

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType, NotificationType
from app.utils.http import RequestUtils


class CloudflaresSubscribe(_PluginBase):
    # 插件名称
    plugin_name = "Cloudflare订阅"
    # 插件描述
    plugin_desc = "自动订阅Cloudflare免费DNS服务，支持批量订阅管理。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/Cloudflare_C.png"
    # 插件版本
    plugin_version = "1.0.5"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "cloudflaressubscribe_"
    # 加载顺序
    plugin_order = 12
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False      # 插件启用状态
    _customhosts = False  # CustomHosts 插件状态
    _scheduler = None     # 定时器对象
    _cron = None         # 定时任务表达式
    _onlyonce = False    # 是否立即运行一次
    _notify = False      # 是否开启通知
    _url = None          # 订阅地址配置
    _use_proxy = True   # 是否使用代理

    # 定时器
    _scheduler: Optional[BackgroundScheduler] = None

    def init_plugin(self, config: dict = None):
        """
        初始化插件
        """
        # 停止现有任务
        self.stop_service()
        
        # 设置默认值
        self._enabled = False
        self._cron = "0 8 * * *"
        self._notify = True
        self._onlyonce = False
        self._url = ""
        self._use_proxy = True

        # 从配置中加载设置
        if config:
            self._enabled = config.get("enabled", False)
            self._cron = config.get("cron", "0 8 * * *")
            self._notify = config.get("notify", False)
            self._onlyonce = config.get("onlyonce", False)
            self._url = config.get("url", "")
            self._use_proxy = config.get("use_proxy", True)

            # 处理立即运行一次的情况
            if self._onlyonce:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                logger.info(f"Cloudflare订阅服务启动，立即运行一次")
                
                # 添加一次性任务
                self._scheduler.add_job(
                    func=self.__cloudflaresSubscribe,
                    trigger='date',
                    run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                    name="Cloudflare自动订阅"
                )
                
                # 更新配置，关闭一次性开关
                self.update_config({
                    "onlyonce": False,
                    "cron": self._cron,
                    "enabled": self._enabled,
                    "notify": self._notify,
                    "url": self._url,
                    "use_proxy": self._use_proxy
                })
                
                # 启动任务
                if self._scheduler.get_jobs():
                    self._scheduler.print_jobs()
                    self._scheduler.start()

    def __cloudflaresSubscribe(self):
        """
        处理Cloudflare订阅
        """
        self._cf_path = self.get_data_path()
        
        # 获取自定义Hosts插件，若无设置则停止
        customHosts = self.get_config("CustomHosts")
        self._customhosts = customHosts and customHosts.get("enabled")
        if not self._customhosts:
            logger.error(f"Cloudflare订阅依赖于自定义Hosts插件，请先安装并启用该插件")
            return
        
        # 解析订阅配置
        subscriptions = self.__parse_subscriptions()
        if not subscriptions:
            logger.error("没有找到有效的订阅配置")
            return

        # 获取当前hosts内容
        hosts = customHosts.get("hosts") or ""
        if isinstance(hosts, str):
            hosts = str(hosts).split('\n')
        
        # 初始化变量
        updated = False
        final_hosts = []
        in_subscription = False
        
        # 第一步：保留原有内容，标记订阅部分
        for host in hosts:
            host_line = host.rstrip('\n')
            
            # 检查是否是订阅开始标记
            if "# =====" in host_line and "订阅开始" in host_line:
                # 提取订阅名称
                sub_name = host_line.split("# =====")[1].split("订阅开始")[0].strip()
                if sub_name:
                    in_subscription = True
                    continue
            
            # 检查是否是订阅结束标记
            if "# =====" in host_line and "订阅结束" in host_line and in_subscription:
                in_subscription = False
                continue
            
            # 如果不在订阅区域内，保留该行
            if not in_subscription:
                final_hosts.append(host_line + '\n')
            
        # 处理每个订阅
        all_subscription_hosts = []
        
        for name, url in subscriptions:
            try:
                logger.info(f"开始处理订阅：{name}")
                # 添加User-Agent和其他请求头，避免被网站阻止
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/plain, text/html, */*",
                    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                    "Cache-Control": "no-cache"
                }
                
                # 获取代理设置
                proxies = self._get_proxies()
                
                max_retries = 3
                retry_count = 0
                response = None
                while retry_count < max_retries:
                    try:
                        # 使用代理（如果有）发送请求
                        if proxies:
                            response = RequestUtils(headers=headers, proxies=proxies).get_res(url, timeout=30)
                        else:
                            response = RequestUtils(headers=headers).get_res(url, timeout=30)
                        
                        if response and response.status_code == 200:
                            break  # 请求成功，跳出重试循环
                        else:
                            error_msg = f"订阅 {name} 请求失败：HTTP {response.status_code if response else 'No Response'}"
                            logger.warning(f"第 {retry_count + 1} 次尝试：{error_msg}")
                            retry_count += 1
                            if retry_count < max_retries:
                                time.sleep(5)  # 在重试之前等待5秒
                    except Exception as e:
                        error_msg = f"订阅 {name} 请求异常：{str(e)}"
                        logger.warning(f"第 {retry_count + 1} 次尝试：{error_msg}")
                        retry_count += 1
                        if retry_count < max_retries:
                            time.sleep(5)  # 在重试之前等待5秒

                if retry_count == max_retries and (not response or response.status_code != 200):
                    error_msg = f"订阅 {name} 请求失败，已重试 {max_retries} 次"
                    logger.error(error_msg)
                    if self._notify:
                        self.post_message(
                            mtype=NotificationType.Plugin,
                            title=f"【Cloudflares订阅更新失败】",
                            text=f"{name} 订阅地址：{url}\n{error_msg}"
                        )
                    continue

                content = response.text
                
                # 检测是否为HTML内容
                html_indicators = ["<!DOCTYPE", "<html", "<body", "<script", "<input", "</div>"]
                is_html = any(indicator.lower() in content.lower() for indicator in html_indicators)
                
                if is_html:
                    error_msg = f"订阅 {name} 返回了HTML页面而不是hosts文件内容，可能是重定向或需要认证"
                    logger.error(error_msg)
                    if self._notify:
                        self.post_message(
                            mtype=NotificationType.Plugin,
                            title=f"【Cloudflares订阅更新失败】",
                            text=f"{name} 订阅地址：{url}\n{error_msg}"
                        )
                    continue
                
                # 尝试清理内容
                content = self.__clean_hosts_content(content)
                
                # 检测是否为有效的hosts格式
                valid_line_pattern = False
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('#', 1)[0].strip().split()
                    if len(parts) >= 2 and self.__is_valid_ip(parts[0]):
                        valid_line_pattern = True
                        break
                
                if not valid_line_pattern:
                    error_msg = f"订阅 {name} 内容无效：未找到任何有效的hosts记录"
                    logger.error(error_msg)
                    if self._notify:
                        self.post_message(
                            mtype=NotificationType.Plugin,
                            title=f"【Cloudflares订阅更新失败】",
                            text=f"{name} 订阅地址：{url}\n{error_msg}"
                        )
                    continue
                
                logger.info(f"成功获取订阅 {name} 的内容，大小：{len(content)} 字节")
                
                # 处理订阅内容，解析hosts
                valid_hosts_count = 0
                subscription_hosts = []
                
                # 添加订阅标题注释
                subscription_hosts.append(f"# ===== {name} 订阅开始 ===== #\n")
                
                # 处理每行hosts
                for line in content.splitlines():
                    line = line.strip()
                    # 跳过空行或注释行
                    if not line or line.startswith('#'):
                        continue
                    
                    # 跳过明显的HTML标签
                    if line.startswith('<') and '>' in line:
                        continue
                        
                    # 解析IP和域名，处理行内注释
                    parts = line.split('#', 1)[0].strip().split()
                    if len(parts) >= 2:
                        ip = parts[0]
                        domain = parts[1]
                        
                        # 简单验证IP格式
                        if self.__is_valid_ip(ip):
                            subscription_hosts.append(f"{ip} {domain}\n")
                            valid_hosts_count += 1
                        else:
                            # 只记录警告，但不显示明显的HTML内容
                            if not any(html_tag in ip.lower() for html_tag in ["<html", "<script", "<body", "<!doctype"]):
                                logger.warning(f"忽略无效的IP记录：{line}")
                    else:
                        # 只记录警告，但不显示明显的HTML内容
                        if not any(html_tag in line.lower() for html_tag in ["<html", "</html>", "<script", "</script>", "<body", "</body>"]):
                            logger.warning(f"忽略格式错误的hosts记录：{line}")
                
                # 添加订阅结束注释
                subscription_hosts.append(f"# ===== {name} 订阅结束 ({valid_hosts_count} 条记录) ===== #\n")
                
                # 只有在有有效记录时才添加到总列表
                if valid_hosts_count > 0:
                    all_subscription_hosts.extend(subscription_hosts)
                    logger.info(f"订阅 {name} 处理完成，共添加 {valid_hosts_count} 条有效hosts记录")
                    updated = True
                    
                    if self._notify:
                        self.post_message(
                            mtype=NotificationType.Plugin,
                            title=f"【Cloudflares订阅更新成功】",
                            text=f"{name} 订阅地址：{url}\n成功添加 {valid_hosts_count} 条hosts记录"
                        )
                else:
                    logger.warning(f"订阅 {name} 未找到有效的hosts记录，跳过更新")
                    if self._notify:
                        self.post_message(
                            mtype=NotificationType.Plugin,
                            title=f"【Cloudflares订阅无有效内容】",
                            text=f"{name} 订阅地址：{url}\n未找到有效的hosts记录"
                        )
            except Exception as e:
                error_msg = f"处理订阅 {name} 时出错：{str(e)}"
                logger.error(error_msg)
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.Plugin,
                        title=f"【Cloudflares订阅更新失败】",
                        text=f"{name} 订阅地址：{url}\n{error_msg}"
                    )
        
        # 合并现有hosts和所有订阅hosts
        if updated and all_subscription_hosts:
            # 添加空行分隔（如果最后一行不是空行）
            if final_hosts and final_hosts[-1].strip():
                final_hosts.append('\n')
                
            # 合并hosts
            new_hosts = ''.join(final_hosts + all_subscription_hosts)
            
            # 更新自定义Hosts
            err_hosts = customHosts.get("err_hosts") or ""
            self.update_config(
                {
                    "hosts": new_hosts,
                    "err_hosts": err_hosts,
                    "enabled": True
                }, "CustomHosts"
            )
            
            # 触发自定义hosts插件重载
            logger.info("通知CustomHosts插件重载...")
            self.eventmanager.send_event(EventType.PluginReload,
                                        {
                                            "plugin_id": "CustomHosts"
                                        })
            
            logger.info(f"Cloudflare订阅更新完成，hosts已更新")
        elif not updated:
            logger.info("所有订阅均未更新，保持原有hosts不变")

    def __is_valid_ip(self, ip: str) -> bool:
        """
        验证IP地址格式是否有效，支持IPv4和IPv6
        :param ip: IP地址字符串
        :return: 是否有效
        """
        # 确保移除任何可能的注释
        ip = ip.strip()
        # 检查是否为注释行
        if not ip or ip.startswith('#'):
            return False
        
        # IPv4验证
        if '.' in ip and ':' not in ip:
            # 检查是否有非法字符
            if any(c not in '0123456789.' for c in ip):
                return False
            
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                # 检查空段
                if not part:
                    return False
                
                # 检查前导零（如01）- 但允许单个0
                if len(part) > 1 and part[0] == '0':
                    return False
                
                # 检查数值范围
                try:
                    num = int(part)
                    if num < 0 or num > 255:
                        return False
                except ValueError:
                    return False
            
            return True
            
        # IPv6验证
        elif ':' in ip:
            # 处理IPv4映射的IPv6地址 (如 ::ffff:192.0.2.128)
            if '.' in ip:
                ipv4_part = ip.split(':')[-1]
                if not self.__is_valid_ip(ipv4_part):  # 递归检查IPv4部分
                    return False
                # 替换IPv4部分为一个占位符，以便进行后续IPv6验证
                ip = ip.rsplit(':', 1)[0] + ':0'
            
            # 基本格式检查
            if ':::' in ip:  # 不允许连续3个及以上冒号
                return False
            
            # 处理双冒号压缩格式 (::)
            if '::' in ip:
                if ip.count('::') > 1:  # 最多只能有一个::
                    return False
            
            # 分割并计算段数
            if '::' in ip:
                parts = [p for p in ip.replace('::', ':z:').split(':') if p]
                if 'z' in parts:
                    z_index = parts.index('z')
                    parts.remove('z')
                    # 计算省略的段数
                    missing_parts = 8 - len(parts)
                    if missing_parts <= 0:
                        return False  # 使用::但没有省略段
                    # 插入省略的段
                    for _ in range(missing_parts):
                        parts.insert(z_index, '0')
            else:
                parts = ip.split(':')
            
            # IPv6应该有8段
            if len(parts) != 8:
                return False
            
            # 验证每一段
            for part in parts:
                # 每段应该是1-4位十六进制数
                if not part or len(part) > 4:
                    return False
                
                # 检查是否为有效的十六进制数
                try:
                    int(part, 16)
                except ValueError:
                    return False
            
            return True
        
        return False
        
    def __clean_hosts_content(self, content: str) -> str:
        """
        清理hosts内容，移除HTML标签和其他非hosts格式的内容
        :param content: 原始内容
        :return: 清理后的内容
        """
        # 如果内容看起来像HTML，尝试提取<pre>标签中的内容
        if "<!DOCTYPE" in content or "<html" in content:
            # 尝试提取<pre>标签中的内容，这通常是格式化的文本
            pre_match = re.search(r'<pre[^>]*>(.*?)</pre>', content, re.DOTALL)
            if pre_match:
                return pre_match.group(1)
            
            # 尝试提取<body>标签中的纯文本
            body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
            if body_match:
                body_content = body_match.group(1)
                # 移除所有HTML标签
                clean_content = re.sub(r'<[^>]*>', '', body_content)
                return clean_content
        
        # 移除可能的JavaScript代码块
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        
        # 移除单行HTML标签
        content = re.sub(r'<[^>]*>', '', content)
        
        # 移除空行
        lines = [line for line in content.splitlines() if line.strip()]
        
        return '\n'.join(lines)
        
    def __parse_subscriptions(self) -> List[Tuple[str, str]]:
        """
        解析用户输入的订阅配置
        格式：订阅名称|订阅地址
        :return: 解析后的订阅列表，每个元素为(订阅名称, 订阅地址)的元组
        """
        if not self._url:
            return []
        
        subscriptions = []
        for line in self._url.splitlines():
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('|', 1)
            if len(parts) != 2:
                logger.error(f"订阅配置格式错误: {line}，正确格式为：订阅名称|订阅地址")
                continue
            
            name, url = parts[0].strip(), parts[1].strip()
            if not name or not url:
                logger.error(f"订阅名称和地址不能为空: {line}")
                continue
            
            if not url.startswith(('http://', 'https://')):
                logger.error(f"订阅地址必须以http://或https://开头: {url}")
                continue
            
            subscriptions.append((name, url))
        
        return subscriptions

    def _get_proxies(self):
        """
        获取代理设置
        """
        if not self._use_proxy:
            logger.info("未启用代理")
            return None
            
        try:
            # 获取系统代理设置
            if hasattr(settings, 'PROXY') and settings.PROXY:
                logger.info(f"使用系统代理: {settings.PROXY}")
                return settings.PROXY
            else:
                logger.warning("系统代理未配置")
                return None
        except Exception as e:
            logger.error(f"获取代理设置出错: {str(e)}")
            return None

    def get_state(self) -> bool:
        """
        获取插件状态
        :return: 插件是否启用
        """
        return bool(self._enabled)

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
                "id": "CloudflaresSubscribe",
                "name": "Cloudflare订阅",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.__cloudflaresSubscribe,
                "kwargs": {}
            }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        # 动态判断MoviePilot版本，决定定时任务输入框组件类型
        version = getattr(settings, "VERSION_FLAG", "v1")
        cron_field_component = "VCronField" if version == "v2" else "VTextField"

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
                                    'md': 3
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
                                    'md': 3
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'use_proxy',
                                            'label': '使用代理',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 3
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
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 3
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
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
                                "component": "VCol",
                                "props": {"cols": 12, "md": 8},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "url",
                                            "label": "订阅地址",
                                            "rows": 6,
                                            "placeholder": "每一行一个配置，配置方式：\n订阅名称|订阅地址https://example.com/"
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': cron_field_component,
                                        'props': {
                                            'model': 'cron',
                                            'label': '订阅周期(cron)',
                                            'placeholder': '0 8 * * *',
                                            'hint': '输入5位cron表达式，默认每天8点运行。',
                                            'persistent-hint': True
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
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '插件依赖于【自定义Hosts】插件，使用前请先安装并启用该插件。'
                                                    '如果订阅失败可以尝试使用加速地址拼接订阅地址。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": self._enabled,
            "notify": self._notify,
            "onlyonce": self._onlyonce,
            "cron": self._cron,
            "url": self._url,
            "use_proxy": self._use_proxy
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
