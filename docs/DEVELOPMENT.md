# XHS 自动化系统 - AI 开发文档

> **目标读者**: Claude Code / Cursor / GitHub Copilot
> **版本**: v1.0 | 2025-12

---

## 1. 项目上下文

```yaml
# 一句话描述
description: 小红书内容自动化运营系统 (采集→AI生成→发布)

# 技术决策
decisions:
  - 使用 n8n 而非自建调度: 低代码、可视化、易维护
  - 使用飞书表格而非数据库: 运营人员可直接操作
  - 补丁脚本模式: 避免重建镜像，快速迭代

# 当前状态
status:
  crawler_api: v16 运行中 (124.221.251.8:8080)
  n8n: 运行中 (https://xhs.adpilot.club)
  redink: 待部署
```

---

## 2. 开发环境

### 2.1 必需工具

```bash
# 本地
- Python 3.11+
- Node.js 18+
- Docker Desktop
- SSH 客户端

# 远程服务器访问
ssh wade@124.221.251.8      # 腾讯云 - 爬虫 API
ssh wade@136.110.80.154     # 谷歌云 - n8n (sudo密码: 103221)
```

### 2.2 环境变量

```bash
# .env 文件 (本地)
LARK_APP_ID=cli_a98f34e454ba100c
LARK_APP_SECRET=<从 .mcp.json 获取>
LARK_APP_TOKEN=Gq93bAlZ7aSSclsLKdTcYCO2nwh

# 表格 ID
TOPICS_TABLE_ID=tblE2SypBdIhJVrR
SOURCE_TABLE_ID=tblPCp5gqgVFnhLc
CONTENT_TABLE_ID=tblMYjwzOkYpW4AX
COOKIE_TABLE_ID=tblYa2d2a5lypzqz
```

### 2.3 MCP 服务器

```json
// .mcp.json - AI 助手可用的工具
{
  "n8n-mcp": "n8n 工作流操作",
  "lark": "飞书表格 CRUD",
  "context7": "获取库文档",
  "fetch": "网页抓取"
}
```

---

## 3. 代码规范

### 3.1 Python 规范

```python
# 文件头模板
"""
模块说明: xxx
作者: AI Assistant
日期: 2025-12
"""

# 命名规范
file_name.py          # 蛇形命名
class ClassName:      # 大驼峰
def function_name():  # 蛇形命名
CONSTANT_VALUE = 1    # 大写下划线

# 类型注解 (必需)
def process_note(note_id: str, options: dict | None = None) -> dict:
    """处理笔记数据"""
    pass

# 错误处理模式
try:
    result = await api_call()
except httpx.TimeoutException:
    logger.warning(f"API 超时: {url}")
    raise
except Exception as e:
    logger.error(f"未知错误: {e}")
    raise
```

### 3.2 补丁脚本模式

```python
#!/usr/bin/env python3
"""
补丁: fix_xxx.py
功能: 修复 xxx 问题
应用: docker exec media-crawler-api python3 /tmp/fix_xxx.py
"""

import re

TARGET_FILE = '/app/main.py'

def apply_patch():
    with open(TARGET_FILE, 'r') as f:
        content = f.read()

    # 1. 定义要查找的代码
    old_code = '''原始代码'''

    # 2. 定义替换后的代码
    new_code = '''修复后代码'''

    # 3. 验证原代码存在
    if old_code not in content:
        print("ERROR: 未找到目标代码，可能已修复或文件结构变化")
        return False

    # 4. 应用替换
    content = content.replace(old_code, new_code)

    with open(TARGET_FILE, 'w') as f:
        f.write(content)

    print("SUCCESS: 补丁应用成功")
    return True

if __name__ == '__main__':
    apply_patch()
```

### 3.3 n8n 工作流脚本

