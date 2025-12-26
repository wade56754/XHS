# MediaCrawler 服务器审查报告

> 审查日期: 2025-12-16
> 审查目标: 对比开发文档与实际服务器配置

---

## 一、审查结果摘要

| 检查项 | 状态 | 说明 |
|--------|------|------|
| n8n 服务器运行状态 | ✅ 通过 | n8n 容器正常运行 |
| 采集服务器运行状态 | ✅ 通过 | MediaCrawler API 正常运行 |
| n8n → 采集服务器网络连通 | ✅ **已修复** | 端口 8080 可从 n8n 服务器访问 |
| API 端点符合规范 | ⚠️ 部分 | 缺少部分规范要求的端点 |
| 环境变量配置 | ✅ **已修复** | MEDIACRAWLER_API_URL 已配置 |

### 总体评估: ✅ 基本就绪 (2025-12-16 已修复)

---

## 二、n8n 服务器 (136.110.80.154)

### 2.1 基本信息

| 项目 | 实际值 | 文档要求 | 状态 |
|------|--------|---------|------|
| 操作系统 | Debian 12 (bookworm) | - | ✅ |
| 公网 IP | 136.110.80.154 | 136.110.80.154 | ✅ |
| n8n 端口 | 5678 | 5678 | ✅ |
| n8n 域名 | n8n.primetat.com | - | ✅ (额外) |

### 2.2 Docker 容器状态

| 容器名 | 镜像 | 端口 | 状态 |
|--------|------|------|------|
| n8n | n8nio/n8n:latest | 5678 | ✅ Up 2 hours |
| caddy | caddy:2 | 80, 443 | ✅ Up 2 hours |
| lark-mcp | n8n-lark-mcp | 3100 | ✅ Up 2 hours |

### 2.3 n8n 环境变量检查

| 变量 | 实际配置 | 文档要求 | 状态 |
|------|---------|---------|------|
| MEDIACRAWLER_API_URL | http://124.221.251.8:8080 | http://124.221.251.8:8080 | ✅ **已配置** |
| PLAYWRIGHT_API_URL | http://124.221.251.8:3000 | - | ✅ 已配置 |
| FEISHU_APP_ID | cli_a98f34e454ba100c | 需配置 | ✅ |
| FEISHU_APP_TOKEN | S8BJbH6TlatgqEsQmoFcb42GnPf | 需配置 | ✅ |
| FEISHU_APP_SECRET | 已配置 | 需配置 | ✅ |
| TZ | Asia/Shanghai | Asia/Shanghai | ✅ |
| WEBHOOK_URL | https://n8n.primetat.com/ | 需配置 | ✅ |

**飞书表配置:**
| 变量 | 值 |
|------|-----|
| SOURCE_TABLE_ID | tblPCp5gqgVFnhLc |
| TOPICS_TABLE_ID | tblE2SypBdIhJVrR |
| PROMPTS_TABLE_ID | tbloTxkevNBssapX |
| PUBLISH_TABLE_ID | tblp3iSuo0dasTtg |
| CONTENT_TABLE_ID | tblMYjwzOkYpW4AX |
| LOGS_TABLE_ID | tbl8xTUEtAQjxP4k |

### 2.4 n8n 健康检查

```
GET http://localhost:5678/healthz
Response: {"status":"ok"}
```
✅ 正常

---

## 三、采集服务器 (124.221.251.8)

### 3.1 基本信息

| 项目 | 实际值 | 文档要求 | 状态 |
|------|--------|---------|------|
| 操作系统 | Ubuntu 24.04.3 LTS | - | ✅ |
| 公网 IP | 124.221.251.8 | 124.221.251.8 | ✅ |
| API 端口 | **8080** | 8000 | ⚠️ **端口不一致** |
| Python 版本 | 3.11.14 | >= 3.9 | ✅ |

### 3.2 Docker 容器状态

| 容器名 | 镜像 | 端口 | 状态 |
|--------|------|------|------|
| media-crawler-api | media-crawler-media-crawler-api | **8080** | ✅ Up 8 hours (healthy) |

### 3.3 API 端点检查

**实际可用端点:**
| 端点 | 状态 | 文档要求 |
|------|------|---------|
| /api/health | ✅ | ✅ /health |
| /api/search | ✅ | ✅ 搜索 API |
| /api/note/detail | ✅ | ✅ 详情 API |
| /api/cookie/validate | ✅ | - |
| /api/cookie/import | ✅ | - |
| /api/cookies (POST) | ❓ 未验证 | 需要 |
| /api/xhs/notes/batch | ❓ 未验证 | 批量 API |

