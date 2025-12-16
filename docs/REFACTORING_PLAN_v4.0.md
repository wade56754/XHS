# MediaCrawler v4.0 重构计划

> 版本: v4.0
> 创建日期: 2025-12-16
> 目标: 基于开源项目借鉴和现有问题分析，系统性重构项目架构

---

## 一、重构背景

### 1.1 现有问题汇总

| 类别 | 问题 | 严重性 | 来源 |
|------|------|--------|------|
| **工作流** | HTTP方法错误 (PATCH→PUT) | P0 | 审查报告 |
| **工作流** | MediaCrawler API URL不可用 | P0 | 审查报告 |
| **架构** | 无IP代理池支持 | P0 | 借鉴分析 |
| **架构** | 无CDP浏览器模式 | P1 | 借鉴分析 |
| **功能** | 缺少创作者爬取 | P1 | 借鉴分析 |
| **功能** | 缺少媒体下载 | P1 | 借鉴分析 |
| **功能** | 无断点续爬 | P1 | 借鉴分析 |
| **代码** | 无统一重试机制 | P2 | 借鉴分析 |
| **架构** | 存储层未抽象 | P2 | 借鉴分析 |

### 1.2 重构目标

```
┌─────────────────────────────────────────────────────────────────┐
│                        v4.0 重构目标                             │
├─────────────────────────────────────────────────────────────────┤
│  1. 修复所有 P0 问题，确保工作流正常运行                          │
│  2. 新增 IP 代理池，提升反爬能力                                  │
│  3. 支持 CDP 模式，连接真实浏览器                                 │
│  4. 新增创作者爬取 API                                           │
│  5. 支持媒体文件下载和存储                                        │
│  6. 抽象存储层，支持多种后端                                      │
│  7. 统一重试和限流机制                                           │
│  8. 完善单元测试覆盖                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、新架构设计

### 2.1 整体架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                           n8n 工作流层                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Discovery │ │Extraction│ │Generation│ │ Publish  │ │  Cookie  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
└───────┼────────────┼────────────┼────────────┼────────────┼─────────┘
        │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        FastAPI 网关层                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Middleware: Auth / RateLimit / RequestID / Logging / ErrorHandle│ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐   │
│  │/search  │ │/note    │ │/creator │ │/cookie  │ │/media       │   │
│  │         │ │/detail  │ │/{id}    │ │/manage  │ │/download    │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └──────┬──────┘   │
└───────┼────────────┼────────────┼────────────┼───────────┼──────────┘
        │            │            │            │           │
        ▼            ▼            ▼            ▼           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         服务层 (Services)                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐   │
│  │ Crawler    │ │ Cookie     │ │ Media      │ │ Creator        │   │
│  │ Service    │ │ Manager    │ │ Downloader │ │ Service        │   │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └───────┬────────┘   │
│        │              │              │                │             │
│  ┌─────┴──────────────┴──────────────┴────────────────┴───────────┐ │
│  │                    公共服务层                                    │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │ │
│  │  │ProxyPool │ │RateLimiter│ │RetryMgr  │ │BrowserManager    │  │ │
│  │  │          │ │          │ │(tenacity)│ │(Playwright/CDP)  │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
        │              │              │                │
        ▼              ▼              ▼                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         存储层 (Store)                                │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   AbstractStore (接口)                          │ │
│  │  save_note() / save_cookie() / get_progress() / save_media()  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                 │
│         ▼                    ▼                    ▼                 │
│  ┌────────────┐      ┌────────────┐      ┌────────────────┐        │
│  │FeishuStore │      │SQLiteStore │      │ MinioStore     │        │
│  │(生产)       │      │(开发/测试)  │      │(媒体文件)       │        │
│  └────────────┘      └────────────┘      └────────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 新增目录结构

```
mediacrawler-api/
├── media_crawler_api/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 入口
│   │
│   ├── models/                     # 数据模型
│   │   ├── request.py              # 请求模型
│   │   ├── response.py             # 响应模型
│   │   └── domain.py               # 领域模型 (新增)
│   │
│   ├── routers/                    # API 路由
│   │   ├── crawler.py              # 搜索/详情 API
│   │   ├── creator.py              # 创作者 API (新增)
│   │   ├── media.py                # 媒体下载 API (新增)
│   │   ├── cookie.py               # Cookie 管理 API
│   │   └── health.py               # 健康检查
│   │
│   ├── services/                   # 业务服务
│   │   ├── crawler.py              # 爬虫核心服务
│   │   ├── cookie.py               # Cookie 管理
│   │   ├── creator.py              # 创作者服务 (新增)
│   │   ├── media.py                # 媒体下载服务 (新增)
│   │   └── progress.py             # 进度追踪服务 (新增)
│   │
│   ├── platforms/                  # 平台抽象层 (新增)
│   │   ├── __init__.py
│   │   ├── base.py                 # 抽象基类
│   │   ├── xhs.py                  # 小红书实现
│   │   └── douyin.py               # 抖音预留
│   │
│   ├── store/                      # 存储层 (新增)
│   │   ├── __init__.py
│   │   ├── abstract.py             # 抽象接口
│   │   ├── feishu.py               # 飞书实现
│   │   ├── sqlite.py               # SQLite实现
│   │   └── minio.py                # MinIO/OSS实现
│   │
│   ├── infra/                      # 基础设施 (新增)
│   │   ├── __init__.py
│   │   ├── proxy.py                # IP代理池
│   │   ├── browser.py              # 浏览器管理 (Playwright/CDP)
│   │   ├── rate_limiter.py         # 限流器
│   │   └── retry.py                # 重试机制
│   │
│   ├── utils/                      # 工具
│   │   ├── crypto.py               # 加密
│   │   ├── logging.py              # 日志脱敏
│   │   └── alerting.py             # 告警
│   │
│   └── config/                     # 配置 (新增)
│       ├── __init__.py
│       └── settings.py             # 统一配置管理
│
├── tests/                          # 测试 (补充)
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│   └── security_audit.py
│
└── docs/
    └── API.md
