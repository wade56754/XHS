# 账号状态机与多账号轮换算法

> 项目代号: XHS_AutoPublisher_v2
> 版本: v1.0 | 创建日期: 2024-12-11

---

## 目录

1. [账号状态机](#1-账号状态机)
2. [多账号轮换算法](#2-多账号轮换算法)
3. [N8N Function 节点实现](#3-n8n-function-节点实现)
4. [辅助工作流](#4-辅助工作流)

---

## 1. 账号状态机

### 1.1 状态定义

| 状态 | 说明 | 可发布 | 自动恢复 |
|------|------|--------|----------|
| `ACTIVE` | 正常可用 | ✅ | - |
| `COOLDOWN` | 临时冷却（如限流、异常后自动保护） | ❌ | ✅ 到 `cooldown_until` 自动恢复 |
| `SUSPENDED` | 人工暂停（如账号维护、内容调整） | ❌ | ❌ 需人工恢复 |
| `BANNED` | 平台封禁（违规或异常） | ❌ | ❌ 需人工处理 |

### 1.2 状态迁移表

| 当前状态 | 目标状态 | 触发条件 | 触发方 |
|----------|----------|----------|--------|
| `ACTIVE` | `COOLDOWN` | 发布失败（限流/异常）达到阈值 | 系统自动 |
| `ACTIVE` | `SUSPENDED` | 人工暂停操作 | 人工 |
| `ACTIVE` | `BANNED` | 检测到平台封禁 | 系统自动 |
| `COOLDOWN` | `ACTIVE` | 当前时间 > `cooldown_until` | 系统自动 |
| `COOLDOWN` | `SUSPENDED` | 人工暂停操作 | 人工 |
| `COOLDOWN` | `BANNED` | 检测到平台封禁 | 系统自动 |
| `SUSPENDED` | `ACTIVE` | 人工恢复操作 | 人工 |
| `SUSPENDED` | `BANNED` | 检测到平台封禁 | 系统自动 |
| `BANNED` | `ACTIVE` | 人工解封确认 | 人工 |
| `BANNED` | `SUSPENDED` | 人工降级为暂停（待观察） | 人工 |

### 1.3 状态流转图

```
                          ┌─────────────────────────────────────┐
                          │                                     │
                          ▼                                     │
┌──────────┐  发布失败阈值  ┌──────────┐  时间到期   ┌──────────┐│
│  ACTIVE  │ ───────────→ │ COOLDOWN │ ──────────→ │  ACTIVE  ││
└────┬─────┘              └────┬─────┘             └──────────┘│
     │                         │                               │
     │ 人工暂停                │ 人工暂停                      │
     ▼                         ▼                               │
┌──────────┐              ┌──────────┐                         │
│SUSPENDED │ ◄────────────│SUSPENDED │                         │
└────┬─────┘  人工恢复    └──────────┘                         │
     │        ─────────────────────────────────────────────────┘
     │
     │ 检测到封禁
     ▼
┌──────────┐
│  BANNED  │
└────┬─────┘
     │
     │ 人工解封
     ▼
┌──────────┐
│  ACTIVE  │
└──────────┘
```

### 1.4 accounts 表字段复习

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | string | 账号唯一标识 |
| name | string | 账号名称/昵称 |
| status | enum | `ACTIVE` / `COOLDOWN` / `SUSPENDED` / `BANNED` |
| last_publish_at | datetime | 最后发布时间 |
| publish_count_today | number | 今日已发布数（每日 00:00 重置） |
| cooldown_until | datetime | 冷却截止时间（仅 COOLDOWN 状态有效） |

---

## 2. 多账号轮换算法

### 2.1 设计目标

| 目标 | 说明 |
|------|------|
| **负载均衡** | 平均分配发布任务到各账号 |
| **风控规避** | 避免单账号短时间连发 |
| **自动恢复** | COOLDOWN 状态到期自动恢复 |
| **优雅降级** | 无可用账号时明确返回原因 |

### 2.2 可用账号筛选条件

一个账号被视为"可用"，必须同时满足以下 **全部条件**：

| 序号 | 条件 | 说明 |
|------|------|------|
| 1 | `status === 'ACTIVE'` | 状态为正常 |
| 2 | `publish_count_today < DAILY_LIMIT` | 今日发布数未达上限（默认 3） |
| 3 | `hours_since_last_publish >= INTERVAL_HOURS` | 距上次发布间隔足够（默认 4 小时） |
| 4 | `cooldown_until` 为空或已过期 | 不在冷却期内 |

**筛选伪代码**：

```javascript
function isAccountAvailable(account, config) {
  const now = new Date();

  // 条件 1: 状态检查
  if (account.status !== 'ACTIVE') {
    return { available: false, reason: 'STATUS_NOT_ACTIVE', status: account.status };
  }

  // 条件 2: 今日发布数检查
  if (account.publish_count_today >= config.dailyLimit) {
    return { available: false, reason: 'DAILY_LIMIT_REACHED', current: account.publish_count_today, limit: config.dailyLimit };
  }

  // 条件 3: 发布间隔检查
  if (account.last_publish_at) {
    const hoursSince = (now - new Date(account.last_publish_at)) / (1000 * 60 * 60);
    if (hoursSince < config.intervalHours) {
      const nextAvailable = new Date(account.last_publish_at).getTime() + config.intervalHours * 60 * 60 * 1000;
      return { available: false, reason: 'INTERVAL_TOO_SHORT', hours_since: hoursSince.toFixed(2), next_available_at: new Date(nextAvailable).toISOString() };
    }
  }

  // 条件 4: 冷却期检查
  if (account.cooldown_until && new Date(account.cooldown_until) > now) {
    return { available: false, reason: 'IN_COOLDOWN', cooldown_until: account.cooldown_until };
  }

  return { available: true };
}
```

### 2.3 账号选择策略

在所有可用账号中，按以下优先级选择：

| 优先级 | 策略 | 说明 |
|--------|------|------|
| 1 | **今日发布数最少** | 实现负载均衡 |
| 2 | **距上次发布时间最长** | 分散风控风险 |
| 3 | **账号 ID 字典序** | 稳定的兜底排序 |

**选择伪代码**：

```javascript
function selectBestAccount(availableAccounts) {
  return availableAccounts.sort((a, b) => {
    // 优先级 1: 今日发布数升序
    const countDiff = (a.publish_count_today || 0) - (b.publish_count_today || 0);
    if (countDiff !== 0) return countDiff;

    // 优先级 2: 上次发布时间升序（越早越优先）
    const aLast = a.last_publish_at ? new Date(a.last_publish_at).getTime() : 0;
    const bLast = b.last_publish_at ? new Date(b.last_publish_at).getTime() : 0;
    if (aLast !== bLast) return aLast - bLast;

    // 优先级 3: ID 字典序
    return a.id.localeCompare(b.id);
  })[0];
}
```

### 2.4 无可用账号的原因分类

| 原因码 | 说明 | 建议操作 |
|--------|------|----------|
| `NO_ACCOUNTS` | 账号表为空 | 添加账号 |
| `ALL_INACTIVE` | 全部账号状态非 ACTIVE | 检查账号状态 |
| `ALL_DAILY_LIMIT` | 全部账号今日额度用尽 | 等待明天 |
| `ALL_INTERVAL_SHORT` | 全部账号距上次发布不足 4 小时 | 稍后重试 |
| `ALL_IN_COOLDOWN` | 全部账号在冷却期 | 等待冷却结束 |

---

## 3. N8N Function 节点实现

### 3.1 Select_Account 节点

将以下代码复制到 N8N 的 Function 节点中：

```javascript
/**
 * Select_Account - 多账号轮换选择
 *
 * 输入：
 *   - $json.accounts: 账号数组（来自 Query_All_Accounts 节点）
 *
 * 输出：
 *   - 成功: { has_available: true, selected_account: {...}, available_count: N }
 *   - 失败: { has_available: false, reason: "...", details: {...} }
 */

// ==================== 配置 ====================
const CONFIG = {
  dailyLimit: 3,        // 单账号每日发布上限
  intervalHours: 4,     // 两次发布最小间隔（小时）
};

// ==================== 工具函数 ====================

/**
 * 检查单个账号是否可用
 */
function checkAccountAvailability(account, now) {
  const fields = account.fields || account;

  // 条件 1: 状态检查
  if (fields.status !== 'ACTIVE') {
    return {
      available: false,
      reason: 'STATUS_NOT_ACTIVE',
      details: { current_status: fields.status }
    };
  }

  // 条件 2: 今日发布数检查
  const publishCount = fields.publish_count_today || 0;
  if (publishCount >= CONFIG.dailyLimit) {
    return {
      available: false,
      reason: 'DAILY_LIMIT_REACHED',
      details: { current: publishCount, limit: CONFIG.dailyLimit }
    };
  }

  // 条件 3: 发布间隔检查
  if (fields.last_publish_at) {
    const lastPublishTime = new Date(fields.last_publish_at);
    const hoursSince = (now - lastPublishTime) / (1000 * 60 * 60);

    if (hoursSince < CONFIG.intervalHours) {
      const nextAvailableTime = new Date(lastPublishTime.getTime() + CONFIG.intervalHours * 60 * 60 * 1000);
      return {
        available: false,
        reason: 'INTERVAL_TOO_SHORT',
        details: {
          hours_since: Math.round(hoursSince * 100) / 100,
          required_hours: CONFIG.intervalHours,
          next_available_at: nextAvailableTime.toISOString()
        }
      };
    }
  }

  // 条件 4: 冷却期检查
  if (fields.cooldown_until) {
    const cooldownEnd = new Date(fields.cooldown_until);
    if (cooldownEnd > now) {
      return {
        available: false,
        reason: 'IN_COOLDOWN',
        details: { cooldown_until: fields.cooldown_until }
      };
    }
  }

  // 全部条件通过
  return { available: true };
}

/**
 * 在可用账号中选择最优账号
 */
function selectBestAccount(availableAccounts) {
  return availableAccounts.sort((a, b) => {
    const aFields = a.fields || a;
    const bFields = b.fields || b;

    // 优先级 1: 今日发布数升序（少的优先）
    const countDiff = (aFields.publish_count_today || 0) - (bFields.publish_count_today || 0);
    if (countDiff !== 0) return countDiff;

    // 优先级 2: 上次发布时间升序（早的优先）
    const aLast = aFields.last_publish_at ? new Date(aFields.last_publish_at).getTime() : 0;
    const bLast = bFields.last_publish_at ? new Date(bFields.last_publish_at).getTime() : 0;
    if (aLast !== bLast) return aLast - bLast;

    // 优先级 3: ID 字典序
    return (aFields.id || '').localeCompare(bFields.id || '');
  })[0];
}

/**
 * 分析无可用账号的原因
 */
function analyzeUnavailableReasons(checkResults) {
  const reasons = checkResults.map(r => r.reason);

  // 统计各原因数量
  const reasonCounts = {};
  reasons.forEach(r => {
    reasonCounts[r] = (reasonCounts[r] || 0) + 1;
  });

  // 确定主要原因
  if (reasonCounts['STATUS_NOT_ACTIVE'] === reasons.length) {
    return 'ALL_INACTIVE';
  }
  if (reasonCounts['DAILY_LIMIT_REACHED'] === reasons.length) {
    return 'ALL_DAILY_LIMIT';
  }
  if (reasonCounts['INTERVAL_TOO_SHORT'] === reasons.length) {
    return 'ALL_INTERVAL_SHORT';
  }
  if (reasonCounts['IN_COOLDOWN'] === reasons.length) {
    return 'ALL_IN_COOLDOWN';
  }

  // 混合原因
  return 'MIXED_REASONS';
}

// ==================== 主逻辑 ====================

const now = new Date();

// 获取账号数据（兼容不同输入格式）
let accounts = $json.accounts || $json.data?.items || [];

// 处理飞书 API 返回格式
if ($json.data && $json.data.items) {
  accounts = $json.data.items;
}

// 无账号检查
if (!accounts || accounts.length === 0) {
  return {
    json: {
      has_available: false,
      reason: 'NO_ACCOUNTS',
      details: { message: '账号表为空，请先添加账号' },
      timestamp: now.toISOString()
    }
  };
}

// 检查每个账号的可用性
const checkResults = accounts.map(account => {
  const fields = account.fields || account;
  const result = checkAccountAvailability(account, now);
  return {
    account_id: fields.id,
    account_name: fields.name,
    record_id: account.record_id,
    ...result,
    raw_account: account
  };
});

// 筛选可用账号
const availableAccounts = checkResults
  .filter(r => r.available)
  .map(r => r.raw_account);

// 无可用账号
if (availableAccounts.length === 0) {
  const mainReason = analyzeUnavailableReasons(checkResults);

  // 计算最近可用时间（如果是时间相关原因）
  let nextAvailableAt = null;
  const intervalShortAccounts = checkResults.filter(r => r.reason === 'INTERVAL_TOO_SHORT');
  if (intervalShortAccounts.length > 0) {
    const nextTimes = intervalShortAccounts.map(r => new Date(r.details.next_available_at));
    nextAvailableAt = new Date(Math.min(...nextTimes.map(t => t.getTime()))).toISOString();
  }

  const cooldownAccounts = checkResults.filter(r => r.reason === 'IN_COOLDOWN');
  if (cooldownAccounts.length > 0 && !nextAvailableAt) {
    const cooldownEnds = cooldownAccounts.map(r => new Date(r.details.cooldown_until));
    nextAvailableAt = new Date(Math.min(...cooldownEnds.map(t => t.getTime()))).toISOString();
  }

  return {
    json: {
      has_available: false,
      reason: mainReason,
      details: {
        total_accounts: accounts.length,
        check_results: checkResults.map(r => ({
          account_id: r.account_id,
          account_name: r.account_name,
          reason: r.reason,
          details: r.details
        })),
        next_available_at: nextAvailableAt
      },
      timestamp: now.toISOString()
    }
  };
}

// 选择最优账号
const selected = selectBestAccount(availableAccounts);
const selectedFields = selected.fields || selected;

return {
  json: {
    has_available: true,
    selected_account: {
      record_id: selected.record_id,
      id: selectedFields.id,
      name: selectedFields.name,
      status: selectedFields.status,
      publish_count_today: selectedFields.publish_count_today || 0,
      last_publish_at: selectedFields.last_publish_at || null
    },
    available_count: availableAccounts.length,
    selection_reason: `负载最低（今日已发布 ${selectedFields.publish_count_today || 0} 篇）`,
    timestamp: now.toISOString()
  }
};
```

### 3.2 使用说明

**节点连接方式**：

```
Query_All_Accounts (HTTP Request)
        ↓
  Select_Account (Function)
        ↓
    IF 节点 (has_available === true)
        ↓ True                    ↓ False
Execute_Sub_Publish        Log_No_Account
```

**输入数据示例**：

```json
{
  "accounts": [
    {
      "record_id": "rec_abc123",
      "fields": {
        "id": "acc_001",
        "name": "运营号1",
        "status": "ACTIVE",
        "publish_count_today": 1,
        "last_publish_at": "2024-12-11T06:00:00.000Z",
        "cooldown_until": null
      }
    },
    {
      "record_id": "rec_def456",
      "fields": {
        "id": "acc_002",
        "name": "运营号2",
        "status": "ACTIVE",
        "publish_count_today": 2,
        "last_publish_at": "2024-12-11T08:00:00.000Z",
        "cooldown_until": null
      }
    }
  ]
}
```

**成功输出示例**：

```json
{
  "has_available": true,
  "selected_account": {
    "record_id": "rec_abc123",
    "id": "acc_001",
    "name": "运营号1",
    "status": "ACTIVE",
    "publish_count_today": 1,
    "last_publish_at": "2024-12-11T06:00:00.000Z"
  },
  "available_count": 2,
  "selection_reason": "负载最低（今日已发布 1 篇）",
  "timestamp": "2024-12-11T10:30:00.000Z"
}
```

**失败输出示例**：

```json
{
  "has_available": false,
  "reason": "ALL_INTERVAL_SHORT",
  "details": {
    "total_accounts": 2,
    "check_results": [
      {
        "account_id": "acc_001",
        "account_name": "运营号1",
        "reason": "INTERVAL_TOO_SHORT",
        "details": {
          "hours_since": 2.5,
          "required_hours": 4,
          "next_available_at": "2024-12-11T12:00:00.000Z"
        }
      },
      {
        "account_id": "acc_002",
        "account_name": "运营号2",
        "reason": "INTERVAL_TOO_SHORT",
        "details": {
          "hours_since": 1.2,
          "required_hours": 4,
          "next_available_at": "2024-12-11T14:00:00.000Z"
        }
      }
    ],
    "next_available_at": "2024-12-11T12:00:00.000Z"
  },
  "timestamp": "2024-12-11T10:30:00.000Z"
}
```

---

## 4. 辅助工作流

### 4.1 每日计数重置工作流

**工作流名称**：`reset_daily_publish_count`

**触发时间**：每天 00:00

```javascript
// Reset_Daily_Count Function 节点

const accounts = $json.data.items || [];
const now = new Date().toISOString();

// 生成批量更新请求
const updateRecords = accounts.map(account => ({
  record_id: account.record_id,
  fields: {
    publish_count_today: 0
  }
}));

return {
  json: {
    records: updateRecords,
    count: updateRecords.length,
    reset_at: now
  }
};
```

### 4.2 冷却状态自动恢复

在 `Select_Account` 节点中已隐式处理：当 `cooldown_until` 过期时，账号自动被视为可用。

如需显式更新状态字段，可添加以下逻辑：

```javascript
// Auto_Recover_Cooldown Function 节点

const accounts = $json.data.items || [];
const now = new Date();

// 找出需要恢复的账号
const toRecover = accounts.filter(acc => {
  const fields = acc.fields;
  if (fields.status !== 'COOLDOWN') return false;
  if (!fields.cooldown_until) return false;
  return new Date(fields.cooldown_until) <= now;
});

if (toRecover.length === 0) {
  return { json: { recovered_count: 0, message: '无需恢复的账号' } };
}

// 生成更新请求
const updateRecords = toRecover.map(acc => ({
  record_id: acc.record_id,
  fields: {
    status: 'ACTIVE',
    cooldown_until: null
  }
}));

return {
  json: {
    records: updateRecords,
    recovered_count: updateRecords.length,
    recovered_accounts: toRecover.map(acc => acc.fields.id)
  }
};
```

### 4.3 发布失败后设置冷却

```javascript
// Set_Account_Cooldown Function 节点
// 在发布失败达到阈值后调用

const accountRecordId = $json.account_record_id;
const failureCount = $json.consecutive_failures || 1;

// 根据失败次数计算冷却时长
const cooldownHours = Math.min(failureCount * 2, 24); // 最长 24 小时
const cooldownUntil = new Date(Date.now() + cooldownHours * 60 * 60 * 1000);

return {
  json: {
    record_id: accountRecordId,
    update_fields: {
      status: 'COOLDOWN',
      cooldown_until: cooldownUntil.toISOString()
    },
    cooldown_hours: cooldownHours
  }
};
```

---

## 5. 配置参数说明

| 参数 | 默认值 | 环境变量 | 说明 |
|------|--------|----------|------|
| dailyLimit | 3 | `PUBLISH_DAILY_LIMIT` | 单账号每日发布上限 |
| intervalHours | 4 | `PUBLISH_INTERVAL_HOURS` | 两次发布最小间隔（小时） |

**动态配置示例**（从环境变量读取）：

```javascript
const CONFIG = {
  dailyLimit: parseInt($env.PUBLISH_DAILY_LIMIT) || 3,
  intervalHours: parseFloat($env.PUBLISH_INTERVAL_HOURS) || 4,
};
```

---

> 文档维护：每次账号策略调整后需同步更新本文档
