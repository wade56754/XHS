# 项目规则 (Project Rules)

> AI 助手在此项目中必须遵循的规则和约束
> 优先级: 高 → 必须遵守 | 中 → 强烈建议 | 低 → 可选

---

## 1. 安全规则 [高]

### 1.1 敏感信息保护
```yaml
禁止提交:
  - .mcp.json          # 包含飞书凭证
  - .env               # 包含 API 密钥
  - *_secret*          # 任何包含 secret 的文件
  - *.pem, *.key       # 证书和密钥

已配置 .gitignore:
  - .mcp.json
  - .env
  - browser_data/
```

### 1.2 服务器操作
```yaml
禁止:
  - 删除生产数据
  - 修改 sudo 密码
  - 暴露新端口到公网
  - 停止运行中的关键服务

需要确认:
  - docker rm 操作
  - 数据库清理
  - 用户权限修改
```

---

## 2. 代码规则 [高]

### 2.1 修改爬虫 API
```yaml
必须:
  - 使用补丁脚本模式 (add_*.py / fix_*.py)
  - 先在本地编写和测试补丁
  - 应用后立即测试
  - 测试通过后提交新镜像版本

禁止:
  - 直接在容器内 vim/nano 编辑
  - sed 修改多行代码 (易出错)
  - 不测试就提交镜像
```

**补丁脚本模板:**
```python
#!/usr/bin/env python3
"""
补丁: fix_xxx.py
功能: 修复 xxx
应用: docker exec media-crawler-api python3 /tmp/fix_xxx.py
"""

TARGET_FILE = '/app/main.py'

def apply_patch():
    with open(TARGET_FILE, 'r') as f:
        content = f.read()

    old_code = '''要替换的代码'''
    new_code = '''替换后的代码'''

    if old_code not in content:
        print("ERROR: 未找到目标代码")
        return False

    content = content.replace(old_code, new_code)

    with open(TARGET_FILE, 'w') as f:
        f.write(content)

    print("SUCCESS: 补丁应用成功")
    return True

if __name__ == '__main__':
    apply_patch()
```

### 2.2 创建 n8n 工作流
```yaml
必须:
  - 使用 Python 脚本生成 JSON
  - 脚本存放在 scripts/create_*.py
  - 通过 API 或界面导入

禁止:
  - 手动编辑工作流 JSON
  - 直接在 n8n 界面从零创建复杂工作流
```

### 2.3 飞书集成
```yaml
必须:
  - 使用 scripts/lark_client.py
  - 凭证从环境变量读取
  - 处理 token 过期自动刷新

禁止:
  - 硬编码凭证
  - 在代码中打印凭证
```

---

## 3. 命名规范 [中]

### 3.1 文件命名
```yaml
补丁脚本:
  - add_功能名.py     # 添加功能
  - fix_问题名.py     # 修复问题

工作流脚本:
  - create_工作流名_workflow.py

部署脚本:
  - deploy_服务名.sh
  - setup_服务名.sh
```

### 3.2 变量命名
```python
# Python
snake_case          # 变量和函数
UPPER_SNAKE_CASE   # 常量
PascalCase         # 类名

# 环境变量
LARK_APP_ID        # 飞书相关
XHS_*              # 小红书相关
N8N_*              # n8n 相关
```

### 3.3 Docker 镜像版本
```yaml
格式: media-crawler-api:v{版本号}
示例: media-crawler-api:v16
规则: 每次重要修改递增版本号
```

---

## 4. Git 规则 [中]

### 4.1 提交信息格式
```yaml
格式: "{type}: {简短描述}"

类型:
  - feat: 新功能
  - fix: Bug 修复
  - docs: 文档更新
  - refactor: 重构
  - chore: 杂项

示例:
  - "feat: 添加人工搜索 API"
  - "fix: 修复 note_detail TypeError"
  - "docs: 更新架构文档为 AI 友好格式"
```

### 4.2 分支策略
```yaml
main: 稳定版本
开发: 直接在 main 上进行 (小项目)
```

### 4.3 提交前检查
```bash
# 检查敏感文件
git diff --cached --name-only | grep -E "\.env|\.mcp\.json|secret"

# 如有匹配，取消暂存
git reset HEAD <敏感文件>
```