```python
#!/usr/bin/env python3
"""
工作流生成: create_xxx_workflow.py
功能: 生成 xxx 工作流 JSON
导入: n8n API 或手动导入
"""

import json

def create_workflow():
    workflow = {
        "name": "工作流名称",
        "nodes": [],
        "connections": {},
        "settings": {"executionOrder": "v1"}
    }

    # 添加触发节点
    workflow["nodes"].append({
        "id": "trigger",
        "name": "Schedule Trigger",
        "type": "n8n-nodes-base.scheduleTrigger",
        "position": [250, 300],
        "parameters": {
            "rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}
        }
    })

    # 添加飞书节点
    workflow["nodes"].append({
        "id": "feishu",
        "name": "查询飞书",
        "type": "n8n-nodes-feishu-lite.feishuLite",
        "position": [450, 300],
        "parameters": {
            "operation": "bitable:table:record:query",
            "app_token": "={{$env.LARK_APP_TOKEN}}",
            "table_id": "tblXXX"
        }
    })

    # 定义连接
    workflow["connections"] = {
        "Schedule Trigger": {"main": [[{"node": "查询飞书", "type": "main", "index": 0}]]}
    }

    return workflow

if __name__ == '__main__':
    wf = create_workflow()
    print(json.dumps(wf, ensure_ascii=False, indent=2))
```

---

## 4. 开发任务指南

### 4.1 添加新的爬虫 API 端点

```bash
# 步骤 1: 创建补丁脚本
cat > add_new_endpoint.py << 'EOF'
"""添加 /api/xxx 端点"""

TARGET_FILE = '/app/main.py'

NEW_ENDPOINT = '''
@app.post("/api/xxx")
async def xxx_endpoint(request: Request):
    """新端点说明"""
    api_key = request.headers.get("X-API-Key")
    if api_key != API_KEY:
        raise HTTPException(status_code=401)

    data = await request.json()
    # 业务逻辑
    return {"success": True, "data": result}
'''

def apply():
    with open(TARGET_FILE, 'r') as f:
        content = f.read()

    # 在文件末尾添加 (app.run 之前)
    marker = 'if __name__ == "__main__":'
    content = content.replace(marker, NEW_ENDPOINT + '\n\n' + marker)

    with open(TARGET_FILE, 'w') as f:
        f.write(content)
    print("SUCCESS")

if __name__ == '__main__':
    apply()
EOF

# 步骤 2: 应用到容器
scp add_new_endpoint.py wade@124.221.251.8:/tmp/
ssh wade@124.221.251.8 << 'EOF'
docker cp /tmp/add_new_endpoint.py media-crawler-api:/tmp/
docker exec media-crawler-api python3 /tmp/add_new_endpoint.py
docker restart media-crawler-api
EOF

# 步骤 3: 测试
curl -X POST "http://124.221.251.8:8080/api/xxx" \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'

# 步骤 4: 提交镜像 (如果测试通过)
ssh wade@124.221.251.8 "docker commit media-crawler-api media-crawler-api:v17"
```

### 4.2 创建 n8n 工作流

```bash
# 步骤 1: 编写工作流生成脚本
python scripts/create_xxx_workflow.py > workflow.json

# 步骤 2: 通过 API 导入 (需要 API Key)
curl -X POST "https://xhs.adpilot.club/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @workflow.json

# 或手动导入
# 1. 打开 https://xhs.adpilot.club
# 2. 设置 → 导入工作流 → 粘贴 JSON
```

### 4.3 操作飞书表格

```python
# scripts/lark_example.py
from lark_client import LarkClient

client = LarkClient()

# 查询待处理记录
records = client.query_records(
    table_id="tblE2SypBdIhJVrR",
    filter={
        "conditions": [
            {"field_name": "status", "operator": "is", "value": ["待采集"]}
        ]
    }
)

# 批量更新状态
updates = [
    {"record_id": r["record_id"], "fields": {"status": "处理中"}}
    for r in records
]
client.batch_update("tblE2SypBdIhJVrR", updates)

# 创建新记录
client.create_record("tblE2SypBdIhJVrR", {
    "keyword": "穿搭分享",
    "category": "穿搭",
    "status": "待采集",
    "min_likes": 1000
})
```

### 4.4 调试爬虫问题

```bash
# 查看容器日志
ssh wade@124.221.251.8 "docker logs media-crawler-api --tail 100"

# 进入容器调试
ssh wade@124.221.251.8 "docker exec -it media-crawler-api bash"

# 容器内 Python 调试
python3 -c "
from main import xhs_client
import asyncio

async def debug():
    # 测试 API 调用
    result = await xhs_client.get_creator_info('user_id')
    print(result)

asyncio.run(debug())
"

# 添加调试日志
ssh wade@124.221.251.8 << 'EOF'
docker exec media-crawler-api sed -i \
  's/result = await/print(f"DEBUG: calling API"); result = await/' \
  /app/main.py
docker restart media-crawler-api
EOF
```

