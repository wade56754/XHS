# RedInk 集成方案

> 目标：将 RedInk 图文生成能力接入现有系统，**不改变现有业务逻辑**

## 一、集成架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        现有系统 (保持不变)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  热点抓取 → 选题生成 → 内容创作 → AI审核 → 飞书存储 → 人工发布        │
│     ↓                                                               │
│  [hot_topics表]              [content_records表]                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 新增调用入口 (可选)
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     RedInk 服务 (独立部署)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [输入] 标题/主题 → 大纲生成 → 封面图 → 内容图(并发) → [输出] 图文    │
│                                                                     │
│  端口: 12398                                                         │
│  API: /api/generate (POST)                                          │
│       /api/status/{task_id} (GET)                                   │
│       /api/images/{task_id} (GET)                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 二、核心原则

| 原则 | 说明 |
|------|------|
| **独立部署** | RedInk 作为独立 Docker 容器运行，不侵入现有服务 |
| **可选调用** | 现有流程完全不变，图文生成作为额外能力 |
| **异步解耦** | 通过任务ID轮询/SSE获取结果，不阻塞主流程 |
| **数据隔离** | RedInk 生成的图片存储在独立目录，按需同步到飞书 |

## 三、部署方案

### 3.1 Docker Compose 扩展

在现有 `docker-compose.yml` 中新增 RedInk 服务：

```yaml
# docker-compose.yml (追加内容)
services:
  # ... 现有服务保持不变 ...

  redink:
    image: redink:latest
    build:
      context: ./redink
      dockerfile: Dockerfile
    container_name: redink
    ports:
      - "12398:12398"
    volumes:
      - ./redink/history:/app/history      # 历史记录持久化
      - ./redink/images:/app/images        # 生成图片存储
      - ./redink/config:/app/config        # 配置文件
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    networks:
      - n8n-network
    restart: unless-stopped
```

### 3.2 目录结构

```
D:\project\XHS\
├── docker-compose.yml        # 追加 redink 服务
├── redink/                   # 新增目录 (克隆 RedInk 项目)
│   ├── backend/
│   ├── frontend/
│   ├── Dockerfile
│   ├── text_providers.yaml   # AI文本配置
│   ├── image_providers.yaml  # AI图像配置
│   └── history/              # 生成历史
└── ... (现有文件保持不变)
```

### 3.3 配置文件

```yaml
# redink/text_providers.yaml
active_provider: claude

providers:
  claude:
    type: openai_compatible
    api_key: ${CLAUDE_API_KEY}
    base_url: https://api.anthropic.com/v1
    model: claude-sonnet-4-20250514
```

```yaml
# redink/image_providers.yaml
active_provider: gemini

providers:
  gemini:
    type: google_genai
    api_key: ${GEMINI_API_KEY}
    model: gemini-2.0-flash-exp
    high_concurrency: false
```

## 四、API 接口设计

### 4.1 图文生成接口

```http
POST http://localhost:12398/api/generate
Content-Type: application/json

{
  "topic": "熬夜后急救护肤法，亲测有效的5个步骤",
  "style": "干货分享",           // 可选: 干货分享/种草推荐/经验总结
  "page_count": 6,              // 可选: 6-9页，默认6
  "reference_image": "base64...", // 可选: 风格参考图
  "callback_url": "http://n8n:5678/webhook/redink-callback"  // 可选: 完成回调
}
```

**响应**:
```json
{
  "success": true,
  "task_id": "task_20241218_001",
  "status": "processing",
  "estimated_time": 60
}
```

### 4.2 状态查询接口

```http
GET http://localhost:12398/api/status/task_20241218_001
```

**响应**:
```json
{
  "task_id": "task_20241218_001",
  "status": "completed",        // pending/processing/completed/failed
  "progress": {
    "current": 6,
    "total": 6,
    "stage": "内容图生成完成"
  },
  "result": {
    "cover_url": "/images/task_20241218_001/cover.jpg",
    "pages": [
      "/images/task_20241218_001/page_1.jpg",
      "/images/task_20241218_001/page_2.jpg",
      // ...
    ],
    "outline": [
      {"type": "cover", "title": "熬夜急救护肤", "content": "..."},
      {"type": "content", "title": "第一步：卸妆清洁", "content": "..."},
      // ...
    ]
  }
}
```

### 4.3 图片下载接口

```http
GET http://localhost:12398/api/images/task_20241218_001?format=zip
```

返回所有图片的 ZIP 压缩包。

## 五、N8N 集成方式

### 5.1 方式一：独立工作流 (推荐)

创建新工作流 `WF-RedInk-Generate`，与现有流程**并行**运行：

```
┌──────────────────────────────────────────────────────────────┐
│  WF-RedInk-Generate (新建，独立工作流)                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [手动触发/Webhook] → [调用RedInk] → [轮询状态] → [存入飞书]  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**工作流节点设计**:

```
1. Webhook 触发
   - 接收: { topic: "xxx", style: "xxx" }

2. HTTP Request - 调用 RedInk
   - URL: http://redink:12398/api/generate
   - Method: POST
   - Body: {{ $json }}

3. Wait 节点
   - 等待 10 秒

4. HTTP Request - 查询状态
   - URL: http://redink:12398/api/status/{{ $json.task_id }}

5. IF 节点
   - 条件: status == "completed"
   - True → 继续
   - False → 返回 Wait 节点 (循环)

6. HTTP Request - 下载图片
   - URL: http://redink:12398/api/images/{{ $json.task_id }}

7. HTTP Request - 上传到飞书
   - 将图片作为附件上传到 content_records 表

8. 完成通知
   - 发送飞书消息通知
