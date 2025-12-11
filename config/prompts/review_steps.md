# AI审核Prompt集合

---

## PROMPT_ID: REVIEW_STEP0 | VERSION: V1 | UPDATED: 2024-12-11

### Step 0: 账号定位检查

**任务**：检查内容是否符合账号定位

**账号定位**：{{account_profile}}

**待审核内容**：
- 标题：{{title}}
- 正文：{{content_body}}

**评分标准(满分100)**：
- 主题匹配度(40分)：内容主题是否在账号覆盖范围内
- 受众匹配度(30分)：目标读者是否与账号受众一致
- 调性匹配度(30分)：写作风格是否符合账号调性

**输出格式**：
```json
{
  "step": 0,
  "score": 85,
  "details": {
    "topic_match": 35,
    "audience_match": 25,
    "tone_match": 25
  },
  "comment": "内容与账号定位契合度高..."
}
```

---

## PROMPT_ID: REVIEW_STEP1 | VERSION: V1 | UPDATED: 2024-12-11

### Step 1: 三秒测试(标题+封面)

**任务**：评估标题的点击吸引力

**待审核标题**：{{title}}

**评分标准(满分100)**：
- 好奇心激发(30分)：是否让人想点进来
- 价值感知(25分)：是否明确传达能获得什么
- 数字/对比(20分)：是否有具体数字或对比
- 情绪触发(15分)：是否触发目标情绪
- 长度适中(10分)：15-30字

**输出格式**：
```json
{
  "step": 1,
  "score": 78,
  "details": {
    "curiosity": 25,
    "value": 20,
    "numbers": 15,
    "emotion": 10,
    "length": 8
  },
  "comment": "标题缺少数字..."
}
```

---

## PROMPT_ID: REVIEW_STEP2 | VERSION: V1 | UPDATED: 2024-12-11

### Step 2: 首屏测试

**任务**：评估开头100字的吸引力

**待审核内容**：{{first_100_chars}}

**评分标准(满分100)**：
- 钩子强度(40分)：开头是否抓人
- 痛点共鸣(30分)：是否触及读者痛点
- 继续阅读欲(30分)：是否想继续看下去

**输出格式**：
```json
{
  "step": 2,
  "score": 82,
  "details": {
    "hook_strength": 35,
    "pain_point": 25,
    "continue_desire": 22
  },
  "comment": "开头有效建立了共鸣..."
}
```

---

## PROMPT_ID: REVIEW_STEP3 | VERSION: V1 | UPDATED: 2024-12-11

### Step 3: 全文质量

**任务**：评估正文的内容质量

**待审核正文**：{{content_body}}

**评分标准(满分100)**：
- 干货密度(35分)：信息量是否充足
- 逻辑结构(25分)：条理是否清晰
- 可操作性(20分)：是否有可执行的建议
- 可读性(20分)：是否易于阅读

**输出格式**：
```json
{
  "step": 3,
  "score": 80,
  "details": {
    "info_density": 30,
    "logic": 20,
    "actionable": 15,
    "readability": 15
  },
  "comment": "内容干货充足，但部分建议可操作性不强..."
}
```

---

## PROMPT_ID: REVIEW_STEP4 | VERSION: V1 | UPDATED: 2024-12-11

### Step 4: 互动设计

**任务**：评估内容的互动引导

**待审核内容**：{{content_body}}

**评分标准(满分100)**：
- 评论引导(35分)：是否有引导评论的设计
- 收藏动机(35分)：是否有让人想收藏的点
- 转发意愿(30分)：是否有分享价值

**输出格式**：
```json
{
  "step": 4,
  "score": 75,
  "details": {
    "comment_guide": 25,
    "save_motivation": 30,
    "share_value": 20
  },
  "comment": "缺少明确的评论引导..."
}
```

---

## PROMPT_ID: REVIEW_STEP5 | VERSION: V1 | UPDATED: 2024-12-11

### Step 5: 平台合规

**任务**：检查内容的平台适配性和合规性

**待审核内容**：
- 标题：{{title}}
- 正文：{{content_body}}
- 标签：{{tags}}

**评分标准(满分100)**：
- 小红书风格(30分)：是否符合平台调性
- 标签质量(25分)：标签是否相关且充足
- 排版规范(20分)：段落、emoji使用是否得当
- 敏感词检查(25分)：是否有违规内容

**输出格式**：
```json
{
  "step": 5,
  "score": 90,
  "details": {
    "platform_style": 28,
    "tags_quality": 22,
    "formatting": 18,
    "compliance": 22
  },
  "comment": "内容符合小红书风格..."
}
```
