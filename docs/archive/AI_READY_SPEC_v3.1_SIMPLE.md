# MediaCrawler v3.1 AI 开发规格

> 目标：AI 按此文档逐步产出代码，通过验收清单后进入灰度

---

## 一、核心规则（必须遵守）

| # | 规则 | 验证方法 |
|---|------|---------|
| 1 | **n8n 是唯一写入者** - API 只读取，不写飞书 | `grep "feishu" api/` 返回空 |
| 2 | **所有写入幂等** - 重复写入无副作用 | 相同数据写2次，表记录=1条 |
| 3 | **执行锁防重入** - 同一工作流只能有1个运行中 | 并发启动2个，只有1个获得锁 |
| 4 | **记录锁防并发** - 同一记录不被多个执行处理 | 2个执行抢1条记录，只有1个成功 |
| 5 | **超时自动回收** - 锁超过30分钟自动释放 | 模拟超时→15分钟后→锁释放 |
| 6 | **request_id 贯穿** - 从n8n到API到日志可追踪 | grep trace_id 能找到完整链路 |
| 7 | **Cookie 不明文** - 存储加密，日志脱敏 | 审计脚本 passed=true |
| 8 | **批量支持部分失败** - 返回成功和失败的详情 | 3条请求1条超时，返回2成功+1失败 |

---

## 二、数据表结构

### 2.1 tbl_cookie（Cookie管理）

```
字段：cookie_name(幂等键), platform, cookie_encrypted, status,
      priority, daily_used, daily_limit, consecutive_errors,
      cooling_until, created_at, updated_at

状态流转：
  active ──(连续错误≥3)──→ cooling ──(30分钟后)──→ active
    │                         │
    │(累计错误≥10)            │(冷却期再错误)
    ↓                         ↓
  invalid                   banned
```

### 2.2 tbl_candidate（候选笔记）

```
字段：note_id(幂等键), platform, note_url, status,
      processing_lock, locked_at, retry_count,
      source_keyword, exec_meta

状态流转：
  pending ──(获取锁)──→ processing ──(成功)──→ collected
                            │
                     (失败且重试<3) → pending
                     (失败且重试≥3) → failed
                     (超时回收)     → pending
```

### 2.3 tbl_crawl_execution（执行锁）

```
字段：workflow_name, execution_id, status,
      started_at, heartbeat_at, completed_at,
      items_processed, items_failed

锁规则：
  - 同一 workflow_name 只能有1条 status=running
  - heartbeat_at 超过30分钟视为超时
  - 超时的执行自动标记为 timeout
```

### 2.4 tbl_source（新增字段）

```
新增：idempotency_key, processing_lock, locked_at,
      retry_count, last_error_code, exec_meta

幂等键格式：{note_id}_v1
```

---

## 三、API 契约

### 3.1 统一响应格式

```json
{
  "success": true/false,
  "data": {...},
  "error": {
    "code": "ERROR_CODE",
    "message": "描述",
    "retryable": true/false
  },
  "meta": {
    "request_id": "xxx",
    "latency_ms": 123,
    "cookie_used": "account_01"
  }
}
```

### 3.2 批量响应格式

```json
{
  "success": false,
  "items": [
    {"id": "note_001", "success": true, "data": {...}},
    {"id": "note_002", "success": false, "error": {...}}
  ],
  "summary": {"total": 2, "succeeded": 1, "failed": 1},
  "error": {"code": "PARTIAL_FAIL", "retryable": true},
  "meta": {...}
}
```

### 3.3 错误码与处理

| 错误码 | 可重试 | n8n动作 | 最大重试 |
|--------|--------|---------|---------|
| COOKIE_EXHAUSTED | 否 | 暂停+告警 | 0 |
| COOKIE_INVALID | 是 | 切换Cookie | 3 |
| PLATFORM_ERROR | 是 | 重试 | 2 |
| TIMEOUT_ERROR | 是 | 重试 | 2 |
| NETWORK_ERROR | 是 | 退避重试 | 3 |
| PARTIAL_FAIL | 是 | 重试失败项 | 2 |
| INVALID_INPUT | 否 | 跳过+告警 | 0 |

---

## 四、n8n 工作流节点

### 4.1 获取执行锁

```javascript
// 输入：workflow_name
// 输出：{locked: bool, execution_id: string}

const execution_id = `exec-${Date.now()}-${random()}`;

// 1. 查询是否有运行中的执行
const running = query("status=running AND heartbeat > now-30min");
if (running.length > 0) {
  return {locked: false, reason: "已有执行在运行"};
}

// 2. 标记超时的执行
update("status=running AND heartbeat < now-30min", {status: "timeout"});

// 3. 创建新执行锁
insert({workflow_name, execution_id, status: "running"});
return {locked: true, execution_id};
```

### 4.2 获取并锁定记录

