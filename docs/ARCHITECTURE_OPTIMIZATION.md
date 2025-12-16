# 系统架构优化方案

> 版本: v1.0
> 日期: 2025-12-16
> 基于: 架构深度分析报告 + MediaCrawler开源项目借鉴

---

## 一、当前架构问题总览

### 1.1 架构评分

| 维度 | 当前评分 | 目标评分 | 差距 |
|------|---------|---------|------|
| 架构清晰度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 层间耦合严重 |
| 可扩展性 | ⭐⭐ | ⭐⭐⭐⭐ | 新增功能需改多个文件 |
| 性能 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | HTTP/Cookie查询瓶颈 |
| 可测试性 | ⭐⭐ | ⭐⭐⭐⭐ | 缺乏接口抽象 |
| 安全性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 缺访问控制 |

### 1.2 核心问题清单

```
┌─────────────────────────────────────────────────────────────┐
│                    🔴 高优先级问题                           │
├─────────────────────────────────────────────────────────────┤
│ 1. Cookie获取 O(n) 复杂度 - 每次请求遍历所有Cookie          │
│ 2. HTTP Session 重复创建 - 无连接池复用                     │
│ 3. 批量请求串行处理 - 20条需300秒 vs 应该15秒               │
│ 4. 无IP代理池 - 容易被封禁                                  │
│ 5. 配置硬编码 - 修改需重新部署                              │
├─────────────────────────────────────────────────────────────┤
│                    🟡 中优先级问题                           │
├─────────────────────────────────────────────────────────────┤
│ 6. 异常处理重复 - 相同逻辑出现5+次                          │
│ 7. 路由层业务逻辑过重 - Cookie获取应在服务层                │
│ 8. 全局单例 - 多进程无法同步状态                            │
│ 9. 无访问控制 - API无认证                                   │
│ 10. 存储层未抽象 - 只有内存存储                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、目标架构设计

### 2.1 架构演进路线

```
当前架构 (v3.1)                    目标架构 (v4.0)
================                   ================

┌─────────────┐                   ┌─────────────────────────┐
│   Routers   │                   │      API Gateway        │
│  (业务混杂)  │                   │  Auth/RateLimit/Log    │
└──────┬──────┘                   └───────────┬─────────────┘
       │                                      │
       │                          ┌───────────▼─────────────┐
       │                          │      Middleware         │
       │                          │  Cookie/Retry/Circuit   │
       │                          └───────────┬─────────────┘
       │                                      │
┌──────▼──────┐                   ┌───────────▼─────────────┐
│  Services   │      ====>       │      Use Cases          │
│ (直接耦合)   │                   │  SearchUC/DetailUC/... │
└──────┬──────┘                   └───────────┬─────────────┘
       │                                      │
       │                          ┌───────────▼─────────────┐
       │                          │    Domain Services      │
       │                          │  Crawler/Cookie/Media   │
       │                          └───────────┬─────────────┘
       │                                      │
┌──────▼──────┐                   ┌───────────▼─────────────┐
│   Utils     │                   │    Infrastructure       │
│ (工具散落)   │                   │  Proxy/Browser/Store   │
└─────────────┘                   └─────────────────────────┘
```

### 2.2 六边形架构设计

```
                    ┌─────────────────────────────────────┐
                    │           Driving Adapters          │
                    │  ┌─────────┐ ┌─────────┐ ┌───────┐ │
                    │  │  HTTP   │ │  n8n    │ │  CLI  │ │
                    │  │  API    │ │ Webhook │ │       │ │
                    │  └────┬────┘ └────┬────┘ └───┬───┘ │
                    └───────┼───────────┼──────────┼─────┘
                            │           │          │
                    ┌───────▼───────────▼──────────▼─────┐
                    │              Ports                  │
                    │  ┌─────────────────────────────┐   │
                    │  │     Application Services     │   │
                    │  │  ┌───────┐ ┌───────┐ ┌────┐ │   │
                    │  │  │Search │ │Extract│ │...│ │   │
                    │  │  │  UC   │ │  UC   │ │   │ │   │
                    │  │  └───────┘ └───────┘ └────┘ │   │
                    │  └──────────────┬──────────────┘   │
                    │                 │                   │
                    │  ┌──────────────▼──────────────┐   │
                    │  │       Domain Core           │   │
                    │  │  ┌────────┐ ┌────────────┐  │   │
                    │  │  │Crawler │ │CookieManager│  │   │
                    │  │  │Service │ │            │  │   │
                    │  │  └────────┘ └────────────┘  │   │
                    │  └─────────────────────────────┘   │
                    │              Ports                  │
                    └───────┬───────────┬────────────────┘
                            │           │
                    ┌───────▼───────────▼────────────────┐
                    │          Driven Adapters            │
                    │  ┌─────────┐ ┌───────┐ ┌────────┐  │
                    │  │ Feishu  │ │ Redis │ │  XHS   │  │
                    │  │  Store  │ │ Cache │ │  API   │  │
                    │  └─────────┘ └───────┘ └────────┘  │
                    │  ┌─────────┐ ┌───────┐ ┌────────┐  │
                    │  │  Proxy  │ │Browser│ │  OSS   │  │
                    │  │  Pool   │ │Manager│ │ Store  │  │
                    │  └─────────┘ └───────┘ └────────┘  │
                    └────────────────────────────────────┘
