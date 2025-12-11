# 小红书自动发布工具

技术需求文档 v2.0

*工程化 · 可实施 · N8N就绪*

项目代号: XHS\_AutoPublisher\_v2

创建日期: 2024-12-11

版本: v2.0 (工程化重构版)

## **文档修订历史**

| 版本 | 日期 | 作者 | 变更说明 |
| ----- | ----- | ----- | ----- |
| **v1.0** | 2024-12-11 | Qi | 初始业务需求版本 |
| **v2.0** | 2024-12-11 | Qi | 工程化重构：N8N视角、数据模型、状态机、可观察性 |

## **v2.0 核心升级**

本版本从「业务需求文档」升级为「工程实施文档」，核心变化：

* **N8N工作流视角：**触发器/输入/输出/节点/错误处理  
* **数据模型设计：**表结构+飞书字段映射  
* **状态机设计：**内容/账号状态+转换规则  
* **可观察性：**日志规范+故障排查SOP  
* **N8N设计规范：**命名/变量/AI网关  
* **模块优先级：**P0/P1/P2分级  
* **验收标准：**量化指标+测试用例

# **目录**

* 第一部分：业务与架构 (1-4章)  
* 第二部分：功能模块设计 (5-9章)  
* 第三部分：数据与状态设计 (10-12章)  
* 第四部分：可靠性与运维 (13-15章)  
* 第五部分：实施与验收 (16-18章)  
* 附录 (A-D)

# **第一部分：业务与架构**

# **1\. 项目概述**

## **1.1 项目定位**

基于N8N的小红书内容自动化系统，实现选题→生成→审核→图片→发布→复盘全流程。

**核心能力：**

* 智能选题：关键词+热点+AI评分  
* 内容生成：Claude多风格+5步审核+100分制  
* 图片生成：Gemini API 3:4竖图  
* 智能发布：AI定时+MCP+半自动  
* 数据闭环：飞书存储+互动回流

## **1.2 核心目标**

| 维度 | 目标 | 指标 | 验证 |
| ----- | ----- | ----- | ----- |
| **效率** | 内容提效 | 2-3h→15min | 时间对比 |
| **质量** | 质量稳定 | 通过率≥85% | 30天数据 |
| **可靠性** | 系统稳定 | 成功率≥90% | N8N日志 |
| **扩展性** | 多账号 | 1→3-5账号 | 账号管理表 |

# **2\. 业务背景与目标**

## **2.1 业务痛点**

| 痛点 | 现状 | 目标 | 方案 |
| ----- | ----- | ----- | ----- |
| **选题难** | 1-2h思考 | AI生成3-5个 | 智能选题+热点 |
| **耗时长** | 2-3h/篇 | 15min内 | 全流程自动化 |
| **质量波动** | 人工不稳定 | ≥85%通过 | 5步AI审核 |
| **发布繁琐** | 手动多步骤 | 人工确认+MCP | 半自动发布 |
| **数据滞后** | 无系统分析 | 自动记录+回流 | 飞书+AI闭环 |

## **2.2 成功指标**

**短期（1-2月）：**

| 指标 | 目标 | 方式 |
| ----- | ----- | ----- |
| **稳定性** | ≥85% | N8N日志 |
| **效率** | ≤15min | 时间戳 |
| **质量** | ≥85% | 审核日志 |
| **发布** | ≥90% | 发布记录 |

中期（3-6月）：支持3-5账号、互动率≥90%、数据闭环

长期（6-12月）：策略优化、多平台扩展、预测准确率≥80%

# **3\. 技术架构与选型**

## **3.1 核心技术栈**

| 组件 | 选型 | 用途 |
| ----- | ----- | ----- |
| **编排器** | N8N | 工作流调度 |
| **LLM** | Claude 4.5 | 选题/创作/审核 |
| **图片** | Gemini API | 3:4竖图生成 |
| **存储** | 飞书多维表格 | 数据管理 |
| **发布** | 小红书MCP | 半自动发布 |
| **通知** | Telegram | 状态推送 |
| **热点** | Web Scraper | 抖音/微博 |

## **3.2 部署方案**

| 项 | 方案 | 说明 |
| ----- | ----- | ----- |
| **服务器** | 阿里云/腾讯云 | 2核4G 50-100GB |
| **系统** | Ubuntu 22.04 | LTS |
| **容器** | Docker | N8N部署 |
| **代理** | Nginx | HTTPS |
| **证书** | Let's Encrypt | 自动续期 |

