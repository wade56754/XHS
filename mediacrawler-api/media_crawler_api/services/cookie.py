"""
Cookie 管理服务

负责 Cookie 的:
- 存储和加密
- 获取和分配
- 状态管理 (active/cooling/invalid/banned)
- 使用统计

Cookie 状态机:
    active -> cooling (连续错误 >= 3)
    cooling -> active (冷却结束)
    cooling -> banned (冷却期再次错误)
    active -> invalid (累计错误 >= 10 或验证失败)
    active -> banned (平台封禁检测)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from enum import Enum
import asyncio

from ..utils.crypto import cookie_encryption, mask_cookie
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CookieStatus(str, Enum):
    """Cookie 状态"""
    ACTIVE = "active"       # 活跃可用
    COOLING = "cooling"     # 冷却中
    INVALID = "invalid"     # 已失效
    BANNED = "banned"       # 已封禁


@dataclass
class Cookie:
    """
    Cookie 实体

    存储 Cookie 的所有信息
    """
    name: str                           # Cookie 标识名
    platform: str = "xhs"               # 所属平台
    encrypted_value: str = ""           # 加密后的值
    encryption_key_id: str = ""         # 加密密钥 ID
    status: CookieStatus = CookieStatus.ACTIVE
    priority: int = 1                   # 优先级
    daily_used: int = 0                 # 当日使用次数
    daily_limit: int = 100              # 每日限额
    total_used: int = 0                 # 累计使用次数
    consecutive_errors: int = 0         # 连续错误次数
    total_errors: int = 0               # 累计错误次数
    last_used_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    cooling_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    record_id: Optional[str] = None     # 飞书记录 ID

    def get_decrypted_value(self) -> str:
        """获取解密后的 Cookie 值"""
        if not self.encrypted_value or not self.encryption_key_id:
            raise ValueError("Cookie 未加密或加密信息不完整")
        return cookie_encryption.decrypt(self.encrypted_value, self.encryption_key_id)

    def is_available(self) -> bool:
        """检查 Cookie 是否可用"""
        if self.status != CookieStatus.ACTIVE:
            return False
        if self.daily_used >= self.daily_limit:
            return False
        return True

    def is_cooling_expired(self) -> bool:
        """检查冷却是否结束"""
        if self.status != CookieStatus.COOLING:
            return False
        if not self.cooling_until:
            return True
        return datetime.utcnow() > self.cooling_until


class CookieManager:
    """
    Cookie 管理器

    提供 Cookie 的增删改查和状态管理功能。
    支持本地存储和飞书存储两种模式。
    """

    # 冷却配置
    COOLING_DURATION_MINUTES = 30       # 冷却时长
    MAX_CONSECUTIVE_ERRORS = 3          # 触发冷却的连续错误数
    MAX_TOTAL_ERRORS = 10               # 触发失效的累计错误数

    def __init__(self, storage_type: str = "memory"):
        """
        初始化 Cookie 管理器

        Args:
            storage_type: 存储类型 (memory/feishu)
        """
        self.storage_type = storage_type
        self._cookies: Dict[str, Cookie] = {}
        self._lock = asyncio.Lock()

    async def add(
        self,
        name: str,
        cookie_value: str,
        platform: str = "xhs",
        priority: int = 1,
        daily_limit: int = 100
    ) -> Cookie:
        """
        添加新 Cookie

        Args:
            name: Cookie 名称
            cookie_value: Cookie 值 (明文，将被加密)
            platform: 平台
            priority: 优先级
            daily_limit: 每日限额

        Returns:
            创建的 Cookie 对象
        """
        async with self._lock:
            # 检查重复
            if name in self._cookies:
                raise ValueError(f"Cookie {name} 已存在")

            # 加密
            encrypted, key_id = cookie_encryption.encrypt(cookie_value)

            # 创建
            cookie = Cookie(
                name=name,
                platform=platform,
                encrypted_value=encrypted,
                encryption_key_id=key_id,
                priority=priority,
                daily_limit=daily_limit
            )

            self._cookies[name] = cookie
            logger.info(f"添加 Cookie: {name}, platform={platform}")

            return cookie

    async def acquire(
        self,
        platform: str = "xhs",
        cookie_name: Optional[str] = None
    ) -> Optional[Cookie]:
        """
        获取可用的 Cookie

        Args:
            platform: 平台
            cookie_name: 指定 Cookie 名称

        Returns:
            可用的 Cookie，无可用时返回 None
        """
        async with self._lock:
            # 先检查并恢复冷却结束的 Cookie
            await self._check_cooling_recovery()

            if cookie_name:
                # 指定了 Cookie 名称
                cookie = self._cookies.get(cookie_name)
                if cookie and cookie.is_available() and cookie.platform == platform:
                    return cookie
                return None

            # 按优先级和使用次数排序，选择最优的
            candidates = [
                c for c in self._cookies.values()
                if c.platform == platform and c.is_available()
            ]

            if not candidates:
                logger.warning(f"无可用 Cookie: platform={platform}")
                return None

            # 排序：优先级高 > 使用次数少
            candidates.sort(key=lambda c: (-c.priority, c.daily_used))

            return candidates[0]

    async def mark_used(
        self,
        name: str,
        success_count: int = 1,
        error_count: int = 0
    ) -> None:
        """
        标记 Cookie 已使用

        Args:
            name: Cookie 名称
            success_count: 成功次数
            error_count: 失败次数
        """
        async with self._lock:
            cookie = self._cookies.get(name)
            if not cookie:
                return

            cookie.daily_used += success_count + error_count
            cookie.total_used += success_count + error_count
            cookie.last_used_at = datetime.utcnow()
            cookie.updated_at = datetime.utcnow()

            if error_count > 0:
                cookie.consecutive_errors += error_count
                cookie.total_errors += error_count
                cookie.last_error_at = datetime.utcnow()

                # 检查是否需要进入冷却
                if cookie.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    await self._start_cooling(cookie)

                # 检查是否需要标记失效
                if cookie.total_errors >= self.MAX_TOTAL_ERRORS:
                    cookie.status = CookieStatus.INVALID
                    logger.warning(f"Cookie 已失效: {name}")

            else:
                # 成功则重置连续错误计数
                cookie.consecutive_errors = 0

    async def _start_cooling(self, cookie: Cookie) -> None:
        """开始冷却"""
        cookie.status = CookieStatus.COOLING
        cookie.cooling_until = datetime.utcnow() + timedelta(
            minutes=self.COOLING_DURATION_MINUTES
        )
        logger.info(f"Cookie 进入冷却: {cookie.name}, until={cookie.cooling_until}")

    async def _check_cooling_recovery(self) -> None:
        """检查并恢复冷却结束的 Cookie"""
        for cookie in self._cookies.values():
            if cookie.is_cooling_expired():
                cookie.status = CookieStatus.ACTIVE
                cookie.cooling_until = None
                cookie.consecutive_errors = 0
                logger.info(f"Cookie 冷却结束: {cookie.name}")

    async def update_status(
        self,
        name: str,
        status: CookieStatus,
        reason: str = ""
    ) -> None:
        """
        更新 Cookie 状态

        Args:
            name: Cookie 名称
            status: 新状态
            reason: 原因说明
        """
        async with self._lock:
            cookie = self._cookies.get(name)
            if not cookie:
                return

            old_status = cookie.status
            cookie.status = status
            cookie.updated_at = datetime.utcnow()

            if status == CookieStatus.COOLING:
                cookie.cooling_until = datetime.utcnow() + timedelta(
                    minutes=self.COOLING_DURATION_MINUTES
                )

            logger.info(
                f"Cookie 状态更新: {name}, {old_status} -> {status}, reason={reason}"
            )

    async def get(self, name: str) -> Optional[Cookie]:
        """获取指定 Cookie"""
        return self._cookies.get(name)

    async def list(
        self,
        platform: Optional[str] = None,
        status: Optional[CookieStatus] = None
    ) -> List[Cookie]:
        """
        列出 Cookie

        Args:
            platform: 按平台过滤
            status: 按状态过滤
        """
        result = list(self._cookies.values())

        if platform:
            result = [c for c in result if c.platform == platform]

        if status:
            result = [c for c in result if c.status == status]

        return result

    async def delete(self, name: str) -> bool:
        """删除 Cookie"""
        async with self._lock:
            if name in self._cookies:
                del self._cookies[name]
                logger.info(f"删除 Cookie: {name}")
                return True
            return False

    async def get_stats(self, platform: str = "xhs") -> Dict[str, Any]:
        """
        获取 Cookie 统计信息

        Args:
            platform: 平台

        Returns:
            统计信息
        """
        cookies = await self.list(platform=platform)

        active_count = sum(1 for c in cookies if c.status == CookieStatus.ACTIVE)
        cooling_count = sum(1 for c in cookies if c.status == CookieStatus.COOLING)
        invalid_count = sum(1 for c in cookies if c.status == CookieStatus.INVALID)
        banned_count = sum(1 for c in cookies if c.status == CookieStatus.BANNED)

        total_daily_used = sum(c.daily_used for c in cookies)
        total_daily_limit = sum(c.daily_limit for c in cookies)

        return {
            "platform": platform,
            "total_count": len(cookies),
            "active_count": active_count,
            "cooling_count": cooling_count,
            "invalid_count": invalid_count,
            "banned_count": banned_count,
            "daily_usage_rate": (
                total_daily_used / total_daily_limit if total_daily_limit > 0 else 0
            )
        }

    async def reset_daily_stats(self) -> None:
        """重置每日统计 (每天 0 点调用)"""
        async with self._lock:
            for cookie in self._cookies.values():
                cookie.daily_used = 0


# ============ 依赖注入 ============

_cookie_manager: Optional[CookieManager] = None


def get_cookie_manager() -> CookieManager:
    """获取 Cookie 管理器实例 (单例)"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
    return _cookie_manager


def reset_cookie_manager() -> None:
    """重置 Cookie 管理器 (用于测试)"""
    global _cookie_manager
    _cookie_manager = None