```

---

## 三、分层优化详解

### 3.1 API网关层优化

**当前问题**: 无认证、无限流、日志分散

**优化方案**:

```python
# media_crawler_api/gateway/middleware.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time

class APIGateway(BaseHTTPMiddleware):
    """API网关中间件"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = self._generate_request_id()

        # 1. 认证检查
        if not await self._authenticate(request):
            raise HTTPException(status_code=401, detail="Unauthorized")

        # 2. 速率限制
        if not await self._check_rate_limit(request):
            raise HTTPException(status_code=429, detail="Too Many Requests")

        # 3. 设置请求上下文
        request.state.request_id = request_id
        request.state.start_time = start_time

        # 4. 执行请求
        response = await call_next(request)

        # 5. 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{(time.time() - start_time)*1000:.2f}ms"

        return response

    async def _authenticate(self, request: Request) -> bool:
        """API Key认证"""
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return request.url.path in ["/health", "/ready", "/live"]
        return api_key == settings.API_KEY

    async def _check_rate_limit(self, request: Request) -> bool:
        """速率限制检查"""
        client_ip = request.client.host
        return await rate_limiter.check(client_ip)
```

### 3.2 中间件层设计

**当前问题**: Cookie获取/异常处理逻辑散落在路由层

**优化方案**: 提取为独立中间件

```python
# media_crawler_api/middleware/cookie_middleware.py

from functools import wraps
from typing import Callable, Optional

class CookieMiddleware:
    """Cookie管理中间件"""

    def __init__(self, cookie_manager: CookieManager):
        self.cookie_manager = cookie_manager

    def with_cookie(self, platform: str = "xhs"):
        """装饰器: 自动管理Cookie获取和标记"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 1. 获取Cookie
                cookie = await self.cookie_manager.acquire(platform)
                if not cookie:
                    raise CookieExhaustedException()

                try:
                    # 2. 注入Cookie到kwargs
                    kwargs['cookie'] = cookie

                    # 3. 执行业务逻辑
                    result = await func(*args, **kwargs)

                    # 4. 标记成功
                    await self.cookie_manager.mark_used(
                        cookie.name,
                        success_count=1
                    )
                    return result

                except Exception as e:
                    # 5. 标记失败
                    await self.cookie_manager.mark_used(
                        cookie.name,
                        error_count=1
                    )
                    raise

            return wrapper
        return decorator


# 使用方式
class SearchUseCase:
    def __init__(self, cookie_middleware: CookieMiddleware):
        self.cookie = cookie_middleware

    @cookie_middleware.with_cookie(platform="xhs")
    async def execute(self, keyword: str, cookie: Cookie = None):
        # Cookie自动注入，无需手动管理
        return await self.crawler.search(keyword, cookie)
```

### 3.3 异常处理统一化

**当前问题**: 相同异常处理逻辑重复5+次

**优化方案**:

```python
# media_crawler_api/middleware/error_handler.py

from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Dict, Type

