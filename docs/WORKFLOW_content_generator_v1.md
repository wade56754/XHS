# N8N 工作流配置说明: content_generator_v1

> 项目代号: XHS_AutoPublisher_v2 | MVP 阶段
> 版本: v1.0 | 最后更新: 2024-12-11

---

## 目录

1. [工作流总览](#1-工作流总览)
2. [节点清单](#2-节点清单)
3. [节点配置详情](#3-节点配置详情)
4. [AI_Gateway 节点设计](#4-ai_gateway-节点设计)
5. [Save_To_Lark 节点配置](#5-save_to_lark-节点配置)
6. [sub_notify 子工作流](#6-sub_notify-子工作流)
7. [错误处理配置](#7-错误处理配置)

---

## 1. 工作流总览

### 1.1 基本信息

| 属性 | 值 |
|------|-----|
| **工作流名称** | content_generator_v1 |
| **职责** | 智能选题 → 内容生成 → 写入飞书 → 通知 |
| **触发方式** | Schedule Trigger (定时) + Manual Trigger (手动) |
| **预计执行时间** | 2-5 分钟/次 |

### 1.2 触发配置

**Schedule Trigger (定时触发)**
- 每天 9:00 和 15:00 执行
- Cron 表达式: `0 9,15 * * *`
- 时区: Asia/Shanghai

**Manual Trigger (手动触发)**
- 支持传入参数覆盖默认配置
- 参数: `keyword`, `content_style`, `test_mode`

### 1.3 数据流概览

```
┌─────────────────┐
│  Trigger        │ (Schedule / Manual)
└────────┬────────┘
         ▼
┌─────────────────┐
│  Fetch_Config   │ → 从飞书读取业务配置
└────────┬────────┘
         ▼
┌─────────────────┐
│  Fetch_Hot      │ → 从飞书读取最新热点
└────────┬────────┘
         ▼
┌─────────────────┐
│  AI_Gateway     │ → Claude: 生成选题 (TOPIC_GEN)
│  (Generate      │
│   Topics)       │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Select_Best    │ → 选择最佳选题
│  Topic          │
└────────┬────────┘
         ▼
┌─────────────────┐
│  AI_Gateway     │ → Claude: 生成内容 (CONTENT_GEN)
│  (Create        │
│   Content)      │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Prepare_Record │ → 组装 content_records 数据
└────────┬────────┘
         ▼
┌─────────────────┐
│  Save_To_Lark   │ → 写入飞书多维表格
└────────┬────────┘
         ▼
┌─────────────────┐
│  sub_notify     │ → 发送 Telegram 通知
└─────────────────┘
```

---

## 2. 节点清单

| 序号 | 节点名称 | 节点类型 | 说明 |
|------|----------|----------|------|
| 1 | Schedule_Trigger | Schedule Trigger | 定时触发 |
| 2 | Manual_Trigger | Manual Trigger | 手动触发（带参数） |
| 3 | Merge_Triggers | Merge | 合并两种触发方式的输出 |
| 4 | Set_Defaults | Set | 设置默认参数 |
| 5 | Fetch_Config | HTTP Request | 从飞书读取 business_config |
| 6 | Parse_Config | Function | 解析配置 JSON |
| 7 | Fetch_Hot_Topics | HTTP Request | 从飞书读取 hot_topics |
| 8 | AI_Gateway_Topics | HTTP Request | 调用 Claude 生成选题 |
| 9 | Parse_Topics | Function | 解析选题结果 |
| 10 | Select_Best_Topic | Function | 选择最佳选题 |
| 11 | AI_Gateway_Content | HTTP Request | 调用 Claude 生成内容 |
| 12 | Parse_Content | Function | 解析内容结果 |
| 13 | Prepare_Record | Function | 组装记录数据 |
| 14 | Save_To_Lark | HTTP Request | 写入 content_records |
| 15 | Execute_Sub_Notify | Execute Workflow | 调用 sub_notify |
| 16 | Log_Success | HTTP Request | 记录成功日志 |
| 17 | Error_Handler | Error Trigger | 全局错误处理 |

---

## 3. 节点配置详情

### 3.1 Schedule_Trigger

**节点类型**: Schedule Trigger

**配置**:
- Trigger Times: Add Cron
- Cron Expression: `0 9,15 * * *`
- Timezone: Asia/Shanghai

**输出数据**:
```json
{
  "trigger_type": "schedule",
  "timestamp": "2024-12-11T09:00:00.000Z"
}
```

---

### 3.2 Manual_Trigger

**节点类型**: Manual Trigger

**配置**:
- 启用 "Test Workflow" 时可传入参数

**输出数据** (示例):
```json
{
  "trigger_type": "manual",
  "keyword": "AI自动化",
  "content_style": "干货教程",
  "test_mode": false
}
```

---

### 3.3 Set_Defaults

**节点类型**: Set

**配置说明**: 设置默认参数，如果手动触发未传入则使用默认值

**配置字段**:
| 字段名 | 类型 | 值 |
|--------|------|-----|
| keyword | String | `{{ $json.keyword || "AI效率工具" }}` |
| content_style | String | `{{ $json.content_style || "干货教程" }}` |
| target_audience | String | `{{ $json.target_audience || "职场人" }}` |
| test_mode | Boolean | `{{ $json.test_mode || false }}` |
| workflow_run_id | String | `{{ $execution.id }}` |
| trigger_type | String | `{{ $json.trigger_type || "manual" }}` |

**输出数据**:
```json
{
  "keyword": "AI效率工具",
  "content_style": "干货教程",
  "target_audience": "职场人",
  "test_mode": false,
  "workflow_run_id": "exec_abc123",
  "trigger_type": "schedule"
}
```

---

### 3.4 Fetch_Config

**节点类型**: HTTP Request

**说明**: 从飞书 business_config 表读取业务配置

**配置**:
| 参数 | 值 |
|------|-----|
| Method | POST |
| URL | `https://open.feishu.cn/open-apis/bitable/v1/apps/{{ $env.LARK_APP_TOKEN }}/tables/{{ $env.LARK_TABLE_BUSINESS_CONFIG }}/records/search` |
| Authentication | None (手动设置 Header) |
| Headers | `Authorization`: `Bearer {{ $env.LARK_ACCESS_TOKEN }}` |
| | `Content-Type`: `application/json` |
| Body (JSON) | 见下方 |

**Request Body**:
```json
{
  "page_size": 100,
  "filter": {
    "conjunction": "and",
    "conditions": [
      {
        "field_name": "is_active",
        "operator": "is",
        "value": [true]
      }
    ]
  }
}
```

**输出数据** (飞书响应):
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "fields": {
          "config_key": "TARGET_KEYWORDS",
          "config_value": "[\"AI\", \"自动化\", \"效率\"]",
          "config_type": "keyword"
        }
      },
      {
        "fields": {
          "config_key": "AUTO_APPROVE_THRESHOLD",
          "config_value": "85",
          "config_type": "threshold"
        }
      }
    ]
  }
}
```

> **注意**: 需要先通过其他方式获取 LARK_ACCESS_TOKEN，或在工作流开头添加获取 Token 的节点。见 [附录: 获取飞书 Token](#附录-获取飞书-token)

---

### 3.5 Parse_Config

**节点类型**: Function

**说明**: 将飞书返回的配置列表解析为键值对象

**代码**:
```javascript
const items = $input.all()[0].json.data.items || [];
const config = {};

for (const item of items) {
  const key = item.fields.config_key;
  let value = item.fields.config_value;

  // 尝试解析 JSON
  try {
    value = JSON.parse(value);
  } catch (e) {
    // 保持原值
  }

  config[key] = value;
}

// 合并前一节点的参数
const params = $('Set_Defaults').item.json;

return [{
  json: {
    ...params,
    config: config,
    keywords: config.TARGET_KEYWORDS || [],
    content_directions: config.CONTENT_DIRECTIONS || [],
    auto_approve_threshold: parseInt(config.AUTO_APPROVE_THRESHOLD) || 85,
    relevance_threshold: parseInt(config.RELEVANCE_THRESHOLD) || 70
  }
}];
```

**输出数据**:
```json
{
  "keyword": "AI效率工具",
  "content_style": "干货教程",
  "target_audience": "职场人",
  "workflow_run_id": "exec_abc123",
  "config": {
    "TARGET_KEYWORDS": ["AI", "自动化", "效率"],
    "AUTO_APPROVE_THRESHOLD": 85
  },
  "keywords": ["AI", "自动化", "效率"],
  "auto_approve_threshold": 85
}
```

---

### 3.6 Fetch_Hot_Topics

**节点类型**: HTTP Request

**说明**: 从飞书 hot_topics 表读取最近 2 小时的热点

**配置**:
| 参数 | 值 |
|------|-----|
| Method | POST |
| URL | `https://open.feishu.cn/open-apis/bitable/v1/apps/{{ $env.LARK_APP_TOKEN }}/tables/{{ $env.LARK_TABLE_HOT_TOPICS }}/records/search` |
| Headers | `Authorization`: `Bearer {{ $env.LARK_ACCESS_TOKEN }}` |
| Body (JSON) | 见下方 |

**Request Body**:
```json
{
  "page_size": 20,
  "sort": [
    {
      "field_name": "hot_value",
      "desc": true
    }
  ]
}
```

**输出数据**:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "fields": {
          "title": "AI让打工人效率翻倍",
          "hot_value": 1234567,
          "source": "weibo"
        }
      }
    ]
  }
}
```

---

### 3.7 Prepare_Hot_Topics

**节点类型**: Function

**说明**: 提取热点标题列表供 AI 参考

**代码**:
```javascript
const items = $input.all()[0].json.data.items || [];
const hotTopics = items.map(item => ({
  title: item.fields.title,
  hot_value: item.fields.hot_value,
  source: item.fields.source
}));

