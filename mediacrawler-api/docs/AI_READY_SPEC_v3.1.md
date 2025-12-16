# MediaCrawler v3.1 AI-Ready 工程规格文档

> **文档类型**: AI 可执行规格 (AI-Ready Spec)
> **版本**: 3.1.0
> **目标**: AI 可按文档逐步产出代码、n8n 配置、测试用例，循环优化直到满足灰度验收
> **基准文档**: MEDIACRAWLER_P0_IMPLEMENTATION_PLAN.md
> **更新日期**: 2025-12-16

---

## 文档结构

```
1. 可执行条款清单 (Executable Clauses)
2. 模块规格 (Module Specs)
   ├── M1: 数据层 (Data Layer)
   ├── M2: API 服务 (API Service)
   ├── M3: n8n 工作流 (Workflow)
   ├── M4: 安全模块 (Security)
   ├── M5: 可观测性 (Observability)
   └── M6: 运维保障 (Operations)
3. Gap & Fix 清单 (一致性审查结果)
4. 测试计划 (Test Plan)
5. n8n 导入指南 (Import Guide)
6. AI 执行路线图 (Execution Roadmap)
```

---

## 1. 可执行条款清单

### 1.1 硬性原则 → 可执行条款映射

| 条款ID | 原则 | 可执行定义 | 触发条件 | 失败语义 | 验收证据 |
|--------|------|-----------|----------|----------|----------|
| C-01 | n8n唯一写入者 | API 层代码禁止导入飞书 SDK，所有飞书写入仅在 n8n Code 节点 | 任何代码提交 | 代码审查拒绝 | `grep -r "lark\|feishu" media_crawler_api/` 返回空 |
| C-02 | 状态机闭环 | 每个实体表必须有 `status` 字段 + 状态转换表 + 不存在孤立状态 | 数据层变更 | 迁移失败 | 状态转换测试用例全通过 |
| C-03 | 幂等写入 | 写入前查询 `idempotency_key`，存在则跳过，返回 `action=skipped` | 任何写入操作 | 重复数据 | 幂等测试: 相同数据写入2次，表记录数=1 |
| C-04 | 执行锁防重入 | 同一 `workflow_name` 仅允许1个 `status=running` 的执行 | 工作流启动 | 第二个执行立即退出 | 并发启动测试: 2个执行，1个获得锁，1个返回 `locked=false` |
| C-05 | 记录锁防并发 | `processing_lock` 字段 + `locked_at` 时间戳 | 记录处理 | 同一记录不被多执行并发处理 | 并发测试: 2个执行抢同一记录，仅1个成功 |
| C-06 | 超时回收 | `locked_at > 30分钟` 的记录自动回退 `pending` | 定时任务(每15分钟) | 锁死记录无法处理 | 模拟锁死→15分钟后→记录回退 pending |
| C-07 | request_id 贯穿 | n8n 生成 `trace_id` → HTTP Header `X-Request-ID` → API 日志 → 响应 `meta.request_id` | 任何请求 | 无法追踪 | `grep "trace_id_xxx" api.log` 能找到完整链路 |
| C-08 | Cookie 永不明文 | 存储用 AES-256 加密，日志用正则替换为 `***REDACTED***` | Cookie 操作 | 安全审计失败 | 审计脚本 `passed=true` |
| C-09 | 批量部分失败 | 响应必须包含 `items[]` + `summary.succeeded/failed` + `error.details.failed_ids` | 批量 API | 丢失部分结果 | 部分失败测试: 3条请求1条超时，返回2条成功+1条失败详情 |
| C-10 | 最小告警 | 3条核心告警必须可触发: COOKIE_EXHAUSTED / API_SUCCESS_RATE_LOW / PROCESSING_BACKLOG | 异常条件 | 无感知 | 告警触发测试全通过 |

### 1.2 条款依赖关系

```
C-01 (n8n唯一写入)
  └── C-03 (幂等写入) 在 n8n 节点实现
  └── C-04/C-05 (锁机制) 在 n8n 节点实现

C-02 (状态机闭环)
  └── C-06 (超时回收) 状态必须能回退

C-07 (request_id)
  └── 依赖 API 和 n8n 同时实现

C-08 (Cookie安全)
  └── 依赖 M4 安全模块
```

---

## 2. 模块规格

### M1: 数据层 (Data Layer)

#### M1.1 飞书表规格

##### tbl_cookie

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| record_id | text | PK, auto | 飞书记录ID |
| cookie_name | text | UNIQUE, NOT NULL | 幂等键 |
| platform | enum | NOT NULL, default='xhs' | xhs/dy/wb |
| cookie_encrypted | text | NOT NULL | AES加密值 |
| encryption_key_id | text | NOT NULL | 密钥ID |
| status | enum | NOT NULL, default='active' | active/cooling/invalid/banned |
| priority | int | NOT NULL, default=1 | 越大越优先 |
| daily_used | int | NOT NULL, default=0 | 当日使用次数 |
| daily_limit | int | NOT NULL, default=100 | 每日限额 |
| total_used | int | NOT NULL, default=0 | 累计使用次数 |
| consecutive_errors | int | NOT NULL, default=0 | 连续错误次数 |
| total_errors | int | NOT NULL, default=0 | 累计错误次数 |
| last_used_at | datetime | NULL | 最后使用时间 |
| last_error_at | datetime | NULL | 最后错误时间 |
| cooling_until | datetime | NULL | 冷却截止时间 |
| created_at | datetime | NOT NULL | 创建时间 |
| updated_at | datetime | NOT NULL | 更新时间 |

