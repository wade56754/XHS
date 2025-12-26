#!/usr/bin/env python3
"""
XHS 自动化运营系统 - n8n 工作流生成脚本

生成以下工作流:
1. WF-Main: 主控制器 (调度)
2. WF-Discovery: 内容发现 (采集)
3. WF-Extraction: 内容提取
4. WF-Generation: AI内容生成
5. WF-Publish: 自动发布
6. WF-CookieManager: Cookie管理
7. WF-ErrorHandler: 错误处理

使用方法:
python scripts/create_workflows.py --output ./n8n-workflows/
"""

import json
import os
import argparse
from datetime import datetime

# 环境变量配置
ENV_CONFIG = {
    "LARK_APP_TOKEN": "Gq93bAlZ7aSSclsLKdTcYCO2nwh",
    "KEYWORDS_TABLE_ID": "tblE2SypBdIhJVrR",
    "TOPICS_TABLE_ID": "tblPCp5gqgVFnhLc",
    "SOURCE_TABLE_ID": "tblMYjwzOkYpW4AX",
    "CONTENT_TABLE_ID": "tblp3iSuo0dasTtg",
    "PUBLISH_TABLE_ID": "tblp3iSuo0dasTtg",
    "LOGS_TABLE_ID": "tbl8xTUEtAQjxP4k",
    "COOKIE_TABLE_ID": "tblYa2d2a5lypzqz",
    "MEDIACRAWLER_API_URL": "http://124.221.251.8:8080",
    "REDINK_API_URL": "http://localhost:12398",
    "SOCIAL_UPLOAD_URL": "http://124.221.251.8:5409",
}