```

---

## 三、Phase 1: 紧急修复 (Day 1)

### 3.1 修复工作流 HTTP 方法

**问题**: 飞书 API 不支持 PATCH 方法

**影响**: 全部5个工作流的锁定/更新节点

**修复方案**:

```javascript
// 所有飞书表更新节点
// 错误
method: "PATCH"

// 正确
method: "PUT"
```

**需修改的节点列表**:

| 工作流 | 节点名称 |
|--------|---------|
| WF-Discovery | Acquire Lock, Release Lock |
| WF-Extraction | Lock Candidate, Mark Candidate Done, Update Failed Candidate |
| WF-Generation | Lock Source, Mark Source Done, Update Source Failed |
| WF-Publish | Lock Content, Mark Published, Mark Failed |
| WF-CookieManager | Batch Updates, Update Cookie, Rollback Stuck |

### 3.2 修复 MediaCrawler API URL

**问题**: `https://media.primetat.com` 端口443未开放

**修复方案**: 使用环境变量

```javascript
// 错误
url: "https://media.primetat.com/api/search"

// 正确
url: "{{ $env.MEDIACRAWLER_API_URL }}/api/search"
```

**环境变量已配置**:
```
MEDIACRAWLER_API_URL=http://124.221.251.8:8080
```

---

## 四、Phase 2: 核心能力增强 (Day 2-4)

### 4.1 IP 代理池

**文件**: `media_crawler_api/infra/proxy.py`