---

## 5. API 参考

### 5.1 MediaCrawler API

```yaml
base_url: http://124.221.251.8:8080
auth: X-API-Key: dev-key

endpoints:
  # 健康检查
  GET /api/health:
    response: {status, crawler_ready, version}

  # 人工搜索 (推荐)
  POST /api/search/human:
    body: {keyword: string, limit: int, skip_warmup?: bool}
    response: {success, data: {items: [], total}}

  # 设置 Cookie
  POST /api/crawler/cookies:
    body: {cookies: [{name, value, domain, path}]}
    response: {success, data: {crawler_ready}}

  # 创作者信息
  GET /api/creator/{user_id}:
    response: {success, data: {nickname, avatar, notes}}

  # 笔记详情 (有平台限制)
  POST /api/note/detail:
    body: {note_ids: string[]}
    response: {success, data: {items: [], failed_ids}}
```

### 5.2 RedInk API

```yaml
base_url: http://localhost:12398

endpoints:
  # 生成大纲
  POST /api/outline:
    body: {topic: string}
    response: {outline: string, pages: [{title, content}]}

  # 生成图片 (SSE)
  POST /api/generate:
    body: {pages: [{title, content}]}
    response: SSE stream
      - {status: "generating", current: 1, total: 5}
      - {status: "done", image_url: "/api/images/xxx/0.png"}
      - {success: true, task_id: "xxx"}

  # 获取图片
  GET /api/images/{task_id}/{index}.png:
    response: image/png
```

### 5.3 飞书 API (via LarkClient)

```python
# 初始化
client = LarkClient()  # 自动读取环境变量

# 查询记录
records = client.query_records(
    table_id="tblXXX",
    filter={"conditions": [...]},  # 可选
    page_size=100                   # 可选
)

# 获取所有记录 (自动分页)
all_records = client.get_all_records("tblXXX")

# 创建记录
record_id = client.create_record("tblXXX", {"field": "value"})

# 更新记录
client.update_record("tblXXX", "recXXX", {"field": "new_value"})

# 批量创建
client.batch_create("tblXXX", [{"field": "v1"}, {"field": "v2"}])

# 删除记录
client.delete_record("tblXXX", "recXXX")
```

---

## 6. 测试清单

### 6.1 爬虫 API 测试

```bash
#!/bin/bash
# test_crawler.sh

API="http://124.221.251.8:8080"
KEY="dev-key"

echo "=== 健康检查 ==="
curl -s "$API/api/health" -H "X-API-Key: $KEY" | jq .

echo "=== 登录状态 ==="
curl -s "$API/api/login/status" -H "X-API-Key: $KEY" | jq .

echo "=== 人工搜索 ==="
curl -s -X POST "$API/api/search/human" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"keyword":"美食","limit":3}' | jq .

echo "=== 创作者信息 ==="
curl -s "$API/api/creator/5dc866630000000001008f8d" \
  -H "X-API-Key: $KEY" | jq .
```

### 6.2 n8n 工作流测试

```bash
# 测试 n8n 健康状态
curl -s https://xhs.adpilot.club/healthz

# 列出工作流 (需要 API Key)
curl -s https://xhs.adpilot.club/api/v1/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[].name'

# 手动触发工作流
curl -X POST "https://xhs.adpilot.club/api/v1/workflows/{id}/activate" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

### 6.3 飞书集成测试

```python
# test_feishu.py
from scripts.lark_client import LarkClient

def test_connection():
    client = LarkClient()

    # 测试读取
    records = client.query_records("tblE2SypBdIhJVrR", page_size=1)
    assert len(records) >= 0, "查询失败"
    print(f"✅ 读取成功: {len(records)} 条记录")

    # 测试创建 + 删除
    record_id = client.create_record("tblE2SypBdIhJVrR", {
        "keyword": "__test__",
        "status": "待采集"
    })
    print(f"✅ 创建成功: {record_id}")

    client.delete_record("tblE2SypBdIhJVrR", record_id)
    print(f"✅ 删除成功")