**状态机定义:**

```yaml
states:
  - active      # 可用
  - cooling     # 冷却中
  - invalid     # 已失效
  - banned      # 被封禁

transitions:
  - from: active
    to: cooling
    trigger: consecutive_errors >= 3
    action: |
      cooling_until = now() + 30min
      consecutive_errors = 0

  - from: cooling
    to: active
    trigger: now() > cooling_until
    action: |
      cooling_until = null

  - from: cooling
    to: banned
    trigger: error_during_cooling
    action: |
      log("Cookie banned during cooling")

  - from: active
    to: invalid
    trigger: total_errors >= 10 OR validation_failed
    action: null

  - from: active
    to: banned
    trigger: platform_ban_detected
    action: null

terminal_states: [invalid, banned]
recovery_from_terminal: manual_only
```

##### tbl_candidate

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| record_id | text | PK, auto | 飞书记录ID |
| note_id | text | UNIQUE, NOT NULL | 幂等键 |
| platform | enum | NOT NULL, default='xhs' | 平台 |
| note_url | url | NOT NULL | 笔记链接 |
| title | text | NULL | 标题 |
| author_id | text | NULL | 作者ID |
| author_name | text | NULL | 作者昵称 |
| liked_count | int | default=0 | 点赞数 |
| collected_count | int | default=0 | 收藏数 |
| comment_count | int | default=0 | 评论数 |
| status | enum | NOT NULL, default='pending' | 状态 |
| processing_lock | text | NULL | 锁: workflow_exec_id |
| locked_at | datetime | NULL | 锁定时间 |
| retry_count | int | default=0 | 重试次数 |
| source_keyword | text | NULL | 来源关键词 |
| discovered_at | datetime | NOT NULL | 发现时间 |
| created_at | datetime | NOT NULL | 创建时间 |
| updated_at | datetime | NOT NULL | 更新时间 |
| exec_meta | json | NULL | 执行元数据 |

**状态机定义:**

```yaml
states:
  - pending     # 待处理
  - processing  # 处理中
  - collected   # 已采集
  - failed      # 失败

transitions:
  - from: pending
    to: processing
    trigger: workflow_acquires_lock
    action: |
      processing_lock = execution_id
      locked_at = now()

  - from: processing
    to: collected
    trigger: crawl_success
    action: |
      processing_lock = null
      locked_at = null
      # 写入 tbl_source

  - from: processing
    to: failed
    trigger: crawl_failed AND retry_count >= 3
    action: |
      processing_lock = null
      last_error_code = error.code
      last_error_message = error.message

  - from: processing
    to: pending
    trigger: timeout_recovery OR (crawl_failed AND retry_count < 3)
    action: |
      processing_lock = null
      locked_at = null
      retry_count += 1

invariants:
  - "processing_lock != null IMPLIES status == 'processing'"
  - "locked_at != null IMPLIES processing_lock != null"
```

##### tbl_crawl_execution (执行锁表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| record_id | text | PK, auto | 飞书记录ID |
| workflow_name | text | NOT NULL | 工作流名称 |
| execution_id | text | UNIQUE, NOT NULL | 执行ID |
| status | enum | NOT NULL, default='running' | running/completed/timeout |
| started_at | datetime | NOT NULL | 开始时间 |
| completed_at | datetime | NULL | 完成时间 |
| heartbeat_at | datetime | NOT NULL | 心跳时间 |
| items_processed | int | default=0 | 已处理条数 |
| items_failed | int | default=0 | 失败条数 |
| error_summary | text | NULL | 错误摘要 |

**执行锁语义:**

```yaml
acquire_lock:
  precondition: |
    NOT EXISTS (
      SELECT 1 FROM tbl_crawl_execution
      WHERE workflow_name = ?
        AND status = 'running'
        AND heartbeat_at > now() - 30min
    )
  action: |
    INSERT INTO tbl_crawl_execution (
      workflow_name, execution_id, status,
      started_at, heartbeat_at
    ) VALUES (?, ?, 'running', now(), now())
  postcondition: |
    EXACTLY_ONE record with status='running' for this workflow_name

release_lock:
  action: |
    UPDATE tbl_crawl_execution
    SET status = 'completed', completed_at = now()
    WHERE execution_id = ?

timeout_recovery:
  trigger: heartbeat_at < now() - 30min AND status = 'running'
  action: |
    UPDATE tbl_crawl_execution
    SET status = 'timeout', completed_at = now(),
        error_summary = '执行超时自动回收'
    WHERE execution_id = ?
```

##### tbl_source (变更字段)

| 新增字段 | 类型 | 约束 | 说明 |
|----------|------|------|------|
| idempotency_key | text | UNIQUE, NOT NULL | {note_id}_v{version} |
| processing_lock | text | NULL | 处理锁 |
| locked_at | datetime | NULL | 锁定时间 |
| retry_count | int | default=0 | 重试次数 |
| last_error_code | text | NULL | 最后错误码 |
| last_error_message | text | NULL | 最后错误信息 |
| exec_meta | json | NULL | 执行元数据 |

**幂等键规则:**