月度成本：服务器60-100元 \+ API约$70-250 ≈ 300-600元

# **4\. N8N工作流设计规范**

*统一规范确保可读、可维护、可扩展。*

## **4.1 命名规范**

| 对象 | 规则 | 示例 |
| ----- | ----- | ----- |
| **工作流** | \[功能\]\_\[版本\] | content\_generator\_v1 |
| **节点** | \[动词\]\_\[对象\] | fetch\_hot\_topics |
| **变量** | camelCase | selectedTopicId |
| **凭证** | \[服务\]\_\[环境\] | claude\_api\_prod |
| **子流程** | sub\_\[功能\] | sub\_ai\_score |

## **4.2 变量管理**

分层管理：

* 全局配置 → Environment Variables（API endpoints）  
* 业务配置 → 飞书config表（阈值、风格）  
* 运行参数 → Workflow Variables（batch\_size）  
* 节点输出 → $json / $("节点名").item.json

## **4.3 错误处理**

| 层级 | 方式 | 场景 |
| ----- | ----- | ----- |
| **节点级** | Continue On Fail | API调用 |
| **工作流级** | Error Trigger | 全局异常 |
| **业务级** | 条件分支+重试 | AI失败/发布失败 |

## **4.4 子工作流策略**

拆分条件：

* ✓ 节点数\>15  
* ✓ 逻辑复用  
* ✓ 可独立测试  
* ✓ 并发执行

建议子流程：

| 子流程 | 职责 | 输入 | 输出 |
| ----- | ----- | ----- | ----- |
| **sub\_ai\_score** | AI评分 | 标题/内容 | score对象 |
| **sub\_hot\_topics** | 热点抓取 | 关键词 | 热点数组 |
| **sub\_image\_gen** | 图片生成 | prompt | 图片URL |
| **sub\_publish** | 内容发布 | 内容对象 | 发布结果 |
| **sub\_notify** | 通知推送 | 消息 | 发送状态 |

## **4.5 AI网关设计**

所有AI调用统一通过Gateway节点：

* 统一错误处理和重试  
* 统一限频控制（RPM）  
* 统一Cost tracking  
* 统一日志记录  
* 便于切换模型

// AI Gateway伪代码  
const request \= {  
  model: 'claude-sonnet-4-20250514',  
  task\_type: $json.task\_type, // generate/score/review  
  prompt: $json.prompt,  
  max\_tokens: $json.max\_tokens || 4000  
};

// 限频检查  
if (timeSinceLastCall \< 1000\) await sleep(1000);

// 调用API \+ 记录Cost \+ 日志  
const response \= await claudeAPI.call(request);  
await logAPIUsage(response.usage);

return { json: response };

# **第二部分：功能模块设计（N8N视角）**

# **5\. 智能选题模块（含热点抓取）**

## **5.1 功能描述**

基于关键词+热点趋势生成3-5个候选选题，100分制评分排序。

## **5.2 评分体系（100分）**

| 维度 | 权重 | 评估要素 |
| ----- | ----- | ----- |
| **A.点击力** | 30% | 封面10分+标题20分 |
| **B.内容力** | 25% | 结构8+密度9+逻辑8 |
| **C.价值感** | 20% | 干货7+情绪7+解决6 |
| **D.互动设计** | 10% | 评论4+收藏3+转化3 |
| **E.平台适配** | 15% | 标签5+SEO5+排版3+合规2 |

通过标准：90-100优秀直发、80-89良好可发、70-79优化后发、\<70重新生成

## **5.3 N8N实现视角 ⭐**

**触发器：**

Schedule Trigger（每天9:00）或 Manual Trigger

**输入规格：**

| 参数 | 类型 | 必填 | 示例 |
| ----- | ----- | ----- | ----- |
| **keyword** | string | 是 | AI自动化 |
| **target\_audience** | string | 否 | 开发者 |
| **content\_style** | string | 否 | 干货教程 |

**输出规格：**

| 字段 | 类型 | 说明 |
| ----- | ----- | ----- |
| **selected\_topic\_id** | string | 选中选题UUID |
| **title** | string | 标题15-30字 |
| **core\_points** | array | 3个核心卖点 |
| **score** | number | AI评分0-100 |

**关键节点流程：**