```

### 5.2 方式二：嵌入现有流程 (可选扩展)

在 `WF-Generation` 审核通过后，**可选**调用 RedInk：

```
现有流程:
选题生成 → 内容创作 → AI审核 → [score >= 85?]
                                    │
                                    ├─ Yes → 飞书存储 → [需要配图?]
                                    │                        │
                                    │                        ├─ Yes → 调用 RedInk
                                    │                        │            ↓
                                    │                        │        等待完成
                                    │                        │            ↓
                                    │                        │        图片存入飞书
                                    │                        │
                                    │                        └─ No → 结束
                                    │
                                    └─ No → 人工审核队列
```

**关键**: 通过 IF 节点判断是否需要配图，默认为 No，不影响现有流程。

### 5.3 方式三：飞书多维表格触发

利用飞书多维表格的「按钮」字段：

```
content_records 表新增字段:
├── generate_images (按钮类型)
│   └── 点击触发 Webhook → WF-RedInk-Generate
│
├── image_status (单选: 待生成/生成中/已完成/失败)
│
└── generated_images (附件类型)
    └── RedInk 生成的图片
```

**用户操作流程**:
1. 查看飞书表中审核通过的内容
2. 点击「生成配图」按钮
3. 后台自动调用 RedInk
4. 完成后图片自动填入附件字段

## 六、数据流转设计

### 6.1 输入来源

| 来源 | 触发方式 | 输入数据 |
|------|----------|----------|
| N8N Webhook | 手动/定时 | `{ topic, style }` |
| 飞书按钮 | 用户点击 | 从表格读取 `title` |
| API 直接调用 | 外部系统 | 完整请求体 |

### 6.2 输出目标

| 目标 | 存储内容 | 格式 |
|------|----------|------|
| RedInk 本地 | 原始图片 | JPG, 1080x1440 |
| 飞书附件 | 压缩图片 | JPG, ≤500KB |
| content_records | 图片URL列表 | JSON数组 |

### 6.3 字段映射

```javascript
// N8N Function 节点 - 数据转换
const redinkResult = $json.result;

return {
  // 写入飞书 content_records 表
  fields: {
    "generated_images": redinkResult.pages.map(p => ({
      file_token: uploadToFeishu(p)  // 先上传获取 token
    })),
    "cover_image": [{
      file_token: uploadToFeishu(redinkResult.cover_url)
    }],
    "image_status": "已完成",
    "image_outline": JSON.stringify(redinkResult.outline)
  }
};
```

## 七、错误处理

### 7.1 RedInk 服务不可用

```javascript
// N8N Error Trigger
if (error.code === 'ECONNREFUSED') {
  // RedInk 服务未启动，记录日志但不阻塞主流程
  await logToFeishu('WARN', 'RedInk服务不可用，跳过图片生成');
  return { skip_images: true };
}
```

### 7.2 生成超时

```javascript
// 设置最大等待时间 5 分钟
const MAX_WAIT = 300000;
let elapsed = 0;

while (status !== 'completed' && elapsed < MAX_WAIT) {
  await wait(10000);
  elapsed += 10000;
  status = await checkStatus(taskId);
}

if (elapsed >= MAX_WAIT) {
  await logToFeishu('ERROR', `RedInk任务超时: ${taskId}`);
}
```

### 7.3 生成失败

```javascript
if (status === 'failed') {
  // 更新飞书状态字段
  await updateFeishuRecord(recordId, {
    "image_status": "生成失败",
    "image_error": result.error_message
  });

  // 发送告警
  await sendFeishuAlert(`图片生成失败: ${result.error_message}`);
}
```

## 八、部署步骤

### Step 1: 克隆 RedInk 项目

```bash
cd D:\project\XHS
git clone https://github.com/HisMax/RedInk.git redink
```

### Step 2: 配置 API 密钥

```bash
cd redink
cp text_providers.yaml.example text_providers.yaml
cp image_providers.yaml.example image_providers.yaml

# 编辑配置文件，填入 API Key
```

### Step 3: 更新 Docker Compose

```bash
# 在现有 docker-compose.yml 追加 redink 服务配置
# (参考 3.1 节)
```

### Step 4: 启动服务

```bash
docker-compose up -d redink

# 验证服务
curl http://localhost:12398/api/health
```

### Step 5: 创建 N8N 工作流

1. 导入 `WF-RedInk-Generate` 工作流模板
2. 配置 Webhook URL
3. 测试端到端流程

### Step 6: 配置飞书表格 (可选)

1. 在 `content_records` 表添加字段
2. 配置按钮触发 Webhook

## 九、验收标准

| 检查项 | 预期结果 |
|--------|----------|
| RedInk 服务健康 | `GET /api/health` 返回 200 |
| 图文生成成功 | 输入主题，60秒内返回6张图 |
| N8N 调用正常 | Webhook 触发后完整执行 |
| 飞书存储正常 | 图片出现在附件字段 |
| 现有流程无影响 | 关闭 RedInk 后，原流程正常 |

## 十、后续扩展

### 10.1 Phase 1: 基础集成 (本方案)
- RedInk 独立部署
- N8N 手动触发生成
- 图片存入飞书

### 10.2 Phase 2: 自动化增强
- 审核通过自动触发图片生成
- 智能匹配内容风格
- 批量生成支持

### 10.3 Phase 3: 深度整合
- RedInk 大纲与 CONTENT_GEN 融合
- 统一 Prompt 管理
- A/B 测试图片风格

---

## 附录：快速验证命令

```bash
# 1. 启动 RedInk
docker-compose up -d redink

# 2. 测试生成
curl -X POST http://localhost:12398/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "熬夜后急救护肤法"}'

# 3. 查询状态
curl http://localhost:12398/api/status/{task_id}

# 4. 下载图片
curl -o images.zip http://localhost:12398/api/images/{task_id}?format=zip
```
