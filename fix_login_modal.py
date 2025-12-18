#!/usr/bin/env python3
"""修复登录弹窗问题"""

# 读取文件
with open('/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在人工搜索的导航后添加关闭登录弹窗的代码
old_navigate = '''if not search_success:
            # 备用方案：直接导航到搜索结果页
            print("DEBUG HUMAN SEARCH: 搜索框输入失败，使用直接导航")
            import urllib.parse
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_search_result_notes"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))'''

new_navigate = '''if not search_success:
            # 备用方案：直接导航到搜索结果页
            print("DEBUG HUMAN SEARCH: 搜索框输入失败，使用直接导航")
            import urllib.parse
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_search_result_notes"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))

        # 关闭可能出现的登录弹窗
        print("DEBUG HUMAN SEARCH: 检查登录弹窗...")
        try:
            # 方法1：点击关闭按钮
            close_btn = await page.query_selector('.close-button, .login-close, .reds-modal .icon-btn-wrapper')
            if close_btn:
                await close_btn.click()
                print("DEBUG HUMAN SEARCH: 点击关闭按钮")
                await asyncio.sleep(1)

            # 方法2：按 ESC 键
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.5)

            # 方法3：点击遮罩层外部
            await page.mouse.click(10, 10)
            await asyncio.sleep(0.5)

            # 方法4：直接移除弹窗元素
            await page.evaluate("""() => {
                // 移除登录弹窗
                const modals = document.querySelectorAll('.login-modal, .reds-modal, [class*="login-container"]');
                modals.forEach(m => m.remove());
                // 移除遮罩层
                const masks = document.querySelectorAll('.reds-mask, [class*="mask"]');
                masks.forEach(m => m.remove());
                // 恢复页面滚动
                document.body.style.overflow = 'auto';
            }""")
            print("DEBUG HUMAN SEARCH: 已移除弹窗元素")
            await asyncio.sleep(1)

        except Exception as e:
            print(f"DEBUG HUMAN SEARCH: 关闭弹窗时出错: {e}")'''

if old_navigate in content:
    content = content.replace(old_navigate, new_navigate)
    print("已添加关闭登录弹窗逻辑")
else:
    print("WARNING: 未找到导航代码块")

# 更新提取选择器，使用更通用的方式
old_extract_start = '''# 6. 提取搜索结果
        extract_js = """() => {
            const results = [];
            console.log('开始提取搜索结果...');

            // 小红书搜索结果页的实际选择器
            const noteCards = document.querySelectorAll(
                '.note-item, ' +                    // 笔记卡片
                'section[class*="note"], ' +        // section 笔记
                '.feeds-container section, ' +      // feeds 容器内的 section
                '.search-result-container section, ' +  // 搜索结果容器
                'a[href*="/explore/"][class*="cover"], ' +  // 封面链接
                '.note-list section, ' +            // 笔记列表
                '[data-v-][class*="note"]'          // Vue 组件笔记
            );

            console.log('找到卡片数量:', noteCards.length);'''

new_extract_start = '''# 6. 提取搜索结果
        extract_js = """() => {
            const results = [];
            console.log('开始提取搜索结果...');

            // 更通用的选择器 - 查找所有包含 /explore/ 或 /discovery/ 链接的元素
            let noteCards = [];

            // 方法1：查找所有笔记链接
            const allLinks = document.querySelectorAll('a[href*="/explore/"], a[href*="/discovery/item/"]');
            console.log('找到链接数量:', allLinks.length);

            // 获取链接的父容器作为卡片
            allLinks.forEach(link => {
                // 向上查找最近的 section 或有类名的 div
                let card = link.closest('section') || link.closest('div[class]') || link.parentElement;
                if (card && !noteCards.includes(card)) {
                    noteCards.push(card);
                }
            });

            // 方法2：如果上面没找到，尝试其他选择器
            if (noteCards.length === 0) {
                noteCards = Array.from(document.querySelectorAll(
                    'section.note-item, ' +
                    '.note-item, ' +
                    '[class*="note-card"], ' +
                    '.feeds-page section'
                ));
            }

            console.log('找到卡片数量:', noteCards.length);'''

if old_extract_start in content:
    content = content.replace(old_extract_start, new_extract_start)
    print("已更新提取选择器")
else:
    print("WARNING: 未找到提取代码开头")

# 写回文件
with open('/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n登录弹窗修复完成！")