1. 1\. Fetch\_Config → 从飞书读取配置  
2. 2\. AI\_Gateway(task=generate\_topic) → 生成3-5选题  
3. 3\. Fetch\_Hot\_Trends → 抓取抖音/微博热搜  
4. 4\. Match\_Trends → 语义匹配热点（相关度≥70%）  
5. 5\. AI\_Gateway(task=score) → 对每个选题评分  
6. 6\. Select\_Best → 选最高分（score≥80）  
7. 7\. Save\_To\_Lark → 存储到飞书content\_records表  
8. 8\. Send\_Notification → 推送Telegram

**错误处理：**

* Claude限频 → 等待60s重试，最多3次  
* 热点抓取失败 → 跳过热点匹配  
* 评分失败 → 使用默认规则fallback  
* 存储失败 → 本地缓存+定时重试

## **5.4 热点抓取策略**

来源：抖音热搜（每小时）、微博热搜（实时）

匹配：直接匹配\>语义匹配\>角度切入

筛选：相关度≥70% \+ 时效性评估

# **6\. 内容创作与AI审核模块**

## **6.1 创作规格**

字数：800-1200字 | 风格：口语化+emoji | 结构：开头+主体+结尾

## **6.2 5步AI审核流程 ⭐**

| 步骤 | 检查项 | 通过标准 |
| ----- | ----- | ----- |
| **Step 0** | 账号定位检查 | 匹配度≥80% |
| **Step 1** | 三秒测试 | 点击力≥24分 |
| **Step 2** | 首屏测试 | 前两屏传达价值 |
| **Step 3** | 全文质量 | 内容力≥20+价值感≥16 |
| **Step 4** | 互动设计 | 互动≥8分 |
| **Step 5** | 平台合规 | 适配≥12+敏感词通过 |

结果：全通过→发布队列 | 部分未过→优化建议 | 严重不合格→重新生成

## **6.3 N8N实现视角 ⭐**

触发器：前序节点（选题完成）触发

**关键节点：**

* AI\_Gateway(task=create\_content) → 生成多风格版本  
* AI\_Gateway(task=audit\_step0-5) → 5步审核  
* Calculate\_Final\_Score → 汇总评分  
* Branch\_By\_Score → 分支判断（通过/优化/拒绝）  
* Update\_Status → 更新状态为AI\_REVIEWED  
* Queue\_For\_Human\_Review → 推送审核队列

# **7\. 图片生成模块**

## **7.1 优先级：P0（必备）**

技术方案：Claude生成prompt → Gemini API生成 → 3:4竖图

## **7.2 N8N实现视角 ⭐**

* AI\_Gateway(task=gen\_image\_prompt) → 根据内容生成描述  
* Gemini\_API\_Call → 生成图片  
* Save\_Image → 存储到云端/本地  
* Update\_Record → 更新image\_url字段

错误处理：Gemini失败→使用模板图+记录失败日志

# **8\. 发布与智能定时模块**

## **8.1 发布方式：半自动**

流程：AI生成→AI审核→人工确认→MCP发布

## **8.2 智能定时策略**

默认时间段：

工作日：7-9点 | 12-13点 | 19-22点

周末：10-11点 | 15-17点 | 20-22点

AI优化逻辑：

9. 初期：使用默认时段  
10. 30天后：分析高表现时段（Top 20%）  
11. 每周：动态调整建议时间  
12. 持续：优化发布策略

## **8.3 N8N实现视角 ⭐**

触发器：Schedule Trigger（AI决定时间）或 Manual Trigger

* Check\_Account\_Status → 检查账号状态（ACTIVE/COOLDOWN）  
* Rate\_Limit\_Check → 检查发布频率  
* Human\_Approval\_Check → 确认人工已审核  
* XHS\_MCP\_Publish → 调用小红书MCP  
* Update\_Status(PUBLISHING→PUBLISHED) → 更新状态  
* Record\_Publish\_Time → 记录发布时间  
* Send\_Success\_Notification → 通知发布成功

失败处理：重试3次 → 标记FAILED → 人工介入

# **9\. 数据记录与分析模块**

## **9.1 数据类型**

* 内容数据：标题/正文/标签/图片  
* 流程数据：生成时间/审核状态/发布时间  
* 互动数据：阅读/点赞/收藏/评论（定期抓取）  
* 评分数据：AI评分/真实评分/预测误差

## **9.2 存储方案：飞书多维表格**

优势：本土服务、API完善、多维视图、团队协作

## **9.3 N8N实现视角 ⭐**

* Collect\_Data → 汇总所有字段  
* Lark\_API\_Insert → 插入content\_records表  
* Generate\_Execution\_Log → 记录到execution\_logs表  
* Schedule\_Data\_Fetch → 定时抓取互动数据（每天）  
* Calculate\_Real\_Score → 计算真实评分  
* Update\_Prediction\_Error → 更新预测误差