const prevData = $('Parse_Config').item.json;

return [{
  json: {
    ...prevData,
    hot_topics: hotTopics,
    hot_topics_text: hotTopics.map(t => `- ${t.title} (${t.source})`).join('\n')
  }
}];
```

---

## 4. AI_Gateway 节点设计

### 4.1 设计原则

AI_Gateway 是统一的 Claude API 调用封装，支持：
- 不同的 `task_type` (TOPIC_GEN / CONTENT_GEN)
- 从环境变量读取 API Key
- 限频控制（1 秒间隔）
- 自动记录 Token 用量

### 4.2 AI_Gateway_Topics (生成选题)

**节点类型**: HTTP Request

**配置**:
| 参数 | 值 |
|------|-----|
| Method | POST |
| URL | `https://api.anthropic.com/v1/messages` |
| Headers | `x-api-key`: `{{ $env.CLAUDE_API_KEY }}` |
| | `anthropic-version`: `2023-06-01` |
| | `content-type`: `application/json` |
| Body (JSON) | 见下方 |

**Request Body**:
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 2000,
  "messages": [
    {
      "role": "user",
      "content": "你是一位资深小红书内容策划师。\n\n## 任务\n基于以下关键词生成3-5个小红书选题：\n\n**关键词**：{{ $json.keyword }}\n**目标受众**：{{ $json.target_audience }}\n**内容风格**：{{ $json.content_style }}\n\n## 当前热点参考\n{{ $json.hot_topics_text }}\n\n## 输出要求\n请以JSON格式输出，包含 topics 数组，每个选题包含：\n1. title: 标题(15-30字，带emoji)\n2. core_points: 3个核心卖点\n3. hook: 开头钩子\n4. score: 你对这个选题的评分(0-100)\n\n只输出JSON，不要其他内容。"
    }
  ]
}
```

**输出数据**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"topics\": [{\"title\": \"3个AI工具让我效率翻倍\", \"core_points\": [...], \"hook\": \"...\", \"score\": 85}]}"
    }
  ],
  "usage": {
    "input_tokens": 500,
    "output_tokens": 800
  }
}
```

