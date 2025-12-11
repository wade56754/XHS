# 飞书多维表格结构定义

> 项目代号: XHS_AutoPublisher_v2
> 版本: v1.0 | 最后更新: 2024-12-11

---

## 目录

1. [content_records - 内容记录表](#1-content_records---内容记录表)
2. [accounts - 账号管理表](#2-accounts---账号管理表)
3. [execution_logs - 执行日志表](#3-execution_logs---执行日志表)
4. [interaction_data - 互动数据表](#4-interaction_data---互动数据表)
5. [hot_topics - 热点话题表](#5-hot_topics---热点话题表)
6. [topic_candidates - 选题候选库](#6-topic_candidates---选题候选库)
7. [topic_history - 选题历史库](#7-topic_history---选题历史库)
8. [business_config - 业务配置表](#8-business_config---业务配置表)
9. [枚举值定义](#9-枚举值定义)

---

## 1. content_records - 内容记录表

**用途**: 存储所有生成的内容记录，包括标题、正文、评分、状态等核心数据。

**写入频率**: 每次内容生成时写入，状态变更时更新（约 1-10 次/天）

**环境变量**: `LARK_TABLE_CONTENT` / `LARK_TABLE_CONTENT_TEST`

| 字段名 | 飞书类型 | 必填 | 说明 |
|--------|----------|------|------|
| id | 单行文本 | ✅ | UUID 主键 |
| created_at | 日期 | ✅ | 创建时间 |
| content_direction | 单选 | ✅ | 内容方向（AI/效率/工具等） |
| topic_source | 单选 | ✅ | 选题来源：`ai` / `hot_trend` / `manual` |
| title | 单行文本 | ✅ | 标题（15-30字） |
| content_body | 多行文本 | ✅ | 正文内容（800-1200字） |
| tags | 多选 | ✅ | 标签数组（8-10个） |
| image_url | 附件 | ❌ | 封面/内容图片 URL |
| ai_score | 数字 | ✅ | AI 综合评分（0-100） |
| real_score | 数字 | ❌ | 真实评分（发布后计算） |
| prediction_error | 数字 | ❌ | 预测误差（real_score - ai_score） |
| status | 单选 | ✅ | 内容状态（见枚举） |
| published_at | 日期 | ❌ | 发布时间 |
| account_id | 关联 | ❌ | 关联的发布账号 |
| workflow_run_id | 单行文本 | ✅ | N8N 执行 ID（唯一） |
| prompt_id | 单行文本 | ✅ | 使用的 Prompt ID |
| prompt_version | 单行文本 | ✅ | 使用的 Prompt 版本 |
| views | 数字 | ❌ | 阅读量 |
| likes | 数字 | ❌ | 点赞数 |
| collects | 数字 | ❌ | 收藏数 |
| comments | 数字 | ❌ | 评论数 |

**典型查询**:
- 待审核列表: `status = 'AI_REVIEWED'` ORDER BY `created_at` DESC
- 今日发布: `published_at >= TODAY` AND `account_id = ?`
- 高分内容: `ai_score >= 85` AND `status = 'PUBLISHED'`

---

## 2. accounts - 账号管理表

**用途**: 管理小红书发布账号，记录状态和发布限制。

**写入频率**: 账号状态变更时更新（约 1-5 次/天）

**环境变量**: `LARK_TABLE_ACCOUNTS`

| 字段名 | 飞书类型 | 必填 | 说明 |
|--------|----------|------|------|
| id | 单行文本 | ✅ | 账号唯一标识 |
| name | 单行文本 | ✅ | 账号名称/昵称 |
| status | 单选 | ✅ | 状态：`ACTIVE` / `COOLDOWN` / `SUSPENDED` / `BANNED` |
| last_publish_at | 日期 | ❌ | 最后发布时间 |
| publish_count_today | 数字 | ✅ | 今日已发布数（每日重置） |
| cooldown_until | 日期 | ❌ | 冷却截止时间 |

**典型查询**:
- 可用账号: `status = 'ACTIVE'` AND `publish_count_today < 3`
- 冷却恢复: `status = 'COOLDOWN'` AND `cooldown_until <= NOW`

---

## 3. execution_logs - 执行日志表

**用途**: 记录工作流执行日志，用于监控、调试和成本统计。

**写入频率**: 高频写入（每次工作流执行产生 5-20 条日志）

**环境变量**: `LARK_TABLE_LOGS`

| 字段名 | 飞书类型 | 必填 | 说明 |
|--------|----------|------|------|
| timestamp | 日期 | ✅ | 日志时间戳 |
| level | 单选 | ✅ | 级别：`DEBUG` / `INFO` / `WARN` / `ERROR` / `FATAL` |
| workflow_id | 单行文本 | ✅ | 工作流 ID |
| workflow_run_id | 单行文本 | ✅ | 执行实例 ID |
| node_name | 单行文本 | ❌ | 节点名称 |
| event_type | 单选 | ✅ | 事件类型（见枚举） |
| message | 多行文本 | ✅ | 日志消息 |
| context | 多行文本 | ❌ | JSON 格式上下文数据 |
| error | 多行文本 | ❌ | JSON 格式错误信息 |

**典型查询**:
- 错误排查: `workflow_run_id = ?` AND `level IN ('ERROR', 'FATAL')`
- API 成本: `event_type = 'AI_API_CALL'` GROUP BY DATE(`timestamp`)
- 日执行统计: `timestamp >= TODAY` GROUP BY `workflow_id`, `level`

---

## 4. interaction_data - 互动数据表

**用途**: 存储已发布内容的互动数据快照，用于计算真实评分。

**写入频率**: 定时抓取（每篇内容发布后 24h、48h、72h 各抓取一次）

**环境变量**: `LARK_TABLE_INTERACTION`

| 字段名 | 飞书类型 | 必填 | 说明 |
|--------|----------|------|------|
| content_id | 单行文本 | ✅ | 关联的内容 ID |
| fetched_at | 日期 | ✅ | 数据抓取时间 |
| views | 数字 | ✅ | 阅读量 |
| likes | 数字 | ✅ | 点赞数 |
| collects | 数字 | ✅ | 收藏数 |
| comments | 数字 | ✅ | 评论数 |

**典型查询**:
- 增长趋势: `content_id = ?` ORDER BY `fetched_at`
- 24h 数据: `fetched_at >= CONTENT.published_at + 24h`

---

## 5. hot_topics - 热点话题表

**用途**: 存储从微博、知乎等平台抓取的热点话题，供选题参考。

**写入频率**: 定时抓取（每 2 小时，约 40 条/次）

**环境变量**: `LARK_TABLE_HOT_TOPICS`

| 字段名 | 飞书类型 | 必填 | 说明 |
|--------|----------|------|------|
| title | 单行文本 | ✅ | 热点标题 |
| hot_value | 数字 | ✅ | 热度值 |
| category | 单行文本 | ❌ | 分类 |
| url | URL | ❌ | 原始链接 |
| source | 单选 | ✅ | 来源：`weibo` / `zhihu` / `douyin` / `xiaohongshu` |
| fetched_at | 日期 | ✅ | 抓取时间 |

**典型查询**:
- 最新热点: `fetched_at >= NOW - 2h` ORDER BY `hot_value` DESC
- 按来源筛选: `source = 'weibo'` ORDER BY `hot_value` DESC

---

## 6. topic_candidates - 选题候选库

**用途**: 存储经过 Agent 处理的选题候选，包含评分和大纲。

**写入频率**: 热点处理后写入（约 10-30 条/天）

**环境变量**: `LARK_TABLE_TOPIC_CANDIDATES`

| 字段名 | 飞书类型 | 必填 | 说明 |
|--------|----------|------|------|
| id | 单行文本 | ✅ | UUID |
| created_at | 日期 | ✅ | 创建时间 |
| status | 单选 | ✅ | 状态（11种，见枚举） |
| topic_title | 单行文本 | ✅ | 原始热点标题 |
| topic_source | 单选 | ✅ | 来源平台 |
| topic_url | URL | ❌ | 原始链接 |
| topic_keywords | 多选 | ❌ | 提取的关键词 |
| relevance_score | 数字 | ❌ | 相关性总分（0-100） |
| relevance_details | 多行文本 | ❌ | JSON 格式详细评分 |
| planned_titles | 多行文本 | ❌ | JSON 格式标题备选 |
| content_angle | 单行文本 | ❌ | 内容切入角度 |
| final_title | 单行文本 | ❌ | 最终确定的标题 |
| content_outline | 多行文本 | ❌ | JSON 格式完整大纲 |
| ai_score_total | 数字 | ❌ | AI 评分总分 |
| ai_score_breakdown | 多行文本 | ❌ | JSON 格式五维度评分 |
| decision | 单选 | ❌ | 决策：`auto_approve` / `human_review` / `auto_reject` |
| priority_score | 数字 | ❌ | 优先级分数 |
| urgency_level | 单选 | ❌ | 紧急程度：`urgent` / `normal` / `low` |
| expiry_date | 日期 | ❌ | 时效截止日期 |
| content_record_id | 关联 | ❌ | 关联的内容记录 ID |

---

## 7. topic_history - 选题历史库

**用途**: 记录所有采集过的热点，用于去重和历史分析。

**写入频率**: 与热点抓取同步（约 40 条/次）

**环境变量**: `LARK_TABLE_TOPIC_HISTORY`

| 字段名 | 飞书类型 | 必填 | 说明 |
|--------|----------|------|------|
| id | 单行文本 | ✅ | UUID |
| collected_at | 日期 | ✅ | 采集时间 |
| topic_title | 单行文本 | ✅ | 热点标题 |
| topic_source | 单选 | ✅ | 来源平台 |
| heat_score | 数字 | ✅ | 平台热度值 |
| is_processed | 复选框 | ✅ | 是否已处理 |
| relevance_score | 数字 | ❌ | 相关性评分 |
| final_status | 单选 | ❌ | 最终状态 |

---

## 8. business_config - 业务配置表

**用途**: 存储可热更新的业务配置，包括 Prompt、阈值、关键词等。

**写入频率**: 手动配置更新（低频）

**环境变量**: `LARK_TABLE_BUSINESS_CONFIG`

| 字段名 | 飞书类型 | 必填 | 说明 |
|--------|----------|------|------|
| config_key | 单行文本 | ✅ | 配置键名（唯一） |
| config_value | 多行文本 | ✅ | 配置值（支持 JSON） |
| config_type | 单选 | ✅ | 类型：`prompt` / `rule` / `keyword` / `threshold` |
| description | 单行文本 | ❌ | 配置说明 |
| is_active | 复选框 | ✅ | 是否启用 |
| updated_at | 日期 | ✅ | 更新时间 |

**预置配置项**:

| config_key | config_type | 说明 |
|------------|-------------|------|
| BUSINESS_CONTEXT | prompt | 业务背景 Prompt |
| CONTENT_DIRECTIONS | rule | 内容方向列表 |
| TARGET_KEYWORDS | keyword | 目标关键词列表 |
| RELEVANCE_THRESHOLD | threshold | 相关性阈值（默认 70） |
| AUTO_APPROVE_THRESHOLD | threshold | 自动通过阈值（默认 85） |

---

## 9. 枚举值定义

### 9.1 内容状态 (content_records.status)

| 状态值 | 说明 | 可转换到 |
|--------|------|----------|
| DRAFT | 草稿 | AI_REVIEWED, REJECTED |
| AI_REVIEWED | AI 审核通过 | PENDING_APPROVAL, ARCHIVED |
| PENDING_APPROVAL | 待人工审核/发布 | PUBLISHING |
| PUBLISHING | 发布中 | PUBLISHED, FAILED |
| PUBLISHED | 已发布 | - |
| REJECTED | 已拒绝 | - |
| ARCHIVED | 已归档 | - |
| FAILED | 发布失败 | PENDING_APPROVAL |

### 9.2 选题状态 (topic_candidates.status)

| 状态值 | 说明 |
|--------|------|
| COLLECTED | 已采集 |
| EVALUATING | 评估中 |
| RELEVANT | 相关（score≥70） |
| IRRELEVANT | 不相关（score<70） |
| OUTLINE_GENERATED | 大纲已生成 |
| AI_SCORED | 已评分 |
| PENDING_REVIEW | 待人工审核 |
| APPROVED | 已批准 |
| REJECTED | 已拒绝 |
| IN_CONTENT_QUEUE | 已加入创作队列 |
| EXPIRED | 已过期 |

### 9.3 账号状态 (accounts.status)

| 状态值 | 说明 | 可发布 |
|--------|------|--------|
| ACTIVE | 正常 | ✅ |
| COOLDOWN | 冷却中 | ❌ |
| SUSPENDED | 暂停 | ❌ |
| BANNED | 封禁 | ❌ |

### 9.4 日志事件类型 (execution_logs.event_type)

| 事件类型 | 级别 | 说明 |
|----------|------|------|
| WORKFLOW_START | INFO | 工作流开始 |
| WORKFLOW_SUCCESS | INFO | 工作流成功 |
| WORKFLOW_FAILED | ERROR | 工作流失败 |
| AI_API_CALL | INFO | AI API 调用 |
| AI_API_RETRY | WARN | AI API 重试 |
| AI_API_FAILED | ERROR | AI API 失败 |
| CONTENT_CREATED | INFO | 内容创建 |
| CONTENT_REVIEWED | INFO | 内容审核 |
| PUBLISH_START | INFO | 开始发布 |
| PUBLISH_SUCCESS | INFO | 发布成功 |
| PUBLISH_FAILED | ERROR | 发布失败 |
| DATA_FETCH_SUCCESS | INFO | 数据抓取成功 |
| NOTIFICATION_SENT | INFO | 通知发送 |

---

## 环境变量汇总

```bash
# 飞书表格 ID 配置
LARK_TABLE_CONTENT=tblContentRecords
LARK_TABLE_CONTENT_TEST=tblContentRecords_test
LARK_TABLE_ACCOUNTS=tblAccounts
LARK_TABLE_LOGS=tblExecutionLogs
LARK_TABLE_INTERACTION=tblInteractionData
LARK_TABLE_HOT_TOPICS=tblHotTopics
LARK_TABLE_TOPIC_CANDIDATES=tblTopicCandidates
LARK_TABLE_TOPIC_HISTORY=tblTopicHistory
LARK_TABLE_BUSINESS_CONFIG=tblBusinessConfig
```
