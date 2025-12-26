"""
飞书 Cookie 获取模块 (无 SDK 依赖版本)
使用 httpx 直接调用飞书开放 API
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger("feishu-cookie")

# 飞书配置
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_APP_TOKEN = os.environ.get("FEISHU_APP_TOKEN", "")
FEISHU_COOKIE_TABLE_ID = os.environ.get("FEISHU_COOKIE_TABLE_ID", "tblYa2d2a5lypzqz")

FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuCookieManager:
    """飞书 Cookie 管理器 (无 SDK 版本)"""

    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.app_token = FEISHU_APP_TOKEN
        self.table_id = FEISHU_COOKIE_TABLE_ID
        self._tenant_token = None

        if not self.app_id or not self.app_secret:
            raise ValueError("FEISHU_APP_ID and FEISHU_APP_SECRET must be set")

    def _get_tenant_token(self) -> str:
        """获取 tenant_access_token"""
        if self._tenant_token:
            return self._tenant_token

        url = f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload)
            data = resp.json()

        if data.get("code") != 0:
            raise Exception(f"Failed to get tenant token: {data}")

        self._tenant_token = data["tenant_access_token"]
        return self._tenant_token

    def get_active_cookie(self) -> Optional[Dict[str, Any]]:
        """获取一个可用的 Cookie"""
        try:
            token = self._get_tenant_token()

            # 列出记录，筛选状态为 active 的
            url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
            headers = {"Authorization": f"Bearer {token}"}
            params = {
                "filter": 'CurrentValue.[状态] = "active"',
                "page_size": 1
            }

            with httpx.Client(timeout=15) as client:
                resp = client.get(url, headers=headers, params=params)
                data = resp.json()

            if data.get("code") != 0:
                logger.error(f"Failed to get records: {data}")
                return None

            items = data.get("data", {}).get("items", [])
            if not items:
                logger.warning("No active cookie found in Feishu")
                return None

            record = items[0]
            fields = record.get("fields", {})

            # 获取 cookie 值 - 支持多种字段名
            cookie_value = None
            for key in ["cookie_value", "Cookie", "cookie", "cookies"]:
                if key in fields:
                    val = fields[key]
                    # 处理飞书多行文本格式
                    if isinstance(val, list):
                        cookie_value = val[0].get("text", "") if val else ""
                    else:
                        cookie_value = str(val)
                    break

            if not cookie_value:
                logger.error(f"Cookie field not found in record. Fields: {list(fields.keys())}")
                return None

            # 解析为 cookie 列表格式
            cookies = self._parse_cookie_string(cookie_value)

            return {
                "record_id": record.get("record_id"),
                "cookies": cookies,
                "account": fields.get("账号", fields.get("account", "")),
                "status": fields.get("状态", fields.get("status", "active"))
            }

        except Exception as e:
            logger.error(f"Error getting cookie from Feishu: {e}")
            return None

    def _parse_cookie_string(self, cookie_str: str) -> List[Dict]:
        """解析 cookie 字符串为 Playwright cookies 格式"""
        cookies = []

        # 清理字符串
        cookie_str = cookie_str.strip()

        # 如果已经是 JSON 格式
        if cookie_str.startswith("["):
            try:
                parsed = json.loads(cookie_str)
                # 确保每个 cookie 有必需字段
                for c in parsed:
                    if "name" in c and "value" in c:
                        cookies.append({
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c.get("domain", ".xiaohongshu.com"),
                            "path": c.get("path", "/")
                        })
                return cookies
            except json.JSONDecodeError:
                pass

        # 解析 key=value; 格式
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookies.append({
                    "name": key.strip(),
                    "value": value.strip(),
                    "domain": ".xiaohongshu.com",
                    "path": "/"
                })

        return cookies

    def update_cookie_status(self, record_id: str, status: str, error_msg: str = "") -> bool:
        """更新 Cookie 状态到飞书"""
        try:
            from datetime import datetime
            token = self._get_tenant_token()

            url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}"
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "fields": {
                    "状态": status,
                    "最后检查": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            if error_msg:
                payload["fields"]["错误信息"] = error_msg

            with httpx.Client(timeout=10) as client:
                resp = client.put(url, headers=headers, json=payload)
                data = resp.json()

            if data.get("code") != 0:
                logger.error(f"Failed to update status: {data}")
                return False

            logger.info(f"Updated cookie {record_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Error updating cookie status: {e}")
            return False


def get_xhs_cookies_from_feishu() -> Optional[List[Dict]]:
    """便捷函数：从飞书获取 XHS cookies"""
    try:
        manager = FeishuCookieManager()
        result = manager.get_active_cookie()
        if result:
            logger.info(f"Got {len(result['cookies'])} cookies from Feishu")
            return result["cookies"]
        return None
    except Exception as e:
        logger.error(f"Failed to get cookies from Feishu: {e}")
        return None


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)
    cookies = get_xhs_cookies_from_feishu()
    if cookies:
        print(f"Got {len(cookies)} cookies:")
        for c in cookies[:3]:
            print(f"  {c['name']}: {c['value'][:20]}...")
    else:
        print("No cookies found")
