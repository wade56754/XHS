# XHS 项目记忆

## 核心规则

### n8n 操作强制规则
**所有 n8n 节点操作必须通过 n8n Skills 调用 n8n-mcp**

> **MCP 来源**: https://github.com/czlonkowski/n8n-mcp
> **npm 包**: `n8n-mcp` (配置于 `.mcp.json`)

#### 禁止行为
- ❌ 手动编写 n8n 节点 JSON 配置
- ❌ 猜测节点参数和属性
- ❌ 不经验证直接部署工作流
- ❌ 跳过 skill 直接调用 MCP 工具

#### 强制流程
```
1. 调用 n8n Skill → 获取指导
2. 使用 MCP 工具 → 搜索/配置/验证
3. 验证通过 → 部署工作流
```

---

### n8n Skills (必须使用)

| Skill | 用途 | 关联 MCP 工具 |
|-------|------|---------------|
| `n8n-mcp-tools-expert` | MCP 工具使用指南 | 所有 20+ 工具 |
| `n8n-workflow-patterns` | 5 种架构模式 | search_templates, get_template |
| `n8n-node-configuration` | 节点配置指南 | get_node, validate_node |
| `n8n-validation-expert` | 错误修复指南 | validate_workflow, n8n_autofix_workflow |
| `n8n-expression-syntax` | 表达式语法 | - |
| `n8n-code-javascript` | JS Code 节点 | - |
| `n8n-code-python` | Python Code 节点 | - |

Skills 位置: `.claude/skills/`

---

### n8n-mcp 核心工具

#### 节点发现
| 工具 | 用途 | 成功率 |
|------|------|--------|
| `search_nodes` | 按关键词搜索节点 | 99.9% |
| `get_node` | 获取节点详情/文档 | 91.7% |

#### 配置验证
| 工具 | 用途 |
|------|------|
| `validate_node` | 验证单个节点配置 |
| `validate_workflow` | 验证完整工作流 |
| `n8n_autofix_workflow` | 自动修复常见错误 |

#### 工作流管理
| 工具 | 用途 |
|------|------|
| `n8n_create_workflow` | 创建新工作流 |
| `n8n_update_partial_workflow` | 增量更新 (推荐) |
| `n8n_get_workflow` | 获取工作流详情 |
| `n8n_list_workflows` | 列出所有工作流 |
| `n8n_test_workflow` | 测试执行工作流 |

#### 模板库
| 工具 | 用途 |
|------|------|
| `search_templates` | 搜索 2,700+ 模板 |
| `get_template` | 获取模板详情 |
| `n8n_deploy_template` | 部署模板到 n8n |

---

### 工作流创建标准流程

```
Step 1: 选择架构模式
  → 调用 /n8n-workflow-patterns
  → 确定: Webhook/HTTP API/Database/AI Agent/Scheduled

Step 2: 搜索节点
  → search_nodes({query: "关键词"})
  → 记录 nodeType (nodes-base.xxx)

Step 3: 获取节点配置
  → get_node({nodeType: "nodes-base.xxx", includeExamples: true})
  → 或 search_templates 获取真实配置

Step 4: 验证节点
  → validate_node({nodeType, config, profile: "runtime"})
  → 修复错误,重复验证

Step 5: 创建/更新工作流
  → n8n_create_workflow 或 n8n_update_partial_workflow
  → 注意: nodeType 格式变为 n8n-nodes-base.xxx

Step 6: 验证工作流
  → n8n_validate_workflow({id})
  → 或 validate_workflow({workflow})

Step 7: 测试执行
  → n8n_test_workflow({workflowId})
  → 检查执行结果
```

---

### nodeType 格式规则

**重要**: 不同工具使用不同格式!

| 场景 | 格式 | 示例 |
|------|------|------|
| search/validate 工具 | 短格式 | `nodes-base.httpRequest` |
| workflow 工具 | 长格式 | `n8n-nodes-base.httpRequest` |
| AI/Langchain 节点 | 特殊格式 | `@n8n/n8n-nodes-langchain.agent` |