class ErrorHandler:
    """统一异常处理器"""

    # 异常 -> 错误码映射
    EXCEPTION_MAPPING: Dict[Type[Exception], tuple] = {
        CookieExhaustedException: (ErrorCode.COOKIE_EXHAUSTED, 503),
        CookieInvalidException: (ErrorCode.COOKIE_INVALID, 401),
        TimeoutError: (ErrorCode.TIMEOUT_ERROR, 504),
        PlatformException: (ErrorCode.PLATFORM_ERROR, 502),
        ValidationError: (ErrorCode.INVALID_INPUT, 400),
    }

    async def __call__(self, request: Request, exc: Exception) -> JSONResponse:
        error_code, status_code = self._map_exception(exc)

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code.value,
                    "message": self._safe_message(exc),
                    "retryable": error_code in RETRYABLE_ERRORS
                },
                "meta": {
                    "request_id": getattr(request.state, 'request_id', None),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

    def _map_exception(self, exc: Exception) -> tuple:
        for exc_type, mapping in self.EXCEPTION_MAPPING.items():
            if isinstance(exc, exc_type):
                return mapping
        return (ErrorCode.INTERNAL_ERROR, 500)

    def _safe_message(self, exc: Exception) -> str:
        """安全的错误消息（不暴露内部细节）"""
        if settings.DEBUG:
            return str(exc)
        return "An error occurred"


# 注册到FastAPI
app.add_exception_handler(Exception, ErrorHandler())
```

---

## 四、性能优化方案

### 4.1 Cookie查询优化: O(n) → O(1)

**当前问题**:
```python
# 每次请求都遍历所有Cookie
candidates = [c for c in self._cookies.values() if c.is_available()]
candidates.sort(key=lambda c: (-c.priority, c.daily_used))
```

**优化方案**:

```python
# media_crawler_api/services/cookie_optimized.py

import heapq
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass(order=True)
class PrioritizedCookie:
    """优先级Cookie包装"""
    priority_key: tuple = field(compare=True)  # (-priority, daily_used)
    cookie: Cookie = field(compare=False)


class OptimizedCookieManager:
    """优化后的Cookie管理器"""

    def __init__(self):
        # 按平台分组的优先级堆
        self._heaps: Dict[str, List[PrioritizedCookie]] = defaultdict(list)
        # 按名称索引
        self._index: Dict[str, Cookie] = {}
        # 分平台锁
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, platform: str) -> Optional[Cookie]:
        """O(log n) 获取最优Cookie"""
        async with self._locks[platform]:
            heap = self._heaps[platform]

            while heap:
                # O(log n) 弹出最优
                item = heapq.heappop(heap)
                cookie = item.cookie

                # 检查是否可用
                if cookie.is_available():
                    # 更新使用计数后重新入堆
                    cookie.daily_used += 1
                    self._push(platform, cookie)
                    return cookie

            return None

    def _push(self, platform: str, cookie: Cookie):
        """入堆"""
        item = PrioritizedCookie(
            priority_key=(-cookie.priority, cookie.daily_used),
            cookie=cookie
        )
        heapq.heappush(self._heaps[platform], item)

    async def add(self, cookie: Cookie):
        """添加Cookie"""
        self._index[cookie.name] = cookie
        self._push(cookie.platform, cookie)
```

**性能对比**:

| 操作 | 优化前 | 优化后 |
|------|--------|--------|
| 获取Cookie | O(n) + O(n log n) | O(log n) |
| 1000个Cookie | ~10ms | ~0.1ms |

### 4.2 HTTP连接池复用

**当前问题**:
```python
# 每次请求创建新Session
async with aiohttp.ClientSession() as session:
    ...
```

**优化方案**:

```python
# media_crawler_api/infra/http_client.py

import aiohttp
from contextlib import asynccontextmanager
from typing import Optional