# **第三部分：数据与状态设计**

# **10\. 数据模型与存储设计**

## **10.1 核心表结构**

**表1：content\_records（内容记录表）**

| 字段名 | 类型 | 约束 | 说明 |
| ----- | ----- | ----- | ----- |
| **id** | string(32) | PRIMARY KEY | UUID |
| **created\_at** | datetime | NOT NULL, INDEX | 创建时间 |
| **content\_direction** | string(50) | NOT NULL, INDEX | 内容方向 |
| **topic\_source** | string(20) | NOT NULL | ai/hot\_trend/manual |
| **title** | string(100) | NOT NULL | 标题 |
| **content\_body** | text | NOT NULL | 正文 |
| **tags** | json | NOT NULL | 标签数组 |
| **image\_url** | string(500) | NULL | 图片URL |
| **ai\_score** | decimal(5,2) | NOT NULL | AI评分0-100 |
| **real\_score** | decimal(5,2) | NULL | 真实评分 |
| **prediction\_error** | decimal(5,2) | NULL | 预测误差 |
| **status** | string(20) | NOT NULL, INDEX | 见状态机 |
| **published\_at** | datetime | NULL, INDEX | 发布时间 |
| **account\_id** | string(32) | FK, NOT NULL | 关联账号 |
| **workflow\_run\_id** | string(50) | UNIQUE, NOT NULL | N8N执行ID |
| **views** | int | NULL | 阅读量 |
| **likes** | int | NULL | 点赞数 |
| **collects** | int | NULL | 收藏数 |
| **comments** | int | NULL | 评论数 |

**索引：**

PRIMARY KEY: id | INDEX: created\_at DESC, status+created\_at, account\_id+published\_at | UNIQUE: workflow\_run\_id

**保留策略：**

草稿\>30天未发布→归档 | 已发布→永久保留 | 失败记录→保留90天

**表2：interaction\_data（互动数据表）**

| 字段 | 类型 | 说明 |
| ----- | ----- | ----- |
| **content\_id** | string(32) FK | 关联内容 |
| **fetched\_at** | datetime | 抓取时间 |
| **views/likes/collects/comments** | int | 互动指标 |

**表3：accounts（账号管理表）**

| 字段 | 类型 | 说明 |
| ----- | ----- | ----- |
| **id** | string(32) PK | 账号ID |
| **name** | string(50) | 账号名称 |
| **status** | string(20) | ACTIVE/COOLDOWN/SUSPENDED/BANNED |
| **last\_publish\_at** | datetime | 最后发布时间 |
| **publish\_count\_today** | int | 今日发布数 |
| **cooldown\_until** | datetime | 冷却截止时间 |

**表4：execution\_logs（执行日志表）**

| 字段 | 类型 | 说明 |
| ----- | ----- | ----- |
| **timestamp** | datetime PK | 时间戳 |
| **level** | string(10) | DEBUG/INFO/WARN/ERROR/FATAL |
| **workflow\_id** | string(50) | 工作流ID |
| **workflow\_run\_id** | string(50) | 执行ID |
| **node\_name** | string(50) | 节点名 |
| **event\_type** | string(50) | 事件类型 |
| **message** | text | 日志消息 |
| **context** | json | 上下文数据 |
| **error** | json | 错误信息 |

# **11\. 状态机与流转设计**

## **11.1 内容流转状态机**

**状态定义（7个状态）：**

| 状态码 | 名称 | 描述 | 可转换到 |
| ----- | ----- | ----- | ----- |
| **DRAFT** | 草稿 | 内容已生成待审 | AI\_REVIEWED, REJECTED |
| **AI\_REVIEWED** | AI通过 | AI评分≥70 | PENDING\_APPROVAL, ARCHIVED |
| **PENDING\_APPROVAL** | 待发布 | 人工确认通过 | PUBLISHING |
| **PUBLISHING** | 发布中 | 调用MCP发布 | PUBLISHED, FAILED |
| **PUBLISHED** | 已发布 | 发布成功 | \- |
| **REJECTED** | AI拒绝 | AI评分\<70 | \- |
| **ARCHIVED** | 已归档 | 人工拒绝或过期 | \- |
| **FAILED** | 发布失败 | 重试3次失败 | PENDING\_APPROVAL |

**状态转换规则：**

