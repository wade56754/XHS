# MediaCrawler v3.1 开发流程指南

> 本文档指导开发者按步骤完成 MediaCrawler v3.1 的开发、测试和部署

---

## 一、服务器架构

### 1.1 服务器清单

| 服务器 | IP | 用途 | 部署服务 |
|--------|-----|------|---------|
| n8n 服务器 | `136.110.80.154` | 工作流编排 | n8n, Docker |
| 采集服务器 | `124.221.251.8` | 爬虫服务 | MediaCrawler API (端口 8080) |

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        飞书多维表格                               │
│  ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐    │
│  │tbl_cookie│ │tbl_candidate │ │tbl_execution│ │tbl_source│    │
│  └────┬─────┘ └──────┬───────┘ └──────┬──────┘ └────┬─────┘    │
└───────┼──────────────┼────────────────┼─────────────┼──────────┘
        │              │                │             │
        │    ┌─────────▼────────────────▼─────────────▼───┐
        │    │         n8n 工作流引擎                       │
        │    │         136.110.80.154                      │
        │    │  ┌─────────────┐  ┌──────────────────┐     │
        │    │  │ 执行锁管理   │  │ 超时回收 (15min) │     │
        │    │  └─────────────┘  └──────────────────┘     │
        │    │  ┌─────────────┐  ┌──────────────────┐     │
        │    │  │ 记录锁管理   │  │ 幂等写入         │     │
        │    │  └──────┬──────┘  └──────────────────┘     │
        │    └─────────┼──────────────────────────────────┘
        │              │
        │              │ HTTP API
        │              ▼
        │    ┌─────────────────────────────────────────────┐
        │    │      MediaCrawler API 服务                   │
        │    │      124.221.251.8:8080                      │
        │    │  ┌─────────────┐  ┌──────────────────┐      │
        └────┼─▶│ Cookie 管理  │  │ 日志脱敏         │      │
             │  └─────────────┘  └──────────────────┘      │
             │  ┌─────────────┐  ┌──────────────────┐      │
             │  │ 搜索 API    │  │ 详情 API         │      │
             │  └──────┬──────┘  └────────┬─────────┘      │
             └─────────┼─────────────────┼────────────────┘
                       │                 │
                       ▼                 ▼
              ┌─────────────────────────────────┐
              │          小红书平台              │
              └─────────────────────────────────┘
```

### 1.3 网络连通性要求

```bash
# n8n 服务器 -> 采集服务器
curl http://124.221.251.8:8080/health

# n8n 服务器 -> 飞书 API
curl https://open.feishu.cn/open-apis/bitable/v1/apps

# 采集服务器 -> 小红书
curl https://www.xiaohongshu.com
```

---

## 二、开发环境准备

### 2.1 必要工具

| 工具 | 版本要求 | 用途 |
|------|---------|------|
| Python | >= 3.9 | API 服务 |
| n8n | >= 1.0 | 工作流编排 |
| Docker | >= 20.0 | 容器化部署 |
| Git | - | 版本控制 |

### 2.2 采集服务器环境配置 (124.221.251.8)

```bash
# SSH 登录采集服务器
ssh wade@124.221.251.8

# 创建项目目录
mkdir -p /opt/mediacrawler-api
cd /opt/mediacrawler-api

# 克隆项目
git clone <repo-url> .

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cat > .env << 'EOF'
# Cookie 加密主密钥 (32字节)
COOKIE_MASTER_KEY=your-32-byte-secret-key-here!!

# 服务配置
API_HOST=0.0.0.0
API_PORT=8080

# 飞书配置 (只读)
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx

# 告警 Webhook
ALERT_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# 日志
LOG_LEVEL=INFO
EOF

# 启动服务
python -m uvicorn media_crawler_api.main:app --host 0.0.0.0 --port 8080
```

### 2.3 n8n 服务器配置 (136.110.80.154)

```bash
# SSH 登录 n8n 服务器
ssh wade@136.110.80.154

# 检查 n8n 状态
docker ps | grep n8n

