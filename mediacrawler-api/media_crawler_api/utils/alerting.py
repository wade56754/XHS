"""
告警模块

提供告警发送功能，支持:
- 飞书 Webhook 告警
- 告警冷却 (防止重复发送)
- 多级别告警 (P0/P1/P2)
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import os

from .logging import get_logger

logger = get_logger(__name__)


class AlertLevel(str, Enum):
    """告警级别"""
    P0 = "P0"  # 立即处理 (5分钟内)
    P1 = "P1"  # 1小时内处理
    P2 = "P2"  # 工作时间处理


# 告警冷却时间 (分钟)
COOLDOWN_MINUTES = {
    AlertLevel.P0: 5,
    AlertLevel.P1: 15,
    AlertLevel.P2: 60
}

# 告警冷却记录 {alert_key: cooldown_until}
_alert_cooldown: Dict[str, datetime] = {}

# 颜色映射
LEVEL_COLORS = {
    AlertLevel.P0: "red",
    AlertLevel.P1: "orange",
    AlertLevel.P2: "yellow"
}


def get_webhook_url() -> Optional[str]:
    """获取飞书 Webhook URL"""
    return os.environ.get("FEISHU_WEBHOOK_URL")


async def send_alert(
    name: str,
    level: AlertLevel,
    message: str,
    runbook: str,
    context: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None,
    skip_cooldown: bool = False
) -> bool:
    """
    发送告警到飞书

    Args:
        name: 告警名称
        level: 告警级别
        message: 告警消息
        runbook: 处理步骤
        context: 额外上下文信息
        webhook_url: Webhook URL (不指定则从环境变量读取)
        skip_cooldown: 是否跳过冷却检查

    Returns:
        是否发送成功
    """
    webhook = webhook_url or get_webhook_url()
    if not webhook:
        logger.warning("FEISHU_WEBHOOK_URL 未配置，跳过告警发送")
        return False

    # 检查冷却
    cooldown_key = f"{name}_{level.value}"
    if not skip_cooldown and cooldown_key in _alert_cooldown:
        cooldown_until = _alert_cooldown[cooldown_key]
        if datetime.now() < cooldown_until:
            logger.debug(f"告警 {name} 在冷却期内，跳过发送")
            return False

    # 构建飞书卡片消息
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"[{level.value}] {name}"
                },
                "template": LEVEL_COLORS[level]
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": message
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**处理步骤**\n```\n{runbook}\n```"
                    }
                }
            ]
        }
    }

    # 添加上下文信息
    if context:
        context_text = "\n".join(f"- {k}: {v}" for k, v in context.items())
        card["card"]["elements"].insert(1, {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**详细信息**\n{context_text}"
            }
        })

    # 添加时间戳
    card["card"]["elements"].append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        ]
    })

    # 发送请求
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook,
                json=card,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code") == 0 or result.get("StatusCode") == 0:
                        # 设置冷却
                        cooldown_minutes = COOLDOWN_MINUTES[level]
                        _alert_cooldown[cooldown_key] = datetime.now() + timedelta(minutes=cooldown_minutes)
                        logger.info(f"告警发送成功: {name}")
                        return True

                logger.error(f"告警发送失败: HTTP {resp.status}")
                return False

    except asyncio.TimeoutError:
        logger.error(f"告警发送超时: {name}")
        return False
    except Exception as e:
        logger.error(f"告警发送异常: {e}")
        return False


# ============ 预定义告警函数 ============

async def check_cookie_exhausted(
    cookie_stats: Dict[str, Any],
    webhook_url: Optional[str] = None
) -> bool:
    """
    检查并发送 Cookie 耗尽告警

    Args:
        cookie_stats: Cookie 统计信息
        webhook_url: Webhook URL

    Returns:
        是否发送了告警
    """
    active_count = cookie_stats.get("active_count", 0)
    if active_count >= 1:
        return False

    return await send_alert(
        name="COOKIE_EXHAUSTED",
        level=AlertLevel.P0,
        message=f"""**Cookie 耗尽告警**

平台: {cookie_stats.get('platform', 'xhs')}
当前可用: {active_count}
冷却中: {cookie_stats.get('cooling_count', 0)}
失效: {cookie_stats.get('invalid_count', 0)}
封禁: {cookie_stats.get('banned_count', 0)}""",
        runbook="""1. 检查飞书 tbl_cookie 表
