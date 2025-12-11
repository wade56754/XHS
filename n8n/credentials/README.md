# N8N 凭证配置说明

## 凭证清单

| 凭证名称 | 类型 | 用途 |
|----------|------|------|
| claude_api_prod | HTTP Header Auth | Claude API 调用 |
| gemini_api_prod | HTTP Header Auth | Gemini 图片生成 |
| lark_api_prod | OAuth2 | 飞书多维表格读写 |
| telegram_bot | Telegram API | 消息通知 |

## 配置步骤

### 1. Claude API
- N8N UI → Settings → Credentials → Add Credential
- 类型: Header Auth
- Name: `x-api-key`
- Value: `sk-ant-xxx`

### 2. Gemini API
- 类型: Header Auth
- Name: `x-goog-api-key`
- Value: `xxx`

### 3. 飞书 API
- 类型: OAuth2 或自定义 HTTP
- App ID: `cli_xxx`
- App Secret: `xxx`

### 4. Telegram Bot
- 类型: Telegram API
- Bot Token: `xxx:xxx`
- Chat ID: 在工作流中配置

## 环境区分

| 环境 | 凭证后缀 |
|------|----------|
| 开发 | `_dev` |
| 测试 | `_stage` |
| 生产 | `_prod` |
