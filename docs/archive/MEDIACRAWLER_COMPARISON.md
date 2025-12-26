# MediaCrawler 开源项目借鉴分析

> 对比项目: https://github.com/NanmiCoder/MediaCrawler
> 分析日期: 2025-12-16

---

## 一、项目对比概览

| 特性 | NanmiCoder/MediaCrawler | 我们的项目 |
|------|-------------------------|------------|
| **定位** | 通用多平台爬虫CLI工具 | n8n集成的自动化采集API |
| **平台支持** | 7个平台（小红书、抖音、快手、B站、微博、贴吧、知乎） | 小红书专注 |
| **技术栈** | Playwright + Python CLI | FastAPI + n8n工作流 |
| **登录方式** | 二维码/手机/Cookie | Cookie导入 |
| **数据存储** | CSV/JSON/SQLite/MySQL | 飞书多维表格 |
| **运行模式** | 本地CLI执行 | Docker服务+定时调度 |

---

## 二、值得借鉴的核心技术点

### 2.1 浏览器自动化架构 ⭐⭐⭐⭐⭐

**开源项目实现:**
```python
# 使用Playwright保持登录态，通过JS表达式获取签名参数
# 避免逆向复杂加密算法

class XiaoHongShuCrawler(AbstractCrawler):
    async def start(self):
        # CDP模式：连接真实浏览器环境
        if self.use_cdp:
            self.cdp_manager = CDPBrowserManager()
            self.browser_context = await self.cdp_manager.connect()
        else:
            # 标准Playwright模式
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
```

**借鉴建议:**
- 我们的工作流已使用Playwright，但可以增加**CDP模式**支持
- CDP模式可以连接用户真实的Chrome浏览器，更好的反检测

```yaml
# 建议新增环境变量
PLAYWRIGHT_CDP_ENDPOINT=ws://localhost:9222  # Chrome DevTools协议端点
PLAYWRIGHT_MODE=cdp|headless|headed          # 运行模式
```

---

### 2.2 IP代理池管理 ⭐⭐⭐⭐⭐

**开源项目实现:**
```python
class ProxyIpPool:
    async def get_proxy(self) -> Optional[str]:
        """获取代理，支持有效性验证"""
        proxy = random.choice(self.proxies)
        if await self._is_valid_proxy(proxy):
            return proxy
        return await self.get_or_refresh_proxy()

    async def _is_valid_proxy(self, proxy: str) -> bool:
        """测试代理可用性"""
        try:
            async with httpx.AsyncClient(proxy=proxy) as client:
                resp = await client.get("http://httpbin.org/ip", timeout=5)
                return resp.status_code == 200
        except:
            return False
```

**借鉴建议:**
我们项目**完全没有代理支持**，这是一个重大缺失！

```python
# 建议新增: media_crawler_api/services/proxy.py

class ProxyPool:
    """代理IP池管理"""

    def __init__(self):
        self.providers = {
            "kuaidaili": KuaiDaiLiProvider(),
            "custom": CustomProxyProvider(),
        }
        self.current_proxy: Optional[str] = None
        self.proxy_expire_at: Optional[datetime] = None

    async def get_proxy(self) -> Optional[str]:
        """获取可用代理"""
        if self._is_expired():
            await self._refresh()
        return self.current_proxy

    async def mark_invalid(self, proxy: str):
        """标记代理失效"""
        if proxy == self.current_proxy:
            await self._refresh()
```

**配置项:**
```yaml
# 代理配置
PROXY_ENABLED: true
PROXY_PROVIDER: kuaidaili|custom
PROXY_POOL_SIZE: 5
PROXY_REFRESH_INTERVAL: 300  # 秒
PROXY_VALIDATION_URL: http://httpbin.org/ip
```

---

### 2.3 登录态持久化 ⭐⭐⭐⭐

**开源项目实现:**
```python
# 保存浏览器上下文（包含Cookie、LocalStorage等）
async def save_login_state(self, context: BrowserContext):
    state = await context.storage_state()
    with open("browser_state.json", "w") as f:
        json.dump(state, f)

# 恢复登录态
async def restore_login_state(self, browser: Browser):
    context = await browser.new_context(storage_state="browser_state.json")
    return context
```

**借鉴建议:**
我们当前只存Cookie字符串，可以扩展为完整的浏览器状态:

```python
# 建议扩展Cookie模型
class BrowserState:
    cookies: List[Dict]           # HTTP Cookies
    local_storage: Dict[str, str] # LocalStorage
    session_storage: Dict[str, str] # SessionStorage
    indexed_db: Optional[bytes]   # IndexedDB (可选)
```

---

### 2.4 多种数据存储适配 ⭐⭐⭐