---

### 4.3 Parse_Topics

**节点类型**: Function

**说明**: 解析 Claude 返回的选题 JSON

**代码**:
```javascript
const response = $input.all()[0].json;
const text = response.content[0].text;
const prevData = $('Prepare_Hot_Topics').item.json;

// 解析 JSON
let topics = [];
try {
  const parsed = JSON.parse(text);
  topics = parsed.topics || [];
} catch (e) {
  // 尝试从文本中提取 JSON
  const match = text.match(/\{[\s\S]*\}/);
  if (match) {
    topics = JSON.parse(match[0]).topics || [];
  }
}

// 记录 Token 用量
const usage = response.usage || {};

return [{
  json: {
    ...prevData,
    topics: topics,
    usage_topic_gen: usage,
    prompt_id: 'TOPIC_GEN',
    prompt_version: 'V1'
  }
}];
```

---

### 4.4 Select_Best_Topic

**节点类型**: Function

**说明**: 选择评分最高的选题

**代码**:
```javascript
const data = $input.all()[0].json;
const topics = data.topics || [];

// 按评分排序，选择最高分
const sortedTopics = topics.sort((a, b) => (b.score || 0) - (a.score || 0));
const bestTopic = sortedTopics[0] || null;

if (!bestTopic) {
  throw new Error('未能生成有效选题');
}

return [{
  json: {
    ...data,
    selected_topic: bestTopic,
    title: bestTopic.title,
    core_points: bestTopic.core_points,
    hook: bestTopic.hook,
    topic_score: bestTopic.score
  }
}];
```

