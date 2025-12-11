# 发布调度工作流设计文档

> 项目代号: XHS_AutoPublisher_v2
> 工作流: publish_scheduler_v1 + sub_publish
> 版本: v1.0 | 创建日期: 2024-12-11

---

## 目录

1. [概述](#1-概述)
2. [发布调度主工作流 publish_scheduler_v1](#2-发布调度主工作流-publish_scheduler_v1)
3. [发布子工作流 sub_publish](#3-发布子工作流-sub_publish)
4. [MCP 调用示例](#4-mcp-调用示例)
5. [状态机与限频策略](#5-状态机与限频策略)
6. [错误处理与重试](#6-错误处理与重试)

---

## 1. 概述

### 1.1 功能目标

自动将 `content_records` 表中已审核通过（`status = APPROVED`）的内容，通过 xiaohongshu-mcp 发布到小红书平台。

### 1.2 发布策略

| 策略 | 规则 |
|------|------|
| 单账号每日上限 | 3 篇 |
| 发布间隔 | ≥ 4 小时 |
| 内容选取 | 按 `priority_score` 降序 |
| 发布窗口 | 每小时检查一次，08:00-22:00 |

### 1.3 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                  publish_scheduler_v1 (主工作流)                  │
├─────────────────────────────────────────────────────────────────┤
│  Schedule_Trigger (每小时)                                        │
│       ↓                                                          │
│  Check_Publish_Window (08:00-22:00)                              │
│       ↓                                                          │
│  Query_Pending_Content (status=APPROVED, priority_score DESC)    │
│       ↓                                                          │
│  Query_All_Accounts                                              │
│       ↓                                                          │
│  Select_Available_Account (限频检查)                              │
│       ↓                                                          │
│  ┌─ No Account → Log_No_Account → End                           │
│  └─ Has Account → Execute_Sub_Publish                           │
│                        ↓                                         │
│                   sub_publish (子工作流)                          │
│                        ↓                                         │
│                   Log_Result → Notify_Telegram                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 发布调度主工作流 publish_scheduler_v1

### 2.1 触发方式

```javascript
// Schedule_Trigger 节点配置
{
  "trigger": {
    "rule": {
      "interval": [{ "field": "hours", "every": 1 }]
    }
  },
  "timezone": "Asia/Shanghai"
}
```

**说明**：每小时触发一次，由后续节点判断是否在发布窗口内。

### 2.2 节点流程图

```
┌──────────────────┐
│ Schedule_Trigger │ ─────→ 每小时触发
└────────┬─────────┘
         ↓
┌──────────────────────┐
│ Check_Publish_Window │ ─────→ 判断当前时间是否在 08:00-22:00
└────────┬─────────────┘
         ↓
    ┌────┴────┐
    │ IF节点  │
    └────┬────┘
    ↓ True         ↓ False
┌────────────┐  ┌──────────┐
│ Continue   │  │ End_Early│ → 不在发布窗口，直接结束
└────┬───────┘  └──────────┘
     ↓
┌──────────────────────┐
│ Query_Pending_Content│ ─────→ 查询待发布内容
└────────┬─────────────┘
         ↓
┌────────────────────┐
│ Query_All_Accounts │ ─────→ 查询所有账号
└────────┬───────────┘
         ↓
┌─────────────────────────┐
│ Select_Available_Account│ ─────→ 选择可用账号（限频检查）
└────────┬────────────────┘
         ↓
    ┌────┴────┐
    │ IF节点  │
    └────┬────┘
    ↓ Has Account      ↓ No Account
┌────────────────┐  ┌─────────────────┐
│Execute_Sub_Pub │  │ Log_No_Account  │ → 无可用账号，记录日志
└────────┬───────┘  └─────────────────┘
         ↓
┌──────────────────┐
│ Log_Publish_Result│
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Notify_Telegram  │
└──────────────────┘
```

### 2.3 核心节点详解

#### 2.3.1 Check_Publish_Window

```javascript
// Function 节点：检查发布窗口
const now = new Date();
const hour = now.getHours();

// 发布窗口：08:00 - 22:00
const isWithinWindow = hour >= 8 && hour < 22;

return {
  json: {
    is_within_window: isWithinWindow,
    current_hour: hour,
    timestamp: now.toISOString()
  }
};
```

#### 2.3.2 Query_Pending_Content

```javascript
// HTTP Request 节点：查询飞书待发布内容
// Method: POST
// URL: https://open.feishu.cn/open-apis/bitable/v1/apps/{{$env.LARK_APP_TOKEN}}/tables/{{$env.LARK_TABLE_CONTENT}}/records/search

// Request Body:
{
  "filter": {
    "conjunction": "and",
    "conditions": [
      {
        "field_name": "status",
        "operator": "is",
        "value": ["APPROVED"]
      }
    ]
  },
  "sort": [
    {
      "field_name": "priority_score",
      "desc": true
    },
    {
      "field_name": "created_at",
      "desc": false
    }
  ],
  "page_size": 10
}
```

**筛选条件**：
- `status = 'APPROVED'`：已审核通过
- 按 `priority_score` 降序排列
- 同分时按 `created_at` 升序（先创建的先发）

#### 2.3.3 Query_All_Accounts

```javascript
// HTTP Request 节点：查询所有账号
// Method: POST
// URL: https://open.feishu.cn/open-apis/bitable/v1/apps/{{$env.LARK_APP_TOKEN}}/tables/{{$env.LARK_TABLE_ACCOUNTS}}/records/search

// Request Body:
{
  "page_size": 100
}
```

#### 2.3.4 Select_Available_Account

```javascript
// Function 节点：选择可用账号

const accounts = $json.accounts;
const now = new Date();
const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

// 筛选可用账号
const availableAccounts = accounts.filter(acc => {
  // 1. 状态必须是 ACTIVE
  if (acc.fields.status !== 'ACTIVE') {
    return false;
  }

  // 2. 今日发布数 < 3
  const publishCountToday = acc.fields.publish_count_today || 0;
  if (publishCountToday >= 3) {
    return false;
  }

  // 3. 距上次发布 > 4 小时
  const lastPublishAt = acc.fields.last_publish_at;
  if (lastPublishAt) {
    const lastTime = new Date(lastPublishAt);
    const hoursSinceLastPublish = (now - lastTime) / (1000 * 60 * 60);
    if (hoursSinceLastPublish < 4) {
      return false;
    }
  }

  // 4. 检查冷却时间
  const cooldownUntil = acc.fields.cooldown_until;
  if (cooldownUntil && new Date(cooldownUntil) > now) {
    return false;
  }

  return true;
});

// 无可用账号
if (availableAccounts.length === 0) {
  return {
    json: {
      has_available_account: false,
      reason: 'NO_AVAILABLE_ACCOUNT',
      checked_accounts: accounts.length
    }
  };
}

// 选择发布数最少的账号（负载均衡）
const selected = availableAccounts.sort(
  (a, b) => (a.fields.publish_count_today || 0) - (b.fields.publish_count_today || 0)
)[0];

return {
  json: {
    has_available_account: true,
    selected_account: {
      record_id: selected.record_id,
      id: selected.fields.id,
      name: selected.fields.name,
      status: selected.fields.status,
      publish_count_today: selected.fields.publish_count_today || 0,
      last_publish_at: selected.fields.last_publish_at
    }
  }
};
```

#### 2.3.5 Execute_Sub_Publish

```javascript
// Execute Workflow 节点配置
{
  "workflowId": "sub_publish",
  "mode": "execute",
  "waitForSubWorkflow": true,
  "workflowInputs": {
    "content": "={{ $('Query_Pending_Content').item.json.items[0] }}",
    "selected_account": "={{ $json.selected_account }}",
    "workflow_run_id": "={{ $execution.id }}"
  }
}
```

---

## 3. 发布子工作流 sub_publish

### 3.1 输入输出定义

**输入参数**：

```typescript
interface SubPublishInput {
  content: {
    record_id: string;
    fields: {
      id: string;
      title: string;
      content_body: string;
      tags: string[];
      image_url?: string;
    };
  };
  selected_account: {
    record_id: string;
    id: string;
    name: string;
    publish_count_today: number;
  };
  workflow_run_id: string;
}
```

**输出参数**：

```typescript
interface SubPublishOutput {
  success: boolean;
  content_id: string;
  account_id: string;
  published_at?: string;
  xhs_note_id?: string;  // 小红书笔记 ID
  error?: {
    code: string;
    message: string;
  };
}
```

### 3.2 节点流程图

```
┌──────────────┐
│    Input     │ ─────→ content + selected_account + workflow_run_id
└──────┬───────┘
       ↓
┌────────────────────────┐
│ Update_Status_Publishing│ ─────→ 更新 content_records.status = 'PUBLISHING'
└──────────┬─────────────┘
           ↓
┌──────────────────────┐
│ Prepare_MCP_Payload  │ ─────→ 构建 MCP 请求参数
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Call_MCP_Publish     │ ─────→ POST /tools/xhs_publish_note
└──────────┬───────────┘
           ↓
      ┌────┴────┐
      │ IF节点  │
      └────┬────┘
      ↓ Success        ↓ Failed
┌───────────────┐  ┌───────────────────┐
│Handle_Success │  │ Handle_Failure    │
└──────┬────────┘  └─────────┬─────────┘
       ↓                     ↓
┌───────────────────┐  ┌───────────────────┐
│Update_Content_Pub │  │Update_Content_Fail│ → status = 'FAILED'
│status='PUBLISHED' │  └─────────┬─────────┘
└──────┬────────────┘            ↓
       ↓                   ┌───────────────┐
┌────────────────────┐     │ Retry_Logic   │ → 重试 3 次
│Update_Account_Stats│     └───────────────┘
└──────┬─────────────┘
       ↓
┌──────────────┐
│    Output    │
└──────────────┘
```

### 3.3 核心节点详解

#### 3.3.1 Update_Status_Publishing

```javascript
// HTTP Request 节点：更新状态为 PUBLISHING
// Method: PUT
// URL: https://open.feishu.cn/open-apis/bitable/v1/apps/{{$env.LARK_APP_TOKEN}}/tables/{{$env.LARK_TABLE_CONTENT}}/records/{{$json.content.record_id}}

// Request Body:
{
  "fields": {
    "status": "PUBLISHING",
    "account_id": "{{ $json.selected_account.id }}"
  }
}
```

#### 3.3.2 Prepare_MCP_Payload

```javascript
// Function 节点：构建 MCP 请求参数

const content = $json.content.fields;
const account = $json.selected_account;

// 处理标签格式
const tags = Array.isArray(content.tags) ? content.tags : [];
const hashtagsText = tags.map(tag => `#${tag}`).join(' ');

// 构建发布内容
const noteContent = `${content.content_body}\n\n${hashtagsText}`;

return {
  json: {
    mcp_payload: {
      tool: "xhs_publish_note",
      arguments: {
        account_id: account.id,
        title: content.title,
        content: noteContent,
        images: content.image_url ? [content.image_url] : [],
        tags: tags
      }
    },
    content_id: content.id,
    content_record_id: $json.content.record_id,
    account_id: account.id,
    account_record_id: account.record_id
  }
};
```

#### 3.3.3 Call_MCP_Publish

```javascript
// HTTP Request 节点：调用 MCP 发布
// Method: POST
// URL: http://localhost:3000/tools/xhs_publish_note
// Headers:
//   Content-Type: application/json
//   Authorization: Bearer {{$env.MCP_API_KEY}}

// Request Body:
{
  "account_id": "{{ $json.mcp_payload.arguments.account_id }}",
  "title": "{{ $json.mcp_payload.arguments.title }}",
  "content": "{{ $json.mcp_payload.arguments.content }}",
  "images": {{ $json.mcp_payload.arguments.images }},
  "tags": {{ $json.mcp_payload.arguments.tags }}
}
```

#### 3.3.4 Handle_Success - Update_Content_Published

```javascript
// HTTP Request 节点：更新状态为 PUBLISHED
// Method: PUT
// URL: https://open.feishu.cn/open-apis/bitable/v1/apps/{{$env.LARK_APP_TOKEN}}/tables/{{$env.LARK_TABLE_CONTENT}}/records/{{$json.content_record_id}}

// Request Body:
{
  "fields": {
    "status": "PUBLISHED",
    "published_at": "{{ $now.toISOString() }}",
    "xhs_note_id": "{{ $json.mcp_response.note_id }}"
  }
}
```

#### 3.3.5 Update_Account_Stats

```javascript
// Function 节点：计算新的账号统计

const currentCount = $json.selected_account.publish_count_today || 0;
const newCount = currentCount + 1;
const now = new Date().toISOString();

return {
  json: {
    account_record_id: $json.account_record_id,
    update_fields: {
      publish_count_today: newCount,
      last_publish_at: now
    }
  }
};

// 后续 HTTP Request 节点执行更新
// Method: PUT
// URL: https://open.feishu.cn/open-apis/bitable/v1/apps/{{$env.LARK_APP_TOKEN}}/tables/{{$env.LARK_TABLE_ACCOUNTS}}/records/{{$json.account_record_id}}
```

#### 3.3.6 Handle_Failure

```javascript
// Function 节点：处理发布失败

const error = $json.error || { code: 'UNKNOWN', message: 'Unknown error' };
const retryCount = $json.retry_count || 0;
const maxRetries = 3;

// 判断是否可重试
const retryableErrors = ['TIMEOUT', 'RATE_LIMIT', 'NETWORK_ERROR'];
const canRetry = retryableErrors.includes(error.code) && retryCount < maxRetries;

return {
  json: {
    can_retry: canRetry,
    retry_count: retryCount + 1,
    error: error,
    should_mark_failed: !canRetry
  }
};
```

---

## 4. MCP 调用示例

### 4.1 MCP 服务信息

| 配置项 | 值 |
|--------|-----|
| 服务名 | xiaohongshu-mcp |
| 管理方式 | pm2 |
| 监听地址 | http://localhost:3000 |
| 工具名 | xhs_publish_note |

### 4.2 HTTP 请求示例

#### 请求

```http
POST /tools/xhs_publish_note HTTP/1.1
Host: localhost:3000
Content-Type: application/json
Authorization: Bearer {{MCP_API_KEY}}

{
  "account_id": "acc_001",
  "title": "我用 3 个自动化流程，把每天 4 小时重复工作干没了",
  "content": "去年双十一之前，我差点被素材脚本干崩溃。每天要写 10 多条短视频文案，写到后面脑子都是浆糊——不是重复几个老梗，就是完全没有情绪张力。\n\n直到那次我抱着「死马当活马医」的心态，试了下用 AI 批量写脚本，结果非常出乎意料。\n\n1️⃣ 第一个流程：每日数据自动汇总\n以前每天下班前要花 30 分钟手动导数据、整理、发给领导。现在 n8n 每天 18:00 自动跑，我只需要看一眼确认就行。\n\n2️⃣ 第二个流程：素材脚本批量生成\n我让 AI 一次性写 30 条，自己挑 10 条精修。效率翻了 3 倍，质量反而更稳定。\n\n3️⃣ 第三个流程：评论自动回复\n高频问题用预设话术自动回，真人只处理复杂问题。回复率从 60% 提升到 95%。\n\n如果你也想从重复劳动里解脱出来，可以先挑一件最机械的事情，从这一个小流程开始。\n\n评论区告诉我，你最想自动化的是哪件事？\n\n#AI自动化 #n8n #运营提效 #工作流 #效率工具 #打工人必看 #职场干货 #自动化办公",
  "images": [
    "https://example.com/cover-image.jpg"
  ],
  "tags": ["AI自动化", "n8n", "运营提效", "工作流", "效率工具", "打工人必看", "职场干货", "自动化办公"]
}
```

#### 成功响应

```json
{
  "success": true,
  "data": {
    "note_id": "xhs_note_64a1b2c3d4e5f6",
    "note_url": "https://www.xiaohongshu.com/explore/64a1b2c3d4e5f6",
    "published_at": "2024-12-11T10:30:00.000Z",
    "account_id": "acc_001"
  },
  "message": "Note published successfully"
}
```

#### 失败响应

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT",
    "message": "Publishing rate limit exceeded. Please try again later.",
    "retry_after": 3600
  }
}
```

### 4.3 N8N HTTP Request 节点完整配置

```javascript
// HTTP Request 节点配置
{
  "method": "POST",
  "url": "http://localhost:3000/tools/xhs_publish_note",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "Content-Type",
        "value": "application/json"
      }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "account_id",
        "value": "={{ $json.mcp_payload.arguments.account_id }}"
      },
      {
        "name": "title",
        "value": "={{ $json.mcp_payload.arguments.title }}"
      },
      {
        "name": "content",
        "value": "={{ $json.mcp_payload.arguments.content }}"
      },
      {
        "name": "images",
        "value": "={{ $json.mcp_payload.arguments.images }}"
      },
      {
        "name": "tags",
        "value": "={{ $json.mcp_payload.arguments.tags }}"
      }
    ]
  },
  "options": {
    "timeout": 30000,
    "response": {
      "response": {
        "fullResponse": true
      }
    }
  }
}
```

---

## 5. 状态机与限频策略

### 5.1 内容状态流转

```
                    ┌──────────────┐
                    │   APPROVED   │ ← 由 content_generator_v1 写入
                    └──────┬───────┘
                           │
                           ↓ publish_scheduler_v1 选中
                    ┌──────────────┐
                    │  PUBLISHING  │ ← 发布中（乐观锁）
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              ↓ MCP 成功                 ↓ MCP 失败（3次重试后）
       ┌──────────────┐          ┌──────────────┐
       │  PUBLISHED   │          │    FAILED    │
       └──────────────┘          └──────┬───────┘
                                        │
                                        ↓ 人工处理后
                                 ┌──────────────┐
                                 │   APPROVED   │ ← 重新进入队列
                                 └──────────────┘
```

### 5.2 账号状态说明

| 状态 | 说明 | 可发布 |
|------|------|--------|
| ACTIVE | 正常 | ✅ |
| COOLDOWN | 冷却中（自动恢复） | ❌ |
| SUSPENDED | 人工暂停 | ❌ |
| BANNED | 封禁（需人工处理） | ❌ |

### 5.3 限频检查逻辑

```javascript
// 账号可用性判断伪代码
function isAccountAvailable(account, now) {
  // 1. 状态检查
  if (account.status !== 'ACTIVE') {
    return { available: false, reason: 'STATUS_NOT_ACTIVE' };
  }

  // 2. 今日发布数检查
  if (account.publish_count_today >= 3) {
    return { available: false, reason: 'DAILY_LIMIT_REACHED' };
  }

  // 3. 发布间隔检查
  if (account.last_publish_at) {
    const hoursSince = (now - new Date(account.last_publish_at)) / (1000 * 60 * 60);
    if (hoursSince < 4) {
      return {
        available: false,
        reason: 'INTERVAL_TOO_SHORT',
        next_available_at: new Date(account.last_publish_at).getTime() + 4 * 60 * 60 * 1000
      };
    }
  }

  // 4. 冷却时间检查
  if (account.cooldown_until && new Date(account.cooldown_until) > now) {
    return {
      available: false,
      reason: 'IN_COOLDOWN',
      cooldown_until: account.cooldown_until
    };
  }

  return { available: true };
}
```

### 5.4 每日计数重置

需要一个独立的定时任务（或工作流）在每天 00:00 重置所有账号的 `publish_count_today`：

```javascript
// Reset_Daily_Count 工作流（每天 00:00 触发）

// 1. 查询所有账号
// 2. 批量更新 publish_count_today = 0

// 飞书批量更新 API
// POST /bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update
{
  "records": [
    {
      "record_id": "rec_xxx",
      "fields": {
        "publish_count_today": 0
      }
    }
    // ... 其他账号
  ]
}
```

---

## 6. 错误处理与重试

### 6.1 错误分类

| 错误类型 | 错误码 | 可重试 | 处理方式 |
|----------|--------|--------|----------|
| 网络超时 | TIMEOUT | ✅ | 指数退避重试 |
| 限流 | RATE_LIMIT | ✅ | 等待 retry_after 后重试 |
| 账号异常 | ACCOUNT_ERROR | ❌ | 标记账号为 SUSPENDED |
| 内容违规 | CONTENT_VIOLATION | ❌ | 标记内容为 FAILED |
| MCP 服务不可用 | SERVICE_UNAVAILABLE | ✅ | 等待后重试 |

### 6.2 重试策略

```javascript
// 重试配置
const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 30000,

  // 指数退避计算
  getDelay: function(retryCount) {
    const delay = this.baseDelayMs * Math.pow(2, retryCount);
    return Math.min(delay, this.maxDelayMs);
  }
};

// 重试逻辑
async function retryPublish(content, account, retryCount = 0) {
  try {
    return await callMCPPublish(content, account);
  } catch (error) {
    if (!isRetryable(error) || retryCount >= RETRY_CONFIG.maxRetries) {
      throw error;
    }

    const delay = RETRY_CONFIG.getDelay(retryCount);
    await sleep(delay);

    return retryPublish(content, account, retryCount + 1);
  }
}
```

### 6.3 告警通知

发布失败时通过 Telegram 发送告警：

```javascript
// Telegram 告警消息模板
const alertMessage = `
🚨 *发布失败告警*

📝 内容ID: ${contentId}
📌 标题: ${title}
👤 账号: ${accountName}
❌ 错误: ${errorCode} - ${errorMessage}
🔄 重试次数: ${retryCount}/${maxRetries}
⏰ 时间: ${timestamp}

请检查 execution_logs 获取详细信息。
`;
```

---

## 7. 环境变量配置

```bash
# MCP 服务配置
MCP_HOST=http://localhost:3000
MCP_API_KEY=your_mcp_api_key

# 发布策略配置
PUBLISH_DAILY_LIMIT=3
PUBLISH_INTERVAL_HOURS=4
PUBLISH_WINDOW_START=8
PUBLISH_WINDOW_END=22

# 重试配置
PUBLISH_MAX_RETRIES=3
PUBLISH_BASE_DELAY_MS=1000
```

---

## 8. 日志记录

### 8.1 关键日志事件

| event_type | level | 触发时机 |
|------------|-------|----------|
| PUBLISH_SCHEDULER_START | INFO | 调度工作流开始 |
| NO_PENDING_CONTENT | INFO | 无待发布内容 |
| NO_AVAILABLE_ACCOUNT | WARN | 无可用账号 |
| PUBLISH_START | INFO | 开始发布 |
| PUBLISH_SUCCESS | INFO | 发布成功 |
| PUBLISH_FAILED | ERROR | 发布失败 |
| PUBLISH_RETRY | WARN | 发布重试 |
| ACCOUNT_STATUS_CHANGED | INFO | 账号状态变更 |

### 8.2 日志示例

```json
{
  "timestamp": "2024-12-11T10:30:00.000Z",
  "level": "INFO",
  "workflow_id": "publish_scheduler_v1",
  "workflow_run_id": "exec_abc123",
  "node_name": "Call_MCP_Publish",
  "event_type": "PUBLISH_SUCCESS",
  "message": "内容发布成功",
  "context": {
    "content_id": "content_001",
    "account_id": "acc_001",
    "xhs_note_id": "xhs_note_64a1b2c3d4e5f6",
    "publish_duration_ms": 2350
  }
}
```

---

> 文档维护：每次工作流结构变更后需同步更新本文档