| 当前状态 | 触发事件 | 目标状态 | 前置条件 | 后置动作 |
| ----- | ----- | ----- | ----- | ----- |
| **DRAFT** | ai\_review\_pass | AI\_REVIEWED | score≥70 | 推送通知 |
| **DRAFT** | ai\_review\_fail | REJECTED | score\<70 | 记录原因 |
| **AI\_REVIEWED** | human\_approve | PENDING\_APPROVAL | \- | 加入队列 |
| **PENDING\_APPROVAL** | publish\_trigger | PUBLISHING | account=ACTIVE | 调用MCP |
| **PUBLISHING** | publish\_success | PUBLISHED | \- | 记录时间 |
| **PUBLISHING** | publish\_fail | FAILED | retry≥3 | 告警通知 |

## **11.2 账号状态机**

| 状态 | 说明 | 发布行为 | 转换条件 |
| ----- | ----- | ----- | ----- |
| **ACTIVE** | 正常 | 可发布 | 发布后→检查频率 |
| **COOLDOWN** | 冷却 | 暂停发布 | 等待cooldown\_until过期 |
| **SUSPENDED** | 暂停 | 禁止发布 | 人工恢复 |
| **BANNED** | 封禁 | 禁止发布 | 申诉后恢复 |

## **11.3 限频策略**

发布限频规则：

* 单账号：最多3篇/天  
* 最小间隔：4小时  
* 触发冷却：连续发布3篇 → COOLDOWN 8小时  
* 异常检测：1小时内2篇 → SUSPENDED

// 发布前检查伪代码  
function canPublish(accountId) {  
  account \= getAccount(accountId);  
    
  if (account.status \!== 'ACTIVE') return false;  
  if (account.publish\_count\_today \>= 3\) return false;  
    
  lastPublish \= account.last\_publish\_at;  
  if (now \- lastPublish \< 4 \* 3600 \* 1000\) return false;  
    
  return true;  
}

# **12\. AI评分闭环设计**

## **12.1 闭环数据流**

完整流程：

1\. AI生成内容 → 预测ai\_score（0-100）

2\. 发布到小红书

3\. 等待24-48小时

4\. 抓取真实互动数据（views/likes/collects/comments）

5\. 计算real\_score（相同100分制）

6\. 计算prediction\_error \= |ai\_score \- real\_score|

7\. 每周分析：高偏差内容（error\>15）人工复盘

8\. 每月更新：调整评分权重，优化prompt

## **12.2 真实评分公式**

real\_score \=   
  views\_weight × (views / views\_benchmark) × 10 \+  
  likes\_weight × (likes / views) × 100 × 30 \+  
  collects\_weight × (collects / views) × 100 × 30 \+  
  comments\_weight × (comments / views) × 100 × 20

权重示例：  
views\_weight \= 1.0 (基准：1000阅读)  
likes\_weight \= 3.0 (点赞率\>5%优秀)  
collects\_weight \= 5.0 (收藏率\>3%优秀)  
comments\_weight \= 2.0 (评论率\>1%优秀)

## **12.3 优化策略**

* 每周：生成偏差分析报告（top10高偏差 \+ top10低偏差）  
* 人工复盘：分析高偏差原因（AI高估 vs AI低估）  
* 提取pattern：成功内容共性（关键词/结构/风格）  
* 更新prompt：融入成功pattern，调整评分规则  
* 持续迭代：目标prediction\_error\<10

# **第四部分：可靠性与运维**

# **13\. 可观察性与日志设计**

## **13.1 日志规范**

**日志级别（6级）：**

| 级别 | 用途 | 示例 |
| ----- | ----- | ----- |
| **DEBUG** | 调试信息 | 变量值、中间结果 |
| **INFO** | 正常流程 | API调用成功、状态更新 |
| **WARN** | 警告 | 重试触发、性能慢 |
| **ERROR** | 错误 | API失败、业务异常 |
| **FATAL** | 致命 | 工作流崩溃、数据丢失 |
| **AUDIT** | 审计 | 人工操作、敏感变更 |

## **13.2 标准日志格式**

{  
  "timestamp": "2024-12-11T14:30:00Z",  
  "level": "INFO",  
  "workflow\_id": "content\_generator\_v1",  
  "workflow\_run\_id": "run\_abc123",  
  "node\_name": "Generate\_Content",  
  "event\_type": "ai\_api\_call",  
  "message": "Claude API调用成功",  
  "context": {  
    "task\_type": "create\_content",  
    "input\_tokens": 1500,  
    "output\_tokens": 2000,  
    "cost\_usd": 0.015,  
    "duration\_ms": 3500  
  },  
  "error": null,  
  "trace\_id": "trace\_xyz789"  
}

