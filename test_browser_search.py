#!/usr/bin/env python3
"""Test if browser can perform search directly via page navigation"""

import asyncio
import sys
sys.path.insert(0, '/app')

from main import browser_context, page

async def test_browser_search():
    if not page:
        print("ERROR: page is None")
        return

    # Try to navigate to search page directly
    print(f"Current URL: {page.url}")

    # Navigate to search URL
    search_url = "https://www.xiaohongshu.com/search_result?keyword=%E7%BE%8E%E9%A3%9F&source=web_search_result_notes"
    print(f"Navigating to: {search_url}")

    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        print(f"Final URL: {page.url}")
        title = await page.title()
        print(f"Title: {title}")

        # Check for search results
        content = await page.content()
        if "安全限制" in content:
            print("BLOCKED: Security restriction page")
        elif "搜索结果" in content or "相关笔记" in content:
            print("SUCCESS: Search results page loaded")
        elif "登录" in content:
            print("LOGIN REQUIRED: Redirected to login")
        else:
            print(f"UNKNOWN: Content preview: {content[:500]}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_browser_search())
