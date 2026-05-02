import ipaddress
import re
import threading
import time
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from xml.etree import ElementTree

import pytz
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from requests import Response

from app.core.config import settings
from app.helper.browser import PlaywrightHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.utils.common import retry
from app.utils.system import SystemUtils

lock = threading.Lock()


class ZTEHosts(_PluginBase):
    # 插件名称
    plugin_name = "中兴问天Hosts"
    # 插件描述
    plugin_desc = "定时将本地Hosts同步至中兴问天路由自定义Hosts。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/ZTEHosts.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "ztehosts_"
    # 加载顺序
    plugin_order = 63
    # 可使用的用户级别
    auth_level = 1


    # 是否开启
    _enabled = False
    # 立即运行一次
    _onlyonce = False
    # 任务执行间隔
    _cron = None
    # 发送通知
    _notify = False
    # 路由地址
    _router_url = None
    # 管理密码
    _password = None
    # 忽略的IP或域名
    _ignore = None
    # 定时器
    _scheduler = None
    # 退出事件
    _event = threading.Event()


    def init_plugin(self, config: dict = None):
        if not config:
            return

        self._enabled = config.get("enabled")
        self._onlyonce = config.get("onlyonce")
        self._cron = config.get("cron")
        self._notify = config.get("notify")
        self._router_url = config.get("router_url")
        self._password = config.get("router_password")
        self._ignore = config.get("ignore")

        # 停止现有任务
        self.stop_service()

        # 启动服务
        self._scheduler = BackgroundScheduler(timezone=settings.TZ)
        if self._onlyonce:
            logger.info(f"{self.plugin_name}服务，立即运行一次")
            self._scheduler.add_job(
                func=self.fetch_and_update_hosts,
                trigger="date",
                run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                name=f"{self.plugin_name}",
            )
            # 关闭一次性开关
            self._onlyonce = False
            config["onlyonce"] = False
            self.update_config(config=config)

        # 启动服务
        if self._scheduler.get_jobs():
            self._scheduler.print_jobs()
            self._scheduler.start()

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return []

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
            logger.info(f"{self.plugin_name}定时服务启动，时间间隔 {self._cron} ")
            return [{
                "id": self.__class__.__name__,
                "name": f"{self.plugin_name}服务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.fetch_and_update_hosts,
                "kwargs": {}
            }]
        return []

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._event.set()
                    self._scheduler.shutdown()
                    self._event.clear()
                self._scheduler = None
        except Exception as e:
            logger.info(str(e))

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
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [
                                        {'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件', 'color': 'primary'}}
                                    ]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [
                                        {'component': 'VSwitch', 'props': {'model': 'notify', 'label': '发送通知', 'color': 'info'}}
                                    ]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [
                                        {'component': 'VSwitch', 'props': {'model': 'onlyonce', 'label': '立即运行一次', 'color': 'success'}}
                                    ]}
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                                        {'component': cron_field_component, 'props': {'model': 'cron', 'label': '执行周期', 'placeholder': '0 9 * * *', 'prepend-inner-icon': 'mdi-clock-outline', 'hint': '使用cron表达式指定执行周期，如 0 9 * * *', 'persistent-hint': True}}
                                    ]}
                                ]}
                            ]}
                        ]
                    },
                    # 路由登录设置卡片
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-3'},
                        'content': [
                            {'component': 'VCardTitle', 'props': {'class': 'd-flex align-center'}, 'content': [
                                {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-router-network'},
                                {'component': 'span', 'text': '路由登录设置'}
                            ]},
                            {'component': 'VDivider'},
                            {'component': 'VCardText', 'content': [
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                        {'component': 'VTextField', 'props': {'model': 'router_url', 'label': '路由地址', 'placeholder': 'http://192.168.5.1 或 https://router.example.com', 'prepend-inner-icon': 'mdi-web'}}
                                    ]},
                                    {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [
                                        {'component': 'VTextField', 'props': {'model': 'router_password', 'label': '管理密码', 'type': 'password', 'placeholder': '请输入路由后台管理密码', 'prepend-inner-icon': 'mdi-lock', 'autocomplete': 'new-password'}}
                                    ]}
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                                        {'component': 'VAlert', 'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '插件会使用 MoviePilot 内置浏览器自动登录路由后台，获取 SID 后读取并同步自定义Hosts；sl-session 仅在存在时附带。',
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
                    # 同步规则设置卡片
                    {
                        'component': 'VCard',
                        'props': {'class': 'mt-3'},
                        'content': [
                            {'component': 'VCardTitle', 'props': {'class': 'd-flex align-center'}, 'content': [
                                {'component': 'VIcon', 'props': {'style': 'color: #16b1ff;', 'class': 'mr-2'}, 'text': 'mdi-format-list-checks'},
                                {'component': 'span', 'text': '同步规则设置'}
                            ]},
                            {'component': 'VDivider'},
                            {'component': 'VCardText', 'content': [
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                                        {'component': 'VTextField', 'props': {'model': 'ignore', 'label': '忽略的IP或域名', 'placeholder': '10.10.10.1|wiki.movie-pilot.org', 'prepend-inner-icon': 'mdi-filter-off', 'hint': '多个规则使用 | 分隔；localhost、回环地址和 IPv6 会自动忽略', 'persistent-hint': True}}
                                    ]}
                                ]},
                                {'component': 'VRow', 'content': [
                                    {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                                        {'component': 'VAlert', 'props': {
                                            'type': 'success',
                                            'variant': 'tonal',
                                            'text': '执行流程：浏览器登录路由后台 -> 处理其他终端登录抢占 -> 读取远程Hosts -> 合并本地Hosts -> 提交至中兴问天自定义Hosts。',
                                            'icon': 'mdi-sync',
                                            'elevation': 1,
                                            'rounded': 'lg',
                                            'density': 'compact'
                                        }}
                                    ]}
                                ]}
                            ]}
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "notify": True,
            "onlyonce": False,
            "cron": "0 9 * * *",
            "router_url": "http://192.168.5.1",
            "router_password": "",
            "ignore": ""
        }

    def get_page(self) -> List[dict]:
        pass

    def fetch_and_update_hosts(self):
        """
        登录路由并用本地Hosts更新远程Hosts
        """
        success = False
        status_text = "同步失败"
        detail_message = "未知错误"
        local_count = 0
        remote_count = 0
        merged_count = 0
        submitted = False

        if not self._router_url or not self._password:
            logger.error("缺少路由地址或管理密码")
            detail_message = "缺少路由地址或管理密码，无法同步"
            self.__send_message(
                title="【🛜 中兴问天Hosts】任务完成：",
                success=success,
                status_text=status_text,
                detail_message=detail_message,
                local_count=local_count,
                remote_count=remote_count,
                merged_count=merged_count,
                submitted=submitted,
            )
            return

        logger.info("开始执行中兴问天Hosts同步任务")
        local_hosts = self.__get_local_hosts()
        local_count = len(local_hosts)
        if not local_hosts:
            detail_message = "获取本地hosts失败，更新失败，请检查日志"
            self.__send_message(
                title="【🛜 中兴问天Hosts】任务完成：",
                success=success,
                status_text=status_text,
                detail_message=detail_message,
                local_count=local_count,
                remote_count=remote_count,
                merged_count=merged_count,
                submitted=submitted,
            )
            return

        login_context = self.__login_with_browser()
        if not login_context:
            detail_message = "路由登录失败，请检查路由地址和管理密码"
            self.__send_message(
                title="【🛜 中兴问天Hosts】任务完成：",
                success=success,
                status_text=status_text,
                detail_message=detail_message,
                local_count=local_count,
                remote_count=remote_count,
                merged_count=merged_count,
                submitted=submitted,
            )
            return

        remote_hosts = self.__fetch_remote_hosts(login_context)
        if remote_hosts is None:
            detail_message = "获取远程hosts失败，更新失败，请检查日志"
            self.__send_message(
                title="【🛜 中兴问天Hosts】任务完成：",
                success=success,
                status_text=status_text,
                detail_message=detail_message,
                local_count=local_count,
                remote_count=remote_count,
                merged_count=merged_count,
                submitted=submitted,
            )
            return

        remote_count = len(remote_hosts)
        logger.info(f"远程Hosts获取完成，共 {remote_count} 条")
        updated_hosts = self.__update_remote_hosts_with_local(local_hosts, remote_hosts)
        merged_count = len(updated_hosts)
        if not updated_hosts:
            logger.info("没有需要更新的hosts，跳过")
            success = True
            status_text = "无需更新"
            detail_message = "本次检查完成，没有可同步的 Hosts 条目"
            self.__send_message(
                title="【🛜 中兴问天Hosts】任务完成：",
                success=success,
                status_text=status_text,
                detail_message=detail_message,
                local_count=local_count,
                remote_count=remote_count,
                merged_count=merged_count,
                submitted=submitted,
            )
            return

        logger.info(f"Hosts合并完成，共 {merged_count} 条")
        submitted = True
        success, detail_message = self.__submit_hosts(login_context, updated_hosts)
        status_text = "同步成功" if success else "同步失败"
        self.__send_message(
            title="【🛜 中兴问天Hosts】任务完成：",
            success=success,
            status_text=status_text,
            detail_message=detail_message,
            local_count=local_count,
            remote_count=remote_count,
            merged_count=merged_count,
            submitted=submitted,
        )

    def __normalize_base_url(self) -> str:
        """
        标准化路由地址
        """
        router_url = (self._router_url or "").strip().rstrip("/")
        if not router_url:
            raise ValueError("未配置路由地址")
        if not re.match(r"^https?://", router_url, re.IGNORECASE):
            router_url = f"http://{router_url}"
        return router_url

    def __login_with_browser(self) -> Optional[Dict[str, Any]]:
        """
        使用 MoviePilot 内置 Playwright 登录路由并抓取 SID/sl-session
        """
        try:
            base_url = self.__normalize_base_url()

            def __page_handler(page):
                preempt_info = {
                    "sessid": "",
                    "token": ""
                }

                def __capture_response(response):
                    try:
                        url = response.url
                        if "login_entry" in url:
                            result = response.json()
                            if result.get("loginErrType") == "e_exceed_max_user_preempt":
                                preempt_info["token"] = response.headers.get("x_xsrf_token") or response.headers.get("X_XSRF_TOKEN") or ""
                        elif "vue_userif_data" in url:
                            token = response.headers.get("x_xsrf_token") or response.headers.get("X_XSRF_TOKEN")
                            if token:
                                preempt_info["token"] = token
                            text = response.text()
                            match = re.search(r"<ParaName>preempt_sessid</ParaName>\s*<ParaValue>(.*?)</ParaValue>", text, re.S)
                            if match:
                                preempt_info["sessid"] = unescape(match.group(1))
                    except Exception:
                        pass

                page.on("response", __capture_response)
                page.goto(f"{base_url}/")
                page.wait_for_load_state("domcontentloaded", timeout=30 * 1000)

                password_locator = page.locator(
                    'input[type="password"], input[placeholder*="密码"], input[placeholder*="Password"]'
                ).first
                password_locator.wait_for(timeout=15 * 1000)
                password_locator.fill(self._password or "")

                login_button = page.get_by_role("button", name="登录")
                login_button.click()

                try:
                    page.wait_for_url("**/#/menu/dashboard", timeout=30 * 1000)
                except Exception:
                    page.wait_for_load_state("networkidle", timeout=30 * 1000)

                page.wait_for_load_state("networkidle", timeout=30 * 1000)
                page.wait_for_timeout(2000)

                if preempt_info.get("sessid") and preempt_info.get("token"):
                    logger.info("检测到其他终端登录，尝试抢占登录会话")
                    page.evaluate(
                        """async ({baseUrl, sessid, token}) => {
                            const body = new URLSearchParams({
                                preempt_sessid: sessid,
                                action: 'preempt',
                                _sessionTOKEN: token
                            });
                            await fetch(`${baseUrl}/?_type=loginData&_tag=login_preempt`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/x-www-form-urlencoded',
                                    'Accept': '*/*'
                                },
                                body
                            });
                        }""",
                        {"baseUrl": base_url, "sessid": preempt_info["sessid"], "token": preempt_info["token"]}
                    )
                    page.wait_for_load_state("networkidle", timeout=30 * 1000)
                    page.reload()
                    page.wait_for_load_state("networkidle", timeout=30 * 1000)
                    page.wait_for_timeout(1000)
                    cookies_after_preempt = page.context.cookies()
                    if not any(cookie.get("name") == "SID" for cookie in cookies_after_preempt):
                        password_locator = page.locator(
                            'input[type="password"], input[placeholder*="密码"], input[placeholder*="Password"]'
                        ).first
                        password_locator.wait_for(timeout=15 * 1000)
                        password_locator.fill(self._password or "")
                        page.get_by_role("button", name="登录").click()
                        try:
                            page.wait_for_url("**/#/menu/dashboard", timeout=30 * 1000)
                        except Exception:
                            page.wait_for_load_state("networkidle", timeout=30 * 1000)
                        page.wait_for_load_state("networkidle", timeout=30 * 1000)

                page.wait_for_timeout(3000)

                browser_cookies = page.context.cookies()
                return browser_cookies, page.url

            result = PlaywrightHelper().action(
                url=f"{base_url}/",
                callback=__page_handler,
                headless=True,
                timeout=60
            )
            if not result:
                return None

            browser_cookies, final_url = result
            if not browser_cookies:
                logger.info("浏览器登录后未获取到任何Cookie")
                return None

            session = requests.Session()
            sid_cookie = None
            sl_session_cookie = None
            cookie_domain = re.sub(r"^https?://", "", base_url, flags=re.I).split("/", 1)[0].split(":", 1)[0]
            for cookie in browser_cookies:
                name = cookie.get("name")
                value = cookie.get("value")
                if not name or value is None:
                    continue
                domain = str(cookie.get("domain") or cookie_domain).lstrip(".")
                path = str(cookie.get("path") or "/")
                session.cookies.set(name, value, domain=domain, path=path)
                if name == "SID":
                    sid_cookie = value
                elif name == "sl-session":
                    sl_session_cookie = value

            if not sid_cookie:
                logger.info(f"浏览器登录结束页：{final_url}，但未获取到 SID")
                return None

            cookie_header = f"SID={sid_cookie}"
            if sl_session_cookie:
                cookie_header += f"; sl-session={sl_session_cookie}"

            logger.info(
                f"浏览器登录成功：SID={self.__mask_token(sid_cookie)}, "
                f"sl-session={'yes' if sl_session_cookie else 'no'}"
            )
            return {
                "base_url": base_url,
                "session": session,
                "cookie_header": cookie_header,
                "latest_xsrf_token": "",
            }
        except Exception as e:
            logger.info(f"浏览器登录失败：{e}")
            return None

    def __fetch_remote_hosts(self, login_context: Dict[str, Any]) -> Optional[List[str]]:
        """
        获取远程Hosts
        """
        try:
            response = self.__request_vue_hosts_data(login_context, use_auth=False)
            if response and self.__looks_like_html(response.text):
                request_token = self.__get_request_token(login_context)
                if not request_token:
                    logger.error(f"获取远程hosts失败，vue_hosts_data 返回 HTML 页面诊断：{self.__diagnose_html_response(response.text)}")
                    return None
                logger.info("远程Hosts首次请求返回HTML，尝试携带认证Token重试一次")
                response = self.__request_vue_hosts_data(login_context, use_auth=True)
            if not response:
                return None

            latest_xsrf_token = self.__get_xsrf_token_from_response(response)
            if latest_xsrf_token:
                login_context["latest_xsrf_token"] = latest_xsrf_token

            if self.__looks_like_html(response.text):
                logger.error(f"获取远程hosts失败，vue_hosts_data 返回 HTML 页面诊断：{self.__diagnose_html_response(response.text)}")
                return None

            hosts = self.__parse_hosts_xml(response.text)
            if hosts is None:
                return None
            return hosts
        except Exception as e:
            logger.error(f"获取远程hosts失败: {e}")
            return None

    def __request_vue_hosts_data(self, login_context: Dict[str, Any], use_auth: bool = False) -> Optional[Response]:
        """
        请求中兴问天 vue_hosts_data 接口
        """
        base_url = login_context["base_url"]
        request_token = self.__get_request_token(login_context)
        url = f"{base_url}/?_type=vueData&_tag=vue_hosts_data&_={int(datetime.now().timestamp() * 1000)}"
        custom_headers = None
        if use_auth:
            if not request_token:
                return None
            url = f"{base_url}/?_type=vueData&_tag=vue_hosts_data&_sessionTOKEN={request_token}&_={int(datetime.now().timestamp() * 1000)}"
            custom_headers = self.__build_auth_headers(login_context)
        return self.__make_router_request(
            session=login_context.get("session"),
            method="GET",
            url=url,
            custom_headers=custom_headers,
            referer=f"{base_url}/",
            cookie_header=login_context.get("cookie_header")
        )

    def __submit_hosts(self, login_context: Dict[str, Any], hosts: List[str]) -> Tuple[bool, str]:
        """
        提交更新后的Hosts
        """
        try:
            base_url = login_context["base_url"]
            session = login_context.get("session")
            submit_token = self.__get_request_token(login_context)
            payload = self.__build_hosts_payload(hosts, submit_token)
            response = self.__make_router_request(
                session=session,
                method="POST",
                url=f"{base_url}/?_type=vueData&_tag=vue_hosts_data",
                data=payload,
                referer=f"{base_url}/",
                cookie_header=login_context.get("cookie_header")
            )
            if response and response.status_code == 200:
                latest_xsrf_token = self.__get_xsrf_token_from_response(response)
                if latest_xsrf_token:
                    login_context["latest_xsrf_token"] = latest_xsrf_token
                error_str = self.__extract_xml_tag(response.text, "IF_ERRORSTR")
                error_id = self.__extract_xml_tag(response.text, "IF_ERRORID")
                if error_id == "0" or error_str == "SUCC":
                    message_text = "更新远程hosts成功"
                    logger.info(message_text)
                    return True, message_text
                else:
                    message_text = f"更新远程hosts失败，返回：{error_str or error_id or response.text}"
                    logger.error(message_text)
                    return False, message_text
            else:
                message_text = "更新远程hosts失败"
                logger.error(message_text)
                return False, message_text
        except Exception as e:
            message_text = f"请求发送异常：{e}"
            logger.error(message_text)
            return False, message_text

    @staticmethod
    def __build_browser_headers(referer: str, is_post: bool = False) -> Dict[str, str]:
        """
        构造接近浏览器访问的请求头
        """
        headers = {
            "User-Agent": settings.USER_AGENT,
            "Referer": referer,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Sec-CH-UA": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=1, i",
        }
        if is_post:
            headers["Origin"] = referer.rstrip("/")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        return headers

    def __build_hosts_payload(self, hosts: List[str], session_tmp_token: Optional[str]) -> str:
        """
        按中兴问天接口格式构造Hosts提交参数
        """
        max_items = 512
        parsed_hosts = []
        for line in hosts[:max_items]:
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 2:
                parsed_hosts.append((parts[0], parts[1]))

        params: List[Tuple[str, str]] = [
            ("IF_ACTION", "Apply"),
            ("Count", str(len(parsed_hosts) + 1)),
            ("EmptyFlag", "0"),
        ]

        for index in range(max_items):
            if index < len(parsed_hosts):
                ip, hostname = parsed_hosts[index]
                params.append((f"HostName{index}", hostname))
                params.append((f"IPAddress{index}", ip))
            else:
                params.append((f"IPAddress{index}", ""))
                params.append((f"HostName{index}", ""))

        if session_tmp_token:
            params.append(("_sessionTOKEN", session_tmp_token))
        return urlencode(params)

    @staticmethod
    def __get_request_token(login_context: Dict[str, Any]) -> Optional[str]:
        """
        获取可用于读写接口的认证Token
        """
        return login_context.get("latest_xsrf_token")

    def __build_auth_headers(self, login_context: Dict[str, Any]) -> Dict[str, str]:
        """
        构造认证增强请求头
        """
        token = self.__get_request_token(login_context)
        if not token:
            return {}
        return {
            "x_xsrf_token": token,
            "X_XSRF_TOKEN": token,
            "_sessionTOKEN": token,
            "X-Requested-With": "XMLHttpRequest",
        }

    @staticmethod
    def __mask_token(token: Optional[str]) -> str:
        """
        脱敏Token
        """
        if not token:
            return "None"
        if len(token) <= 8:
            return token
        return f"{token[:4]}***{token[-4:]}"

    @staticmethod
    def __short_text(text: Optional[str], limit: int = 300) -> str:
        """
        截断长文本用于日志输出
        """
        if not text:
            return ""
        compact = text.replace("\r", " ").replace("\n", " ")
        compact = re.sub(r"\s+", " ", compact).strip()
        if len(compact) <= limit:
            return compact
        return compact[:limit] + "..."

    def __parse_hosts_xml(self, xml_text: str) -> Optional[List[str]]:
        """
        解析中兴问天Hosts XML响应
        """
        if not xml_text:
            return None
        hosts: List[str] = []
        if self.__looks_like_html(xml_text):
            logger.error(f"vue_hosts_data 返回 HTML 页面诊断：{self.__diagnose_html_response(xml_text)}")
            return None
        obj_match = re.search(r"<OBJ_HOSTS_ID>(.*?)</OBJ_HOSTS_ID>", xml_text, re.S)
        if not obj_match:
            logger.error(f"未找到 OBJ_HOSTS_ID 节点，响应摘要：{self.__short_text(xml_text)}")
            return None

        webstrings: Dict[int, str] = {}
        for index_str, value in re.findall(r"<ParaName>WebString(\d+)</ParaName>\s*<ParaValue>(.*?)</ParaValue>", obj_match.group(1), re.S):
            webstrings[int(index_str)] = unescape(value or "")

        logger.debug(f"从 OBJ_HOSTS_ID 中直接提取到 WebString 节点数：{len(webstrings)}")
        for index in sorted(webstrings):
            text = webstrings[index].replace("\r", "")
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                hosts.append(line)
        logger.debug(f"从 OBJ_HOSTS_ID 中直接提取到 Hosts 行数：{len(hosts)}")
        return hosts

    @staticmethod
    def __get_xsrf_token_from_response(response: Optional[Response]) -> Optional[str]:
        """
        从响应头提取 XSRF Token
        """
        if not response:
            return None
        return (
            response.headers.get("x_xsrf_token")
            or response.headers.get("X_XSRF_TOKEN")
            or response.headers.get("X-XSRF-TOKEN")
        )

    @staticmethod
    def __extract_xml_tag(xml_text: str, tag_name: str) -> Optional[str]:
        """
        提取XML中的指定标签内容
        """
        if not xml_text:
            return None
        try:
            root = ElementTree.fromstring(xml_text)
            value = root.findtext(tag_name)
            if value is not None:
                return value
        except Exception:
            pass
        match = re.search(rf"<{tag_name}>(.*?)</{tag_name}>", xml_text, re.S)
        if match:
            return unescape(match.group(1))
        return None

    @staticmethod
    def __looks_like_html(text: Optional[str]) -> bool:
        """
        判断响应是否为HTML页面
        """
        if not text:
            return False
        prefix = text[:500].lower()
        return "<!doctype html" in prefix or "<html" in prefix

    def __diagnose_html_response(self, html_text: str) -> str:
        """
        诊断意外返回的HTML页面
        """
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
        title = self.__short_text(unescape(title_match.group(1)).strip(), 80) if title_match else ""

        flags = []
        checks = {
            "contains_login": r"login|登录|Frm_Logintoken|login_entry",
            "contains_challenge": r"challenge|sl-challenge|cloud",
            "contains_redirect": r"location\.|window\.location|top\.location|self\.location",
            "contains_form": r"<form\b",
            "contains_vue_hosts": r"vue_hosts_data|getHostsLua|OBJ_HOSTS_ID",
            "contains_sid_hint": r"SID=|sl-session",
        }
        lowered = html_text.lower()
        for name, pattern in checks.items():
            if re.search(pattern, lowered, re.I):
                flags.append(name)

        body_preview = self.__short_text(html_text, 300)
        return f"title={title or 'None'}, flags={','.join(flags) if flags else 'none'}, preview={body_preview}"

    def __update_remote_hosts_with_local(self, local_hosts: List[str], remote_hosts: List[str]) -> List[str]:
        """
        使用本地hosts内容覆盖远程hosts，并合并未冲突的条目，同时忽略IPv6和其他特定的本地定义
        """
        try:
            ignore = self._ignore.split("|") if self._ignore else []
            ignore.extend(["localhost"])

            # 创建远程hosts字典，适应空格或制表符分隔
            remote_dict: Dict[str, str] = {}
            for line in remote_hosts:
                line = line.strip()
                if " " in line or "\t" in line:
                    parts = re.split(r'\s+', line)
                    if len(parts) > 1 and not line.startswith('#'):
                        ip, hostname = parts[0], parts[1]
                        if not self.__should_ignore_ip(ip) and hostname not in ignore and ip not in ignore:
                            remote_dict[hostname] = f"{ip} {hostname}"

            # 用本地hosts更新远程hosts
            for line in local_hosts:
                line = line.lstrip("\ufeff").strip()
                if line.startswith("#") or any(ign in line for ign in ignore):
                    continue
                parts = re.split(r'\s+', line)
                if len(parts) < 2:
                    continue
                ip, hostname = parts[0], parts[1]
                if not self.__should_ignore_ip(ip) and hostname not in ignore and ip not in ignore:
                    remote_dict[hostname] = f"{ip} {hostname}"

            # 组装最终的hosts列表
            updated_hosts = sorted(remote_dict.values(), key=lambda item: item.split(maxsplit=1)[1])
            logger.debug(f"合并后的hosts共 {len(updated_hosts)} 条")
            return updated_hosts
        except Exception as e:
            logger.error(f"合并hosts失败: {e}")
            return []

    @staticmethod
    def __get_local_hosts() -> List[str]:
        """
        获取本地hosts文件的内容
        """
        try:
            logger.debug("正在准备获取本地hosts")
            # 确定hosts文件的路径
            if SystemUtils.is_windows():
                hosts_path = r"c:\windows\system32\drivers\etc\hosts"
            else:
                hosts_path = '/etc/hosts'
            with open(hosts_path, "r", encoding="utf-8") as file:
                local_hosts = file.readlines()
            logger.debug(f"本地hosts文件读取成功，共 {len(local_hosts)} 行，路径：{hosts_path}")
            return local_hosts
        except Exception as e:
            logger.error(f"读取本地hosts文件失败: {e}")
            return []

    @staticmethod
    def __should_ignore_ip(ip: str) -> bool:
        """
        检查是否应该忽略给定的IP地址
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
            # 忽略本地回环地址和所有IPv6地址
            if ip_obj.is_loopback or ip_obj.version == 6:
                return True
        except ValueError:
            pass
        return False

    @retry(Exception, logger=logger)
    def __make_router_request(self, method: str, url: str, data: Any = None,
                              session: Optional[requests.Session] = None,
                              custom_headers: Optional[Dict[str, str]] = None,
                              referer: Optional[str] = None,
                              cookie_header: Optional[str] = None) -> Optional[Response]:
        """
        发送路由请求
        """
        if not session:
            logger.error("缺少路由登录会话，无法发送请求")
            return None

        actual_referer = referer or f"{self.__normalize_base_url()}/"
        headers = self.__build_browser_headers(
            referer=actual_referer,
            is_post=method.upper() == "POST"
        )
        if custom_headers:
            headers.update(custom_headers)
        if cookie_header:
            headers["Cookie"] = cookie_header

        logger.debug(f"发送路由请求：{method.upper()} {url}")
        response = session.request(
            method=method.upper(),
            url=url,
            data=data,
            headers=headers,
            timeout=30,
            verify=False
        )
        response.raise_for_status()
        logger.debug(f"路由响应：{response.status_code} {url}")
        return response

    def __send_message(self, title: str, success: bool, status_text: str, detail_message: str,
                       local_count: int = 0, remote_count: int = 0, merged_count: int = 0,
                       submitted: bool = False):
        """
        发送消息
        """
        if not self._notify:
            return

        notify_lines = []
        notify_lines.append("━━━━━━━━━━━━━━")
        notify_lines.append(f"{'✅' if success else '❌'} {status_text}")
        notify_lines.append("━━━━━━━━━━━━━━")
        notify_lines.append("📊 同步统计：")
        notify_lines.append(f"📁 本地Hosts数量：{local_count}")
        notify_lines.append(f"☁️ 远程Hosts数量：{remote_count}")
        notify_lines.append(f"🧩 合并后Hosts数量：{merged_count}")
        notify_lines.append(f"🚀 是否提交更新：{'是' if submitted else '否'}")
        notify_lines.append("━━━━━━━━━━━━━━")
        notify_lines.append(f"⏱ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")

        self.post_message(mtype=NotificationType.Plugin, title=title, text="\n".join(notify_lines))