```yaml
idempotency_key_format: "{note_id}_v{version}"
version_strategy: "固定为 v1，除非数据结构变更"
collision_handling: "跳过写入，返回 existing_record_id"
```

---

### M2: API 服务 (API Service)

#### M2.1 响应契约

```yaml
# 统一响应信封
APIResponse:
  success: bool          # true=成功, false=失败
  data: object | null    # 成功时的数据
  error: ErrorDetail | null  # 失败时的错误
  meta: ResponseMeta     # 必填元数据

ErrorDetail:
  code: ErrorCode        # 枚举错误码
  message: string        # 人类可读描述
  retryable: bool        # n8n 是否应重试
  details: object | null # 附加信息

ResponseMeta:
  request_id: string     # 追踪ID (来自 X-Request-ID 或自动生成)
  timestamp: datetime    # ISO8601 UTC
  latency_ms: int        # 处理耗时
  cookie_used: string | null  # 使用的Cookie名 (脱敏)
  retry_count: int       # 内部重试次数

# 批量响应信封
BatchResponse:
  success: bool          # 全部成功=true, 有失败=false
  data: object           # 请求相关元信息
  items: BatchItemResult[]  # 每项结果
  summary:
    total: int
    succeeded: int
    failed: int
  error: ErrorDetail | null  # 有失败时为 PARTIAL_FAIL
  meta: ResponseMeta

BatchItemResult:
  id: string             # 项目ID (如 note_id)
  success: bool
  data: object | null
  error: ErrorDetail | null
```

#### M2.2 错误码映射表

| ErrorCode | retryable | HTTP Status | n8n 动作 | 重试上限 | 退避策略 |
|-----------|-----------|-------------|----------|----------|----------|
| COOKIE_EXHAUSTED | false | 503 | 暂停WF + 发送P0告警 | 0 | - |
| COOKIE_INVALID | true | 401 | 切换Cookie重试 | 3 | 立即 |
| COOKIE_COOLING | true | 429 | 等待或切换Cookie | 3 | 等待cooling_until |
| ACCOUNT_BANNED | false | 403 | 移除Cookie + 发送告警 | 0 | - |
| PLATFORM_ERROR | true | 502 | 重试 | 2 | 5s→15s |
| PARSE_ERROR | true | 500 | 重试 | 2 | 5s→15s |
| NETWORK_ERROR | true | 503 | 重试 | 3 | 5s→15s→45s |
| TIMEOUT_ERROR | true | 504 | 重试 | 2 | 10s→30s |
| PARTIAL_FAIL | true | 207 | 处理成功项，重试失败项 | 2 | 10s |
| INVALID_INPUT | false | 400 | 跳过 + 发送告警 | 0 | - |

#### M2.3 超时配置表

| 端点 | 默认超时 | 最大超时 | 重试间隔序列 | 最大重试 |
|------|---------|---------|-------------|---------|
| POST /api/search | 30s | 60s | [5s, 15s, 45s] | 3 |
| POST /api/note/detail (单条) | 15s | 30s | [5s, 15s] | 2 |
| POST /api/note/detail (批量≤20) | 60s | 120s | [10s, 30s] | 2 |
| GET /api/cookie/validate | 10s | 20s | [5s] | 2 |
| GET /health | 5s | 10s | - | 0 |

#### M2.4 API 端点规格

```yaml
POST /api/note/detail:
  description: "批量获取笔记详情"
  request:
    headers:
      X-Request-ID: string (optional)
    body:
      platform: enum [xhs, dy, wb]
      note_ids: string[] (1-20)
      cookie_name: string (optional)
      get_comments: bool (default=true)
      comments_limit: int (default=50, max=200)
  response: BatchResponse
  behavior:
    - 逐条获取，收集所有结果
    - 单条超时不影响其他
    - 返回 items[] 包含成功和失败详情
    - summary 统计成功/失败数
  error_handling:
    - Cookie 耗尽: 立即返回 COOKIE_EXHAUSTED
    - 单条超时: 该条返回 TIMEOUT_ERROR, retryable=true
    - 单条解析失败: 该条返回 PARSE_ERROR, retryable=true

POST /api/search:
  description: "搜索笔记"
  request:
    body:
      platform: enum
      keyword: string
      page: int (1-100)
      page_size: int (1-50)
      sort_type: enum [general, time_descending, popularity_descending]
      note_type: enum [0=all, 1=video, 2=image]
  response: APIResponse
  behavior:
    - 返回搜索结果列表
    - 不含完整内容，需调用 detail 获取

GET /health:
  response:
    status: enum [healthy, degraded, unhealthy]
    timestamp: datetime
    checks:
      api: string
      cookie_store: object
      memory: object
    metrics:
      total_requests: int
      success_rate: float
      active_cookies: int

GET /ready:
  response:
    ready: bool
    reason: string (if not ready)
```

---

### M3: n8n 工作流 (Workflow)

#### M3.1 工作流清单

| 工作流 | 触发器 | 职责 | 关键节点 |
|--------|--------|------|----------|
| WF-采集主流程 | Schedule/Manual | 搜索+详情+写入 | 执行锁、记录锁、幂等写入 |
| WF-锁超时回收 | Schedule (每15分钟) | 回收超时的执行锁和记录锁 | 超时检测、状态回退 |
| WF-Cookie管理 | Manual/Webhook | Cookie验证和状态更新 | 验证、状态转换 |

#### M3.2 节点规格: 执行锁

