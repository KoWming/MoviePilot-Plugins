from typing import Dict, List
from urllib.parse import urljoin

from app.log import logger
from app.utils.http import RequestUtils
from app.core.config import settings

from .base import BaseMedalSiteHandler


class RousiProMedalHandler(BaseMedalSiteHandler):
    """Rousi Pro 站点勋章处理器"""

    API_PATH = "/api/medals"
    USER_MEDALS_API_PATH = "/api/user/medals"
    USER_MEDALS_WEAR_API_PATH = "/api/user/medals/{medal_id}/wear"
    USER_MEDALS_UNWEAR_API_PATH = "/api/user/medals/{medal_id}/unwear"

    def match(self, site) -> bool:
        """判断是否为 Rousi Pro 站点"""
        site_name = (site.name or "").lower()
        site_url = (site.url or "").lower()
        return (
            "rousi" in site_name
            or "rousi" in site_url
            or "rousi.pro" in site_url
        )

    def should_append_unmatched_user_medals(self) -> bool:
        """Rousi 仅以商店勋章为准，不追加独立的用户勋章卡片"""
        return False

    def fetch_medals(self, site) -> List[Dict]:
        """获取 Rousi Pro 勋章数据"""
        try:
            site_name = site.name
            site_url = site.url.rstrip("/")

            url = f"{site_url}{self.API_PATH}"
            logger.info(f"正在获取【{site_name}】站点勋章数据: {url}")

            res = self._request_with_retry(
                url=url,
                cookies=getattr(site, "cookie", None),
                ua=getattr(site, "ua", None),
                headers=self._build_headers(site, site_url),
            )
            if not res:
                logger.error(f"请求 Rousi Pro 勋章接口失败！站点：{site_name}")
                return []

            try:
                payload = res.json()
            except Exception as e:
                logger.error(f"解析 Rousi Pro 勋章接口响应失败: {e}")
                return []

            if payload.get("code") != 0:
                logger.error(
                    f"Rousi Pro 勋章接口返回异常: code={payload.get('code')}, message={payload.get('message')}"
                )
                return []

            items = payload.get("data") or []
            medals: List[Dict] = []
            for item in items:
                try:
                    medal = self._process_medal_item(item, site_name, site_url)
                    if medal:
                        medals.append(medal)
                except Exception as e:
                    logger.error(f"处理 Rousi Pro 勋章数据时发生错误: {e}")

            logger.info(f"共获取到 {len(medals)} 个 Rousi Pro 勋章数据")
            return medals
        except Exception as e:
            logger.error(f"处理 Rousi Pro 站点勋章数据时发生错误: {e}")
            return []

    def fetch_user_medals(self, site) -> List[Dict]:
        """获取 Rousi Pro 用户已拥有勋章"""
        try:
            site_name = site.name
            site_url = site.url.rstrip("/")
            url = f"{site_url}{self.USER_MEDALS_API_PATH}"
            logger.info(f"正在获取【{site_name}】用户已拥有勋章数据: {url}")

            res = self._request_with_retry(
                url=url,
                cookies=getattr(site, "cookie", None),
                ua=getattr(site, "ua", None),
                headers=self._build_headers(site, site_url),
            )
            if not res:
                logger.error(f"请求 Rousi Pro 用户勋章接口失败！站点：{site_name}")
                return []

            try:
                payload = res.json()
            except Exception as e:
                logger.error(f"解析 Rousi Pro 用户勋章接口响应失败: {e}")
                return []

            if payload.get("code") != 0:
                logger.error(
                    f"Rousi Pro 用户勋章接口返回异常: code={payload.get('code')}, message={payload.get('message')}"
                )
                return []

            items = payload.get("data") or []
            user_medals: List[Dict] = []
            for item in items:
                try:
                    medal = self._process_user_medal_item(item, site_name, site_url)
                    if medal:
                        user_medals.append(medal)
                except Exception as e:
                    logger.error(f"处理 Rousi Pro 用户勋章数据时发生错误: {e}")

            logger.info(f"共获取到 {len(user_medals)} 个 Rousi Pro 已拥有勋章")
            return user_medals
        except Exception as e:
            logger.error(f"获取 Rousi Pro 用户勋章数据失败: {e}")
            return []

    def _process_medal_item(self, item: Dict, site_name: str, site_url: str) -> Dict:
        """处理单个勋章项"""
        medal: Dict = {
            "medal_id": item.get("id", "") or "",
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "price": self._safe_int(item.get("price")),
            "site": site_name,
            "validity": self._format_duration(item.get("duration")),
            "bonus_rate": self._format_bonus_rate(item),
            "purchase_status": self._map_purchase_status(item),
            "stock": self._format_stock(item.get("inventory")),
            "currency": "魔力",
            "group": self._map_group(item),
            "new_time": item.get("created_at", "") or "",
            "saleBeginTime": item.get("sale_begin_time") or "不限",
            "saleEndTime": item.get("sale_end_time") or "长期",
        }

        image_url = item.get("image_small") or item.get("image_large") or ""
        if image_url:
            if not image_url.startswith(("http://", "https://")):
                image_url = urljoin(f"{site_url}/", image_url.lstrip("/"))
            medal["imageSmall"] = image_url
            medal["original_image_url"] = image_url

        return self._format_medal_data(medal)

    def purchase_medal(self, site, medal: Dict) -> Dict:
        """购买 Rousi Pro 勋章"""
        site_name = getattr(site, "name", "")
        site_url = (getattr(site, "url", "") or "").rstrip("/")
        medal_id = medal.get("medal_id") or medal.get("id")
        medal_name = medal.get("name") or "未知勋章"

        if not medal_id:
            return {"success": False, "message": f"{medal_name} 缺少勋章ID，无法购买"}

        site_cookie = getattr(site, "cookie", None)
        headers = self._build_headers(site, site_url, include_ua=True)

        req_kwargs = {
            "headers": headers,
            "timeout": self._timeout,
        }
        if site_cookie:
            req_kwargs["cookies"] = site_cookie
        if self._use_proxy and hasattr(settings, 'PROXY'):
            req_kwargs['proxies'] = settings.PROXY

        url = f"{site_url}/api/medals/{medal_id}/purchase"
        try:
            res = RequestUtils(**req_kwargs).post_res(url=url)
            if not res:
                return {"success": False, "message": f"请求购买接口失败：{medal_name}"}

            try:
                payload = res.json()
            except Exception:
                payload = {}

            if res.status_code != 200:
                return {
                    "success": False,
                    "message": payload.get("message") or f"购买失败，HTTP {res.status_code}"
                }

            success = payload.get("code") == 0 or payload.get("success") is True
            message = payload.get("message") or ("购买成功" if success else "购买失败")
            return {
                "success": success,
                "message": message,
                "data": payload.get("data") or payload
            }
        except Exception as e:
            logger.error(f"购买 Rousi Pro 勋章失败: {site_name} - {medal_name} - {e}")
            return {"success": False, "message": f"购买失败: {e}"}

    def wear_medal(self, site, medal: Dict) -> Dict:
        """佩戴 Rousi Pro 勋章"""
        return self._toggle_wear_medal(site, medal, wear=True)

    def unwear_medal(self, site, medal: Dict) -> Dict:
        """取下 Rousi Pro 勋章"""
        return self._toggle_wear_medal(site, medal, wear=False)

    def _process_user_medal_item(self, item: Dict, site_name: str, site_url: str) -> Dict:
        """处理用户已拥有勋章项"""
        medal_info = item.get("medal") or {}
        if not medal_info:
            return {}

        medal = self._process_medal_item(medal_info, site_name, site_url)
        medal["medal_id"] = medal_info.get("id") or item.get("medal_id") or medal.get("medal_id")
        medal["purchase_status"] = "已拥有"
        medal["wear_status"] = "已佩戴" if item.get("status") == 2 else "未佩戴"
        medal["new_time"] = item.get("created_at") or medal.get("new_time") or ""
        medal["validity"] = self._format_duration(medal_info.get("duration"))
        medal["saleBeginTime"] = medal_info.get("sale_begin_time") or "不限"
        medal["saleEndTime"] = medal_info.get("sale_end_time") or "长期"
        medal["stock"] = self._format_stock(medal_info.get("inventory"))
        return medal

    def _toggle_wear_medal(self, site, medal: Dict, wear: bool) -> Dict:
        site_name = getattr(site, "name", "")
        site_url = (getattr(site, "url", "") or "").rstrip("/")
        medal_id = medal.get("medal_id") or medal.get("id")
        medal_name = medal.get("name") or "未知勋章"

        if not medal_id:
            return {"success": False, "message": f"{medal_name} 缺少勋章ID，无法操作"}

        api_path = self.USER_MEDALS_WEAR_API_PATH if wear else self.USER_MEDALS_UNWEAR_API_PATH
        action_text = "佩戴" if wear else "取下"
        url = f"{site_url}{api_path.format(medal_id=medal_id)}"
        site_cookie = getattr(site, "cookie", None)
        headers = self._build_headers(site, site_url, include_ua=True)

        req_kwargs = {
            "headers": headers,
            "timeout": self._timeout,
        }
        if site_cookie:
            req_kwargs["cookies"] = site_cookie
        if self._use_proxy and hasattr(settings, 'PROXY'):
            req_kwargs['proxies'] = settings.PROXY

        try:
            res = RequestUtils(**req_kwargs).post_res(url=url)
            if not res:
                return {"success": False, "message": f"请求{action_text}接口失败：{medal_name}"}

            try:
                payload = res.json()
            except Exception:
                payload = {}

            if res.status_code != 200:
                return {
                    "success": False,
                    "message": payload.get("message") or f"{action_text}失败，HTTP {res.status_code}"
                }

            success = payload.get("code") == 0 or payload.get("success") is True
            message = payload.get("message") or (f"{action_text}成功" if success else f"{action_text}失败")
            return {
                "success": success,
                "message": message,
                "data": payload.get("data") or payload
            }
        except Exception as e:
            logger.error(f"{action_text} Rousi Pro 勋章失败: {site_name} - {medal_name} - {e}")
            return {"success": False, "message": f"{action_text}失败: {e}"}

    @staticmethod
    def _build_headers(site, site_url: str, include_ua: bool = False) -> Dict:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{site_url}/",
        }

        site_token = getattr(site, "token", None)
        site_apikey = getattr(site, "apikey", None)
        site_ua = getattr(site, "ua", None)

        if include_ua:
            headers["User-Agent"] = site_ua if site_ua else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        if site_token:
            headers["Authorization"] = site_token
        if site_apikey:
            headers["apikey"] = site_apikey

        return headers

    @staticmethod
    def _safe_int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _format_duration(duration) -> str:
        if duration in (None, "", 0):
            return "长期"
        return f"{duration} 天"

    @staticmethod
    def _format_stock(inventory) -> str:
        if inventory is None:
            return "不限"
        return str(inventory)

    @staticmethod
    def _format_bonus_rate(item: Dict) -> str:
        parts = []
        karma_bonus = item.get("karma_bonus")
        if karma_bonus not in (None, "", 0):
            try:
                parts.append(f"魔力 +{float(karma_bonus) * 100:g}%")
            except (TypeError, ValueError):
                parts.append(f"魔力 +{karma_bonus}")

        upload_bonus = item.get("upload_bonus")
        if upload_bonus not in (None, "", 0):
            parts.append(f"上传 +{upload_bonus}")

        download_discount = item.get("download_discount")
        if download_discount not in (None, "", 0):
            parts.append(f"下载 -{download_discount}")

        invite_bonus = item.get("invite_bonus")
        if invite_bonus not in (None, "", 0):
            parts.append(f"邀请 +{invite_bonus}")

        return " / ".join(parts)

    @staticmethod
    def _map_purchase_status(item: Dict) -> str:
        get_type = item.get("get_type")
        if get_type == 1:
            return "购买"
        if get_type == 2:
            return "仅授予"
        if get_type == 4:
            return "工作组"
        return "未知"

    @staticmethod
    def _map_group(item: Dict) -> str:
        get_type = item.get("get_type")
        if get_type == 1:
            return "可购买勋章"
        return "特殊勋章"