class HTTPClientPool:
    """HTTP连接池管理"""

    def __init__(
        self,
        pool_size: int = 100,
        timeout: int = 30,
        keepalive_timeout: int = 60
    ):
        self.pool_size = pool_size
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.keepalive_timeout = keepalive_timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """获取共享Session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.pool_size,
                keepalive_timeout=self.keepalive_timeout,
                enable_cleanup_closed=True
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout
            )
        return self._session

    async def close(self):
        """关闭连接池"""
        if self._session:
            await self._session.close()
            self._session = None

    @asynccontextmanager
    async def request(self, method: str, url: str, **kwargs):
        """请求上下文管理器"""
        session = await self.get_session()
        async with session.request(method, url, **kwargs) as response:
            yield response


# 集成到CrawlerService
class CrawlerService:
    def __init__(self, http_client: HTTPClientPool):
        self.http = http_client

    async def search(self, ...):
        async with self.http.request(
            "POST",
            f"{self.base_url}/api/xhs/search",
            json={...},
            headers={...}
        ) as resp:
            return await resp.json()
```

**性能对比**:

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 连接建立 | 每次请求 | 复用 |
| SSL握手 | 每次请求 | 复用 |
| 延迟 | +100-300ms | 0ms |
| 并发10请求 | ~3s | ~0.3s |

### 4.3 批量请求并发化

**当前问题**:
```python
# 串行处理
for note_id in body.note_ids:
    detail = await crawler.get_note_detail(note_id)
```

**优化方案**:

```python
# media_crawler_api/services/batch_processor.py

import asyncio
from typing import List, TypeVar, Callable, Any

T = TypeVar('T')

class BatchProcessor:
    """批量请求并发处理器"""

    def __init__(
        self,
        max_concurrency: int = 5,
        timeout_per_item: float = 15.0
    ):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.timeout = timeout_per_item

    async def process(
        self,
        items: List[Any],
        handler: Callable,
        **kwargs
    ) -> List[dict]:
        """并发处理批量请求"""

        async def process_one(item) -> dict:
            async with self.semaphore:
                try:
                    result = await asyncio.wait_for(
                        handler(item, **kwargs),
                        timeout=self.timeout
                    )
                    return {"id": item, "success": True, "data": result}
                except asyncio.TimeoutError:
                    return {"id": item, "success": False, "error": "TIMEOUT"}
                except Exception as e:
                    return {"id": item, "success": False, "error": str(e)}

        tasks = [process_one(item) for item in items]
        return await asyncio.gather(*tasks)


# 使用方式
batch = BatchProcessor(max_concurrency=5)
results = await batch.process(
    items=note_ids,
    handler=crawler.get_note_detail
)
```

**性能对比**:

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 20条笔记 | 20 × 15s = 300s | 15s (并发5) |
| 提升 | - | **20倍** |

---

## 五、基础设施层优化

### 5.1 代理池架构

```
┌─────────────────────────────────────────────────────────┐
│                     ProxyPool                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   Provider  │    │   Provider  │    │   Provider  │ │
│  │  (快代理)    │    │  (自定义)    │    │  (芝麻)     │ │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘ │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            │                            │
│                    ┌───────▼───────┐                   │
│                    │  Proxy Queue  │                   │
│                    │  (优先级队列)  │                   │
│                    └───────┬───────┘                   │
│                            │                            │
│         ┌──────────────────┼──────────────────┐        │
│         │                  │                  │         │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌─────▼──────┐ │
│  │  Validator  │    │  Rotator    │    │  Monitor   │ │
│  │  (可用验证)  │    │  (轮换策略)  │    │  (健康监控) │ │
│  └─────────────┘    └─────────────┘    └────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 存储层抽象

```python
# media_crawler_api/store/interface.py

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class StorageInterface(ABC):
    """存储层接口"""

    # ========== Cookie 存储 ==========

    @abstractmethod
    async def get_cookie(self, name: str) -> Optional[Dict]: ...

    @abstractmethod
    async def save_cookie(self, cookie: Dict) -> str: ...

    @abstractmethod
    async def list_cookies(
        self,
        platform: str,
        status: str = "active"
    ) -> List[Dict]: ...

    @abstractmethod
    async def update_cookie(self, name: str, updates: Dict) -> bool: ...

    # ========== 笔记存储 ==========

    @abstractmethod
    async def save_note(self, note: Dict) -> str: ...

    @abstractmethod
    async def get_note(self, note_id: str) -> Optional[Dict]: ...

    @abstractmethod
    async def note_exists(self, note_id: str) -> bool: ...

    # ========== 进度存储 ==========

    @abstractmethod
    async def save_progress(self, key: str, progress: Dict) -> None: ...

    @abstractmethod
    async def get_progress(self, key: str) -> Optional[Dict]: ...


# 实现类
class FeishuStorage(StorageInterface):
    """飞书多维表格存储"""
    ...

class SQLiteStorage(StorageInterface):
    """SQLite本地存储"""
    ...

class RedisStorage(StorageInterface):
    """Redis缓存存储"""
    ...
```

### 5.3 配置管理优化

```python
# media_crawler_api/config/settings.py

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict, List, Optional

class Settings(BaseSettings):
    """应用配置 - 支持环境变量覆盖"""

    # ========== 应用配置 ==========
    APP_NAME: str = "MediaCrawler API"
    APP_VERSION: str = "4.0.0"
    DEBUG: bool = False
    ENV: str = "production"

    # ========== API配置 ==========
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    API_KEY: Optional[str] = None
    API_RATE_LIMIT: int = 100  # 每分钟

    # ========== 超时配置 ==========
    TIMEOUT_SEARCH: int = 30
    TIMEOUT_DETAIL: int = 15
    TIMEOUT_BATCH: int = 60
    TIMEOUT_COMMENTS: int = 15

    # ========== Cookie配置 ==========
    COOKIE_COOLING_MINUTES: int = 30
    COOKIE_MAX_CONSECUTIVE_ERRORS: int = 3
    COOKIE_MAX_TOTAL_ERRORS: int = 10
    COOKIE_DAILY_LIMIT: int = 100

    # ========== 代理配置 ==========
    PROXY_ENABLED: bool = False
    PROXY_PROVIDER: str = "custom"
    PROXY_LIST: List[str] = []
    PROXY_POOL_SIZE: int = 5
    PROXY_REFRESH_INTERVAL: int = 300

    # ========== 重试配置 ==========
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_MIN_WAIT: float = 2.0
    RETRY_MAX_WAIT: float = 30.0

    # ========== 并发配置 ==========
    BATCH_MAX_CONCURRENCY: int = 5
    HTTP_POOL_SIZE: int = 100
    HTTP_KEEPALIVE: int = 60

    # ========== 存储配置 ==========
    STORAGE_BACKEND: str = "feishu"  # feishu|sqlite|redis

    # ========== 安全配置 ==========
    COOKIE_MASTER_KEY: str = ""
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_prefix = "MC_"  # 环境变量前缀


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（缓存）"""
    return Settings()