## **13.3 关键事件定义**

| 事件类型 | 触发时机 | 必含字段 |
| ----- | ----- | ----- |
| **ai\_api\_call** | AI调用 | task\_type, tokens, cost |
| **content\_created** | 内容生成 | content\_id, score |
| **content\_published** | 发布成功 | content\_id, url |
| **publish\_failed** | 发布失败 | content\_id, error\_code, retry\_count |
| **human\_reviewed** | 人工审核 | content\_id, decision, reviewer |
| **data\_fetched** | 数据抓取 | content\_id, views, likes |

# **14\. 故障恢复与重试策略**

## **14.1 三层重试机制**

| 层级 | 触发条件 | 策略 | 最大次数 |
| ----- | ----- | ----- | ----- |
| **即时重试** | API限频/网络波动 | 等待1s后重试 | 3次 |
| **延迟重试** | API长时间超时 | 等待5min后重试 | 3次 |
| **人工介入** | 业务异常/数据错误 | 告警通知+人工处理 | \- |

## **14.2 幂等性设计**

关键操作保证幂等：

* 内容创建：使用workflow\_run\_id作为唯一标识  
* 数据存储：INSERT前检查是否存在  
* 发布操作：MCP返回已发布视为成功  
* 状态更新：检查当前状态再更新

## **14.3 故障排查SOP**

**问题：内容生成失败**

Step 1: 定位执行记录

打开N8N UI → Executions → 筛选失败（红色）→ 记录workflow\_run\_id

Step 2: 查看日志

在飞书execution\_logs表搜索workflow\_run\_id → 筛选ERROR级别 → 查看error字段

Step 3: 根因分析

| 错误码 | 原因 | 解决 | 预防 |
| ----- | ----- | ----- | ----- |
| **RATE\_LIMIT** | Claude限频 | 等待1min重试 | 增加限频检查节点 |
| **INVALID\_PROMPT** | Prompt错误 | 检查prompt模板 | 增加validation |
| **TIMEOUT** | API超时 | 增加timeout/分段处理 | 优化prompt长度 |
| **AUTH\_FAILED** | 认证失败 | 检查API key | 更新凭证 |

Step 4: 恢复运行

* 临时错误：点击N8N「Retry Execution」  
* 数据错误：更新飞书表格后重新触发  
* 代码bug：修复workflow后重新执行

# **15\. 非功能性需求**

## **15.1 性能要求**

| 指标 | 目标 | 说明 |
| ----- | ----- | ----- |
| **内容生成** | ≤5min | 从选题到审核完成 |
| **工作流响应** | ≤10s | 节点启动时间 |
| **并发支持** | ≥3任务 | 同时运行工作流 |
| **API超时** | 30s | Claude/Gemini调用 |

## **15.2 可靠性要求**

* 系统可用性：≥95%  
* 内容生成成功率：≥85%  
* 所有节点：错误捕获+重试机制  
* 日志记录：完整执行日志

## **15.3 安全性要求**

* API密钥：N8N凭证管理  
* 账号信息：加密存储  
* 敏感词过滤：避免违规  
* 访问控制：workflow权限管理

## **15.4 扩展性要求**

* 多账号：1→3-5账号（预留扩展）  
* 多平台：预留接口（抖音/知乎）  
* 子工作流：模块化设计  
* AI模型：可切换（Claude/GPT/国内）

# **第五部分：实施与验收**

# **16\. 分阶段实施计划**

## **16.1 MVP阶段（第1-2周）**

**目标：核心流程验证，成功率≥80%**

实施内容：

* 搭建N8N环境（云服务器Docker部署）  
* 配置Claude API \+ 飞书API  
* 实现选题生成+内容创作+AI审核  
* 实现数据记录（飞书表格）  
* 配置Telegram通知  
* 人工审核后手动发布

**验收标准：**

| 指标 | 标准 | 验证方式 |
| ----- | ----- | ----- |
| **工作流运行** | 成功生成10篇内容 | N8N执行日志 |
| **AI审核** | 通过率≥80% | 审核日志统计 |
| **数据存储** | 100%记录到飞书 | 飞书表格检查 |
| **通知功能** | 关键节点及时通知 | Telegram消息 |

## **16.2 优化阶段（第3-4周）**

**目标：质量优化，成功率≥85%**

实施内容：