---

## 5. 测试规则 [中]

### 5.1 API 修改后必须测试
```bash
# 健康检查
curl -s "http://124.221.251.8:8080/api/health" -H "X-API-Key: dev-key"

# 功能测试
curl -s -X POST "http://124.221.251.8:8080/api/search/human" \
  -H "X-API-Key: dev-key" \
  -d '{"keyword":"测试","limit":3}'
```

### 5.2 n8n 工作流测试
```yaml
步骤:
  1. 导入工作流
  2. 手动执行一次
  3. 检查执行日志
  4. 验证飞书表格数据
```

---

## 6. 文档规则 [中]

### 6.1 文档优先级
```yaml
必须更新:
  - CLAUDE.md          # 项目变更时
  - .claude/MEMORY.md  # 重要发现时
  - docs/DEVELOPMENT.md # 新增开发模式时

可选更新:
  - docs/架构文档.md    # 架构变更时
```

### 6.2 文档格式
```yaml
必须:
  - 使用 Markdown
  - 代码块指定语言
  - 表格对齐
  - 命令可直接复制执行

禁止:
  - 过期信息不更新
  - 复杂嵌套结构
```

---

## 7. 调试规则 [低]

### 7.1 日志输出
```python
# 在 Uvicorn 环境中
print(f"DEBUG: {message}")  # ✅ 会输出
logger.info(message)         # ❌ 可能不输出
```

### 7.2 容器调试
```bash
# 查看日志
docker logs media-crawler-api --tail 50

# 进入容器
docker exec -it media-crawler-api bash

# 不要用 docker exec python3 -c '...' 测试 API 状态
# 因为会创建新进程，不反映运行中的 API 状态
```

---

## 8. 部署规则 [中]

### 8.1 镜像更新流程
```bash
# 1. 应用补丁
docker cp patch.py media-crawler-api:/tmp/
docker exec media-crawler-api python3 /tmp/patch.py

# 2. 重启测试
docker restart media-crawler-api
# 等待 10 秒
curl http://124.221.251.8:8080/api/health -H "X-API-Key: dev-key"

# 3. 测试通过后提交
docker commit media-crawler-api media-crawler-api:v{新版本}

# 4. 备份旧版本
docker tag media-crawler-api:v{旧版本} media-crawler-api:v{旧版本}-backup
```

### 8.2 回滚流程
```bash
# 停止当前容器
docker stop media-crawler-api
docker rm media-crawler-api

# 使用旧版本启动
docker run -d --name media-crawler-api \
  -p 8080:8080 \
  -v /home/wade/media-crawler/browser_data:/app/browser_data \
  -e API_KEY=dev-key \
  -e HEADLESS=true \
  media-crawler-api:v{旧版本} \
  uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## 9. 禁止事项汇总

```yaml
绝对禁止:
  - 提交 .mcp.json 到 Git
  - 在代码中硬编码凭证
  - 直接在容器内编辑代码
  - 不测试就提交镜像
  - 删除生产数据
  - 暴露敏感端口

强烈避免:
  - 手动编辑 n8n 工作流 JSON
  - 使用 sed 修改多行 Python 代码
  - docker exec python3 测试 API 状态
  - 忽略错误直接继续
```

---

## 10. 快速参考卡片

```yaml
# 常用命令
测试爬虫: curl -X POST "http://124.221.251.8:8080/api/search/human" -H "X-API-Key: dev-key" -d '{"keyword":"测试","limit":3}'
测试n8n: curl https://xhs.adpilot.club/healthz
查看日志: ssh wade@124.221.251.8 "docker logs media-crawler-api --tail 50"
应用补丁: docker exec media-crawler-api python3 /tmp/patch.py
提交镜像: docker commit media-crawler-api media-crawler-api:vXX

# SSH 连接
腾讯云: ssh wade@124.221.251.8
谷歌云: ssh wade@136.110.80.154 (sudo密码: 103221)

# 关键路径
飞书凭证: .mcp.json
环境变量: .env
补丁脚本: ./add_*.py, ./fix_*.py
工作流脚本: ./scripts/create_*.py
Caddy配置: /opt/n8n/Caddyfile (谷歌云)
```
