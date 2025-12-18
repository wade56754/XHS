#!/usr/bin/env python3
"""添加人工模拟搜索端点"""

# 读取文件
with open('/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 人工搜索端点代码
human_search_code = '''
@app.post("/api/search/human")
async def search_notes_human(
    request: Request,
    body: dict = Body(...),
    api_key: str = Depends(verify_api_key),
):
    """
    完全模拟人工搜索行为：
    1. 预热浏览器
    2. 在搜索框输入关键词
    3. 从页面提取搜索结果
    """
    global page, browser_context
    request_id = getattr(request.state, 'request_id', 'unknown')

    if not page:
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": {"code": "CRAWLER_NOT_READY", "message": "Crawler not initialized"}}
        )

    keyword = body.get("keyword", "")
    limit = min(body.get("limit", 20), 100)
    skip_warmup = body.get("skip_warmup", False)

    if not keyword:
        return {"success": False, "error": {"code": "MISSING_KEYWORD", "message": "keyword is required"}}

    try:
        print(f"DEBUG HUMAN SEARCH: 开始人工模拟搜索: {keyword}")

        # 1. 预热浏览器（可选跳过）
        if not skip_warmup:
            await warmup_browser(page, browser_context)

        # 2. 导航到首页
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(2, 4))

        # 3. 模拟在搜索框输入
        search_success = await simulate_search_input(page, keyword)

        if not search_success:
            # 备用方案：直接导航到搜索结果页
            print("DEBUG HUMAN SEARCH: 搜索框输入失败，使用直接导航")
            import urllib.parse
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_search_result_notes"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))

        # 4. 等待搜索结果加载
        await asyncio.sleep(random.uniform(2, 4))

        # 5. 检查页面状态
        current_url = page.url
        page_content = await page.content()

        print(f"DEBUG HUMAN SEARCH: 当前URL: {current_url}")

        if "安全限制" in page_content:
            return {"success": False, "error": {"code": "BLOCKED", "message": "被安全限制页面拦截"}}

        if "login" in current_url.lower() and "explore" not in current_url.lower():
            return {"success": False, "error": {"code": "LOGIN_REQUIRED", "message": "需要重新登录"}}

        # 6. 提取搜索结果
        extract_js = """() => {
            const results = [];
            // 尝试多种选择器
            const noteCards = document.querySelectorAll('section.note-item, div[data-note-id], .note-card, a[href*="/explore/"], a[href*="/search_result/"]');

            noteCards.forEach((card, index) => {
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
            });

            // 去重
            const seen = new Set();
            return results.filter(item => {
                const key = item.note_id || item.title;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
        }"""

        notes = await page.evaluate(extract_js)

        print(f"DEBUG HUMAN SEARCH: 提取到 {len(notes)} 条结果")

        # 7. 模拟浏览结果（增加真实性）
        if notes:
            await page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(random.uniform(1, 2))

        return {
            "success": True,
            "data": {
                "items": notes[:limit],
                "total": len(notes),
                "method": "human_simulation",
                "current_url": current_url
            },
            "meta": {"request_id": request_id}
        }

    except Exception as e:
        import traceback
        print(f"DEBUG HUMAN SEARCH ERROR: {traceback.format_exc()}")
        return {"success": False, "error": {"code": "HUMAN_SEARCH_FAILED", "message": str(e)}}


'''

# 在 @app.post("/api/search/browser") 之前插入新端点
if '@app.post("/api/search/human")' not in content:
    # 找到 browser search 端点
    marker = '@app.post("/api/search/browser")'
    if marker in content:
        content = content.replace(marker, human_search_code + marker)
        print("已添加 /api/search/human 端点")
    else:
        # 尝试找原始搜索端点
        marker2 = '@app.post("/api/search")'
        if marker2 in content:
            content = content.replace(marker2, human_search_code + marker2)
            print("已添加 /api/search/human 端点（在原始搜索端点之前）")
        else:
            print("ERROR: 未找到插入点")
else:
    print("/api/search/human 端点已存在")

# 写回文件
with open('/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("人工搜索端点添加完成！")
