# n8n 工作流审查报告

> 审查日期: 2025-12-16
> 审查目标: 验证5个新导入的工作流配置及执行状态

---

## 一、工作流清单

| 工作流名称 | ID | 状态 | 节点数 |
|-----------|-----|------|--------|
| WF-Discovery | xopUSPFnPvdSWtGc | ✅ Active | 22 |
| WF-CookieManager | 6dANUjTZ7ZQ4SMbg | ⚪ Inactive | 22 |
| WF-Extraction | RFYlklhmvcYbbeEm | ⚪ Inactive | 24 |
| WF-Generation | SKcl7dJKGYeQaB5y | ⚪ Inactive | 25 |
| WF-Publish | WY64JIonli7ZFD7v | ⚪ Inactive | 20 |

---

## 二、关键问题汇总

### 🔴 严重问题 (P0)

#### 2.1 HTTP方法错误 - PATCH不支持

**问题**: 飞书Bitable API 不支持 PATCH 方法，需要使用 PUT 方法更新记录

**影响的节点**:
- WF-Discovery: `Acquire Lock`
- WF-Extraction: `Lock Candidate`, `Mark Candidate Done`, `Update Failed Candidate`
- WF-Generation: `Lock Source`, `Mark Source Done`, `Update Source Failed`
- WF-Publish: `Lock Content`, `Mark Published`, `Mark Failed`
- WF-CookieManager: `Batch Updates`, `Update Cookie`, `Rollback Stuck`

**错误信息**:
```
The resource you are requesting could not be found (404 page not found)
```

**修复方案**:
```javascript
// 错误
method: "PATCH"

// 正确
method: "PUT"
```

#### 2.2 MediaCrawler API 域名不可用

**问题**: 工作流使用 `https://media.primetat.com` 访问 MediaCrawler API，但该域名没有配置 HTTPS (端口443)

**影响的工作流**:
- WF-Discovery: `MediaCrawler Search` 节点
- WF-Extraction: `Get Note Detail` 节点

**当前配置**:
```
https://media.primetat.com/api/search
https://media.primetat.com/api/note/detail
```

**测试结果**:
```bash
# HTTPS访问失败 (端口443未开放)
curl https://media.primetat.com/api/health
→ Connection refused

# HTTP直接IP访问成功
curl http://124.221.251.8:8080/api/health
→ {"status":"healthy","version":"1.0.0"}
```

**修复方案 (选择其一)**:

1. **方案A - 改用IP地址 (推荐)**:
   ```
   http://124.221.251.8:8080/api/search
   http://124.221.251.8:8080/api/note/detail
   ```

2. **方案B - 使用环境变量**:
   ```
   {{ $env.MEDIACRAWLER_API_URL }}/api/search
   {{ $env.MEDIACRAWLER_API_URL }}/api/note/detail
   ```
   环境变量已配置: `MEDIACRAWLER_API_URL=http://124.221.251.8:8080`

3. **方案C - 配置反向代理**:
   在采集服务器配置 Caddy/Nginx + SSL 证书

---

### 🟡 配置问题 (P1)

#### 2.3 硬编码飞书表Token

**问题**: 工作流使用硬编码的 `FEISHU_APP_TOKEN` 而不是环境变量

**当前配置**:
```
https://open.feishu.cn/open-apis/bitable/v1/apps/Gq93bAlZ7aSSclsLKdTcYCO2nwh/tables/...
```

**n8n环境变量**:
```
FEISHU_APP_TOKEN=S8BJbH6TlatgqEsQmoFcb42GnPf  ← 不同的值!
```

**说明**:
- 硬编码值: `Gq93bAlZ7aSSclsLKdTcYCO2nwh`
- 环境变量值: `S8BJbH6TlatgqEsQmoFcb42GnPf`
- 两者不一致，但硬编码的表是可访问的

**建议**:
- 如果使用当前飞书表 (`Gq93...`)，不需要修改
- 如果要切换到环境变量配置的表，需要更新所有节点URL

---

## 三、执行历史分析

### WF-Discovery 执行记录

| 执行ID | 时间 | 状态 | 失败节点 |
|--------|------|------|---------|
| 41 | 2025-12-16 17:00:46 | ❌ Error | Acquire Lock |
| 40 | 2025-12-16 15:00:59 | ❌ Error | Acquire Lock |
| 39 | 2025-12-16 13:35:29 | ❌ Error | Acquire Lock |
| 38 | 2025-12-16 13:00:59 | ❌ Error | Acquire Lock |
| 37 | 2025-12-16 12:49:22 | ❌ Error | Acquire Lock |

**根本原因**: 飞书API不支持PATCH方法

---

## 四、服务连通性测试

| 服务 | 地址 | 状态 |
|------|------|------|
| n8n | http://localhost:5678 | ✅ 正常 |
| 飞书 API | https://open.feishu.cn | ✅ 正常 |
| MediaCrawler (IP) | http://124.221.251.8:8080 | ✅ 正常 |
| MediaCrawler (域名) | https://media.primetat.com | ❌ 端口443未开放 |
| Playwright API | http://124.221.251.8:3000 | ❌ 服务未运行 |

---

## 五、飞书表结构验证

### 当前配置的飞书表 (APP_TOKEN: Gq93bAlZ7aSSclsLKdTcYCO2nwh)

