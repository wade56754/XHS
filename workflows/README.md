# XHS 内容自动化工作流

本目录包含 4 个 n8n 子工作流，用于实现小红书内容的自动化采集、处理和发布。

## 工作流概览

| 工作流 | 文件 | 功能 | 触发方式 |
|--------|------|------|----------|
| WF-Discovery | `WF-Discovery.json` | 搜索热门内容 | 每30分钟 / Webhook |
| WF-Extraction | `WF-Extraction.json` | 提取笔记详情 | 每15分钟 / Webhook |
| WF-Generation | `WF-Generation.json` | AI 内容生成 | 每20分钟 / Webhook |
| WF-Publish | `WF-Publish.json` | 发布到小红书 | 每2小时 / Webhook |

## 数据流

```
Keywords (关键词表)
    ↓ [WF-Discovery]
Topics (选题表)
    ↓ [WF-Extraction]
Source (素材表)
    ↓ [WF-Generation]
Content (内容表)
    ↓ [WF-Publish]
Publish (发布表)
```

## 安装步骤

### 1. 配置环境变量

在 n8n 中设置以下环境变量（参考 `n8n-env-template.txt`）：

```bash
# 飞书配置
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
LARK_APP_TOKEN=xxx
LARK_KEYWORDS_TABLE_ID=tblXxx
LARK_TOPICS_TABLE_ID=tblXxx
LARK_SOURCE_TABLE_ID=tblXxx
LARK_CONTENT_TABLE_ID=tblXxx
LARK_PUBLISH_TABLE_ID=tblXxx
LARK_PROMPTS_TABLE_ID=tblXxx
LARK_LOGS_TABLE_ID=tblXxx

# 爬虫 API
CRAWLER_API_URL=http://124.221.251.8:8080
CRAWLER_API_KEY=dev-key

# RedInk AI
REDINK_API_URL=http://xxx:3000
REDINK_API_KEY=xxx
```

### 2. 导入工作流

1. 打开 n8n 界面
2. 点击 "Import from file"
3. 依次导入 4 个 JSON 文件
4. 检查并修改节点配置（如有必要）
5. **手动激活**每个工作流

### 3. Webhook 端点

导入后，每个工作流将创建以下 Webhook 端点：

| 工作流 | Webhook 路径 | 用途 |
|--------|-------------|------|
| WF-Discovery | `/webhook/xhs-discovery` | 手动触发内容发现 |
| WF-Extraction | `/webhook/xhs-extraction` | 手动触发内容提取 |
| WF-Generation | `/webhook/xhs-generation` | 手动触发 AI 生成 |
| WF-Publish | `/webhook/xhs-publish` | 手动触发内容发布 |

## 工作流详情

### WF-Discovery (内容发现)

**功能**: 从关键词表读取待采集关键词，调用爬虫 API 搜索小红书，将结果写入选题表。

**节点流程**:
```
Schedule/Webhook → Get Lark Token → Query Keywords → Has Keywords?
    ↓ (Yes)                                    ↓ (No)
Extract Keywords → Lock Keyword → Search XHS → Respond No Keywords
    ↓
Search Success? → Transform Results → Save to Topics → Update Keyword Success → Respond Success
    ↓ (No)
Update Keyword Failed
```

**特性**:
- 支持最低点赞数过滤
- 乐观锁防止重复采集
- 状态自动流转

### WF-Extraction (内容提取)

**功能**: 从选题表读取待提取笔记，调用爬虫 API 获取详情，写入素材表。

**节点流程**:
```
Schedule/Webhook → Get Lark Token → Query Topics → Has Topics?
    ↓ (Yes)                                   ↓ (No)
Extract Topics → Lock Topic → Get Note Detail → Respond No Topics
    ↓
Detail Success? → Transform Detail → Save to Source → Update Topic Success → Respond Success
    ↓ (No)
Update Topic Failed
```

**特性**:
- 提取标题、内容、图片、互动数据
- 批量处理（每次最多 10 条）

### WF-Generation (AI 内容生成)

**功能**: 从素材表读取待生成内容，调用 RedInk API 生成二创内容，写入内容表。

**节点流程**:
```
Schedule/Webhook → Get Lark Token → Query Sources → Has Sources?
    ↓ (Yes)                                      ↓ (No)
Get Prompt Template → Prepare Generation → Lock Source → Respond No Sources
    ↓
Generate Outline → Outline Success? → Generate Content → Content Success?
    ↓                    ↓ (No)                              ↓ (No)
Transform Content    Update Source Failed             Update Source Failed
    ↓
Save to Content → Update Source Success → Respond Success
```

**特性**:
- 两阶段生成：大纲 → 完整内容
- 支持自定义提示词模板
- 超时设置 5 分钟

### WF-Publish (内容发布)

**功能**: 从内容表读取待发布内容，调用爬虫 API 发布到小红书，记录到发布表。