**开源项目实现:**
```python
# 抽象存储接口
class AbstractStore(ABC):
    @abstractmethod
    async def store_content(self, content: Dict): pass

    @abstractmethod
    async def store_comment(self, comment: Dict): pass

# 多种实现
class CsvStore(AbstractStore): ...
class JsonStore(AbstractStore): ...
class SqliteStore(AbstractStore): ...
class MysqlStore(AbstractStore): ...
```

**借鉴建议:**
我们可以抽象存储层，便于未来扩展:

```python
# media_crawler_api/store/abstract.py
class AbstractStore(ABC):
    @abstractmethod
    async def save_note(self, note: NoteData) -> str: ...

    @abstractmethod
    async def save_cookie(self, cookie: Cookie) -> str: ...

# 实现
class FeishuStore(AbstractStore):
    """飞书多维表格存储"""

class LocalStore(AbstractStore):
    """本地SQLite存储（开发/测试用）"""
```

---

### 2.5 并发控制和限流 ⭐⭐⭐⭐

**开源项目实现:**
```python
# 使用Semaphore控制并发
semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY)

async def batch_get_note_comments(self, note_ids: List[str]):
    async def get_with_limit(note_id):
        async with semaphore:
            await asyncio.sleep(random.uniform(1, 3))  # 随机延迟
            return await self.get_comments(note_id)

    tasks = [get_with_limit(nid) for nid in note_ids]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

**借鉴建议:**
我们的工作流在n8n层面做了限流，但API层也应该有保护:

```python
# 建议新增: 请求限流器
from asyncio import Semaphore
from collections import defaultdict

class RateLimiter:
    def __init__(self):
        self.platform_semaphores = defaultdict(lambda: Semaphore(5))
        self.request_intervals = {"xhs": 2.0, "dy": 1.5}  # 平台间隔

    async def acquire(self, platform: str):
        await self.platform_semaphores[platform].acquire()
        await asyncio.sleep(self.request_intervals.get(platform, 1.0))

    def release(self, platform: str):
        self.platform_semaphores[platform].release()
```

---

### 2.6 错误重试机制 ⭐⭐⭐

**开源项目实现:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def get_note_detail(self, note_id: str):
    # 自动重试，指数退避
    ...
```

**借鉴建议:**
我们可以在服务层统一添加重试装饰器:

```python
# 建议新增到 crawler.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

def with_retry(max_attempts=3):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((TimeoutError, PlatformError)),
        before_sleep=lambda retry_state: logger.warning(
            f"重试 {retry_state.attempt_number}/{max_attempts}"
        )
    )

class CrawlerService:
    @with_retry(max_attempts=3)
    async def search(self, ...):
        ...
```

---

### 2.7 平台抽象架构 ⭐⭐⭐

**开源项目实现:**
```python
# 抽象爬虫基类
class AbstractCrawler(ABC):
    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def search(self, keyword: str): ...

    @abstractmethod
    async def get_note_detail(self, note_id: str): ...

# 平台实现
class XiaoHongShuCrawler(AbstractCrawler): ...
class DouyinCrawler(AbstractCrawler): ...
class BilibiliCrawler(AbstractCrawler): ...
```

**借鉴建议:**
虽然我们目前只支持小红书，但预留多平台架构是有价值的:

```python
# media_crawler_api/platforms/__init__.py
from abc import ABC, abstractmethod

class PlatformCrawler(ABC):
    platform: str

    @abstractmethod
    async def search(self, keyword: str, **kwargs) -> SearchResult: ...

    @abstractmethod
    async def get_detail(self, content_id: str) -> ContentDetail: ...

# 实现
class XHSCrawler(PlatformCrawler):
    platform = "xhs"

class DouyinCrawler(PlatformCrawler):  # 未来扩展
    platform = "douyin"

# 工厂
def get_crawler(platform: str) -> PlatformCrawler:
    crawlers = {"xhs": XHSCrawler, "douyin": DouyinCrawler}
    return crawlers[platform]()
```

---

## 三、功能缺失对比

| 功能 | 开源项目 | 我们的项目 | 优先级 |
|------|----------|------------|--------|
| IP代理池 | ✅ 完整实现 | ❌ 缺失 | **P0** |
| 评论词云 | ✅ 支持 | ❌ 缺失 | P2 |
| 创作者主页爬取 | ✅ 支持 | ❌ 缺失 | P1 |
| 视频下载 | ✅ 支持 | ❌ 缺失 | P1 |
| 图片下载 | ✅ 支持 | ⚠️ 只返回URL | P1 |
| 断点续爬 | ✅ Pro版支持 | ❌ 缺失 | P1 |
| 多账号轮换 | ✅ 支持 | ⚠️ 需优化 | P1 |
| QR码登录 | ✅ 支持 | ❌ 缺失 | P2 |
| 本地数据存储 | ✅ 多格式 | ❌ 仅飞书 | P2 |