```

---

## 六、新目录结构

```
mediacrawler-api/
├── media_crawler_api/
│   ├── __init__.py
│   ├── main.py                     # 应用入口
│   │
│   ├── gateway/                    # 🆕 API网关层
│   │   ├── __init__.py
│   │   ├── middleware.py           # 认证/限流/日志
│   │   └── rate_limiter.py         # 速率限制器
│   │
│   ├── middleware/                 # 🆕 业务中间件
│   │   ├── __init__.py
│   │   ├── cookie.py               # Cookie自动管理
│   │   ├── retry.py                # 重试策略
│   │   ├── circuit_breaker.py      # 断路器
│   │   └── error_handler.py        # 统一异常处理
│   │
│   ├── use_cases/                  # 🆕 用例层
│   │   ├── __init__.py
│   │   ├── search.py               # 搜索用例
│   │   ├── extract.py              # 详情提取用例
│   │   ├── creator.py              # 创作者用例
│   │   └── batch.py                # 批量处理用例
│   │
│   ├── domain/                     # 🆕 领域层
│   │   ├── __init__.py
│   │   ├── entities/               # 实体
│   │   │   ├── cookie.py
│   │   │   ├── note.py
│   │   │   └── creator.py
│   │   ├── services/               # 领域服务
│   │   │   ├── crawler.py
│   │   │   └── cookie_manager.py
│   │   └── exceptions.py           # 领域异常
│   │
│   ├── infra/                      # 🆕 基础设施层
│   │   ├── __init__.py
│   │   ├── http_client.py          # HTTP连接池
│   │   ├── proxy_pool.py           # 代理池
│   │   ├── browser_manager.py      # 浏览器管理
│   │   └── cache.py                # 缓存管理
│   │
│   ├── store/                      # 🆕 存储层
│   │   ├── __init__.py
│   │   ├── interface.py            # 存储接口
│   │   ├── feishu.py               # 飞书实现
│   │   ├── sqlite.py               # SQLite实现
│   │   └── redis.py                # Redis实现
│   │
│   ├── api/                        # 重构后的API层
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── search.py
│   │   │   ├── note.py
│   │   │   ├── creator.py
│   │   │   └── health.py
│   │   └── schemas/                # 请求/响应模型
│   │       ├── request.py
│   │       └── response.py
│   │
│   ├── config/                     # 🆕 配置管理
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   └── utils/                      # 工具层
│       ├── crypto.py
│       ├── logging.py
│       └── alerting.py
│
├── tests/                          # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/
```

---

## 七、依赖注入容器

```python
# media_crawler_api/container.py

