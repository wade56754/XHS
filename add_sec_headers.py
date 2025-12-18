#!/usr/bin/env python3
"""Add sec-ch-ua headers to xhs_client.py for search API compatibility"""

# Read the file
with open('/app/xhs_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the current headers definition and replace with expanded version
old_headers = """        self._headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Origin': 'https://www.xiaohongshu.com',
            'Referer': 'https://www.xiaohongshu.com/',
            'Content-Type': 'application/json;charset=UTF-8',
        }"""

new_headers = """        self._headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Origin': 'https://www.xiaohongshu.com',
            'Referer': 'https://www.xiaohongshu.com/',
            'Content-Type': 'application/json;charset=UTF-8',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }"""

if old_headers in content:
    content = content.replace(old_headers, new_headers)
    with open('/app/xhs_client.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully added sec-ch-ua headers to xhs_client.py")
else:
    print("ERROR: Could not find headers block to replace")
    # Try to find what's there
    import re
    match = re.search(r'self\._headers = headers or \{[^}]+\}', content, re.DOTALL)
    if match:
        print(f"Found headers block:\n{match.group()[:500]}")
    else:
        print("No headers block found at all")
