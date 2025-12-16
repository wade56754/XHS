"""
路由模块
"""

from .crawler import router as crawler_router
from .health import router as health_router
from .cookie import router as cookie_router

__all__ = [
    "crawler_router",
    "health_router",
    "cookie_router",
]
