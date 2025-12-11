# MVP 端到端联调检查表 & 回归测试用例

> 项目代号: XHS_AutoPublisher_v2
> 版本: v1.0 | 创建日期: 2024-12-11
> 适用阶段: MVP Phase 1 (Day 9-10 联调)

---

## 目录

1. [端到端联调检查表](#1-端到端联调检查表)
2. [回归测试用例表](#2-回归测试用例表)
3. [测试数据准备](#3-测试数据准备)
4. [问题记录模板](#4-问题记录模板)

---

## 1. 端到端联调检查表

### 1.1 环境与基础设施

| 检查项 | 前置条件 | 操作步骤 | 预期结果 |
|--------|----------|----------|----------|
| E-01 N8N 服务可用 | Docker 容器已启动 | 访问 `http://<IP>:5678` | N8N 编辑器正常打开，无报错 |
| E-02 飞书 API 连通 | LARK_APP_ID/SECRET/TOKEN 已配置 | 在 N8N 中执行 HTTP 节点查询 `business_config` 表 | 返回 `code: 0`，有配置数据 |
| E-03 Claude API 连通 | CLAUDE_API_KEY 已配置 | 发送简单 prompt（"你好"） | 返回有效响应，无 401/429 |
| E-04 Telegram Bot 连通 | BOT_TOKEN/CHAT_ID 已配置 | 发送测试消息 | 手机收到 Telegram 通知 |
| E-05 热点数据已入库 | hot_topics.py 已执行 | 查询飞书 `hot_topics` 表 | 有最近 2 小时内的热点记录 |

### 1.2 内容生成链路 (content_generator_v1)

| 检查项 | 前置条件 | 操作步骤 | 预期结果 |
|--------|----------|----------|----------|
| C-01 手动触发成功 | E-01~E-05 全部通过 | 点击 N8N 工作流 "Test workflow" 按钮 | 工作流开始执行，无立即报错 |
| C-02 配置加载成功 | C-01 通过 | 观察 `Fetch_Config` 节点输出 | 包含 `business_context`、`target_keywords` 等字段 |
| C-03 热点获取成功 | E-05 有数据 | 观察 `Fetch_Hot_Topics` 节点输出 | 返回 ≥3 条热点记录 |
| C-04 选题生成成功 | C-02, C-03 通过 | 观察 `AI_Gateway_Topics` 节点输出 | 返回 JSON，包含 3~5 个选题对象 |
| C-05 选题解析成功 | C-04 通过 | 观察 `Parse_Topics` 节点输出 | `topics` 数组非空，每项有 `title`、`angle`、`estimated_score` |
| C-06 最佳选题选中 | C-05 通过 | 观察 `Select_Best_Topic` 节点输出 | 输出单个选题对象，`estimated_score` 最高 |
| C-07 内容生成成功 | C-06 通过 | 观察 `AI_Gateway_Content` 节点输出 | 返回完整内容 JSON |
| C-08 内容解析成功 | C-07 通过 | 观察 `Parse_Content` 节点输出 | `title` 15-30 字，`content_body` 800-1200 字，`tags` 8-10 个 |

### 1.3 AI 审核链路 (sub_ai_score)

| 检查项 | 前置条件 | 操作步骤 | 预期结果 |
|--------|----------|----------|----------|
| S-01 子工作流触发 | C-08 通过 | 观察 `Execute_Sub_AI_Score` 节点 | 子工作流开始执行 |
| S-02 Step 0 账号定位 | S-01 通过 | 观察 Step 0 输出 | 返回 `score` (0-100)、`passed`、`comment` |
| S-03 Step 1 三秒测试 | S-02 通过 | 观察 Step 1 输出 | 返回 `score` (0-100)、`comment` |
| S-04 Step 2 首屏测试 | S-03 通过 | 观察 Step 2 输出 | 返回 `score` (0-100)、`comment` |
| S-05 Step 3 全文质量 | S-04 通过 | 观察 Step 3 输出 | 返回 `score` (0-100)、`comment` |
| S-06 Step 4 互动设计 | S-05 通过 | 观察 Step 4 输出 | 返回 `score` (0-100)、`comment` |
| S-07 Step 5 平台合规 | S-06 通过 | 观察 Step 5 输出 | 返回 `score` (0-100)、`comment` |
| S-08 评分汇总正确 | S-02~S-07 通过 | 观察 `Calculate_Final_Score` 输出 | 加权总分正确，`status` 符合阈值规则 |

### 1.4 数据持久化链路

| 检查项 | 前置条件 | 操作步骤 | 预期结果 |
|--------|----------|----------|----------|
| D-01 记录字段完整 | S-08 通过 | 观察 `Prepare_Record` 节点输出 | 包含全部必填字段（id, title, content_body, ai_score, status, workflow_run_id, prompt_id, prompt_version） |
| D-02 飞书写入成功 | D-01 通过 | 观察 `Save_To_Lark` 节点输出 | 返回 `code: 0`，包含 `record_id` |
| D-03 飞书数据验证 | D-02 通过 | 登录飞书多维表格查看 `content_records` 表 | 新记录存在，字段值与 N8N 输出一致 |
| D-04 日志写入成功 | D-02 通过 | 查询 `execution_logs` 表 | 有本次 `workflow_run_id` 的 INFO/ERROR 日志 |

### 1.5 通知链路

| 检查项 | 前置条件 | 操作步骤 | 预期结果 |
|--------|----------|----------|----------|
| N-01 成功通知发送 | D-02 通过，status=AI_REVIEWED | 观察 `Log_Success` → Telegram 节点 | 手机收到 Telegram 消息，包含标题和评分 |
| N-02 失败通知发送 | 任意节点失败 | 手动制造错误（如删除 API Key） | 手机收到 Telegram 错误告警 |

---

## 2. 回归测试用例表

### 2.1 正常路径用例

| 用例ID | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|----------|--------|
| TC-001 | 正常生成并写入飞书 | 环境正常，热点数据存在 | 1. 手动触发工作流<br>2. 等待执行完成<br>3. 检查飞书表 | 1. 工作流成功完成<br>2. content_records 新增 1 条记录<br>3. ai_score ≥ 0，status 为 AI_REVIEWED/NEEDS_OPTIMIZATION/REJECTED 之一<br>4. prompt_id/version 正确记录 | P0 |
| TC-002 | 高分内容状态为 AI_REVIEWED | TC-001 通过 | 1. 检查 ai_score ≥ 80 的记录<br>2. 验证 status 字段 | status = 'AI_REVIEWED' | P0 |
| TC-003 | 中分内容状态为 NEEDS_OPTIMIZATION | TC-001 通过 | 1. 检查 70 ≤ ai_score < 80 的记录<br>2. 验证 status 字段 | status = 'NEEDS_OPTIMIZATION' | P0 |
| TC-004 | 低分内容状态为 REJECTED | TC-001 通过 | 1. 检查 ai_score < 70 的记录<br>2. 验证 status 字段 | status = 'REJECTED' | P0 |
| TC-005 | 内容格式符合规范 | TC-001 通过 | 1. 检查 title 长度<br>2. 检查 content_body 长度<br>3. 检查 tags 数量 | 1. title: 15-30 字<br>2. content_body: 800-1200 字<br>3. tags: 8-10 个 | P0 |
| TC-006 | Telegram 成功通知 | TC-001 通过，ai_score ≥ 70 | 1. 执行工作流<br>2. 检查手机 Telegram | 收到消息，包含：标题、评分、状态、飞书链接 | P1 |

### 2.2 Claude API 异常用例

| 用例ID | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|----------|--------|
| TC-007 | Claude API Key 无效 | 将 CLAUDE_API_KEY 设为无效值 | 1. 触发工作流<br>2. 观察错误处理 | 1. 工作流进入 Error_Handler<br>2. execution_logs 写入 ERROR 级别日志<br>3. Telegram 收到错误告警<br>4. 不写入 content_records | P0 |
| TC-008 | Claude API 超时 | 设置极短 timeout（如 1ms） | 1. 触发工作流<br>2. 观察重试行为 | 1. 自动重试 2 次<br>2. 3 次失败后进入 Error_Handler<br>3. 日志记录每次重试 | P1 |
| TC-009 | Claude 返回空内容 | 使用会返回空响应的 prompt | 1. 修改 prompt 触发空响应<br>2. 观察解析节点 | 1. Parse 节点检测到空内容<br>2. 抛出自定义错误<br>3. 不写入无效记录 | P1 |
| TC-010 | Claude 返回格式错误 | 模拟返回非 JSON 格式 | 1. 触发工作流<br>2. 观察 JSON 解析 | 1. 解析失败被捕获<br>2. 错误日志包含原始响应<br>3. 进入 Error_Handler | P1 |

### 2.3 飞书 API 异常用例

| 用例ID | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|----------|--------|
| TC-011 | 飞书 Token 过期 | 清除缓存的 tenant_access_token | 1. 触发工作流<br>2. 观察 Token 刷新 | 1. 自动刷新 Token<br>2. 重试写入成功<br>3. 日志记录 Token 刷新事件 | P0 |
| TC-012 | 飞书 API 写入失败 | 将 table_id 设为无效值 | 1. 触发工作流<br>2. 观察错误处理 | 1. Save_To_Lark 失败<br>2. execution_logs 写入错误（包含 table_id 和错误码）<br>3. Telegram 告警包含"飞书写入失败" | P0 |
| TC-013 | 飞书 API 限流 | 短时间内大量请求 | 1. 连续触发 10 次工作流<br>2. 观察限流处理 | 1. 检测到 429 错误<br>2. 等待后自动重试<br>3. 最终成功或报告限流错误 | P2 |

### 2.4 Telegram 通知异常用例

| 用例ID | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|----------|--------|
| TC-014 | Telegram Bot Token 无效 | 将 TELEGRAM_BOT_TOKEN 设为无效值 | 1. 触发工作流（正常生成内容）<br>2. 观察通知节点 | 1. 内容正常写入飞书（主流程不受影响）<br>2. 通知失败被记录到 execution_logs<br>3. 工作流整体状态为"部分成功" | P1 |
| TC-015 | Telegram Chat ID 无效 | 将 TELEGRAM_CHAT_ID 设为无效值 | 1. 触发工作流<br>2. 观察通知节点 | 同 TC-014：主流程成功，通知失败被记录 | P1 |

### 2.5 边界条件用例

| 用例ID | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|----------|--------|
| TC-016 | 无热点数据时的处理 | 清空 hot_topics 表 | 1. 触发工作流<br>2. 观察选题生成 | 1. Fetch_Hot_Topics 返回空数组<br>2. AI_Gateway_Topics 使用纯 AI 生成模式<br>3. 仍能生成有效选题 | P1 |

---

## 3. 测试数据准备

### 3.1 飞书表必备数据

#### business_config 表

```json
[
  {
    "config_key": "BUSINESS_CONTEXT",
    "config_value": "你是一个专注于AI自动化和工作流优化的小红书创作者...",
    "config_type": "prompt",
    "is_active": true
  },
  {
    "config_key": "CONTENT_DIRECTIONS",
    "config_value": "[\"AI Agent开发\", \"N8N工作流\", \"小红书运营\", \"效率工具\"]",
    "config_type": "rule",
    "is_active": true
  },
  {
    "config_key": "TARGET_KEYWORDS",
    "config_value": "[\"AI\", \"自动化\", \"工作流\", \"N8N\", \"Claude\", \"效率\"]",
    "config_type": "keyword",
    "is_active": true
  },
  {
    "config_key": "RELEVANCE_THRESHOLD",
    "config_value": "70",
    "config_type": "threshold",
    "is_active": true
  },
  {
    "config_key": "AUTO_APPROVE_THRESHOLD",
    "config_value": "85",
    "config_type": "threshold",
    "is_active": true
  }
]
```

#### hot_topics 表（至少 3 条）

```json
[
  {
    "title": "AI 工具推荐：提升效率的 10 个神器",
    "hot_value": 12345,
    "source": "weibo",
    "fetched_at": "<当前时间>"
  },
  {
    "title": "自动化办公：如何用 AI 处理日常工作",
    "hot_value": 9876,
    "source": "zhihu",
    "fetched_at": "<当前时间>"
  },
  {
    "title": "效率工具盘点：2024 年必备 APP",
    "hot_value": 8765,
    "source": "xiaohongshu",
    "fetched_at": "<当前时间>"
  }
]
```

### 3.2 环境变量检查清单

```bash
# 必须配置（缺一不可）
CLAUDE_API_KEY=sk-ant-xxx
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
LARK_APP_TOKEN=xxx
TELEGRAM_BOT_TOKEN=xxx:xxx
TELEGRAM_CHAT_ID=-100xxx

# 飞书表 ID（根据实际创建的表填写）
LARK_TABLE_CONTENT=tblXXX
LARK_TABLE_LOGS=tblXXX
LARK_TABLE_HOT_TOPICS=tblXXX
LARK_TABLE_BUSINESS_CONFIG=tblXXX
```

---

## 4. 问题记录模板

### 4.1 问题单模板

```markdown
## 问题编号: BUG-001

**发现日期**: 2024-12-XX
**发现人**: XXX
**关联用例**: TC-XXX

### 问题描述
[简要描述问题现象]

### 复现步骤
1.
2.
3.

### 预期结果
[应该是什么样]

### 实际结果
[实际是什么样]

### 相关日志
```
[粘贴 N8N 执行日志或飞书 execution_logs 记录]
```

### 根因分析
[定位后填写]

### 修复方案
[修复后填写]

### 验证结果
- [ ] 修复已验证
- [ ] 回归测试通过
```

### 4.2 测试执行记录表

| 日期 | 执行人 | 用例范围 | 通过数 | 失败数 | 阻塞数 | 备注 |
|------|--------|----------|--------|--------|--------|------|
| 2024-12-XX | XXX | TC-001~TC-016 | X | X | X | [备注] |

---

## 5. MVP 验收标准汇总

根据开发计划，MVP 阶段需达到以下指标：

### 5.1 功能验收

- [ ] 输入关键词后能生成 3-5 个选题
- [ ] 选中的选题能生成 800-1200 字内容
- [ ] 5 步审核能正常执行并给出分数
- [ ] 分数 ≥80 的内容状态为 AI_REVIEWED
- [ ] 分数 70-79 的内容状态为 NEEDS_OPTIMIZATION
- [ ] 分数 <70 的内容状态为 REJECTED
- [ ] 所有内容正确写入飞书表格
- [ ] 生成完成后收到 Telegram 通知

### 5.2 指标验收

- [ ] 10 次测试中 ≥8 次成功（80% 成功率）
- [ ] 单次生成时间 ≤5 分钟
- [ ] 无未捕获的错误

### 5.3 数据验收

- [ ] content_records 表数据完整（所有必填字段非空）
- [ ] execution_logs 表有完整日志（至少包含 WORKFLOW_START、WORKFLOW_SUCCESS/FAILED）
- [ ] prompt_id 和 prompt_version 正确记录

---

## 附录：快速测试脚本

### A. 飞书连通性测试（Python）

```python
#!/usr/bin/env python3
"""飞书 API 连通性测试"""

import os
from lark_client import LarkClient

def test_lark_connection():
    try:
        client = LarkClient()
        # 查询 business_config 表
        result = client.query_records(
            table_id=os.environ.get('LARK_TABLE_BUSINESS_CONFIG', 'tblBusinessConfig'),
            page_size=1
        )
        print(f"✅ 飞书连接成功，查询到 {len(result.get('data', {}).get('items', []))} 条配置")
        return True
    except Exception as e:
        print(f"❌ 飞书连接失败: {e}")
        return False

if __name__ == "__main__":
    test_lark_connection()
```

### B. Telegram 通知测试（curl）

```bash
#!/bin/bash
# Telegram 通知测试

BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID}"

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=🧪 XHS_AutoPublisher MVP 测试消息 - $(date '+%Y-%m-%d %H:%M:%S')" \
  -d "parse_mode=Markdown"

echo ""
echo "如果收到消息，说明 Telegram 配置正确 ✅"
```

### C. Claude API 测试（curl）

```bash
#!/bin/bash
# Claude API 连通性测试

CLAUDE_API_KEY="${CLAUDE_API_KEY}"

curl -s -X POST "https://api.anthropic.com/v1/messages" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${CLAUDE_API_KEY}" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "请用一句话回复：你好"}]
  }' | jq '.content[0].text'

echo ""
echo "如果返回问候语，说明 Claude API 配置正确 ✅"
```

---

> 文档维护: 每次重大功能变更后需同步更新本检查表