---

### 4.5 AI_Gateway_Content (生成内容)

**节点类型**: HTTP Request

**配置**: 与 AI_Gateway_Topics 类似

**Request Body**:
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4000,
  "messages": [
    {
      "role": "user",
      "content": "你是一位小红书爆款内容创作者。\n\n## 任务\n基于以下选题创作小红书文章：\n\n**标题**：{{ $json.title }}\n**核心卖点**：{{ $json.core_points.join(', ') }}\n**目标受众**：{{ $json.target_audience }}\n**开头钩子**：{{ $json.hook }}\n\n## 内容结构\n1. 开头(50-100字)：用痛点/问题/故事引入\n2. 主体(600-900字)：3-5个要点，每点配案例\n3. 结尾(50-100字)：总结+互动引导\n\n## 风格要求\n- 口语化表达，像朋友聊天\n- 适当使用emoji(5-10个)\n- 段落短小，3-5行换段\n\n## 输出格式\n只输出JSON：\n{\"content\": \"正文内容\", \"tags\": [\"标签1\", ...], \"summary\": \"一句话总结\"}"
    }
  ]
}
```

---

### 4.6 Parse_Content

**节点类型**: Function

**说明**: 解析生成的内容

**代码**:
```javascript
const response = $input.all()[0].json;
const text = response.content[0].text;
const prevData = $('Select_Best_Topic').item.json;

let content = {};
try {
  content = JSON.parse(text);
} catch (e) {
  const match = text.match(/\{[\s\S]*\}/);
  if (match) {
    content = JSON.parse(match[0]);
  }
}

const usage = response.usage || {};

// 简单评分（MVP 阶段使用选题评分，后续接入完整 AI 审核）
const aiScore = prevData.topic_score || 75;

return [{
  json: {
    ...prevData,
    content_body: content.content || '',
    tags: content.tags || [],
    summary: content.summary || '',
    ai_score: aiScore,
    usage_content_gen: usage,
    content_prompt_id: 'CONTENT_GEN',
    content_prompt_version: 'V1'
  }
}];
```

---

### 4.7 限频控制 (可选增强)

如需添加限频控制，在 AI_Gateway 节点前添加 **Wait** 节点或使用 **Function** 节点：

**Function 节点代码**:
```javascript
// 获取上次调用时间
const lastCallTime = $getWorkflowStaticData('global').lastClaudeCall || 0;
const now = Date.now();
const minInterval = 1000; // 1秒

if (now - lastCallTime < minInterval) {
  const waitTime = minInterval - (now - lastCallTime);
  await new Promise(resolve => setTimeout(resolve, waitTime));
}

// 更新调用时间
const staticData = $getWorkflowStaticData('global');
staticData.lastClaudeCall = Date.now();

return $input.all();
```

---

## 5. Save_To_Lark 节点配置

### 5.1 Prepare_Record

**节点类型**: Function

**说明**: 组装要写入飞书的记录数据

**代码**:
```javascript
const data = $input.all()[0].json;
const uuid = require('uuid');