if __name__ == '__main__':
    test_connection()
```

---

## 7. 故障排除

### 7.1 常见错误速查

| 错误 | 原因 | 解决 |
|------|------|------|
| `-104 权限错误` | XHS 搜索 API 限制 | 使用 `/api/search/human` |
| `TypeError: xsec_source` | 参数不匹配 | 应用 `fix_note_detail.py` |
| `502 Bad Gateway` | Caddy 代理错误 | 检查 `/opt/n8n/Caddyfile` |
| `Cookie 过期` | 登录失效 | 更新飞书 Cookie 表 |
| `CRAWLER_NOT_READY` | 未初始化 | 调用 `/api/crawler/cookies` |
| `飞书 token 过期` | Token 2小时有效 | LarkClient 自动刷新 |

### 7.2 调试命令

```bash
# 查看爬虫日志
ssh wade@124.221.251.8 "docker logs media-crawler-api --tail 50 -f"

# 查看 n8n 日志
ssh wade@136.110.80.154 "journalctl -u n8n -f"

# 查看 Caddy 状态
ssh wade@136.110.80.154 "ps aux | grep caddy"

# 测试容器内网络
ssh wade@124.221.251.8 "docker exec media-crawler-api curl -s https://www.xiaohongshu.com"
```

### 7.3 重启服务

```bash
# 重启爬虫 API
ssh wade@124.221.251.8 "docker restart media-crawler-api"

# 重启 n8n
ssh wade@136.110.80.154 "echo '103221' | sudo -S systemctl restart n8n"

# 重启 Caddy
ssh wade@136.110.80.154 "echo '103221' | sudo -S docker restart caddy"
```

---

## 8. 部署流程

### 8.1 发布新版本爬虫

```bash
# 1. 应用所有补丁
for patch in fix_*.py add_*.py; do
  scp $patch wade@124.221.251.8:/tmp/
  ssh wade@124.221.251.8 "docker cp /tmp/$patch media-crawler-api:/tmp/"
  ssh wade@124.221.251.8 "docker exec media-crawler-api python3 /tmp/$patch"
done

# 2. 测试
bash test_crawler.sh

# 3. 提交新镜像
ssh wade@124.221.251.8 "docker commit media-crawler-api media-crawler-api:v17"

# 4. 备份旧镜像
ssh wade@124.221.251.8 "docker tag media-crawler-api:v16 media-crawler-api:v16-backup"
```

### 8.2 部署 n8n 工作流

```bash
# 1. 生成工作流 JSON
python scripts/create_feishu_redink_final.py > workflow.json

# 2. 导入到 n8n
# 方式A: API
curl -X POST "https://xhs.adpilot.club/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -d @workflow.json

# 方式B: 手动
# 打开 https://xhs.adpilot.club → 设置 → 导入

# 3. 激活工作流
curl -X POST "https://xhs.adpilot.club/api/v1/workflows/{id}/activate" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

---

## 9. 文件索引

| 文件 | 类型 | 说明 |
|------|------|------|
| `CLAUDE.md` | 配置 | AI 助手主指令文件 |
| `.mcp.json` | 配置 | MCP 服务器配置 (含凭证) |
| `.env` | 配置 | 环境变量 |
| `scripts/lark_client.py` | 库 | 飞书 API 客户端 |
| `scripts/create_*.py` | 脚本 | n8n 工作流生成器 |
| `add_*.py` | 补丁 | 爬虫功能添加 |
| `fix_*.py` | 补丁 | 爬虫 bug 修复 |
| `docs/飞书+n8n+小红书...md` | 文档 | 系统架构文档 |
| `docs/DEVELOPMENT.md` | 文档 | 本开发文档 |

---

## 10. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v16 | 2025-12-18 | 修复 note_detail TypeError |
| v15 | 2025-12-18 | 添加人工搜索、修复登录弹窗 |
| v14 | 2025-12-18 | 添加浏览器预热 |
| v13 | 2025-12-17 | QR 登录 + b1 等待 |

---

*文档版本: v1.0 | AI-Friendly Development Guide | 2025-12*