```yaml
node_name: "获取执行锁"
node_type: Code
position: 工作流开始处

input:
  workflow_name: string (硬编码或从环境变量)
  lock_timeout_minutes: 30

output:
  locked: bool
  execution_id: string (if locked=true)
  lock_record_id: string (if locked=true)
  reason: string (if locked=false)

logic: |
  1. 生成 execution_id = `exec-${timestamp}-${random}`
  2. 查询 tbl_crawl_execution WHERE workflow_name=? AND status='running'
  3. 对于每条 running 记录:
     - 计算 age = now - heartbeat_at
     - IF age < 30min: 返回 {locked: false, reason: "另一执行正在运行"}
     - ELSE: 更新该记录 status='timeout'
  4. 插入新记录 {workflow_name, execution_id, status='running', ...}
  5. 返回 {locked: true, execution_id, lock_record_id}

error_handling:
  - 飞书 API 失败: 返回 {locked: false, reason: "飞书API错误"}

verification:
  test_case: "并发启动2个执行"
  expected: "第1个获得锁，第2个返回 locked=false"
```

#### M3.3 节点规格: 记录锁

```yaml
node_name: "获取并锁定记录"
node_type: Code
position: 执行锁之后

input:
  execution_id: string (from 执行锁节点)
  batch_size: 10

output:
  has_records: bool
  locked_count: int
  records: array

logic: |
  1. 查询 tbl_candidate WHERE status='pending' ORDER BY discovered_at LIMIT batch_size
  2. 对于每条记录:
     - UPDATE SET status='processing', processing_lock=execution_id, locked_at=now()
     - 如果更新成功: 加入 locked_records
     - 如果失败(被其他执行抢占): 跳过
  3. 返回 {has_records: locked_count > 0, locked_count, records}

error_handling:
  - 更新冲突: 跳过该记录，不影响其他

verification:
  test_case: "2个执行同时抢10条记录"
  expected: "总共锁定10条，每条仅被1个执行锁定"
```

#### M3.4 节点规格: 幂等写入

```yaml
node_name: "幂等写入"
node_type: Code
position: API调用成功后

input:
  crawl_result: object (API返回的笔记详情)
  record_info: object (锁定的候选记录信息)

output:
  action: enum [created, skipped]
  idempotency_key: string
  source_record_id: string (if created)
  existing_record_id: string (if skipped)

logic: |
  1. 生成 idempotency_key = `${note_id}_v1`
  2. 查询 tbl_source WHERE idempotency_key=?
  3. IF 存在:
     - 返回 {action: 'skipped', idempotency_key, existing_record_id}
  4. ELSE:
     - 插入 tbl_source
     - 更新 tbl_candidate SET status='collected', processing_lock=null
     - 返回 {action: 'created', idempotency_key, source_record_id}

verification:
  test_case: "相同 note_id 写入2次"
  expected: "第1次 action=created, 第2次 action=skipped, tbl_source 仅1条记录"
```

#### M3.5 节点规格: 部分失败处理

```yaml
node_name: "处理批量结果"
node_type: Code
position: API调用返回后

input:
  api_response: BatchResponse
  locked_records: array

output:
  succeeded: array (可直接写入)
  failed: array (不可重试)
  retry_needed: array (可重试)
  request_id: string

logic: |
  1. 构建 note_id → record 映射
  2. 遍历 api_response.items:
     - IF success: 加入 succeeded
     - ELIF error.retryable: 加入 retry_needed
     - ELSE: 加入 failed
  3. 返回分类结果

downstream:
  - succeeded → 幂等写入节点
  - retry_needed → 重试节点 (if retry_count < max)
  - failed → 更新状态为 failed
```

#### M3.6 节点规格: trace_id 传递

```yaml
node_name: "初始化追踪"
node_type: Code
position: 工作流最开始

output:
  trace_id: string
  workflow_name: string
  execution_id: string

logic: |
  trace_id = `wf-${timestamp}-${random8}`
  store in $workflow.staticData

usage:
  - HTTP 请求必须设置 Header: X-Request-ID = trace_id + suffix
  - 示例: trace_id = "wf-1702728000-abc123"
         API 调用 Header: X-Request-ID = "wf-1702728000-abc123-detail"
```

---

### M4: 安全模块 (Security)

#### M4.1 Cookie 加密规格

```yaml
algorithm: AES-256 (via Fernet)
key_derivation: PBKDF2-SHA256, 100000 iterations

environment_variables:
  COOKIE_MASTER_KEY: string (必填, ≥32字符)
  COOKIE_KEY_SALT: string (可选, default="mediacrawler_v3")
  COOKIE_KEY_ID: string (可选, default="key_v1")

encryption_flow:
  input: plaintext_cookie
  output: (encrypted_value, key_id)
  steps:
    1. Derive key from MASTER_KEY using PBKDF2
    2. Encrypt with Fernet
    3. Base64 encode
    4. Return (encoded_value, current_key_id)

decryption_flow:
  input: (encrypted_value, key_id)
  output: plaintext_cookie
  steps:
    1. Load key for key_id (current or historical)
    2. Base64 decode
    3. Decrypt with Fernet
    4. Return plaintext

key_rotation:
  strategy: "新密钥加密新数据，旧密钥保留用于解密旧数据"
  historical_key_env: COOKIE_KEY_{KEY_ID} (如 COOKIE_KEY_KEY_V0)
```