def create_wf_main():
    """创建主控制器工作流"""
    return {
        "name": "WF-Main-Pipeline",
        "nodes": [
            # 1. Schedule 触发器
            {
                "parameters": {
                    "rule": {
                        "interval": [{"field": "minutes", "minutesInterval": 5}]
                    }
                },
                "id": "schedule",
                "name": "每5分钟触发",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 300]
            },
            # 2. Webhook 触发器
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "xhs-pipeline",
                    "responseMode": "lastNode",
                    "options": {}
                },
                "id": "webhook",
                "name": "手动触发",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 500],
                "webhookId": "xhs-pipeline"
            },
            # 3. 合并触发器
            {
                "parameters": {"mode": "chooseBranch"},
                "id": "merge",
                "name": "合并入口",
                "type": "n8n-nodes-base.merge",
                "typeVersion": 3,
                "position": [250, 400]
            },
            # 4. 健康检查
            {
                "parameters": {
                    "method": "GET",
                    "url": f"={ENV_CONFIG['MEDIACRAWLER_API_URL']}/api/health",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "X-API-Key", "value": "dev-key"}
                        ]
                    },
                    "options": {"timeout": 10000}
                },
                "id": "health-check",
                "name": "检查爬虫健康",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [450, 400]
            },
            # 5. IF 爬虫就绪
            {
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [
                            {
                                "id": "ready",
                                "leftValue": "={{ $json.crawler_ready }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "equals"}
                            }
                        ],
                        "combinator": "and"
                    },
                    "options": {}
                },
                "id": "if-ready",
                "name": "爬虫就绪?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [650, 400]
            },
            # 6. 查询待处理任务 (Code节点生成查询)
            {
                "parameters": {
                    "jsCode": """// 生成并行查询配置
const queries = [
  { table: 'keywords', filter: "status='待采集'", priority: 1 },
  { table: 'topics', filter: "status='待提取'", priority: 2 },
  { table: 'source', filter: "status='待生成'", priority: 3 },
  { table: 'content', filter: "status='待发布'", priority: 4 }
];
return queries.map(q => ({ json: q }));"""
                },
                "id": "prepare-queries",
                "name": "准备查询",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [850, 300]
            },
            # 7. 飞书查询 (使用 feishu-lark 节点)
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "getRecords",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": "={{ $json.table === 'keywords' ? '" + ENV_CONFIG['KEYWORDS_TABLE_ID'] + "' : $json.table === 'topics' ? '" + ENV_CONFIG['TOPICS_TABLE_ID'] + "' : $json.table === 'source' ? '" + ENV_CONFIG['SOURCE_TABLE_ID'] + "' : '" + ENV_CONFIG['CONTENT_TABLE_ID'] + "' }}",
                    "filter": "={{ $json.filter }}",
                    "pageSize": 10
                },
                "id": "feishu-query",
                "name": "飞书查询",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1050, 300],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 8. 优先级分发
            {
                "parameters": {
                    "jsCode": """// 优先级分发逻辑
const results = $input.all();
let selectedTask = null;
let maxPriority = 0;

for (const item of results) {
  const records = item.json.data?.items || [];
  if (records.length > 0 && item.json.priority > maxPriority) {
    maxPriority = item.json.priority;
    selectedTask = {
      action: ['discovery', 'extraction', 'generation', 'publish'][item.json.priority - 1],
      records: records,
      count: records.length
    };
  }
}

if (!selectedTask) {
  return [{ json: { action: 'skip', message: '无待处理任务' } }];
}

return [{ json: selectedTask }];"""
                },
                "id": "priority-dispatch",
                "name": "优先级分发",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1250, 300]
            },
            # 9. Switch 路由
            {
                "parameters": {
                    "rules": {
                        "rules": [
                            {"value": "discovery", "outputIndex": 0},
                            {"value": "extraction", "outputIndex": 1},
                            {"value": "generation", "outputIndex": 2},
                            {"value": "publish", "outputIndex": 3},
                            {"value": "skip", "outputIndex": 4}
                        ]
                    },
                    "options": {},
                    "dataPropertyName": "={{ $json.action }}"
                },
                "id": "switch",
                "name": "路由分发",
                "type": "n8n-nodes-base.switch",
                "typeVersion": 3,
                "position": [1450, 300]
            },
            # 10-14. 执行子工作流占位节点
            {
                "parameters": {
                    "jsCode": "// Discovery - 调用子工作流\nreturn [{ json: { action: 'discovery', status: 'TODO: 连接子工作流' } }];"
                },
                "id": "exec-discovery",
                "name": "执行 Discovery",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1700, 100]
            },
            {
                "parameters": {
                    "jsCode": "// Extraction - 调用子工作流\nreturn [{ json: { action: 'extraction', status: 'TODO: 连接子工作流' } }];"
                },
                "id": "exec-extraction",
                "name": "执行 Extraction",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1700, 250]
            },
            {
                "parameters": {
                    "jsCode": "// Generation - 调用子工作流\nreturn [{ json: { action: 'generation', status: 'TODO: 连接子工作流' } }];"
                },
                "id": "exec-generation",
                "name": "执行 Generation",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1700, 400]
            },
            {
                "parameters": {
                    "jsCode": "// Publish - 调用子工作流\nreturn [{ json: { action: 'publish', status: 'TODO: 连接子工作流' } }];"
                },
                "id": "exec-publish",
                "name": "执行 Publish",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1700, 550]
            },
            {
                "parameters": {
                    "jsCode": "// Skip - 无任务\nreturn [{ json: { action: 'skip', message: '无待处理任务' } }];"
                },
                "id": "skip",
                "name": "跳过",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1700, 700]
            },
            # 15. 合并结果
            {
                "parameters": {"mode": "chooseBranch"},
                "id": "merge-results",
                "name": "合并结果",
                "type": "n8n-nodes-base.merge",
                "typeVersion": 3,
                "position": [1950, 400]
            },
            # 16. 记录日志
            {
                "parameters": {
                    "jsCode": """// 准备日志记录
const input = $input.first().json;
return [{ json: {
  fields: {
    timestamp: new Date().toISOString(),
    level: 'INFO',
    workflow_id: $workflow.id,
    event_type: 'pipeline_execution',
    message: input.message || \`执行: \${input.action}\`,
    context: JSON.stringify(input)
  }
} }];"""
                },
                "id": "prepare-log",
                "name": "准备日志",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [2150, 400]
            },
            # 17. 爬虫未就绪处理
            {
                "parameters": {
                    "jsCode": "return [{ json: { action: 'error', message: '爬虫未就绪，请检查服务状态' } }];"
                },
                "id": "crawler-not-ready",
                "name": "爬虫未就绪",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [850, 550]
            }
        ],
        "connections": {
            "每5分钟触发": {"main": [[{"node": "合并入口", "type": "main", "index": 0}]]},
            "手动触发": {"main": [[{"node": "合并入口", "type": "main", "index": 1}]]},
            "合并入口": {"main": [[{"node": "检查爬虫健康", "type": "main", "index": 0}]]},
            "检查爬虫健康": {"main": [[{"node": "爬虫就绪?", "type": "main", "index": 0}]]},
            "爬虫就绪?": {
                "main": [
                    [{"node": "准备查询", "type": "main", "index": 0}],
                    [{"node": "爬虫未就绪", "type": "main", "index": 0}]
                ]
            },
            "准备查询": {"main": [[{"node": "飞书查询", "type": "main", "index": 0}]]},
            "飞书查询": {"main": [[{"node": "优先级分发", "type": "main", "index": 0}]]},
            "优先级分发": {"main": [[{"node": "路由分发", "type": "main", "index": 0}]]},
            "路由分发": {
                "main": [
                    [{"node": "执行 Discovery", "type": "main", "index": 0}],
                    [{"node": "执行 Extraction", "type": "main", "index": 0}],
                    [{"node": "执行 Generation", "type": "main", "index": 0}],
                    [{"node": "执行 Publish", "type": "main", "index": 0}],
                    [{"node": "跳过", "type": "main", "index": 0}]
                ]
            },
            "执行 Discovery": {"main": [[{"node": "合并结果", "type": "main", "index": 0}]]},
            "执行 Extraction": {"main": [[{"node": "合并结果", "type": "main", "index": 0}]]},
            "执行 Generation": {"main": [[{"node": "合并结果", "type": "main", "index": 0}]]},
            "执行 Publish": {"main": [[{"node": "合并结果", "type": "main", "index": 0}]]},
            "跳过": {"main": [[{"node": "合并结果", "type": "main", "index": 0}]]},
            "合并结果": {"main": [[{"node": "准备日志", "type": "main", "index": 0}]]},
            "爬虫未就绪": {"main": [[{"node": "准备日志", "type": "main", "index": 0}]]}
        },
        "settings": {
            "executionOrder": "v1",
            "saveManualExecutions": True,
            "callerPolicy": "workflowsFromSameOwner"
        },
        "staticData": None,
        "tags": [],
        "meta": {"templateCredsSetupCompleted": True}
    }


