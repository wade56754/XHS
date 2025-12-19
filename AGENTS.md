# AGENTS.md - XHS 自动化运营系统

> 为 AI 编码代理提供的项目指导文件

## 项目概述

这是一个**小红书自动化运营系统**，集成了内容采集、AI生成、自动发布的完整工作流。

```yaml
类型: 低代码自动化运营平台
技术栈: n8n + MediaCrawler + RedInk + 飞书多维表格
语言: Python (后端) + TypeScript (n8n)
```

## 服务器环境

| 服务器 | IP | 用途 | SSH |
|--------|-----|------|-----|
| 腾讯云 | 124.221.251.8 | MediaCrawler API | `ssh wade@124.221.251.8` |
| 谷歌云 | 136.110.80.154 | N8N + RedInk | `ssh wade@136.110.80.154` |

```bash
# 服务端口
MediaCrawler API: 124.221.251.8:8080
N8N:              https://xhs.adpilot.club (136.110.80.154:443)
RedInk:           136.110.80.154:12398
```

## 开发环境

### 前置条件

```bash
# 必需
- Python 3.11+
- Docker & Docker Compose
- SSH 密钥配置 (~/.ssh/id_rsa)

# 可选
- Node.js 18+ (本地 n8n 开发)
```

### 本地开发

```bash
# 克隆项目
git clone https://github.com/wade56754/XHS.git
cd XHS

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入必要的 API Keys

# 启动本地服务 (可选)
docker-compose up -d
```

## 构建与测试

### 爬虫 API 测试

```bash
# 健康检查
curl http://124.221.251.8:8080/health

# 人工搜索 API
curl -X POST "http://124.221.251.8:8080/api/search/human" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -d '{"keyword":"美食","limit":5}'
```

### N8N 测试

```bash
# 健康检查
curl https://xhs.adpilot.club/healthz

# 列出工作流
ssh wade@136.110.80.154 'sg docker -c "docker exec n8n n8n list:workflow"'
```

### RedInk 测试

```bash
# 健康检查
curl http://136.110.80.154:12398/api/health

# 生成大纲
curl -X POST http://136.110.80.154:12398/api/outline \
  -H "Content-Type: application/json" \
  -d '{"topic": "测试主题"}'
```

## 代码规范

### Python 补丁脚本

```python
# 命名规范
add_xxx.py   # 添加新功能
fix_xxx.py   # 修复 bug

# 补丁脚本模板
"""
补丁说明: [功能描述]
目标文件: [要修改的文件路径]
"""
import re

def apply_patch():
    # 读取文件
    with open('/app/xxx.py', 'r') as f:
        content = f.read()

    # 应用补丁
    new_content = content.replace('old', 'new')

    # 写入文件
    with open('/app/xxx.py', 'w') as f:
        f.write(new_content)

    print("补丁应用成功")

if __name__ == '__main__':
    apply_patch()
```

### N8N 工作流

- 使用 JSON 文件存储工作流定义
- 工作流文件存放在 `n8n/workflows/` 目录
- 使用 `n8n import:workflow` 命令导入

### 提交规范

```bash
# 提交消息格式
<type>: <description>

# 类型
feat:     新功能
fix:      bug 修复
docs:     文档更新
refactor: 重构
test:     测试
chore:    杂项

# 示例
feat: 添加 RedInk 图文生成集成
fix: 修复搜索 API -104 错误
docs: 更新 AGENTS.md
```

## 常用任务

### 1. 修改爬虫 API

```bash
# 步骤
1. 创建补丁脚本 (fix_xxx.py 或 add_xxx.py)
2. 复制到容器:
   scp fix_xxx.py wade@124.221.251.8:~/
   ssh wade@124.221.251.8 'docker cp fix_xxx.py media-crawler-api:/tmp/'
3. 执行补丁:
   ssh wade@124.221.251.8 'docker exec media-crawler-api python3 /tmp/fix_xxx.py'
4. 重启容器 (如需):
   ssh wade@124.221.251.8 'docker restart media-crawler-api'
5. 提交新镜像:
   ssh wade@124.221.251.8 'docker commit media-crawler-api media-crawler-api:vXX'
```

