import re
import pytz
import time
import requests

from lxml import etree
from datetime import datetime, timedelta
from typing import Any, List, Dict, Tuple, Optional

from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler

from app.log import logger
from app.core.config import settings
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.db.site_oper import SiteOper

class ContentFilter:

    @staticmethod
    def lxml_get_HTML(response):
        return etree.HTML(response.text)

    @staticmethod
    def lxml_get_text(response, xpath, split_str=""):
        return split_str.join(etree.HTML(response.text).xpath(xpath))

    @staticmethod
    def lxml_get_texts(response, xpath, split_str=""):
        return [split_str.join(item.xpath(".//text()")) for item in etree.HTML(response.text).xpath(xpath)]

    @staticmethod
    def re_get_text(response, pattern, group=0):
        match = re.search(pattern, response.text)
        return match.group(group) if match else None

    @staticmethod
    def re_get_texts(response, pattern, group=0):
        return [match.group(group) for match in re.finditer(pattern, response.text)]

    @staticmethod
    def re_get_match(response, pattern):
        match = re.search(pattern, response.text)
        return match

class VicomoVS(_PluginBase):
    # 插件名称
    plugin_name = "象岛传说竞技场"
    # 插件描述
    plugin_desc = "象岛传说竞技场，对战boss。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/Vicomovs.png"
    # 插件版本
    plugin_version = "1.2.5"
    # 插件作者
    plugin_author = "KoWming"
    # 作者主页
    author_url = "https://github.com/KoWming"
    # 插件配置项ID前缀
    plugin_config_prefix = "vicomovs_"
    # 加载顺序
    plugin_order = 24
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enabled: bool = False  # 是否启用插件
    _onlyonce: bool = False  # 是否仅运行一次
    _notify: bool = False  # 是否开启通知
    _use_proxy: bool = True  # 是否使用代理，默认启用
    _retry_count: int = 1  # 失败重试次数
    _retry_interval: int = 2  # 重试间隔(小时)
    _cron: Optional[str] = None  # 定时任务表达式
    _cookie: Optional[str] = None  # 手动配置的cookie
    _auto_cookie: bool = False  # 是否使用站点cookie
    _history_count: Optional[int] = None  # 历史记录数量
    _retry_jobs: Dict[str, Any] = {}  # 存储重试任务信息
    _proxies: Optional[Dict[str, str]] = None  # 代理设置

    # 对战参数
    _vs_boss_count: int = 3  # 对战次数
    _vs_boss_interval: int = 15  # 对战间隔
    _vs_site_url: str = "https://ptvicomo.net/"  # 对战站点URL
    
    # 定时器
    _scheduler: Optional[BackgroundScheduler] = None

    # 站点操作实例
    _siteoper = None

    def init_plugin(self, config: Optional[dict] = None) -> None:
        """
        初始化插件
        """
        # 停止现有任务
        self.stop_service()

        # 创建站点操作实例
        self._siteoper = SiteOper()

        if config:
            self._enabled = config.get("enabled", False)
            self._cron = config.get("cron")
            self._cookie = config.get("cookie")
            self._notify = config.get("notify", False)
            self._onlyonce = config.get("onlyonce", False)
            self._history_count = int(config.get("history_count", 10))
            self._vs_boss_count = int(config.get("vs_boss_count", 3))
            self._vs_boss_interval = int(config.get("vs_boss_interval", 15))
            self._use_proxy = config.get("use_proxy", True)
            self._retry_count = int(config.get("retry_count", 1))
            self._retry_interval = int(config.get("retry_interval", 2))
            self._auto_cookie = config.get("auto_cookie", False)

            # 初始化代理设置
            self._proxies = self._get_proxies()

            # 处理自动获取cookie
            if self._auto_cookie:
                self._cookie = self.get_site_cookie()
            else:
                self._cookie = config.get("cookie")
            
        if self._onlyonce:
            try:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                logger.info(f"象岛传说竞技场服务启动，立即运行一次")
                self._scheduler.add_job(func=self._battle_task, trigger='date',
                                        run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                        name="象岛传说竞技场")
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "onlyonce": False,
                    "cron": self._cron,
                    "enabled": self._enabled,
                    "cookie": self._cookie,
                    "notify": self._notify,
                    "history_count": self._history_count,
                    "vs_boss_count": self._vs_boss_count,
                    "vs_boss_interval": self._vs_boss_interval,
                    "use_proxy": self._use_proxy,
                    "retry_count": self._retry_count,
                    "retry_interval": self._retry_interval,
                    "auto_cookie": self._auto_cookie
                })

                # 启动任务
                if self._scheduler.get_jobs():
                   self._scheduler.print_jobs()
                   self._scheduler.start()
            except Exception as e:
                logger.error(f"象岛传说竞技场服务启动失败: {str(e)}")

    def get_member_ids(self, n=None):
        """获取前n个（或全部）角色编号，拼成逗号字符串"""
        try:
            url = f"{self._vs_site_url}/customgame.php"
            response = requests.get(url, headers={
                "cookie": self._cookie,
                "referer": self._vs_site_url,
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"
            }, proxies=self._proxies, timeout=30)
            html = etree.HTML(response.text)
            values = html.xpath('//input[contains(@class, "memberSelected")]/@value')
            if n is not None:
                values = values[:n]
            vs_member_name = ','.join(values)
            logger.info(f"自动获取{('全部' if n is None else f'前{n}个')}角色vs_member_name: {vs_member_name}")
            return vs_member_name
        except Exception as e:
            logger.error(f"获取角色vs_member_name失败: {str(e)}")
            return ""

    def vs_boss(self):
        """对战boss"""
        self.vs_boss_url = self._vs_site_url + "/customgame.php?action=exchange"
        self.headers = {
            "cookie": self._cookie,
            "referer": self._vs_site_url,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"
        }
        
        # 使用已保存的代理设置
        proxies = self._proxies
        
        # 根据星期几选择对战模式
        if datetime.today().weekday() in [0, 2]:
            vs_boss_data = "option=1&vs_member_name=0&submit=%E9%94%8B%E8%8A%92%E4%BA%A4%E9%94%99+-+1v1"  # Monday Wednesday
        elif datetime.today().weekday() in [1, 3]:
            # 5v5，自动选择5个角色
            vs_member_name = self.get_member_ids(5)
            vs_boss_data = f"option=1&vs_member_name={vs_member_name}&submit=%E9%BE%99%E4%B8%8E%E5%87%A4%E7%9A%84%E6%8A%97%E8%A1%A1+-+%E5%9B%A2%E6%88%98+5v5"
        elif datetime.today().weekday() in [4, 5, 6]:
            # 世界boss，自动全选角色
            vs_member_name = self.get_member_ids()
            vs_boss_data = f"option=1&vs_member_name={vs_member_name}&submit=%E4%B8%96%E7%95%8Cboss+-+%E5%AF%B9%E6%8A%97Sysrous"
        self.headers.update({
            "content-type": "application/x-www-form-urlencoded",
            "pragma": "no-cache",
        })
        response = requests.post(self.vs_boss_url, headers=self.headers, data=vs_boss_data, proxies=proxies, timeout=30)
        logger.info(f"对战请求状态码: {response.status_code}")

        # 从响应中提取重定向 URL
        redirect_url = None
        
        # 尝试多种正则表达式模式
        patterns = [
            r"window\.location\.href\s*=\s*'([^']+战斗结果[^']+)'",
            r"window\.location\.href\s*=\s*\"([^\"]+战斗结果[^\"]+)\"",
            r"location\.href\s*=\s*'([^']+战斗结果[^']+)'",
            r"location\.href\s*=\s*\"([^\"]+战斗结果[^\"]+)\"",
            r"window\.location\s*=\s*'([^']+战斗结果[^']+)'",
            r"window\.location\s*=\s*\"([^\"]+战斗结果[^\"]+)\""
        ]
        
        for pattern in patterns:
            match = ContentFilter.re_get_match(response, pattern)
            if match:
                redirect_url = match.group(1)
                logger.info(f"提取到的战斗结果重定向 URL: {redirect_url}")
                break
        
        if not redirect_url:
            # 如果正则表达式都失败，尝试从响应内容中查找
            logger.warning("正则表达式匹配失败，尝试从响应内容中查找重定向URL")
            if "战斗结果" in response.text:
                # 查找包含"战斗结果"的URL
                import re
                url_match = re.search(r'https?://[^\s\'"]*战斗结果[^\s\'"]*', response.text)
                if url_match:
                    redirect_url = url_match.group(0)
                    logger.info(f"从响应内容中提取到的重定向 URL: {redirect_url}")
        
        if not redirect_url:
            logger.error("未找到战斗结果重定向 URL")
            logger.debug(f"响应内容片段: {response.text[:500]}...")
            return None

        # 访问重定向 URL，添加重试机制和URL修复
        battle_result_response = None
        max_retries = 3
        
        # 尝试修复重定向URL格式
        fixed_redirect_url = self._fix_redirect_url(redirect_url)
        if fixed_redirect_url != redirect_url:
            logger.info(f"修复重定向URL: {redirect_url} -> {fixed_redirect_url}")
            redirect_url = fixed_redirect_url
        
        for retry in range(max_retries):
            try:
                # 添加更多请求头，模拟真实浏览器访问
                battle_headers = self.headers.copy()
                battle_headers.update({
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                })
                
                logger.info(f"正在访问重定向URL (第{retry + 1}次): {redirect_url}")
                battle_result_response = requests.get(redirect_url, headers=battle_headers, proxies=proxies, timeout=30)
                logger.info(f"战斗结果重定向页面状态码: {battle_result_response.status_code}")
                
                # 检查响应状态
                if battle_result_response.status_code == 200:
                    logger.info("成功获取战斗结果页面")
                    break
                elif battle_result_response.status_code in [301, 302, 303, 307, 308]:
                    # 处理重定向
                    new_url = battle_result_response.headers.get('Location')
                    if new_url:
                        logger.info(f"跟随重定向到: {new_url}")
                        redirect_url = new_url if new_url.startswith('http') else f"{self._vs_site_url}{new_url}"
                        continue
                    else:
                        logger.warning("收到重定向状态码但未找到Location头")
                else:
                    logger.warning(f"重定向页面返回非200状态码: {battle_result_response.status_code}")
                    logger.debug(f"响应头: {dict(battle_result_response.headers)}")
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"访问重定向URL第{retry + 1}次失败: {str(e)}")
                if retry < max_retries - 1:
                    wait_time = 3 * (retry + 1)  # 递增等待时间
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"访问重定向URL失败，已重试{max_retries}次")
                    return None
            except requests.exceptions.Timeout as e:
                logger.warning(f"访问重定向URL第{retry + 1}次超时: {str(e)}")
                if retry < max_retries - 1:
                    wait_time = 3 * (retry + 1)  # 递增等待时间
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"访问重定向URL超时，已重试{max_retries}次")
                    return None
            except Exception as e:
                logger.error(f"访问重定向URL时发生异常: {str(e)}")
                if retry < max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    return None
        
        if not battle_result_response:
            logger.error("无法获取战斗结果页面")
            return None

        # 解析战斗结果页面并提取战斗结果
        try:
            parsed_html = ContentFilter.lxml_get_HTML(battle_result_response)
            
            # 调试：记录页面内容片段
            logger.debug(f"战斗结果页面内容片段: {battle_result_response.text[:500]}...")
            
            # 首先尝试查找包含"平局"、"胜利"、"战败"等关键词的文本
            # 从截图可以看到，战斗结果直接显示在页面上
            result_text = None
            
            # 方法1：查找包含战斗结果的文本节点
            result_patterns = [
                '//*[contains(text(), "平局")]',
                '//*[contains(text(), "胜利")]',
                '//*[contains(text(), "战败")]',
                '//*[contains(text(), "象草")]'
            ]
            
            for pattern in result_patterns:
                elements = parsed_html.xpath(pattern)
                if elements:
                    for element in elements:
                        text = element.text.strip() if element.text else ""
                        if text and ("胜利" in text or "战败" in text or "平局" in text) and "象草" in text:
                            logger.info(f"通过模式 {pattern} 找到战斗结果: {text}")
                            result_text = text
                            break
                    if result_text:
                        break
            
            # 方法2：如果方法1失败，尝试查找特定的div结构
            if not result_text:
                logger.warning("方法1失败，尝试查找特定div结构")
                battle_result_divs = parsed_html.xpath('//div[contains(text(), "平局") or contains(text(), "胜利") or contains(text(), "战败")]')
                for div in battle_result_divs:
                    text = div.text.strip() if div.text else ""
                    if text and ("胜利" in text or "战败" in text or "平局" in text) and "象草" in text:
                        logger.info(f"通过div结构找到战斗结果: {text}")
                        result_text = text
                        break
            
            # 方法3：如果方法2失败，尝试从页面文本中提取
            if not result_text:
                logger.warning("方法2失败，尝试从页面文本中提取")
                page_text = battle_result_response.text
                import re
                # 查找包含战斗结果和象草的行
                result_match = re.search(r'(平局|胜利|战败)[^\\n]*?(\d+)象草', page_text)
                if result_match:
                    result_text = f"{result_match.group(1)} - 获得奖励: {result_match.group(2)}象草"
                    logger.info(f"通过正则表达式找到战斗结果: {result_text}")
            
            if result_text:
                return result_text
            else:
                logger.error("未找到任何战斗结果信息")
                # 记录更多调试信息
                logger.debug(f"页面内容: {battle_result_response.text}")
                return None
                
        except Exception as e:
            logger.error(f"解析战斗结果页面时发生异常: {str(e)}")
            return None

    def _battle_task(self):
        """
        执行对战任务
        """
        try:
            # 获取角色和战斗次数信息
            logger.info("开始获取角色和战斗次数信息...")
            char_info = self.get_character_info()
            
            # 检查是否有角色
            if char_info.get("has_characters") is None:
                # 网络问题，发送错误通知
                error_msg = char_info.get("error", "未知网络错误")
                msg = f"❌网络连接失败，无法获取角色信息：{error_msg}"
                logger.error(msg)
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【🐘象岛传说竞技场】网络错误",
                        text=f"━━━━━━━━━━━━━━\n"
                             f"⚠️ 错误提示：\n"
                             f"❌ 网络连接失败，无法获取角色信息\n"
                             f"🔍 错误详情：{error_msg}\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"💡 解决建议：\n"
                             f"🌐 检查网络连接是否正常\n"
                             f"🔧 检查代理设置是否正确\n"
                             f"🔄 稍后重试\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return
            elif not char_info["has_characters"]:
                msg = "😵‍💫你还还未获得任何角色，无法进行战斗！"
                logger.info(msg)
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【🐘象岛传说竞技场】任务失败",
                        text=f"━━━━━━━━━━━━━━\n"
                             f"⚠️ 错误提示：\n"
                             f"😵‍💫 你还还未获得任何角色，无法进行战斗！\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"📌 获取角色方式：\n"
                             f"🎰 智能扭蛋机 Plus\n"
                             f"🎰 智能扭蛋机 Pro Max Ultra 至尊豪华Master版\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"💡 提示：\n"   
                             f"✨ 集齐10枚碎片可以获得对应角色\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"📊 状态信息：\n"
                             f"⚔️ 今日剩余战斗次数：{char_info['battles_remaining']}")
                return
                
            # 检查剩余战斗次数
            logger.info(f"检查剩余战斗次数: {char_info['battles_remaining']}")
            if char_info["battles_remaining"] == 0:
                msg = "😴你今天已经战斗过了，请休息整备明天再战！"
                logger.info(msg)
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【🐘象岛传说竞技场】任务失败",
                        text=f"━━━━━━━━━━━━━━\n"
                             f"⚠️ 错误提示：\n"
                             f"😴 你今天已经战斗过了，请休息整备明天再战！\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"📊 状态信息：\n"
                             f"⚔️ 今日剩余战斗次数：{char_info['battles_remaining']}")
                return

            # 开始执行对战
            logger.info("开始执行对战...")
            battle_results = []
            failed_battles = []  # 记录失败的对战
            
            # 获取可执行的对战次数（不超过剩余次数）
            battles_to_execute = min(char_info["battles_remaining"], self._vs_boss_count)
            
            # 循环执行多次对战
            for i in range(battles_to_execute):
                # 计算当前场次（3 - 剩余次数 + 1 + i）
                current_battle = 3 - char_info["battles_remaining"] + 1 + i
                logger.info(f"开始第 {current_battle} 场对战")
                
                # 执行对战
                battle_result = None
                try:
                    battle_result = self.vs_boss()
                except Exception as e:
                    logger.error(f"第{current_battle}次对战失败: {e}")
                    # 记录失败的对战信息
                    failed_battles.append({
                        "battle_number": current_battle,
                        "battle_date": datetime.now().strftime('%Y-%m-%d'),
                        "error": str(e)
                    })
                
                if battle_result:
                    battle_results.append(battle_result)
                    logger.info(f"第 {current_battle} 次对战结果：{battle_result}")
                    
                    # 如果还有下一场对战，等待指定间隔时间
                    if i < battles_to_execute - 1:
                        logger.info(f"等待 {self._vs_boss_interval} 秒后进行下一场对战...")
                        time.sleep(self._vs_boss_interval)

            # 生成报告
            logger.info("开始生成报告...")
            rich_text_report = self.generate_rich_text_report(battle_results)
            logger.info(f"报告生成完成：\n{rich_text_report}")

            # 保存历史记录
            sign_dict = {
                "date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                "battle_results": battle_results,
                "battle_count": current_battle
            }

            # 读取历史记录
            history = self.get_data('sign_dict') or []
            history.append(sign_dict)
            
            # 只保留最新的N条记录
            if len(history) > self._history_count:
                history = sorted(history, key=lambda x: x.get("date") or "", reverse=True)[:self._history_count]
            
            self.save_data(key="sign_dict", value=history)

            # 发送通知
            if self._notify:
                self.post_message(
                    mtype=NotificationType.SiteMessage,
                    title="【象岛传说竞技场】任务完成：",
                    text=f"{rich_text_report}")

            # 处理失败的对战
            if failed_battles and self._retry_count > 0:
                logger.info(f"有 {len(failed_battles)} 场对战失败，将创建重试任务")
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【象岛传说竞技场】部分对战失败",
                        text=f"━━━━━━━━━━━━━━\n"
                             f"⚠️ 失败信息：\n"
                             f"共有 {len(failed_battles)} 场对战失败\n"
                             f"将创建重试任务\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"📊 失败场次：\n"
                             + "\n".join([f"第 {battle['battle_number']} 场" for battle in failed_battles]) + "\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # 为每个失败的对战创建重试任务
                for failed_battle in failed_battles:
                    # 创建多次重试任务
                    for retry_index in range(self._retry_count):
                        # 计算重试时间
                        retry_time = datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(hours=self._retry_interval * (retry_index + 1))
                        
                        # 生成唯一的任务ID
                        job_id = f"retry_battle_{failed_battle['battle_number']}_{retry_index}_{int(time.time())}"
                        
                        # 保存重试任务信息
                        self._retry_jobs[job_id] = {
                            "battle_number": failed_battle["battle_number"],
                            "battle_date": failed_battle["battle_date"],
                            "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "retry_index": retry_index + 1
                        }
                        
                        logger.info(f"已创建第 {failed_battle['battle_number']} 场对战的第 {retry_index + 1} 次重试任务，将在 {retry_time.strftime('%Y-%m-%d %H:%M:%S')} 执行")

        except Exception as e:
            logger.error(f"执行对战任务时发生异常: {e}")

    def generate_rich_text_report(self, battle_results: List[str]) -> str:
        """生成对战报告"""
        try:
            # 获取当前对战模式
            if datetime.today().weekday() in [0, 2]:
                battle_mode = "⚔️ 锋芒交错 - 1v1"
            elif datetime.today().weekday() in [1, 3]:
                battle_mode = "🐉 龙与凤的抗衡 - 5v5"
            elif datetime.today().weekday() in [4, 5, 6]:
                battle_mode = "👑 世界boss - 对抗Sysrous"
            
            # 统计信息
            total_battles = len(battle_results)
            victories = sum(1 for result in battle_results if "胜利" in result)
            defeats = sum(1 for result in battle_results if "战败" in result)
            draws = sum(1 for result in battle_results if "平局" in result)
            total_grass = sum(int(self.parse_battle_result(result)[1]) for result in battle_results)
            
            # 生成报告
            report = f"━━━━━━━━━━━━━━\n"
            report += f"🎮 对战模式：\n"
            report += f"{battle_mode}\n\n"
            
            report += f"━━━━━━━━━━━━━━\n"
            report += f"🎯 对战统计：\n"
            report += f"⚔️ 总对战次数：{total_battles}\n"
            report += f"🏆 胜利场次：{victories}\n"
            report += f"💔 战败场次：{defeats}\n"
            report += f"🤝 平局场次：{draws}\n"
            report += f"🌿 获得象草：{total_grass}\n\n"
            
            report += f"━━━━━━━━━━━━━━\n"
            report += f"📊 详细战报：\n"
            for i, result in enumerate(battle_results, 1):
                status, grass = self.parse_battle_result(result)
                status_emoji = "🏆" if status == "胜利" else "💔" if status == "战败" else "🤝"
                report += f"第 {i} 场：{status_emoji} {status} | 🌿 {grass}象草\n"
            
            # 添加时间戳
            report += f"\n⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return report
        except Exception as e:
            logger.error(f"生成报告时发生异常: {e}")
            return "象岛传说竞技场\n生成报告时发生错误，请检查日志以获取更多信息。"
        
    def parse_battle_result(self, result: str) -> Tuple[str, str]:
        """
        解析战斗结果，提取战斗状态和象草数量
        """
        # 提取战斗状态
        if "战败" in result:
            status = "战败"
        elif "胜利" in result:
            status = "胜利"
        elif "平局" in result:
            status = "平局"
        else:
            status = "未知"
            
        # 提取象草数量
        grass_match = re.search(r"(\d+)象草", result)
        grass_amount = grass_match.group(1) if grass_match else "0"
        
        return status, grass_amount

    def get_character_info(self) -> Dict[str, Any]:
        """
        获取英灵殿角色名称列表和剩余战斗次数
        返回:
            Dict[str, Any]: 包含以下信息的字典:
            - has_characters: bool, 是否拥有任何角色
            - character_names: List[str], 角色名称列表
            - battles_remaining: int, 今日剩余战斗次数
        """
        try:
            # 获取页面内容
            url = f"{self._vs_site_url}/customgame.php"
            headers = {
                "cookie": self._cookie,
                "referer": self._vs_site_url,
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"
            }
            response = requests.get(url, headers=headers, proxies=self._proxies, timeout=30)
            
            # 解析页面
            html = ContentFilter.lxml_get_HTML(response)
            
            # 获取所有角色名称
            character_names = []
            character_divs = html.xpath('//div[@class="member"]')
            
            # for div in character_divs:
                # 获取角色基本信息文本
                # info_text = " ".join(div.xpath('.//div[@class="memberText"]//text()'))
                
                # 解析角色名称 - 在memberText div中的第一个文本内容就是角色名称
                # name = div.xpath('.//div[@class="memberText"]/text()')[0].strip()
                # if name:
                #     character_names.append(name)
            
            # 获取剩余战斗次数 - 在vs_submit按钮的文本中
            battles_text = html.xpath('//b[contains(text(), "今日剩余战斗次数")]')
            battles_remaining = 0
            if battles_text:
                match = re.search(r"今日剩余战斗次数:\s*(\d+)", battles_text[0].text)
                if match:
                    battles_remaining = int(match.group(1))
            
            return {
                "has_characters": len(character_divs) > 0,
                "character_names": character_names,
                "battles_remaining": battles_remaining
            }
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"网络连接失败: {str(e)}")
            return {
                "has_characters": None,  # 使用None表示网络问题，不是真的没有角色
                "character_names": [],
                "battles_remaining": None,
                "error": "网络连接失败"
            }
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时: {str(e)}")
            return {
                "has_characters": None,
                "character_names": [],
                "battles_remaining": None,
                "error": "请求超时"
            }
        except Exception as e:
            logger.error(f"获取角色名称和战斗次数失败: {str(e)}")
            return {
                "has_characters": False,
                "character_names": [],
                "battles_remaining": 0
            }

    def get_site_cookie(self, domain: str = 'ptvicomo.net') -> str:
        """
        获取站点cookie
        
        Args:
            domain: 站点域名,默认为象岛站点
            
        Returns:
            str: 有效的cookie字符串,如果获取失败则返回空字符串
        """
        try:
            # 优先使用手动配置的cookie
            if self._cookie:
                if str(self._cookie).strip().lower() == "cookie":
                    logger.warning("手动配置的cookie无效")
                    return ""
                return self._cookie
                
            # 如果手动配置的cookie无效,则从站点配置获取
            site = self._siteoper.get_by_domain(domain)
            if not site:
                logger.warning(f"未找到站点: {domain}")
                return ""
                
            cookie = site.cookie
            if not cookie or str(cookie).strip().lower() == "cookie":
                logger.warning(f"站点 {domain} 的cookie无效")
                return ""
                
            # 将获取到的cookie保存到实例变量
            self._cookie = cookie
            return cookie
            
        except Exception as e:
            logger.error(f"获取站点cookie失败: {str(e)}")
            return ""

    def _fix_redirect_url(self, url: str) -> str:
        """
        修复重定向URL格式
        """
        try:
            # 从截图确认，URL格式 do=战斗结果=1756024896 是正确的
            # 不需要修复这种格式
            if "do=战斗结果=" in url:
                logger.info(f"URL格式正确，无需修复: {url}")
                return url
            
            # 检查其他可能的格式问题
            if "战斗结果" in url and "=" in url and "&" not in url:
                # 尝试修复参数格式
                parts = url.split("?")
                if len(parts) == 2:
                    base_url = parts[0]
                    params = parts[1]
                    # 将单个参数转换为标准格式
                    if "=" in params:
                        param_parts = params.split("=")
                        if len(param_parts) >= 2:
                            key = param_parts[0]
                            value = "=".join(param_parts[1:])
                            fixed_url = f"{base_url}?{key}={value}"
                            logger.info(f"修复参数格式: {url} -> {fixed_url}")
                            return fixed_url
            
            return url
        except Exception as e:
            logger.error(f"修复重定向URL时发生异常: {str(e)}")
            return url

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
        """获取插件状态"""
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取命令"""
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """获取API"""
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        """
        service = []
        if self._cron:
            service.append({
                "id": "VicomoVS",
                "name": "象岛传说竞技场 - 定时任务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self._battle_task,
                "kwargs": {}
            })

        # 注册重试任务
        if self._retry_jobs:
            for job_id, job_info in self._retry_jobs.items():
                # 计算重试时间
                create_time = datetime.strptime(job_info['create_time'], '%Y-%m-%d %H:%M:%S')
                retry_time = create_time + timedelta(hours=self._retry_interval * job_info['retry_index'])
                
                if retry_time < datetime.now():
                    continue
                    
                service.append({
                    "id": job_id,
                    "name": f"象岛传说竞技场-第{job_info['retry_index']}次重试第{job_info['battle_number']}场对战",
                    "trigger": "date",
                    "run_date": retry_time,
                    "func": self._retry_battle_task,
                    "kwargs": {
                        "battle_info": {
                            "battle_number": job_info["battle_number"],
                            "battle_date": job_info["battle_date"],
                            "job_id": job_id,
                            "retry_index": job_info["retry_index"]
                        }
                    }
                })

        if service:
            return service

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
                                    'class': 'px-6 pb-0'
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
                                'component': 'VDivider',
                                'props': {
                                    'class': 'mx-4 my-2'
                                }
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
                                                    'sm': 4
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
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 4
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'notify',
                                                            'label': '开启通知',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 4
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'onlyonce',
                                                            'label': '立即运行一次',
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
                    # 功能设置
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
                                    'class': 'px-6 pb-0'
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
                                                'text': 'mdi-sword-cross'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '功能设置'
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
                                                    'sm': 4
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'auto_cookie',
                                                            'label': '使用站点Cookie',
                                                            'color': 'primary',
                                                            'hide-details': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 4
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'use_proxy',
                                                            'label': '使用代理',
                                                            'color': 'primary',
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
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 6
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'cookie',
                                                            'label': '站点Cookie',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'placeholder': '🐘站点Cookie',
                                                            'class': 'mt-2',
                                                            'disabled': 'auto_cookie'
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'retry_count',
                                                            'label': '重试任务次数',
                                                            'type': 'number',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'hint': '为0时，不创建重试任务',
                                                            'class': 'mt-2',
                                                            'items': [
                                                                {'title': '关闭', 'value': 0},
                                                                {'title': '1次', 'value': 1},
                                                                {'title': '2次', 'value': 2},
                                                                {'title': '3次', 'value': 3}
                                                            ]
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'retry_interval',
                                                            'label': '重试间隔(小时)',
                                                            'type': 'number',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'hint': '重试任务间隔时间',
                                                            'class': 'mt-2',
                                                            'items': [
                                                                {'title': '1小时', 'value': 1},
                                                                {'title': '2小时', 'value': 2},
                                                                {'title': '3小时', 'value': 3},
                                                                {'title': '4小时', 'value': 4}
                                                            ]
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
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'vs_boss_count',
                                                            'label': '对战次数(秒)',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'hint': '对战次数',
                                                            'class': 'mt-2',
                                                            'items': [
                                                                {'title': '1次', 'value': 1},
                                                                {'title': '2次', 'value': 2},
                                                                {'title': '3次', 'value': 3}
                                                            ]
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'vs_boss_interval',
                                                            'label': '对战间隔(秒)',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'hint': '对战间隔',
                                                            'class': 'mt-2',
                                                            'items': [
                                                                {'title': '5秒', 'value': 5},
                                                                {'title': '10秒', 'value': 10},
                                                                {'title': '15秒', 'value': 15},
                                                                {'title': '20秒', 'value': 20}
                                                            ]
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': cron_field_component,
                                                        'props': {
                                                            'model': 'cron',
                                                            'label': '执行周期(cron)',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'placeholder': '5位cron表达式，默认每天9点执行',
                                                            'class': 'mt-2'
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {
                                                    'cols': 12,
                                                    'sm': 3
                                                },
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'history_count',
                                                            'label': '保留历史条数',
                                                            'variant': 'outlined',
                                                            'color': 'primary',
                                                            'hide-details': True,
                                                            'class': 'mt-2'
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
                                    'class': 'px-6 pb-0'
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
                                                'text': 'mdi-treasure-chest'
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
                                'props': {
                                    'class': 'mx-4 my-2'
                                }
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6 pb-6'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1'
                                        },
                                        'content': [
                                            {
                                                'component': 'div',
                                                'props': {
                                                    'class': 'mb-4'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-center mb-2'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'style': 'color: #16b1ff;',
                                                                    'class': 'mr-2',
                                                                    'size': 'small'
                                                                },
                                                                'text': 'mdi-cog'
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-bold'
                                                                },
                                                                'text': '基本设置'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'pl-4'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'mb-2 d-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '⚙️'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '启用【使用站点Cookie】功能后，插件会自动获取已配置站点的cookie，请确保cookie有效。'
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
                                                    'class': 'mb-4'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-center mb-2'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'style': 'color: #16b1ff;',
                                                                    'class': 'mr-2',
                                                                    'size': 'small'
                                                                },
                                                                'text': 'mdi-refresh'
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-bold'
                                                                },
                                                                'text': '重试机制'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'pl-4'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'mb-2 d-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '🔄'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '当对战失败时，系统会自动创建重试任务'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'mb-2 d-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '📊'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '重试任务次数：设置每个失败对战最多重试几次'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'mb-2 d-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '⏱'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '重试间隔：设置每次重试之间的时间间隔'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'mb-2 d-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '🤖'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '重试任务会在指定时间自动执行，无需手动干预'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'd-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '📢'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '重试结果会通过通知发送，请确保开启通知功能'
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
                                                    'class': 'mb-4'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-center mb-2'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'style': 'color: #16b1ff;',
                                                                    'class': 'mr-2',
                                                                    'size': 'small'
                                                                },
                                                                'text': 'mdi-sword-cross'
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-bold'
                                                                },
                                                                'text': '战斗规则'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'pl-4'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'mb-2 d-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '🎮'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '每人每天拥有三次参战机会，每场战斗最长持续30回合，击溃敌方全体角色获得胜利。'
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
                                                    'class': 'mb-4'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'd-flex align-center mb-2'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VIcon',
                                                                'props': {
                                                                    'style': 'color: #16b1ff;',
                                                                    'class': 'mr-2',
                                                                    'size': 'small'
                                                                },
                                                                'text': 'mdi-calendar'
                                                            },
                                                            {
                                                                'component': 'span',
                                                                'props': {
                                                                    'class': 'text-subtitle-1 font-weight-bold'
                                                                },
                                                                'text': '对战模式'
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'div',
                                                        'props': {
                                                            'class': 'pl-4'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'mb-2 d-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '⚔️'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '周一和周三是锋芒交错的时刻，1v1的激烈对决等着您。'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'mb-2 d-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '🐉'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '周二周四上演龙与凤的抗衡，5v5的团战战场精彩纷呈。'
                                                                    }
                                                                ]
                                                            },
                                                            {
                                                                'component': 'div',
                                                                'props': {
                                                                    'class': 'd-flex align-center'
                                                                },
                                                                'content': [
                                                                    {
                                                                        'component': 'span',
                                                                        'props': {
                                                                            'class': 'mr-2',
                                                                            'style': 'width: 24px; text-align: center; margin-left: 8px;'
                                                                        },
                                                                        'text': '👑'
                                                                    },
                                                                    {
                                                                        'component': 'span',
                                                                        'text': '周五、周六和周日，世界boss【Sysrous】将会降临，勇士们齐心协力，挑战最强BOSS，获得奖励Sysrous魔力/200000+总伤害/4的象草。'
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
                    }
                ]
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "notify": True,
            "use_proxy": True,
            "cookie": "",
            "history_count": 10,
            "cron": "0 9 * * *",
            "vs_boss_count": 3,
            "vs_boss_interval": 15,
            "retry_count": 1,
            "retry_interval": 2,
            "auto_cookie": False
        }

    def get_page(self) -> List[dict]:
        # 查询同步详情
        historys = self.get_data('sign_dict')
        if not historys:
            return [
                {
                    'component': 'VCard',
                    'props': {
                        'variant': 'flat',
                        'class': 'mb-4'
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
                                                'color': 'primary',
                                                'class': 'mr-3',
                                                'size': 'default'
                                            },
                                            'text': 'mdi-database-remove'
                                        },
                                        {
                                            'component': 'span',
                                            'text': '暂无历史记录'
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]

        if not isinstance(historys, list):
            return [
                {
                    'component': 'VCard',
                    'props': {
                        'variant': 'flat',
                        'class': 'mb-4'
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
                                                'color': 'error',
                                                'class': 'mr-3',
                                                'size': 'default'
                                            },
                                            'text': 'mdi-alert-circle'
                                        },
                                        {
                                            'component': 'span',
                                            'text': '数据格式错误'
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]

        # 展开所有历史批次的battle_results为明细列表，并按天编号场次
        details = []
        # 先按date升序排列（旧到新）
        historys_sorted = sorted(historys, key=lambda x: x.get("date", ""))
        # 按天统计场次编号
        day_counters = {}
        for history in historys_sorted:
            date = history.get("date", "")
            day = date[:10]
            battle_results = history.get("battle_results", [])
            for result in battle_results:
                if day not in day_counters:
                    day_counters[day] = 1
                else:
                    day_counters[day] += 1
                details.append({
                    "date": date,
                    "battle_count": f"第{day_counters[day]}场",
                    "result": result
                })

        # 渲染时按date倒序排列（新到旧）
        details = sorted(details, key=lambda x: (x["date"]), reverse=True)

        # 取前N条
        max_count = self._history_count or 10
        details = details[:max_count]

        return [
            {
                'component': 'VCard',
                'props': {
                    'variant': 'flat',
                    'class': 'mb-4 elevation-2',
                    'style': 'border-radius: 16px;'
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
                                            'style': 'color: #9155fd;',
                                            'class': 'mr-3',
                                            'size': 'default'
                                        },
                                        'text': 'mdi-history'
                                    },
                                    {
                                        'component': 'span',
                                        'text': '历史记录'
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VCardText',
                        'props': {
                            'class': 'pa-6'
                        },
                        'content': [
                            {
                                'component': 'VTable',
                                'props': {
                                    'hover': True,
                                    'density': 'comfortable',
                                    'class': 'rounded-lg'
                                },
                                'content': [
                                    {
                                        'component': 'thead',
                                        'content': [
                                            {
                                                'component': 'tr',
                                                'content': [
                                                    {
                                                        'component': 'th',
                                                        'props': {
                                                            'class': 'text-center text-body-1 font-weight-bold'
                                                        },
                                                        'content': [
                                                            {'component': 'VIcon', 'props': {'style': 'color: #1976d2;', 'size': 'small', 'class': 'mr-1'}, 'text': 'mdi-clock-time-four-outline'},
                                                            {'component': 'span', 'text': '执行时间'}
                                                        ]
                                                    },
                                                    {
                                                        'component': 'th',
                                                        'props': {
                                                            'class': 'text-center text-body-1 font-weight-bold'
                                                        },
                                                        'content': [
                                                            {'component': 'VIcon', 'props': {'style': 'color: #1976d2;', 'size': 'small', 'class': 'mr-1'}, 'text': 'mdi-counter'},
                                                            {'component': 'span', 'text': '战斗场次'}
                                                        ]
                                                    },
                                                    {
                                                        'component': 'th',
                                                        'props': {
                                                            'class': 'text-center text-body-1 font-weight-bold'
                                                        },
                                                        'content': [
                                                            {'component': 'VIcon', 'props': {'style': 'color: #fb8c00;', 'size': 'small', 'class': 'mr-1'}, 'text': 'mdi-sword-cross'},
                                                            {'component': 'span', 'text': '战斗结果'}
                                                        ]
                                                    },
                                                    {
                                                        'component': 'th',
                                                        'props': {
                                                            'class': 'text-center text-body-1 font-weight-bold'
                                                        },
                                                        'content': [
                                                            {'component': 'VIcon', 'props': {'color': 'success', 'size': 'small', 'class': 'mr-1'}, 'text': 'mdi-leaf'},
                                                            {'component': 'span', 'text': '获得象草'}
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'tbody',
                                        'content': [
                                            {
                                                'component': 'tr',
                                                'props': {
                                                    'class': 'text-sm'
                                                },
                                                'content': [
                                                    {
                                                        'component': 'td',
                                                        'props': {
                                                            'class': 'text-center text-high-emphasis'
                                                        },
                                                        'content': [
                                                            {'component': 'VIcon', 'props': {'style': 'color: #1976d2;', 'size': 'x-small', 'class': 'mr-1'}, 'text': 'mdi-clock-time-four-outline'},
                                                            {'component': 'span', 'text': detail["date"][:10]}
                                                        ]
                                                    },
                                                    {
                                                        'component': 'td',
                                                        'props': {
                                                            'class': 'text-center text-high-emphasis'
                                                        },
                                                        'content': [
                                                            {'component': 'VIcon', 'props': {'style': 'color: #1976d2;', 'size': 'x-small', 'class': 'mr-1'}, 'text': 'mdi-sword-cross'},
                                                            {'component': 'span', 'text': detail["battle_count"]}
                                                        ]
                                                    },
                                                    {
                                                        'component': 'td',
                                                        'props': {
                                                            'class': 'text-center text-high-emphasis'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'VChip',
                                                                'props': {
                                                                    'color': 'success' if self.parse_battle_result(detail["result"])[0] == '胜利' else '#ffcdd2' if self.parse_battle_result(detail["result"])[0] == '战败' else 'info',
                                                                    'variant': 'elevated',
                                                                    'size': 'small',
                                                                    'class': 'mr-1',
                                                                },
                                                                'content': [
                                                                    {'component': 'span', 'text': '🏆' if self.parse_battle_result(detail["result"])[0] == '胜利' else '💔' if self.parse_battle_result(detail["result"])[0] == '战败' else '🤝'},
                                                                    {'component': 'span', 'text': self.parse_battle_result(detail["result"])[0]}
                                                                ]
                                                            }
                                                        ]
                                                    },
                                                    {
                                                        'component': 'td',
                                                        'props': {
                                                            'class': 'text-center text-high-emphasis'
                                                        },
                                                        'content': [
                                                            {'component': 'VIcon', 'props': {'color': 'success', 'size': 'x-small', 'class': 'mr-1'}, 'text': 'mdi-leaf'},
                                                            {'component': 'span', 'text': self.parse_battle_result(detail["result"])[1]}
                                                        ]
                                                    }
                                                ]
                                            } for detail in details
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'div',
                                'props': {
                                    'class': 'text-caption text-grey mt-2',
                                    'style': 'background: #f5f5f7; border-radius: 8px; padding: 6px 12px; display: inline-block;'
                                },
                                'content': [
                                    {'component': 'VIcon', 'props': {'size': 'x-small', 'class': 'mr-1'}, 'text': 'mdi-format-list-bulleted'},
                                    {'component': 'span', 'text': f'共显示 {len(details)} 条记录'}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

    def stop_service(self) -> None:
        """
        退出插件
        """
        try:
            if self._scheduler:
                # 清理所有重试任务
                for job_id in list(self._retry_jobs.keys()):
                    try:
                        self._scheduler.remove_job(job_id)
                        del self._retry_jobs[job_id]
                    except Exception as e:
                        logger.error(f"清理重试任务 {job_id} 失败: {str(e)}")
                
                # 清理其他任务
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("退出插件失败：%s" % str(e))

    def _retry_battle_task(self, battle_info: Dict[str, Any]) -> None:
        """
        执行重试对战任务
        
        Args:
            battle_info: 对战信息,包含:
                - battle_number: 对战场次
                - battle_date: 对战日期
                - job_id: 任务ID
                - retry_index: 重试次数
        """
        try:
            logger.info(f"开始执行第 {battle_info['battle_number']} 场对战的第 {battle_info['retry_index']} 次重试任务")
            
            # 执行对战
            battle_result = self.vs_boss()
            
            if battle_result:
                # 更新历史记录
                history = self.get_data('sign_dict') or []
                # 找到对应日期的记录
                for record in history:
                    if record.get("date", "").startswith(battle_info['battle_date']):
                        # 更新对战结果
                        battle_results = record.get("battle_results", [])
                        if len(battle_results) >= battle_info['battle_number']:
                            battle_results[battle_info['battle_number'] - 1] = battle_result
                            record["battle_results"] = battle_results
                            break
                
                # 保存更新后的历史记录
                self.save_data(key="sign_dict", value=history)
                
                # 发送通知
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【象岛传说竞技场】重试任务完成",
                        text=f"━━━━━━━━━━━━━━\n"
                             f"🎯 重试信息：\n"
                             f"⚔️ 第 {battle_info['battle_number']} 场对战第 {battle_info['retry_index']} 次重试成功\n"
                             f"📅 对战日期：{battle_info['battle_date']}\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"📊 对战结果：\n"
                             f"{battle_result}\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                logger.error(f"第 {battle_info['battle_number']} 场对战第 {battle_info['retry_index']} 次重试失败")
                if self._notify:
                    self.post_message(
                        mtype=NotificationType.SiteMessage,
                        title="【象岛传说竞技场】重试任务失败",
                        text=f"━━━━━━━━━━━━━━\n"
                             f"⚠️ 错误提示：\n"
                             f"第 {battle_info['battle_number']} 场对战第 {battle_info['retry_index']} 次重试失败\n"
                             f"📅 对战日期：{battle_info['battle_date']}\n\n"
                             f"━━━━━━━━━━━━━━\n"
                             f"⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 清理重试任务信息
            if battle_info['job_id'] in self._retry_jobs:
                del self._retry_jobs[battle_info['job_id']]
                
        except Exception as e:
            logger.error(f"执行重试对战任务时发生异常: {e}")
            if self._notify:
                self.post_message(
                    mtype=NotificationType.SiteMessage,
                    title="【象岛传说竞技场】重试任务异常",
                    text=f"━━━━━━━━━━━━━━\n"
                         f"⚠️ 错误提示：\n"
                         f"执行重试对战任务时发生异常\n"
                         f"📅 对战日期：{battle_info['battle_date']}\n"
                         f"⚔️ 对战场次：{battle_info['battle_number']}\n"
                         f"🔄 重试次数：{battle_info['retry_index']}\n"
                         f"❌ 异常信息：{str(e)}\n\n"
                         f"━━━━━━━━━━━━━━\n"
                         f"⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 清理重试任务信息
            if battle_info['job_id'] in self._retry_jobs:
                del self._retry_jobs[battle_info['job_id']]
