# MediaCrawler v4.0 重构计划

> 版本: v4.0 | 更新: 2025-12-17
> 核心原则: **最大化复用 MediaCrawler 代码，最小化新开发量**

---

## 一、问题与目标

### 1.1 现有问题

| 优先级 | 问题 | 解决方案 |
|--------|------|---------|
| P0 | HTTP方法错误 (PATCH→PUT) | 修改工作流节点 |
| P0 | API URL不可用 | 使用环境变量 |
| P1 | 无代理池/重试机制 | **直接复用 MediaCrawler** |
| P1 | 无CDP模式 | **直接复用 MediaCrawler** |
| P2 | 存储层未抽象 | **直接复用 MediaCrawler** |

### 1.2 复用策略

```
┌─────────────────────────────────────────────────────────┐
│  复用优先级: 直接复用 > 适配包装 > 参考重写 > 新开发      │
├─────────────────────────────────────────────────────────┤
│  ✅ 直接复用: proxy/, base/, store/, config/            │
│  ✅ 适配包装: media_platform/xhs/ (添加FastAPI路由)     │
│  ⚠️ 参考重写: 仅飞书存储后端                            │
│  ❌ 新开发:   尽量避免                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 二、MediaCrawler 可复用模块

**仓库**: https://github.com/NanmiCoder/MediaCrawler

### 2.1 直接复用清单

| 模块 | 源文件 | 复用方式 | 开发量 |
|------|--------|---------|--------|
| **抽象基类** | `base/base_crawler.py` | 直接复制 | 0 |
| **代理池** | `proxy/proxy_ip_pool.py` | 直接复制 | 0 |
| **代理提供商** | `proxy/providers/` | 直接复制 | 0 |
| **XHS客户端** | `media_platform/xhs/client.py` | 直接复制 | 0 |
| **XHS核心** | `media_platform/xhs/core.py` | 适配包装 | 少量 |
| **存储抽象** | `store/xhs/_store_impl.py` | 直接复制 | 0 |
| **配置管理** | `config/base_config.py` | 合并使用 | 少量 |
| **工具函数** | `tools/utils.py` | 直接复制 | 0 |

### 2.2 需要新增的代码

| 模块 | 说明 | 开发量 |
|------|------|--------|
| FastAPI路由层 | 包装现有功能为REST API | 中等 |
| 飞书存储后端 | 实现 AbstractStore 接口 | 中等 |
| n8n工作流修复 | 修改HTTP方法和URL | 少量 |

---

## 三、精简架构

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI 路由层                    │
│   /search  /note  /creator  /cookie  /media        │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│              MediaCrawler 核心 (直接复用)            │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐  │
│  │XHSClient    │ │ProxyIpPool  │ │AbstractStore │  │
│  │+tenacity    │ │+RefreshMixin│ │(6种后端)      │  │
│  └─────────────┘ └─────────────┘ └──────────────┘  │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                   存储层                             │
│   SQLite(复用) │ JSON(复用) │ Feishu(新增)          │
└─────────────────────────────────────────────────────┘
```

---

## 四、实施计划

### Phase 1: 紧急修复 (Day 1)

**工作流修复** - 无需代码开发:

```javascript
// 所有飞书更新节点: PATCH → PUT
// API URL: 硬编码 → {{ $env.MEDIACRAWLER_API_URL }}
```

| 工作流 | 修改节点 |
|--------|---------|
| WF-Discovery | Acquire Lock, Release Lock |
| WF-Extraction | Lock Candidate, Mark Done, Update Failed |
| WF-Generation | Lock Source, Mark Done, Update Failed |
| WF-Publish | Lock Content, Mark Published, Mark Failed |
| WF-CookieManager | Batch Updates, Update Cookie, Rollback |

### Phase 2: 复用集成 (Day 2-4)

**Step 1: 复制 MediaCrawler 核心模块**

```bash
# 直接复制，无需修改
cp -r MediaCrawler/base/ ./media_crawler_api/
cp -r MediaCrawler/proxy/ ./media_crawler_api/
cp -r MediaCrawler/media_platform/xhs/ ./media_crawler_api/platforms/
cp -r MediaCrawler/tools/ ./media_crawler_api/
cp MediaCrawler/config/base_config.py ./media_crawler_api/config/
```

**Step 2: 创建 FastAPI 包装层**

```python
# media_crawler_api/routers/crawler.py
from fastapi import APIRouter
from ..platforms.xhs.client import XiaoHongShuClient  # 直接复用

router = APIRouter(prefix="/api")
client = XiaoHongShuClient()  # 已内置 tenacity 重试 + 代理刷新

@router.get("/search")
async def search(keyword: str, limit: int = 20):
    return await client.get_note_by_keyword(keyword, limit)

@router.get("/note/{note_id}")
async def get_note(note_id: str, xsec_token: str):
    return await client.get_note_by_id(note_id, xsec_token)

@router.get("/creator/{user_id}")
async def get_creator(user_id: str):
    return await client.get_creator_info(user_id)

@router.get("/note/{note_id}/comments")
async def get_comments(note_id: str, cursor: str = ""):
    return await client.get_note_comments(note_id, cursor)
```

