# 小红书自动发布工具 - 项目开发文档

> 基于需求文档 v2.0 编写 | 项目代号: XHS_AutoPublisher_v2
> 文档版本: v1.0-SoT | 最后更新: 2024-12-11

---

## 目录

1. [项目概览](#1-项目概览)
2. [技术架构](#2-技术架构)
3. [开发环境搭建](#3-开发环境搭建)
4. [模块开发指南](#4-模块开发指南)
5. [数据库设计与实现](#5-数据库设计与实现)
6. [N8N工作流开发规范](#6-n8n工作流开发规范)
7. [API集成指南](#7-api集成指南)
8. [测试策略](#8-测试策略)
9. [部署与运维指南](#9-部署与运维指南)
10. [开发里程碑](#10-开发里程碑)

---

## 1. 项目概览

### 1.1 项目目标

构建一个基于 N8N 的小红书内容自动化系统，实现：

| 功能 | 描述 |
|------|------|
| 智能选题 | 关键词 + 热点趋势 + AI评分 |
| 内容生成 | Claude多风格创作 + 5步审核 |
| 图片生成 | Gemini API 3:4竖图 |
| 智能发布 | AI定时 + MCP半自动发布 |
| 数据闭环 | 飞书存储 + 互动数据回流 |

### 1.2 核心指标

| 指标 | 目标值 | 验证方式 |
|------|--------|----------|
| 内容生产效率 | 2-3h → 15min | 时间对比 |
| AI审核通过率 | ≥85% | 30天数据统计 |
| 系统成功率 | ≥90% | N8N执行日志 |
| 多账号支持 | 3-5个账号 | 账号管理验证 |

### 1.3 项目结构

```
xiaohongshu_auto_publisher/
├── docs/                          # 文档目录
│   ├── requirements_v2.0.md       # 需求文档
│   └── DEVELOPMENT_GUIDE.md       # 开发文档(本文件)
├── n8n/                           # N8N工作流
│   ├── workflows/                 # 主工作流JSON
│   │   ├── content_generator_v1.json
│   │   ├── publish_scheduler_v1.json
│   │   └── data_collector_v1.json
│   ├── sub_workflows/             # 子工作流
│   │   ├── sub_ai_score.json
│   │   ├── sub_hot_topics.json
│   │   ├── sub_image_gen.json
│   │   ├── sub_publish.json
│   │   └── sub_notify.json
│   └── credentials/               # 凭证配置说明
├── scripts/                       # 辅助脚本
│   ├── setup.sh                   # 环境初始化
│   ├── backup.sh                  # 数据备份
│   └── health_check.sh            # 健康检查
├── config/                        # 配置文件
│   ├── prompts/                   # AI Prompt模板
│   │   ├── topic_generation.md
│   │   ├── content_creation.md
│   │   └── review_steps.md
│   ├── prompt_registry.json       # Prompt版本注册表
│   └── settings.json              # 系统配置
├── tests/                         # 测试用例
│   ├── golden/                    # 金数据测试集
│   └── regression/                # 回归测试脚本
└── docker-compose.yml             # Docker编排
```

### 1.4 功能模块 ↔ 工作流 ↔ 数据表 映射表

本节提供功能需求与技术实现的快速对照，便于从业务需求直接定位到工作流和数据表。

#### 1.4.1 主映射表

| 功能模块 | 主工作流 | 子工作流 | 主要数据表 | 需求章节 |
|----------|----------|----------|------------|----------|
| **智能选题** | `content_generator_v1` | `sub_hot_topics`, `sub_ai_score` | `content_records`, `execution_logs` | 需求5章 |
| **内容生成+AI审核** | `content_generator_v1` | `sub_ai_score` | `content_records`, `execution_logs` | 需求6章 |
| **图片生成** | `content_generator_v1` | `sub_image_gen` | `content_records` | 需求7章 |
| **半自动发布** | `publish_scheduler_v1` | `sub_publish`, `sub_notify` | `content_records`, `accounts` | 需求8章 |
| **数据回流与分析** | `data_collector_v1` | - | `content_records`, `interaction_data` | 需求9章 |
| **账号管理** | `publish_scheduler_v1` | - | `accounts` | 需求11章 |
| **日志与监控** | 所有工作流 | - | `execution_logs` | 需求13章 |

#### 1.4.2 数据流向图

```
[选题触发] ──→ content_generator_v1 ──→ content_records (DRAFT)
                    │
                    ├─→ sub_hot_topics ──→ execution_logs
                    ├─→ sub_ai_score ──→ content_records (AI_REVIEWED/REJECTED)
                    └─→ sub_image_gen ──→ content_records.image_url

[发布触发] ──→ publish_scheduler_v1 ──→ accounts (限频检查)
                    │
                    ├─→ sub_publish ──→ content_records (PUBLISHED/FAILED)
                    └─→ sub_notify ──→ Telegram

[数据回流] ──→ data_collector_v1 ──→ interaction_data
                    │
                    └─→ content_records (real_score, prediction_error)
```

#### 1.4.3 状态与工作流对应

| 内容状态 | 产生该状态的工作流/节点 | 后续可触发的工作流 |
|----------|------------------------|-------------------|
| `DRAFT` | `content_generator_v1` / Generate_Content | (同工作流内) AI_Review |
| `AI_REVIEWED` | `content_generator_v1` / AI_Gateway(score) | `publish_scheduler_v1` |
| `REJECTED` | `content_generator_v1` / Branch_By_Score | 无（终态） |
| `PENDING_APPROVAL` | 人工审核通过 | `publish_scheduler_v1` |
| `PUBLISHING` | `publish_scheduler_v1` / XHS_MCP_Publish | (同工作流内) |
| `PUBLISHED` | `publish_scheduler_v1` / Publish_Success | `data_collector_v1` |
| `FAILED` | `publish_scheduler_v1` / Publish_Fail | 人工介入后重试 |

---

## 2. 技术架构

### 2.1 技术栈

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│  [Telegram Bot] ←→ [飞书多维表格] ←→ [小红书App]             │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│                      N8N 编排层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ 选题工作流 │  │ 创作工作流 │  │ 发布工作流 │  │ 数据工作流 │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                      ↓                                       │
│              [AI Gateway - 统一调度]                          │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│                       服务层                                 │
│  [Claude API]  [Gemini API]  [飞书API]  [小红书MCP]          │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│                      基础设施                                │
│  [Ubuntu 22.04] + [Docker] + [Nginx] + [Let's Encrypt]      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 组件清单

| 组件 | 选型 | 版本要求 | 用途 |
|------|------|----------|------|
| 编排引擎 | N8N | ≥1.20 | 工作流调度 |
| LLM | Claude API | claude-sonnet-4 | 选题/创作/审核 |
| 图片生成 | Gemini API | gemini-2.0 | 3:4竖图 |
| 数据存储 | 飞书多维表格 | - | 结构化数据 |
| 发布通道 | 小红书MCP | - | 半自动发布 |
| 通知服务 | Telegram Bot | - | 状态推送 |
| 热点抓取 | Web Scraper | - | 抖音/微博热搜 |

### 2.3 数据流图

```
[定时触发/手动触发]
        ↓
[1. 智能选题模块]
   ├─ 读取配置(飞书)
   ├─ AI生成选题(Claude)
   ├─ 抓取热点(Web Scraper)
   ├─ 语义匹配
   └─ AI评分排序
        ↓
[2. 内容创作模块]
   ├─ AI生成内容(Claude)
   ├─ 5步AI审核
   ├─ 计算综合评分
   └─ 分支判断(通过/优化/拒绝)
        ↓
[3. 图片生成模块]
   ├─ 生成图片Prompt(Claude)
   ├─ 生成图片(Gemini)
   └─ 存储图片
        ↓
[4. 人工审核队列]
   ├─ Telegram通知
   └─ 飞书表格更新
        ↓
[5. 发布模块]
   ├─ 检查账号状态
   ├─ 限频检查
   ├─ MCP发布
   └─ 记录结果
        ↓
[6. 数据回流模块]
   ├─ 定时抓取互动数据
   ├─ 计算真实评分
   └─ 更新预测误差
```

---

## 3. 开发环境搭建

### 3.1 服务器要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2核 | 4核 |
| 内存 | 4GB | 8GB |
| 存储 | 50GB SSD | 100GB SSD |
| 系统 | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| 网络 | 公网IP | 公网IP + 域名 |

### 3.2 环境初始化

```bash
#!/bin/bash
# scripts/setup.sh

# 1. 系统更新
sudo apt update && sudo apt upgrade -y

# 2. 安装Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 3. 安装Docker Compose
sudo apt install docker-compose -y

# 4. 创建项目目录
mkdir -p ~/xhs_publisher/{n8n_data,backups}

# 5. 复制环境变量模板（不要直接在脚本中写入敏感信息）
cp .env.example .env
echo "请编辑 .env 文件，填入真实的 API 密钥"
```

### 3.3 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=${N8N_HOST}
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - NODE_ENV=production
      - WEBHOOK_URL=https://${N8N_HOST}/
      - GENERIC_TIMEZONE=Asia/Shanghai
      - TZ=Asia/Shanghai
    volumes:
      - ./n8n_data:/home/node/.n8n
      - ./backups:/backups
    networks:
      - n8n-network

  nginx:
    image: nginx:alpine
    container_name: nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - ./nginx/certbot:/var/www/certbot
    depends_on:
      - n8n
    networks:
      - n8n-network

networks:
  n8n-network:
    driver: bridge
```

### 3.4 Nginx配置

```nginx
# nginx/conf.d/n8n.conf
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location / {
        proxy_pass http://n8n:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

### 3.5 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f n8n

# 停止服务
docker-compose down
```

---

## 4. 模块开发指南

### 4.1 模块优先级

| 优先级 | 模块 | 说明 |
|--------|------|------|
| **P0** | 智能选题 | 核心功能，必须首先实现 |
| **P0** | 内容创作+AI审核 | 核心功能 |
| **P0** | 数据存储(飞书) | 核心功能 |
| **P0** | 通知(Telegram) | 核心功能 |
| **P1** | 图片生成 | 重要功能 |
| **P1** | 热点抓取 | 重要功能 |
| **P1** | 半自动发布(MCP) | 重要功能 |
| **P2** | 智能定时 | 优化功能 |
| **P2** | 互动数据回流 | 优化功能 |
| **P2** | AI评分闭环 | 优化功能 |

### 4.2 模块一：智能选题

#### 4.2.1 功能说明

基于关键词+热点趋势生成3-5个候选选题，100分制评分排序。

#### 4.2.2 输入/输出规格

**输入：**
```json
{
  "keyword": "AI自动化",           // 必填
  "target_audience": "开发者",     // 可选
  "content_style": "干货教程"      // 可选
}
```

**输出：**
```json
{
  "selected_topic_id": "uuid-xxx",
  "title": "标题15-30字",
  "core_points": ["卖点1", "卖点2", "卖点3"],
  "score": 85,
  "prompt_id": "TOPIC_GEN",
  "prompt_version": "V1"
}
```

#### 4.2.3 评分体系(100分)

| 维度 | 权重 | 评估要素 |
|------|------|----------|
| A.点击力 | 30% | 封面10分+标题20分 |
| B.内容力 | 25% | 结构8+密度9+逻辑8 |
| C.价值感 | 20% | 干货7+情绪7+解决6 |
| D.互动设计 | 10% | 评论4+收藏3+转化3 |
| E.平台适配 | 15% | 标签5+SEO5+排版3+合规2 |

**通过标准：**
- 90-100：优秀，直接发布
- 80-89：良好，可发布
- 70-79：需优化后发布
- <70：重新生成

#### 4.2.4 N8N节点流程

```
[Schedule Trigger] (每天9:00)
       ↓
[Fetch_Config] → 从飞书读取配置
       ↓
[AI_Gateway] task=generate_topic → 生成3-5选题
       ↓
[Fetch_Hot_Trends] → 抓取热搜
       ↓
[Match_Trends] → 语义匹配(≥70%相关度)
       ↓
[AI_Gateway] task=score → 对每个选题评分
       ↓
[Select_Best] → 选最高分(≥80)
       ↓
[Save_To_Lark] → 存储到飞书
       ↓
[Send_Notification] → Telegram推送
```

#### 4.2.5 Prompt模板

```markdown
# config/prompts/topic_generation.md
# PROMPT_ID: TOPIC_GEN | VERSION: V1 | UPDATED: 2024-12-11

## 角色
你是一位资深小红书内容策划师，擅长发现热点话题并创作爆款选题。

## 任务
基于以下关键词生成3-5个小红书选题：

**关键词**：{{keyword}}
**目标受众**：{{target_audience}}
**内容风格**：{{content_style}}

## 输出要求
请以JSON格式输出，每个选题包含：
1. title: 标题(15-30字，带emoji)
2. core_points: 3个核心卖点
3. hook: 开头钩子(让人想点进来)
4. target_emotion: 目标情绪(好奇/焦虑/共鸣/获得感)

## 选题标准
- 标题必须有数字或对比
- 包含痛点或解决方案
- 适合小红书用户群体
- 符合平台调性
```

#### 4.2.6 错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| Claude限频 | 等待60s重试，最多3次 |
| 热点抓取失败 | 跳过热点匹配，继续流程 |
| 评分失败 | 使用默认规则fallback |
| 存储失败 | 本地缓存+定时重试 |

---

### 4.3 模块二：内容创作与AI审核

#### 4.3.1 创作规格

| 项目 | 要求 |
|------|------|
| 字数 | 800-1200字 |
| 风格 | 口语化+emoji |
| 结构 | 开头hook + 主体3-5点 + 结尾互动 |
| 标签 | 8-10个相关标签 |

#### 4.3.2 5步AI审核流程

| 步骤 | 检查项 | 通过标准 |
|------|--------|----------|
| Step 0 | 账号定位检查 | 匹配度≥80% |
| Step 1 | 三秒测试(标题+封面) | 点击力≥24分 |
| Step 2 | 首屏测试 | 前两屏传达核心价值 |
| Step 3 | 全文质量 | 内容力≥20 + 价值感≥16 |
| Step 4 | 互动设计 | 互动分≥8分 |
| Step 5 | 平台合规 | 适配≥12 + 敏感词通过 |

#### 4.3.3 审核结果处理

```
评分结果 → [分支判断]
              ├─ score ≥ 80 → [发布队列]
              ├─ 70 ≤ score < 80 → [优化建议] → [人工决定]
              └─ score < 70 → [重新生成]
```

#### 4.3.4 Prompt模板

```markdown
# config/prompts/content_creation.md
# PROMPT_ID: CONTENT_GEN | VERSION: V1 | UPDATED: 2024-12-11

## 角色
你是一位小红书爆款内容创作者，风格亲切自然，善于用故事和案例打动读者。

## 任务
基于以下选题创作小红书文章：

**标题**：{{title}}
**核心卖点**：{{core_points}}
**目标受众**：{{target_audience}}

## 内容结构
1. 开头(50-100字)：用痛点/问题/故事引入
2. 主体(600-900字)：3-5个要点，每点配案例
3. 结尾(50-100字)：总结+互动引导

## 风格要求
- 口语化表达，像朋友聊天
- 适当使用emoji(5-10个)
- 段落短小，3-5行换段
- 重点内容用【】标注

## 输出格式
```json
{
  "content": "正文内容",
  "tags": ["标签1", "标签2", ...],
  "summary": "一句话总结"
}
```
```

---

### 4.4 模块三：图片生成

#### 4.4.1 技术方案

```
[内容文本] → [Claude生成描述Prompt] → [Gemini API生成图片] → [3:4竖图]
```

#### 4.4.2 图片规格

| 项目 | 要求 |
|------|------|
| 比例 | 3:4 (竖图) |
| 分辨率 | 1080 x 1440 px |
| 风格 | 与内容调性一致 |
| 数量 | 封面1张 + 内容图2-5张 |

#### 4.4.3 Prompt模板

```markdown
# 图片描述Prompt生成
# PROMPT_ID: IMAGE_DESC | VERSION: V1 | UPDATED: 2024-12-11

基于以下内容生成图片描述：
**标题**：{{title}}
**主题**：{{topic}}

输出要求：
1. 简洁的英文描述
2. 包含主体、场景、风格
3. 适合小红书审美
4. 避免文字/人脸

示例输出：
"A minimalist workspace with laptop showing AI interface, soft lighting, modern aesthetic, 3:4 vertical composition"
```

---

### 4.5 模块四：发布与智能定时

#### 4.5.1 发布方式

**半自动流程：**
```
AI生成 → AI审核 → 人工确认 → MCP发布
```

#### 4.5.2 智能定时策略

**默认发布时段：**

| 时段 | 工作日 | 周末 |
|------|--------|------|
| 早高峰 | 7:00-9:00 | 10:00-11:00 |
| 午间 | 12:00-13:00 | 15:00-17:00 |
| 晚高峰 | 19:00-22:00 | 20:00-22:00 |

**AI优化逻辑：**
1. 初期：使用默认时段
2. 30天后：分析高表现时段(Top 20%)
3. 每周：动态调整建议时间

#### 4.5.3 限频策略

```javascript
// 发布前检查
function canPublish(accountId) {
  const account = getAccount(accountId);

  // 1. 检查账号状态
  if (account.status !== 'ACTIVE') return false;

  // 2. 检查今日发布数(最多3篇/天)
  if (account.publish_count_today >= 3) return false;

  // 3. 检查发布间隔(最小4小时)
  const lastPublish = account.last_publish_at;
  if (Date.now() - lastPublish < 4 * 3600 * 1000) return false;

  return true;
}
```

---

### 4.6 模块五：数据记录与分析

#### 4.6.1 数据类型

| 类型 | 包含字段 |
|------|----------|
| 内容数据 | 标题、正文、标签、图片 |
| 流程数据 | 生成时间、审核状态、发布时间 |
| 互动数据 | 阅读、点赞、收藏、评论 |
| 评分数据 | AI评分、真实评分、预测误差 |

#### 4.6.2 AI评分闭环

```
[AI预测分数] → [发布] → [等待24-48h] → [抓取真实数据]
       ↓                                      ↓
[记录prediction_error] ← [计算real_score] ←┘
       ↓
[每周分析] → [调整评分权重] → [优化Prompt]
```

**真实评分公式：**
```javascript
real_score =
  views_weight * (views / views_benchmark) * 10 +
  likes_weight * (likes / views) * 100 * 30 +
  collects_weight * (collects / views) * 100 * 30 +
  comments_weight * (comments / views) * 100 * 20;

// 权重参考
// views_benchmark = 1000
// likes_weight = 3.0 (点赞率>5%优秀)
// collects_weight = 5.0 (收藏率>3%优秀)
// comments_weight = 2.0 (评论率>1%优秀)
```

---

### 4.7 AI Prompt 版本管理规范

#### 4.7.1 PROMPT_ID 命名约定

所有 Prompt 必须分配唯一的 PROMPT_ID，命名规则：

| PROMPT_ID | 用途 | 文件路径 |
|-----------|------|----------|
| `TOPIC_GEN` | 选题生成 | `config/prompts/topic_generation.md` |
| `CONTENT_GEN` | 内容创作 | `config/prompts/content_creation.md` |
| `REVIEW_STEP0` | 账号定位审核 | `config/prompts/review_steps.md` |
| `REVIEW_STEP1` | 三秒测试审核 | `config/prompts/review_steps.md` |
| `REVIEW_STEP2` | 首屏测试审核 | `config/prompts/review_steps.md` |
| `REVIEW_STEP3` | 全文质量审核 | `config/prompts/review_steps.md` |
| `REVIEW_STEP4` | 互动设计审核 | `config/prompts/review_steps.md` |
| `REVIEW_STEP5` | 平台合规审核 | `config/prompts/review_steps.md` |
| `IMAGE_DESC` | 图片描述生成 | `config/prompts/image_prompt.md` |
| `SCORE_CALC` | 评分计算 | `config/prompts/score_calculation.md` |

#### 4.7.2 VERSION 管理机制

版本号格式：`V{major}.{minor}`，例如 `V1`, `V1.1`, `V2`

**版本注册表 (config/prompt_registry.json)：**

```json
{
  "prompts": [
    {
      "prompt_id": "TOPIC_GEN",
      "current_version": "V1",
      "versions": [
        {
          "version": "V1",
          "created_at": "2024-12-11",
          "description": "初始版本",
          "file_path": "config/prompts/topic_generation.md",
          "status": "active"
        }
      ]
    },
    {
      "prompt_id": "CONTENT_GEN",
      "current_version": "V1",
      "versions": [
        {
          "version": "V1",
          "created_at": "2024-12-11",
          "description": "初始版本",
          "file_path": "config/prompts/content_creation.md",
          "status": "active"
        }
      ]
    }
  ],
  "last_updated": "2024-12-11"
}
```

#### 4.7.3 Prompt 使用记录

每次 AI 调用必须在 `content_records` 和 `execution_logs` 中记录使用的 Prompt：

**content_records 新增字段：**
- `prompt_id`: 使用的 Prompt ID
- `prompt_version`: 使用的 Prompt 版本

**execution_logs 记录格式：**
```json
{
  "event_type": "AI_PROMPT_USED",
  "context": {
    "prompt_id": "CONTENT_GEN",
    "prompt_version": "V1",
    "task_type": "create_content"
  }
}
```

#### 4.7.4 Prompt 更新流程

1. **新建版本**：复制当前 Prompt，修改版本号为 V{n+1}
2. **测试验证**：使用 TEST 模式在金数据上验证新 Prompt
3. **灰度发布**：配置 `prompt_registry.json` 中的流量比例
4. **全量切换**：验证通过后，更新 `current_version`
5. **归档旧版**：将旧版本 `status` 改为 `archived`

---

## 5. 数据库设计与实现

### 5.1 飞书多维表格结构

#### 表1：content_records (内容记录表)

| 字段名 | 飞书类型 | 约束 | 说明 |
|--------|----------|------|------|
| id | 单行文本 | PK | UUID主键 |
| created_at | 日期 | NOT NULL | 创建时间 |
| content_direction | 单选 | NOT NULL | 内容方向 |
| topic_source | 单选 | NOT NULL | ai/hot_trend/manual |
| title | 单行文本 | NOT NULL | 标题15-30字 |
| content_body | 多行文本 | NOT NULL | 正文800-1200字 |
| tags | 多选 | NOT NULL | 标签数组 |
| image_url | 附件 | - | 图片URL |
| ai_score | 数字 | NOT NULL | AI评分0-100 |
| real_score | 数字 | - | 真实评分 |
| prediction_error | 数字 | - | 预测误差 |
| status | 单选 | NOT NULL | 状态(见状态机) |
| published_at | 日期 | - | 发布时间 |
| account_id | 关联 | FK | 关联账号 |
| workflow_run_id | 单行文本 | UNIQUE | N8N执行ID |
| prompt_id | 单行文本 | NOT NULL | 使用的Prompt ID |
| prompt_version | 单行文本 | NOT NULL | 使用的Prompt版本 |
| views | 数字 | - | 阅读量 |
| likes | 数字 | - | 点赞数 |
| collects | 数字 | - | 收藏数 |
| comments | 数字 | - | 评论数 |

**典型查询场景：**

| 场景 | 查询条件 | 用途 |
|------|----------|------|
| 待审核列表 | `status = 'AI_REVIEWED'` ORDER BY `created_at` DESC | 人工审核队列 |
| 今日发布 | `published_at >= TODAY` AND `account_id = ?` | 限频检查 |
| 高分内容分析 | `ai_score >= 85` AND `status = 'PUBLISHED'` | 提取成功模式 |
| Prompt效果对比 | GROUP BY `prompt_id`, `prompt_version` AVG(`real_score`) | Prompt A/B测试 |
| 预测误差分析 | `prediction_error > 15` ORDER BY `prediction_error` DESC | 模型校准 |

#### 表2：accounts (账号管理表)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | 单行文本 | 账号ID |
| name | 单行文本 | 账号名称 |
| status | 单选 | ACTIVE/COOLDOWN/SUSPENDED/BANNED |
| last_publish_at | 日期 | 最后发布时间 |
| publish_count_today | 数字 | 今日发布数 |
| cooldown_until | 日期 | 冷却截止时间 |

**典型查询场景：**

| 场景 | 查询条件 | 用途 |
|------|----------|------|
| 可用账号 | `status = 'ACTIVE'` AND `publish_count_today < 3` | 发布调度 |
| 冷却检查 | `status = 'COOLDOWN'` AND `cooldown_until <= NOW` | 自动恢复 |
| 账号健康 | GROUP BY `status` COUNT(*) | 运营监控 |

#### 表3：execution_logs (执行日志表)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| timestamp | 日期 | 时间戳 |
| level | 单选 | DEBUG/INFO/WARN/ERROR/FATAL |
| workflow_id | 单行文本 | 工作流ID |
| workflow_run_id | 单行文本 | 执行ID |
| node_name | 单行文本 | 节点名 |
| event_type | 单选 | 事件类型（见5.3枚举） |
| message | 多行文本 | 日志消息 |
| context | 多行文本 | JSON上下文 |
| error | 多行文本 | JSON错误信息 |

**典型查询场景：**

| 场景 | 查询条件 | 用途 |
|------|----------|------|
| 错误排查 | `workflow_run_id = ?` AND `level IN ('ERROR', 'FATAL')` | 故障定位 |
| API成本 | `event_type = 'AI_API_CALL'` GROUP BY DATE(`timestamp`) | 成本监控 |
| 发布失败 | `event_type = 'PUBLISH_FAILED'` ORDER BY `timestamp` DESC | 问题追踪 |
| 日执行统计 | `timestamp >= TODAY` GROUP BY `workflow_id`, `level` | 健康看板 |

#### 表4：interaction_data (互动数据表)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| content_id | 单行文本 | 关联内容ID |
| fetched_at | 日期 | 抓取时间 |
| views | 数字 | 阅读量 |
| likes | 数字 | 点赞数 |
| collects | 数字 | 收藏数 |
| comments | 数字 | 评论数 |

**典型查询场景：**

| 场景 | 查询条件 | 用途 |
|------|----------|------|
| 增长趋势 | `content_id = ?` ORDER BY `fetched_at` | 单篇内容分析 |
| 24h数据 | `fetched_at >= CONTENT.published_at + 24h` | 真实评分计算 |

### 5.2 状态机设计

#### 内容状态流转

```
                    score ≥ 70
[DRAFT] ─────────────────────────→ [AI_REVIEWED]
   │                                     │
   │ score < 70                          │ human_approve
   ↓                                     ↓
[REJECTED]                        [PENDING_APPROVAL]
                                         │
                                         │ publish_trigger
                                         ↓
                                   [PUBLISHING]
                                    ↙        ↘
                          success ↙            ↘ fail (retry≥3)
                                ↓                ↓
                          [PUBLISHED]        [FAILED]
                                                 │
                                                 │ retry
                                                 ↓
                                          [PENDING_APPROVAL]
```

#### 状态定义

| 状态码 | 名称 | 可转换到 |
|--------|------|----------|
| DRAFT | 草稿 | AI_REVIEWED, REJECTED |
| AI_REVIEWED | AI通过 | PENDING_APPROVAL, ARCHIVED |
| PENDING_APPROVAL | 待发布 | PUBLISHING |
| PUBLISHING | 发布中 | PUBLISHED, FAILED |
| PUBLISHED | 已发布 | - |
| REJECTED | AI拒绝 | - |
| ARCHIVED | 已归档 | - |
| FAILED | 发布失败 | PENDING_APPROVAL |

#### 账号状态

| 状态 | 说明 | 发布行为 |
|------|------|----------|
| ACTIVE | 正常 | 可发布 |
| COOLDOWN | 冷却中 | 暂停发布 |
| SUSPENDED | 暂停 | 禁止发布 |
| BANNED | 封禁 | 禁止发布 |

### 5.3 日志事件类型枚举

为保证日志的规范性和可统计性，`execution_logs.event_type` 必须使用以下枚举值：

#### 5.3.1 事件类型定义

| event_type | 级别 | 描述 | 必含context字段 |
|------------|------|------|----------------|
| **工作流生命周期** |
| `WORKFLOW_START` | INFO | 工作流开始执行 | `trigger_type` |
| `WORKFLOW_SUCCESS` | INFO | 工作流执行成功 | `duration_ms` |
| `WORKFLOW_FAILED` | ERROR | 工作流执行失败 | `error_code`, `error_message` |
| **AI调用相关** |
| `AI_API_CALL` | INFO | AI API调用完成 | `task_type`, `prompt_id`, `prompt_version`, `input_tokens`, `output_tokens`, `cost_usd`, `duration_ms` |
| `AI_API_RETRY` | WARN | AI API重试 | `retry_count`, `error_reason` |
| `AI_API_FAILED` | ERROR | AI API失败（重试耗尽） | `error_code`, `retry_count` |
| `AI_PROMPT_USED` | DEBUG | 记录使用的Prompt | `prompt_id`, `prompt_version` |
| **内容生命周期** |
| `CONTENT_CREATED` | INFO | 内容生成完成 | `content_id`, `ai_score` |
| `CONTENT_REVIEWED` | INFO | AI审核完成 | `content_id`, `review_result`, `score` |
| `CONTENT_APPROVED` | INFO | 人工审核通过 | `content_id`, `reviewer` |
| `CONTENT_REJECTED` | INFO | 内容被拒绝 | `content_id`, `reject_reason` |
| **发布相关** |
| `PUBLISH_START` | INFO | 开始发布 | `content_id`, `account_id` |
| `PUBLISH_SUCCESS` | INFO | 发布成功 | `content_id`, `post_url` |
| `PUBLISH_FAILED` | ERROR | 发布失败 | `content_id`, `error_code`, `retry_count` |
| `PUBLISH_RATE_LIMITED` | WARN | 触发限频 | `account_id`, `reason` |
| **数据回流** |
| `DATA_FETCH_START` | INFO | 开始抓取数据 | `content_id` |
| `DATA_FETCH_SUCCESS` | INFO | 数据抓取成功 | `content_id`, `views`, `likes`, `collects`, `comments` |
| `DATA_FETCH_FAILED` | ERROR | 数据抓取失败 | `content_id`, `error_reason` |
| `SCORE_CALCULATED` | INFO | 真实评分计算完成 | `content_id`, `real_score`, `prediction_error` |
| **系统事件** |
| `CONFIG_LOADED` | DEBUG | 配置加载完成 | `config_source` |
| `NOTIFICATION_SENT` | INFO | 通知发送成功 | `channel`, `message_type` |
| `NOTIFICATION_FAILED` | ERROR | 通知发送失败 | `channel`, `error_reason` |

#### 5.3.2 事件类型使用规范

```javascript
// N8N Function节点中的日志记录示例
async function logEvent(eventType, level, message, context = {}) {
  const logEntry = {
    timestamp: new Date().toISOString(),
    level: level,
    workflow_id: $workflow.id,
    workflow_run_id: $execution.id,
    node_name: $node.name,
    event_type: eventType,  // 必须使用枚举值
    message: message,
    context: JSON.stringify(context),
    error: null
  };

  // 写入飞书execution_logs表
  await larkAPI.insertRecord('execution_logs', logEntry);
}

// 使用示例
await logEvent('AI_API_CALL', 'INFO', 'Claude API调用成功', {
  task_type: 'create_content',
  prompt_id: 'CONTENT_GEN',
  prompt_version: 'V1',
  input_tokens: 1500,
  output_tokens: 2000,
  cost_usd: 0.015,
  duration_ms: 3500
});
```

#### 5.3.3 告警配置建议

| 事件类型 | 触发条件 | 告警级别 | 告警方式 |
|----------|----------|----------|----------|
| `WORKFLOW_FAILED` | 任意一次 | 高 | Telegram即时 |
| `AI_API_FAILED` | 任意一次 | 高 | Telegram即时 |
| `PUBLISH_FAILED` | 同一内容3次 | 高 | Telegram即时 |
| `AI_API_RETRY` | 1小时内>10次 | 中 | Telegram汇总 |
| `PUBLISH_RATE_LIMITED` | 任意一次 | 中 | Telegram即时 |
| `DATA_FETCH_FAILED` | 连续3次 | 低 | 日报汇总 |

---

## 6. N8N工作流开发规范

### 6.1 命名规范

| 对象 | 规则 | 示例 |
|------|------|------|
| 工作流 | [功能]_[版本] | content_generator_v1 |
| 节点 | [动词]_[对象] | fetch_hot_topics |
| 变量 | camelCase | selectedTopicId |
| 凭证 | [服务]_[环境] | claude_api_prod |
| 子流程 | sub_[功能] | sub_ai_score |

### 6.2 变量管理分层

| 层级 | 存储位置 | 示例 |
|------|----------|------|
| 全局配置 | Environment Variables | API endpoints |
| 业务配置 | 飞书config表 | 阈值、风格 |
| 运行参数 | Workflow Variables | batch_size |
| 节点输出 | $json / $("节点名") | 动态数据 |

### 6.3 错误处理策略

| 层级 | 方式 | 场景 |
|------|------|------|
| 节点级 | Continue On Fail | API调用 |
| 工作流级 | Error Trigger | 全局异常 |
| 业务级 | 条件分支+重试 | AI失败/发布失败 |

### 6.4 子工作流设计

**拆分条件：**
- 节点数 > 15
- 逻辑复用
- 可独立测试
- 需要并发执行

**建议子流程：**

| 子流程 | 职责 | 输入 | 输出 |
|--------|------|------|------|
| sub_ai_score | AI评分 | 标题/内容 | score对象 |
| sub_hot_topics | 热点抓取 | 关键词 | 热点数组 |
| sub_image_gen | 图片生成 | prompt | 图片URL |
| sub_publish | 内容发布 | 内容对象 | 发布结果 |
| sub_notify | 通知推送 | 消息 | 发送状态 |

### 6.5 AI Gateway设计

所有AI调用统一通过Gateway节点：

```javascript
// AI Gateway 代码示例
const request = {
  model: 'claude-sonnet-4-20250514',
  task_type: $json.task_type, // generate/score/review
  prompt_id: $json.prompt_id,
  prompt_version: $json.prompt_version,
  prompt: $json.prompt,
  max_tokens: $json.max_tokens || 4000
};

// 限频检查
const lastCallTime = $getWorkflowStaticData('lastCallTime') || 0;
if (Date.now() - lastCallTime < 1000) {
  await new Promise(r => setTimeout(r, 1000));
}

// 调用API
const startTime = Date.now();
const response = await claudeAPI.call(request);
const duration = Date.now() - startTime;

// 记录日志（含Prompt版本）
await logEvent('AI_API_CALL', 'INFO', 'Claude API调用成功', {
  task_type: request.task_type,
  prompt_id: request.prompt_id,
  prompt_version: request.prompt_version,
  input_tokens: response.usage.input_tokens,
  output_tokens: response.usage.output_tokens,
  cost_usd: calculateCost(response.usage),
  duration_ms: duration
});

// 更新限频时间
$setWorkflowStaticData('lastCallTime', Date.now());

return { json: response };
```

### 6.6 工作流清单（Workflow Catalog）

本节集中列出所有工作流的详细定义，便于查阅和维护。

#### 6.6.1 主工作流清单

##### content_generator_v1 - 内容生成工作流

| 属性 | 值 |
|------|-----|
| **工作流ID** | `content_generator_v1` |
| **职责** | 智能选题 → 内容生成 → AI审核 → 图片生成 → 存储通知 |
| **触发方式** | Schedule Trigger (每天9:00) / Manual Trigger |
| **输入参数** | `keyword`(必填), `target_audience`(可选), `content_style`(可选) |
| **输出数据** | `content_id`, `title`, `content_body`, `ai_score`, `status`, `image_url` |
| **涉及数据表** | `content_records`, `execution_logs` |
| **调用子工作流** | `sub_hot_topics`, `sub_ai_score`, `sub_image_gen`, `sub_notify` |

**关键节点：**
```
Schedule_Trigger → Fetch_Config → AI_Gateway(generate_topic)
→ sub_hot_topics → Match_Trends → AI_Gateway(score_topics)
→ Select_Best → AI_Gateway(create_content) → sub_ai_score(5步审核)
→ Branch_By_Score → sub_image_gen → Save_To_Lark → sub_notify
```

**错误处理策略：**
| 节点 | 错误类型 | 处理方式 |
|------|----------|----------|
| AI_Gateway | RATE_LIMIT | 等待60s，重试3次 |
| AI_Gateway | TIMEOUT | 增加timeout，重试2次 |
| sub_hot_topics | 抓取失败 | 跳过热点，继续流程 |
| Save_To_Lark | 存储失败 | 本地缓存，定时重试 |
| 任意节点 | 未知错误 | Error Trigger → Telegram告警 |

---

##### publish_scheduler_v1 - 发布调度工作流

| 属性 | 值 |
|------|-----|
| **工作流ID** | `publish_scheduler_v1` |
| **职责** | 检查发布队列 → 限频检查 → 账号调度 → MCP发布 → 状态更新 |
| **触发方式** | Schedule Trigger (每小时) / Webhook (人工触发) |
| **输入参数** | `content_id`(可选，指定发布), `account_id`(可选，指定账号) |
| **输出数据** | `publish_status`, `post_url`, `published_at` |
| **涉及数据表** | `content_records`, `accounts`, `execution_logs` |
| **调用子工作流** | `sub_publish`, `sub_notify` |

**关键节点：**
```
Schedule_Trigger → Fetch_Pending_Content → Check_Account_Status
→ Rate_Limit_Check → Select_Account → sub_publish
→ Update_Content_Status → Update_Account_Stats → sub_notify
```

**错误处理策略：**
| 节点 | 错误类型 | 处理方式 |
|------|----------|----------|
| Check_Account_Status | 无可用账号 | 跳过本轮，记录WARN |
| Rate_Limit_Check | 触发限频 | 跳过本轮，更新账号为COOLDOWN |
| sub_publish | MCP失败 | 重试3次，然后标记FAILED |
| sub_publish | 账号封禁 | 更新账号为BANNED，告警 |

---

##### data_collector_v1 - 数据回流工作流

| 属性 | 值 |
|------|-----|
| **工作流ID** | `data_collector_v1` |
| **职责** | 定时抓取已发布内容的互动数据 → 计算真实评分 → 更新预测误差 |
| **触发方式** | Schedule Trigger (每天10:00, 22:00) |
| **输入参数** | 无（自动查询24-72h前发布的内容） |
| **输出数据** | `interaction_data`, `real_score`, `prediction_error` |
| **涉及数据表** | `content_records`, `interaction_data`, `execution_logs` |
| **调用子工作流** | 无 |

**关键节点：**
```
Schedule_Trigger → Fetch_Published_Content(24-72h)
→ Loop_Each_Content → Fetch_XHS_Data → Calculate_Real_Score
→ Update_Content_Record → Update_Interaction_Data → Generate_Report
```

**错误处理策略：**
| 节点 | 错误类型 | 处理方式 |
|------|----------|----------|
| Fetch_XHS_Data | 抓取失败 | 记录失败，跳过该内容，继续处理其他 |
| Fetch_XHS_Data | 内容被删 | 标记内容为ARCHIVED |
| Calculate_Real_Score | 数据异常 | 跳过计算，记录WARN |

---

#### 6.6.2 子工作流清单

##### sub_ai_score - AI评分子工作流

| 属性 | 值 |
|------|-----|
| **子工作流ID** | `sub_ai_score` |
| **职责** | 执行5步AI审核，返回综合评分 |
| **输入** | `{ title, content_body, tags, account_profile }` |
| **输出** | `{ score, step_scores[], review_comments, passed }` |
| **超时设置** | 120s |

**节点流程：**
```
Input → AI_Gateway(REVIEW_STEP0) → AI_Gateway(REVIEW_STEP1)
→ AI_Gateway(REVIEW_STEP2) → AI_Gateway(REVIEW_STEP3)
→ AI_Gateway(REVIEW_STEP4) → AI_Gateway(REVIEW_STEP5)
→ Calculate_Final_Score → Output
```

---

##### sub_hot_topics - 热点抓取子工作流

| 属性 | 值 |
|------|-----|
| **子工作流ID** | `sub_hot_topics` |
| **职责** | 抓取抖音/微博热搜，返回结构化热点列表 |
| **输入** | `{ keyword, max_results }` |
| **输出** | `{ hot_topics[], fetch_time }` |
| **超时设置** | 30s |

**节点流程：**
```
Input → Parallel_Fetch[Douyin_Hot, Weibo_Hot]
→ Merge_Results → Filter_By_Keyword → Format_Output → Output
```

---

##### sub_image_gen - 图片生成子工作流

| 属性 | 值 |
|------|-----|
| **子工作流ID** | `sub_image_gen` |
| **职责** | 生成图片描述Prompt → 调用Gemini生成图片 → 返回URL |
| **输入** | `{ title, topic, style }` |
| **输出** | `{ image_url, image_prompt }` |
| **超时设置** | 60s |

**节点流程：**
```
Input → AI_Gateway(IMAGE_DESC) → Gemini_API_Call
→ Upload_To_Storage → Output
```

---

##### sub_publish - 内容发布子工作流

| 属性 | 值 |
|------|-----|
| **子工作流ID** | `sub_publish` |
| **职责** | 调用小红书MCP执行发布 |
| **输入** | `{ content_id, title, content_body, tags, image_url, account_id }` |
| **输出** | `{ success, post_url, error_message }` |
| **超时设置** | 120s |
| **重试策略** | 3次，间隔30s |

**节点流程：**
```
Input → Prepare_Publish_Data → XHS_MCP_Call
→ Parse_Response → Output
```

---

##### sub_notify - 通知推送子工作流

| 属性 | 值 |
|------|-----|
| **子工作流ID** | `sub_notify` |
| **职责** | 发送Telegram通知 |
| **输入** | `{ message_type, title, content, score, status }` |
| **输出** | `{ sent, message_id }` |
| **超时设置** | 10s |

**节点流程：**
```
Input → Format_Message → Telegram_Send → Output
```

---

## 7. API集成指南

### 7.1 Claude API

```javascript
// Claude API 调用示例
const response = await fetch('https://api.anthropic.com/v1/messages', {
  method: 'POST',
  headers: {
    'x-api-key': process.env.CLAUDE_API_KEY,
    'anthropic-version': '2023-06-01',
    'content-type': 'application/json'
  },
  body: JSON.stringify({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 4000,
    messages: [{
      role: 'user',
      content: prompt
    }]
  })
});

const data = await response.json();
return data.content[0].text;
```

### 7.2 飞书API

```javascript
// 获取access_token
const tokenRes = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    app_id: process.env.LARK_APP_ID,
    app_secret: process.env.LARK_APP_SECRET
  })
});
const { tenant_access_token } = await tokenRes.json();

// 插入记录
const insertRes = await fetch(
  `https://open.feishu.cn/open-apis/bitable/v1/apps/${appToken}/tables/${tableId}/records`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${tenant_access_token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      fields: {
        id: 'uuid-xxx',
        title: '内容标题',
        ai_score: 85,
        status: 'AI_REVIEWED',
        prompt_id: 'CONTENT_GEN',
        prompt_version: 'V1'
      }
    })
  }
);
```

### 7.3 Telegram Bot

```javascript
// 发送通知
const sendNotification = async (message) => {
  const url = `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: CHAT_ID,
      text: message,
      parse_mode: 'Markdown'
    })
  });
};

// 通知模板
const notifyTemplate = `
*新内容生成完成*

**标题**: ${title}
**AI评分**: ${score}/100
**状态**: ${status}

${score >= 80 ? '可以发布' : '需要优化'}
`;
```

---

## 8. 测试策略

### 8.1 单元测试

| 测试项 | 方法 | 标准 |
|--------|------|------|
| Prompt解析 | 输入多种格式测试 | 100%正确解析 |
| 评分计算 | 边界值测试 | 结果准确 |
| 状态转换 | 覆盖所有转换路径 | 100%正确 |
| API调用 | Mock测试 | 正确处理响应 |

### 8.2 集成测试

| 测试项 | 方法 | 标准 |
|--------|------|------|
| 选题生成 | 运行10次 | 合格率≥80% |
| 内容创作 | 人工评审10篇 | 通过率≥85% |
| 图片生成 | 生成20张检查 | 成功率≥90% |
| 发布功能 | 实际发布测试 | 成功率≥95% |
| 数据存储 | 飞书表格核对 | 100%完整 |

### 8.3 性能测试

| 指标 | 目标 | 测试方法 |
|------|------|----------|
| 单篇生成时间 | ≤5min | 10次平均 |
| 工作流响应 | ≤10s | 节点启动计时 |
| 并发支持 | ≥3任务 | 同时运行测试 |
| 错误恢复 | ≥80% | 模拟错误测试 |

### 8.4 测试用例示例

```yaml
# tests/test_cases.yml

test_topic_generation:
  name: "选题生成测试"
  input:
    keyword: "AI自动化"
    target_audience: "开发者"
  expected:
    - topics_count: 3-5
    - each_score: ">= 70"
    - title_length: "15-30字"
  runs: 10
  pass_rate: ">= 80%"

test_content_creation:
  name: "内容创作测试"
  input:
    title: "测试标题"
    core_points: ["点1", "点2", "点3"]
  expected:
    - word_count: "800-1200"
    - has_emoji: true
    - tags_count: "8-10"
  human_review: true

test_publish_flow:
  name: "发布流程测试"
  preconditions:
    - account_status: "ACTIVE"
    - publish_count_today: "< 3"
  expected:
    - status_after: "PUBLISHED"
    - notification_sent: true
```

### 8.5 N8N工作流回归测试规范

#### 8.5.1 TEST模式设计

所有主工作流必须支持 TEST 模式，通过输入参数 `test_mode: true` 启用：

**TEST模式特性：**

| 特性 | 正常模式 | TEST模式 |
|------|----------|----------|
| 数据存储 | 飞书正式表 | 飞书测试表（表名加 `_test` 后缀） |
| 发布操作 | 真实发布 | 跳过，返回模拟成功 |
| 通知推送 | 正式频道 | 测试频道或跳过 |
| API调用 | 正常调用 | 正常调用（记录到测试日志） |
| 费用计入 | 生产统计 | 测试统计（独立追踪） |

**TEST模式触发方式：**
```json
// Manual Trigger 输入
{
  "test_mode": true,
  "keyword": "AI自动化",
  "target_audience": "开发者"
}
```

**工作流中的TEST模式处理：**
```javascript
// 在Save_To_Lark节点中
const tableId = $json.test_mode
  ? process.env.LARK_TABLE_CONTENT_TEST
  : process.env.LARK_TABLE_CONTENT;

// 在sub_publish节点中
if ($json.test_mode) {
  return {
    json: {
      success: true,
      post_url: 'https://test.xiaohongshu.com/mock/12345',
      test_mode: true
    }
  };
}
```

#### 8.5.2 金数据测试集

在 `tests/golden/` 目录下维护固定输入和预期输出的测试用例：

**目录结构：**
```
tests/golden/
├── content_generator/
│   ├── case_001_basic.json
│   ├── case_002_hot_trend.json
│   └── case_003_edge_case.json
├── publish_scheduler/
│   └── case_001_normal.json
└── data_collector/
    └── case_001_normal.json
```

**金数据用例格式 (case_001_basic.json)：**
```json
{
  "case_id": "CG_001",
  "case_name": "基础选题生成",
  "workflow": "content_generator_v1",
  "description": "验证基础选题生成流程",
  "input": {
    "test_mode": true,
    "keyword": "AI自动化",
    "target_audience": "开发者",
    "content_style": "干货教程"
  },
  "expected_output": {
    "structure": {
      "content_id": "string:uuid",
      "title": "string:length:15-30",
      "content_body": "string:length:800-1200",
      "ai_score": "number:range:0-100",
      "status": "enum:DRAFT|AI_REVIEWED|REJECTED",
      "tags": "array:length:8-10"
    },
    "business_rules": [
      { "rule": "ai_score >= 70", "implies": "status == AI_REVIEWED" },
      { "rule": "ai_score < 70", "implies": "status == REJECTED" }
    ]
  },
  "expected_logs": [
    { "event_type": "WORKFLOW_START" },
    { "event_type": "AI_API_CALL", "context.task_type": "generate_topic" },
    { "event_type": "AI_API_CALL", "context.task_type": "create_content" },
    { "event_type": "CONTENT_CREATED" },
    { "event_type": "WORKFLOW_SUCCESS" }
  ],
  "created_at": "2024-12-11",
  "last_verified": "2024-12-11"
}
```

#### 8.5.3 回归测试执行策略

**触发时机：**

| 场景 | 必须执行的回归测试 |
|------|-------------------|
| 修改主工作流节点 | 该工作流所有金数据用例 |
| 修改子工作流 | 调用该子工作流的所有主工作流用例 |
| 修改Prompt | 使用该Prompt的所有用例 |
| 修改数据表结构 | 所有涉及该表的用例 |
| 每周定期 | 全量回归测试 |

**回归测试脚本 (tests/regression/run_tests.sh)：**
```bash
#!/bin/bash
# 回归测试执行脚本

WORKFLOW=$1  # 可选：指定工作流
GOLDEN_DIR="tests/golden"
RESULTS_DIR="tests/results/$(date +%Y%m%d_%H%M%S)"

mkdir -p $RESULTS_DIR

# 执行测试
if [ -z "$WORKFLOW" ]; then
  # 全量测试
  for case_file in $GOLDEN_DIR/**/*.json; do
    run_single_test "$case_file" "$RESULTS_DIR"
  done
else
  # 指定工作流测试
  for case_file in $GOLDEN_DIR/$WORKFLOW/*.json; do
    run_single_test "$case_file" "$RESULTS_DIR"
  done
fi

# 生成报告
generate_report "$RESULTS_DIR"
```

**测试结果验证：**
```javascript
// tests/regression/validator.js
function validateOutput(actual, expected) {
  const errors = [];

  // 结构验证
  for (const [field, rule] of Object.entries(expected.structure)) {
    const value = actual[field];
    if (!validateRule(value, rule)) {
      errors.push(`Field ${field} failed: expected ${rule}, got ${typeof value}`);
    }
  }

  // 业务规则验证
  for (const rule of expected.business_rules) {
    if (evaluateCondition(actual, rule.rule)) {
      if (!evaluateCondition(actual, rule.implies)) {
        errors.push(`Business rule failed: ${rule.rule} => ${rule.implies}`);
      }
    }
  }

  return { passed: errors.length === 0, errors };
}
```

#### 8.5.4 测试报告格式

```markdown
# 回归测试报告

**执行时间**: 2024-12-11 14:30:00
**执行环境**: TEST
**总用例数**: 15
**通过数**: 14
**失败数**: 1
**通过率**: 93.3%

## 失败用例详情

### CG_003 - 边界情况测试
- **工作流**: content_generator_v1
- **失败原因**: ai_score = 69, status = AI_REVIEWED (应为 REJECTED)
- **相关日志**: workflow_run_id = test_run_xyz789

## 建议
- 检查 Branch_By_Score 节点的判断条件
```

---

## 9. 部署与运维指南

### 9.1 部署检查清单

```markdown
## 部署前检查

### 服务器
- [ ] 服务器配置满足要求(2核4G+)
- [ ] Ubuntu 22.04 LTS已安装
- [ ] Docker已安装并运行
- [ ] 防火墙已配置(80, 443, 5678)

### 域名与证书
- [ ] 域名已解析到服务器
- [ ] SSL证书已配置
- [ ] HTTPS访问正常

### 凭证配置
- [ ] Claude API Key已配置
- [ ] Gemini API Key已配置
- [ ] 飞书App ID/Secret已配置
- [ ] Telegram Bot Token已配置
- [ ] 小红书MCP已配置

### N8N配置
- [ ] 工作流已导入
- [ ] 凭证已绑定节点
- [ ] 触发器已启用
- [ ] 测试执行成功
```

### 9.2 备份策略

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份N8N数据
docker exec n8n n8n export:workflow --all --output=/backups/workflows_${DATE}.json

# 备份数据库(如果有)
# docker exec db pg_dump -U user dbname > ${BACKUP_DIR}/db_${DATE}.sql

# 保留最近7天备份
find ${BACKUP_DIR} -name "*.json" -mtime +7 -delete

echo "Backup completed: ${DATE}"
```

### 9.3 健康检查

```bash
#!/bin/bash
# scripts/health_check.sh

# 检查N8N服务
N8N_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/healthz)
if [ "$N8N_STATUS" != "200" ]; then
  echo "N8N服务异常!"
  # 发送告警
fi

# 检查Docker容器
CONTAINERS=("n8n" "nginx")
for container in "${CONTAINERS[@]}"; do
  STATUS=$(docker inspect -f '{{.State.Running}}' $container 2>/dev/null)
  if [ "$STATUS" != "true" ]; then
    echo "容器 $container 未运行!"
    # 发送告警
  fi
done

echo "Health check completed"
```

### 9.4 监控告警

建议配置以下监控：

| 监控项 | 阈值 | 告警方式 |
|--------|------|----------|
| CPU使用率 | > 80% | Telegram |
| 内存使用率 | > 85% | Telegram |
| 磁盘空间 | > 90% | Telegram |
| N8N执行失败 | 连续3次 | Telegram |
| API调用失败 | 连续5次 | Telegram |

### 9.5 安全与环境管理规范

#### 9.5.1 环境区分

本项目支持三套环境，通过 `.env` 文件区分：

| 环境 | 用途 | 配置文件 | 飞书表后缀 |
|------|------|----------|-----------|
| `dev` | 本地开发 | `.env.dev` | `_dev` |
| `stage` | 测试验证 | `.env.stage` | `_test` |
| `prod` | 生产运行 | `.env.prod` | 无后缀 |

**环境变量规范：**
```bash
# .env.example (提交到版本库的模板)
# ===== 环境标识 =====
NODE_ENV=development  # development | staging | production

# ===== N8N配置 =====
N8N_HOST=your-domain.com
N8N_PORT=5678
N8N_PROTOCOL=https

# ===== API密钥 (请勿提交真实值) =====
CLAUDE_API_KEY=sk-xxx-placeholder
GEMINI_API_KEY=xxx-placeholder
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx-placeholder
TELEGRAM_BOT_TOKEN=xxx-placeholder

# ===== 飞书表格ID =====
LARK_APP_TOKEN=xxx
LARK_TABLE_CONTENT=tblXXX
LARK_TABLE_CONTENT_TEST=tblXXX_test
LARK_TABLE_ACCOUNTS=tblXXX
LARK_TABLE_LOGS=tblXXX

# ===== 通知配置 =====
TELEGRAM_CHAT_ID=xxx
TELEGRAM_CHAT_ID_TEST=xxx
```

#### 9.5.2 API Key 管理规范

| 规则 | 说明 |
|------|------|
| **禁止硬编码** | 所有密钥必须通过环境变量或N8N凭证管理 |
| **禁止提交** | `.env` 文件已加入 `.gitignore`，禁止提交真实密钥 |
| **定期轮换** | 生产环境API Key每90天轮换一次 |
| **最小权限** | 飞书App仅开通必要的API权限 |
| **独立账号** | dev/stage/prod使用独立的API账号 |

**N8N凭证管理：**
```
N8N UI → Settings → Credentials
├── claude_api_dev     # 开发环境
├── claude_api_stage   # 测试环境
├── claude_api_prod    # 生产环境
├── lark_api_dev
├── lark_api_stage
├── lark_api_prod
└── ...
```

#### 9.5.3 敏感文件清单

以下文件**禁止提交**到版本控制：

```gitignore
# .gitignore 必须包含

# 环境变量
.env
.env.*
!.env.example

# N8N数据（含凭证）
n8n_data/

# 备份文件
backups/

# SSL证书
nginx/ssl/

# 日志文件
*.log
logs/
```

#### 9.5.4 部署前安全检查

```bash
#!/bin/bash
# scripts/security_check.sh

echo "=== 安全检查 ==="

# 检查是否有敏感文件被跟踪
SENSITIVE_FILES=$(git ls-files | grep -E '\.env$|credentials|secret|password')
if [ -n "$SENSITIVE_FILES" ]; then
  echo "[ERROR] 敏感文件被版本控制: $SENSITIVE_FILES"
  exit 1
fi

# 检查环境变量是否配置
REQUIRED_VARS=("CLAUDE_API_KEY" "LARK_APP_ID" "LARK_APP_SECRET" "TELEGRAM_BOT_TOKEN")
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "[ERROR] 缺少必要环境变量: $var"
    exit 1
  fi
done

# 检查API Key格式（基础校验）
if [[ ! $CLAUDE_API_KEY =~ ^sk-ant- ]]; then
  echo "[WARN] CLAUDE_API_KEY 格式异常，请确认"
fi

echo "=== 安全检查通过 ==="
```

---

## 10. 开发里程碑

### Phase 1: MVP阶段

**目标：** 核心流程验证，成功率≥80%

| 任务 | 优先级 | 预期产出 |
|------|--------|----------|
| 搭建N8N环境 | P0 | Docker部署完成 |
| 配置Claude API | P0 | API调用正常 |
| 配置飞书API | P0 | 数据读写正常 |
| 实现选题生成 | P0 | 工作流v1 |
| 实现内容创作 | P0 | 工作流v1 |
| 实现AI审核 | P0 | 5步审核完成 |
| 配置Telegram通知 | P0 | 通知正常 |
| 人工发布测试 | P0 | 手动发布成功 |

**验收标准：**
- [ ] 成功生成10篇内容
- [ ] AI审核通过率≥80%
- [ ] 100%记录到飞书
- [ ] 关键节点通知正常

---

### Phase 2: 优化阶段

**目标：** 质量优化，成功率≥85%

| 任务 | 优先级 | 预期产出 |
|------|--------|----------|
| 优化Prompt | P0 | 提升生成质量 |
| 完善错误处理 | P0 | 重试机制 |
| 增加热点抓取 | P1 | 热点匹配功能 |
| 优化评分规则 | P1 | 评分更准确 |
| 初步数据分析 | P1 | 周报功能 |

**验收标准：**
- [ ] 30天持续产出(每天≥1篇)
- [ ] AI审核通过率≥85%
- [ ] 热点匹配成功率≥60%
- [ ] 错误自动恢复率≥80%

---

### Phase 3: 扩展阶段

**目标：** 功能完善，支持多账号

| 任务 | 优先级 | 预期产出 |
|------|--------|----------|
| 图片生成模块 | P1 | Gemini集成 |
| 小红书MCP发布 | P1 | 半自动发布 |
| 账号状态机 | P1 | 多账号管理 |
| 限频策略 | P1 | 安全发布 |
| 互动数据抓取 | P2 | 数据回流 |
| AI评分闭环 | P2 | 评分优化 |

**验收标准：**
- [ ] 图片生成成功率≥90%
- [ ] MCP发布成功率≥95%
- [ ] 支持3-5账号
- [ ] 互动数据每日抓取
- [ ] AI评分误差<15

---

## 附录

### A. 故障排查SOP

#### 问题：内容生成失败

```
Step 1: 定位执行记录
→ N8N UI → Executions → 筛选失败 → 记录workflow_run_id

Step 2: 查看日志
→ 飞书execution_logs表 → 搜索workflow_run_id → 筛选ERROR

Step 3: 根因分析
┌────────────────┬───────────────┬─────────────────┐
│ 错误码         │ 原因          │ 解决方案        │
├────────────────┼───────────────┼─────────────────┤
│ RATE_LIMIT     │ Claude限频    │ 等待1min重试    │
│ INVALID_PROMPT │ Prompt错误    │ 检查prompt模板  │
│ TIMEOUT        │ API超时       │ 增加timeout     │
│ AUTH_FAILED    │ 认证失败      │ 更新API Key     │
└────────────────┴───────────────┴─────────────────┘

Step 4: 恢复运行
→ 临时错误：点击「Retry Execution」
→ 数据错误：更新飞书后重新触发
→ 代码bug：修复workflow后重新执行
```

### B. 常用命令速查

```bash
# Docker操作
docker-compose up -d          # 启动服务
docker-compose down           # 停止服务
docker-compose logs -f n8n    # 查看日志
docker-compose restart n8n    # 重启N8N

# 备份恢复
./scripts/backup.sh           # 执行备份
./scripts/health_check.sh     # 健康检查

# 工作流导入导出
docker exec n8n n8n export:workflow --all --output=/backups/all.json
docker exec n8n n8n import:workflow --input=/backups/all.json

# 回归测试
./tests/regression/run_tests.sh                    # 全量测试
./tests/regression/run_tests.sh content_generator  # 指定工作流测试
```

### C. 成本估算

| 项目 | 月度成本 |
|------|----------|
| 云服务器(2核4G) | ¥60-100 |
| Claude API | $50-150 |
| Gemini API | $20-50 |
| 域名+SSL | ¥10-20 |
| **总计** | **¥300-600** |

### D. 术语表

| 术语 | 说明 |
|------|------|
| SoT | Source of Truth，单一可信数据源 |
| Workflow | N8N中的工作流 |
| Node | N8N工作流中的单个处理节点 |
| Trigger | 工作流触发器 |
| MCP | Model Context Protocol，小红书发布协议 |
| Golden Data | 金数据，用于回归测试的固定测试用例 |
| Prompt Registry | Prompt注册表，管理所有AI Prompt的版本 |

---

## 文档版本

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2024-12-11 | 初始版本 |
| v1.0-SoT | 2024-12-11 | 工程化重构：新增映射表、工作流清单、事件枚举、Prompt版本管理、回归测试规范、安全规范 |

---

*本文档基于需求文档v2.0编写，已完成工程化升级，可作为项目v1.0上线的SoT开发文档。*
