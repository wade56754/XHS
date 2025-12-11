#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书多维表格通用客户端
功能：Token 管理、批量创建记录、查询记录
用于 N8N 工作流 / Python 脚本联动

使用示例:
    from lark_client import LarkClient

    client = LarkClient()

    # 创建记录
    records = [{"title": "测试", "status": "DRAFT"}]
    result = client.create_records("tblContentRecords", records)

    # 查询记录
    records = client.query_records("tblContentRecords", filter="status='DRAFT'")
"""

import os
import time
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class LarkClient:
    """飞书多维表格 API 客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        app_token: Optional[str] = None
    ):
        """
        初始化客户端

        Args:
            app_id: 飞书应用 ID，默认从环境变量 LARK_APP_ID 读取
            app_secret: 飞书应用密钥，默认从环境变量 LARK_APP_SECRET 读取
            app_token: 多维表格 App Token，默认从环境变量 LARK_APP_TOKEN 读取
        """
        self.app_id = app_id or os.environ.get('LARK_APP_ID')
        self.app_secret = app_secret or os.environ.get('LARK_APP_SECRET')
        self.app_token = app_token or os.environ.get('LARK_APP_TOKEN')

        if not all([self.app_id, self.app_secret, self.app_token]):
            raise ValueError("Missing required credentials. Set LARK_APP_ID, LARK_APP_SECRET, LARK_APP_TOKEN")

        self._token: Optional[str] = None
        self._token_expires: float = 0

    def _get_token(self) -> str:
        """获取或刷新 tenant_access_token"""
        # 检查缓存的 token 是否有效（提前 60 秒刷新）
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        response = requests.post(url, json=payload, timeout=10)
        data = response.json()

        if data.get('code') != 0:
            raise Exception(f"获取飞书 Token 失败: {data}")

        self._token = data['tenant_access_token']
        self._token_expires = time.time() + data['expire']
        logger.debug("Token 刷新成功")

        return self._token

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """发送 API 请求"""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json"
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params,
            timeout=30
        )

        result = response.json()

        if result.get('code') != 0:
            logger.error(f"API 请求失败: {result}")
            raise Exception(f"飞书 API 错误: {result.get('msg', 'Unknown error')}")

        return result

    # ==================== 记录操作 ====================

    def create_records(
        self,
        table_id: str,
        records: List[Dict[str, Any]],
        app_token: Optional[str] = None
    ) -> Dict:
        """
        批量创建记录

        Args:
            table_id: 表格 ID
            records: 记录列表，每条记录是字段名到值的映射
            app_token: 可选，覆盖默认的 app_token

        Returns:
            API 响应结果

        Example:
            records = [
                {"title": "标题1", "ai_score": 85, "status": "DRAFT"},
                {"title": "标题2", "ai_score": 90, "status": "AI_REVIEWED"}
            ]
            result = client.create_records("tblXXX", records)
        """
        app_token = app_token or self.app_token
        endpoint = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"

        payload = {
            "records": [{"fields": record} for record in records]
        }

        result = self._request("POST", endpoint, data=payload)
        logger.info(f"创建 {len(records)} 条记录成功")

        return result

    def create_record(
        self,
        table_id: str,
        record: Dict[str, Any],
        app_token: Optional[str] = None
    ) -> Dict:
        """
        创建单条记录

        Args:
            table_id: 表格 ID
            record: 字段名到值的映射
            app_token: 可选，覆盖默认的 app_token

        Returns:
            API 响应结果
        """
        app_token = app_token or self.app_token
        endpoint = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records"

        payload = {"fields": record}

        result = self._request("POST", endpoint, data=payload)
        logger.info(f"创建记录成功: {result.get('data', {}).get('record', {}).get('record_id')}")

        return result

    def query_records(
        self,
        table_id: str,
        filter: Optional[str] = None,
        sort: Optional[List[Dict]] = None,
        page_size: int = 100,
        page_token: Optional[str] = None,
        app_token: Optional[str] = None
    ) -> Dict:
        """
        查询记录

        Args:
            table_id: 表格 ID
            filter: 筛选条件，如 "status='DRAFT'"
            sort: 排序规则，如 [{"field_name": "created_at", "desc": True}]
            page_size: 每页数量（最大 500）
            page_token: 分页标记
            app_token: 可选，覆盖默认的 app_token

        Returns:
            API 响应结果，包含 items 和 page_token

        Example:
            result = client.query_records(
                "tblXXX",
                filter="status='AI_REVIEWED'",
                sort=[{"field_name": "ai_score", "desc": True}],
                page_size=20
            )
            records = result['data']['items']
        """
        app_token = app_token or self.app_token
        endpoint = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"

        payload = {
            "page_size": min(page_size, 500)
        }

        if filter:
            payload["filter"] = {"conditions": [{"field_name": "status", "operator": "is", "value": [filter.split("=")[1].strip("'")] if "=" in filter else []}]}
            # 简化处理，实际应根据飞书 API 文档构建复杂筛选条件
            # 这里使用原始 filter 字符串
            payload["filter"] = filter

        if sort:
            payload["sort"] = sort

        if page_token:
            payload["page_token"] = page_token

        result = self._request("POST", endpoint, data=payload)
        items = result.get('data', {}).get('items', [])
        logger.info(f"查询到 {len(items)} 条记录")

        return result

    def update_record(
        self,
        table_id: str,
        record_id: str,
        fields: Dict[str, Any],
        app_token: Optional[str] = None
    ) -> Dict:
        """
        更新单条记录

        Args:
            table_id: 表格 ID
            record_id: 记录 ID
            fields: 要更新的字段
            app_token: 可选，覆盖默认的 app_token

        Returns:
            API 响应结果
        """
        app_token = app_token or self.app_token
        endpoint = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"

        payload = {"fields": fields}

        result = self._request("PUT", endpoint, data=payload)
        logger.info(f"更新记录成功: {record_id}")

        return result

    def delete_record(
        self,
        table_id: str,
        record_id: str,
        app_token: Optional[str] = None
    ) -> Dict:
        """
        删除单条记录

        Args:
            table_id: 表格 ID
            record_id: 记录 ID
            app_token: 可选，覆盖默认的 app_token

        Returns:
            API 响应结果
        """
        app_token = app_token or self.app_token
        endpoint = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"

        result = self._request("DELETE", endpoint)
        logger.info(f"删除记录成功: {record_id}")

        return result

    # ==================== 便捷方法 ====================

    def get_all_records(
        self,
        table_id: str,
        filter: Optional[str] = None,
        app_token: Optional[str] = None
    ) -> List[Dict]:
        """
        获取所有记录（自动分页）

        Args:
            table_id: 表格 ID
            filter: 筛选条件
            app_token: 可选，覆盖默认的 app_token

        Returns:
            所有记录列表
        """
        all_records = []
        page_token = None

        while True:
            result = self.query_records(
                table_id=table_id,
                filter=filter,
                page_size=500,
                page_token=page_token,
                app_token=app_token
            )

            items = result.get('data', {}).get('items', [])
            all_records.extend(items)

            page_token = result.get('data', {}).get('page_token')
            if not page_token:
                break

        logger.info(f"共获取 {len(all_records)} 条记录")
        return all_records

    def log_event(
        self,
        event_type: str,
        level: str,
        message: str,
        workflow_id: str = "",
        workflow_run_id: str = "",
        node_name: str = "",
        context: Optional[Dict] = None,
        error: Optional[Dict] = None,
        table_id: Optional[str] = None
    ) -> Dict:
        """
        写入执行日志（便捷方法）

        Args:
            event_type: 事件类型（见枚举）
            level: 日志级别（DEBUG/INFO/WARN/ERROR/FATAL）
            message: 日志消息
            workflow_id: 工作流 ID
            workflow_run_id: 执行 ID
            node_name: 节点名称
            context: 上下文数据
            error: 错误信息
            table_id: 日志表 ID，默认从环境变量读取

        Returns:
            API 响应结果
        """
        table_id = table_id or os.environ.get('LARK_TABLE_LOGS', 'tblExecutionLogs')

        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "workflow_id": workflow_id,
            "workflow_run_id": workflow_run_id,
            "node_name": node_name,
            "event_type": event_type,
            "message": message,
            "context": json.dumps(context, ensure_ascii=False) if context else "",
            "error": json.dumps(error, ensure_ascii=False) if error else ""
        }

        return self.create_record(table_id, record)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 确保设置了环境变量
    # export LARK_APP_ID=cli_xxx
    # export LARK_APP_SECRET=xxx
    # export LARK_APP_TOKEN=xxx

    try:
        client = LarkClient()

        # 示例 1: 创建热点记录
        print("=== 示例 1: 创建热点记录 ===")
        hot_topics = [
            {
                "title": "AI 自动化工具推荐",
                "hot_value": 12345,
                "source": "weibo",
                "fetched_at": datetime.utcnow().isoformat() + "Z"
            }
        ]
        # result = client.create_records("tblHotTopics", hot_topics)
        # print(f"创建结果: {result}")
        print("(跳过实际调用，仅示例)")

        # 示例 2: 查询记录
        print("\n=== 示例 2: 查询记录 ===")
        # result = client.query_records("tblContentRecords", filter="status='DRAFT'")
        # print(f"查询结果: {result}")
        print("(跳过实际调用，仅示例)")

        # 示例 3: 写入日志
        print("\n=== 示例 3: 写入日志 ===")
        # client.log_event(
        #     event_type="WORKFLOW_START",
        #     level="INFO",
        #     message="内容生成工作流启动",
        #     workflow_id="content_generator_v1",
        #     workflow_run_id="exec_12345",
        #     context={"trigger_type": "manual"}
        # )
        print("(跳过实际调用，仅示例)")

        print("\n=== 客户端初始化成功 ===")

    except ValueError as e:
        print(f"配置错误: {e}")
        print("请设置环境变量: LARK_APP_ID, LARK_APP_SECRET, LARK_APP_TOKEN")
    except Exception as e:
        print(f"运行错误: {e}")
