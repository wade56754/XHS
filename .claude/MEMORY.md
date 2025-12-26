# 项目记忆 (Project Memory)

> 此文件记录项目关键信息，帮助 AI 助手快速理解项目上下文
> 最后更新: 2025-12-19

---

## 项目概述

**名称**: XHS 自动化运营系统
**目标**: 小红书内容自动化采集 → AI生成 → 自动发布
**技术栈**: n8n + MediaCrawler + RedInk + 飞书多维表格

---

## 服务器信息

### 腾讯云 (爬虫 API)
```yaml
ip: 124.221.251.8
user: wade
auth: SSH 免密登录
service: MediaCrawler API (Docker)
port: 8080
container: media-crawler-api
image: media-crawler-api:v16
api_key: dev-key
```

### 谷歌云 (n8n)
```yaml
ip: 136.110.80.154
user: wade
auth: SSH 免密登录
sudo_password: "103221"
service: n8n (systemd, debian用户)
port: 5678
domain: https://xhs.adpilot.club
reverse_proxy: Caddy (Docker)
caddy_config: /opt/n8n/Caddyfile
```

---

## 飞书配置

### 应用凭证
```yaml
app_id: cli_a98f34e454ba100c
app_secret: <见 .mcp.json>
app_token: Gq93bAlZ7aSSclsLKdTcYCO2nwh
```

### 表格 ID
```yaml
cookie_table: tblYa2d2a5lypzqz      # XHS Cookie 存储
topics_table: tblE2SypBdIhJVrR      # 选题库
source_table: tblPCp5gqgVFnhLc      # 素材库
content_table: tblMYjwzOkYpW4AX     # 内容库
publish_table: tblp3iSuo0dasTtg     # 发布库
prompts_table: tbloTxkevNBssapX     # 提示词库
logs_table: tbl8xTUEtAQjxP4k        # 执行日志
```

---

## API 状态

### MediaCrawler API (v16)

| 端点 | 状态 | 备注 |
|------|------|------|
| `GET /api/health` | ✅ | 健康检查 |
| `GET /api/login/status` | ✅ | 登录状态 |
| `POST /api/search/human` | ✅ | 人工搜索 (绕过-104) |
| `POST /api/crawler/cookies` | ✅ | 设置 Cookie |
| `GET /api/creator/{id}` | ✅ | 创作者信息 |
| `POST /api/note/detail` | ⚠️ | XHS 平台限制返回空数据 |

### n8n
| 检查项 | 状态 |
|--------|------|
| 健康检查 | ✅ `/healthz` 返回 ok |
| API 认证 | 需要 `X-N8N-API-KEY` |
| 外部访问 | ✅ https://xhs.adpilot.club |

---

## 已解决的问题

### 1. 搜索 -104 错误
- **问题**: XHS 搜索 API 返回 "没有权限访问"
- **原因**: 平台风控，服务器 IP 被识别
- **解决**: 使用 `/api/search/human` 人工模拟搜索
- **相关文件**: `add_human_search.py`, `fix_human_search.py`, `fix_login_modal.py`

### 2. TypeError: xsec_source
- **问题**: 调用 `get_note_by_id()` 时参数不匹配
- **解决**: 移除多余的 `xsec_source` 参数
- **相关文件**: `fix_note_detail.py`
- **修复版本**: v16

### 3. 502 Bad Gateway
- **问题**: n8n 域名无法访问
- **原因**: Caddy 配置使用 `n8n:5678` (Docker网络名)，但 n8n 运行在宿主机
- **解决**: 修改 `/opt/n8n/Caddyfile` 使用 `172.17.0.1:5678`

### 4. DNS 劫持
- **问题**: 本地 DNS 返回错误 IP
- **原因**: ISP DNS 劫持 UDP 53 端口
- **解决**: 使用 DoH 或修改 hosts 文件

---

## 镜像版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v16 | 2025-12-18 | 修复 note_detail TypeError |
| v15 | 2025-12-18 | 人工搜索 + 登录弹窗修复 |
| v14 | 2025-12-18 | 浏览器预热功能 |
| v13 | 2025-12-17 | QR 登录 + b1 等待 |
| v12 | 2025-12-17 | Pillow + QR 登录 |
| v11 | 2025-12-17 | 基础镜像 |

---

## 补丁脚本清单

### 功能添加 (add_*.py)
| 脚本 | 功能 |
|------|------|
| `add_qr_login.py` | QR 登录端点 |
| `add_warmup.py` | 浏览器预热 |
| `add_human_search.py` | 人工搜索端点 |
| `add_browser_search.py` | 浏览器原生搜索 |
| `add_sec_headers.py` | sec-ch-ua 头 |
| `add_xray_traceid.py` | x-xray-traceid 头 |

### Bug 修复 (fix_*.py)
| 脚本 | 修复内容 |
|------|----------|
| `fix_note_detail.py` | TypeError: xsec_source |
| `fix_human_search.py` | CSS 选择器 + 滚动加载 |
| `fix_login_modal.py` | 登录弹窗阻挡 |
| `fix_b1_wait.py` | b1 生成等待 |
| `fix_qrcode.py` | QR 码生成 |
| `fix_search_id.py` | search_id 格式 |

---

## 工作流脚本

| 脚本 | 用途 |
|------|------|
| `scripts/lark_client.py` | 飞书 API 客户端 |
| `scripts/create_feishu_redink_final.py` | 飞书+RedInk 工作流 |
| `scripts/deploy_redink_remote.sh` | RedInk 远程部署 |

---

## 待办事项

- [ ] 部署 RedInk 服务
- [ ] 创建完整的 n8n 工作流
- [ ] 测试端到端流程
- [ ] 配置定时任务

---

## 重要发现

### XHS 平台限制
1. **搜索 API** 严格风控，服务器 IP 容易被封
2. **笔记详情 API** 需要真实浏览器会话
3. **Cookie 导入** 不等同于登录，缺少浏览器指纹
4. **b1 值** 需要等待 4 秒生成

### 技术经验
1. `docker exec python3 -c '...'` 创建新进程，不反映 API 状态
2. 容器内文件被 Chromium 锁定时无法删除
3. Caddy 容器内 `localhost` 指向容器自身
4. `logger.info()` 在 Uvicorn 中不输出，用 `print()`