2. 确认失效原因 (cooling/invalid/banned)
3. 如果是 cooling: 等待冷却结束
4. 如果是 invalid: 重新登录获取 Cookie
5. 如果是 banned: 更换账号
6. 验证新 Cookie 有效性
7. 手动触发 WF-Cookie管理 更新状态""",
        context=cookie_stats,
        webhook_url=webhook_url
    )


async def alert_api_success_rate_low(
    success_rate: float,
    failed_count: int,
    top_error_code: str,
    webhook_url: Optional[str] = None
) -> bool:
    """
    API 成功率下降告警

    Args:
        success_rate: 成功率 (0-1)
        failed_count: 失败数量
        top_error_code: 最多的错误码
    """
    if success_rate >= 0.9:
        return False

    return await send_alert(
        name="API_SUCCESS_RATE_LOW",
        level=AlertLevel.P1,
        message=f"""**API 成功率下降告警**

当前成功率: {success_rate * 100:.1f}%
最近失败数: {failed_count}
主要错误码: {top_error_code}""",
        runbook="""1. 检查错误码分布
2. 如果是 TIMEOUT_ERROR: 检查网络/平台状态
3. 如果是 COOKIE_*: 执行 Cookie 告警 Runbook
4. 如果是 PLATFORM_ERROR: 检查小红书是否有反爬策略更新
5. 查看 API 日志: docker logs mediacrawler-api --since 10m
6. 必要时暂停采集工作流""",
        context={
            "success_rate": f"{success_rate * 100:.1f}%",
            "failed_count": failed_count,
            "top_error_code": top_error_code
        },
        webhook_url=webhook_url
    )


async def alert_processing_backlog(
    pending_count: int,
    processing_count: int,
    completed_hourly: int,
    webhook_url: Optional[str] = None
) -> bool:
    """
    处理积压告警

    Args:
        pending_count: 待处理数
        processing_count: 处理中数
        completed_hourly: 每小时完成数
    """
    if pending_count <= 500:
        return False

    return await send_alert(
        name="PROCESSING_BACKLOG",
        level=AlertLevel.P2,
        message=f"""**处理积压告警**

待处理数: {pending_count}
处理中数: {processing_count}
最近1小时完成: {completed_hourly}""",
        runbook="""1. 检查采集工作流是否正常运行
2. 检查是否有执行锁超时
3. 如果工作流正常: 可能需要增加并发或 Cookie 数量
4. 如果有大量 processing: 执行锁回收任务
5. 考虑调整采集频率""",
        context={
            "pending_count": pending_count,
            "processing_count": processing_count,
            "completed_hourly": completed_hourly
        },
        webhook_url=webhook_url
    )


async def alert_lock_timeout_recovered(
    execution_recovered: int,
    record_recovered: int,
    webhook_url: Optional[str] = None
) -> bool:
    """
    锁超时回收告警

    当回收了异常数量的锁时发送告警
    """
    if execution_recovered == 0 and record_recovered <= 5:
        return False

    return await send_alert(
        name="LOCK_TIMEOUT_RECOVERED",
        level=AlertLevel.P1 if execution_recovered > 0 else AlertLevel.P2,
        message=f"""**锁超时回收告警**

执行锁回收: {execution_recovered} 个
记录锁回收: {record_recovered} 个

这可能表示工作流异常中断或处理超时。""",
        runbook="""1. 检查最近的工作流执行日志
2. 确认是否有网络或平台问题
3. 如果频繁出现，考虑:
   - 增加超时时间
   - 减少单次处理数量
   - 检查 Cookie 可用性""",
        context={
            "execution_recovered": execution_recovered,
            "record_recovered": record_recovered
        },
        webhook_url=webhook_url
    )


# ============ 告警管理 ============

def clear_cooldown(alert_name: Optional[str] = None):
    """
    清除告警冷却

    Args:
        alert_name: 告警名称，不指定则清除所有
    """
    global _alert_cooldown

    if alert_name:
        keys_to_remove = [k for k in _alert_cooldown if k.startswith(alert_name)]
        for k in keys_to_remove:
            del _alert_cooldown[k]
    else:
        _alert_cooldown.clear()


def get_cooldown_status() -> Dict[str, str]:
    """获取当前冷却状态"""
    now = datetime.now()
    return {
        k: v.strftime('%Y-%m-%d %H:%M:%S')
        for k, v in _alert_cooldown.items()
        if v > now
    }
