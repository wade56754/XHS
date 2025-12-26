# 小红书自动发布工具 - 开发计划

> 项目代号: XHS_AutoPublisher_v2
> 版本: v1.0 | 创建日期: 2024-12-11
> 配套文档: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)

---

## 目录

1. [计划概述](#1-计划概述)
2. [可复用资源集成策略](#2-可复用资源集成策略)
3. [开发阶段与任务分解](#3-开发阶段与任务分解)
4. [技术集成指南](#4-技术集成指南)
5. [风险评估与应对](#5-风险评估与应对)
6. [验收标准与交付物](#6-验收标准与交付物)

---

## 1. 计划概述

### 1.1 项目目标

构建基于 N8N 的小红书内容自动化系统，实现从选题到发布的全流程自动化。

**核心指标：**

| 指标 | 目标值 | 优先级 |
|------|--------|--------|
| 内容生产效率 | 2-3h → 15min | P0 |
| AI审核通过率 | ≥85% | P0 |
| 系统成功率 | ≥90% | P0 |
| 多账号支持 | 3-5个 | P1 |

### 1.2 开发原则

| 原则 | 说明 |
|------|------|
| **复用优先** | 优先使用成熟开源项目，减少重复造轮子 |
| **MVP 先行** | 先跑通核心流程，再优化细节 |
| **模块解耦** | 每个子工作流可独立测试和替换 |
| **可观测性** | 所有关键操作必须有日志记录 |

### 1.3 开发周期总览

```
Week 1-2: MVP阶段 ──→ Week 3-4: 优化阶段 ──→ Week 5-8: 扩展阶段
    │                      │                      │
    ├─ 环境搭建            ├─ Prompt优化          ├─ 图片生成
    ├─ 热点抓取集成        ├─ 错误处理完善        ├─ MCP发布
    ├─ 内容生成            ├─ 热点匹配            ├─ 多账号
    ├─ AI审核              ├─ 数据分析            ├─ 数据回流
    └─ 飞书存储            └─ 周报功能            └─ AI闭环
```

---

## 2. 可复用资源集成策略

### 2.1 资源清单与复用方案

#### 2.1.1 热点抓取 - MediaCrawler

| 属性 | 值 |
|------|-----|
| **项目地址** | https://github.com/NanmiCoder/MediaCrawler |
| **Stars** | 27.7K+ |
| **覆盖平台** | 小红书、抖音、微博、B站、快手、知乎、贴吧 |
| **集成方式** | 本地部署 + API 调用 |
| **节省工作量** | 90%+ |

**集成步骤：**

```bash
# 1. 克隆项目
git clone https://github.com/NanmiCoder/MediaCrawler.git
cd MediaCrawler

# 2. 安装依赖
pip install -r requirements.txt
playwright install

# 3. 配置账号（首次需扫码登录）
python main.py --platform weibo --login

# 4. 启动 API 服务（供 N8N 调用）
python api_server.py --port 8080
```

**N8N 调用示例：**

```javascript
// HTTP Request 节点配置
{
  "method": "POST",
  "url": "http://localhost:8080/api/search",
  "body": {
    "platform": "weibo",
    "keyword": "{{$json.keyword}}",
    "type": "hot",
    "limit": 20
  }
}
```

**输出数据格式：**

```json
{
  "hot_topics": [
    {
      "title": "热搜标题",
      "hot_value": 1234567,
      "url": "https://...",
      "category": "娱乐"
    }
  ],
  "fetch_time": "2024-12-11T09:00:00Z"
}
```

---

#### 2.1.2 小红书发布 - xiaohongshu-mcp

| 属性 | 值 |
|------|-----|
| **项目地址** | https://github.com/xpzouying/xiaohongshu-mcp |
| **功能** | 发布图文/视频到小红书 |
| **技术栈** | MCP + Playwright |
| **集成方式** | MCP Server + N8N MCP Client |
| **节省工作量** | 80%+ |

**集成步骤：**

```bash
# 1. 克隆项目
git clone https://github.com/xpzouying/xiaohongshu-mcp.git
cd xiaohongshu-mcp

# 2. 安装依赖
npm install
npx playwright install chromium

# 3. 配置 MCP Server
cp config.example.json config.json
# 编辑 config.json，填入 Cookie 或扫码配置

# 4. 启动 MCP Server
npm start
```

**MCP 工具清单：**

| 工具名 | 功能 | 输入参数 |
|--------|------|----------|
| `xhs_publish_note` | 发布图文笔记 | title, content, images[], tags[] |
| `xhs_publish_video` | 发布视频笔记 | title, content, video_url, tags[] |
| `xhs_get_note` | 获取笔记详情 | note_id |
| `xhs_login` | 登录/刷新Cookie | - |

**N8N MCP Client 配置：**

```json
{
  "mcp_server_url": "http://localhost:3000",
  "tool": "xhs_publish_note",
  "arguments": {
    "title": "{{$json.title}}",
    "content": "{{$json.content_body}}",
    "images": "{{$json.image_urls}}",
    "tags": "{{$json.tags}}"
  }
}
```

---

#### 2.1.3 数据回流 - RedNote-MCP

| 属性 | 值 |
|------|-----|
| **项目地址** | https://github.com/iFurySt/RedNote-MCP |
| **功能** | 获取笔记内容、评论、互动数据 |
| **集成方式** | MCP Server |
| **节省工作量** | 70%+ |

**MCP 工具清单：**

| 工具名 | 功能 | 输出 |
|--------|------|------|
| `get_note_by_url` | 获取笔记详情 | title, content, likes, collects, comments |
| `get_comments` | 获取评论列表 | comments[] |
| `search_notes` | 搜索笔记 | notes[] |

---

#### 2.1.4 飞书 API - feishu-bitable-python-tool

| 属性 | 值 |
|------|-----|
| **项目地址** | https://github.com/dungeer619/feishu-bitable-python-tool |
| **功能** | 飞书多维表格读写 |
| **语言** | Python |
| **集成方式** | 作为辅助脚本 / 参考实现 |

**参考其认证逻辑：**

```python
# 复用其 Token 获取逻辑
class FeishuAuth:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self.token = None
        self.token_expires = 0

    def get_token(self):
        if time.time() < self.token_expires - 60:
            return self.token

        resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret}
        )
        data = resp.json()
        self.token = data["tenant_access_token"]
        self.token_expires = time.time() + data["expire"]
        return self.token
```

---

#### 2.1.5 N8N 工作流模板

| 资源 | 链接 | 参考价值 |
|------|------|----------|
| **awesome-n8n-templates** | https://github.com/enescingoz/awesome-n8n-templates | AI 自动化模板结构 |
| **n8n 官方模板库** | https://n8n.io/workflows/ | Claude 集成示例 |
| **SEO Content 模板** | https://n8n.io/workflows/5374 | 内容生成 + 图片流程 |

---

### 2.2 自研 vs 复用决策矩阵

| 模块 | 决策 | 理由 | 工作量估算 |
|------|------|------|-----------|
| **热点抓取** | MVP: 脚本 / 扩展: MediaCrawler | MVP先跑通，后期再完整集成 | 0.5天(脚本) / 2天(完整) |
| **小红书发布** | MVP: 手动 / 扩展: xiaohongshu-mcp | 降低MVP复杂度 | 0天(手动) / 2天(MCP) |
| **数据回流抓取** | MVP: 手动 / 扩展: RedNote-MCP | 后期再自动化 | 0天(手动) / 1天(MCP) |
| **飞书 API** | 参考 + 自研 | N8N 有原生 HTTP 节点 | 2天开发 |
| **AI 内容生成** | 自研 | Prompt 是核心竞争力 | 3天开发 |
| **5步 AI 审核** | 自研 | 评分体系需定制 | 5天开发 |
| **图片生成** | 自研 | Gemini API 调用简单 | 2天开发 |
| **智能定时** | 自研 | 需积累自有数据 | 3天开发 |
| **AI 评分闭环** | 自研 | 业务特定逻辑 | 3天开发 |

**总结：MVP 先简化，扩展阶段再完整集成**

---

### 2.3 分阶段集成策略（推荐）

> **核心原则：MVP 先跑通核心内容生成，扩展阶段再集成复杂的开源项目**

#### 2.3.1 为什么推荐分阶段？

| 因素 | 完整集成 | 分阶段集成 |
|------|----------|------------|
| **MVP 复杂度** | 高（5个Docker服务） | 低（2个Docker服务） |
| **环境依赖** | Playwright + Node + Python | Docker + Python |
| **调试难度** | 难（多服务联调） | 易（服务独立） |
| **服务器资源** | 4GB+ 内存 | 2GB 内存即可 |
| **首次跑通时间** | 3-5 天 | 1-2 天 |

#### 2.3.2 阶段划分

```
┌─────────────────────────────────────────────────────────────────────┐
│ MVP 阶段（Week 1-4）                                                 │
│                                                                      │
│   Docker 容器           服务器原生                                   │
│   ┌─────────┐          ┌─────────────────────────────────┐          │
│   │  N8N    │          │  Python 脚本 (Crontab 定时)     │          │
│   │ :5678   │◄─────────│  - hot_topics.py (热点抓取)     │          │
│   └─────────┘          │  - 结果写入飞书表格              │          │
│        │               └─────────────────────────────────┘          │
│   ┌─────────┐                                                       │
│   │  Nginx  │                                                       │
│   │ :80/443 │          📝 发布方式：人工从飞书复制发布               │
│   └─────────┘                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 扩展阶段（Week 5-8）                                                 │
│                                                                      │
│   新增服务（pm2 管理）                                               │
│   ┌─────────────────┐  ┌─────────────────┐                          │
│   │ xiaohongshu-mcp │  │  RedNote-MCP    │                          │
│   │    :3000        │  │    :3001        │                          │
│   │  (Node.js)      │  │   (Node.js)     │                          │
│   └─────────────────┘  └─────────────────┘                          │
│                                                                      │
│   📝 发布方式：N8N → MCP → 小红书自动发布                            │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.3.3 MVP 阶段技术栈

| 组件 | 技术方案 | 部署方式 |
|------|----------|----------|
| **工作流引擎** | N8N | Docker |
| **反向代理** | Nginx | Docker |
| **热点抓取** | Python 脚本 + 公开 API | Crontab |
| **AI 内容生成** | Claude API | N8N HTTP 节点 |
| **AI 审核** | Claude API | N8N HTTP 节点 |
| **数据存储** | 飞书多维表格 | N8N HTTP 节点 |
| **通知** | Telegram Bot | N8N 节点 |
| **发布** | 人工操作 | 飞书表格导出 |

#### 2.3.4 热点抓取脚本方案

**scripts/hot_topics.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点抓取脚本 - MVP 简化版
功能：抓取微博热搜，写入飞书多维表格
部署：Crontab 每 2 小时执行一次
"""

import os
import json
import requests
from datetime import datetime, timezone
from typing import List, Dict

# 环境变量
LARK_APP_ID = os.environ.get('LARK_APP_ID')
LARK_APP_SECRET = os.environ.get('LARK_APP_SECRET')
LARK_APP_TOKEN = os.environ.get('LARK_APP_TOKEN')
LARK_TABLE_HOT_TOPICS = os.environ.get('LARK_TABLE_HOT_TOPICS', 'tblHotTopics')

class LarkClient:
    """飞书 API 客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_expires = 0

    def get_token(self) -> str:
        """获取 tenant_access_token"""
        import time
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret}
        )
        data = resp.json()
        if data.get('code') != 0:
            raise Exception(f"获取飞书 Token 失败: {data}")

        self._token = data['tenant_access_token']
        self._token_expires = time.time() + data['expire']
        return self._token

    def add_records(self, app_token: str, table_id: str, records: List[Dict]):
        """批量添加记录"""
        token = self.get_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"

        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={"records": [{"fields": r} for r in records]}
        )
        return resp.json()


def fetch_weibo_hot() -> List[Dict]:
    """
    抓取微博热搜（公开 API，无需登录）
    返回前 20 条热搜
    """
    url = "https://weibo.com/ajax/side/hotSearch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://weibo.com/"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        hot_topics = []
        for item in data.get('data', {}).get('realtime', [])[:20]:
            hot_topics.append({
                "title": item.get('word', ''),
                "hot_value": item.get('num', 0),
                "category": item.get('category', '综合'),
                "url": f"https://s.weibo.com/weibo?q=%23{item.get('word', '')}%23",
                "source": "weibo"
            })

        return hot_topics
    except Exception as e:
        print(f"[ERROR] 抓取微博热搜失败: {e}")
        return []


def fetch_zhihu_hot() -> List[Dict]:
    """
    抓取知乎热榜（公开 API）
    """
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        hot_topics = []
        for item in data.get('data', [])[:20]:
            target = item.get('target', {})
            hot_topics.append({
                "title": target.get('title', ''),
                "hot_value": item.get('detail_text', '0').replace('万热度', '0000').replace('热度', ''),
                "category": "知乎",
                "url": f"https://www.zhihu.com/question/{target.get('id', '')}",
                "source": "zhihu"
            })

        return hot_topics
    except Exception as e:
        print(f"[ERROR] 抓取知乎热榜失败: {e}")
        return []


def main():
    """主函数"""
    print(f"[{datetime.now().isoformat()}] 开始抓取热点...")

    # 1. 抓取热点
    all_topics = []
    all_topics.extend(fetch_weibo_hot())
    all_topics.extend(fetch_zhihu_hot())

    if not all_topics:
        print("[WARN] 未抓取到任何热点")
        return

    print(f"[INFO] 共抓取 {len(all_topics)} 条热点")

    # 2. 准备写入飞书的数据
    fetch_time = datetime.now(timezone.utc).isoformat()
    records = []
    for topic in all_topics:
        records.append({
            "title": topic["title"],
            "hot_value": int(topic["hot_value"]) if str(topic["hot_value"]).isdigit() else 0,
            "category": topic["category"],
            "url": topic["url"],
            "source": topic["source"],
            "fetched_at": fetch_time
        })

    # 3. 写入飞书
    if LARK_APP_ID and LARK_APP_SECRET and LARK_APP_TOKEN:
        client = LarkClient(LARK_APP_ID, LARK_APP_SECRET)
        result = client.add_records(LARK_APP_TOKEN, LARK_TABLE_HOT_TOPICS, records)

        if result.get('code') == 0:
            print(f"[OK] 成功写入 {len(records)} 条记录到飞书")
        else:
            print(f"[ERROR] 写入飞书失败: {result}")
    else:
        # 本地测试：输出到文件
        with open('/tmp/hot_topics.json', 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 飞书配置缺失，已输出到 /tmp/hot_topics.json")


if __name__ == "__main__":
    main()
```

**Crontab 配置**

```bash
# 编辑 crontab
crontab -e

# 添加定时任务：每 2 小时执行一次
0 */2 * * * /usr/bin/python3 /opt/xhs_auto/scripts/hot_topics.py >> /var/log/hot_topics.log 2>&1

# 或者每天固定时间执行（9点、12点、15点、18点、21点）
0 9,12,15,18,21 * * * /usr/bin/python3 /opt/xhs_auto/scripts/hot_topics.py >> /var/log/hot_topics.log 2>&1
```

**环境变量配置（/opt/xhs_auto/.env）**

```bash
# 飞书配置
export LARK_APP_ID=cli_xxxxx
export LARK_APP_SECRET=xxxxx
export LARK_APP_TOKEN=xxxxx
export LARK_TABLE_HOT_TOPICS=tblHotTopics
```

#### 2.3.5 扩展阶段 MCP 部署（pm2 方案）

当 MVP 稳定运行后，扩展阶段集成 MCP 服务：

**安装 pm2**

```bash
# 安装 Node.js (如果没有)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 pm2
npm install -g pm2
```

**部署 xiaohongshu-mcp**

```bash
# 1. 克隆项目
cd /opt/xhs_auto
git clone https://github.com/xpzouying/xiaohongshu-mcp.git
cd xiaohongshu-mcp

# 2. 安装依赖
npm install
npx playwright install chromium

# 3. 配置
cp config.example.json config.json
# 编辑 config.json，填入 Cookie

# 4. 使用 pm2 启动
pm2 start npm --name "xhs-mcp" -- start
pm2 save
pm2 startup
```

**部署 RedNote-MCP**

```bash
# 1. 克隆项目
cd /opt/xhs_auto
git clone https://github.com/iFurySt/RedNote-MCP.git
cd RedNote-MCP

# 2. 安装依赖
npm install

# 3. 使用 pm2 启动
pm2 start npm --name "rednote-mcp" -- start
pm2 save
```

**pm2 常用命令**

```bash
# 查看服务状态
pm2 status

# 查看日志
pm2 logs xhs-mcp
pm2 logs rednote-mcp

# 重启服务
pm2 restart xhs-mcp

# 停止服务
pm2 stop xhs-mcp

# 监控面板
pm2 monit
```

**N8N 调用 MCP 配置更新**

```javascript
// 更新 .env 中的 MCP 地址
XHS_MCP_URL=http://localhost:3000
REDNOTE_MCP_URL=http://localhost:3001
```

---

## 3. 开发阶段与任务分解

### 3.1 Phase 0: 环境准备（Day 1-2）

#### 任务清单（简化版）

| 任务ID | 任务名称 | 负责人 | 前置任务 | 交付物 |
|--------|----------|--------|----------|--------|
| P0-01 | 服务器初始化 | - | - | 可访问的云服务器 |
| P0-02 | Docker 环境搭建 | - | P0-01 | Docker + Docker Compose |
| P0-03 | N8N + Nginx 部署 | - | P0-02 | https://your-domain.com 可访问 |
| P0-04 | SSL 证书配置 | - | P0-03 | HTTPS 正常 |
| P0-05 | API 密钥申请 | - | - | Claude/Gemini/飞书 Key |
| P0-06 | 飞书多维表格创建 | - | P0-05 | 5张表结构就绪（新增 hot_topics 表） |
| P0-07 | Telegram Bot 创建 | - | - | Bot Token |
| P0-08 | 热点抓取脚本部署 | - | P0-06 | hot_topics.py + Crontab 配置完成 |

> **注意：** MVP 阶段不部署 MediaCrawler/MCP，用 Python 脚本替代热点抓取，人工发布

#### P0-06 飞书表格创建脚本

```bash
#!/bin/bash
# scripts/init_lark_tables.sh

# 需要手动在飞书创建以下表格：

echo "=== 飞书多维表格初始化清单 ==="
echo ""
echo "1. content_records (内容记录表)"
echo "   字段: id, created_at, content_direction, topic_source, title,"
echo "         content_body, tags, image_url, ai_score, real_score,"
echo "         prediction_error, status, published_at, account_id,"
echo "         workflow_run_id, prompt_id, prompt_version,"
echo "         views, likes, collects, comments"
echo ""
echo "2. accounts (账号管理表)"
echo "   字段: id, name, status, last_publish_at, publish_count_today, cooldown_until"
echo ""
echo "3. execution_logs (执行日志表)"
echo "   字段: timestamp, level, workflow_id, workflow_run_id, node_name,"
echo "         event_type, message, context, error"
echo ""
echo "4. interaction_data (互动数据表)"
echo "   字段: content_id, fetched_at, views, likes, collects, comments"
echo ""
echo "5. hot_topics (热点话题表) [MVP新增]"
echo "   字段: title, hot_value, category, url, source, fetched_at"
echo "   说明: 由 hot_topics.py 脚本定时写入"
echo ""
echo "请在飞书中手动创建以上表格，并记录 App Token 和 Table ID"
```

#### 环境验证检查点（MVP 简化版）

```bash
#!/bin/bash
# scripts/verify_env.sh
# MVP 阶段只验证核心服务

echo "=== MVP 环境验证 ==="

# 1. 检查 Docker
docker --version && echo "[OK] Docker" || echo "[FAIL] Docker"

# 2. 检查 N8N
curl -s http://localhost:5678/healthz | grep -q "ok" && echo "[OK] N8N" || echo "[FAIL] N8N"

# 3. 检查 Nginx (通过 HTTPS 访问)
curl -s -o /dev/null -w "%{http_code}" https://${N8N_HOST}/ | grep -q "200\|301\|302" && echo "[OK] Nginx/HTTPS" || echo "[FAIL] Nginx/HTTPS"

# 4. 检查热点抓取脚本
python3 /opt/xhs_auto/scripts/hot_topics.py --test && echo "[OK] hot_topics.py" || echo "[FAIL] hot_topics.py"

# 5. 检查 Claude API
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $CLAUDE_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}' \
  | grep -q "content" && echo "[OK] Claude API" || echo "[FAIL] Claude API"

# 6. 检查飞书 API
curl -s https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$LARK_APP_ID\",\"app_secret\":\"$LARK_APP_SECRET\"}" \
  | grep -q "tenant_access_token" && echo "[OK] Lark API" || echo "[FAIL] Lark API"

# 7. 检查 Crontab 是否配置
crontab -l | grep -q "hot_topics.py" && echo "[OK] Crontab" || echo "[WARN] Crontab 未配置热点抓取任务"

echo "=== MVP 验证完成 ==="
echo ""
echo "注意：扩展阶段需额外验证 MCP 服务 (xiaohongshu-mcp, RedNote-MCP)"
```

#### 扩展阶段验证脚本

```bash
#!/bin/bash
# scripts/verify_env_extended.sh
# 扩展阶段：验证 MCP 服务

echo "=== 扩展阶段环境验证 ==="

# 运行 MVP 验证
./verify_env.sh

echo ""
echo "=== MCP 服务验证 ==="

# 1. 检查 pm2
pm2 --version && echo "[OK] pm2" || echo "[FAIL] pm2"

# 2. 检查 xiaohongshu-mcp
pm2 describe xhs-mcp | grep -q "online" && echo "[OK] XHS-MCP (pm2)" || echo "[FAIL] XHS-MCP"
curl -s http://localhost:3000/health | grep -q "ok" && echo "[OK] XHS-MCP (HTTP)" || echo "[FAIL] XHS-MCP (HTTP)"

# 3. 检查 RedNote-MCP
pm2 describe rednote-mcp | grep -q "online" && echo "[OK] RedNote-MCP (pm2)" || echo "[FAIL] RedNote-MCP"
curl -s http://localhost:3001/health | grep -q "ok" && echo "[OK] RedNote-MCP (HTTP)" || echo "[FAIL] RedNote-MCP (HTTP)"

echo "=== 扩展阶段验证完成 ==="
```

---

### 3.2 Phase 1: MVP 阶段（Day 3-10）

#### 3.2.1 Sprint 1: 核心数据流（Day 3-5）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P1-01 | 创建 content_generator_v1 骨架 | P0 | 创建主工作流，配置 Schedule Trigger |
| P1-02 | 实现 Fetch_Config 节点 | P1-01 | 从飞书读取配置（关键词、风格等） |
| P1-03 | 实现 AI_Gateway 节点 | P1-01 | Claude API 统一调用封装 |
| P1-04 | 实现热点读取节点 | P0-08 | 从飞书 hot_topics 表读取（脚本已定时写入） |
| P1-05 | 实现选题生成 | P1-03, P1-04 | AI_Gateway(task=generate_topic)，结合热点 |
| P1-06 | 实现内容创作 | P1-05 | AI_Gateway(task=create_content) |
| P1-07 | 实现 Save_To_Lark 节点 | P0-06 | 写入 content_records 表 |
| P1-08 | 实现 sub_notify 子工作流 | P0-07 | Telegram 通知 |

> **MVP 简化说明：** 热点数据由 hot_topics.py 脚本定时抓取写入飞书，N8N 直接从飞书读取，无需 MediaCrawler Docker 服务

**P1-03 AI_Gateway 核心代码：**

```javascript
// AI_Gateway Function 节点

const PROMPT_REGISTRY = {
  'TOPIC_GEN': { version: 'V1', template: '...' },
  'CONTENT_GEN': { version: 'V1', template: '...' },
  // ... 其他 Prompt
};

async function callClaude(taskType, variables) {
  const promptConfig = PROMPT_REGISTRY[taskType];
  const prompt = renderTemplate(promptConfig.template, variables);

  const startTime = Date.now();

  const response = await $http.request({
    method: 'POST',
    url: 'https://api.anthropic.com/v1/messages',
    headers: {
      'x-api-key': $env.CLAUDE_API_KEY,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json'
    },
    body: {
      model: 'claude-sonnet-4-20250514',
      max_tokens: $json.max_tokens || 4000,
      messages: [{ role: 'user', content: prompt }]
    }
  });

  const duration = Date.now() - startTime;

  // 记录日志
  await logEvent('AI_API_CALL', 'INFO', 'Claude API 调用成功', {
    task_type: taskType,
    prompt_id: taskType,
    prompt_version: promptConfig.version,
    input_tokens: response.body.usage.input_tokens,
    output_tokens: response.body.usage.output_tokens,
    cost_usd: calculateCost(response.body.usage),
    duration_ms: duration
  });

  return {
    content: response.body.content[0].text,
    prompt_id: taskType,
    prompt_version: promptConfig.version
  };
}

// 限频控制
const lastCallTime = $getWorkflowStaticData('lastCallTime') || 0;
if (Date.now() - lastCallTime < 1000) {
  await new Promise(r => setTimeout(r, 1000));
}
$setWorkflowStaticData('lastCallTime', Date.now());

// 执行调用
const result = await callClaude($json.task_type, $json.variables);
return { json: result };
```

---

#### 3.2.2 Sprint 2: AI 审核（Day 6-8）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P1-09 | 创建 sub_ai_score 子工作流 | P1-03 | 5步审核框架 |
| P1-10 | 实现 Step 0: 账号定位检查 | P1-09 | REVIEW_STEP0 Prompt |
| P1-11 | 实现 Step 1: 三秒测试 | P1-10 | REVIEW_STEP1 Prompt |
| P1-12 | 实现 Step 2: 首屏测试 | P1-11 | REVIEW_STEP2 Prompt |
| P1-13 | 实现 Step 3: 全文质量 | P1-12 | REVIEW_STEP3 Prompt |
| P1-14 | 实现 Step 4: 互动设计 | P1-13 | REVIEW_STEP4 Prompt |
| P1-15 | 实现 Step 5: 平台合规 | P1-14 | REVIEW_STEP5 Prompt |
| P1-16 | 实现评分汇总与分支 | P1-15 | Calculate_Final_Score + Branch |

**sub_ai_score 工作流结构：**

```
Input
  ↓
┌─────────────────────────────────────────────────────────┐
│ Loop: 6次 (Step 0-5)                                    │
│   ↓                                                     │
│   AI_Gateway(REVIEW_STEP_{{$index}})                   │
│   ↓                                                     │
│   Parse_Score → 提取该步骤分数                          │
│   ↓                                                     │
│   Append_To_Array → 累积分数                            │
└─────────────────────────────────────────────────────────┘
  ↓
Calculate_Final_Score
  ↓
Output: { score, step_scores[], review_comments, passed }
```

**评分汇总逻辑：**

```javascript
// Calculate_Final_Score 节点

const stepScores = $json.step_scores; // [step0_score, step1_score, ...]
const weights = [0.10, 0.30, 0.15, 0.25, 0.10, 0.10]; // 各步骤权重

// 加权计算
let finalScore = 0;
for (let i = 0; i < 6; i++) {
  finalScore += stepScores[i] * weights[i];
}
finalScore = Math.round(finalScore);

// 判断是否通过
const passed = finalScore >= 70;
const status = finalScore >= 80 ? 'AI_REVIEWED' :
               finalScore >= 70 ? 'NEEDS_OPTIMIZATION' : 'REJECTED';

return {
  json: {
    score: finalScore,
    step_scores: stepScores,
    passed: passed,
    status: status,
    review_comments: $json.all_comments
  }
};
```

---

#### 3.2.3 Sprint 3: 端到端联调（Day 9-10）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P1-17 | 工作流串联 | P1-01~P1-16 | 连接所有节点 |
| P1-18 | 错误处理添加 | P1-17 | 各节点 Continue On Fail |
| P1-19 | Error Trigger 配置 | P1-17 | 全局异常捕获 + 告警 |
| P1-20 | TEST 模式实现 | P1-17 | test_mode 参数支持 |
| P1-21 | 首次全流程测试 | P1-20 | 手动触发 10 次 |
| P1-22 | 问题修复 | P1-21 | 根据测试结果调整 |
| P1-23 | MVP 验收 | P1-22 | 确认达到 80% 成功率 |

**MVP 验收检查表：**

```markdown
## MVP 验收清单

### 功能验收
- [ ] 输入关键词后能生成 3-5 个选题
- [ ] 选中的选题能生成 800-1200 字内容
- [ ] 5步审核能正常执行并给出分数
- [ ] 分数 ≥70 的内容状态为 AI_REVIEWED
- [ ] 分数 <70 的内容状态为 REJECTED
- [ ] 所有内容正确写入飞书表格
- [ ] 生成完成后收到 Telegram 通知

### 指标验收
- [ ] 10 次测试中 ≥8 次成功（80%）
- [ ] 单次生成时间 ≤5 分钟
- [ ] 无未捕获的错误

### 数据验收
- [ ] content_records 表数据完整
- [ ] execution_logs 表有完整日志
- [ ] prompt_id 和 prompt_version 正确记录
```

---

### 3.3 Phase 2: 优化阶段（Day 11-20）

#### 3.3.1 Sprint 4: Prompt 优化（Day 11-13）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P2-01 | 分析 MVP 生成内容 | P1-23 | 人工评审前 10 篇 |
| P2-02 | 优化 TOPIC_GEN Prompt | P2-01 | 根据反馈调整 |
| P2-03 | 优化 CONTENT_GEN Prompt | P2-01 | 增加风格示例 |
| P2-04 | 优化 REVIEW 系列 Prompt | P2-01 | 调整评分标准 |
| P2-05 | 创建 Prompt V1.1 版本 | P2-02~04 | 更新 prompt_registry.json |
| P2-06 | A/B 测试新旧 Prompt | P2-05 | 各生成 5 篇对比 |

**Prompt 优化记录模板：**

```markdown
## Prompt 优化记录

### TOPIC_GEN V1 → V1.1

**问题：**
- 生成的标题缺少数字
- 核心卖点过于抽象

**优化点：**
1. 增加示例：提供 3 个高分标题示例
2. 强制要求：标题必须包含数字或对比
3. 增加约束：每个卖点不超过 15 字

**对比结果：**
| 版本 | 平均分 | 标题含数字比例 |
|------|--------|---------------|
| V1   | 72.3   | 40%           |
| V1.1 | 81.5   | 90%           |

**结论：** V1.1 显著优于 V1，设为当前版本
```

---

#### 3.3.2 Sprint 5: 热点匹配增强（Day 14-16）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P2-07 | 优化 MediaCrawler 集成 | P1-04 | 增加抖音热搜源 |
| P2-08 | 实现语义匹配 | P2-07 | 关键词 vs 热点相似度 |
| P2-09 | 实现热点评分加权 | P2-08 | 热点相关选题加分 |
| P2-10 | 热点缓存机制 | P2-07 | 避免频繁抓取 |

**语义匹配实现：**

```javascript
// Match_Trends 节点

const topics = $json.generated_topics;  // AI 生成的选题
const hotTopics = $json.hot_topics;     // MediaCrawler 返回的热点

// 简单关键词匹配（后续可升级为 embedding）
function calculateRelevance(topic, hotTopic) {
  const topicWords = topic.title.toLowerCase().split(/\s+/);
  const hotWords = hotTopic.title.toLowerCase().split(/\s+/);

  let matchCount = 0;
  for (const word of topicWords) {
    if (hotWords.some(hw => hw.includes(word) || word.includes(hw))) {
      matchCount++;
    }
  }

  return matchCount / topicWords.length;
}

// 为每个选题计算热点相关度
const enhancedTopics = topics.map(topic => {
  let maxRelevance = 0;
  let matchedHot = null;

  for (const hot of hotTopics) {
    const relevance = calculateRelevance(topic, hot);
    if (relevance > maxRelevance) {
      maxRelevance = relevance;
      matchedHot = hot;
    }
  }

  return {
    ...topic,
    hot_relevance: maxRelevance,
    matched_hot_topic: matchedHot,
    // 相关度 ≥70% 加 10 分
    adjusted_score: topic.score + (maxRelevance >= 0.7 ? 10 : 0)
  };
});

return { json: { topics: enhancedTopics } };
```

---

#### 3.3.3 Sprint 6: 错误处理与数据分析（Day 17-20）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P2-11 | 完善重试机制 | P1-18 | 3层重试策略实现 |
| P2-12 | 添加限频保护 | P2-11 | Claude API RPM 限制 |
| P2-13 | 实现周报生成 | P1-07 | 飞书数据聚合 |
| P2-14 | 优化日志结构 | P1-19 | 便于后续分析 |
| P2-15 | Phase 2 验收 | P2-14 | 85% 成功率 |

**周报生成逻辑：**

```javascript
// Generate_Weekly_Report 节点

// 从飞书查询本周数据
const weekStart = getWeekStart();
const records = await larkAPI.queryRecords('content_records', {
  filter: `created_at >= '${weekStart}'`
});

// 统计
const stats = {
  total_generated: records.length,
  ai_reviewed: records.filter(r => r.status === 'AI_REVIEWED').length,
  published: records.filter(r => r.status === 'PUBLISHED').length,
  rejected: records.filter(r => r.status === 'REJECTED').length,
  avg_ai_score: average(records.map(r => r.ai_score)),
  top_3_contents: records.sort((a, b) => b.ai_score - a.ai_score).slice(0, 3)
};

// 生成报告文本
const report = `
📊 *本周内容生产报告*

**生成统计：**
- 总生成: ${stats.total_generated} 篇
- AI通过: ${stats.ai_reviewed} 篇 (${(stats.ai_reviewed/stats.total_generated*100).toFixed(1)}%)
- 已发布: ${stats.published} 篇
- 被拒绝: ${stats.rejected} 篇

**质量指标：**
- 平均AI评分: ${stats.avg_ai_score.toFixed(1)} 分

**Top 3 内容：**
${stats.top_3_contents.map((c, i) => `${i+1}. ${c.title} (${c.ai_score}分)`).join('\n')}
`;

return { json: { report } };
```

---

### 3.4 Phase 3: 扩展阶段（Day 21-40）

#### 3.4.1 Sprint 7: 图片生成（Day 21-25）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P3-01 | 创建 sub_image_gen 子工作流 | P1-03 | 框架搭建 |
| P3-02 | 实现图片描述生成 | P3-01 | IMAGE_DESC Prompt |
| P3-03 | 集成 Gemini API | P3-02 | 图片生成调用 |
| P3-04 | 实现图片上传存储 | P3-03 | 本地/云存储 |
| P3-05 | 图片质量检查 | P3-04 | 尺寸/格式验证 |
| P3-06 | 集成到主工作流 | P3-05 | 在审核通过后调用 |

**Gemini API 调用：**

```javascript
// Gemini_Generate_Image 节点

const response = await $http.request({
  method: 'POST',
  url: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent',
  headers: {
    'Content-Type': 'application/json',
    'x-goog-api-key': $env.GEMINI_API_KEY
  },
  body: {
    contents: [{
      parts: [{
        text: $json.image_prompt
      }]
    }],
    generationConfig: {
      responseModalities: ["image", "text"],
      imageDimensions: {
        width: 1080,
        height: 1440  // 3:4 竖图
      }
    }
  }
});

// 提取图片 base64
const imageData = response.body.candidates[0].content.parts
  .find(p => p.inlineData)?.inlineData;

if (!imageData) {
  throw new Error('图片生成失败');
}

return {
  json: {
    image_base64: imageData.data,
    mime_type: imageData.mimeType
  }
};
```

---

#### 3.4.2 Sprint 8: MCP 发布集成（Day 26-30）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P3-07 | 创建 publish_scheduler_v1 | - | 发布调度主工作流 |
| P3-08 | 集成 xiaohongshu-mcp | P0-08 | sub_publish 子工作流 |
| P3-09 | 实现账号状态检查 | P3-07 | 查询 accounts 表 |
| P3-10 | 实现限频检查 | P3-09 | 3篇/天，间隔4小时 |
| P3-11 | 实现发布后状态更新 | P3-08 | PUBLISHING → PUBLISHED/FAILED |
| P3-12 | 发布通知 | P3-11 | 成功/失败通知 |
| P3-13 | 发布功能测试 | P3-12 | 测试账号实际发布 |

**sub_publish 工作流：**

```
Input: { content_id, title, content_body, tags, image_url, account_id }
  ↓
Check_Account_Active
  ↓ (status === 'ACTIVE')
Check_Rate_Limit
  ↓ (publish_count_today < 3 && interval > 4h)
Prepare_Publish_Data
  ↓
MCP_Client(xhs_publish_note)
  ↓
├─ Success → Update_Status(PUBLISHED) → Update_Account_Stats → Output
└─ Failure → Retry(3次) → Update_Status(FAILED) → Output
```

---

#### 3.4.3 Sprint 9: 多账号与数据回流（Day 31-35）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P3-14 | 实现账号状态机 | P3-09 | ACTIVE/COOLDOWN/SUSPENDED/BANNED |
| P3-15 | 实现账号轮换 | P3-14 | 自动选择可用账号 |
| P3-16 | 创建 data_collector_v1 | - | 数据回流主工作流 |
| P3-17 | 集成 RedNote-MCP | P0-08 | 获取互动数据 |
| P3-18 | 实现真实评分计算 | P3-17 | real_score 公式 |
| P3-19 | 实现预测误差更新 | P3-18 | prediction_error 计算 |

**账号轮换逻辑：**

```javascript
// Select_Account 节点

const accounts = $json.accounts;
const now = new Date();

// 筛选可用账号
const availableAccounts = accounts.filter(acc => {
  // 状态必须是 ACTIVE
  if (acc.status !== 'ACTIVE') return false;

  // 今日发布数 < 3
  if (acc.publish_count_today >= 3) return false;

  // 距上次发布 > 4小时
  const lastPublish = new Date(acc.last_publish_at);
  const hoursSince = (now - lastPublish) / (1000 * 60 * 60);
  if (hoursSince < 4) return false;

  return true;
});

if (availableAccounts.length === 0) {
  return { json: { error: 'NO_AVAILABLE_ACCOUNT' } };
}

// 选择发布数最少的账号（负载均衡）
const selected = availableAccounts.sort(
  (a, b) => a.publish_count_today - b.publish_count_today
)[0];

return { json: { selected_account: selected } };
```

---

#### 3.4.4 Sprint 10: AI 闭环与最终验收（Day 36-40）

| 任务ID | 任务名称 | 依赖 | 详细说明 |
|--------|----------|------|----------|
| P3-20 | 实现偏差分析 | P3-19 | prediction_error 统计 |
| P3-21 | 生成优化建议 | P3-20 | 高偏差内容分析 |
| P3-22 | 回归测试全量执行 | - | 所有金数据用例 |
| P3-23 | 性能优化 | P3-22 | 瓶颈排查 |
| P3-24 | 文档更新 | P3-23 | 根据实际情况更新 |
| P3-25 | 最终验收 | P3-24 | 全部验收标准 |

---

## 4. 技术集成指南

### 4.1 服务部署架构

#### MVP 阶段架构（推荐先用这个）

```
┌─────────────────────────────────────────────────────────────┐
│            Docker Network: n8n-network                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐                        │
│  │    N8N      │    │   Nginx     │                        │
│  │  :5678      │    │  :80/:443   │                        │
│  └──────┬──────┘    └─────────────┘                        │
│         │                                                   │
└─────────┼───────────────────────────────────────────────────┘
          │
          │ HTTP 调用
          ▼
┌─────────────────────────────────────────────────────────────┐
│               服务器原生运行                                 │
│                                                             │
│  ┌───────────────────────────────────────────────┐         │
│  │  Python 脚本 (Crontab)                        │         │
│  │  hot_topics.py → 飞书 hot_topics 表           │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Claude API  │  │ Gemini API  │  │  飞书 API   │
└─────────────┘  └─────────────┘  └─────────────┘

📝 发布方式：人工从飞书表格复制内容到小红书
```

#### 扩展阶段架构（MVP 稳定后升级）

```
┌─────────────────────────────────────────────────────────────┐
│            Docker Network: n8n-network                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐                        │
│  │    N8N      │    │   Nginx     │                        │
│  │  :5678      │    │  :80/:443   │                        │
│  └──────┬──────┘    └─────────────┘                        │
└─────────┼───────────────────────────────────────────────────┘
          │
          │ HTTP 调用
          ▼
┌─────────────────────────────────────────────────────────────┐
│               服务器原生运行 (pm2 管理)                      │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ xiaohongshu-mcp │  │  RedNote-MCP    │                  │
│  │    :3000        │  │    :3001        │                  │
│  │  (Node.js)      │  │   (Node.js)     │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  ┌───────────────────────────────────────────────┐         │
│  │  Python 脚本 (Crontab)                        │         │
│  │  hot_topics.py → 飞书 hot_topics 表           │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Claude API  │  │ Gemini API  │  │  飞书 API   │
└─────────────┘  └─────────────┘  └─────────────┘

📝 发布方式：N8N → xiaohongshu-mcp → 小红书自动发布
```

### 4.2 MVP 阶段 docker-compose.yml（推荐）

```yaml
version: '3.8'

# MVP 阶段：只部署 N8N + Nginx
# 热点抓取用 Python 脚本 + Crontab
# 发布用人工操作

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
      # API Keys (通过 .env 文件注入)
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - LARK_APP_ID=${LARK_APP_ID}
      - LARK_APP_SECRET=${LARK_APP_SECRET}
      - LARK_APP_TOKEN=${LARK_APP_TOKEN}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
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
      - ./nginx/logs:/var/log/nginx
    depends_on:
      - n8n
    networks:
      - n8n-network

networks:
  n8n-network:
    driver: bridge
```

### 4.3 MVP 阶段 Nginx 配置

```nginx
# nginx/conf.d/n8n.conf

upstream n8n {
    server n8n:5678;
}

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

    # SSL 优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://n8n;
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

### 4.4 MVP 阶段 .env 配置

```bash
# .env 文件（不要提交到 Git）

# N8N 配置
N8N_HOST=your-domain.com

# Claude API
CLAUDE_API_KEY=sk-ant-xxxxx

# Gemini API
GEMINI_API_KEY=xxxxx

# 飞书配置
LARK_APP_ID=cli_xxxxx
LARK_APP_SECRET=xxxxx
LARK_APP_TOKEN=xxxxx
LARK_TABLE_CONTENT=tblContentRecords
LARK_TABLE_ACCOUNTS=tblAccounts
LARK_TABLE_LOGS=tblExecutionLogs
LARK_TABLE_INTERACTION=tblInteractionData
LARK_TABLE_HOT_TOPICS=tblHotTopics

# Telegram 通知
TELEGRAM_BOT_TOKEN=xxxxx
TELEGRAM_CHAT_ID=xxxxx
```

### 4.5 扩展阶段配置（参考）

扩展阶段需要额外添加到 .env：

```bash
# MCP 服务（扩展阶段添加）
XHS_MCP_URL=http://localhost:3000
REDNOTE_MCP_URL=http://localhost:3001
```

---

## 5. 风险评估与应对

### 5.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| **小红书 MCP 失效** | 中 | 高 | 准备备用方案（手动发布队列） |
| **MediaCrawler 被封** | 中 | 中 | 配置代理池，降低抓取频率 |
| **Claude API 限频** | 低 | 中 | 实现请求队列，错峰调用 |
| **飞书 API 变更** | 低 | 低 | 监控官方文档，及时更新 |

### 5.2 业务风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| **账号封禁** | 中 | 高 | 半自动发布，人工确认环节 |
| **内容质量波动** | 中 | 中 | 5步审核 + 人工抽检 |
| **发布频率过高** | 低 | 高 | 严格限频（3篇/天，间隔4h） |

### 5.3 应急预案

```markdown
## 应急预案

### 场景1：小红书 MCP 完全不可用
1. 立即停止 publish_scheduler_v1
2. 内容继续生成，状态保持 PENDING_APPROVAL
3. 人工通过飞书表格导出内容，手动发布
4. 联系 MCP 项目维护者或寻找替代方案

### 场景2：Claude API 大规模限频
1. 降低触发频率（每天1次 → 每2天1次）
2. 启用请求队列，增加间隔到 5 秒
3. 评估切换到 Claude Haiku 降低成本和限频

### 场景3：账号被封
1. 立即将账号状态改为 BANNED
2. 停止该账号的所有发布任务
3. 切换到备用账号继续运营
4. 分析封禁原因，调整发布策略
```

---

## 6. 验收标准与交付物

### 6.1 各阶段验收标准

#### Phase 0 验收（MVP 简化版）

| 检查项 | 标准 | 验证方式 |
|--------|------|----------|
| 服务器 | 可 SSH 访问 | ssh user@server |
| Docker | 运行正常 | docker --version |
| N8N | UI 可访问 | https://domain.com |
| Nginx | HTTPS 正常 | curl https://domain.com |
| hot_topics.py | 脚本可执行 | python3 hot_topics.py --test |
| Crontab | 定时任务已配置 | crontab -l |
| Claude API | 调用成功 | 测试请求 |
| 飞书表格 | 5张表已创建（含 hot_topics） | 手动检查 |

#### Phase 1 验收

| 检查项 | 标准 | 验证方式 |
|--------|------|----------|
| 选题生成 | 生成3-5个 | 10次测试 |
| 内容创作 | 800-1200字 | 人工检查 |
| AI审核 | 5步执行 | 日志检查 |
| 成功率 | ≥80% | 统计计算 |
| 数据存储 | 100%记录 | 飞书核对 |

#### Phase 2 验收

| 检查项 | 标准 | 验证方式 |
|--------|------|----------|
| AI通过率 | ≥85% | 30天统计 |
| 热点匹配 | ≥60%成功 | 统计计算 |
| 错误恢复 | ≥80%自动 | 日志分析 |
| 周报功能 | 正常生成 | 实际运行 |

#### Phase 3 验收

| 检查项 | 标准 | 验证方式 |
|--------|------|----------|
| 图片生成 | ≥90%成功 | 20张测试 |
| MCP发布 | ≥95%成功 | 实际发布 |
| 多账号 | 3-5个 | 轮换测试 |
| 数据回流 | 每日抓取 | 日志检查 |
| AI误差 | <15 | 统计计算 |

### 6.2 交付物清单

#### MVP 阶段交付物

| 阶段 | 交付物 | 格式 | 说明 |
|------|--------|------|------|
| Phase 0 | docker-compose.yml | YAML | N8N + Nginx 简化版 |
| Phase 0 | nginx/conf.d/n8n.conf | Nginx | 反向代理配置 |
| Phase 0 | scripts/hot_topics.py | Python | 热点抓取脚本 |
| Phase 0 | .env.example | Bash | 环境变量模板 |
| Phase 1 | content_generator_v1.json | N8N JSON | 主工作流 |
| Phase 1 | sub_ai_score.json | N8N JSON | AI审核子工作流 |
| Phase 1 | sub_notify.json | N8N JSON | 通知子工作流 |
| Phase 1 | Prompt 模板 V1 | Markdown | AI Prompt 集合 |
| Phase 2 | Prompt 模板 V1.1 | Markdown | 优化后 Prompt |
| Phase 2 | 优化报告 | Markdown | 效果对比 |

#### 扩展阶段交付物

| 阶段 | 交付物 | 格式 | 说明 |
|------|--------|------|------|
| Phase 3 | publish_scheduler_v1.json | N8N JSON | 发布调度工作流 |
| Phase 3 | data_collector_v1.json | N8N JSON | 数据回流工作流 |
| Phase 3 | sub_image_gen.json | N8N JSON | 图片生成子工作流 |
| Phase 3 | sub_publish.json | N8N JSON | MCP发布子工作流 |
| Phase 3 | pm2.config.js | JavaScript | MCP 服务 pm2 配置 |
| 最终 | 完整工作流备份 | N8N JSON | 所有工作流导出 |
| 最终 | 运维手册 | Markdown | 故障排查 SOP |

### 6.3 最终上线检查清单

```markdown
## 上线前最终检查

### 功能完整性
- [ ] 智能选题正常工作
- [ ] 内容生成正常工作
- [ ] 5步AI审核正常工作
- [ ] 图片生成正常工作
- [ ] 小红书发布正常工作
- [ ] 数据回流正常工作
- [ ] 周报生成正常工作

### 稳定性
- [ ] 连续运行7天无崩溃
- [ ] 错误自动恢复率≥80%
- [ ] 无内存泄漏

### 安全性
- [ ] 所有密钥通过环境变量管理
- [ ] .env 文件未提交到 Git
- [ ] N8N 已配置访问密码
- [ ] SSL 证书有效

### 可观测性
- [ ] 所有操作有日志记录
- [ ] 告警配置完成
- [ ] 健康检查脚本可用

### 备份
- [ ] 工作流备份脚本配置
- [ ] 定时备份任务启用
- [ ] 恢复流程已测试

### 文档
- [ ] DEVELOPMENT_GUIDE.md 已更新
- [ ] DEVELOPMENT_PLAN.md 已完成
- [ ] 运维手册已编写
- [ ] 故障排查SOP已验证
```

---

## 附录

### A. 每日站会模板

```markdown
## 站会记录 - YYYY-MM-DD

### 昨日完成
- [ ] 任务ID: xxx - 完成情况

### 今日计划
- [ ] 任务ID: xxx - 预计完成

### 阻塞问题
- 问题描述
- 需要支持

### 风险预警
- 风险描述
- 应对措施
```

### B. 代码提交规范

```
feat: 新功能
fix: Bug修复
docs: 文档更新
refactor: 重构
test: 测试
chore: 构建/工具

示例:
feat(workflow): 添加 sub_ai_score 子工作流
fix(gateway): 修复 Claude API 限频处理
docs(plan): 更新开发计划 Phase 2 任务
```

### C. 参考资源汇总

| 资源 | 链接 |
|------|------|
| MediaCrawler | https://github.com/NanmiCoder/MediaCrawler |
| xiaohongshu-mcp | https://github.com/xpzouying/xiaohongshu-mcp |
| RedNote-MCP | https://github.com/iFurySt/RedNote-MCP |
| N8N 官方文档 | https://docs.n8n.io |
| N8N 模板库 | https://n8n.io/workflows |
| Claude API 文档 | https://docs.anthropic.com |
| Gemini API 文档 | https://ai.google.dev/docs |
| 飞书开放平台 | https://open.feishu.cn |

---

*本开发计划基于需求文档v2.0和开发文档v1.0-SoT编写，用于指导项目实施。*

**文档版本：** v1.1
**创建日期：** 2024-12-11
**最后更新：** 2025-12-11
**更新说明：** v1.1 加入分阶段集成策略，MVP 阶段简化部署（N8N+Nginx Docker + 热点脚本 Crontab），扩展阶段再集成 MCP (pm2)