```python
"""
IP代理池管理

功能:
- 支持多个代理提供商
- 自动验证代理可用性
- 代理失效自动切换
- 代理使用统计
"""

import asyncio
import random
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import httpx

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ProxyProvider(str, Enum):
    """代理提供商"""
    KUAIDAILI = "kuaidaili"
    CUSTOM = "custom"
    NONE = "none"


@dataclass
class ProxyInfo:
    """代理信息"""
    url: str                              # 代理URL (http://ip:port)
    provider: ProxyProvider               # 来源
    expire_at: Optional[datetime] = None  # 过期时间
    success_count: int = 0                # 成功次数
    fail_count: int = 0                   # 失败次数
    last_used_at: Optional[datetime] = None


class ProxyPool:
    """IP代理池"""

    def __init__(
        self,
        provider: ProxyProvider = ProxyProvider.CUSTOM,
        pool_size: int = 5,
        validation_url: str = "http://httpbin.org/ip",
        refresh_interval: int = 300
    ):
        self.provider = provider
        self.pool_size = pool_size
        self.validation_url = validation_url
        self.refresh_interval = timedelta(seconds=refresh_interval)

        self._proxies: List[ProxyInfo] = []
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._last_refresh: Optional[datetime] = None

    async def initialize(self, proxy_list: Optional[List[str]] = None):
        """初始化代理池"""
        if proxy_list:
            self._proxies = [
                ProxyInfo(url=p, provider=ProxyProvider.CUSTOM)
                for p in proxy_list
            ]
        elif self.provider == ProxyProvider.KUAIDAILI:
            await self._fetch_from_kuaidaili()

        self._last_refresh = datetime.now()
        logger.info(f"代理池初始化完成, 共 {len(self._proxies)} 个代理")

    async def get_proxy(self) -> Optional[str]:
        """获取可用代理"""
        async with self._lock:
            if not self._proxies:
                return None

            # 检查是否需要刷新
            if self._should_refresh():
                await self._refresh()

            # 轮询获取
            for _ in range(len(self._proxies)):
                proxy = self._proxies[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._proxies)

                # 检查过期
                if proxy.expire_at and proxy.expire_at < datetime.now():
                    continue

                # 验证可用性
                if await self._validate(proxy.url):
                    proxy.last_used_at = datetime.now()
                    return proxy.url

            return None

    async def mark_success(self, proxy_url: str):
        """标记代理成功"""
        for p in self._proxies:
            if p.url == proxy_url:
                p.success_count += 1
                break

    async def mark_failed(self, proxy_url: str):
        """标记代理失败"""
        async with self._lock:
            for i, p in enumerate(self._proxies):
                if p.url == proxy_url:
                    p.fail_count += 1
                    # 连续失败3次移除
                    if p.fail_count >= 3:
                        self._proxies.pop(i)
                        logger.warning(f"代理已移除: {proxy_url}")
                    break

    async def _validate(self, proxy_url: str) -> bool:
        """验证代理可用性"""
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=5
            ) as client:
                resp = await client.get(self.validation_url)
                return resp.status_code == 200
        except Exception as e:
            logger.debug(f"代理验证失败: {proxy_url}, {e}")
            return False

    def _should_refresh(self) -> bool:
        """检查是否需要刷新"""
        if not self._last_refresh:
            return True
        return datetime.now() - self._last_refresh > self.refresh_interval

    async def _refresh(self):
        """刷新代理池"""
        if self.provider == ProxyProvider.KUAIDAILI:
            await self._fetch_from_kuaidaili()
        self._last_refresh = datetime.now()

    async def _fetch_from_kuaidaili(self):
        """从快代理获取代理"""
        # TODO: 实现快代理API集成
        pass


# 单例
_proxy_pool: Optional[ProxyPool] = None


def get_proxy_pool() -> ProxyPool:
    """获取代理池单例"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool()
    return _proxy_pool
```

### 4.2 CDP 浏览器模式

**文件**: `media_crawler_api/infra/browser.py`

