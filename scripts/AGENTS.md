# AGENTS.md - 脚本工具

> 项目工具脚本和自动化

## 概述

此目录包含项目的工具脚本，主要用于飞书集成和工作流生成。

## 文件说明

| 文件 | 用途 |
|------|------|
| `lark_client.py` | 飞书多维表格 CRUD 客户端 |
| `create_*.py` | N8N 工作流生成脚本 |
| `setup_*.sh` | 环境部署脚本 |

## 飞书客户端使用

```python
from scripts.lark_client import LarkClient

# 初始化 (自动读取 .mcp.json)
client = LarkClient()

# 查询记录
records = client.query_records(
    table_id="tblXXX",
    filter_expr='CurrentValue.[状态]="待处理"'
)

# 创建记录
client.create_record("tblXXX", {
    "标题": "新记录",
    "状态": "待处理"
})

# 更新记录
client.update_record("tblXXX", "recXXX", {
    "状态": "已完成"
})
```

## 飞书表格 ID

```yaml
# 存储在环境变量或 .mcp.json
TOPICS_TABLE_ID: tblE2SypBdIhJVrR      # 选题库
SOURCE_TABLE_ID: tblPCp5gqgVFnhLc      # 素材库
CONTENT_TABLE_ID: tblMYjwzOkYpW4AX     # 内容库
PUBLISH_TABLE_ID: tblp3iSuo0dasTtg     # 发布库
PROMPTS_TABLE_ID: tbloTxkevNBssapX     # 提示词库
LOGS_TABLE_ID: tbl8xTUEtAQjxP4k        # 执行日志
```

## 开发规范

### 新建脚本

```python
#!/usr/bin/env python3
"""
脚本名称: xxx.py
功能描述: [简要说明]
使用方法: python scripts/xxx.py [args]
"""

import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='脚本描述')
    parser.add_argument('--arg', help='参数说明')
    args = parser.parse_args()

    # 主逻辑
    logger.info("开始执行...")

if __name__ == '__main__':
    main()
```

### 测试脚本

```bash
# 本地测试
python scripts/xxx.py --help
python scripts/xxx.py --arg value

# 确保依赖
pip install -r requirements.txt
```

## 敏感信息

```yaml
不要硬编码:
  - API Keys
  - 飞书凭证
  - 服务器密码

使用:
  - 环境变量 (.env)
  - MCP 配置 (.mcp.json)
  - 命令行参数
```
