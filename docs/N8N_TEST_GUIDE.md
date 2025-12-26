# n8n 工作流测试指南

> **版本**: v1.0 | **更新**: 2025-12-20
> **适用**: XHS 自动化运营系统测试

---

## 一、测试环境

### 1.1 服务地址

| 服务 | 地址 | 端口 | 用途 |
|------|------|------|------|
| **n8n** | https://n8n.primetat.com | 443 | 工作流引擎 (Cloudflare 代理) |
| **n8n 直连** | http://136.110.80.154 | 5678 | 工作流引擎 (直连) |
| **MediaCrawler** | http://124.221.251.8 | 8080 | 小红书爬虫 API |
| **RedInk** | http://136.110.80.154 | 12398 | AI 图文生成 |
| **social-auto-upload** | http://136.110.80.154 | 5409 | 自动发布 |

### 1.2 认证信息

```bash
# MediaCrawler API
API_KEY: mc-api-key-2024-secure
Header: X-API-Key: mc-api-key-2024-secure

# 飞书
LARK_APP_TOKEN: Gq93bAlZ7aSSclsLKdTcYCO2nwh
LARK_APP_ID: cli_a98f34e454ba100c

# 飞书表格 ID
COOKIE_TABLE_ID: tblYa2d2a5lypzqz
TOPICS_TABLE_ID: tblE2SypBdIhJVrR
SOURCE_TABLE_ID: tblPCp5gqgVFnhLc
CONTENT_TABLE_ID: tblMYjwzOkYpW4AX
PUBLISH_TABLE_ID: tblp3iSuo0dasTtg
```

---

## 二、连通性测试

### 2.1 n8n 服务测试

```bash
# 测试 1: 健康检查 (通过 Cloudflare)
curl -s "https://n8n.primetat.com/healthz"
# 预期: {"status":"ok"}

# 测试 2: 健康检查 (直连)
curl -s "http://136.110.80.154:5678/healthz"
# 预期: {"status":"ok"}

# 测试 3: API 认证检查
curl -s "http://136.110.80.154:5678/api/v1/workflows"
# 预期: {"message":"'X-N8N-API-KEY' header required"}
```

**测试结果表:**

| 测试项 | 命令 | 预期结果 | 实际结果 | 状态 |
|--------|------|----------|----------|------|
| Cloudflare 代理 | `curl https://n8n.primetat.com/healthz` | `{"status":"ok"}` | | ☐ |
| 直连访问 | `curl http://136.110.80.154:5678/healthz` | `{"status":"ok"}` | | ☐ |
| API 认证 | `curl .../api/v1/workflows` | 需要 API Key | | ☐ |

### 2.2 MediaCrawler API 测试

```bash
# 测试 1: 健康检查
curl -s "http://124.221.251.8:8080/api/health" -H "X-API-Key: mc-api-key-2024-secure"
# 预期: {"status":"healthy","crawler_ready":true,...}

# 测试 2: 登录状态
curl -s "http://124.221.251.8:8080/api/login/status" -H "X-API-Key: mc-api-key-2024-secure"
# 预期: {"success":true,"data":{"status":"confirmed","crawler_ready":true}}

# 测试 3: 人工搜索
curl -s -X POST "http://124.221.251.8:8080/api/search/human" \
  -H "X-API-Key: mc-api-key-2024-secure" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "美食", "limit": 3}'
# 预期: {"success":true,"data":{"items":[...],"total":3}}

# 测试 4: 创作者信息
curl -s "http://124.221.251.8:8080/api/creator/5dc866630000000001008f8d" \
  -H "X-API-Key: mc-api-key-2024-secure"
# 预期: 返回创作者信息或 "创作者不存在" (非 -104 错误)
```

**测试结果表:**

| 测试项 | 端点 | 预期结果 | 实际结果 | 状态 |
|--------|------|----------|----------|------|
| 健康检查 | `/api/health` | `crawler_ready:true` | | ☐ |
| 登录状态 | `/api/login/status` | `status:confirmed` | | ☐ |
| 人工搜索 | `/api/search/human` | 返回笔记数据 | | ☐ |
| 创作者 API | `/api/creator/{id}` | 非 -104 响应 | | ☐ |