| 表名 | Table ID | 状态 |
|------|----------|------|
| tbl_execution_lock | tblKwmP3Q9lNTJDf | ✅ 存在 |
| tbl_candidate | tbleFs8pwdee2DWX | ✅ 存在 |
| tbl_source | tblsqXtjfMxzhUu2 | ✅ 存在 |
| tbl_content | tblEMrCOGQuC36MU | ✅ 存在 |
| tbl_cookie | tblYa2d2a5lypzqz | ✅ 存在 |
| tbl_config | tblH7tedq8ITPfiu | ✅ 存在 |
| tbl_logs | tbl4asiKhYyzcDPX | ✅ 存在 |

### tbl_execution_lock 字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| workflow_name | Text | 工作流名称 (PK) |
| execution_id | Text | 执行ID |
| locked_at | DateTime | 锁定时间 |
| expires_at | DateTime | 过期时间 |

---

## 六、修复优先级

### P0 - 立即修复

1. **修改HTTP方法**
   - 将所有飞书表更新节点的 `PATCH` 改为 `PUT`
   - 影响工作流: 全部5个

2. **修改MediaCrawler API地址**
   - `https://media.primetat.com` → `http://124.221.251.8:8080`
   - 或使用 `{{ $env.MEDIACRAWLER_API_URL }}`
   - 影响工作流: WF-Discovery, WF-Extraction

### P1 - 尽快修复

3. **启动Playwright服务** (如果需要)
   - 检查采集服务器是否需要运行Playwright
   - 端口: 3000

### P2 - 可选优化

4. **统一使用环境变量**
   - 将硬编码的飞书表Token改为 `$env.FEISHU_APP_TOKEN`
   - 需要确认使用哪个飞书表

---

## 七、工作流节点详情

### WF-Discovery (22节点)

```
Schedule Trigger → 获取飞书Token → Generate RequestID → Check Execution Lock
    ↓
Check Lock Status → IF Should Run → Acquire Lock → Get Search Config
    ↓
Parse Config → Split Keywords → MediaCrawler Search → Process Results
    ↓
IF Candidate → Check Duplicate → Decide Action → IF Insert
    ↓
Insert Candidate → Rate Limit Wait → Release Lock → Log Completion
```

### WF-Extraction (24节点)

```
Schedule Trigger → Generate RequestID → Check Execution Lock → Check Lock Status
    ↓
IF Should Run → Acquire Lock → Get Pending Candidates → Filter Candidates
    ↓
IF Has Candidates → Split Candidates → Lock Candidate → Get Note Detail
    ↓
Process Detail → IF Success → Check Source Exists → Decide Source Action
    ↓
IF Insert Source → Insert Source → Mark Candidate Done → Rate Limit Wait
    ↓
Release Lock → Log Completion
```

### WF-Generation (25节点)

```
Schedule Trigger → Generate RequestID → Check Execution Lock → Check Lock Status
    ↓
IF Should Run → Acquire Lock → Get Pending Sources → Filter Sources
    ↓
IF Has Sources → Split Sources → Lock Source → Build Prompt
    ↓
Claude Generate → Parse Response → IF Success → Quality Check
    ↓
IF Quality Pass → Insert Content → Mark Source Done → Rate Limit Wait
    ↓
Release Lock → Log Completion
```

### WF-Publish (20节点)

```
Schedule Trigger → Generate RequestID → Check Execution Lock → Check Lock Status
    ↓
IF Should Run → Acquire Lock → Get Approved Content → Filter Content
    ↓
IF Has Content → Split Content → Lock Content → Simulate Publish
    ↓
IF Publish Success → Mark Published → Calculate Wait → Anti-Detect Wait
    ↓
Release Lock → Log Completion
```

### WF-CookieManager (22节点)

```
Schedule Trigger → Generate RequestID → Check Execution Lock → Check Lock Status
    ↓
IF Should Run → Acquire Lock → Get All Cookies → Analyze Cookies
    ↓
IF Has Updates → Split Updates → Batch Updates → Update Cookie
    ↓
Rate Limit Wait → Check Stuck Candidates → Filter Stuck → IF Has Stuck
    ↓
Rollback Stuck → IF Need Alert → Send Alert → Release Lock
    ↓
Log Completion
```

---

## 八、修复操作指南

### 步骤1: 修复HTTP方法

在n8n编辑器中，对每个工作流执行以下操作：

1. 打开工作流编辑器
2. 找到所有使用 `method: "PATCH"` 的节点
3. 将方法改为 `method: "PUT"`
4. 保存工作流

### 步骤2: 修复MediaCrawler API地址

在 WF-Discovery 和 WF-Extraction 中：

1. 找到 `MediaCrawler Search` 或 `Get Note Detail` 节点
2. 将 URL 从 `https://media.primetat.com/api/...` 改为 `{{ $env.MEDIACRAWLER_API_URL }}/api/...`
3. 保存工作流

### 步骤3: 验证修复

```bash
# 从n8n服务器测试MediaCrawler API
curl http://124.221.251.8:8080/api/health

# 测试飞书表更新
curl -X PUT "https://open.feishu.cn/open-apis/bitable/v1/apps/Gq93bAlZ7aSSclsLKdTcYCO2nwh/tables/tblKwmP3Q9lNTJDf/records/recv5uMCs9GhVz" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"fields":{"execution_id":"test"}}'
```

---

> 审查完成时间: 2025-12-16 18:45 CST
