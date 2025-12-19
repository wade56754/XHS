# XHS 自动化运营系统重构方案 v5.0

> **版本**: v5.0 | **更新**: 2025-12-19
> **原则**: 最大化复用开源项目，最小化自定义开发

---

## 一、技术栈全景

### 1.1 核心组件

| 组件 | 项目 | 端口 | 用途 |
|------|------|------|------|
| **工作流引擎** | [n8n](https://github.com/n8n-io/n8n) | 5678 | 流程编排、调度 |
| **飞书节点** | [n8n-nodes-feishu-lite](https://github.com/other-blowsnow/n8n-nodes-feishu-lite) | - | 飞书多维表格操作 |
| **内容采集** | [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | 8080 | 小红书数据爬取 |
| **AI生成** | [RedInk](https://github.com/HisMax/RedInk) | 12398 | 小红书风格图文 |
| **自动发布** | [social-auto-upload](https://github.com/dreammis/social-auto-upload) | 5409 | 多平台发布 |

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         n8n 工作流引擎 (:5678)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ WF-Discovery│  │WF-Extraction│  │WF-Generation│  │ WF-Publish │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
└─────────┼────────────────┼────────────────┼───────────────┼────────┘
          │                │                │               │
          ▼                ▼                ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐
│ MediaCrawler    │ │   飞书      │ │   RedInk    │ │social-auto-upload│
│ API (:8080)     │ │ 多维表格    │ │ API (:12398)│ │ API (:5409)      │
│                 │ │             │ │             │ │                  │
│ /api/search     │ │ n8n-nodes-  │ │ /outline    │ │ /upload          │
│ /api/note       │ │ feishu-lite │ │ /generate   │ │ /status          │
│ /api/creator    │ │             │ │ /images     │ │ /cookies         │
└────────┬────────┘ └──────┬──────┘ └──────┬──────┘ └────────┬─────────┘
         │                 │               │                 │
         ▼                 ▼               ▼                 ▼
     ┌───────┐       ┌──────────┐    ┌──────────┐      ┌──────────┐
     │ 小红书 │       │ 飞书云端  │    │ AI服务   │      │ 小红书   │
     │ 平台   │       │ 表格存储  │    │OpenAI/   │      │ 创作中心 │
     └───────┘       └──────────┘    │Gemini    │      └──────────┘
                                     └──────────┘
```

---

## 二、各组件详细分析

### 2.1 n8n-nodes-feishu-lite (飞书节点)

**安装方法:**
```bash
# n8n 社区节点安装
npm install n8n-nodes-feishu-lite
```

**支持的操作 (共100+):**

| 模块 | 操作数 | 关键功能 |
|------|--------|----------|
| 多维表格 | 28 | 记录CRUD、字段管理、表格解析 |
| 电子表格 | 24 | 行列操作、单元格格式化 |
| 日历 | 16 | 日程管理、参与人管理 |
| 知识库 | 12 | 空间管理、节点操作 |
| 消息 | 8 | 发送、回复、批量操作 |
| 云文档 | 6 | 文档创建、块级编辑 |

**多维表格关键操作:**

```yaml
# 查询记录
operation: "bitable:table:record:query"
params:
  app_token: "Gq93bAlZ7aSSclsLKdTcYCO2nwh"
  table_id: "tblE2SypBdIhJVrR"
  filter:
    conditions:
      - field_name: "status"
        operator: "is"
        value: ["待采集"]

# 更新记录
operation: "bitable:table:record:update"
params:
  record_id: "{{$json.record_id}}"
  fields:
    status: "采集中"
    locked_at: "{{$now.toISO()}}"

# 批量创建
operation: "bitable:table:record:batchCreate"
params:
  records: "{{$json.records}}"
```

### 2.2 MediaCrawler (小红书爬虫)

**API 端点 (已部署 :8080):**

| 端点 | 方法 | 状态 | 用途 |
|------|------|------|------|
| `/api/health` | GET | ✅ | 健康检查 |
| `/api/search/human` | POST | ✅ | 人工模拟搜索 (绕过-104) |
| `/api/note/detail` | POST | ⚠️ | 笔记详情 (平台限制) |
| `/api/creator/{id}` | GET | ✅ | 创作者信息 |
| `/api/crawler/cookies` | POST | ✅ | Cookie 管理 |
| `/api/login/qrcode` | POST | ✅ | QR 登录 |

**请求示例:**
```javascript
// n8n HTTP Request 节点配置
{
  method: "POST",
  url: "http://124.221.251.8:8080/api/search/human",
  headers: { "X-API-Key": "dev-key" },
  body: { keyword: "穿搭", limit: 10 }
}
```

### 2.3 RedInk (AI图文生成)

**工作流程:**
```
输入话题 → /api/outline (10-20秒) → 大纲JSON
    ↓
大纲 → /api/generate (SSE流式) → 生成图片
    ↓
/api/images/{task_id}/{index}.png → 下载图片
```

**API 端点:**

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/outline` | POST | 生成内容大纲 |
| `/api/generate` | POST | 生成图片 (SSE) |
| `/api/images/{task_id}/{index}.png` | GET | 获取生成的图片 |
| `/api/history` | GET | 历史记录 |
| `/api/config` | GET/POST | 配置管理 |

**配置文件:**
```yaml
# text_providers.yaml - 文本生成
openai_compatible:
  api_key: "sk-xxx"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4"

# image_providers.yaml - 图片生成
google_genai:
  api_key: "xxx"
  high_concurrency: false  # GCP试用关闭
```

### 2.4 social-auto-upload (自动发布)

**支持平台:**
- ✅ 小红书
- ✅ 抖音
- ✅ 视频号
- ✅ Bilibili
- ✅ 快手
- ✅ TikTok

**API 端点 (:5409):**

| 端点 | 方法 | 用途 |
|------|------|------|
| `/upload` | POST | 上传发布 |
| `/status` | GET | 发布状态 |
| `/cookies` | GET/POST | Cookie 管理 |

**小红书发布流程:**
```python
# 1. 获取 Cookie
python examples/get_xhs_cookie.py

# 2. 准备视频/图片
videos/
├── content.mp4
└── content.txt  # 标题和标签

# 3. 发布
python examples/upload_video_to_xhs.py
```

---

## 三、重构方案

### 3.1 整体架构调整

**从:**
```
n8n → HTTP Request → 飞书 API
n8n → 自定义 /api/publish
```

**改为:**
```
n8n → n8n-nodes-feishu-lite → 飞书
n8n → social-auto-upload API → 小红书发布
```

### 3.2 工作流重新设计

#### WF-Main (主控制器)

```
┌─────────────────────────────────────────────────────────────────┐
│ 触发器: Schedule (每5分钟) + Webhook (手动)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 飞书节点: 并行查询4个表状态                                       │
│ ├─ Keywords (status='待采集')                                    │
│ ├─ Topics (status='待提取')                                      │
│ ├─ Source (status='待生成')                                      │
│ └─ Content (status='待发布')                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Code节点: 优先级分发                                             │
│ 优先级: Publish(4) > Generation(3) > Extraction(2) > Discovery(1)│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Switch节点: 路由到子工作流                                       │
│ ├─ discovery → Execute WF-Discovery                             │
│ ├─ extraction → Execute WF-Extraction                           │
│ ├─ generation → Execute WF-Generation                           │
│ └─ publish → Execute WF-Publish                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### WF-Discovery (内容发现)

```yaml
节点流程:
  1. 飞书节点: 锁定记录 (status → 采集中)
  2. HTTP Request: POST /api/search/human
  3. Code节点: 过滤 (min_likes)
  4. 飞书节点: 批量创建 Topics
  5. 飞书节点: 更新 Keywords (status → 已采集)

使用的组件:
  - n8n-nodes-feishu-lite: 记录操作
  - MediaCrawler: /api/search/human
```

#### WF-Generation (AI生成)

```yaml
节点流程:
  1. 飞书节点: 锁定记录 (status → 生成中)
  2. 飞书节点: 获取 Prompts 模板
  3. HTTP Request: POST RedInk /api/outline
  4. HTTP Request: POST RedInk /api/generate (SSE)
  5. HTTP Request: GET RedInk /api/images/{task_id}/*.png
  6. 飞书节点: 上传图片到云空间
  7. 飞书节点: 创建 Content 记录
  8. 飞书节点: 更新 Source (status → 已生成)

使用的组件:
  - n8n-nodes-feishu-lite: 记录操作 + 素材上传
  - RedInk: /outline + /generate + /images
```

#### WF-Publish (自动发布)

```yaml
节点流程:
  1. 飞书节点: 锁定记录 (status → 发布中)
  2. 飞书节点: 下载图片附件
  3. HTTP Request: POST social-auto-upload /upload
  4. Wait节点: 等待发布完成
  5. HTTP Request: GET social-auto-upload /status
  6. 飞书节点: 创建 Publish 记录
  7. 飞书节点: 更新 Content (status → 已发布)
  8. 飞书节点: 发送通知消息

使用的组件:
  - n8n-nodes-feishu-lite: 记录操作 + 消息通知
  - social-auto-upload: /upload + /status
```

### 3.3 部署架构

```yaml
# docker-compose.yml
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    ports: ["5678:5678"]
    volumes:
      - n8n_data:/home/node/.n8n
    environment:
      - N8N_COMMUNITY_PACKAGES_ENABLED=true

  mediacrawler:
    image: media-crawler-api:v16
    ports: ["8080:8080"]
    volumes:
      - ./browser_data:/app/browser_data
    environment:
      - API_KEY=dev-key

  redink:
    image: histonemax/redink:latest
    ports: ["12398:12398"]
    volumes:
      - ./redink/history:/app/history
      - ./redink/output:/app/output

  social-upload:
    image: gzxy/social-auto-upload:latest
    ports: ["5409:5409"]
    volumes:
      - ./social/cookies:/app/cookiesFile
      - ./social/videos:/app/videoFile
```

---

## 四、实施步骤

### Phase 1: 环境准备 (Day 1)

```bash
# 1. 安装飞书节点
ssh wade@136.110.80.154
cd /home/debian/.n8n
npm install n8n-nodes-feishu-lite
sudo systemctl restart n8n

# 2. 部署 RedInk
docker run -d --name redink \
  -p 12398:12398 \
  -v ./history:/app/history \
  histonemax/redink:latest

# 3. 部署 social-auto-upload
docker run -d --name social-upload \
  -p 5409:5409 \
  gzxy/social-auto-upload:latest
```

### Phase 2: 飞书凭证配置 (Day 1)

```javascript
// n8n 凭证配置
{
  name: "飞书凭证",
  type: "feishuCredentialsApi",
  data: {
    appId: "cli_a98f34e454ba100c",
    appSecret: "C0mABqwJAOAfhGudb8qfCbwool64Q0Tn"
  }
}
```

### Phase 3: 工作流创建 (Day 2-3)

| 工作流 | 节点数 | 关键组件 |
|--------|--------|----------|
| WF-Main | 12 | Schedule, Webhook, 飞书节点, Switch |
| WF-Discovery | 8 | 飞书节点, MediaCrawler HTTP |
| WF-Extraction | 6 | 飞书节点, MediaCrawler HTTP |
| WF-Generation | 10 | 飞书节点, RedInk HTTP |
| WF-Publish | 9 | 飞书节点, social-upload HTTP |
| WF-CookieManager | 5 | 飞书节点, MediaCrawler HTTP |
| WF-ErrorHandler | 4 | 飞书节点 (消息通知) |

### Phase 4: 测试验收 (Day 4)

```bash
# 端到端测试
1. 添加关键词到飞书 → 触发 Discovery
2. 检查 Topics 表 → 触发 Extraction
3. 检查 Source 表 → 触发 Generation
4. 检查 Content 表 → 触发 Publish
5. 检查 Publish 表 + 小红书创作中心
```

---

## 五、n8n 飞书节点使用示例

### 5.1 查询待处理记录

```json
{
  "parameters": {
    "operation": "bitable:table:record:query",
    "app_token": "={{$env.LARK_APP_TOKEN}}",
    "table_id": "={{$env.KEYWORDS_TABLE_ID}}",
    "filter": {
      "conditions": [
        {
          "field_name": "status",
          "operator": "is",
          "value": ["待采集"]
        }
      ],
      "conjunction": "and"
    },
    "page_size": 10
  },
  "credentials": {
    "feishuCredentialsApi": "飞书凭证"
  }
}
```

### 5.2 更新记录状态

```json
{
  "parameters": {
    "operation": "bitable:table:record:update",
    "app_token": "={{$env.LARK_APP_TOKEN}}",
    "table_id": "={{$env.KEYWORDS_TABLE_ID}}",
    "record_id": "={{$json.record_id}}",
    "fields": {
      "status": "采集中",
      "locked_at": "={{$now.toISO()}}",
      "locked_by": "={{$workflow.id}}"
    }
  }
}
```

### 5.3 批量创建记录

```json
{
  "parameters": {
    "operation": "bitable:table:record:batchCreate",
    "app_token": "={{$env.LARK_APP_TOKEN}}",
    "table_id": "={{$env.TOPICS_TABLE_ID}}",
    "records": "={{$json.topics}}"
  }
}
```

### 5.4 发送飞书通知

```json
{
  "parameters": {
    "operation": "message:send",
    "receive_id_type": "chat_id",
    "receive_id": "={{$env.NOTIFY_CHAT_ID}}",
    "msg_type": "interactive",
    "content": {
      "elements": [
        {
          "tag": "div",
          "text": {
            "content": "✅ 发布成功: {{$json.title}}",
            "tag": "lark_md"
          }
        }
      ]
    }
  }
}
```

---

## 六、对比表

### 6.1 重构前后对比

| 方面 | 重构前 | 重构后 |
|------|--------|--------|
| 飞书操作 | HTTP Request 直接调 API | n8n-nodes-feishu-lite 节点 |
| 发布功能 | 自定义 /api/publish | social-auto-upload 服务 |
| 工作流创建 | 手动写 JSON | 使用 n8n UI 或脚本生成 |
| AI生成 | ✅ RedInk | ✅ RedInk (不变) |
| 爬虫 | ✅ MediaCrawler | ✅ MediaCrawler (不变) |

### 6.2 优势

| 优势 | 说明 |
|------|------|
| 飞书节点更稳定 | 专门维护，支持100+操作 |
| 发布更可靠 | social-auto-upload 支持7个平台 |
| 维护成本低 | 复用开源项目，无需自己开发 |
| 功能更丰富 | 飞书消息、日历、文档等均可集成 |

---

## 七、关键配置清单

### 环境变量 (.env)

```bash
# 飞书
LARK_APP_ID=cli_a98f34e454ba100c
LARK_APP_SECRET=C0mABqwJAOAfhGudb8qfCbwool64Q0Tn
LARK_APP_TOKEN=Gq93bAlZ7aSSclsLKdTcYCO2nwh

# 飞书表格 ID
KEYWORDS_TABLE_ID=tblE2SypBdIhJVrR
TOPICS_TABLE_ID=tblPCp5gqgVFnhLc
SOURCE_TABLE_ID=tblMYjwzOkYpW4AX
CONTENT_TABLE_ID=tblp3iSuo0dasTtg
PUBLISH_TABLE_ID=tblp3iSuo0dasTtg
COOKIE_TABLE_ID=tblYa2d2a5lypzqz

# 服务地址
MEDIACRAWLER_URL=http://124.221.251.8:8080
REDINK_URL=http://localhost:12398
SOCIAL_UPLOAD_URL=http://localhost:5409

# n8n
N8N_URL=https://xhs.adpilot.club
```

### 服务端口

| 服务 | 端口 | 用途 |
|------|------|------|
| n8n | 5678 | 工作流引擎 |
| MediaCrawler | 8080 | 小红书爬虫 |
| RedInk | 12398 | AI图文生成 |
| social-auto-upload | 5409 | 自动发布 |

---

*文档版本: v5.0 | 基于开源组件重构方案 | 2025-12-19*
