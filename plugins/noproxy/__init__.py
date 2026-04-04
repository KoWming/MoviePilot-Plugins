import fnmatch
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

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
    plugin_version = "1.0.0"
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
            for pattern in cls._build_target_hosts(cls._extra_hosts):
                if "*" in pattern:
                    if fnmatch.fnmatch(hostname, pattern):
                        return True
                else:
                    if hostname == pattern:
                        return True
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
            return

        try:
            from app.utils.http import RequestUtils, AsyncRequestUtils
        except Exception as err:
            logger.error(f"直连模式: 导入 HTTP 工具失败: {err}")
            return

        cls._original_sync_request = RequestUtils.request
        cls._original_async_request = AsyncRequestUtils.request

        def patched_sync(instance, method: str, url: str, raise_exception: bool = False, **kwargs):
            """同步补丁：命中白名单时清空实例代理，强制直连。"""
            if cls._should_bypass(url):
                instance._proxies = None
                if cls._debug_log:
                    logger.info(f"直连模式: 同步直连 -> {method.upper()} {url}")
            return cls._original_sync_request(instance, method, url, raise_exception, **kwargs)

        async def patched_async(instance, method: str, url: str, raise_exception: bool = False, **kwargs):
            """
            异步补丁：命中白名单时强制直连，分两种情形处理：
            - 无预建 client：清空 _proxies，原始方法内部创建无代理的 AsyncClient 即可。
            - 有预建 client：代理已固化在 client 中，改为临时创建无代理的 AsyncClient
              并直接调用 _make_request，绕开原 client。
            """
            if cls._should_bypass(url):
                if instance._client is not None:
                    import httpx
                    try:
                        async with httpx.AsyncClient(
                            proxy=None,
                            timeout=instance._timeout,
                            verify=False,
                            follow_redirects=True,
                            cookies=instance._cookies,
                        ) as tmp_client:
                            if cls._debug_log:
                                logger.info(f"直连模式: 异步(预建client)直连 -> {method.upper()} {url}")
                            return await instance._make_request(tmp_client, method, url, raise_exception, **kwargs)
                    except Exception as e:
                        logger.warning(f"直连模式: 临时 client 创建失败，回退原始流程: {e}")
                        return await cls._original_async_request(instance, method, url, raise_exception, **kwargs)
                else:
                    instance._proxies = None
                    if cls._debug_log:
                        logger.info(f"直连模式: 异步直连 -> {method.upper()} {url}")

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
                                                'props': {'cols': 12, 'sm': 6},
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
                                                'props': {'cols': 12, 'sm': 6},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'debug_log',
                                                            'label': '输出调试日志',
                                                            'color': 'secondary',
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
                                            # 条目1：工作原理
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
                                                                'text': '工作原理'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '插件启动后，在运行时对 RequestUtils 和 AsyncRequestUtils 注入补丁。当请求目标主机命中白名单时，自动清除代理配置，强制走直连，其余请求不受影响。'
                                                    }
                                                ]
                                            },
                                            # 条目2：内置主机
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
                                                                'text': '内置白名单'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': f'MP_SERVER_HOST 配置的主机（当前为 {mp_server_host}）已自动加入直连白名单，涵盖插件安装统计、订阅分享、OCR、CookieCloud 等核心服务请求。'
                                                    }
                                                ]
                                            },
                                            # 条目3：补丁开关
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
                                                                'text': 'mdi-sync'
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {'class': 'text-subtitle-1 font-weight-regular mb-1'},
                                                                'text': '热切换支持'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {'class': 'text-body-2 ml-8'},
                                                        'text': '启用或禁用插件时，补丁将实时注入或回滚，无需重启 MoviePilot。'
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
            'debug_log': self.__class__._debug_log,
            'extra_hosts': self.__class__._extra_hosts,
        }