# n8n 环境变量 (docker-compose.yml)
cat > /opt/n8n/docker-compose.yml << 'EOF'
version: '3'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=your-password
      - WEBHOOK_URL=http://136.110.80.154:5678/
      - GENERIC_TIMEZONE=Asia/Shanghai
      # MediaCrawler API 地址
      - MEDIACRAWLER_API_URL=http://124.221.251.8:8080
    volumes:
      - /opt/n8n/data:/home/node/.n8n
    restart: always
EOF

# 启动 n8n
cd /opt/n8n && docker-compose up -d
```

### 2.4 服务访问地址

| 服务 | 地址 | 用途 |
|------|------|------|
| n8n 控制台 | `http://136.110.80.154:5678` | 工作流管理 |
| MediaCrawler API | `http://124.221.251.8:8080` | 爬虫 API |
| API 文档 | `http://124.221.251.8:8080/docs` | Swagger 文档 |
| 健康检查 | `http://124.221.251.8:8080/health` | 服务状态 |

---

## 三、Day 1：数据层 + API 基础

### 3.1 飞书表结构创建

**步骤 1: 创建 tbl_cookie 表**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| cookie_name | 文本 | 是 | 幂等键，唯一标识 |
| platform | 单选 | 是 | 平台：xhs |
| cookie_encrypted | 文本 | 是 | 加密后的 Cookie |
| encryption_key_id | 文本 | 是 | 加密密钥 ID |
| status | 单选 | 是 | active/cooling/invalid/banned |
| priority | 数字 | 是 | 优先级，默认 1 |
| daily_used | 数字 | 是 | 当日使用次数 |
| daily_limit | 数字 | 是 | 每日限额，默认 100 |
| consecutive_errors | 数字 | 是 | 连续错误次数 |
| total_errors | 数字 | 是 | 累计错误次数 |
| cooling_until | 日期 | 否 | 冷却结束时间 |
| created_at | 日期 | 是 | 创建时间 |
| updated_at | 日期 | 是 | 更新时间 |

**步骤 2: 创建 tbl_candidate 表**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| note_id | 文本 | 是 | 幂等键，笔记 ID |
| platform | 单选 | 是 | 平台：xhs |
| note_url | URL | 是 | 笔记链接 |
| status | 单选 | 是 | pending/processing/collected/failed |
| processing_lock | 文本 | 否 | 执行锁 ID |
| locked_at | 日期 | 否 | 锁定时间 |
| retry_count | 数字 | 是 | 重试次数，默认 0 |
| source_keyword | 文本 | 否 | 来源关键词 |
| exec_meta | 文本 | 否 | 执行元数据 (JSON) |

**步骤 3: 创建 tbl_crawl_execution 表**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| workflow_name | 文本 | 是 | 工作流名称 |
| execution_id | 文本 | 是 | 执行 ID |
| status | 单选 | 是 | running/completed/failed/timeout |
| started_at | 日期 | 是 | 开始时间 |
| heartbeat_at | 日期 | 是 | 心跳时间 |
| completed_at | 日期 | 否 | 完成时间 |
| items_processed | 数字 | 是 | 处理成功数 |
| items_failed | 数字 | 是 | 处理失败数 |

**步骤 4: 扩展 tbl_source 表**

新增字段：
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| idempotency_key | 文本 | 是 | 幂等键：{note_id}_v1 |
| processing_lock | 文本 | 否 | 执行锁 ID |
| locked_at | 日期 | 否 | 锁定时间 |
| retry_count | 数字 | 是 | 重试次数 |
| last_error_code | 文本 | 否 | 最后错误码 |
| exec_meta | 文本 | 否 | 执行元数据 |

### 3.2 API 代码开发 (采集服务器 124.221.251.8)

```bash
# 登录采集服务器
ssh wade@124.221.251.8
cd /opt/mediacrawler-api
source venv/bin/activate
```

**步骤 1: 实现响应模型**

```python
# media_crawler_api/models/response.py
# 实现 ErrorCode 枚举、ApiResponse、BatchResponse 等模型
# 参考 AI_READY_SPEC_v3.1_SIMPLE.md 第三节
```

验证点：
- [ ] ErrorCode 包含所有 7 种错误码
- [ ] ApiResponse 包含 success/data/error/meta 字段
- [ ] BatchResponse 包含 items/summary 字段

