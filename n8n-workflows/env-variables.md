# n8n 环境变量配置

在 n8n 中配置以下环境变量，路径: Settings > Variables

## 飞书配置

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `LARK_APP_ID` | `cli_a98f34e454ba100c` | 飞书应用 ID |
| `LARK_APP_SECRET` | `C0mABqwJAOAfhGudb8qfCbwool64Q0Tn` | 飞书应用密钥 |
| `LARK_APP_TOKEN` | `Gq93bAlZ7aSSclsLKdTcYCO2nwh` | 飞书多维表格 Token |

## 飞书表格 ID

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `KEYWORDS_TABLE_ID` | `tblXXXXXX` | Keywords 表 (需要创建) |
| `TOPICS_TABLE_ID` | `tblE2SypBdIhJVrR` | Topics 选题库表 |
| `SOURCE_TABLE_ID` | `tblPCp5gqgVFnhLc` | Source 素材库表 |
| `CONTENT_TABLE_ID` | `tblMYjwzOkYpW4AX` | Content 内容库表 |
| `PUBLISH_TABLE_ID` | `tblp3iSuo0dasTtg` | Publish 发布库表 |
| `LOGS_TABLE_ID` | `tbl8xTUEtAQjxP4k` | 执行日志表 |
| `COOKIE_TABLE_ID` | `tblYa2d2a5lypzqz` | Cookie 管理表 |

## 子工作流 ID

创建子工作流后，记录其 ID 并配置:

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `WF_DISCOVERY_ID` | `待创建后填写` | WF-Discovery 工作流 ID |
| `WF_EXTRACTION_ID` | `待创建后填写` | WF-Extraction 工作流 ID |
| `WF_GENERATION_ID` | `待创建后填写` | WF-Generation 工作流 ID |
| `WF_PUBLISH_ID` | `待创建后填写` | WF-Publish 工作流 ID |

## 爬虫 API 配置

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `CRAWLER_API_URL` | `http://124.221.251.8:8080` | MediaCrawler API 地址 |
| `CRAWLER_API_KEY` | `dev-key` | API 密钥 |

## AI 服务配置

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `REDINK_API_URL` | `http://xxx:3000` | RedInk AI 服务地址 |
| `REDINK_API_KEY` | `xxx` | RedInk API 密钥 |

---

## 配置步骤

1. 打开 n8n 界面: https://n8n.primetat.com/
2. 进入 Settings > Variables
3. 逐个添加上述环境变量
4. 保存后工作流即可使用 `{{ $env.VAR_NAME }}` 访问变量

## 注意事项

- **敏感信息**: `LARK_APP_SECRET` 等敏感信息不要提交到代码仓库
- **表格 ID**: 从飞书多维表格 URL 中获取，格式为 `tblXXXXXXXX`
- **工作流 ID**: 创建工作流后从 URL 或工作流设置中获取
