#!/usr/bin/env python3
"""
修复笔记详情 API TypeError 问题

问题: get_note_by_id() 被调用时传入了不存在的 xsec_source 参数
原因: main.py 中调用传了 xsec_source="pc_search"，但 xhs_client.py 中该方法没有这个参数
修复: 移除 xsec_source 参数

使用方法:
1. 复制到服务器: scp fix_note_detail.py wade@124.221.251.8:/home/wade/
2. 进入容器执行: docker exec media-crawler-api python3 /fix_note_detail.py
3. 重启容器: docker restart media-crawler-api
"""

import re

def fix_note_detail():
    # 读取 main.py
    with open('/app/main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除 xsec_source 参数
    old_pattern = r'result = await xhs_client\.get_note_by_id\(\s*note_id=note_id,\s*xsec_source="pc_search",\s*xsec_token=xsec_token,\s*\)'
    new_code = '''result = await xhs_client.get_note_by_id(
                note_id=note_id,
                xsec_token=xsec_token,
            )'''

    if 'xsec_source="pc_search"' in content:
        content = re.sub(old_pattern, new_code, content)
        with open('/app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("已移除 xsec_source 参数")
    else:
        print("xsec_source 参数已被移除，无需修复")

if __name__ == '__main__':
    fix_note_detail()