```python
"""
浏览器管理

支持两种模式:
1. Playwright Headless - 标准自动化
2. CDP Mode - 连接真实Chrome浏览器，更好的反检测
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio

from ..utils.logging import get_logger

logger = get_logger(__name__)


class BrowserMode(str, Enum):
    """浏览器模式"""
    HEADLESS = "headless"    # Playwright无头模式
    HEADED = "headed"        # Playwright有头模式
    CDP = "cdp"              # Chrome DevTools Protocol


class AbstractBrowserManager(ABC):
    """浏览器管理器抽象基类"""

    @abstractmethod
    async def start(self) -> None:
        """启动浏览器"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止浏览器"""
        pass

    @abstractmethod
    async def new_context(
        self,
        storage_state: Optional[Dict] = None
    ) -> BrowserContext:
        """创建新的浏览器上下文"""
        pass

    @abstractmethod
    async def new_page(self, context: BrowserContext) -> Page:
        """创建新页面"""
        pass


class PlaywrightManager(AbstractBrowserManager):
    """Playwright 浏览器管理"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]
        )
        logger.info(f"Playwright浏览器已启动, headless={self.headless}")

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Playwright浏览器已关闭")

    async def new_context(
        self,
        storage_state: Optional[Dict] = None
    ) -> BrowserContext:
        return await self._browser.new_context(
            storage_state=storage_state,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
            viewport={"width": 1920, "height": 1080}
        )

    async def new_page(self, context: BrowserContext) -> Page:
        return await context.new_page()


class CDPManager(AbstractBrowserManager):
    """Chrome DevTools Protocol 管理"""

    def __init__(self, endpoint: str = "http://localhost:9222"):
        self.endpoint = endpoint
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(
            self.endpoint
        )
        logger.info(f"CDP浏览器已连接: {self.endpoint}")

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("CDP浏览器已断开")

    async def new_context(
        self,
        storage_state: Optional[Dict] = None
    ) -> BrowserContext:
        # CDP模式使用现有上下文
        contexts = self._browser.contexts
        if contexts:
            return contexts[0]
        return await self._browser.new_context(storage_state=storage_state)

    async def new_page(self, context: BrowserContext) -> Page:
        return await context.new_page()


def create_browser_manager(
    mode: BrowserMode,
    **kwargs
) -> AbstractBrowserManager:
    """工厂函数"""
    if mode == BrowserMode.CDP:
        return CDPManager(endpoint=kwargs.get("cdp_endpoint", "http://localhost:9222"))
    elif mode == BrowserMode.HEADED:
        return PlaywrightManager(headless=False)
    else:
        return PlaywrightManager(headless=True)
```

### 4.3 统一重试机制

**文件**: `media_crawler_api/infra/retry.py`

```python
"""
统一重试机制

基于 tenacity 库实现指数退避重试
"""

from functools import wraps
from typing import Type, Tuple, Callable, Any
import asyncio

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)

from ..utils.logging import get_logger

logger = get_logger(__name__)


# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 2,
    max_wait: float = 30,
    exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS
):
    """
    重试装饰器

    Args:
        max_attempts: 最大重试次数
        min_wait: 最小等待时间(秒)
        max_wait: 最大等待时间(秒)
        exceptions: 可重试的异常类型

    Example:
        @with_retry(max_attempts=3)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, log_level=30),  # WARNING
            reraise=True
        )
        async def wrapper(*args, **kwargs) -> Any:
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RetryConfig:
    """重试配置"""

    # 搜索接口
    SEARCH = {
        "max_attempts": 3,
        "min_wait": 2,
        "max_wait": 15
    }

    # 详情接口
    DETAIL = {
        "max_attempts": 2,
        "min_wait": 1,
        "max_wait": 10
    }

    # 创作者接口
    CREATOR = {
        "max_attempts": 3,
        "min_wait": 3,
        "max_wait": 30
    }
```

### 4.4 限流器

**文件**: `media_crawler_api/infra/rate_limiter.py`

