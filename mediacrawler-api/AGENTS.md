# AGENTS.md - MediaCrawler API

> 小红书爬虫 API 服务

## 概述

基于 MediaCrawler 的小红书数据采集 API，运行在 Docker 容器中。

```yaml
服务器: 124.221.251.8:8080
容器名: media-crawler-api
镜像: media-crawler-api:v14+
```

## 开发指南

### 修改 API

**不要直接修改源码**，使用补丁脚本：

```bash
# 1. 创建补丁脚本
vim fix_xxx.py

# 2. 上传到服务器
scp fix_xxx.py wade@124.221.251.8:~/

# 3. 复制到容器
ssh wade@124.221.251.8 'docker cp fix_xxx.py media-crawler-api:/tmp/'

# 4. 执行补丁
ssh wade@124.221.251.8 'docker exec media-crawler-api python3 /tmp/fix_xxx.py'

# 5. 验证
curl http://124.221.251.8:8080/health
```

### 补丁脚本模板

```python
"""
补丁: [功能描述]
目标: /app/media_crawler_api/xxx.py
"""
import re

TARGET_FILE = '/app/media_crawler_api/xxx.py'

def apply():
    with open(TARGET_FILE, 'r') as f:
        content = f.read()

    # 应用修改
    if 'marker' not in content:
        content = content.replace('old_code', 'new_code')
        with open(TARGET_FILE, 'w') as f:
            f.write(content)
        print("✅ 补丁应用成功")
    else:
        print("⏭️ 补丁已存在")

if __name__ == '__main__':
    apply()
```

## API 端点

| 端点 | 方法 | 请求体 |
|------|------|--------|
| `/health` | GET | - |
| `/api/search/human` | POST | `{"keyword": "...", "limit": 10}` |
| `/api/note/detail` | POST | `{"note_id": "..."}` |
| `/api/crawler/cookies` | POST | `{"cookies": "..."}` |

## 测试命令

```bash
# 健康检查
curl http://124.221.251.8:8080/health

# 搜索
curl -X POST http://124.221.251.8:8080/api/search/human \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -d '{"keyword":"美食","limit":5}'

# 笔记详情
curl -X POST http://124.221.251.8:8080/api/note/detail \
  -H "Content-Type: application/json" \
  -d '{"note_id":"xxx"}'
```

## 已知问题

| 问题 | 状态 | 解决方案 |
|------|------|----------|
| -104 签名错误 | ✅ 已绕过 | 使用 human 搜索 |
| TypeError xsec | ✅ 已修复 | v16+ 镜像 |
| 笔记详情为空 | ⚠️ 限制 | 需要 QR 登录 |

## 容器管理

```bash
# 查看日志
docker logs media-crawler-api --tail 100

# 重启
docker restart media-crawler-api

# 提交新镜像
docker commit media-crawler-api media-crawler-api:vXX

# 进入容器
docker exec -it media-crawler-api bash
```