* 根据测试反馈优化prompt  
* 完善错误处理和重试机制  
* 增加热点抓取模块  
* 优化评分规则  
* 建立初步数据分析

**验收标准：**

* • 持续产出30天数据：每天至少1篇  
* • AI审核通过率≥85%：30天统计  
* • 热点匹配成功率≥60%：有热点的选题  
* • 错误自动恢复率≥80%：可重试错误

## **16.3 扩展阶段（第5-8周）**

**目标：功能完善，支持多账号**

实施内容：

* 实现图片生成模块（Gemini API）  
* 接入小红书MCP自动发布  
* 实现账号状态机+限频策略  
* 实现互动数据自动抓取  
* 建立AI评分闭环  
* 支持3-5账号管理

**验收标准：**

* 图片生成成功率≥90%  
* MCP发布成功率≥95%  
* 支持3-5账号并发运营  
* 互动数据每日自动抓取  
* AI评分vs真实评分误差\<15

# **17\. 验收标准与测试用例**

## **17.1 功能验收**

| 功能 | 标准 | 测试方法 |
| ----- | ----- | ----- |
| **选题生成** | 生成3-5个评分\>70 | 运行10次，统计合格率 |
| **内容创作** | 800-1200字+emoji+标签 | 人工评审10篇 |
| **AI审核** | 5步全部执行+给出明确结果 | 检查审核日志 |
| **图片生成** | 3:4竖图+与内容相关 | 生成20张检查 |
| **发布功能** | 成功发布到小红书 | 实际发布测试 |
| **数据记录** | 所有字段完整存储 | 飞书表格核对 |

## **17.2 性能验收**

* 单篇生成时间：10次平均≤5分钟  
* 工作流成功率：30天统计≥85%  
* 并发测试：同时运行3个任务无阻塞  
* 错误恢复：可重试错误80%自动恢复

## **17.3 质量验收**

| 测试项 | 方法 | 标准 |
| ----- | ----- | ----- |
| **内容可读性** | 人工评审20篇 | ≥85%良好 |
| **风格一致性** | 对比30天内容 | 无明显波动 |
| **违规检测** | 测试100次 | 0次违规内容 |
| **标签准确性** | 人工核对50篇 | ≥90%相关 |

# **18\. 约束条件与风险**

## **18.1 平台限制**

* 小红书无官方API，需通过MCP  
* 频繁发布可能触发风控  
* 内容需符合平台规范  
* 自动化存在账号封禁风险

## **18.2 技术风险**

| 风险 | 级别 | 应对策略 |
| ----- | ----- | ----- |
| **RPA不稳定** | 高 | MCP方案+人工审核 |
| **账号安全** | 高 | 半自动+限频+多账号 |
| **内容质量波动** | 高 | 多层审核+数据优化 |
| **第三方依赖** | 中 | 准备备用方案 |
| **网络问题** | 中 | 重试机制+本地缓存 |
| **数据丢失** | 中 | 定期备份 |
| **服务器宕机** | 低 | 监控+告警 |
| **版本升级** | 低 | 测试环境验证 |

## **18.3 应对措施**

**账号安全：**

* 半自动发布（人工确认环节）  
* 严格限频（3篇/天，间隔4h）  
* 多账号轮换（降低单账号风险）  
* 内容审核（AI+人工双重保障）

**技术稳定：**

* 完善错误处理（3层重试）  
* 关键节点通知（及时发现问题）  
* 定期备份（每日备份工作流+数据）  
* 监控告警（服务异常自动通知）

# **附录**

# **A. 飞书多维表格字段映射**

**表名：content\_records**

| 飞书字段名 | 字段类型 | 代码字段 | 必填 | 说明 |
| ----- | ----- | ----- | ----- | ----- |
| **记录ID** | 单行文本 | id | ✓ | UUID主键 |
| **创建时间** | 日期 | created\_at | ✓ | 自动填充 |
| **内容方向** | 单选 | content\_direction | ✓ | AI工具/自动化/技术教程 |
| **选题来源** | 单选 | topic\_source | ✓ | AI生成/热点结合/手动 |
| **标题** | 单行文本 | title | ✓ | 15-30字 |
| **正文** | 多行文本 | content\_body | ✓ | 800-1200字 |
| **标签** | 多选 | tags | ✓ | 8-10个 |
| **封面图** | 附件 | image\_url | \- | 图片URL |
| **AI评分** | 数字 | ai\_score | ✓ | 0-100 |
| **真实评分** | 数字 | real\_score | \- | 发布后计算 |
| **预测误差** | 数字 | prediction\_error | \- | |ai-real| |
| **状态** | 单选 | status | ✓ | 见状态机 |
| **发布时间** | 日期 | published\_at | \- | 发布后填充 |
| **关联账号** | 关联字段 | account\_id | ✓ | 关联accounts表 |
| **执行ID** | 单行文本 | workflow\_run\_id | ✓ | N8N执行ID |
| **阅读量** | 数字 | views | \- | 定期抓取 |
| **点赞数** | 数字 | likes | \- | 定期抓取 |
| **收藏数** | 数字 | collects | \- | 定期抓取 |
| **评论数** | 数字 | comments | \- | 定期抓取 |

