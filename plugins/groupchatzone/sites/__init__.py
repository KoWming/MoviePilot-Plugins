from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import etree

from app.db.site_oper import SiteOper
from app.core.config import settings
from app.log import logger
from app.utils.string import StringUtils
from app.helper.browser import PlaywrightHelper


class ISiteHandler(metaclass=ABCMeta):
    """
    站点处理基类
    """
    
    
    class MockResponse:
        """
        模拟Requests Response对象
        """
        def __init__(self, text):
            self.text = text
            self.status_code = 200
    
    def __init__(self, site_info: dict):
        """
        初始化站点信息
        """
        self.site_info = site_info
        self.site_url = site_info.get("url", "").strip()
        self.site_name = site_info.get("name", "").strip()
        self.site_cookie = site_info.get("cookie", "").strip()
        self.ua = site_info.get("ua", "").strip()
        self.render = site_info.get("render", False)
        self.use_proxy = site_info.get("use_proxy", True)
        self.proxies = settings.PROXY if (site_info.get("proxy") and self.use_proxy) else None
        
        # 构建请求头
        self.headers = {
            "User-Agent": self.ua,
            "Cookie": self.site_cookie,
            "Referer": self.site_url
        }
        
        # 配置重试策略
        self.session = self._init_session()
        
        # 初始化站点操作对象
        self.siteoper = SiteOper()
        
        # 初始化URL
        self.url_shoutbox = self.site_url + "/shoutbox.php"
        self.url_ajax = self.site_url + "/ajax.php"
        self.attendance_url = self.site_url + "/attendance.php"
        self.messages_url = self.site_url + "/messages.php"
        
    def _init_session(self) -> requests.Session:
        """
        初始化请求会话
        """
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[403, 404, 500, 502, 503, 504],
            allowed_methods=frozenset(['GET', 'POST']),
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=1, pool_maxsize=1)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        session.headers.update(self.headers)
        if self.proxies:
            session.proxies = self.proxies
        return session

    def _get_page_source_via_browser(self, url: str, ua: str = None) -> Optional[str]:
        """通过PlaywrightHelper获取页面源码 (支持 FlareSolverr/Playwright)"""
        # 构造代理配置
        proxies = None
        if self.use_proxy and hasattr(settings, 'PROXY') and settings.PROXY:
            try:
                proxy_url = None
                if isinstance(settings.PROXY, dict):
                    proxy_url = settings.PROXY.get('http') or settings.PROXY.get('https')
                elif isinstance(settings.PROXY, str):
                    proxy_url = settings.PROXY
                
                if proxy_url:
                    proxies = {"server": proxy_url}
            except Exception as e:
                logger.warning(f"解析代理配置失败: {e}")

        try:
            return PlaywrightHelper().get_page_source(
                url=url,
                cookies=self.site_cookie,
                ua=ua,
                proxies=proxies
            )
        except Exception as e:
            logger.error(f"BrowserHelper 请求异常: {e}")
            return None

    def _post_via_browser(self, url: str, data: dict = None) -> Optional[str]:
        """通过PlaywrightHelper执行POST请求"""
        # 构造代理配置
        proxies = None
        if self.use_proxy and hasattr(settings, 'PROXY') and settings.PROXY:
            try:
                proxy_url = None
                if isinstance(settings.PROXY, dict):
                    proxy_url = settings.PROXY.get('http') or settings.PROXY.get('https')
                elif isinstance(settings.PROXY, str):
                    proxy_url = settings.PROXY
                
                if proxy_url:
                    proxies = {"server": proxy_url}
            except Exception as e:
                logger.warning(f"解析代理配置失败: {e}")

        def post_action(page):
            js_data = data if data else {}
            return page.evaluate("""
                async (data) => {
                    const formData = new URLSearchParams();
                    for (const [key, value] of Object.entries(data)) {
                        formData.append(key, value);
                    }
                    const response = await fetch(window.location.href, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: formData
                    });
                    return await response.text();
                }
            """, js_data)

        try:
            return PlaywrightHelper().action(
                url=url,
                callback=post_action,
                cookies=self.site_cookie,
                ua=self.ua,
                proxies=proxies
            )
        except Exception as e:
            logger.error(f"BrowserHelper POST请求异常: {e}")
            return None



    def _send_get_request(self, url: str, params: dict = None, rt_method: callable = None) -> Optional[requests.Response]:
        """
        发送GET请求
        :param url: 请求URL
        :param params: 请求参数
        :param rt_method: 响应处理方法
        :return: 处理后的响应结果
        """
        try:
            # 优先尝试 BrowserHelper
            if self.render:
                html_text = self._get_page_source_via_browser(url, self.ua)
                if html_text:
                    response = self.MockResponse(html_text)
                    # 如果有响应处理方法,则使用该方法处理响应
                    if rt_method:
                        return rt_method(response)
                    return response

            response = self.session.get(url, params=params, timeout=(3.05, 10))
            response.raise_for_status()
            
            # 如果有响应处理方法,则使用该方法处理响应
            if rt_method:
                return rt_method(response)
                
            return response
        except Exception as e:
            logger.error(f"GET请求失败: {str(e)}")
            return None

    def _send_post_request(self, url: str, data: dict = None, rt_method: callable = None) -> Optional[requests.Response]:
        """
        发送POST请求
        :param url: 请求URL
        :param data: 请求数据
        :param rt_method: 响应处理方法
        :return: 处理后的响应结果
        """
        try:
            # 优先尝试 BrowserHelper
            if self.render:
                html_text = self._post_via_browser(url, data)
                if html_text:
                    response = self.MockResponse(html_text)
                    # 如果有响应处理方法,则使用该方法处理响应
                    if rt_method:
                        return rt_method(response)
                    return response

            response = self.session.post(url, data=data, timeout=(3.05, 10))
            response.raise_for_status()
            
            # 如果有响应处理方法,则使用该方法处理响应
            if rt_method:
                return rt_method(response)
                
            return response
        except Exception as e:
            logger.error(f"POST请求失败: {str(e)}")
            return None

    def send_messagebox(self, message: str, rt_method: callable = None) -> Tuple[bool, str]:
        """
        发送群聊区消息
        :param message: 消息内容
        :param rt_method: 响应处理方法
        :return: (是否成功, 结果信息)
        """
        try:
            if rt_method is None:
                rt_method = lambda response: " ".join(
                    etree.HTML(response.text).xpath("//tr[1]/td//text()"))
            params = {
                "shbox_text": message,
                "shout": "%E6%88%91%E5%96%8A",
                "sent": "yes",
                "type": "shoutbox"
            }
            result = self._send_get_request(self.url_shoutbox, params=params, rt_method=rt_method)
            if result is None:
                return False, "发送消息失败"
            return True, result
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return False, str(e)

    def get_messagebox(self, rt_method: callable = None) -> list:
        """
        获取群聊区消息
        :param rt_method: 响应处理方法
        :return: 消息列表
        """
        if rt_method is None:
            rt_method = lambda response: ["".join(item.xpath(".//text()")) for item in
                                          etree.HTML(response.text).xpath("//tr/td")]
        return self._send_get_request(self.url_shoutbox, rt_method=rt_method)

    def get_message_list(self, rt_method: callable = None):
        """
        获取邮件列表
        :param rt_method: 响应处理方法
        :return: 邮件列表
        """
        if rt_method is None:
            rt_method = lambda response: [
                {"status": "".join(item.xpath("./td[1]/img/@title")), 
                 "topic": "".join(item.xpath("./td[2]//text()")),
                 "from": "".join(item.xpath("./td[3]/text()")), 
                 "time": "".join(item.xpath("./td[4]//text()")),
                 "id": "".join(item.xpath("./td[5]/input/@value"))} 
                for item in etree.HTML(response.text).xpath("//form/table//tr")]
        return self._send_get_request(self.messages_url, rt_method=rt_method)

    def set_message_read(self, message_id: str, rt_method: callable = lambda response: ""):
        """
        将邮件设为已读
        :param message_id: 邮件ID
        :param rt_method: 响应处理方法
        :return: 处理后的响应结果
        """
        data = {
            "action": "moveordel",
            "messages[]": message_id,
            "markread": "设为已读",
            "box": "1"
        }
        return self._send_post_request(self.messages_url, data=data, rt_method=rt_method)

    @abstractmethod
    def match(self) -> bool:
        """
        判断是否匹配该站点处理器
        """
        pass

    @abstractmethod
    def get_feedback(self, message: str = None) -> Optional[Dict]:
        """
        获取站点反馈
        :param message: 发送的消息内容(可选)
        :return: 反馈信息字典
        """
        pass

    def get_rewards(self) -> List[Dict]:
        """
        获取奖励信息
        :return: 奖励信息列表
        """
        pass
        
    def get_username(self) -> Optional[str]:
        """
        获取用户名
        :return: 用户名或None
        """
        site_name = self.site_name
        site_domain = StringUtils.get_url_domain(self.site_url)
        
        try:
            user_data_list = self.siteoper.get_userdata_latest()
            for user_data in user_data_list:
                if user_data.domain == site_domain:
                    logger.info(f"站点: {user_data.name}, 用户名: {user_data.username}")
                    return user_data.username
            
            logger.warning(f"未找到站点 {site_name} 的用户信息")
            return None
        except Exception as e:
            logger.error(f"获取站点 {site_name} 的用户信息失败: {str(e)}")
            return None