#### M4.2 日志脱敏规格

```yaml
sensitive_patterns:
  # Cookie 值
  - pattern: '(web_session|a1|webId|gid|xsecappid)=[^;\s&]+'
    replacement: '\1=***REDACTED***'

  # JSON 字段
  - pattern: '"cookie_value"\s*:\s*"[^"]*"'
    replacement: '"cookie_value": "***REDACTED***"'
  - pattern: '"cookie_encrypted"\s*:\s*"[^"]*"'
    replacement: '"cookie_encrypted": "***REDACTED***"'

  # Authorization
  - pattern: '(Authorization|Bearer)\s*[:=]\s*[^\s,}]+'
    replacement: '\1: ***REDACTED***'

  # 密钥
  - pattern: '(api_key|secret|password)\s*[:=]\s*[^\s,}]+'
    replacement: '\1=***REDACTED***'

sensitive_dict_keys:
  - cookie_value
  - cookie_encrypted
  - cookie_string
  - password
  - secret
  - api_key
  - token
  - authorization

verification:
  method: "安全审计脚本"
  command: "python scripts/security_audit.py ."
  pass_criteria: "critical=0 AND high=0"
```

---

### M5: 可观测性 (Observability)

#### M5.1 exec_meta 规格

```yaml
exec_meta_schema:
  request_id: string      # API 返回的 request_id
  crawled_at: datetime    # 采集时间
  source_keyword: string  # 来源关键词
  workflow_trace_id: string  # n8n trace_id
  latency_ms: int         # API 耗时
  retry_count: int        # 重试次数

storage:
  table: tbl_source.exec_meta
  format: JSON string

example: |
  {
    "request_id": "wf-1702728000-abc123-detail",
    "crawled_at": "2025-12-16T10:00:00Z",
    "source_keyword": "粉底液",
    "workflow_trace_id": "wf-1702728000-abc123",
    "latency_ms": 1234,
    "retry_count": 0
  }
```

#### M5.2 追踪链路规格

```yaml
trace_chain:
  1_n8n_start:
    generate: trace_id = "wf-{timestamp}-{random8}"
    store: $workflow.staticData

  2_api_call:
    header: X-Request-ID = "{trace_id}-{step}"
    example: "wf-1702728000-abc123-detail"

  3_api_log:
    format: "{timestamp} - {logger} - {level} - [{request_id}] {message}"
    example: "2025-12-16 10:00:00 - crawler - INFO - [wf-1702728000-abc123-detail] 开始获取笔记"

  4_api_response:
    field: meta.request_id
    value: 与 header 相同

  5_feishu_write:
    field: exec_meta.request_id
    value: 与 API 响应相同

verification:
  command: |
    grep "wf-1702728000-abc123" api.log  # 应能找到完整链路
```

---

### M6: 运维保障 (Operations)

#### M6.1 告警规格

```yaml
alerts:
  COOKIE_EXHAUSTED:
    severity: P0
    condition: "active_cookie_count < 1"
    cooldown: 5min
    webhook: FEISHU_WEBHOOK_URL
    runbook: |
      1. 检查 tbl_cookie 表
      2. 确认失效原因
      3. cooling → 等待
      4. invalid → 重新登录
      5. banned → 更换账号
      6. 验证新 Cookie
      7. 更新状态

  API_SUCCESS_RATE_LOW:
    severity: P1
    condition: "success_rate < 0.9 for 10min"
    cooldown: 15min
    webhook: FEISHU_WEBHOOK_URL
    runbook: |
      1. 检查错误码分布
      2. TIMEOUT_ERROR → 检查网络
      3. COOKIE_* → 执行 Cookie Runbook
      4. PLATFORM_ERROR → 检查平台策略
      5. 查看日志: docker logs mediacrawler-api --since 10m

  PROCESSING_BACKLOG:
    severity: P2
    condition: "pending_count > 500 for 30min"
    cooldown: 60min
    webhook: FEISHU_WEBHOOK_URL
    runbook: |
      1. 检查工作流运行状态
      2. 检查执行锁超时
      3. 考虑增加 Cookie/并发
```

#### M6.2 健康检查规格

```yaml
/health:
  checks:
    api: "always ok if responding"
    cookie_store:
      ok: active_count > 0
      warning: active_count == 0
    memory:
      ok: process_mb < 1024
      warning: process_mb < 2048
      critical: process_mb >= 2048

/ready:
  ok: active_cookie_count >= 1
  not_ready: active_cookie_count < 1

/metrics:
  requests:
    total, success, error, success_rate
  cookies:
    active, cooling, invalid, total, daily_usage_rate
  resources:
    memory_mb, cpu_percent
```

---

## 3. Gap & Fix 清单

### 3.1 P0 级别问题 (必须修复)

