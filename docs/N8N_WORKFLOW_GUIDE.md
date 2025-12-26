# n8n 工作流使用指南

## 概述

本项目包含 8 个核心 n8n 工作流，用于 XHS（小红书）内容自动化发布系统。

---

## 工作流架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        WF-Main (主控制器)                         │
│  Schedule Trigger ──┐                                           │
│  Webhook ──────────┴→ Merge → Prepare → Switch ─┬→ Discovery    │
│                                                  ├→ Extraction   │
│                                                  ├→ Generation   │
│                                                  └→ Publish      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        子工作流                                   │
├─────────────────────────────────────────────────────────────────┤
│  WF-Discovery    │ 关键词搜索 → 话题发现 → 写入飞书              │
│  WF-Extraction   │ 笔记详情 → 内容提取 → 写入飞书                │
│  WF-Generation   │ 构建提示 → AI生成 → 写入飞书                  │
│  WF-Publish      │ 准备发布 → 写入飞书发布队列                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        支撑工作流                                 │
├─────────────────────────────────────────────────────────────────┤
│  WF-CookieManager  │ 定时检查 Cookie 状态 → 写入日志             │
│  WF-ErrorHandler   │ 错误捕获 → 格式化 → 写入日志                │
│  RedInk-Full-Pipeline │ 图文生成 (Webhook 触发)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 工作流详情

### 1. RedInk-Full-Pipeline (图文生成)

**状态**: ✅ 激活
**ID**: `3WPIC1h6mu9eO154`
**触发方式**: Webhook POST
**节点数**: 8

#### 功能
调用 RedInk 服务生成小红书风格的图文内容。

#### Webhook 端点
```
POST https://n8n.primetat.com/webhook/redink-full
```

#### 请求参数
```json
{
  "topic": "主题内容",
  "style": "干货分享",      // 可选，默认: 干货分享
  "page_count": 3           // 可选，默认: 6
}
```

#### 响应示例
```json
{
  "success": true,
  "task_id": "task_31d80790",
  "images": [
    {"index": 0, "url": "http://136.110.80.154:12398/api/images/task_31d80790/0.png"},
    {"index": 1, "url": "http://136.110.80.154:12398/api/images/task_31d80790/1.png"},
    {"index": 2, "url": "http://136.110.80.154:12398/api/images/task_31d80790/2.png"}
  ],
  "image_count": 3,
  "message": "图片生成成功"
}
```

#### 测试命令
```bash
curl -X POST "https://n8n.primetat.com/webhook/redink-full" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python编程技巧", "style": "干货分享", "page_count": 3}'
```

---

### 2. WF-Main-20251220 (主控制器)

**状态**: 未激活
**ID**: `Cx6LtrF1sBElLjms`
**触发方式**: Schedule + Webhook
**节点数**: 9

#### 功能
主控制器工作流，根据 action 参数路由到不同子工作流。

#### Webhook 端点
```
POST https://n8n.primetat.com/webhook/<webhook-id>
```

#### 请求参数
```json
{
  "action": "discovery",     // discovery | extraction | generation | publish
  "params": {
    // action 对应的参数
  }
}
```

#### 路由逻辑
| action | 目标工作流 | 说明 |
|--------|-----------|------|
| `discovery` | WF-Discovery | 内容发现 |
| `extraction` | WF-Extraction | 内容提取 |
| `generation` | WF-Generation | AI 内容生成 |
| `publish` | WF-Publish | 内容发布 |

---

### 3. WF-Discovery-20251220 (内容发现)

**状态**: 未激活
**ID**: `Mh4qedUD85tyW6WW`
**触发方式**: Execute Workflow Trigger
**节点数**: 6

#### 功能
搜索小红书关键词，发现热门话题并写入飞书 Topics 表。

#### 流程
```
触发 → 搜索XHS → 格式化结果 → 检查结果 → 拆分话题 → 写入飞书
```

#### 输入参数
```json
{
  "keyword": "搜索关键词",
  "limit": 10
}
```

---

### 4. WF-Extraction-20251220 (内容提取)

**状态**: 未激活
**ID**: `3QC6mnfnceEYmwjU`
**触发方式**: Execute Workflow Trigger
**节点数**: 6

#### 功能
获取小红书笔记详情，提取内容并写入飞书 Source 表。

#### 流程
```
触发 → 获取笔记详情 → 格式化素材 → 检查结果 → 拆分素材 → 写入飞书
```

#### 输入参数
```json
{
  "note_id": "笔记ID",
  "xsec_token": "安全令牌"
}
```

---

### 5. WF-Generation-20251220 (AI内容生成)

**状态**: 未激活
**ID**: `wBtTJ1ldleFIKdjp`
**触发方式**: Execute Workflow Trigger
**节点数**: 5

#### 功能
使用 AI 生成内容并写入飞书 Content 表。

#### 流程
```
触发 → 构建提示词 → 调用AI生成 → 格式化内容 → 写入飞书
```

#### 输入参数
```json
{
  "source_id": "素材ID",
  "prompt_template": "提示词模板"
}
```

---

### 6. WF-Publish-20251220 (内容发布)

**状态**: 未激活
**ID**: `Q4J82Vgni3c2s4Jq`
**触发方式**: Execute Workflow Trigger
**节点数**: 3

#### 功能
准备发布数据并写入飞书 Publish 表。

#### 流程
```
触发 → 准备发布数据 → 写入飞书
```

#### 输入参数
```json
{
  "content_id": "内容ID",
  "publish_time": "发布时间"
}
```

---

### 7. WF-CookieManager-20251220 (Cookie管理)