def create_wf_discovery():
    """创建内容发现工作流"""
    return {
        "name": "WF-Discovery",
        "nodes": [
            # 1. 工作流输入
            {
                "parameters": {},
                "id": "input",
                "name": "工作流输入",
                "type": "n8n-nodes-base.executeWorkflowTrigger",
                "typeVersion": 1,
                "position": [0, 300]
            },
            # 2. 提取关键词
            {
                "parameters": {
                    "jsCode": """// 提取关键词记录
const records = $input.first().json.records || [];
if (records.length === 0) {
  return [{ json: { success: false, message: '无记录' } }];
}
return records.map(r => ({
  json: {
    record_id: r.record_id,
    keyword: r.fields?.keyword || '',
    min_likes: r.fields?.min_likes || 100,
    crawl_limit: r.fields?.crawl_limit || 20
  }
}));"""
                },
                "id": "extract",
                "name": "提取关键词",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [200, 300]
            },
            # 3. 锁定记录
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['KEYWORDS_TABLE_ID'],
                    "recordId": "={{ $json.record_id }}",
                    "fields": {
                        "status": "采集中",
                        "locked_at": "={{ $now.toISO() }}"
                    }
                },
                "id": "lock",
                "name": "锁定记录",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [400, 300],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 4. 搜索小红书
            {
                "parameters": {
                    "method": "POST",
                    "url": f"{ENV_CONFIG['MEDIACRAWLER_API_URL']}/api/search/human",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "X-API-Key", "value": "dev-key"},
                            {"name": "Content-Type", "value": "application/json"}
                        ]
                    },
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ keyword: $('提取关键词').item.json.keyword, limit: $('提取关键词').item.json.crawl_limit }) }}",
                    "options": {"timeout": 60000}
                },
                "id": "search",
                "name": "搜索小红书",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [600, 300]
            },
            # 5. 检查搜索结果
            {
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [
                            {
                                "id": "success",
                                "leftValue": "={{ $json.success }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "equals"}
                            }
                        ],
                        "combinator": "and"
                    },
                    "options": {}
                },
                "id": "if-success",
                "name": "搜索成功?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [800, 300]
            },
            # 6. 转换数据
            {
                "parameters": {
                    "jsCode": f"""// 转换为飞书记录格式
const items = $input.first().json.data?.items || [];
const keyword = $('提取关键词').item.json.keyword;
const keywordId = $('提取关键词').item.json.record_id;
const minLikes = $('提取关键词').item.json.min_likes;

const filtered = items.filter(i => (i.likes || 0) >= minLikes || !i.likes);

const records = filtered.map(item => ({{
  fields: {{
    keyword_id: keywordId,
    keyword: keyword,
    note_id: item.note_id || item.id,
    title: item.title || '',
    author: item.author || '',
    likes: item.likes || 0,
    cover_url: item.cover || '',
    note_url: 'https://www.xiaohongshu.com/explore/' + (item.note_id || item.id),
    status: '待提取',
    crawled_at: new Date().toISOString()
  }}
}}));

return [{{ json: {{ records, count: records.length }} }}];"""
                },
                "id": "transform",
                "name": "转换数据",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1000, 200]
            },
            # 7. 批量创建Topics
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "createRecords",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['TOPICS_TABLE_ID'],
                    "records": "={{ $json.records }}"
                },
                "id": "create-topics",
                "name": "创建Topics",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1200, 200],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 8. 更新关键词状态(成功)
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['KEYWORDS_TABLE_ID'],
                    "recordId": "={{ $('提取关键词').item.json.record_id }}",
                    "fields": {
                        "status": "已采集",
                        "last_crawl_time": "={{ $now.toISO() }}",
                        "locked_at": ""
                    }
                },
                "id": "update-success",
                "name": "更新成功",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1400, 200],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 9. 处理错误
            {
                "parameters": {
                    "jsCode": """// 处理搜索失败
return [{ json: {
  success: false,
  record_id: $('提取关键词').item.json.record_id,
  error: $input.first().json.error?.message || '搜索失败'
} }];"""
                },
                "id": "handle-error",
                "name": "处理错误",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1000, 400]
            },
            # 10. 更新关键词状态(失败)
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['KEYWORDS_TABLE_ID'],
                    "recordId": "={{ $json.record_id }}",
                    "fields": {
                        "status": "采集失败",
                        "error_message": "={{ $json.error }}",
                        "locked_at": ""
                    }
                },
                "id": "update-failed",
                "name": "更新失败",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1200, 400],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 11. 输出结果
            {
                "parameters": {
                    "jsCode": """// 汇总结果
const results = $input.all();
let success = 0, failed = 0, topics = 0;

for (const item of results) {
  if (item.json.success !== false) {
    success++;
    topics += item.json.count || 0;
  } else {
    failed++;
  }
}

return [{ json: {
  action: 'discovery',
  success: failed === 0,
  keywords_processed: results.length,
  topics_created: topics,
  failed: failed
} }];"""
                },
                "id": "output",
                "name": "输出结果",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1600, 300]
            }
        ],
        "connections": {
            "工作流输入": {"main": [[{"node": "提取关键词", "type": "main", "index": 0}]]},
            "提取关键词": {"main": [[{"node": "锁定记录", "type": "main", "index": 0}]]},
            "锁定记录": {"main": [[{"node": "搜索小红书", "type": "main", "index": 0}]]},
            "搜索小红书": {"main": [[{"node": "搜索成功?", "type": "main", "index": 0}]]},
            "搜索成功?": {
                "main": [
                    [{"node": "转换数据", "type": "main", "index": 0}],
                    [{"node": "处理错误", "type": "main", "index": 0}]
                ]
            },
            "转换数据": {"main": [[{"node": "创建Topics", "type": "main", "index": 0}]]},
            "创建Topics": {"main": [[{"node": "更新成功", "type": "main", "index": 0}]]},
            "更新成功": {"main": [[{"node": "输出结果", "type": "main", "index": 0}]]},
            "处理错误": {"main": [[{"node": "更新失败", "type": "main", "index": 0}]]},
            "更新失败": {"main": [[{"node": "输出结果", "type": "main", "index": 0}]]}
        },
        "settings": {"executionOrder": "v1", "saveManualExecutions": True},
        "staticData": None,
        "tags": [],
        "meta": {"templateCredsSetupCompleted": True}
    }