search_nodes 返回两种格式:
```json
{
  "nodeType": "nodes-base.slack",           // 用于 validate
  "workflowNodeType": "n8n-nodes-base.slack" // 用于 workflow
}
```

---

## 项目架构

### 服务器
| 服务器 | IP | 用途 |
|--------|-----|------|
| 腾讯云 | 124.221.251.8 | MediaCrawler API (Docker) |
| 谷歌云 | 136.110.80.154 | n8n 工作流引擎 |
| Heroku | n8n.primetat.com | n8n 前端 (备用) |

### API 端点 (MediaCrawler v16)
| 端点 | 状态 | 说明 |
|------|------|------|
| `POST /api/search/human` | ✅ | 人工模拟搜索 (绕过-104) |
| `GET /api/creator/{id}` | ✅ | 获取创作者信息 |
| `POST /api/note/detail` | ⚠️ | XHS API 返回空数据 (平台限制) |
| `GET /api/health` | ✅ | 健康检查 |
| `GET /api/login/status` | ✅ | 登录状态 |

### 飞书配置

**App Token**: `Gq93bAlZ7aSSclsLKdTcYCO2nwh`

| 表格 | Table ID | 用途 |
|------|----------|------|
| tbl_candidate | tbleFs8pwdee2DWX | 候选笔记 (Topics) |
| tbl_source | tblsqXtjfMxzhUu2 | 素材库 |
| tbl_content | tblEMrCOGQuC36MU | 内容库 |
| tbl_cookie | tblYa2d2a5lypzqz | Cookie 管理 |
| tbl_config | tblH7tedq8ITPfiu | 配置表 |
| tbl_execution_lock | tblKwmP3Q9lNTJDf | 执行锁 |
| tbl_logs | tbl4asiKhYyzcDPX | 执行日志 |

**tbl_candidate 字段映射**:
| 字段 | 类型 | 说明 |
|------|------|------|
| note_id | Text (主键) | 笔记 ID |
| note_url | URL | 笔记链接 (格式: {link, text}) |
| preview_title | Text | 预览标题 |
| preview_author | Text | 作者名称 |
| preview_likes | Number | 点赞数 |
| search_keyword | Text | 搜索关键词 |
| discovery_source | Select | 来源 (search/hot/user/topic) |
| candidate_status | Select | 状态 (pending/crawling/done/skipped) |
| discovered_at | DateTime | 发现时间 (时间戳) |

---

## 工作流计划

按照 `docs/REFACTORING_PLAN_v4.0.md` 实施：

### 主工作流
- **WF-Main** - 主控制器 (定时轮询 + Webhook 手动触发)

### 子工作流
- **WF-Discovery** - 内容发现 (Keywords → Topics)
- **WF-Extraction** - 内容提取 (Topics → Source)
- **WF-Generation** - AI内容生成 (Source → Content)
- **WF-Publish** - 内容发布 (Content → Publish)

### 支撑工作流
- **WF-CookieManager** - Cookie 健康检查 + 轮换
- **WF-ErrorHandler** - 统一错误处理 + 告警

---

## 敏感信息

**不要提交到 Git：**
- `.mcp.json` - 包含飞书凭证 (已在 .gitignore)
- `.env` 文件
- API 密钥

**模板文件：**
- `.mcp.json.example` - MCP 配置模板 (占位符)

---

## 常用命令

```bash
# MediaCrawler API
ssh wade@124.221.251.8 "curl -s http://localhost:8080/api/health -H 'X-API-Key: dev-key'"

# n8n 服务
ssh wade@136.110.80.154 "curl -s http://localhost:5678/healthz"

# 人工搜索测试
curl -X POST "http://124.221.251.8:8080/api/search/human" -H "X-API-Key: dev-key" -d '{"keyword":"编程","limit":5}'
```