| ID | 问题描述 | 影响 | 修复方案 | 验证方法 |
|----|---------|------|---------|---------|
| GAP-01 | tbl_candidate 缺少 retry_count 字段 | 超时回收无法判断重试次数 | 添加 retry_count 字段 | 字段存在性检查 |
| GAP-02 | 执行锁超时阈值不一致: §5.1 用 30min, §5.6 回收用 30min, 但文档 §2.1.4 未明确 | 超时判断混乱 | 统一为 LOCK_TIMEOUT_MINUTES=30 | 代码常量一致性检查 |
| GAP-03 | 幂等键版本策略未定义 | 数据结构变更时幂等失效 | 定义 version=v1 固定, 结构变更时升级 v2 | 文档明确 |
| GAP-04 | tbl_candidate 状态机缺少 failed→pending 的恢复路径 | failed 状态无法恢复 | 添加手动恢复路径或标记为 terminal | 状态机完整性测试 |
| GAP-05 | PARTIAL_FAIL 的 retryable 在原文 §3.3 表中是 true, 但 §3.1 ERROR_CONFIG 中是 false | n8n 重试逻辑混乱 | 统一为 retryable=true (可重试失败项) | 代码一致性检查 |

### 3.2 P1 级别问题 (应该修复)

| ID | 问题描述 | 影响 | 修复方案 | 验证方法 |
|----|---------|------|---------|---------|
| GAP-06 | Cookie 冷却时长未定义具体值 | 冷却策略不明确 | 定义 COOLING_DURATION_MINUTES=30 | 常量检查 |
| GAP-07 | 心跳更新机制未实现 | 长时间执行被误判超时 | 添加定期心跳更新节点 | 长任务测试 |
| GAP-08 | 超时配置表 §3.4 未被 API 代码引用 | 超时值硬编码 | 将超时值提取为配置 | 代码审查 |
| GAP-09 | trace_id 在 exec_meta 中字段名不一致 | 追踪困难 | 统一为 workflow_trace_id | 字段名一致性 |

### 3.3 修订版本

```yaml
# GAP-01 修复
tbl_candidate:
  add_field:
    name: retry_count
    type: int
    default: 0

# GAP-02 修复
constants:
  EXECUTION_LOCK_TIMEOUT_MINUTES: 30
  RECORD_LOCK_TIMEOUT_MINUTES: 30
  RECOVERY_INTERVAL_MINUTES: 15

# GAP-05 修复
ERROR_CONFIG:
  PARTIAL_FAIL:
    retryable: true  # 修正: 失败项可重试
    http_status: 207

# GAP-06 修复
cookie_config:
  COOLING_DURATION_MINUTES: 30
  MAX_CONSECUTIVE_ERRORS: 3
  MAX_TOTAL_ERRORS: 10
```

---

## 4. 测试计划

### 4.1 Day 1 测试用例

| 测试ID | 测试目标 | 前置条件 | 步骤 | 预期结果 | 证据 |
|--------|---------|---------|------|---------|------|
| T1-01 | tbl_cookie 表结构 | 飞书已授权 | 查询表字段 | 16个字段全部存在 | 字段列表截图 |
| T1-02 | tbl_candidate 表结构 | 飞书已授权 | 查询表字段 | 19个字段全部存在 | 字段列表截图 |
| T1-03 | tbl_source 新增字段 | 表已存在 | 查询新字段 | 7个新字段存在 | 字段列表截图 |
| T1-04 | tbl_crawl_execution 表结构 | 飞书已授权 | 查询表字段 | 10个字段全部存在 | 字段列表截图 |
| T1-05 | Cookie 状态机转换 | Cookie 已添加 | 模拟错误 | 状态按规则转换 | 状态变化日志 |
| T1-06 | API 响应信封格式 | API 运行中 | 调用 /api/note/detail | 返回 success/data/error/meta | 响应 JSON |
| T1-07 | 错误码枚举完整 | API 代码 | 检查 ErrorCode | 15种错误码 | 代码截图 |
| T1-08 | 部分失败响应 | Mock 超时 | 3条请求1条超时 | items[2].success=false | 响应 JSON |
| T1-09 | Cookie 加密 | MASTER_KEY 已设 | 加密→解密 | 明文一致 | 单元测试 |
| T1-10 | 安全审计通过 | 代码已提交 | 运行审计脚本 | passed=true | 脚本输出 |

### 4.2 Day 2 测试用例

| 测试ID | 测试目标 | 前置条件 | 步骤 | 预期结果 | 证据 |
|--------|---------|---------|------|---------|------|
| T2-01 | 执行锁获取 | 工作流存在 | 启动工作流 | locked=true | 节点输出 |
| T2-02 | 执行锁防重入 | 有运行中执行 | 再次启动 | locked=false | 节点输出 |
| T2-03 | 记录锁获取 | pending 记录存在 | 执行锁定节点 | 记录变为 processing | 表状态 |
| T2-04 | 记录锁防并发 | 2个执行同时 | 抢同一记录 | 仅1个成功 | 锁定结果 |
| T2-05 | 幂等写入-新建 | 记录不存在 | 写入 | action=created | 节点输出 |
| T2-06 | 幂等写入-跳过 | 记录已存在 | 再次写入 | action=skipped | 节点输出 |
| T2-07 | request_id 贯穿 | 完整流程 | 执行采集 | 日志可 grep 到 | 日志内容 |
| T2-08 | 超时回收-执行锁 | 执行超时 | 等待+触发回收 | status=timeout | 表状态 |
| T2-09 | 超时回收-记录锁 | 记录锁超时 | 等待+触发回收 | status=pending | 表状态 |
| T2-10 | 日志脱敏 | 有 Cookie 操作 | 检查日志 | 无明文 Cookie | grep 结果 |

### 4.3 Day 3 测试用例

