# N8N 子工作流配置说明: sub_ai_score

> 项目代号: XHS_AutoPublisher_v2 | 5 步 AI 审核
> 版本: v1.0 | 最后更新: 2024-12-11

---

## 目录

1. [子工作流结构说明](#1-子工作流结构说明)
2. [Step 0-5 Prompt 模板](#2-step-0-5-prompt-模板)
3. [汇总逻辑伪代码](#3-汇总逻辑伪代码)

---

## 1. 子工作流结构说明

### 1.1 基本信息

| 属性 | 值 |
|------|-----|
| **子工作流名称** | sub_ai_score |
| **职责** | 执行 6 步 AI 审核，返回综合评分和审核意见 |
| **调用方式** | Execute Workflow (从主工作流调用) |
| **预计执行时间** | 30-60 秒 |

### 1.2 输入数据结构

```json
{
  "title": "3个AI工具让我效率翻倍，第2个太香了",
  "content_body": "完整正文内容（800-1200字）...",
  "tags": ["AI", "效率", "工具推荐"],
  "account_profile": {
    "name": "AI效率君",
    "positioning": "专注AI自动化和效率提升",
    "tone": "专业但亲切",
    "target_audience": "25-35岁职场人"
  },
  "metadata": {
    "content_id": "uuid-xxx",
    "workflow_run_id": "exec_abc123",
    "prompt_id": "CONTENT_GEN",
    "prompt_version": "V2"
  }
}
```

### 1.3 输出数据结构

```json
{
  "score": 82,
  "status": "AI_REVIEWED",
  "step_scores": [
    { "step_id": 0, "name": "账号定位检查", "score": 85, "weight": 0.10 },
    { "step_id": 1, "name": "三秒测试", "score": 78, "weight": 0.30 },
    { "step_id": 2, "name": "首屏测试", "score": 80, "weight": 0.15 },
    { "step_id": 3, "name": "全文质量", "score": 85, "weight": 0.25 },
    { "step_id": 4, "name": "互动设计", "score": 75, "weight": 0.10 },
    { "step_id": 5, "name": "平台合规", "score": 90, "weight": 0.10 }
  ],
  "review_comments": [
    "标题缺少数字元素，建议优化",
    "开头钩子较弱，可加强痛点共鸣",
    "内容干货充足，逻辑清晰",
    "缺少明确的评论引导"
  ],
  "suggestions": [
    "标题建议改为：3个AI工具让我效率翻3倍，第2个太香了",
    "开头可以加入具体场景：上周加班到12点..."
  ],
  "passed": true
}
```

### 1.4 节点流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                        sub_ai_score                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  Workflow       │ (Execute Workflow Trigger)
│  Trigger        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Prepare_Input  │ → 提取 title, content_body, 首屏内容
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Loop: 6 次 (Step 0 → Step 5)                                    │
│  ┌─────────────────┐                                            │
│  │  Set_Step_Info  │ → 设置当前 step_id 和 prompt                │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  AI_Gateway     │ → 调用 Claude 执行审核                      │
│  │  (REVIEW_STEP_i)│                                            │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Parse_Step     │ → 解析评分和评语                            │
│  │  Result         │                                            │
│  └────────┬────────┘                                            │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  Append_To      │ → 累积到 step_scores 数组                   │
│  │  Results        │                                            │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Calculate      │ → 加权计算最终得分
│  Final_Score    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Determine      │ → 根据阈值判断 status
│  Status         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Format_Output  │ → 组装输出数据
└─────────────────┘
```

### 1.5 N8N 实现方式

**方式 A: 使用 Split In Batches + Loop**

由于 N8N 原生不支持 for 循环，可以用以下方式：

1. 创建包含 6 个 step 配置的数组
2. 使用 Split In Batches 节点逐个处理
3. 每个 batch 调用 AI_Gateway
4. 使用 Merge 节点汇总结果

**方式 B: 串联 6 个独立节点**

更直观的方式是创建 6 个串联的审核节点：
```
AI_Step0 → AI_Step1 → AI_Step2 → AI_Step3 → AI_Step4 → AI_Step5 → Calculate
```

### 1.6 评分权重配置

| Step | 名称 | 权重 | 满分贡献 |
|------|------|------|----------|
| 0 | 账号定位检查 | 10% | 10 分 |
| 1 | 三秒测试 | 30% | 30 分 |
| 2 | 首屏测试 | 15% | 15 分 |
| 3 | 全文质量 | 25% | 25 分 |
| 4 | 互动设计 | 10% | 10 分 |
| 5 | 平台合规 | 10% | 10 分 |

### 1.7 状态判定阈值

| 总分范围 | status | 说明 |
|----------|--------|------|
| ≥ 80 | AI_REVIEWED | 质量良好，可直接发布 |
| 70-79 | NEEDS_OPTIMIZATION | 建议优化后发布 |
| < 70 | REJECTED | 不建议发布，需重新生成 |

---

## 2. Step 0-5 Prompt 模板

### 2.1 通用 Prompt 结构

每个 Step 的 Prompt 遵循统一结构：
1. 角色定义
2. 审核任务说明
3. 评分维度和标准
4. 待审核内容
5. 输出格式要求

### 2.2 Step 0: 账号定位检查

```markdown
# PROMPT_ID: REVIEW_STEP_0 | VERSION: V1

## 角色
你是一位小红书账号运营专家，负责检查内容与账号定位的匹配度。

## 审核任务
检查以下内容是否符合账号定位，评估主题、受众、调性的一致性。

## 账号定位信息
- 账号名称：{account_name}
- 账号定位：{account_positioning}
- 目标受众：{target_audience}
- 内容调性：{account_tone}

## 待审核内容
**标题**：{title}

**正文**：
{content_body}

## 评分维度（总分 100）
1. **主题匹配度（40分）**：内容主题是否在账号覆盖范围内
2. **受众匹配度（30分）**：目标读者是否与账号受众一致
3. **调性匹配度（30分）**：写作风格是否符合账号调性

## 输出格式
严格按照以下 JSON 格式输出，禁止输出任何额外文字：

```json
{
  "step_id": 0,
  "step_name": "账号定位检查",
  "score": 85,
  "dimension_scores": {
    "topic_match": 35,
    "audience_match": 25,
    "tone_match": 25
  },
  "short_comment": "一句话总结（20字内）",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}
```

只输出 JSON，不要任何解释。
```

---

### 2.3 Step 1: 三秒测试

```markdown
# PROMPT_ID: REVIEW_STEP_1 | VERSION: V1

## 角色
你是一位小红书用户体验专家，负责评估内容的第一印象吸引力。

## 审核任务
模拟用户在信息流中 3 秒内的决策：看到标题后是否想点进来？

## 待审核内容
**标题**：{title}

**开头首句**：{first_sentence}

## 评分维度（总分 100）
1. **好奇心激发（30分）**：标题是否让人想点进来一探究竟
2. **价值感知（25分）**：是否能快速感知到能获得什么
3. **数字/对比（20分）**：是否使用了数字、对比等吸睛元素
4. **情绪触发（15分）**：是否能触发好奇/焦虑/共鸣/获得感
5. **长度适中（10分）**：标题长度是否在 15-30 字

## 小红书爆款标题公式参考
- 数字公式：「3个方法」「5分钟学会」
- 对比公式：「月薪3k vs 月薪3w」
- 痛点公式：「为什么你总是...」
- 好奇公式：「原来...竟然...」

## 输出格式
严格按照以下 JSON 格式输出，禁止输出任何额外文字：

```json
{
  "step_id": 1,
  "step_name": "三秒测试",
  "score": 78,
  "dimension_scores": {
    "curiosity": 25,
    "value_perception": 20,
    "numbers_contrast": 15,
    "emotion_trigger": 10,
    "length_appropriate": 8
  },
  "short_comment": "一句话总结（20字内）",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}
```

只输出 JSON，不要任何解释。
```

---

### 2.4 Step 2: 首屏测试

```markdown
# PROMPT_ID: REVIEW_STEP_2 | VERSION: V1

## 角色
你是一位小红书内容编辑，负责评估开头内容的吸引力。

## 审核任务
评估用户点进来后，前 100 字（首屏）是否能留住用户继续阅读。

## 待审核内容
**标题**：{title}

**首屏内容（前100字）**：
{first_100_chars}

## 评分维度（总分 100）
1. **钩子强度（40分）**：开头是否有力，能否立即抓住注意力
2. **痛点共鸣（30分）**：是否触及读者真实痛点或需求
3. **继续阅读欲（30分）**：看完首屏是否想继续往下看

## 优秀开头特征
- 场景代入：「上周加班到12点的时候...」
- 痛点直击：「是不是每次做PPT都要花3小时？」
- 反差吸引：「以前我也觉得AI没用，直到...」
- 数据冲击：「用了这个方法，效率提升了300%」

## 输出格式
严格按照以下 JSON 格式输出，禁止输出任何额外文字：

```json
{
  "step_id": 2,
  "step_name": "首屏测试",
  "score": 80,
  "dimension_scores": {
    "hook_strength": 35,
    "pain_point_resonance": 25,
    "continue_desire": 20
  },
  "short_comment": "一句话总结（20字内）",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}
```

只输出 JSON，不要任何解释。
```

---

### 2.5 Step 3: 全文质量

```markdown
# PROMPT_ID: REVIEW_STEP_3 | VERSION: V1

## 角色
你是一位资深内容审核编辑，负责评估文章的整体内容质量。

## 审核任务
评估全文的干货密度、逻辑结构、可操作性和可读性。

## 待审核内容
**标题**：{title}

**完整正文**：
{content_body}

## 评分维度（总分 100）
1. **干货密度（35分）**：信息量是否充足，有多少实质性内容
2. **逻辑结构（25分）**：条理是否清晰，是否有明确的结构
3. **可操作性（20分）**：建议是否具体可执行，读者能否直接应用
4. **可读性（20分）**：是否易于阅读，段落、排版是否合理

## 内容质量标准
- 干货：有具体方法/工具/数据，而非泛泛而谈
- 结构：开头-要点1-要点2-要点3-结尾，逻辑递进
- 操作：「第一步...第二步...」或「打开xx→点击xx」
- 排版：短段落、适度emoji、重点标注

## 输出格式
严格按照以下 JSON 格式输出，禁止输出任何额外文字：

```json
{
  "step_id": 3,
  "step_name": "全文质量",
  "score": 85,
  "dimension_scores": {
    "info_density": 30,
    "logic_structure": 22,
    "actionability": 18,
    "readability": 15
  },
  "short_comment": "一句话总结（20字内）",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}
```

只输出 JSON，不要任何解释。
```

---

### 2.6 Step 4: 互动设计

```markdown
# PROMPT_ID: REVIEW_STEP_4 | VERSION: V1

## 角色
你是一位小红书运营专家，负责评估内容的互动引导设计。

## 审核任务
评估内容是否有效引导用户评论、收藏、分享。

## 待审核内容
**标题**：{title}

**完整正文**：
{content_body}

**标签**：{tags}

## 评分维度（总分 100）
1. **评论引导（35分）**：是否有引导评论的设计（提问、互动话题）
2. **收藏动机（35分）**：是否有让人想收藏的干货/清单/教程
3. **分享价值（30分）**：是否有让人想分享给朋友的价值

## 互动引导技巧
- 评论引导：「你们觉得哪个最有用？评论区告诉我」
- 收藏动机：「建议先收藏，用的时候翻出来」
- 分享价值：实用清单、避坑指南、省钱攻略

## 输出格式
严格按照以下 JSON 格式输出，禁止输出任何额外文字：

```json
{
  "step_id": 4,
  "step_name": "互动设计",
  "score": 75,
  "dimension_scores": {
    "comment_guide": 25,
    "save_motivation": 30,
    "share_value": 20
  },
  "short_comment": "一句话总结（20字内）",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}
```

只输出 JSON，不要任何解释。
```

---

### 2.7 Step 5: 平台合规

```markdown
# PROMPT_ID: REVIEW_STEP_5 | VERSION: V1

## 角色
你是一位小红书平台规则专家，负责检查内容的合规性和平台适配度。

## 审核任务
检查内容是否符合小红书平台规则，风格是否适配平台调性。

## 待审核内容
**标题**：{title}

**完整正文**：
{content_body}

**标签**：{tags}

## 评分维度（总分 100）
1. **平台风格（30分）**：是否符合小红书的内容调性（真实、有用、有趣）
2. **标签质量（25分）**：标签是否相关、数量是否合适（3-8个）
3. **排版规范（20分）**：段落、emoji、格式是否符合平台习惯
4. **合规检查（25分）**：是否有敏感词、违规内容、过度营销

## 小红书内容红线
- 禁止：虚假宣传、诱导交易、敏感政治、低俗内容
- 慎用：绝对化用语（最好、第一）、医疗健康建议
- 注意：不要过度引流、不要硬广

## 输出格式
严格按照以下 JSON 格式输出，禁止输出任何额外文字：

```json
{
  "step_id": 5,
  "step_name": "平台合规",
  "score": 90,
  "dimension_scores": {
    "platform_style": 28,
    "tags_quality": 22,
    "formatting": 18,
    "compliance": 22
  },
  "short_comment": "一句话总结（20字内）",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"],
  "risk_flags": []
}
```

只输出 JSON，不要任何解释。
```

---

## 3. 汇总逻辑伪代码

### 3.1 完整 Function 节点代码

```javascript
/**
 * sub_ai_score - 最终评分汇总节点
 * 用于 N8N Function 节点
 */

// ==================== 配置 ====================

const STEP_CONFIG = [
  { step_id: 0, name: '账号定位检查', weight: 0.10, prompt_id: 'REVIEW_STEP_0' },
  { step_id: 1, name: '三秒测试',     weight: 0.30, prompt_id: 'REVIEW_STEP_1' },
  { step_id: 2, name: '首屏测试',     weight: 0.15, prompt_id: 'REVIEW_STEP_2' },
  { step_id: 3, name: '全文质量',     weight: 0.25, prompt_id: 'REVIEW_STEP_3' },
  { step_id: 4, name: '互动设计',     weight: 0.10, prompt_id: 'REVIEW_STEP_4' },
  { step_id: 5, name: '平台合规',     weight: 0.10, prompt_id: 'REVIEW_STEP_5' }
];

const STATUS_THRESHOLDS = {
  AI_REVIEWED: 80,        // >= 80 通过
  NEEDS_OPTIMIZATION: 70, // >= 70 && < 80 需优化
  REJECTED: 0             // < 70 拒绝
};

// ==================== 主逻辑 ====================

/**
 * 计算加权总分
 * @param {Array} stepResults - 各步骤的评分结果
 * @returns {number} 加权总分 (0-100)
 */
function calculateWeightedScore(stepResults) {
  let totalScore = 0;
  let totalWeight = 0;

  for (const result of stepResults) {
    const config = STEP_CONFIG.find(s => s.step_id === result.step_id);
    if (config) {
      totalScore += result.score * config.weight;
      totalWeight += config.weight;
    }
  }

  // 确保权重总和为 1，否则归一化
  if (totalWeight > 0 && totalWeight !== 1) {
    totalScore = totalScore / totalWeight;
  }

  return Math.round(totalScore * 100) / 100; // 保留两位小数
}

/**
 * 根据总分判定状态
 * @param {number} score - 总分
 * @returns {string} 状态
 */
function determineStatus(score) {
  if (score >= STATUS_THRESHOLDS.AI_REVIEWED) {
    return 'AI_REVIEWED';
  } else if (score >= STATUS_THRESHOLDS.NEEDS_OPTIMIZATION) {
    return 'NEEDS_OPTIMIZATION';
  } else {
    return 'REJECTED';
  }
}

/**
 * 收集所有评语和建议
 * @param {Array} stepResults - 各步骤的评分结果
 * @returns {Object} { comments, suggestions, issues }
 */
function collectFeedback(stepResults) {
  const comments = [];
  const suggestions = [];
  const issues = [];

  for (const result of stepResults) {
    // 收集简短评语
    if (result.short_comment) {
      comments.push(`[Step ${result.step_id}] ${result.short_comment}`);
    }

    // 收集建议
    if (result.suggestions && result.suggestions.length > 0) {
      suggestions.push(...result.suggestions);
    }

    // 收集问题
    if (result.issues && result.issues.length > 0) {
      issues.push(...result.issues);
    }
  }

  return { comments, suggestions, issues };
}

/**
 * 格式化步骤分数（添加权重信息）
 * @param {Array} stepResults - 各步骤的评分结果
 * @returns {Array} 格式化后的分数数组
 */
function formatStepScores(stepResults) {
  return stepResults.map(result => {
    const config = STEP_CONFIG.find(s => s.step_id === result.step_id);
    return {
      step_id: result.step_id,
      name: config?.name || `Step ${result.step_id}`,
      score: result.score,
      weight: config?.weight || 0,
      weighted_score: Math.round(result.score * (config?.weight || 0) * 100) / 100,
      dimension_scores: result.dimension_scores || {},
      short_comment: result.short_comment || ''
    };
  });
}

// ==================== N8N 节点执行 ====================

// 获取所有步骤的评分结果
// 假设前序节点已将 6 个步骤的结果合并到一个数组中
const inputData = $input.all()[0].json;
const stepResults = inputData.step_results || [];

// 如果使用串联节点方式，需要从各个节点收集结果
// const stepResults = [
//   $('AI_Step0').item.json,
//   $('AI_Step1').item.json,
//   $('AI_Step2').item.json,
//   $('AI_Step3').item.json,
//   $('AI_Step4').item.json,
//   $('AI_Step5').item.json,
// ];

// 验证结果完整性
if (stepResults.length !== 6) {
  console.warn(`预期 6 个步骤结果，实际收到 ${stepResults.length} 个`);
}

// 计算总分
const finalScore = calculateWeightedScore(stepResults);

// 判定状态
const status = determineStatus(finalScore);

// 收集反馈
const feedback = collectFeedback(stepResults);

// 格式化输出
const formattedStepScores = formatStepScores(stepResults);

// 组装输出
const output = {
  // 核心结果
  score: finalScore,
  status: status,
  passed: status !== 'REJECTED',

  // 详细分数
  step_scores: formattedStepScores,

  // 反馈信息
  review_comments: feedback.comments,
  suggestions: feedback.suggestions.slice(0, 5), // 最多 5 条建议
  issues: feedback.issues,

  // 元数据
  metadata: {
    total_steps: stepResults.length,
    weights_sum: STEP_CONFIG.reduce((sum, s) => sum + s.weight, 0),
    thresholds: STATUS_THRESHOLDS,
    reviewed_at: new Date().toISOString()
  },

  // 保留原始输入（便于调试）
  original_input: {
    title: inputData.title,
    content_length: inputData.content_body?.length || 0
  }
};

return [{ json: output }];
```

### 3.2 单步 AI 调用封装

```javascript
/**
 * 单步审核调用封装
 * 用于循环中的 AI_Gateway 调用
 */

// 审核步骤 Prompt 模板
const REVIEW_PROMPTS = {
  0: { /* Step 0 模板 - 账号定位检查 */ },
  1: { /* Step 1 模板 - 三秒测试 */ },
  2: { /* Step 2 模板 - 首屏测试 */ },
  3: { /* Step 3 模板 - 全文质量 */ },
  4: { /* Step 4 模板 - 互动设计 */ },
  5: { /* Step 5 模板 - 平台合规 */ }
};

/**
 * 渲染审核 Prompt
 * @param {number} stepId - 步骤 ID (0-5)
 * @param {Object} content - 待审核内容
 * @returns {string} 渲染后的 Prompt
 */
function renderReviewPrompt(stepId, content) {
  const { title, content_body, tags, account_profile } = content;

  // 提取首句和首屏内容
  const firstSentence = content_body.split(/[。！？\n]/)[0] || '';
  const first100Chars = content_body.substring(0, 100);

  // 通用变量
  const variables = {
    title: title,
    content_body: content_body,
    first_sentence: firstSentence,
    first_100_chars: first100Chars,
    tags: Array.isArray(tags) ? tags.join('、') : tags,
    account_name: account_profile?.name || '未设置',
    account_positioning: account_profile?.positioning || '未设置',
    target_audience: account_profile?.target_audience || '未设置',
    account_tone: account_profile?.tone || '未设置'
  };

  // 获取对应步骤的模板并渲染
  // (实际实现中从 REVIEW_PROMPTS 获取模板)
  const template = getPromptTemplate(stepId);
  return renderTemplate(template, variables);
}

/**
 * 解析 AI 返回的审核结果
 * @param {string} responseText - AI 原始响应
 * @param {number} stepId - 步骤 ID
 * @returns {Object} 解析后的结果
 */
function parseReviewResult(responseText, stepId) {
  // 尝试提取 JSON
  let jsonStr = responseText;
  const match = responseText.match(/```json\s*([\s\S]*?)\s*```/);
  if (match) {
    jsonStr = match[1];
  }

  try {
    const result = JSON.parse(jsonStr);

    // 验证必要字段
    if (typeof result.score !== 'number') {
      throw new Error('Missing score field');
    }

    // 确保 step_id 正确
    result.step_id = stepId;

    return result;
  } catch (e) {
    // 解析失败时返回默认结果
    console.error(`Step ${stepId} 解析失败:`, e.message);
    return {
      step_id: stepId,
      score: 60, // 默认中等分数
      short_comment: '解析失败，使用默认评分',
      issues: ['AI 响应格式异常'],
      suggestions: [],
      parse_error: e.message
    };
  }
}
```

### 3.3 使用示例（主工作流调用）

```javascript
/**
 * 在主工作流 content_generator_v1 中调用 sub_ai_score
 */

// 准备输入数据
const contentData = $('Parse_Content').item.json;

const reviewInput = {
  title: contentData.title,
  content_body: contentData.content_body,
  tags: contentData.tags,
  account_profile: {
    name: 'AI效率君',
    positioning: '专注AI自动化和效率提升',
    tone: '专业但亲切',
    target_audience: '25-35岁职场人'
  },
  metadata: {
    content_id: contentData.content_id,
    workflow_run_id: $execution.id
  }
};

// 调用子工作流（使用 Execute Workflow 节点）
// 配置：
// - Source: Database
// - Workflow: sub_ai_score
// - Mode: Wait for Sub-Workflow Completion

return [{ json: reviewInput }];
```

---

## 附录: 快速配置清单

### N8N 节点配置

| 节点 | 类型 | 说明 |
|------|------|------|
| Workflow_Trigger | Execute Workflow Trigger | 接收主工作流输入 |
| Prepare_Input | Function | 预处理内容（提取首屏等） |
| Loop_Steps | Split In Batches | 循环 6 个步骤 |
| Set_Step_Config | Set | 设置当前步骤的 Prompt |
| AI_Gateway | HTTP Request | 调用 Claude API |
| Parse_Result | Function | 解析 AI 响应 |
| Merge_Results | Merge | 合并所有步骤结果 |
| Calculate_Score | Function | 计算最终得分 |
| Output | Set | 格式化输出 |

### 环境变量

| 变量 | 说明 |
|------|------|
| CLAUDE_API_KEY | Claude API 密钥 |
| AI_REVIEW_MODEL | 审核使用的模型（默认 claude-sonnet-4-20250514） |