```python
"""
请求限流器

功能:
- 平台级别并发控制
- 请求间隔控制
- 滑动窗口限流
"""

import asyncio
from typing import Dict
from collections import defaultdict
from datetime import datetime, timedelta
import random

from ..utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """请求限流器"""

    # 平台配置
    PLATFORM_CONFIG = {
        "xhs": {
            "max_concurrency": 3,       # 最大并发
            "min_interval": 2.0,        # 最小请求间隔(秒)
            "max_interval": 5.0,        # 最大请求间隔(秒)
            "requests_per_minute": 20,  # 每分钟最大请求数
        },
        "douyin": {
            "max_concurrency": 5,
            "min_interval": 1.0,
            "max_interval": 3.0,
            "requests_per_minute": 30,
        }
    }

    def __init__(self):
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._last_request: Dict[str, datetime] = defaultdict(lambda: datetime.min)
        self._request_counts: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()

    def _get_config(self, platform: str) -> dict:
        return self.PLATFORM_CONFIG.get(platform, self.PLATFORM_CONFIG["xhs"])

    def _get_semaphore(self, platform: str) -> asyncio.Semaphore:
        if platform not in self._semaphores:
            config = self._get_config(platform)
            self._semaphores[platform] = asyncio.Semaphore(config["max_concurrency"])
        return self._semaphores[platform]

    async def acquire(self, platform: str = "xhs") -> None:
        """获取请求许可"""
        config = self._get_config(platform)
        semaphore = self._get_semaphore(platform)

        # 1. 获取并发锁
        await semaphore.acquire()

        # 2. 检查请求间隔
        async with self._lock:
            now = datetime.now()
            last = self._last_request[platform]
            elapsed = (now - last).total_seconds()

            # 随机延迟
            min_interval = config["min_interval"]
            max_interval = config["max_interval"]
            required_wait = random.uniform(min_interval, max_interval)

            if elapsed < required_wait:
                await asyncio.sleep(required_wait - elapsed)

            # 3. 检查速率限制
            self._cleanup_old_requests(platform)
            while len(self._request_counts[platform]) >= config["requests_per_minute"]:
                await asyncio.sleep(1)
                self._cleanup_old_requests(platform)

            # 4. 记录请求
            self._last_request[platform] = datetime.now()
            self._request_counts[platform].append(datetime.now())

    def release(self, platform: str = "xhs") -> None:
        """释放请求许可"""
        self._get_semaphore(platform).release()

    def _cleanup_old_requests(self, platform: str) -> None:
        """清理过期请求记录"""
        cutoff = datetime.now() - timedelta(minutes=1)
        self._request_counts[platform] = [
            t for t in self._request_counts[platform]
            if t > cutoff
        ]


# 上下文管理器
class RateLimitContext:
    """限流上下文管理器"""

    def __init__(self, limiter: RateLimiter, platform: str):
        self.limiter = limiter
        self.platform = platform

    async def __aenter__(self):
        await self.limiter.acquire(self.platform)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.limiter.release(self.platform)


# 单例
_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
```

---

## 五、Phase 3: 功能扩展 (Day 5-7)

### 5.1 创作者爬取 API

**文件**: `media_crawler_api/routers/creator.py`

```python
"""
创作者 API

端点:
- GET /api/creator/{user_id} - 获取创作者信息
- GET /api/creator/{user_id}/notes - 获取创作者笔记列表
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from ..services.creator import CreatorService, get_creator_service
from ..models.response import APIResponse
from ..models.request import CreatorRequest

router = APIRouter(prefix="/api/creator", tags=["Creator"])


@router.get("/{user_id}")
async def get_creator_info(
    user_id: str,
    service: CreatorService = Depends(get_creator_service)
) -> APIResponse:
    """获取创作者信息"""
    result = await service.get_creator_info(user_id)
    return APIResponse.success(data=result)


@router.get("/{user_id}/notes")
async def get_creator_notes(
    user_id: str,
    cursor: Optional[str] = None,
    limit: int = Query(default=20, le=50),
    service: CreatorService = Depends(get_creator_service)
) -> APIResponse:
    """获取创作者笔记列表"""
    result = await service.get_creator_notes(
        user_id=user_id,
        cursor=cursor,
        limit=limit
    )
    return APIResponse.success(data=result)
```

### 5.2 媒体下载 API

**文件**: `media_crawler_api/routers/media.py`