**步骤 2: 实现 Cookie 加密**

```python
# media_crawler_api/utils/crypto.py
# 实现 AES-256 加密/解密
# 密钥从 COOKIE_MASTER_KEY 环境变量派生
```

验证命令：
```bash
# 在采集服务器上测试
ssh wade@124.221.251.8
cd /opt/mediacrawler-api && source venv/bin/activate

python -c "
from media_crawler_api.utils.crypto import cookie_encryption
encrypted, key_id = cookie_encryption.encrypt('test_cookie_value')
decrypted = cookie_encryption.decrypt(encrypted, key_id)
assert decrypted == 'test_cookie_value'
print('Cookie 加密测试通过')
"
```

**步骤 3: 实现日志脱敏**

```python
# media_crawler_api/utils/logging.py
# 实现敏感信息脱敏过滤器
```

验证命令：
```bash
# 检查日志无明文 Cookie
grep -r "web_session=" /opt/mediacrawler-api/logs/ && echo "FAIL" || echo "PASS"
```

### 3.3 Day 1 验收清单

```bash
# 在采集服务器上运行
ssh wade@124.221.251.8
cd /opt/mediacrawler-api && source venv/bin/activate
python scripts/day1_acceptance.py
```

检查项：
- [ ] 4 张表已创建，字段完整
- [ ] API 返回统一响应格式
- [ ] 错误码枚举完整 (7 种)
- [ ] Cookie 加密/解密正常
- [ ] 安全审计脚本通过

---

## 四、Day 2：n8n 工作流 + 锁机制

### 4.1 n8n 工作流配置 (n8n 服务器 136.110.80.154)

访问 n8n 控制台：`http://136.110.80.154:5678`

**全局变量设置**

在 n8n 中配置以下环境变量：
```
MEDIACRAWLER_API_URL = http://124.221.251.8:8080
FEISHU_APP_TOKEN = xxx
FEISHU_TABLE_COOKIE = tbl_cookie
FEISHU_TABLE_CANDIDATE = tbl_candidate
FEISHU_TABLE_EXECUTION = tbl_crawl_execution
FEISHU_TABLE_SOURCE = tbl_source
```

### 4.2 执行锁工作流

**节点 1: 获取执行锁**

n8n Code 节点配置：
```javascript
// 输入：workflow_name (从触发器获取)
const workflow_name = $input.first().json.workflow_name || 'default_workflow';
const execution_id = `exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// 返回给下一个节点
return {
  json: {
    workflow_name,
    execution_id,
    action: 'check_and_acquire'
  }
};
```

**节点 2: 查询运行中执行 (飞书节点)**

筛选条件：
```
workflow_name = {{$json.workflow_name}}
AND status = "running"
AND heartbeat_at > NOW() - 30min
```

**节点 3: 判断是否可获取锁 (IF 节点)**

条件：`{{$json.items.length}} === 0`

**节点 4: 创建执行锁 (飞书节点)**

写入数据：
```json
{
  "workflow_name": "{{$json.workflow_name}}",
  "execution_id": "{{$json.execution_id}}",
  "status": "running",
  "started_at": "{{$now}}",
  "heartbeat_at": "{{$now}}",
  "items_processed": 0,
  "items_failed": 0
}
```

### 4.3 记录锁工作流

**节点 1: 查询待处理记录**

```javascript
// 查询 tbl_candidate，条件：status=pending
// limit = 10 (批量大小)
```

**节点 2: 逐条锁定 (Loop 节点)**

对每条记录执行：
```javascript
// 更新记录
{
  "status": "processing",
  "processing_lock": "{{$execution_id}}",
  "locked_at": "{{$now}}"
}
```

### 4.4 调用采集 API

**HTTP Request 节点配置**

```
Method: POST
URL: http://124.221.251.8:8080/api/xhs/note/detail
Headers:
  Content-Type: application/json
  X-Request-ID: {{$json.execution_id}}-{{$json.note_id}}
Body:
{
  "note_id": "{{$json.note_id}}",
  "cookie_name": "{{$json.cookie_name}}"
}
```

### 4.5 超时回收工作流

**触发器：Schedule Trigger (每 15 分钟)**

```javascript
// 节点 1: 计算超时阈值
const timeout_threshold = new Date(Date.now() - 30 * 60 * 1000);