def create_wf_publish():
    """创建自动发布工作流"""
    return {
        "name": "WF-Publish",
        "nodes": [
            # 1. 工作流输入
            {
                "parameters": {},
                "id": "input",
                "name": "工作流输入",
                "type": "n8n-nodes-base.executeWorkflowTrigger",
                "typeVersion": 1,
                "position": [0, 300]
            },
            # 2. 提取内容
            {
                "parameters": {
                    "jsCode": """// 提取待发布内容
const records = $input.first().json.records || [];
if (records.length === 0) {
  return [{ json: { success: false, message: '无记录' } }];
}
return records.map(r => ({
  json: {
    record_id: r.record_id,
    title: r.fields?.ai_title || r.fields?.title || '',
    content: r.fields?.ai_content || r.fields?.content || '',
    images: r.fields?.ai_images || []
  }
}));"""
                },
                "id": "extract",
                "name": "提取内容",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [200, 300]
            },
            # 3. 锁定记录
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['CONTENT_TABLE_ID'],
                    "recordId": "={{ $json.record_id }}",
                    "fields": {
                        "status": "发布中",
                        "locked_at": "={{ $now.toISO() }}"
                    }
                },
                "id": "lock",
                "name": "锁定记录",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [400, 300],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 4. 获取有效账号
            {
                "parameters": {
                    "method": "GET",
                    "url": f"{ENV_CONFIG['SOCIAL_UPLOAD_URL']}/getValidAccounts",
                    "options": {"timeout": 10000}
                },
                "id": "get-accounts",
                "name": "获取账号",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [600, 300]
            },
            # 5. 检查账号
            {
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [
                            {
                                "id": "has-account",
                                "leftValue": "={{ $json.data?.length > 0 }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "equals"}
                            }
                        ],
                        "combinator": "and"
                    },
                    "options": {}
                },
                "id": "if-has-account",
                "name": "有账号?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [800, 300]
            },
            # 6. 准备发布请求
            {
                "parameters": {
                    "jsCode": """// 准备发布请求
const content = $('提取内容').item.json;
const accounts = $('获取账号').item.json.data || [];
const xhsAccount = accounts.find(a => a.type === 4) || accounts[0]; // type 4 = 小红书

return [{ json: {
  fileList: content.images,
  accountList: [xhsAccount?.id],
  type: 4, // 小红书
  title: content.title,
  tags: '',
  category: '',
  enableTimer: false,
  isDraft: false
} }];"""
                },
                "id": "prepare-publish",
                "name": "准备发布",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1000, 200]
            },
            # 7. 发布到小红书
            {
                "parameters": {
                    "method": "POST",
                    "url": f"{ENV_CONFIG['SOCIAL_UPLOAD_URL']}/postVideo",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Content-Type", "value": "application/json"}
                        ]
                    },
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify($json) }}",
                    "options": {"timeout": 120000}
                },
                "id": "post-video",
                "name": "发布内容",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [1200, 200]
            },
            # 8. 更新状态(成功)
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['CONTENT_TABLE_ID'],
                    "recordId": "={{ $('提取内容').item.json.record_id }}",
                    "fields": {
                        "status": "已发布",
                        "published_at": "={{ $now.toISO() }}",
                        "locked_at": ""
                    }
                },
                "id": "update-success",
                "name": "更新成功",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1400, 200],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 9. 无账号处理
            {
                "parameters": {
                    "jsCode": "return [{ json: { success: false, error: '无可用账号，请先登录' } }];"
                },
                "id": "no-account",
                "name": "无账号",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1000, 400]
            },
            # 10. 更新状态(失败)
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['CONTENT_TABLE_ID'],
                    "recordId": "={{ $('提取内容').item.json.record_id }}",
                    "fields": {
                        "status": "发布失败",
                        "error_message": "={{ $json.error || '发布失败' }}",
                        "locked_at": ""
                    }
                },
                "id": "update-failed",
                "name": "更新失败",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1200, 400],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 11. 输出结果
            {
                "parameters": {
                    "jsCode": """// 汇总结果
const results = $input.all();
let success = 0, failed = 0;

for (const item of results) {
  if (item.json.success !== false) success++;
  else failed++;
}

return [{ json: {
  action: 'publish',
  success: failed === 0,
  published: success,
  failed: failed
} }];"""
                },
                "id": "output",
                "name": "输出结果",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1600, 300]
            }
        ],
        "connections": {
            "工作流输入": {"main": [[{"node": "提取内容", "type": "main", "index": 0}]]},
            "提取内容": {"main": [[{"node": "锁定记录", "type": "main", "index": 0}]]},
            "锁定记录": {"main": [[{"node": "获取账号", "type": "main", "index": 0}]]},
            "获取账号": {"main": [[{"node": "有账号?", "type": "main", "index": 0}]]},
            "有账号?": {
                "main": [
                    [{"node": "准备发布", "type": "main", "index": 0}],
                    [{"node": "无账号", "type": "main", "index": 0}]
                ]
            },
            "准备发布": {"main": [[{"node": "发布内容", "type": "main", "index": 0}]]},
            "发布内容": {"main": [[{"node": "更新成功", "type": "main", "index": 0}]]},
            "更新成功": {"main": [[{"node": "输出结果", "type": "main", "index": 0}]]},
            "无账号": {"main": [[{"node": "更新失败", "type": "main", "index": 0}]]},
            "更新失败": {"main": [[{"node": "输出结果", "type": "main", "index": 0}]]}
        },
        "settings": {"executionOrder": "v1", "saveManualExecutions": True},
        "staticData": None,
        "tags": [],
        "meta": {"templateCredsSetupCompleted": True}
    }