```python
"""
媒体下载 API

端点:
- POST /api/media/download - 批量下载媒体
- GET /api/media/{media_id} - 获取已下载媒体
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from typing import List

from ..services.media import MediaService, get_media_service
from ..models.response import APIResponse
from ..models.request import MediaDownloadRequest

router = APIRouter(prefix="/api/media", tags=["Media"])


@router.post("/download")
async def download_media(
    request: MediaDownloadRequest,
    background_tasks: BackgroundTasks,
    service: MediaService = Depends(get_media_service)
) -> APIResponse:
    """
    批量下载媒体文件

    支持:
    - 图片下载
    - 视频下载
    - 异步处理
    """
    task_id = await service.create_download_task(request.urls)
    background_tasks.add_task(service.process_download_task, task_id)

    return APIResponse.success(data={
        "task_id": task_id,
        "status": "processing",
        "total": len(request.urls)
    })


@router.get("/task/{task_id}")
async def get_download_status(
    task_id: str,
    service: MediaService = Depends(get_media_service)
) -> APIResponse:
    """获取下载任务状态"""
    result = await service.get_task_status(task_id)
    return APIResponse.success(data=result)
```

### 5.3 存储层抽象

**文件**: `media_crawler_api/store/abstract.py`

```python
"""
存储层抽象接口
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class NoteData:
    """笔记数据"""
    note_id: str
    title: str
    content: str
    author_id: str
    images: List[str]
    video_url: Optional[str]
    likes: int
    collects: int
    comments: int
    tags: List[str]
    created_at: str


@dataclass
class CookieData:
    """Cookie数据"""
    name: str
    platform: str
    encrypted_value: str
    status: str
    priority: int


class AbstractStore(ABC):
    """存储层抽象基类"""

    # ========== 笔记 ==========

    @abstractmethod
    async def save_note(self, note: NoteData) -> str:
        """保存笔记，返回记录ID"""
        pass

    @abstractmethod
    async def get_note(self, note_id: str) -> Optional[NoteData]:
        """获取笔记"""
        pass

    @abstractmethod
    async def note_exists(self, note_id: str) -> bool:
        """检查笔记是否存在"""
        pass

    # ========== Cookie ==========

    @abstractmethod
    async def save_cookie(self, cookie: CookieData) -> str:
        """保存Cookie"""
        pass

    @abstractmethod
    async def get_active_cookies(self, platform: str) -> List[CookieData]:
        """获取活跃Cookie列表"""
        pass

    @abstractmethod
    async def update_cookie_status(self, name: str, status: str) -> None:
        """更新Cookie状态"""
        pass

    # ========== 进度 ==========

    @abstractmethod
    async def save_progress(
        self,
        task_type: str,
        task_id: str,
        progress: Dict[str, Any]
    ) -> None:
        """保存任务进度"""
        pass

    @abstractmethod
    async def get_progress(
        self,
        task_type: str,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取任务进度"""
        pass
```

**文件**: `media_crawler_api/store/sqlite.py`

```python
"""
SQLite 存储实现 (用于开发和测试)
"""

import aiosqlite
from typing import Optional, List, Dict, Any
from pathlib import Path

from .abstract import AbstractStore, NoteData, CookieData


class SQLiteStore(AbstractStore):
    """SQLite存储实现"""

    def __init__(self, db_path: str = "data/mediacrawler.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def _get_conn(self):
        return await aiosqlite.connect(self.db_path)

    async def initialize(self):
        """初始化数据库表"""
        async with await self._get_conn() as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS notes (
                    note_id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    author_id TEXT,
                    images TEXT,
                    video_url TEXT,
                    likes INTEGER,
                    collects INTEGER,
                    comments INTEGER,
                    tags TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS cookies (
                    name TEXT PRIMARY KEY,
                    platform TEXT,
                    encrypted_value TEXT,
                    status TEXT,
                    priority INTEGER
                );

                CREATE TABLE IF NOT EXISTS progress (
                    task_type TEXT,
                    task_id TEXT,
                    progress TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (task_type, task_id)
                );
            """)
            await db.commit()

    async def save_note(self, note: NoteData) -> str:
        async with await self._get_conn() as db:
            await db.execute("""
                INSERT OR REPLACE INTO notes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                note.note_id, note.title, note.content, note.author_id,
                ",".join(note.images), note.video_url,
                note.likes, note.collects, note.comments,
                ",".join(note.tags), note.created_at
            ))
            await db.commit()
        return note.note_id

    async def get_note(self, note_id: str) -> Optional[NoteData]:
        async with await self._get_conn() as db:
            async with db.execute(
                "SELECT * FROM notes WHERE note_id = ?", (note_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return NoteData(
                        note_id=row[0],
                        title=row[1],
                        content=row[2],
                        author_id=row[3],
                        images=row[4].split(",") if row[4] else [],
                        video_url=row[5],
                        likes=row[6],
                        collects=row[7],
                        comments=row[8],
                        tags=row[9].split(",") if row[9] else [],
                        created_at=row[10]
                    )
        return None

    async def note_exists(self, note_id: str) -> bool:
        async with await self._get_conn() as db:
            async with db.execute(
                "SELECT 1 FROM notes WHERE note_id = ?", (note_id,)
            ) as cursor:
                return await cursor.fetchone() is not None

    # ... 其他方法实现
```