**状态**: 未激活
**ID**: `CWrk327laiU7JYzi`
**触发方式**: Schedule Trigger
**节点数**: 4

#### 功能
定时检查 XHS Cookie 登录状态，记录日志到飞书。

#### 流程
```
定时触发 → 检查登录状态 → 格式化状态 → 写入日志
```

#### 配置
- 默认每 30 分钟检查一次
- 检查 MediaCrawler API 的登录状态

---

### 8. WF-ErrorHandler-20251220 (错误处理)

**状态**: 未激活
**ID**: `Tvc4kjJVbCsniXUD`
**触发方式**: Error Trigger
**节点数**: 3

#### 功能
捕获其他工作流的错误，格式化后写入飞书日志表。

#### 流程
```
错误触发 → 格式化错误 → 写入日志
```

---

## 验证结果

| 工作流 | 验证状态 | 节点数 | 说明 |
|--------|---------|--------|------|
| RedInk-Full-Pipeline | ⚠️ 警告 | 8 | responseNode 模式配置警告 |
| WF-Main-20251220 | ✅ 通过 | 9 | 主控制器 |
| WF-Discovery-20251220 | ✅ 通过 | 7 | 使用 HTTP Request 调用飞书 API |
| WF-Extraction-20251220 | ✅ 通过 | 7 | 使用 HTTP Request 调用飞书 API |
| WF-Generation-20251220 | ✅ 通过 | 6 | 使用 HTTP Request 调用飞书 API |
| WF-Publish-20251220 | ✅ 通过 | 4 | 使用 HTTP Request 调用飞书 API |
| WF-CookieManager-20251220 | ✅ 通过 | 5 | 使用 HTTP Request 调用飞书 API |
| WF-ErrorHandler-20251220 | ✅ 通过 | 4 | 使用 HTTP Request 调用飞书 API |

> **修复说明**: 2025-12-20 将飞书社区节点 (`n8n-nodes-feishu-lark.lark`) 替换为 HTTP Request 节点，直接调用飞书 API，避免凭证配置问题。

---

## 测试结果

### RedInk-Full-Pipeline 测试
```
测试时间: 2025-12-20 08:56:49
请求: {"topic": "Python 编程入门技巧", "style": "干货分享", "page_count": 3}
响应时间: 23.4 秒
结果: ✅ 成功生成 3 张图片
```

### WF-Discovery 测试
```
测试时间: 2025-12-20 17:27:38
请求: {"keyword": "Claude", "limit": 2}
响应时间: 40.2 秒
执行节点: 7/7 全部成功
结果: ✅ 搜索到笔记并成功写入飞书
飞书记录ID: recv5Uv7gJ5qhX
```

> **修复历史**:
> 1. 修复连接类型 (type: "0" → "main")
> 2. 更新 App Token 和 Table ID
> 3. 修复字段映射 (title → preview_title 等)
> 4. 修复 URL 字段格式 (string → {link, text})

---

## 快速开始

### 1. 测试 RedInk 图文生成
```bash
# 生成小红书风格图文
curl -X POST "https://n8n.primetat.com/webhook/redink-full" \
  -H "Content-Type: application/json" \
  -d '{"topic": "你的主题", "page_count": 3}'
```

### 2. 在 n8n UI 中激活工作流
1. 访问 https://n8n.primetat.com
2. 找到需要激活的工作流
3. 点击右上角开关激活

### 3. 配置飞书凭证
确保 n8n 中已配置飞书凭证：
- Feishu App Token
- Feishu Table IDs

---

## 飞书表格映射

**App Token**: `Gq93bAlZ7aSSclsLKdTcYCO2nwh`

| 表格 | Table ID | 对应工作流 |
|------|----------|-----------|
| tbl_candidate | tbleFs8pwdee2DWX | WF-Discovery |
| tbl_source | tblsqXtjfMxzhUu2 | WF-Extraction |
| tbl_content | tblEMrCOGQuC36MU | WF-Generation |
| tbl_cookie | tblYa2d2a5lypzqz | WF-CookieManager |
| tbl_logs | tbl4asiKhYyzcDPX | WF-ErrorHandler |

---

## 常见问题

### Q: Feishu 节点验证失败怎么办？
A: 这是验证工具的限制，不影响实际运行。确保 n8n 服务器已安装 `n8n-nodes-feishu-lark` 社区节点。

### Q: 如何安装 Feishu 社区节点？
```bash
# 在 n8n 容器中
cd /home/node/.n8n
npm install n8n-nodes-feishu-lark
```

### Q: RedInk 生成超时怎么办？
A: 默认超时为 3 分钟。如果生成复杂内容，可能需要更长时间。检查：
1. RedInk 服务是否正常运行
2. Gemini API 配额是否充足

### Q: 如何调试工作流？
1. 在 n8n UI 中手动执行工作流
2. 查看每个节点的输入/输出
3. 检查 WF-ErrorHandler 的日志

---

## 服务器信息

| 服务 | 地址 | 用途 |
|------|------|------|
| n8n | https://n8n.primetat.com | 工作流引擎 |
| RedInk | http://136.110.80.154:12398 | 图文生成 |
| MediaCrawler | http://124.221.251.8:8080 | XHS 数据采集 |

---

## 更新日志

- **2025-12-20 (v2)**: 修复 6 个工作流的飞书节点，改用 HTTP Request 直接调用飞书 API
- **2025-12-20**: 创建 8 个核心工作流，测试 RedInk-Full-Pipeline
- **2025-12-19**: 修复 RedInk-Full-Pipeline IF 节点和 SSE 解析问题