```javascript
// 输入：execution_id, batch_size=10
// 输出：{records: [...], locked_count: int}

// 1. 查询待处理记录
const pending = query("status=pending", limit=batch_size);

// 2. 逐条锁定
const locked = [];
for (record of pending) {
  try {
    update(record.id, {
      status: "processing",
      processing_lock: execution_id,
      locked_at: now()
    });
    locked.push(record);
  } catch (e) {
    // 被其他执行抢占，跳过
  }
}
return {records: locked, locked_count: locked.length};
```

### 4.3 幂等写入

```javascript
// 输入：crawl_result, record_info
// 输出：{action: "created"|"skipped"}

const idempotency_key = `${record_info.note_id}_v1`;

// 1. 检查是否已存在
const existing = query(`idempotency_key=${idempotency_key}`);
if (existing.length > 0) {
  return {action: "skipped", existing_id: existing[0].id};
}

// 2. 写入新记录
insert(tbl_source, {...crawl_result, idempotency_key});

// 3. 更新候选记录状态
update(tbl_candidate, record_info.id, {
  status: "collected",
  processing_lock: null
});

return {action: "created"};
```

### 4.4 超时回收（独立工作流，每15分钟）

```javascript
const timeout_threshold = now() - 30min;

// 1. 回收执行锁
update(tbl_crawl_execution,
  "status=running AND heartbeat_at < threshold",
  {status: "timeout"}
);

// 2. 回收记录锁
const stale = query(tbl_candidate,
  "status=processing AND locked_at < threshold"
);
for (record of stale) {
  update(record.id, {
    status: record.retry_count >= 3 ? "failed" : "pending",
    processing_lock: null,
    retry_count: record.retry_count + 1
  });
}
```

---

## 五、安全要求

### 5.1 Cookie 加密

```
算法：AES-256 (Fernet)
密钥：从环境变量 COOKIE_MASTER_KEY 派生
存储：tbl_cookie.cookie_encrypted + encryption_key_id
```

### 5.2 日志脱敏

```
脱敏模式：
  web_session=xxx  →  web_session=***REDACTED***
  "cookie_value": "xxx"  →  "cookie_value": "***REDACTED***"

验证：grep "web_session=" logs/ 返回空
```

---

## 六、告警配置

| 告警 | 条件 | 级别 |
|------|------|------|
| Cookie耗尽 | active_count < 1 | P0 |
| 成功率低 | success_rate < 90% 持续10分钟 | P1 |
| 处理积压 | pending > 500 持续30分钟 | P2 |

---

## 七、验收清单

### Day 1 ✓

- [ ] 4张表已创建，字段完整
- [ ] API 返回统一响应格式
- [ ] 错误码枚举完整
- [ ] Cookie 加密/解密正常
- [ ] 安全审计脚本通过

### Day 2 ✓

- [ ] 执行锁获取/释放正常
- [ ] 记录锁获取/释放正常
- [ ] 幂等写入测试通过
- [ ] request_id 全链路可追踪
- [ ] 超时回收任务正常
- [ ] 日志无明文Cookie

### Day 3 ✓

- [ ] 3条告警可触发
- [ ] 完整采集流程跑通
- [ ] 部分失败场景验证通过
- [ ] 回滚方案可执行

---

## 八、常量配置

```yaml
# 锁超时
LOCK_TIMEOUT_MINUTES: 30
RECOVERY_INTERVAL_MINUTES: 15

# Cookie
COOLING_DURATION_MINUTES: 30
MAX_CONSECUTIVE_ERRORS: 3
MAX_TOTAL_ERRORS: 10

# API 超时
SEARCH_TIMEOUT: 30s
DETAIL_TIMEOUT: 15s (单条) / 60s (批量)

# 重试
MAX_RETRY: 2-3 次
BACKOFF: [5s, 15s, 45s]

# 批量
BATCH_SIZE: 10
```

---

## 九、已知问题修复

| 问题 | 修复 |
|------|------|
| tbl_candidate 缺少 retry_count | 添加字段 |
| 锁超时阈值不一致 | 统一为 30 分钟 |
| PARTIAL_FAIL.retryable 矛盾 | 改为 true |
| 幂等键版本未定义 | 固定为 v1 |

---

## 十、文件清单

```
mediacrawler-api/
├── media_crawler_api/
│   ├── models/response.py      # 响应模型
│   ├── routers/crawler.py      # API路由
│   ├── routers/health.py       # 健康检查
│   ├── services/cookie.py      # Cookie管理
│   ├── utils/crypto.py         # 加密
│   ├── utils/logging.py        # 日志脱敏
│   └── utils/alerting.py       # 告警
├── scripts/security_audit.py   # 安全审计
└── docs/AI_READY_SPEC.md       # 本文档
```

---

> **执行顺序**：Day1(数据+API) → Day2(n8n+安全) → Day3(告警+测试) → 灰度