| 测试ID | 测试目标 | 前置条件 | 步骤 | 预期结果 | 证据 |
|--------|---------|---------|------|---------|------|
| T3-01 | 告警-Cookie耗尽 | active=0 | 触发检查 | 收到 P0 告警 | 飞书消息 |
| T3-02 | 告警-成功率低 | Mock 失败 | 10min 低于90% | 收到 P1 告警 | 飞书消息 |
| T3-03 | 告警-处理积压 | pending>500 | 30min 后 | 收到 P2 告警 | 飞书消息 |
| T3-04 | 完整采集流程 | 关键词+Cookie | 执行工作流 | 数据写入成功 | 表记录 |
| T3-05 | Cookie 轮换 | 多个 Cookie | 第一个失败 | 自动切换 | 日志 |
| T3-06 | 回滚验证 | 有变更 | 执行回滚 | 旧工作流正常 | 功能验证 |

### 4.4 故障注入测试

| 测试ID | 故障类型 | 注入方式 | 预期行为 | 验证点 |
|--------|---------|---------|---------|--------|
| TF-01 | API 超时 | Mock 延迟 | 返回 TIMEOUT_ERROR, retryable=true | 错误码正确 |
| TF-02 | Cookie 失效 | 设置无效 Cookie | 返回 COOKIE_INVALID, 自动切换 | 切换日志 |
| TF-03 | 飞书 API 失败 | Mock 503 | 工作流优雅退出 | 不崩溃 |
| TF-04 | 执行中断 | Kill 进程 | 下次启动回收锁 | 锁状态恢复 |
| TF-05 | 并发抢锁 | 同时启动5个 | 仅1个成功 | 锁定计数=1 |

---

## 5. n8n 导入指南

### 5.1 环境变量配置

```bash
# n8n 环境变量
FEISHU_BASE_URL=https://open.feishu.cn/open-apis
FEISHU_APP_TOKEN=<your_app_token>
FEISHU_ACCESS_TOKEN=<your_access_token>
FEISHU_WEBHOOK_URL=<your_webhook_url>

# 表 ID
TBL_COOKIE=<table_id>
TBL_CANDIDATE=<table_id>
TBL_SOURCE=<table_id>
TBL_CRAWL_EXECUTION=<table_id>

# API 配置
CRAWLER_API_URL=http://localhost:8080

# 常量
LOCK_TIMEOUT_MINUTES=30
BATCH_SIZE=10
```

### 5.2 工作流创建步骤

#### WF-采集主流程

```yaml
步骤:
  1. 创建新工作流, 命名为 "WF-采集主流程"
  2. 添加触发器: Schedule Trigger (每5分钟)
  3. 添加节点: "初始化追踪" (Code)
     - 复制 §M3.6 代码
  4. 添加节点: "获取执行锁" (Code)
     - 复制 §M3.2 代码
     - 设置 WORKFLOW_NAME = "WF-采集"
  5. 添加节点: "检查锁结果" (IF)
     - 条件: {{$json.locked}} = true
  6. 添加节点: "获取并锁定记录" (Code)
     - 复制 §M3.3 代码
  7. 添加节点: "调用采集API" (HTTP Request)
     - Method: POST
     - URL: {{$env.CRAWLER_API_URL}}/api/note/detail
     - Headers: X-Request-ID = {{trace_id}}-detail
  8. 添加节点: "处理批量结果" (Code)
     - 复制 §M3.5 代码
  9. 添加节点: "幂等写入" (Code)
     - 复制 §M3.4 代码
  10. 添加节点: "释放执行锁" (Code)
  11. 连接所有节点
  12. 保存并激活

验证:
  - 手动执行一次
  - 检查 tbl_crawl_execution 有新记录
  - 检查日志包含 trace_id
```

#### WF-锁超时回收

```yaml
步骤:
  1. 创建新工作流, 命名为 "WF-锁超时回收"
  2. 添加触发器: Schedule Trigger (每15分钟)
  3. 添加节点: "回收超时锁" (Code)
     - 复制原文 §5.6 代码
  4. 保存并激活

验证:
  - 手动创建一条超时的执行锁记录
  - 手动触发工作流
  - 验证状态变为 timeout
```

### 5.3 验证清单

```yaml
导入后验证:
  □ 所有环境变量已设置
  □ 飞书 API 可访问 (测试获取记录)
  □ Crawler API 可访问 (测试 /health)
  □ 工作流可手动触发
  □ 执行锁正常获取/释放
  □ 日志包含 trace_id
```

---

## 6. AI 执行路线图

### Day 1 任务包

```yaml
D1-Task1: 数据层
  改动文件:
    - 飞书多维表格 (手动创建)
  交付物:
    - tbl_cookie 表 (16字段)
    - tbl_candidate 表 (19字段)
    - tbl_crawl_execution 表 (10字段)
    - tbl_source 新增字段 (7字段)
  验收:
    - T1-01 ~ T1-04 全部通过
  回滚:
    - 删除新表
    - 从 tbl_source 删除新字段

D1-Task2: API 响应模型
  改动文件:
    - media_crawler_api/models/response.py
    - media_crawler_api/models/request.py
  交付物:
    - ErrorCode 枚举 (15种)
    - ERROR_CONFIG 映射
    - APIResponse / BatchResponse 模型
  验收:
    - T1-06 ~ T1-08 全部通过
  回滚:
    - git revert

D1-Task3: Cookie 加密
  改动文件:
    - media_crawler_api/utils/crypto.py
  交付物:
    - CookieEncryption 类
    - encrypt/decrypt 方法
  验收:
    - T1-09 通过
    - 单元测试通过
  回滚:
    - git revert

D1-Task4: 安全审计
  改动文件:
    - scripts/security_audit.py
  交付物:
    - 审计脚本
  验收:
    - T1-10 通过 (passed=true)
  回滚:
    - 无需回滚
```