---

## 六、Phase 4: 测试与文档 (Day 8-10)

### 6.1 测试覆盖

```
tests/
├── unit/
│   ├── test_proxy_pool.py        # 代理池单元测试
│   ├── test_rate_limiter.py      # 限流器单元测试
│   ├── test_retry.py             # 重试机制测试
│   ├── test_cookie_manager.py    # Cookie管理测试
│   └── test_crypto.py            # 加密模块测试
│
├── integration/
│   ├── test_crawler_api.py       # 爬虫API集成测试
│   ├── test_creator_api.py       # 创作者API集成测试
│   ├── test_media_api.py         # 媒体API集成测试
│   └── test_store.py             # 存储层集成测试
│
└── e2e/
    └── test_full_workflow.py     # 端到端测试
```

### 6.2 测试示例

```python
# tests/unit/test_proxy_pool.py

import pytest
from unittest.mock import AsyncMock, patch
from media_crawler_api.infra.proxy import ProxyPool, ProxyProvider


@pytest.fixture
def proxy_pool():
    return ProxyPool(provider=ProxyProvider.CUSTOM)


@pytest.mark.asyncio
async def test_initialize_with_custom_proxies(proxy_pool):
    """测试自定义代理初始化"""
    proxies = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080"
    ]
    await proxy_pool.initialize(proxies)

    assert len(proxy_pool._proxies) == 2


@pytest.mark.asyncio
async def test_get_proxy_with_validation(proxy_pool):
    """测试获取代理并验证"""
    proxies = ["http://valid.proxy:8080"]
    await proxy_pool.initialize(proxies)

    with patch.object(proxy_pool, "_validate", return_value=True):
        proxy = await proxy_pool.get_proxy()
        assert proxy == "http://valid.proxy:8080"


@pytest.mark.asyncio
async def test_mark_failed_removes_proxy(proxy_pool):
    """测试失败代理移除"""
    await proxy_pool.initialize(["http://bad.proxy:8080"])

    # 标记3次失败
    for _ in range(3):
        await proxy_pool.mark_failed("http://bad.proxy:8080")

    assert len(proxy_pool._proxies) == 0
```

---

## 七、配置管理

### 7.1 统一配置

**文件**: `media_crawler_api/config/settings.py`

