import fnmatch
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
import requests

from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase


class NoProxy(_PluginBase):
    # 插件名称
    plugin_name = "直连模式"
    # 插件描述
    plugin_desc = "对指定域名的请求强制直连，绕过 MoviePilot 全局代理。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/noproxy.png"
    # 插件版本
    plugin_version = "1.1.0"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项 ID 前缀
    plugin_config_prefix = "noproxy_"
    # 加载顺序
    plugin_order = 1
    # 可使用的用户级别
    auth_level = 1

    # ---- 类变量 ----
    _patched: bool = False             # 是否已注入补丁
    _extra_hosts: str = ""             # 用户配置的额外直连主机
    _compat_mode: bool = False         # 直连失败后是否回退系统代理
    _debug_log: bool = False           # 是否输出调试日志
    _original_sync_request = None      # 原始同步 request 方法引用
    _original_async_request = None     # 原始异步 request 方法引用

    # ---- 实例属性 ----
    _enabled: bool = False             # 插件启用状态

    def init_plugin(self, config: Optional[dict] = None):
        """
        生效配置。
        禁用分支必须主动回滚补丁。
        """
        cfg = config or {}
        self._enabled = bool(cfg.get("enabled", False))
        self.__class__._extra_hosts = cfg.get("extra_hosts", "") or ""
        self.__class__._compat_mode = bool(cfg.get("compat_mode", False))
        self.__class__._debug_log = bool(cfg.get("debug_log", False))

        if self._enabled:
            self._apply_patch()
            logger.info(f"{self.plugin_name}: 已启用，目标主机: {', '.join(self._get_target_hosts())}")
        else:
            self._remove_patch()
            logger.info(f"{self.plugin_name}: 未启用")

    def get_state(self) -> bool:
        """返回插件启用状态。"""
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取命令"""
        pass

    def get_page(self) -> List[dict]:
        """详情页面"""
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """获取API"""
        pass

    def stop_service(self):
        """停止插件服务，回滚所有已注入的补丁。"""
        self._remove_patch()

    @classmethod
    def _build_target_hosts(cls, extra_hosts_raw: str = "") -> List[str]:
        """
        构建直连主机白名单：
        1. 自动解析 settings.MP_SERVER_HOST 的 hostname（精确匹配）
        2. 追加用户配置（支持纯 hostname / 完整 URL / 通配符模式）
           - 精确：movie-pilot.org
           - 通配：*.movie-pilot.org（匹配所有子域名）
           - URL：https://other-host.com（自动提取 hostname）
        3. 去重并保持原始顺序
        """
        hosts = []

        mp_server_host = getattr(settings, "MP_SERVER_HOST", None)
        if mp_server_host:
            try:
                parsed = urlparse(mp_server_host)
                if parsed.hostname:
                    hosts.append(parsed.hostname.lower())
            except Exception:
                pass

        if extra_hosts_raw:
            for item in str(extra_hosts_raw).replace("\n", ",").split(","):
                host = item.strip().lower()
                if not host:
                    continue
                # 通配符模式（如 *.example.com）直接保留，不做 URL 解析
                if "*" in host:
                    hosts.append(host)
                    continue
                if "://" in host:
                    try:
                        parsed = urlparse(host)
                        if parsed.hostname:
                            host = parsed.hostname.lower()
                        else:
                            continue
                    except Exception:
                        continue
                hosts.append(host)

        seen: set = set()
        return [h for h in hosts if not (h in seen or seen.add(h))]

    def _get_target_hosts(self) -> List[str]:
        """返回当前生效的直连主机列表（用于日志展示）。"""
        return self._build_target_hosts(self.__class__._extra_hosts)

    @classmethod
    def _log_debug(cls, message: str):
        """仅在开启调试日志时输出 debug 级别日志。"""
        if cls._debug_log:
            logger.debug(message)

    @staticmethod
    def _normalize_httpx_timeout(timeout: Any) -> httpx.Timeout:
        """将宿主 timeout 配置转换为 httpx.Timeout，避免直连临时客户端沿用环境代理。"""
        if isinstance(timeout, httpx.Timeout):
            return timeout
        if timeout is None:
            timeout = 20
        return httpx.Timeout(timeout)

    @staticmethod
    def _get_sync_proxy_config(instance) -> Optional[Dict[str, Any]]:
        """获取同步兼容模式使用的系统代理配置。"""
        proxies = getattr(instance, "_proxies", None) or getattr(settings, "PROXY", None)
        return proxies or None

    @staticmethod
    def _get_async_proxy_config(instance) -> Optional[str]:
        """获取异步兼容模式使用的系统代理配置。"""
        proxies = getattr(instance, "_proxies", None)
        if proxies:
            return proxies
        try:
            from app.utils.http import AsyncRequestUtils
            return AsyncRequestUtils._convert_proxies_for_httpx(getattr(settings, "PROXY", None))
        except Exception:
            return None

    @classmethod
    def _compat_enabled(cls) -> bool:
        return bool(cls._compat_mode)

    @classmethod
    def _match_target_pattern(cls, url: str) -> Optional[str]:
        """返回命中的白名单模式，未命中则返回 None。"""
        if not url:
            return None
        try:
            hostname = (urlparse(url).hostname or "").lower()
            if not hostname:
                return None
            for pattern in cls._build_target_hosts(cls._extra_hosts):
                if "*" in pattern:
                    if fnmatch.fnmatch(hostname, pattern):
                        return pattern
                else:
                    if hostname == pattern:
                        return pattern
            return None
        except Exception:
            return None

    @classmethod
    def _should_bypass(cls, url: str) -> bool:
        """
        判断给定 URL 的 hostname 是否命中直连白名单。
        支持两种匹配模式：
        - 精确匹配：movie-pilot.org == movie-pilot.org
        - 通配匹配：fnmatch(sub.movie-pilot.org, *.movie-pilot.org)
        """
        if not url:
            return False
        try:
            hostname = (urlparse(url).hostname or "").lower()
            if not hostname:
                return False
            matched_pattern = cls._match_target_pattern(url)
            if matched_pattern:
                cls._log_debug(f"直连模式: 白名单命中 hostname={hostname}, pattern={matched_pattern}, url={url}")
                return True
            cls._log_debug(f"直连模式: 白名单未命中 hostname={hostname}, url={url}")
            return False
        except Exception:
            return False

    @classmethod
    def _apply_patch(cls):
        """
        向 RequestUtils.request 和 AsyncRequestUtils.request 注入直连补丁。
        通过类变量 _patched 确保同一进程内只注入一次。
        """
        if cls._patched:
            cls._log_debug("直连模式: HTTP 补丁已存在，跳过重复注入")
            return

        try:
            from app.utils.http import RequestUtils, AsyncRequestUtils
        except Exception as err:
            logger.error(f"直连模式: 导入 HTTP 工具失败: {err}")
            return

        cls._original_sync_request = RequestUtils.request
        cls._original_async_request = AsyncRequestUtils.request
        cls._log_debug("直连模式: 已缓存原始 RequestUtils.request 与 AsyncRequestUtils.request")

        def patched_sync(instance, method: str, url: str, raise_exception: bool = False, **kwargs):
            """同步补丁：命中白名单时禁用显式代理和环境代理，强制直连。"""
            if cls._should_bypass(url):
                cls._log_debug(
                    f"直连模式: 进入同步补丁 method={method.upper()}, url={url}, "
                    f"compat_mode={cls._compat_enabled()}, instance_proxies={getattr(instance, '_proxies', None)}"
                )
                if cls._debug_log:
                    logger.info(f"直连模式: 同步直连 -> {method.upper()} {url}")

                request_kwargs = dict(kwargs)
                request_kwargs.setdefault("headers", getattr(instance, "_headers", None))
                request_kwargs.setdefault("cookies", getattr(instance, "_cookies", None))
                request_kwargs.setdefault("timeout", getattr(instance, "_timeout", 20))
                request_kwargs.setdefault("verify", False)
                request_kwargs.setdefault("stream", False)
                request_kwargs["proxies"] = {}
                cls._log_debug(
                    f"直连模式: 同步直连请求参数 timeout={request_kwargs.get('timeout')}, "
                    f"verify={request_kwargs.get('verify')}, stream={request_kwargs.get('stream')}"
                )

                try:
                    session = requests.Session()
                    session.trust_env = False
                    cls._log_debug("直连模式: 同步直连 Session.trust_env=False")
                    return session.request(method, url, **request_kwargs)
                except requests.exceptions.RequestException as e:
                    error_msg = str(e) if str(e) else f"未知网络错误 (URL: {url}, Method: {method.upper()})"
                    logger.debug(f"直连模式: 同步直连失败: {error_msg}")

                    proxy_config = cls._get_sync_proxy_config(instance)
                    cls._log_debug(f"直连模式: 同步兼容模式代理配置={proxy_config}")
                    if cls._compat_enabled() and proxy_config:
                        if cls._debug_log:
                            logger.info(f"直连模式: 同步兼容模式回退系统代理 -> {method.upper()} {url}")
                        compat_kwargs = dict(request_kwargs)
                        compat_kwargs["proxies"] = proxy_config
                        try:
                            compat_session = requests.Session()
                            compat_session.trust_env = False
                            cls._log_debug("直连模式: 同步兼容模式 Session.trust_env=False")
                            return compat_session.request(method, url, **compat_kwargs)
                        except requests.exceptions.RequestException as compat_err:
                            compat_error_msg = str(compat_err) if str(compat_err) else f"未知网络错误 (URL: {url}, Method: {method.upper()})"
                            logger.debug(f"直连模式: 同步兼容模式回退失败: {compat_error_msg}")
                            if raise_exception:
                                raise compat_err
                            return None

                    if cls._compat_enabled() and not proxy_config:
                        cls._log_debug("直连模式: 已开启兼容模式，但未获取到同步代理配置")

                    if raise_exception:
                        raise
                    return None
            return cls._original_sync_request(instance, method, url, raise_exception, **kwargs)

        async def patched_async(instance, method: str, url: str, raise_exception: bool = False, **kwargs):
            """
            异步补丁：命中白名单时使用临时直连 AsyncClient，
            同时禁用 httpx 环境代理（trust_env=False）。
            """
            if cls._should_bypass(url):
                cls._log_debug(
                    f"直连模式: 进入异步补丁 method={method.upper()}, url={url}, "
                    f"compat_mode={cls._compat_enabled()}, instance_proxies={getattr(instance, '_proxies', None)}, "
                    f"has_make_request={callable(getattr(instance, '_make_request', None))}"
                )
                if cls._debug_log:
                    logger.info(f"直连模式: 异步直连 -> {method.upper()} {url}")

                make_request_func = getattr(instance, "_make_request", None)
                if callable(make_request_func):
                    try:
                        cls._log_debug(
                            f"直连模式: 创建异步直连临时客户端 timeout={getattr(instance, '_timeout', 20)}, trust_env=False"
                        )
                        async with httpx.AsyncClient(
                            proxy=None,
                            timeout=cls._normalize_httpx_timeout(getattr(instance, "_timeout", 20)),
                            verify=False,
                            follow_redirects=True,
                            cookies=getattr(instance, "_cookies", None),
                            trust_env=False,
                        ) as tmp_client:
                            return await make_request_func(tmp_client, method, url, raise_exception, **kwargs)
                    except httpx.RequestError as e:
                        error_msg = str(e) if str(e) else f"未知网络错误 (URL: {url}, Method: {method.upper()})"
                        logger.debug(f"直连模式: 异步直连失败: {error_msg}")

                        proxy_config = cls._get_async_proxy_config(instance)
                        cls._log_debug(f"直连模式: 异步兼容模式代理配置={proxy_config}")
                        if cls._compat_enabled() and proxy_config:
                            if cls._debug_log:
                                logger.info(f"直连模式: 异步兼容模式回退系统代理 -> {method.upper()} {url}")
                            try:
                                cls._log_debug(
                                    f"直连模式: 创建异步兼容模式临时客户端 timeout={getattr(instance, '_timeout', 20)}, trust_env=False"
                                )
                                async with httpx.AsyncClient(
                                    proxy=proxy_config,
                                    timeout=cls._normalize_httpx_timeout(getattr(instance, "_timeout", 20)),
                                    verify=False,
                                    follow_redirects=True,
                                    cookies=getattr(instance, "_cookies", None),
                                    trust_env=False,
                                ) as compat_client:
                                    return await make_request_func(compat_client, method, url, raise_exception, **kwargs)
                            except httpx.RequestError as compat_err:
                                compat_error_msg = str(compat_err) if str(compat_err) else f"未知网络错误 (URL: {url}, Method: {method.upper()})"
                                logger.debug(f"直连模式: 异步兼容模式回退失败: {compat_error_msg}")
                                if raise_exception:
                                    raise compat_err
                                return None

                        if cls._compat_enabled() and not proxy_config:
                            cls._log_debug("直连模式: 已开启兼容模式，但未获取到异步代理配置")

                        if raise_exception:
                            raise
                        return None
                    except Exception as e:
                        logger.warning(f"直连模式: 临时直连 client 创建失败，回退原始流程: {e}")
                else:
                    logger.warning("直连模式: 未找到 _make_request 方法，回退原始流程")

            return await cls._original_async_request(instance, method, url, raise_exception, **kwargs)

        RequestUtils.request = patched_sync
        AsyncRequestUtils.request = patched_async
        cls._patched = True
        logger.info("直连模式: HTTP 补丁已注入")

    @classmethod
    def _remove_patch(cls):
        """
        回滚补丁，恢复 RequestUtils 和 AsyncRequestUtils 的原始 request 方法。
        幂等操作，重复调用安全。
        """
        if not cls._patched:
            cls._log_debug("直连模式: HTTP 补丁未注入，无需回滚")
            return

        try:
            from app.utils.http import RequestUtils, AsyncRequestUtils
        except Exception:
            return

        if cls._original_sync_request is not None:
            RequestUtils.request = cls._original_sync_request
            cls._original_sync_request = None

        if cls._original_async_request is not None:
            AsyncRequestUtils.request = cls._original_async_request
            cls._original_async_request = None

        cls._patched = False
        logger.info("直连模式: HTTP 补丁已回滚")

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        mp_server_host = getattr(settings, "MP_SERVER_HOST", "https://movie-pilot.org")
        return [
            {
                'component': 'VForm',
                'content': [
                    # ---- 卡片1：基本设置 ----
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
                                                            'model': 'compat_mode',
                                                            'label': '兼容模式',
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
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'debug_log',
                                                            'label': '输出调试日志',
                                                            'color': 'warning',
                                                            'hide-details': True
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
                                                        'component': 'VTextarea',
                                                        'props': {
                                                            'model': 'extra_hosts',
                                                            'label': '额外直连主机',
                                                            'rows': 4,
                                                            'auto-grow': False,
                                                            'hide-details': False,
                                                            'active': True,
                                                            'persistent-hint': True,
                                                            'hint': f'MP_SERVER_HOST ({mp_server_host}) 已自动加入，此处填写额外需要直连的主机，支持通配符。',
                                                            'placeholder': '每行或逗号分隔，支持精确主机名、完整 URL 或通配符，例如：\nother-host.com\n*.movie-pilot.org\nhttps://sub.example.com'
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
                    # ---- 卡片2：使用说明 ----
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
                                                'text': '使用说明'
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
                                        'component': 'VList',
                                        'props': {
                                            'lines': 'two',
                                            'density': 'comfortable'
                                        },
                                        'content': [
                                            # 条目1：工作模式
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
                                                                'text': 'mdi-transit-connection-variant'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '工作模式'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '插件启动后会在运行时为 RequestUtils 和 AsyncRequestUtils 注入补丁。当请求目标主机命中白名单时，优先禁用全局代理并直接发起请求；未命中白名单的请求保持宿主原有逻辑不变。'
                                                    }
                                                ]
                                            },
                                            # 条目2：白名单来源
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
                                                                'text': 'mdi-check-circle'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '白名单来源'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': f'MP_SERVER_HOST 配置的主机（当前为 {mp_server_host}）会自动加入白名单；你也可以在“额外直连主机”中补充精确域名、完整 URL 或通配符域名，例如 *.movie-pilot.org。'
                                                    }
                                                ]
                                            },
                                            # 条目3：兼容模式
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
                                                                'text': 'mdi-compare-horizontal'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '兼容模式'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '开启兼容模式后，命中白名单的请求会先尝试直连；若直连失败，再回退使用系统代理重新请求。适合 bridge 网络下直连不稳定、但代理可用的场景。'
                                                    }
                                                ]
                                            },
                                            # 条目4：调试日志与热切换
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
                                                                'text': 'mdi-bug-outline'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '调试日志与热切换'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '开启“输出调试日志”后，插件会额外输出白名单命中、同步/异步补丁、直连失败与兼容模式回退等 debug 日志；同时插件支持热切换，启用或禁用后补丁会实时注入或回滚，无需重启 MoviePilot。'
                                                    }
                                                ]
                                            },
                                            # 条目5：适用场景
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
                                                                'text': 'mdi-lightbulb-on-outline'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '适用场景'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '适用于 MP 开启全局代理后，少量目标站点仍需直连的场景，例如 movie-pilot.org 统计接口、热门订阅、订阅分享、工作流分享、OCR、CookieCloud、自建服务域名，或 bridge 网络下部分请求直连不稳定但系统代理仍可访问的情况。'
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
            'enabled': self._enabled,
            'compat_mode': self.__class__._compat_mode,
            'debug_log': self.__class__._debug_log,
            'extra_hosts': self.__class__._extra_hosts,
        }