// 节点 2: 查询超时执行
// 条件：status=running AND heartbeat_at < threshold

// 节点 3: 标记为 timeout

// 节点 4: 查询超时记录
// 条件：status=processing AND locked_at < threshold

// 节点 5: 回收记录锁
// 如果 retry_count >= 3，设置 status=failed
// 否则设置 status=pending，retry_count += 1
```

### 4.6 幂等写入工作流

```javascript
// 节点 1: 生成幂等键
const idempotency_key = `${note_id}_v1`;

// 节点 2: 查询是否已存在
// 条件：idempotency_key = {{$json.idempotency_key}}

// 节点 3: IF 已存在则跳过

// 节点 4: 写入 tbl_source

// 节点 5: 更新 tbl_candidate 状态为 collected
```

### 4.7 Day 2 验收清单

```bash
# 在采集服务器上运行
ssh wade@124.221.251.8
cd /opt/mediacrawler-api && source venv/bin/activate
python scripts/day2_acceptance.py
```

检查项：
- [ ] 执行锁获取/释放正常
- [ ] 记录锁获取/释放正常
- [ ] 幂等写入测试通过
- [ ] request_id 全链路可追踪
- [ ] 超时回收任务正常
- [ ] 日志无明文 Cookie

---

## 五、Day 3：告警 + 集成测试

### 5.1 告警配置

**P0 告警：Cookie 耗尽**
```python
# 条件：active_count < 1
# 动作：立即通知 + 暂停工作流
```

**P1 告警：成功率低**
```python
# 条件：success_rate < 90% 持续 10 分钟
# 动作：通知 + 记录日志
```

**P2 告警：处理积压**
```python
# 条件：pending > 500 持续 30 分钟
# 动作：通知
```

### 5.2 端到端测试

**测试用例 1：正常采集流程**

```bash
# 1. 添加测试 Cookie (从本地或 n8n 服务器)
curl -X POST http://124.221.251.8:8080/api/cookies \
  -H "Content-Type: application/json" \
  -d '{"name": "test_cookie", "value": "xxx", "platform": "xhs"}'

# 2. 添加候选笔记
# (通过 n8n 工作流 http://136.110.80.154:5678 或直接写入飞书表)

# 3. 在 n8n 控制台触发采集工作流
# http://136.110.80.154:5678

# 4. 验证结果
# - tbl_candidate 状态变为 collected
# - tbl_source 有新记录
# - idempotency_key 正确
```

**测试用例 2：并发锁测试**

```bash
# 在 n8n 中同时启动 2 个执行
# 验证只有 1 个获得锁
```

**测试用例 3：部分失败测试**

```bash
# 批量请求 3 条，模拟 1 条超时
curl -X POST http://124.221.251.8:8080/api/xhs/notes/batch \
  -H "Content-Type: application/json" \
  -d '{"note_ids": ["id1", "id2", "id3"]}'

# 验证返回：2 成功 + 1 失败
# 验证 error.code = PARTIAL_FAIL
```

**测试用例 4：超时回收测试**

```bash
# 1. 锁定记录但不处理
# 2. 等待 30+ 分钟（或手动修改 locked_at）
# 3. 在 n8n 中触发回收工作流
# 4. 验证记录状态回到 pending
```

### 5.3 Day 3 验收清单

```bash
ssh wade@124.221.251.8
cd /opt/mediacrawler-api && source venv/bin/activate
python scripts/day3_acceptance.py
```

检查项：
- [ ] 3 条告警可触发
- [ ] 完整采集流程跑通
- [ ] 部分失败场景验证通过
- [ ] 回滚方案可执行

---

## 六、部署流程

### 6.1 采集服务器部署 (124.221.251.8)

```bash
# 登录采集服务器
ssh wade@124.221.251.8

# 使用 Docker 部署
cd /opt/mediacrawler-api

# 构建镜像
docker build -t mediacrawler-api:v3.1 .

# 停止旧容器
docker stop mediacrawler-api || true
docker rm mediacrawler-api || true