### 2. 创建 N8N 工作流

```bash
# 方法1: 通过 CLI 导入
ssh wade@136.110.80.154 '
  sg docker -c "docker cp workflow.json n8n:/tmp/"
  sg docker -c "docker exec n8n n8n import:workflow --input=/tmp/workflow.json"
'

# 方法2: 通过 Web UI
打开 https://xhs.adpilot.club → 创建新工作流 → 导入 JSON
```

### 3. 部署 RedInk 更新

```bash
ssh wade@136.110.80.154 '
  cd ~/redink
  sg docker -c "docker compose pull"
  sg docker -c "docker compose up -d"
'
```

### 4. 查看服务日志

```bash
# MediaCrawler
ssh wade@124.221.251.8 'docker logs media-crawler-api --tail 50'

# N8N
ssh wade@136.110.80.154 'sg docker -c "docker logs n8n --tail 50"'

# RedInk
ssh wade@136.110.80.154 'sg docker -c "docker logs redink --tail 50"'
```

## API 参考

### MediaCrawler API (124.221.251.8:8080)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/search/human` | POST | 人工模拟搜索 |
| `/api/note/detail` | POST | 获取笔记详情 |
| `/api/crawler/cookies` | POST | 设置 Cookie |

### RedInk API (136.110.80.154:12398)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/outline` | POST | 生成内容大纲 |
| `/api/generate` | POST | 生成图片 |
| `/api/images/<task_id>/<filename>` | GET | 获取图片 |

## 项目结构

```
XHS/
├── AGENTS.md              # AI 代理指导 (本文件)
├── CLAUDE.md              # Claude 特定指令
├── .env.example           # 环境变量模板
├── docker-compose.yml     # Docker 编排
│
├── scripts/               # 工具脚本
│   └── lark_client.py     # 飞书 API 客户端
│
├── add_*.py               # 爬虫功能补丁
├── fix_*.py               # 爬虫修复补丁
│
├── n8n/
│   ├── workflows/         # N8N 工作流 JSON
│   └── credentials/       # 凭证模板
│
├── mediacrawler-api/      # 爬虫 API 源码
│
├── redink/                # RedInk 配置
│   ├── text_providers.yaml
│   └── image_providers.yaml
│
├── docs/                  # 文档
│   ├── DEVELOPMENT.md
│   └── 架构文档.md
│
└── .claude/
    ├── skills/            # Claude Code 技能
    └── settings.local.json
```

## 安全注意事项

```yaml
敏感文件 (勿提交):
  - .env                   # 环境变量
  - .mcp.json              # MCP 配置 (飞书凭证)
  - n8n/credentials/*.json # N8N 凭证

已在 .gitignore:
  - *.png, *.jpg           # 二维码图片
  - temp_*.py              # 临时脚本
  - __pycache__/
```

## 故障排除

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 搜索返回 -104 | 签名失效 | 使用 `/api/search/human` |
| 笔记详情为空 | 需要登录 | 执行 QR 登录流程 |
| Docker 权限拒绝 | 用户不在 docker 组 | `sudo usermod -aG docker $USER` |
| RedInk API 超时 | Google API 不可达 | 检查服务器网络 |

### 日志位置

```bash
# 服务器日志
MediaCrawler: docker logs media-crawler-api
N8N:          docker logs n8n
RedInk:       docker logs redink

# 本地日志
./logs/       # 如有配置
```

## 相关文档

- [开发指南](docs/DEVELOPMENT.md) - 详细开发步骤
- [架构文档](docs/飞书+n8n+小红书自动化运营系统架构文档.md) - 系统设计
- [RedInk 集成](docs/REDINK_INTEGRATION_PLAN.md) - AI 图文生成

---

*此文件遵循 [agents.md](https://agents.md) 规范，为 AI 编码代理提供项目上下文。*