def create_wf_generation():
    """创建AI内容生成工作流"""
    return {
        "name": "WF-Generation",
        "nodes": [
            # 1. 工作流输入
            {
                "parameters": {},
                "id": "input",
                "name": "工作流输入",
                "type": "n8n-nodes-base.executeWorkflowTrigger",
                "typeVersion": 1,
                "position": [0, 300]
            },
            # 2. 提取素材
            {
                "parameters": {
                    "jsCode": """// 提取素材记录
const records = $input.first().json.records || [];
if (records.length === 0) {
  return [{ json: { success: false, message: '无记录' } }];
}
return records.map(r => ({
  json: {
    record_id: r.record_id,
    title: r.fields?.title || '',
    content: r.fields?.content || '',
    note_type: r.fields?.note_type || '图文'
  }
}));"""
                },
                "id": "extract",
                "name": "提取素材",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [200, 300]
            },
            # 3. 锁定记录
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['SOURCE_TABLE_ID'],
                    "recordId": "={{ $json.record_id }}",
                    "fields": {
                        "status": "生成中",
                        "locked_at": "={{ $now.toISO() }}"
                    }
                },
                "id": "lock",
                "name": "锁定记录",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [400, 300],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 4. 生成大纲
            {
                "parameters": {
                    "method": "POST",
                    "url": f"{ENV_CONFIG['REDINK_API_URL']}/api/outline",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Content-Type", "value": "application/json"}
                        ]
                    },
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ topic: $('提取素材').item.json.title, original_content: $('提取素材').item.json.content }) }}",
                    "options": {"timeout": 60000}
                },
                "id": "outline",
                "name": "生成大纲",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [600, 300]
            },
            # 5. 检查大纲
            {
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [
                            {
                                "id": "has-outline",
                                "leftValue": "={{ $json.outline !== undefined }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "equals"}
                            }
                        ],
                        "combinator": "and"
                    },
                    "options": {}
                },
                "id": "if-outline",
                "name": "有大纲?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [800, 300]
            },
            # 6. 生成图片
            {
                "parameters": {
                    "method": "POST",
                    "url": f"{ENV_CONFIG['REDINK_API_URL']}/api/generate",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Content-Type", "value": "application/json"}
                        ]
                    },
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ outline: $json.outline, image_count: 3 }) }}",
                    "options": {"timeout": 180000}
                },
                "id": "generate",
                "name": "生成图片",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [1000, 200]
            },
            # 7. 处理生成结果
            {
                "parameters": {
                    "jsCode": """// 处理生成结果
const result = $input.first().json;
const sourceRecord = $('提取素材').item.json;

return [{ json: {
  source_id: sourceRecord.record_id,
  ai_title: result.title || sourceRecord.title,
  ai_content: result.content || '',
  ai_images: result.images || [],
  status: '待发布'
} }];"""
                },
                "id": "process",
                "name": "处理结果",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1200, 200]
            },
            # 8. 创建Content记录
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "createRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['CONTENT_TABLE_ID'],
                    "fields": "={{ $json }}"
                },
                "id": "create-content",
                "name": "创建Content",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1400, 200],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 9. 更新Source(成功)
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['SOURCE_TABLE_ID'],
                    "recordId": "={{ $('提取素材').item.json.record_id }}",
                    "fields": {
                        "status": "已生成",
                        "locked_at": ""
                    }
                },
                "id": "update-success",
                "name": "更新成功",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1600, 200],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 10. 处理错误
            {
                "parameters": {
                    "jsCode": "return [{ json: { success: false, record_id: $('提取素材').item.json.record_id, error: '生成失败' } }];"
                },
                "id": "handle-error",
                "name": "处理错误",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1000, 400]
            },
            # 11. 更新Source(失败)
            {
                "parameters": {
                    "resource": "bitable",
                    "operation": "updateRecord",
                    "appToken": ENV_CONFIG['LARK_APP_TOKEN'],
                    "tableId": ENV_CONFIG['SOURCE_TABLE_ID'],
                    "recordId": "={{ $json.record_id }}",
                    "fields": {
                        "status": "生成失败",
                        "error_message": "={{ $json.error }}",
                        "locked_at": ""
                    }
                },
                "id": "update-failed",
                "name": "更新失败",
                "type": "n8n-nodes-feishu-lark.feishuLark",
                "typeVersion": 1,
                "position": [1200, 400],
                "credentials": {
                    "feishuLarkApi": {"id": "feishu-cred", "name": "飞书凭证"}
                }
            },
            # 12. 输出结果
            {
                "parameters": {
                    "jsCode": """// 汇总结果
const results = $input.all();
let success = 0, failed = 0;

for (const item of results) {
  if (item.json.success !== false) success++;
  else failed++;
}

return [{ json: {
  action: 'generation',
  success: failed === 0,
  generated: success,
  failed: failed
} }];"""
                },
                "id": "output",
                "name": "输出结果",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1800, 300]
            }
        ],
        "connections": {
            "工作流输入": {"main": [[{"node": "提取素材", "type": "main", "index": 0}]]},
            "提取素材": {"main": [[{"node": "锁定记录", "type": "main", "index": 0}]]},
            "锁定记录": {"main": [[{"node": "生成大纲", "type": "main", "index": 0}]]},
            "生成大纲": {"main": [[{"node": "有大纲?", "type": "main", "index": 0}]]},
            "有大纲?": {
                "main": [
                    [{"node": "生成图片", "type": "main", "index": 0}],
                    [{"node": "处理错误", "type": "main", "index": 0}]
                ]
            },
            "生成图片": {"main": [[{"node": "处理结果", "type": "main", "index": 0}]]},
            "处理结果": {"main": [[{"node": "创建Content", "type": "main", "index": 0}]]},
            "创建Content": {"main": [[{"node": "更新成功", "type": "main", "index": 0}]]},
            "更新成功": {"main": [[{"node": "输出结果", "type": "main", "index": 0}]]},
            "处理错误": {"main": [[{"node": "更新失败", "type": "main", "index": 0}]]},
            "更新失败": {"main": [[{"node": "输出结果", "type": "main", "index": 0}]]}
        },
        "settings": {"executionOrder": "v1", "saveManualExecutions": True},
        "staticData": None,
        "tags": [],
        "meta": {"templateCredsSetupCompleted": True}
    }