**Step 3: 新增飞书存储后端**

```python
# media_crawler_api/store/feishu.py
from ..base.base_crawler import AbstractStore  # 复用抽象类

class FeishuStore(AbstractStore):
    """仅需实现3个方法"""

    async def store_content(self, content_item: dict) -> None:
        # 调用飞书API写入
        pass

    async def store_comment(self, comment_item: dict) -> None:
        pass

    async def store_creator(self, creator: dict) -> None:
        pass
```

### Phase 3: 配置合并 (Day 5)

```python
# media_crawler_api/config/settings.py
# 复用 MediaCrawler 配置项，仅新增飞书相关

# === 直接复用 MediaCrawler 配置 ===
PLATFORM = "xhs"
ENABLE_IP_PROXY = True
IP_PROXY_PROVIDER_NAME = "kuaidaili"  # 或 custom
HEADLESS = True
SAVE_DATA_OPTION = "feishu"  # 新增选项
CRAWLER_MAX_NOTES_COUNT = 100
ENABLE_GET_COMMENTS = True

# === 新增飞书配置 ===
FEISHU_APP_ID = ""
FEISHU_APP_SECRET = ""
FEISHU_APP_TOKEN = ""
```

---

## 五、目录结构 (精简版)

```
media_crawler_api/
├── main.py                    # FastAPI入口
├── config/
│   └── settings.py            # 合并配置 (复用+新增)
├── base/                      # 【直接复制】
│   └── base_crawler.py        # 抽象基类
├── proxy/                     # 【直接复制】
│   ├── proxy_ip_pool.py       # 代理池
│   └── providers/             # 代理提供商
├── platforms/
│   └── xhs/                   # 【直接复制+少量适配】
│       ├── client.py          # API客户端 (已含重试)
│       └── core.py            # 爬虫核心
├── store/
│   ├── abstract.py            # 【直接复制】
│   ├── sqlite.py              # 【直接复制】
│   ├── json_store.py          # 【直接复制】
│   └── feishu.py              # 【新增】
├── routers/                   # 【新增-包装层】
│   ├── crawler.py             # 搜索/详情/评论
│   ├── creator.py             # 创作者
│   └── cookie.py              # Cookie管理
└── tools/                     # 【直接复制】
    └── utils.py
```

---

## 六、关键复用代码

### 6.1 代理池 (零开发-直接用)

MediaCrawler 已实现:
- `ProxyIpPool.get_or_refresh_proxy()` - 过期自动刷新
- `ProxyRefreshMixin` - 混入API客户端
- `@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))` - tenacity重试

### 6.2 XHS客户端 (零开发-直接用)

MediaCrawler `client.py` 已包含:
- `get_note_by_keyword()` - 搜索
- `get_note_by_id()` - 详情
- `get_note_comments()` - 评论
- `get_note_sub_comments()` - 子评论
- `get_creator_info()` - 创作者
- `get_notes_by_creator()` - 创作者笔记

### 6.3 存储后端 (仅新增飞书)

MediaCrawler 已实现:
- `XhsCsvStoreImplement`
- `XhsDbStoreImplement`
- `XhsJsonStoreImplement`
- `XhsSqliteStoreImplement`
- `XhsMongoStoreImplement`
- `XhsExcelStoreImplement`

**仅需新增**: `FeishuStoreImplement`

---

## 七、验收清单

### Phase 1 ✅
- [ ] 工作流 HTTP 方法修复 (PATCH → PUT)
- [ ] API URL 环境变量化

### Phase 2 ✅
- [ ] MediaCrawler 模块复制完成
- [ ] FastAPI 路由层包装完成
- [ ] 代理池正常工作
- [ ] 重试机制正常工作

### Phase 3 ✅
- [ ] 飞书存储后端实现
- [ ] 配置合并完成
- [ ] 端到端测试通过

---

## 八、开发量估算

| 阶段 | 工作内容 | 代码行数 | 耗时 |
|------|---------|---------|------|
| Phase 1 | 工作流修复 | 0 (配置) | 0.5天 |
| Phase 2 | 复制+包装 | ~200行 | 2天 |
| Phase 3 | 飞书后端 | ~150行 | 1.5天 |
| **总计** | | **~350行** | **4天** |

**对比**: 如果全部重写需 2000+ 行代码，复用策略节省 **80%** 开发量。

---

## 九、风险与应对

| 风险 | 应对 |
|------|------|
| MediaCrawler 版本更新 | 锁定 commit hash |
| 接口不兼容 | 添加适配层 |
| 飞书API限流 | 复用现有限流器 |

---

> 文档版本: v4.0 (精简版)
> 核心策略: 复用 MediaCrawler，仅新增 FastAPI 路由 + 飞书存储
> 预计新增代码: ~350行 | 预计耗时: 4天
