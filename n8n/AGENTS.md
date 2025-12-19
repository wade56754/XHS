# AGENTS.md - N8N 工作流

> N8N 自动化工作流配置

## 概述

N8N 是核心的工作流编排引擎，连接所有服务。

```yaml
服务器: 136.110.80.154
端口: 5678 (内部), 443 (外部)
URL: https://xhs.adpilot.club
容器: n8n
```

## 工作流管理

### 导入工作流

```bash
# 方法1: CLI 导入
ssh wade@136.110.80.154 '
  sg docker -c "docker cp workflow.json n8n:/tmp/"
  sg docker -c "docker exec n8n n8n import:workflow --input=/tmp/workflow.json"
'

# 方法2: Web UI
1. 打开 https://xhs.adpilot.club
2. 创建新工作流
3. 菜单 → Import from File
```

### 导出工作流

```bash
# 列出所有工作流
ssh wade@136.110.80.154 'sg docker -c "docker exec n8n n8n list:workflow"'

# 导出指定工作流
ssh wade@136.110.80.154 'sg docker -c "docker exec n8n n8n export:workflow --id=xxx"'
```

### 激活工作流

```bash
# CLI 激活 (可能有限制)
ssh wade@136.110.80.154 'sg docker -c "docker exec n8n n8n update:workflow --id=xxx --active=true"'

# 推荐: 通过 Web UI 激活
```

## 工作流文件

```
n8n/workflows/
├── redink_manual_test.json         # RedInk 手动测试
├── redink_content_generator.json   # RedInk Webhook 版
└── WF-RedInk-Generate.json         # 完整生成工作流
```

## 工作流开发规范

### JSON 结构

```json
{
  "name": "工作流名称",
  "active": false,
  "versionId": "1",
  "nodes": [...],
  "connections": {...},
  "settings": {"executionOrder": "v1"}
}
```

### 节点命名

```yaml
触发器: "Webhook", "手动触发", "定时触发"
HTTP: "调用XXX API", "获取XXX"
逻辑: "检查结果", "条件判断"
输出: "返回成功", "发送通知"
```

### 常用节点

| 节点 | 类型 | 用途 |
|------|------|------|
| `n8n-nodes-base.webhook` | 触发 | HTTP 入口 |
| `n8n-nodes-base.httpRequest` | 动作 | API 调用 |
| `n8n-nodes-base.set` | 转换 | 数据映射 |
| `n8n-nodes-base.if` | 逻辑 | 条件分支 |
| `n8n-nodes-base.respondToWebhook` | 输出 | 返回响应 |

## 测试命令

```bash
# 健康检查
curl https://xhs.adpilot.club/healthz

# 测试 Webhook (需先激活)
curl -X POST https://xhs.adpilot.club/webhook/xxx \
  -H "Content-Type: application/json" \
  -d '{"data": "test"}'
```

## 容器管理

```bash
# SSH 到服务器
ssh wade@136.110.80.154

# Docker 命令 (需要 sg docker)
sg docker -c "docker ps | grep n8n"
sg docker -c "docker logs n8n --tail 50"
sg docker -c "docker restart n8n"
```

## 环境变量

关键环境变量 (在服务器 /opt/n8n/.env):

```bash
N8N_HOST=n8n.primetat.com
MEDIACRAWLER_API_URL=http://124.221.251.8:8080
REDINK_API_URL=http://localhost:12398
FEISHU_APP_ID=xxx
```
