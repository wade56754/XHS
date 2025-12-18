#!/usr/bin/env python3
"""添加浏览器预热功能，模拟真实用户行为"""

# 读取文件
with open('/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加预热函数（在 init_browser 函数之后）
warmup_function = """

# ============== 浏览器预热功能 ==============
import random

async def warmup_browser(page, browser_context):
    \"\"\"
    模拟真实用户浏览行为，降低被风控的概率
    在搜索前调用此函数进行"预热"
    \"\"\"
    print("DEBUG WARMUP: 开始浏览器预热...")

    try:
        # 1. 确保在首页
        current_url = page.url
        if "explore" not in current_url:
            print("DEBUG WARMUP: 导航到首页...")
            await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))

        # 2. 模拟滚动浏览
        print("DEBUG WARMUP: 模拟滚动浏览...")
        for i in range(3):
            scroll_distance = random.randint(300, 600)
            await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            await asyncio.sleep(random.uniform(1, 2.5))

        # 3. 滚动回顶部
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(random.uniform(1, 2))

        # 4. 模拟鼠标移动（随机位置）
        print("DEBUG WARMUP: 模拟鼠标移动...")
        for _ in range(2):
            x = random.randint(100, 800)
            y = random.randint(100, 500)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.3, 0.8))

        # 5. 再次滚动
        await page.evaluate(f"window.scrollBy(0, {random.randint(200, 400)})")
        await asyncio.sleep(random.uniform(1.5, 3))

        print("DEBUG WARMUP: 预热完成！")
        return True

    except Exception as e:
        print(f"DEBUG WARMUP ERROR: {e}")
        return False


async def simulate_search_input(page, keyword):
    \"\"\"
    模拟在搜索框中输入关键词的行为
    \"\"\"
    print(f"DEBUG SIMULATE: 模拟搜索输入: {keyword}")

    try:
        # 1. 点击搜索框
        search_box = await page.query_selector('input[placeholder*="搜索"]')
        if not search_box:
            search_box = await page.query_selector('.search-input')
        if not search_box:
            search_box = await page.query_selector('input[type="search"]')

        if search_box:
            await search_box.click()
            await asyncio.sleep(random.uniform(0.5, 1))

            # 2. 逐字符输入（模拟打字）
            for char in keyword:
                await search_box.type(char, delay=random.randint(50, 150))

            await asyncio.sleep(random.uniform(0.5, 1.5))

            # 3. 按回车搜索
            await page.keyboard.press('Enter')
            await asyncio.sleep(random.uniform(2, 4))

            print("DEBUG SIMULATE: 搜索输入完成")
            return True
        else:
            print("DEBUG SIMULATE: 未找到搜索框")
            return False

    except Exception as e:
        print(f"DEBUG SIMULATE ERROR: {e}")
        return False

# ============== 预热功能结束 ==============

"""

# 找到 init_browser 函数结束的位置，在其后添加预热函数
# 查找 "async def init_xhs_client" 作为插入点
insert_marker = "async def init_xhs_client"

if insert_marker in content and "async def warmup_browser" not in content:
    content = content.replace(insert_marker, warmup_function + insert_marker)
    print("已添加 warmup_browser 和 simulate_search_input 函数")
else:
    if "async def warmup_browser" in content:
        print("warmup_browser 函数已存在")
    else:
        print("ERROR: 未找到插入点")

# 写回文件
with open('/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("预热功能添加完成！")
