#!/usr/bin/env python3
"""Fix search_id generation to match MediaCrawler implementation"""

# Read the file
with open('/app/xhs_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add base36 encoding functions after imports
import_section_end = "from tenacity import retry, stop_after_attempt, wait_fixed"
base36_code = '''from tenacity import retry, stop_after_attempt, wait_fixed
import random


def base36encode(number: int) -> str:
    """Convert integer to base36 string"""
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if number == 0:
        return '0'

    sign = ''
    if number < 0:
        sign = '-'
        number = -number

    result = ''
    while number:
        number, remainder = divmod(number, 36)
        result = alphabet[remainder] + result

    return sign + result


def get_search_id() -> str:
    """Generate search_id in XHS format: base36(timestamp << 64 + random)"""
    e = int(time.time() * 1000) << 64
    t = int(random.uniform(0, 2147483646))
    return base36encode(e + t)'''

if import_section_end in content and 'def base36encode' not in content:
    content = content.replace(import_section_end, base36_code)
    print("Added base36encode and get_search_id functions")
else:
    if 'def base36encode' in content:
        print("base36encode already exists")
    else:
        print("ERROR: Could not find import section")

# Update get_note_by_keyword to use new search_id format
old_search_id = "        search_id = hashlib.md5(f'{keyword}{time.time()}'.encode()).hexdigest()[:16]"
new_search_id = "        search_id = get_search_id()"

if old_search_id in content:
    content = content.replace(old_search_id, new_search_id)
    print("Updated search_id generation in get_note_by_keyword")
else:
    # Try to find current implementation
    if "search_id = get_search_id()" in content:
        print("search_id already using get_search_id()")
    else:
        print("WARNING: Could not find search_id generation to replace")
        # Search for what's there
        import re
        match = re.search(r'search_id = .*', content)
        if match:
            print(f"Found: {match.group()}")

# Write back
with open('/app/xhs_client.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch complete")
