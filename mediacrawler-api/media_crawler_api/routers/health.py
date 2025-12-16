"""
健康检查路由

提供服务健康状态检查端点:
- /health: 详细健康检查 (用于监控)
- /ready: 就绪检查 (用于负载均衡)
- /live: 存活检查 (用于 Kubernetes)
"""

from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import Dict, Any
import psutil
import os

from ..services.cookie import CookieManager, get_cookie_manager
from ..utils.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)

# 服务启动时间
_start_time = datetime.utcnow()

# 请求统计 (简单内存计数器，生产环境建议使用 Prometheus)
_stats = {
    "total_requests": 0,
    "success_count": 0,
    "error_count": 0,
}


def increment_request_count(success: bool = True):
    """增加请求计数"""
    _stats["total_requests"] += 1
    if success:
        _stats["success_count"] += 1
    else:
        _stats["error_count"] += 1


def get_uptime_seconds() -> int:
    """获取服务运行时间 (秒)"""
    return int((datetime.utcnow() - _start_time).total_seconds())


def get_success_rate() -> float:
    """获取请求成功率"""
    total = _stats["total_requests"]
    if total == 0:
        return 1.0
    return _stats["success_count"] / total


async def check_cookie_store(cookie_mgr: CookieManager) -> Dict[str, Any]:
    """检查 Cookie 存储状态"""
    try:
        stats = await cookie_mgr.get_stats()
        if stats.get("active_count", 0) > 0:
            return {
                "status": "ok",
                "active_count": stats.get("active_count", 0),
                "total_count": stats.get("total_count", 0)
            }
        else:
            return {
                "status": "warning",
                "message": "无可用 Cookie",
                "active_count": 0
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def check_memory() -> Dict[str, Any]:
    """检查内存使用"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        # 获取系统内存
        system_memory = psutil.virtual_memory()

        status = "ok"
        if memory_mb > 1024:  # 超过 1GB
            status = "warning"
        if memory_mb > 2048:  # 超过 2GB
            status = "critical"

        return {
            "status": status,
            "process_mb": round(memory_mb, 2),
            "system_percent": system_memory.percent
        }
    except Exception as e:
        return {
            "status": "unknown",
            "message": str(e)
        }


def check_cpu() -> Dict[str, Any]:
    """检查 CPU 使用"""
    try:
        process = psutil.Process()
        cpu_percent = process.cpu_percent(interval=0.1)
        system_cpu = psutil.cpu_percent(interval=0.1)

        status = "ok"
        if system_cpu > 80:
            status = "warning"
        if system_cpu > 95:
            status = "critical"

        return {
            "status": status,
            "process_percent": round(cpu_percent, 2),
            "system_percent": round(system_cpu, 2)
        }
    except Exception as e:
        return {
            "status": "unknown",
            "message": str(e)
        }


@router.get("/health", summary="健康检查")
async def health_check(
    cookie_mgr: CookieManager = Depends(get_cookie_manager)
) -> Dict[str, Any]:
    """
    详细健康检查

    返回服务各组件的健康状态，用于监控系统。

    **检查项目:**
    - api: API 服务状态
    - cookie_store: Cookie 存储状态
    - memory: 内存使用情况
    - cpu: CPU 使用情况

    **状态说明:**
    - healthy: 所有组件正常
    - degraded: 部分组件异常，但服务可用
    - unhealthy: 服务不可用
    """
    checks = {
        "api": {"status": "ok"},
        "cookie_store": await check_cookie_store(cookie_mgr),
        "memory": check_memory(),
        "cpu": check_cpu(),
    }

    # 判断整体状态
    statuses = [c.get("status", "unknown") for c in checks.values()]

    if all(s == "ok" for s in statuses):
        overall_status = "healthy"
    elif "critical" in statuses or "error" in statuses:
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "uptime_seconds": get_uptime_seconds(),
        "metrics": {
            "total_requests": _stats["total_requests"],
            "success_rate": round(get_success_rate(), 4),
            "active_cookies": checks["cookie_store"].get("active_count", 0),
        },
        "version": os.environ.get("APP_VERSION", "3.1.0")
    }


@router.get("/ready", summary="就绪检查")
async def readiness_check(
    cookie_mgr: CookieManager = Depends(get_cookie_manager)
) -> Dict[str, Any]:
    """
    就绪检查

    用于负载均衡器判断服务是否可以接收流量。

    **返回:**
    - ready=true: 服务可以接收请求
    - ready=false: 服务暂时无法处理请求
    """
    try:
        stats = await cookie_mgr.get_stats()
        active_count = stats.get("active_count", 0)

        if active_count < 1:
            return {
                "ready": False,
                "reason": "no_active_cookies",
                "message": "无可用 Cookie，无法处理采集请求"
            }

        return {
            "ready": True,
            "active_cookies": active_count
        }
    except Exception as e:
        return {
            "ready": False,
            "reason": "check_failed",
            "message": str(e)
        }


@router.get("/live", summary="存活检查")
async def liveness_check() -> Dict[str, Any]:
    """
    存活检查

    用于 Kubernetes 等容器编排系统判断服务是否存活。
    只要服务能响应，就返回 200。
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": get_uptime_seconds()
    }


@router.get("/metrics", summary="获取指标")
async def get_metrics(
    cookie_mgr: CookieManager = Depends(get_cookie_manager)
) -> Dict[str, Any]:
    """
    获取服务指标

    返回用于监控和告警的关键指标。
    """
    cookie_stats = await cookie_mgr.get_stats()
    memory = check_memory()
    cpu = check_cpu()

    return {
        "timestamp": datetime.utcnow().isoformat(),

        # 请求指标
        "requests": {
            "total": _stats["total_requests"],
            "success": _stats["success_count"],
            "error": _stats["error_count"],
            "success_rate": round(get_success_rate(), 4)
        },

        # Cookie 指标
        "cookies": {
            "active": cookie_stats.get("active_count", 0),
            "cooling": cookie_stats.get("cooling_count", 0),
            "invalid": cookie_stats.get("invalid_count", 0),
            "total": cookie_stats.get("total_count", 0),
            "daily_usage_rate": cookie_stats.get("daily_usage_rate", 0)
        },

        # 资源指标
        "resources": {
            "memory_mb": memory.get("process_mb", 0),
            "memory_system_percent": memory.get("system_percent", 0),
            "cpu_process_percent": cpu.get("process_percent", 0),
            "cpu_system_percent": cpu.get("system_percent", 0)
        },

        # 运行时间
        "uptime_seconds": get_uptime_seconds()
    }
