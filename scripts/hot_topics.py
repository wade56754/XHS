#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点抓取脚本 - MVP 简化版
功能：抓取微博热搜、知乎热榜，写入飞书多维表格
部署：Crontab 每 2 小时执行一次
"""

import os
import json
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict

# 环境变量
LARK_APP_ID = os.environ.get('LARK_APP_ID')
LARK_APP_SECRET = os.environ.get('LARK_APP_SECRET')
LARK_APP_TOKEN = os.environ.get('LARK_APP_TOKEN')
LARK_TABLE_HOT_TOPICS = os.environ.get('LARK_TABLE_HOT_TOPICS', 'tblHotTopics')


class LarkClient:
    """飞书 API 客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_expires = 0

    def get_token(self) -> str:
        """获取 tenant_access_token"""
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret}
        )
        data = resp.json()
        if data.get('code') != 0:
            raise Exception(f"获取飞书 Token 失败: {data}")

        self._token = data['tenant_access_token']
        self._token_expires = time.time() + data['expire']
        return self._token

    def add_records(self, app_token: str, table_id: str, records: List[Dict]):
        """批量添加记录"""
        token = self.get_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"

        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={"records": [{"fields": r} for r in records]}
        )
        return resp.json()


def fetch_weibo_hot() -> List[Dict]:
    """
    抓取微博热搜（公开 API，无需登录）
    返回前 20 条热搜
    """
    url = "https://weibo.com/ajax/side/hotSearch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://weibo.com/"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        hot_topics = []
        for item in data.get('data', {}).get('realtime', [])[:20]:
            hot_topics.append({
                "title": item.get('word', ''),
                "hot_value": item.get('num', 0),
                "category": item.get('category', '综合'),
                "url": f"https://s.weibo.com/weibo?q=%23{item.get('word', '')}%23",
                "source": "weibo"
            })

        return hot_topics
    except Exception as e:
        print(f"[ERROR] 抓取微博热搜失败: {e}")
        return []


def fetch_zhihu_hot() -> List[Dict]:
    """
    抓取知乎热榜（公开 API）
    """
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        hot_topics = []
        for item in data.get('data', [])[:20]:
            target = item.get('target', {})
            hot_value_str = item.get('detail_text', '0')
            # 转换热度值
            if '万' in hot_value_str:
                hot_value = int(float(hot_value_str.replace('万热度', '').replace(' ', '')) * 10000)
            else:
                hot_value = int(hot_value_str.replace('热度', '').replace(' ', '') or 0)

            hot_topics.append({
                "title": target.get('title', ''),
                "hot_value": hot_value,
                "category": "知乎",
                "url": f"https://www.zhihu.com/question/{target.get('id', '')}",
                "source": "zhihu"
            })

        return hot_topics
    except Exception as e:
        print(f"[ERROR] 抓取知乎热榜失败: {e}")
        return []


def main():
    """主函数"""
    print(f"[{datetime.now().isoformat()}] 开始抓取热点...")

    # 1. 抓取热点
    all_topics = []
    all_topics.extend(fetch_weibo_hot())
    all_topics.extend(fetch_zhihu_hot())

    if not all_topics:
        print("[WARN] 未抓取到任何热点")
        return

    print(f"[INFO] 共抓取 {len(all_topics)} 条热点")

    # 2. 准备写入飞书的数据
    fetch_time = datetime.now(timezone.utc).isoformat()
    records = []
    for topic in all_topics:
        records.append({
            "title": topic["title"],
            "hot_value": topic["hot_value"],
            "category": topic["category"],
            "url": topic["url"],
            "source": topic["source"],
            "fetched_at": fetch_time
        })

    # 3. 写入飞书
    if LARK_APP_ID and LARK_APP_SECRET and LARK_APP_TOKEN:
        client = LarkClient(LARK_APP_ID, LARK_APP_SECRET)
        result = client.add_records(LARK_APP_TOKEN, LARK_TABLE_HOT_TOPICS, records)

        if result.get('code') == 0:
            print(f"[OK] 成功写入 {len(records)} 条记录到飞书")
        else:
            print(f"[ERROR] 写入飞书失败: {result}")
    else:
        # 本地测试：输出到文件
        output_file = '/tmp/hot_topics.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 飞书配置缺失，已输出到 {output_file}")


if __name__ == "__main__":
    main()