def save_workflow(workflow, output_dir):
    """保存工作流到JSON文件"""
    filename = f"{workflow['name']}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)

    print(f"✅ 已保存: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description='生成 XHS n8n 工作流')
    parser.add_argument('--output', '-o', default='./n8n-workflows/', help='输出目录')
    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)

    print("=" * 50)
    print("XHS 自动化运营系统 - n8n 工作流生成")
    print("=" * 50)
    print(f"输出目录: {args.output}")
    print(f"生成时间: {datetime.now().isoformat()}")
    print("-" * 50)

    # 生成工作流
    workflows = [
        ("WF-Main", create_wf_main),
        ("WF-Discovery", create_wf_discovery),
        ("WF-Generation", create_wf_generation),
        ("WF-Publish", create_wf_publish),
    ]

    saved_files = []
    for name, creator in workflows:
        print(f"\n生成 {name}...")
        workflow = creator()
        filepath = save_workflow(workflow, args.output)
        saved_files.append(filepath)

    print("\n" + "=" * 50)
    print("生成完成！")
    print(f"共生成 {len(saved_files)} 个工作流")
    print("-" * 50)
    print("\n导入命令:")
    for f in saved_files:
        print(f"  docker exec n8n n8n import:workflow --input=/home/node/.n8n/{os.path.basename(f)}")


if __name__ == "__main__":
    main()