```python
"""
统一配置管理
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from enum import Enum


class Environment(str, Enum):
    DEV = "development"
    STAGING = "staging"
    PROD = "production"


class Settings(BaseSettings):
    """应用配置"""

    # 环境
    ENV: Environment = Environment.DEV
    DEBUG: bool = True

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    API_KEY: Optional[str] = None

    # 代理
    PROXY_ENABLED: bool = False
    PROXY_PROVIDER: str = "custom"
    PROXY_LIST: List[str] = []
    PROXY_POOL_SIZE: int = 5
    PROXY_REFRESH_INTERVAL: int = 300

    # 浏览器
    BROWSER_MODE: str = "headless"  # headless|headed|cdp
    CDP_ENDPOINT: str = "http://localhost:9222"

    # 限流
    RATE_LIMIT_ENABLED: bool = True
    XHS_MAX_CONCURRENCY: int = 3
    XHS_MIN_INTERVAL: float = 2.0
    XHS_MAX_INTERVAL: float = 5.0

    # 重试
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_MIN_WAIT: float = 2.0
    RETRY_MAX_WAIT: float = 30.0

    # 存储
    STORE_BACKEND: str = "feishu"  # feishu|sqlite|both
    SQLITE_PATH: str = "data/mediacrawler.db"

    # 飞书
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_APP_TOKEN: str = ""

    # 安全
    COOKIE_MASTER_KEY: str = ""
    LOG_LEVEL: str = "INFO"

    # 媒体
    MEDIA_STORAGE: str = "local"  # local|minio|oss
    MEDIA_LOCAL_PATH: str = "data/media"
    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "mediacrawler"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

### 7.2 环境变量模板

**文件**: `.env.example`

```bash
# ============ 环境 ============
ENV=development
DEBUG=true

# ============ API ============
API_HOST=0.0.0.0
API_PORT=8080
API_KEY=your-api-key

# ============ 代理 ============
PROXY_ENABLED=false
PROXY_PROVIDER=custom
PROXY_LIST=http://proxy1:8080,http://proxy2:8080
PROXY_POOL_SIZE=5
PROXY_REFRESH_INTERVAL=300

# ============ 浏览器 ============
BROWSER_MODE=headless
CDP_ENDPOINT=http://localhost:9222

# ============ 限流 ============
RATE_LIMIT_ENABLED=true
XHS_MAX_CONCURRENCY=3
XHS_MIN_INTERVAL=2.0
XHS_MAX_INTERVAL=5.0

# ============ 存储 ============
STORE_BACKEND=feishu
SQLITE_PATH=data/mediacrawler.db

# ============ 飞书 ============
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_APP_TOKEN=xxx

# ============ 安全 ============
COOKIE_MASTER_KEY=your-32-char-minimum-key
LOG_LEVEL=INFO

# ============ 媒体存储 ============
MEDIA_STORAGE=local
MEDIA_LOCAL_PATH=data/media
MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=mediacrawler
```

---

## 八、实施时间表

| Phase | 任务 | 预计时间 | 交付物 |
|-------|------|----------|--------|
| **Phase 1** | 紧急修复 | Day 1 | 工作流正常运行 |
| **Phase 2** | 核心能力增强 | Day 2-4 | 代理池、CDP、重试、限流 |
| **Phase 3** | 功能扩展 | Day 5-7 | 创作者API、媒体下载、存储抽象 |
| **Phase 4** | 测试文档 | Day 8-10 | 单元测试、集成测试、API文档 |

---

## 九、验收清单

### Phase 1 验收

- [ ] 所有工作流 HTTP 方法已修复 (PATCH → PUT)
- [ ] MediaCrawler API URL 使用环境变量
- [ ] WF-Discovery 可正常执行
- [ ] 飞书表记录可正常更新

### Phase 2 验收

- [ ] 代理池初始化正常
- [ ] 代理自动验证和切换
- [ ] CDP 模式可连接浏览器
- [ ] 重试机制按预期工作
- [ ] 限流器控制请求频率

### Phase 3 验收

- [ ] 创作者 API 返回正确数据
- [ ] 媒体下载任务正常处理
- [ ] SQLite 存储可用
- [ ] 飞书存储可用

### Phase 4 验收

- [ ] 单元测试覆盖率 > 70%
- [ ] 集成测试通过
- [ ] API 文档完整
- [ ] 部署文档完整

---

## 十、风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| CDP模式不稳定 | 中 | 中 | 保留Playwright模式作为备选 |
| 代理服务商不可用 | 低 | 高 | 支持多个代理提供商 |
| 飞书API限流 | 中 | 中 | 增加请求间隔，使用批量API |
| 测试覆盖不足 | 中 | 中 | 优先覆盖核心路径 |

---

> 文档版本: v4.0
> 创建时间: 2025-12-16
> 最后更新: 2025-12-16