**节点流程**:
```
Schedule/Webhook → Check Publish Time → Can Publish?
    ↓ (Yes)                                  ↓ (No)
Get Lark Token → Query Contents → Has Contents? → Respond Bad Time
    ↓ (Yes)                           ↓ (No)
Extract Contents → Lock Content   Respond No Contents
    ↓
Random Delay → Publish to XHS → Publish Success?
    ↓                              ↓ (No)
Transform Publish Result       Update Content Failed
    ↓
Save to Publish → Update Content Success → Log Success → Respond Success
```

**特性**:
- 发布时间窗口控制（避开凌晨时段）
- 随机延迟（5-15秒）模拟人工操作
- 每次最多发布 3 条
- 执行日志记录

## 飞书表结构

### Keywords 表 (关键词库)
| 字段 | 类型 | 说明 |
|------|------|------|
| keyword | Text | 搜索关键词 |
| category | SingleSelect | 分类 |
| status | SingleSelect | 待采集/采集中/已采集/采集失败 |
| min_likes | Number | 最低点赞数 |
| crawl_limit | Number | 采集数量上限 |
| last_crawl_time | DateTime | 上次采集时间 |
| locked_at | DateTime | 锁定时间 |

### Topics 表 (选题库)
| 字段 | 类型 | 说明 |
|------|------|------|
| keyword_id | Text | 关联关键词 |
| note_id | Text | 原笔记 ID |
| title | Text | 标题 |
| author | Text | 作者 |
| likes | Number | 点赞数 |
| cover_url | URL | 封面图 |
| status | SingleSelect | 待提取/提取中/已提取/提取失败 |
| crawled_at | DateTime | 采集时间 |

### Source 表 (素材库)
| 字段 | 类型 | 说明 |
|------|------|------|
| topic_id | Text | 关联选题 |
| note_id | Text | 原笔记 ID |
| original_title | Text | 原标题 |
| original_content | Text | 原内容 |
| original_images | Text | 原图片 (JSON) |
| author_name | Text | 作者名 |
| status | SingleSelect | 待生成/生成中/已生成/生成失败 |
| extracted_at | DateTime | 提取时间 |

### Content 表 (内容库)
| 字段 | 类型 | 说明 |
|------|------|------|
| source_id | Text | 关联素材 |
| note_id | Text | 原笔记 ID |
| ai_title | Text | AI 生成标题 |
| ai_content | Text | AI 生成内容 |
| ai_images | Text | AI 生成图片 (JSON) |
| outline | Text | 大纲 (JSON) |
| status | SingleSelect | 待发布/发布中/已发布/发布失败 |
| generated_at | DateTime | 生成时间 |
| published_at | DateTime | 发布时间 |

### Publish 表 (发布库)
| 字段 | 类型 | 说明 |
|------|------|------|
| content_id | Text | 关联内容 |
| source_id | Text | 关联素材 |
| published_note_id | Text | 发布后笔记 ID |
| published_note_url | URL | 发布后笔记链接 |
| title | Text | 发布标题 |
| publish_status | SingleSelect | 已发布/审核中/被删除 |
| published_at | DateTime | 发布时间 |

### Prompts 表 (提示词库)
| 字段 | 类型 | 说明 |
|------|------|------|
| name | Text | 模板名称 |
| prompt_content | Text | 提示词内容 |
| is_active | Checkbox | 是否启用 |
| created_at | DateTime | 创建时间 |

### Logs 表 (执行日志)
| 字段 | 类型 | 说明 |
|------|------|------|
| workflow | Text | 工作流名称 |
| action | Text | 操作类型 |
| status | SingleSelect | success/failed |
| record_id | Text | 关联记录 ID |
| message | Text | 日志消息 |
| executed_at | DateTime | 执行时间 |

## 注意事项

1. **API 限制**: 小红书爬虫 API 可能有频率限制，工作流已设置合理的执行间隔
2. **发布风控**: 发布功能使用随机延迟和时间窗口控制，减少被封号风险
3. **手动激活**: 导入后需要在 n8n UI 中手动激活每个工作流
4. **错误处理**: 所有工作流都有失败状态处理，可在飞书表中查看失败原因
5. **日志监控**: 发布工作流会记录执行日志到 Logs 表

## 故障排除

### 飞书 Token 获取失败
- 检查 `LARK_APP_ID` 和 `LARK_APP_SECRET` 是否正确
- 确认飞书应用已开通多维表格权限

### 爬虫 API 调用失败
- 检查 `CRAWLER_API_URL` 是否可访问
- 确认爬虫容器已登录（调用 `/api/login/status` 检查）

### RedInk API 超时
- AI 生成可能需要较长时间，超时设置为 5 分钟
- 检查 RedInk 服务是否正常运行

### 发布失败
- 检查爬虫是否已登录 XHS 账号
- 确认 `/api/publish` 端点已实现
- 查看错误消息了解具体原因