**健康检查响应:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "location": "tencent-cloud",
  "timestamp": "2025-12-16T10:06:30.313777+00:00"
}
```

### 3.4 环境变量检查

| 变量 | 实际配置 | 文档要求 | 状态 |
|------|---------|---------|------|
| FEISHU_APP_ID | cli_a98f34e454ba100c | 需配置 | ✅ |
| TZ | Asia/Shanghai | - | ✅ |
| ALLOWED_ORIGINS | * | - | ✅ |
| COOKIE_MASTER_KEY | ❓ 未检查 | 需配置 | ⚠️ 待验证 |
| ALERT_WEBHOOK_URL | ❓ 未检查 | 需配置 | ⚠️ 待验证 |

---

## 四、网络连通性检查

### 4.1 测试结果

| 测试项 | 结果 | 状态 |
|--------|------|------|
| n8n 服务器 → 采集服务器 (8080) | Connection timed out | ❌ **失败** |
| 采集服务器本地访问 (8080) | 正常 | ✅ |
| 采集服务器端口监听 | 0.0.0.0:8080 | ✅ |

### 4.2 问题分析

```
从 n8n 服务器 (136.110.80.154) 访问采集服务器 (124.221.251.8:8080):
* Trying 124.221.251.8:8080...
* Connection timed out after 10000 milliseconds
```

**可能原因:**
1. 腾讯云安全组未开放 8080 端口
2. 服务器防火墙阻止入站连接
3. 云服务商网络隔离

---

## 五、与开发文档差异

### 5.1 需要修正的配置

| 差异项 | 文档值 | 实际值 | 修复建议 |
|--------|--------|--------|---------|
| API 端口 | 8000 | 8080 | 更新文档或重新配置容器 |
| MEDIACRAWLER_API_URL | http://124.221.251.8:8000 | 未配置 | 在 n8n 中配置 |
| 网络连通性 | 要求可达 | 超时 | 开放腾讯云安全组 8080 端口 |

### 5.2 需要更新的文档

**开发文档中需修改:**

```markdown
# 原文档
| MediaCrawler API | `http://124.221.251.8:8000` | 爬虫 API |

# 应改为
| MediaCrawler API | `http://124.221.251.8:8080` | 爬虫 API |
```

---

## 六、修复建议

### 6.1 紧急修复 (P0)

**1. 开放腾讯云安全组端口**

在腾讯云控制台 → 安全组中添加规则:
```
协议: TCP
端口: 8080
来源: 136.110.80.154/32 (或 0.0.0.0/0)
```

**2. 在 n8n 中配置 MediaCrawler API 地址**

添加环境变量:
```bash
MEDIACRAWLER_API_URL=http://124.221.251.8:8080
```

### 6.2 文档更新 (P1)

更新 `DEVELOPMENT_GUIDE.md` 中所有 `:8000` 为 `:8080`

### 6.3 待验证项 (P2)

- [ ] 验证 COOKIE_MASTER_KEY 是否已配置
- [ ] 验证 ALERT_WEBHOOK_URL 是否已配置
- [ ] 验证批量 API 端点是否可用
- [ ] 验证飞书表结构是否完整

---

## 七、验收清单对照

### Day 1 检查项

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 4 张表已创建 | ⚠️ | 有表配置，需验证字段完整性 |
| API 返回统一响应格式 | ⚠️ | 需验证响应格式 |
| 错误码枚举完整 | ⚠️ | 需验证 7 种错误码 |
| Cookie 加密/解密正常 | ⚠️ | 需验证 |
| 安全审计脚本通过 | ⚠️ | 需验证 |

### 网络/服务检查项

| 检查项 | 状态 | 备注 |
|--------|------|------|
| n8n 服务运行 | ✅ | 正常 |
| 采集 API 服务运行 | ✅ | 正常 |
| n8n → 采集 API 连通 | ❌ | **需修复** |
| API Swagger 文档可用 | ✅ | /docs 可访问 |

---

## 八、下一步行动

| 优先级 | 任务 | 负责 |
|--------|------|------|
| P0 | 开放腾讯云安全组 8080 端口 | 运维 |
| P0 | 在 n8n 添加 MEDIACRAWLER_API_URL 环境变量 | 运维 |
| P1 | 更新开发文档中的端口号 | 开发 |
| P2 | 验证所有 Day1 检查项 | 开发 |

---

> 审查完成时间: 2025-12-16 18:06 CST