### 2.3 RedInk API 测试

```bash
# 测试 1: 健康检查 (如果部署)
curl -s "http://136.110.80.154:12398/api/health"
# 预期: 服务状态

# 测试 2: 生成大纲
curl -s -X POST "http://136.110.80.154:12398/api/outline" \
  -H "Content-Type: application/json" \
  -d '{"topic": "如何搭配秋季穿搭"}'
# 预期: {"success":true,"outline":{...}}
```

### 2.4 飞书 API 测试

```bash
# 测试 1: 获取 Token
curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"cli_a98f34e454ba100c","app_secret":"YOUR_SECRET"}'
# 预期: {"code":0,"tenant_access_token":"xxx"}

# 测试 2: 读取 Cookie 表 (需要 Token)
curl -s "https://open.feishu.cn/open-apis/bitable/v1/apps/Gq93bAlZ7aSSclsLKdTcYCO2nwh/tables/tblYa2d2a5lypzqz/records" \
  -H "Authorization: Bearer YOUR_TOKEN"
# 预期: {"code":0,"data":{"items":[...]}}
```

---

## 三、n8n 工作流单元测试

### 3.1 WF-Discovery (内容发现)

**测试场景:**

| 场景 | 输入 | 预期输出 | 验证方法 |
|------|------|----------|----------|
| 正常采集 | keyword="穿搭" | Topics 表新增记录 | 查询飞书表 |
| 空结果 | keyword="xyzabc123" | 无新记录，状态=已完成 | 查询飞书表 |
| API 错误 | 爬虫服务宕机 | 状态=采集失败，发送告警 | 查看通知 |

**手动测试步骤:**

```bash
# 1. 在飞书 Keywords 表添加测试记录
#    keyword: "测试关键词"
#    status: "待采集"
#    min_likes: 100
#    crawl_limit: 5

# 2. 触发工作流 (Webhook 或等待定时)
curl -X POST "https://n8n.primetat.com/webhook/xhs-discovery" \
  -H "Content-Type: application/json" \
  -d '{"keyword_id": "recXXX"}'

# 3. 验证结果
# - Keywords 表: status 应变为 "已完成"
# - Topics 表: 应有新记录 (如果有匹配结果)
```

### 3.2 WF-Extraction (内容提取)

**测试场景:**

| 场景 | 输入 | 预期输出 | 验证方法 |
|------|------|----------|----------|
| 正常提取 | note_id 有效 | Source 表新增记录 | 查询飞书表 |
| 笔记不存在 | note_id 无效 | 状态=提取失败 | 查询飞书表 |
| 平台限制 | API 返回空数据 | 记录失败原因 | 查看日志 |

### 3.3 WF-Generation (AI 生成)

**测试场景:**

| 场景 | 输入 | 预期输出 | 验证方法 |
|------|------|----------|----------|
| 正常生成 | Source 记录 | Content 表新增图文 | 查询飞书表 |
| 大纲生成失败 | RedInk 超时 | 状态=生成失败 | 查看日志 |
| 图片下载失败 | 图片 URL 失效 | 部分成功，记录失败 | 查看日志 |

**手动测试步骤:**

```bash
# 1. 确保 Source 表有 status="待生成" 的记录

# 2. 触发工作流
curl -X POST "https://n8n.primetat.com/webhook/xhs-generation" \
  -H "Content-Type: application/json" \
  -d '{"source_id": "recXXX"}'

# 3. 验证结果
# - Source 表: status 应变为 "已生成"
# - Content 表: 应有新记录，包含 ai_title, ai_content, ai_images
```

### 3.4 WF-Publish (自动发布)

**测试场景:**

| 场景 | 输入 | 预期输出 | 验证方法 |
|------|------|----------|----------|
| 正常发布 | Content 记录 | Publish 表新增，小红书有笔记 | 查看平台 |
| Cookie 失效 | 登录过期 | 状态=发布失败，触发 Cookie 轮换 | 查看告警 |
| 内容审核失败 | 敏感词 | 状态=审核中 | 查看平台 |

---

## 四、端到端测试

### 4.1 完整流程测试

**测试流程:**