const record = {
  // 主键
  id: uuid.v4(),

  // 时间
  created_at: new Date().toISOString(),

  // 内容字段
  title: data.title,
  content_body: data.content_body,
  tags: data.tags,

  // 来源信息
  content_direction: data.content_style || '干货教程',
  topic_source: data.hot_topics?.length > 0 ? 'hot_trend' : 'ai',

  // 评分
  ai_score: data.ai_score,

  // 状态 (MVP 阶段简化：>=70 为 AI_REVIEWED)
  status: data.ai_score >= 70 ? 'AI_REVIEWED' : 'REJECTED',

  // 追踪字段
  workflow_run_id: data.workflow_run_id,
  prompt_id: data.content_prompt_id || 'CONTENT_GEN',
  prompt_version: data.content_prompt_version || 'V1'
};

// 判断是否使用测试表
const tableId = data.test_mode
  ? $env.LARK_TABLE_CONTENT_TEST
  : $env.LARK_TABLE_CONTENT;

return [{
  json: {
    ...data,
    record: record,
    table_id: tableId
  }
}];
```

**输出数据**:
```json
{
  "record": {
    "id": "uuid-xxx",
    "created_at": "2024-12-11T09:05:00.000Z",
    "title": "3个AI工具让我效率翻倍",
    "content_body": "...",
    "tags": ["AI", "效率", "工具"],
    "content_direction": "干货教程",
    "topic_source": "hot_trend",
    "ai_score": 85,
    "status": "AI_REVIEWED",
    "workflow_run_id": "exec_abc123",
    "prompt_id": "CONTENT_GEN",
    "prompt_version": "V1"
  },
  "table_id": "tblContentRecords"
}
```

---

### 5.2 Save_To_Lark

**节点类型**: HTTP Request

**配置**:
| 参数 | 值 |
|------|-----|
| Method | POST |
| URL | `https://open.feishu.cn/open-apis/bitable/v1/apps/{{ $env.LARK_APP_TOKEN }}/tables/{{ $json.table_id }}/records` |
| Headers | `Authorization`: `Bearer {{ $env.LARK_ACCESS_TOKEN }}` |
| | `Content-Type`: `application/json` |
| Body (JSON) | 见下方 |

**Request Body**:
```json
{
  "fields": {
    "id": "{{ $json.record.id }}",
    "created_at": {{ $json.record.created_at }},
    "title": "{{ $json.record.title }}",
    "content_body": "{{ $json.record.content_body }}",
    "tags": {{ $json.record.tags }},
    "content_direction": "{{ $json.record.content_direction }}",
    "topic_source": "{{ $json.record.topic_source }}",
    "ai_score": {{ $json.record.ai_score }},
    "status": "{{ $json.record.status }}",
    "workflow_run_id": "{{ $json.record.workflow_run_id }}",
    "prompt_id": "{{ $json.record.prompt_id }}",
    "prompt_version": "{{ $json.record.prompt_version }}"
  }
}
```

> **提示**: 日期字段需要转换为飞书要求的时间戳格式（毫秒）

---

## 6. sub_notify 子工作流

### 6.1 创建子工作流

在 N8N 中创建新工作流，命名为 `sub_notify`

### 6.2 子工作流输入

**节点类型**: Execute Workflow Trigger

**预期输入数据**:
```json
{
  "title": "3个AI工具让我效率翻倍",
  "ai_score": 85,
  "status": "AI_REVIEWED",
  "workflow_run_id": "exec_abc123",
  "content_direction": "干货教程"
}
```

### 6.3 Format_Message

**节点类型**: Function

**代码**:
```javascript
const data = $input.all()[0].json;

// 状态 emoji 映射
const statusEmoji = {
  'AI_REVIEWED': '✅',
  'REJECTED': '❌',
  'PUBLISHED': '🎉',
  'FAILED': '⚠️'
};

const emoji = statusEmoji[data.status] || '📝';

// 构建消息
const message = `${emoji} *内容生成完成*

📌 *标题*: ${data.title}

📊 *AI评分*: ${data.ai_score}/100
📁 *状态*: ${data.status}
🏷️ *方向*: ${data.content_direction}

🔗 执行ID: \`${data.workflow_run_id}\`

${data.ai_score >= 80 ? '👍 质量良好，可以发布' : data.ai_score >= 70 ? '⚡ 建议优化后发布' : '🔄 评分较低，建议重新生成'}`;

