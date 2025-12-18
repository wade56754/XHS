#!/usr/bin/env python3
"""修复人工搜索：关闭弹窗 + 更新选择器"""

# 读取文件
with open('/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 更新 warmup_browser 函数，添加关闭弹窗逻辑
old_warmup_start = '''async def warmup_browser(page, browser_context):
    """
    模拟真实用户浏览行为，降低被风控的概率
    在搜索前调用此函数进行"预热"
    """
    print("DEBUG WARMUP: 开始浏览器预热...")

    try:
        # 1. 确保在首页'''

new_warmup_start = '''async def warmup_browser(page, browser_context):
    """
    模拟真实用户浏览行为，降低被风控的概率
    在搜索前调用此函数进行"预热"
    """
    print("DEBUG WARMUP: 开始浏览器预热...")

    try:
        # 0. 先关闭可能存在的弹窗
        print("DEBUG WARMUP: 检查并关闭弹窗...")
        try:
            # 尝试关闭各种可能的弹窗
            close_selectors = [
                '.reds-mask',  # 遮罩层
                '[aria-label="关闭"]',
                '.close-btn',
                '.modal-close',
                'button:has-text("关闭")',
                'button:has-text("取消")',
                '.login-close',
            ]
            for selector in close_selectors:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        await el.click(timeout=1000)
                        print(f"DEBUG WARMUP: 关闭了弹窗: {selector}")
                        await asyncio.sleep(0.5)
                except:
                    pass
            # 按 ESC 键尝试关闭弹窗
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.3)
        except:
            pass

        # 1. 确保在首页'''

if old_warmup_start in content:
    content = content.replace(old_warmup_start, new_warmup_start)
    print("已更新 warmup_browser 函数添加关闭弹窗逻辑")
else:
    print("WARNING: 未找到 warmup_browser 函数开头")

# 2. 更新搜索结果提取 JavaScript - 使用更准确的选择器
old_extract = '''extract_js = """() => {
            const results = [];
            // 尝试多种选择器
            const noteCards = document.querySelectorAll('section.note-item, div[data-note-id], .note-card, a[href*="/explore/"], a[href*="/search_result/"]');'''

new_extract = '''extract_js = """() => {
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

if old_extract in content:
    content = content.replace(old_extract, new_extract)
    print("已更新搜索结果提取选择器（第一部分）")
else:
    print("WARNING: 未找到提取代码第一部分")

# 3. 更新提取逻辑的详细部分
old_extract_detail = '''noteCards.forEach((card, index) => {
                if (index >= """ + str(limit) + """) return;

                let noteId = card.getAttribute('data-note-id');
                if (!noteId) {
                    const href = card.href || card.querySelector('a')?.href || '';
                    const match = href.match(/explore\\/([a-f0-9]+)/) || href.match(/item\\/([a-f0-9]+)/);
                    noteId = match ? match[1] : null;
                }

                const title = card.querySelector('.title, .note-title, h3, .desc')?.textContent?.trim() ||
                              card.querySelector('span')?.textContent?.trim();
                const author = card.querySelector('.author, .user-name, .nickname, .name')?.textContent?.trim();
                const likes = card.querySelector('.like-count, .likes, .like-wrapper span, .count')?.textContent?.trim();
                const cover = card.querySelector('img')?.src;

                if (noteId || title) {
                    results.push({
                        note_id: noteId || null,
                        title: title || '无标题',
                        author: author || '未知',
                        likes: likes || '0',
                        cover: cover || null
                    });
                }
            });'''

new_extract_detail = '''noteCards.forEach((card, index) => {
                if (index >= """ + str(limit) + """) return;

                // 获取笔记 ID - 多种方式尝试
                let noteId = card.getAttribute('data-note-id') || card.getAttribute('data-id');
                if (!noteId) {
                    // 从链接中提取
                    const allLinks = card.querySelectorAll('a[href]');
                    for (const link of allLinks) {
                        const href = link.href || '';
                        const match = href.match(/explore\\/([a-f0-9]{24})/) ||
                                      href.match(/discovery\\/item\\/([a-f0-9]{24})/) ||
                                      href.match(/note\\/([a-f0-9]{24})/);
                        if (match) {
                            noteId = match[1];
                            break;
                        }
                    }
                }

                // 获取标题 - 多种选择器
                const title = card.querySelector('.title, .note-title, .desc, .content, span.title')?.textContent?.trim() ||
                              card.querySelector('a .info span, a span')?.textContent?.trim() ||
                              card.querySelector('p, span')?.textContent?.trim()?.substring(0, 50);

                // 获取作者
                const author = card.querySelector('.author, .user-name, .nickname, .name, .user span')?.textContent?.trim() ||
                               card.querySelector('[class*="author"], [class*="user"]')?.textContent?.trim();

                // 获取点赞数
                const likes = card.querySelector('.like-count, .likes, .count, [class*="like"] span')?.textContent?.trim() ||
                              card.querySelector('.engagements span, .interactions span')?.textContent?.trim();

                // 获取封面图
                const cover = card.querySelector('img[src*="xhscdn"], img[src*="xiaohongshu"], img')?.src;

                // 只要有 ID 或标题就添加
                if (noteId || (title && title.length > 2)) {
                    results.push({
                        note_id: noteId || null,
                        title: title || '无标题',
                        author: author || '未知',
                        likes: likes || '0',
                        cover: cover || null,
                        raw_html: card.outerHTML?.substring(0, 200)  // 调试用
                    });
                }
            });'''

if old_extract_detail in content:
    content = content.replace(old_extract_detail, new_extract_detail)
    print("已更新搜索结果提取逻辑")
else:
    print("WARNING: 未找到提取代码详细部分")

# 4. 添加更多等待时间，确保页面完全加载
old_wait = '''# 4. 等待搜索结果加载
        await asyncio.sleep(random.uniform(2, 4))'''

new_wait = '''# 4. 等待搜索结果加载（增加等待时间）
        print("DEBUG HUMAN SEARCH: 等待页面加载...")
        await asyncio.sleep(random.uniform(3, 5))

        # 滚动页面触发懒加载
        await page.evaluate("window.scrollBy(0, 500)")
        await asyncio.sleep(random.uniform(1, 2))
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(random.uniform(1, 2))'''

if old_wait in content:
    content = content.replace(old_wait, new_wait)
    print("已增加页面加载等待时间")
else:
    print("WARNING: 未找到等待代码")

# 5. 添加调试：打印页面 HTML 片段
old_check = '''# 5. 检查页面状态
        current_url = page.url
        page_content = await page.content()'''

new_check = '''# 5. 检查页面状态
        current_url = page.url
        page_content = await page.content()

        # 调试：打印搜索结果区域的 HTML
        debug_html = await page.evaluate("() => { const el = document.querySelector('.feeds-container, .search-result-container, main, #app'); return el ? el.innerHTML.substring(0, 1000) : 'NOT FOUND'; }")
        print(f"DEBUG HUMAN SEARCH: 页面结构预览: {debug_html[:500]}...")'''

if old_check in content:
    content = content.replace(old_check, new_check)
    print("已添加页面结构调试输出")
else:
    print("WARNING: 未找到检查页面状态代码")

# 写回文件
with open('/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n修复完成！")