```
Keywords(待采集) → Discovery → Topics(待提取) → Extraction →
Source(待生成) → Generation → Content(待发布) → Publish →
Publish(已发布)
```

**测试步骤:**

```bash
# Step 1: 添加关键词
# 在飞书 Keywords 表添加:
# - keyword: "n8n测试_20251220"
# - status: "待采集"
# - min_likes: 50
# - crawl_limit: 3

# Step 2: 等待/触发 Discovery
# 检查 Topics 表是否有新记录

# Step 3: 等待/触发 Extraction
# 检查 Source 表是否有新记录

# Step 4: 等待/触发 Generation
# 检查 Content 表是否有 AI 生成的内容

# Step 5: 人工审核 (可选)
# 将 Content 记录 status 改为 "待发布"

# Step 6: 等待/触发 Publish
# 检查 Publish 表和小红书创作中心
```

### 4.2 测试检查清单

| 阶段 | 检查项 | 预期 | 实际 | 状态 |
|------|--------|------|------|------|
| Discovery | Keywords 状态更新 | 待采集→已完成 | | ☐ |
| Discovery | Topics 新增记录 | ≥1 条 | | ☐ |
| Extraction | Topics 状态更新 | 待提取→已提取 | | ☐ |
| Extraction | Source 新增记录 | ≥1 条 | | ☐ |
| Generation | Source 状态更新 | 待生成→已生成 | | ☐ |
| Generation | Content 新增记录 | 包含 ai_* 字段 | | ☐ |
| Publish | Content 状态更新 | 待发布→已发布 | | ☐ |
| Publish | Publish 新增记录 | 包含 note_url | | ☐ |

---

## 五、错误处理测试

### 5.1 服务不可用测试

```bash
# 测试: MediaCrawler 宕机时的行为
# 1. 停止爬虫服务 (测试环境)
ssh wade@124.221.251.8 "docker stop media-crawler-api"

# 2. 触发 Discovery 工作流
# 3. 验证:
#    - 工作流应捕获错误
#    - Keywords 状态应为 "采集失败"
#    - 应发送飞书告警通知

# 4. 恢复服务
ssh wade@124.221.251.8 "docker start media-crawler-api"
```

### 5.2 Cookie 失效测试

```bash
# 测试: Cookie 失效时的自动轮换
# 1. 确保飞书 Cookie 表有多个账号 (status=active)
# 2. 将当前使用的 Cookie 标记为失效
# 3. 触发需要登录的 API 调用
# 4. 验证:
#    - 系统应自动切换到下一个可用 Cookie
#    - 失效 Cookie 状态应更新
```

### 5.3 重试机制测试

```bash
# 测试: API 超时重试
# 1. 设置较短的超时时间
# 2. 模拟网络延迟
# 3. 验证:
#    - 应按配置重试 (默认 3 次)
#    - 重试间隔应符合配置
#    - 最终失败应正确记录
```

---

## 六、性能测试

### 6.1 并发测试

```bash
# 测试: 同时处理多个关键词
# 1. 在 Keywords 表添加 5 个待采集记录
# 2. 触发批量处理
# 3. 验证:
#    - 所有记录应被处理
#    - 无死锁或资源竞争
#    - 锁定机制正常工作
```

### 6.2 大数据量测试

```bash
# 测试: 单次采集大量结果
# 1. 设置 crawl_limit: 50
# 2. 使用热门关键词
# 3. 验证:
#    - 批量写入飞书正常
#    - 无超时错误
#    - 内存使用合理
```

---

## 七、测试脚本

### 7.1 快速连通性测试脚本