### Day 2 任务包

```yaml
D2-Task1: n8n 执行锁
  改动文件:
    - n8n 工作流 (UI 创建)
  交付物:
    - "获取执行锁" 节点
    - "释放执行锁" 节点
  验收:
    - T2-01, T2-02 通过
  回滚:
    - 删除节点

D2-Task2: n8n 记录锁
  改动文件:
    - n8n 工作流 (UI 创建)
  交付物:
    - "获取并锁定记录" 节点
  验收:
    - T2-03, T2-04 通过
  回滚:
    - 删除节点

D2-Task3: 幂等写入
  改动文件:
    - n8n 工作流 (UI 创建)
  交付物:
    - "幂等写入" 节点
  验收:
    - T2-05, T2-06 通过
  回滚:
    - 删除节点

D2-Task4: 超时回收工作流
  改动文件:
    - n8n 新工作流
  交付物:
    - WF-锁超时回收 工作流
  验收:
    - T2-08, T2-09 通过
  回滚:
    - 删除工作流

D2-Task5: 日志脱敏
  改动文件:
    - media_crawler_api/utils/logging.py
  交付物:
    - sanitize_log 函数
    - SanitizedFormatter 类
  验收:
    - T2-10 通过
  回滚:
    - git revert
```

### Day 3 任务包

```yaml
D3-Task1: 告警实现
  改动文件:
    - media_crawler_api/utils/alerting.py
  交付物:
    - send_alert 函数
    - 3条核心告警检查函数
  验收:
    - T3-01 ~ T3-03 通过
  回滚:
    - git revert

D3-Task2: 集成测试
  改动文件:
    - tests/integration/
  交付物:
    - 完整流程测试脚本
  验收:
    - T3-04 ~ T3-06 通过
  回滚:
    - 无需回滚

D3-Task3: 文档与Runbook
  改动文件:
    - docs/RUNBOOK.md
  交付物:
    - 运维手册
    - 告警处理步骤
  验收:
    - 文档完整性审查
  回滚:
    - 无需回滚
```

### 灰度期间检查脚本

```bash
#!/bin/bash
# daily_check.sh - 每日灰度检查

echo "=== 灰度检查 $(date) ==="

# 1. API 成功率
SUCCESS_RATE=$(curl -s http://localhost:8080/metrics | jq '.requests.success_rate')
echo "API 成功率: $SUCCESS_RATE"
[ $(echo "$SUCCESS_RATE < 0.95" | bc) -eq 1 ] && echo "⚠️ 成功率低于95%"

# 2. Cookie 使用率
COOKIE_USAGE=$(curl -s http://localhost:8080/metrics | jq '.cookies.daily_usage_rate')
echo "Cookie 使用率: $COOKIE_USAGE"
[ $(echo "$COOKIE_USAGE > 0.8" | bc) -eq 1 ] && echo "⚠️ Cookie使用率高于80%"

# 3. 处理积压
# (需要查询飞书表)

# 4. 日志敏感信息检查
grep -E "web_session=|a1=" /var/log/mediacrawler/*.log && echo "❌ 发现敏感信息!" || echo "✅ 日志脱敏正常"

echo "=== 检查完成 ==="
```

---

## 附录: 常量汇总

```yaml
# 锁超时
EXECUTION_LOCK_TIMEOUT_MINUTES: 30
RECORD_LOCK_TIMEOUT_MINUTES: 30
RECOVERY_INTERVAL_MINUTES: 15

# Cookie 管理
COOLING_DURATION_MINUTES: 30
MAX_CONSECUTIVE_ERRORS: 3
MAX_TOTAL_ERRORS: 10
DEFAULT_DAILY_LIMIT: 100

# API 超时
SEARCH_TIMEOUT_SECONDS: 30
DETAIL_SINGLE_TIMEOUT_SECONDS: 15
DETAIL_BATCH_TIMEOUT_SECONDS: 60
HEALTH_TIMEOUT_SECONDS: 5

# 重试策略
MAX_RETRY_NETWORK_ERROR: 3
MAX_RETRY_PLATFORM_ERROR: 2
MAX_RETRY_TIMEOUT_ERROR: 2
BACKOFF_SEQUENCE: [5, 15, 45]  # seconds

# 批量处理
DEFAULT_BATCH_SIZE: 10
MAX_BATCH_SIZE: 20

# 告警冷却
ALERT_COOLDOWN_P0_MINUTES: 5
ALERT_COOLDOWN_P1_MINUTES: 15
ALERT_COOLDOWN_P2_MINUTES: 60

# 幂等键
IDEMPOTENCY_KEY_VERSION: "v1"
```

---

> **文档结束**
>
> 此文档为 AI 可执行规格，AI 应按照:
> 1. Day1/Day2/Day3 任务包顺序执行
> 2. 每个任务完成后运行对应测试用例
> 3. 测试失败则修复后重新验证
> 4. 所有测试通过后进入下一任务
> 5. Day3 全部完成后进入灰度