---

## 四、架构差异分析

### 4.1 我们的优势

| 优势 | 说明 |
|------|------|
| **n8n工作流集成** | 可视化编排，易于调整流程 |
| **飞书表格存储** | 团队协作友好，无需额外数据库 |
| **统一API接口** | RESTful设计，便于集成 |
| **Cookie状态机** | 完善的生命周期管理 |
| **安全性** | AES加密、日志脱敏、审计 |
| **request_id追踪** | 全链路可观测 |

### 4.2 开源项目优势

| 优势 | 说明 |
|------|------|
| **多平台支持** | 7个主流平台，代码复用率高 |
| **代理IP池** | 应对反爬必备 |
| **CDP模式** | 连接真实浏览器，反检测效果好 |
| **本地执行** | 无需服务器，适合个人使用 |
| **断点续爬** | 大规模采集必备 |

---

## 五、推荐实施路线图

### Phase 1: 紧急补充 (1-2天)

1. **添加IP代理支持**
   - 实现 `ProxyPool` 类
   - 集成到 `CrawlerService`
   - 支持代理失效自动切换

2. **修复工作流问题** (已识别)
   - PATCH → PUT 方法修复
   - MediaCrawler API URL修复

### Phase 2: 功能增强 (3-5天)

3. **CDP模式支持**
   - 支持连接远程Chrome
   - 更好的反检测能力

4. **媒体下载**
   - 图片批量下载到OSS
   - 视频下载支持

5. **创作者爬取**
   - 新增 `/api/creator/{user_id}` 端点
   - 获取创作者所有笔记

### Phase 3: 架构优化 (1周)

6. **抽象存储层**
   - 支持本地SQLite（开发用）
   - 保持飞书表格（生产用）

7. **多平台预留**
   - 抽象 `PlatformCrawler` 接口
   - 为抖音等平台预留

8. **断点续爬**
   - 记录采集进度
   - 支持从中断点恢复

---

## 六、代码示例：代理池集成

```python
# media_crawler_api/services/proxy.py

import asyncio
import random
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
from ..utils.logging import get_logger

logger = get_logger(__name__)

class ProxyPool:
    """IP代理池管理"""

    def __init__(self, provider: str = "custom"):
        self.provider = provider
        self.proxies: List[str] = []
        self.current_index = 0
        self.last_refresh: Optional[datetime] = None
        self.refresh_interval = timedelta(minutes=5)
        self._lock = asyncio.Lock()

    async def initialize(self, proxy_list: List[str]):
        """初始化代理列表"""
        self.proxies = proxy_list
        self.last_refresh = datetime.now()
        logger.info(f"代理池初始化完成，共 {len(proxy_list)} 个代理")

    async def get_proxy(self) -> Optional[str]:
        """获取一个可用代理"""
        async with self._lock:
            if not self.proxies:
                return None

            # 轮询方式获取
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)

            # 验证代理
            if await self._validate(proxy):
                return proxy

            # 代理无效，尝试下一个
            return await self._get_next_valid()

    async def _validate(self, proxy: str) -> bool:
        """验证代理可用性"""
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=5) as client:
                resp = await client.get("http://httpbin.org/ip")
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"代理验证失败: {proxy}, {e}")
            return False

    async def _get_next_valid(self) -> Optional[str]:
        """获取下一个有效代理"""
        for _ in range(len(self.proxies)):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            if await self._validate(proxy):
                return proxy
        return None

    async def mark_failed(self, proxy: str):
        """标记代理失败"""
        async with self._lock:
            if proxy in self.proxies:
                self.proxies.remove(proxy)
                logger.warning(f"代理已移除: {proxy}, 剩余 {len(self.proxies)} 个")


# 集成到CrawlerService
class CrawlerService:
    def __init__(self, proxy_pool: Optional[ProxyPool] = None):
        self.proxy_pool = proxy_pool

    async def search(self, ...):
        proxy = None
        if self.proxy_pool:
            proxy = await self.proxy_pool.get_proxy()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                proxy=proxy,  # 使用代理
                ...
            ) as resp:
                ...
```

---

## 七、总结

### 必须借鉴 (P0)
1. **IP代理池** - 反爬必备，目前完全缺失
2. **CDP模式** - 提升反检测能力

### 建议借鉴 (P1)
3. **tenacity重试** - 统一的重试策略
4. **媒体下载** - 图片/视频本地化
5. **创作者爬取** - 扩展采集维度

### 可选借鉴 (P2)
6. **多平台架构** - 预留扩展能力
7. **抽象存储层** - 便于测试和扩展
8. **词云生成** - 数据分析增值

---

> 分析完成时间: 2025-12-16 19:00 CST