# 启动新容器
docker run -d \
  --name mediacrawler-api \
  --restart always \
  -p 8080:8080 \
  -v /opt/mediacrawler-api/logs:/app/logs \
  --env-file /opt/mediacrawler-api/.env \
  mediacrawler-api:v3.1

# 验证部署
curl http://localhost:8080/api/health
```

### 6.2 n8n 工作流部署 (136.110.80.154)

```bash
# 登录 n8n 服务器
ssh wade@136.110.80.154

# 检查 n8n 状态
docker ps | grep n8n

# 导入工作流
# 1. 打开 http://136.110.80.154:5678
# 2. 导入工作流 JSON 文件
# 3. 配置飞书凭证
# 4. 激活工作流
```

### 6.3 灰度验证

```bash
# 1. 在 n8n 中执行小批量测试 (10 条)
# 2. 观察 30 分钟
# 3. 检查指标：
#    - 错误率 < 1%
#    - 延迟 P99 < 500ms
# 4. 逐步放量
```

### 6.4 回滚方案

```bash
# 采集服务器回滚
ssh wade@124.221.251.8
docker stop mediacrawler-api
docker run -d --name mediacrawler-api ... mediacrawler-api:v3.0  # 旧版本

# n8n 工作流回滚
# 1. 在 n8n 控制台停用新工作流
# 2. 启用旧版本工作流

# 数据回滚 (如需要)
# 1. 停止所有工作流
# 2. 执行数据修复脚本
# 3. 重启服务
```

---

## 七、运维操作手册

### 7.1 日常检查

```bash
# 采集服务器健康检查
curl http://124.221.251.8:8080/health

# 查看 API 日志
ssh wade@124.221.251.8
docker logs -f mediacrawler-api --tail 100

# n8n 服务检查
curl http://136.110.80.154:5678/healthz

# 查看 n8n 日志
ssh wade@136.110.80.154
docker logs -f n8n --tail 100
```

### 7.2 常见问题排查

| 问题 | 检查命令 | 解决方案 |
|------|---------|---------|
| API 无响应 | `curl http://124.221.251.8:8080/health` | 重启容器 |
| n8n 工作流失败 | 查看 n8n 执行日志 | 检查飞书凭证 |
| Cookie 耗尽 | 查看 tbl_cookie 表 | 添加新 Cookie |
| 锁死记录 | 查看 processing 状态记录 | 手动触发回收 |

### 7.3 服务重启命令

```bash
# 重启采集服务
ssh wade@124.221.251.8
docker restart mediacrawler-api

# 重启 n8n
ssh wade@136.110.80.154
docker restart n8n
```

---

## 八、监控指标

### 8.1 关键指标

| 指标 | 阈值 | 告警级别 | 采集方式 |
|------|------|---------|---------|
| API 成功率 | < 90% | P1 | `http://124.221.251.8:8080/metrics` |
| API 延迟 P99 | > 5s | P2 | API 日志 |
| Cookie 可用数 | < 1 | P0 | 飞书表查询 |
| 待处理队列 | > 500 | P2 | 飞书表查询 |
| n8n 工作流失败率 | > 5% | P1 | n8n 执行历史 |

### 8.2 监控面板 URL

| 面板 | 地址 |
|------|------|
| n8n 执行历史 | `http://136.110.80.154:5678/executions` |
| API Swagger | `http://124.221.251.8:8080/docs` |
| 飞书多维表格 | 飞书应用链接 |

---

## 九、代码审查清单

提交代码前检查：

- [ ] 不直接写入飞书（n8n 是唯一写入者）
- [ ] 所有写入操作幂等
- [ ] Cookie 值已加密存储
- [ ] 日志已脱敏处理
- [ ] 错误码使用正确
- [ ] request_id 贯穿全链路
- [ ] 超时配置合理
- [ ] 单元测试覆盖

---

## 十、联系方式

| 角色 | 负责 | 服务器 |
|------|------|--------|
| API 开发 | MediaCrawler API | 124.221.251.8 |
| 工作流开发 | n8n 工作流 | 136.110.80.154 |
| 运维 | 服务器运维 | 两台服务器 |

---

> **开发顺序**：环境准备 → Day1 → Day2 → Day3 → 灰度 → 全量