from dependency_injector import containers, providers
from .config.settings import Settings
from .infra.http_client import HTTPClientPool
from .infra.proxy_pool import ProxyPool
from .domain.services.crawler import CrawlerService
from .domain.services.cookie_manager import CookieManager
from .store.feishu import FeishuStorage
from .store.sqlite import SQLiteStorage

class Container(containers.DeclarativeContainer):
    """依赖注入容器"""

    # 配置
    config = providers.Singleton(Settings)

    # 基础设施
    http_client = providers.Singleton(
        HTTPClientPool,
        pool_size=config.provided.HTTP_POOL_SIZE,
        timeout=config.provided.TIMEOUT_SEARCH
    )

    proxy_pool = providers.Singleton(
        ProxyPool,
        enabled=config.provided.PROXY_ENABLED,
        provider=config.provided.PROXY_PROVIDER
    )

    # 存储
    storage = providers.Selector(
        config.provided.STORAGE_BACKEND,
        feishu=providers.Singleton(FeishuStorage),
        sqlite=providers.Singleton(SQLiteStorage)
    )

    # 领域服务
    cookie_manager = providers.Singleton(
        CookieManager,
        storage=storage
    )

    crawler_service = providers.Singleton(
        CrawlerService,
        http_client=http_client,
        proxy_pool=proxy_pool
    )


# 使用
container = Container()
crawler = container.crawler_service()
```

---

## 八、实施优先级

### Phase 1: 基础优化 (Week 1)

| 任务 | 影响 | 复杂度 | 收益 |
|------|------|--------|------|
| 配置管理统一 | 全局 | 低 | 高 |
| HTTP连接池 | 性能 | 中 | 高 |
| 异常处理统一 | 代码质量 | 中 | 高 |
| Cookie查询优化 | 性能 | 中 | 高 |

### Phase 2: 架构重构 (Week 2-3)

| 任务 | 影响 | 复杂度 | 收益 |
|------|------|--------|------|
| 中间件层提取 | 架构 | 高 | 高 |
| 用例层设计 | 可扩展性 | 高 | 高 |
| 存储层抽象 | 灵活性 | 中 | 中 |
| 依赖注入 | 可测试性 | 中 | 高 |

### Phase 3: 功能增强 (Week 4)

| 任务 | 影响 | 复杂度 | 收益 |
|------|------|--------|------|
| 代理池实现 | 稳定性 | 高 | 高 |
| 批量并发处理 | 性能 | 中 | 高 |
| API认证 | 安全性 | 中 | 高 |
| 断路器模式 | 稳定性 | 中 | 中 |

---

## 九、预期收益

### 性能提升

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| Cookie获取 | 10ms | 0.1ms | **100x** |
| HTTP请求延迟 | +300ms | 0ms | **∞** |
| 批量20条请求 | 300s | 15s | **20x** |
| 并发能力 | 1 | 5+ | **5x** |

### 代码质量

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 代码重复率 | ~15% | <5% |
| 测试覆盖率 | 0% | >70% |
| 耦合度 | 高 | 低 |
| 新功能开发时间 | 长 | 短 |

### 运维能力

| 能力 | 优化前 | 优化后 |
|------|--------|--------|
| 配置修改 | 重新部署 | 环境变量 |
| 存储切换 | 改代码 | 配置切换 |
| 问题定位 | 困难 | request_id追踪 |
| 扩容 | 单进程 | 多实例 |

---

> 文档版本: v1.0
> 创建时间: 2025-12-16