return [{
  json: {
    ...data,
    telegram_message: message
  }
}];
```

### 6.4 Send_Telegram

**节点类型**: Telegram (或 HTTP Request)

**方式 A: 使用 Telegram 节点**

| 参数 | 值 |
|------|-----|
| Resource | Message |
| Operation | Send Message |
| Chat ID | `{{ $env.TELEGRAM_CHAT_ID }}` |
| Text | `{{ $json.telegram_message }}` |
| Parse Mode | Markdown |

**方式 B: 使用 HTTP Request**

| 参数 | 值 |
|------|-----|
| Method | POST |
| URL | `https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage` |
| Body (JSON) | 见下方 |

**Request Body**:
```json
{
  "chat_id": "{{ $env.TELEGRAM_CHAT_ID }}",
  "text": "{{ $json.telegram_message }}",
  "parse_mode": "Markdown"
}
```

### 6.5 在主工作流中调用

**节点类型**: Execute Workflow

**配置**:
| 参数 | 值 |
|------|-----|
| Source | Database |
| Workflow | sub_notify |
| Mode | Wait for Sub-Workflow Completion |

**传入数据** (在 Prepare_Record 之后):
```json
{
  "title": "{{ $json.title }}",
  "ai_score": "{{ $json.ai_score }}",
  "status": "{{ $json.record.status }}",
  "workflow_run_id": "{{ $json.workflow_run_id }}",
  "content_direction": "{{ $json.record.content_direction }}"
}
```

---

## 7. 错误处理配置

### 7.1 节点级错误处理

对以下节点启用 **Continue On Fail**:
- Fetch_Hot_Topics（热点抓取失败时继续）
- AI_Gateway_Topics
- AI_Gateway_Content
- Save_To_Lark

**配置方式**:
节点 Settings → On Error → Continue (using error output)

### 7.2 Error_Handler (全局错误处理)

**节点类型**: Error Trigger

**连接**: 在工作流中添加 Error Trigger 节点

**后续节点**: Function → HTTP Request (发送错误通知)

**Function 代码**:
```javascript
const error = $input.all()[0].json;

const message = `🚨 *工作流执行失败*

📋 *工作流*: content_generator_v1
🔗 *执行ID*: ${error.execution?.id || 'unknown'}
❌ *错误节点*: ${error.node?.name || 'unknown'}
💬 *错误信息*: ${error.message || 'Unknown error'}

⏰ 时间: ${new Date().toISOString()}`;

return [{
  json: {
    telegram_message: message,
    error_details: error
  }
}];
```

---

## 附录: 获取飞书 Token

在工作流最开始添加获取 Token 的节点：

### Get_Lark_Token

**节点类型**: HTTP Request

**配置**:
| 参数 | 值 |
|------|-----|
| Method | POST |
| URL | `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal` |
| Body (JSON) | 见下方 |

**Request Body**:
```json
{
  "app_id": "{{ $env.LARK_APP_ID }}",
  "app_secret": "{{ $env.LARK_APP_SECRET }}"
}
```

**后续节点使用**:
```
{{ $('Get_Lark_Token').item.json.tenant_access_token }}
```

或使用 Set 节点将 Token 存储到变量中供后续节点使用。

---

## 环境变量清单

在 N8N 中配置以下环境变量:

| 变量名 | 说明 |
|--------|------|
| CLAUDE_API_KEY | Claude API 密钥 |
| LARK_APP_ID | 飞书应用 ID |
| LARK_APP_SECRET | 飞书应用密钥 |
| LARK_APP_TOKEN | 多维表格 App Token |
| LARK_TABLE_CONTENT | content_records 表 ID |
| LARK_TABLE_CONTENT_TEST | 测试表 ID |
| LARK_TABLE_HOT_TOPICS | hot_topics 表 ID |
| LARK_TABLE_BUSINESS_CONFIG | business_config 表 ID |
| TELEGRAM_BOT_TOKEN | Telegram Bot Token |
| TELEGRAM_CHAT_ID | Telegram Chat ID |

---

## 验证清单

配置完成后，按以下步骤验证:

- [ ] 手动触发工作流，检查每个节点输出
- [ ] 验证飞书 Token 获取正常
- [ ] 验证 Claude API 调用成功
- [ ] 验证数据正确写入飞书表格
- [ ] 验证 Telegram 通知发送成功
- [ ] 测试 test_mode=true 时写入测试表
- [ ] 验证错误处理和告警正常