```bash
#!/bin/bash
# test_connectivity.sh

echo "=== n8n 工作流系统连通性测试 ==="
echo ""

# n8n 测试
echo "[1/4] 测试 n8n..."
N8N_RESULT=$(curl -s "https://n8n.primetat.com/healthz" 2>&1)
if [[ "$N8N_RESULT" == *"ok"* ]]; then
    echo "✅ n8n: 正常"
else
    echo "❌ n8n: 异常 - $N8N_RESULT"
fi

# MediaCrawler 测试
echo "[2/4] 测试 MediaCrawler..."
MC_RESULT=$(curl -s "http://124.221.251.8:8080/api/health" -H "X-API-Key: mc-api-key-2024-secure" 2>&1)
if [[ "$MC_RESULT" == *"healthy"* ]]; then
    echo "✅ MediaCrawler: 正常"
else
    echo "❌ MediaCrawler: 异常 - $MC_RESULT"
fi

# 人工搜索测试
echo "[3/4] 测试人工搜索 API..."
SEARCH_RESULT=$(curl -s -X POST "http://124.221.251.8:8080/api/search/human" \
  -H "X-API-Key: mc-api-key-2024-secure" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "测试", "limit": 1}' 2>&1)
if [[ "$SEARCH_RESULT" == *"success\":true"* ]]; then
    echo "✅ 人工搜索: 正常"
else
    echo "❌ 人工搜索: 异常"
fi

# 飞书 API 测试
echo "[4/4] 测试飞书 API..."
LARK_RESULT=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"cli_a98f34e454ba100c","app_secret":"YOUR_SECRET"}' 2>&1)
if [[ "$LARK_RESULT" == *"tenant_access_token"* ]]; then
    echo "✅ 飞书 API: 正常"
else
    echo "⚠️ 飞书 API: 需要配置 app_secret"
fi

echo ""
echo "=== 测试完成 ==="
```

### 7.2 工作流触发测试脚本

```bash
#!/bin/bash
# test_workflow.sh

WEBHOOK_BASE="https://n8n.primetat.com/webhook"

echo "=== 工作流触发测试 ==="

# Discovery 测试
echo "[1/4] 触发 Discovery..."
curl -s -X POST "$WEBHOOK_BASE/xhs-discovery" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
echo ""

# Extraction 测试
echo "[2/4] 触发 Extraction..."
curl -s -X POST "$WEBHOOK_BASE/xhs-extraction" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
echo ""

# Generation 测试
echo "[3/4] 触发 Generation..."
curl -s -X POST "$WEBHOOK_BASE/xhs-generation" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
echo ""

# Publish 测试
echo "[4/4] 触发 Publish..."
curl -s -X POST "$WEBHOOK_BASE/xhs-publish" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
echo ""

echo "=== 请在 n8n 面板查看执行结果 ==="
```

---

## 八、测试报告模板

### 测试执行记录

| 项目 | 信息 |
|------|------|
| 测试日期 | 2025-12-__ |
| 测试人员 | |
| n8n 版本 | 1.123.5 |
| MediaCrawler 版本 | v16 |
| 测试环境 | 生产 / 测试 |

### 测试结果汇总

| 类别 | 总数 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| 连通性测试 | 8 | | | |
| 单元测试 | 12 | | | |
| 端到端测试 | 8 | | | |
| 错误处理测试 | 6 | | | |
| **总计** | **34** | | | |

### 问题记录

| # | 问题描述 | 严重程度 | 状态 | 负责人 |
|---|----------|----------|------|--------|
| 1 | | 高/中/低 | 待修复/已修复 | |
| 2 | | | | |

---

## 九、附录

### A. 状态码参考

| 代码 | 含义 | 处理方式 |
|------|------|----------|
| -104 | 小红书权限限制 | 使用人工搜索 API |
| 461/471 | 需要验证码 | 更新 Cookie |
| 502 | 网关错误 | 检查 Caddy 配置 |
| CRAWLER_NOT_READY | 爬虫未初始化 | 调用 `/api/crawler/cookies` |

### B. 飞书表格状态流转

```
Keywords: 待采集 → 采集中 → 已完成/采集失败
Topics:   待提取 → 提取中 → 已提取/提取失败
Source:   待生成 → 生成中 → 已生成/生成失败
Content:  待审核 → 待发布 → 发布中 → 已发布/发布失败
```

### C. 相关文档

- [系统架构文档](./飞书%20+%20n8n%20+%20小红书%20自动化运营系统架构文档.md)
- [重构计划 v5.0](./REFACTORING_PLAN_v5.0.md)
- [n8n 官方文档](https://docs.n8n.io/)

---

*文档版本: v1.0 | 测试指南 | 2025-12-20*