视图设置建议：

* 视图1：待审核内容（status=AI\_REVIEWED）  
* 视图2：已发布内容（status=PUBLISHED，按published\_at降序）  
* 视图3：失败记录（status=FAILED）  
* 视图4：本周统计（按account分组聚合）

# **B. N8N工作流示例JSON**

**核心工作流：content\_generator\_v1**

{  
  "name": "content\_generator\_v1",  
  "nodes": \[  
    {  
      "name": "Schedule Trigger",  
      "type": "n8n-nodes-base.scheduleTrigger",  
      "parameters": {  
        "rule": { "hour": 9, "minute": 0 }  
      }  
    },  
    {  
      "name": "Fetch\_Config",  
      "type": "n8n-nodes-base.httpRequest",  
      "parameters": {  
        "url": "https://open.feishu.cn/...",  
        "authentication": "predefinedCredentialType",  
        "nodeCredentialType": "larkApi"  
      }  
    },  
    {  
      "name": "AI\_Gateway",  
      "type": "n8n-nodes-base.function",  
      "parameters": {  
        "functionCode": "// 见4.5章AI网关设计"  
      }  
    },  
    {  
      "name": "Save\_To\_Lark",  
      "type": "n8n-nodes-base.httpRequest",  
      "parameters": {  
        "method": "POST",  
        "url": "https://open.feishu.cn/...",  
        "bodyParameters": {  
          "fields": "{{ $json }}"  
        }  
      }  
    }  
  \],  
  "connections": {  
    "Schedule Trigger": { "main": \[\[{ "node": "Fetch\_Config" }\]\] },  
    "Fetch\_Config": { "main": \[\[{ "node": "AI\_Gateway" }\]\] }  
  }  
}

# **C. API调用示例**

**Claude API调用示例：**

// JavaScript示例  
const response \= await fetch('https://api.anthropic.com/v1/messages', {  
  method: 'POST',  
  headers: {  
    'x-api-key': process.env.CLAUDE\_API\_KEY,  
    'anthropic-version': '2023-06-01',  
    'content-type': 'application/json'  
  },  
  body: JSON.stringify({  
    model: 'claude-sonnet-4-20250514',  
    max\_tokens: 4000,  
    messages: \[{  
      role: 'user',  
      content: '生成一个关于AI自动化的小红书选题...'  
    }\]  
  })  
});

const data \= await response.json();  
console.log(data.content\[0\].text);  
console.log('Cost:', data.usage);

**飞书API调用示例：**

// 插入记录  
POST https://open.feishu.cn/open-api/bitable/v1/apps/{app\_token}/tables/{table\_id}/records  
Authorization: Bearer {access\_token}

{  
  "fields": {  
    "id": "uuid-xxx",  
    "title": "AI自动化工具推荐",  
    "ai\_score": 85,  
    "status": "AI\_REVIEWED"  
  }  
}

# **D. 故障排查检查清单**

**1\. 内容生成失败：**

□ Claude API密钥是否有效

□ 是否超过RPM限制

□ Prompt长度是否超限

□ 查看N8N execution日志

□ 检查飞书config配置

**2\. 图片生成失败：**

□ Gemini API密钥

□ 图片prompt是否合规

□ 网络连接

□ 存储空间

**3\. 发布失败：**

□ 小红书MCP配置

□ 账号状态（是否封禁）

□ 发布频率是否过高

□ 内容敏感词检测

**4\. 数据存储失败：**

□ 飞书API Token

□ 字段类型匹配

□ 必填字段完整

□ 网络连接

**5\. 工作流不触发：**

□ Schedule Trigger时间

□ enable\_flag是否开启

□ N8N服务运行状态

□ 服务器时区设置

## **文档结束**

本技术需求文档v2.0已完成，可直接用于N8N+Claude实施。

如有疑问或需要调整，请及时反馈。