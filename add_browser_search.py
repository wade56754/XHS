#!/usr/bin/env python3
"""Add browser-native search endpoint that uses page.request instead of httpx"""

# Read the file
with open('/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find a good place to add the new endpoint (after search endpoint)
search_endpoint = '@app.post("/api/search")\nasync def search_notes('

# New endpoint using browser's native fetch
browser_search_code = '''@app.post("/api/search/browser")
async def search_notes_browser(
    request: Request,
    body: dict = Body(...),
    api_key: str = Depends(verify_api_key),
):
    """Search notes using browser's native fetch (bypasses httpx)"""
    global xhs_client, page
    request_id = getattr(request.state, 'request_id', 'unknown')

    if not xhs_client or not page:
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": {"code": "CRAWLER_NOT_READY", "message": "Crawler not initialized"}}
        )

    keyword = body.get("keyword", "")
    limit = min(body.get("limit", 20), 100)

    if not keyword:
        return {"success": False, "error": {"code": "MISSING_KEYWORD", "message": "keyword is required"}}

    try:
        import time
        import hashlib
        import json as json_module

        # Build search request
        uri = '/api/sns/web/v1/search/notes'
        search_id = hashlib.md5(f'{keyword}{time.time()}'.encode()).hexdigest()[:16]
        data = {
            'keyword': keyword,
            'page': 1,
            'page_size': limit,
            'search_id': search_id,
            'sort': 'general',
            'note_type': 0,
        }

        # Build sign string
        sign_str = uri + json_module.dumps(data, separators=(",", ":"), ensure_ascii=False)

        # Get signature from browser
        sign_js = "(async () => { const signStr = " + json_module.dumps(sign_str) + "; if (typeof window._webmsxyw === 'function') { const result = await window._webmsxyw(signStr); return result; } return null; })()"
        sign_result = await page.evaluate(sign_js)
        print(f"DEBUG BROWSER SEARCH: sign_result={sign_result}")

        if not sign_result:
            return {"success": False, "error": {"code": "SIGN_FAILED", "message": "Failed to get signature"}}

        # Get b1 from localStorage
        b1 = await page.evaluate('localStorage.getItem("b1")') or ""

        # Get cookies
        cookies = await browser_context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies if ".xiaohongshu.com" in c.get("domain", "")}
        a1 = cookie_dict.get("a1", "")

        # Build x-s-common using xhs_client's method
        from xhs_client import _build_xs_common, get_trace_id
        x_s = sign_result.get("X-s", "")
        x_t = str(sign_result.get("X-t", int(time.time() * 1000)))
        x_s_common = _build_xs_common(a1, b1, x_s, x_t)
        trace_id = get_trace_id()

        # Use browser's native fetch via page.evaluate
        body_json = json_module.dumps(data, separators=(",", ":"), ensure_ascii=False)
        fetch_js = f'(async () => {{ const response = await fetch("https://edith.xiaohongshu.com{uri}", {{ method: "POST", headers: {{ "Content-Type": "application/json;charset=UTF-8", "X-S": {json_module.dumps(x_s)}, "X-T": {json_module.dumps(x_t)}, "x-S-Common": {json_module.dumps(x_s_common)}, "X-B3-Traceid": {json_module.dumps(trace_id)} }}, body: {json_module.dumps(body_json)}, credentials: "include" }}); return await response.json(); }})()'

        print(f"DEBUG BROWSER SEARCH: Making fetch request")
        result = await page.evaluate(fetch_js)
        print(f"DEBUG BROWSER SEARCH: result={result}")

        if result.get('success') == False:
            error_msg = result.get('msg', 'Search failed')
            error_code = result.get('code', 'unknown')
            return {"success": False, "error": {"code": f"XHS_ERROR_{error_code}", "message": error_msg}}

        items = result.get('data', {}).get('items', [])
        return {
            "success": True,
            "data": {
                "items": items[:limit],
                "total": len(items),
                "has_more": result.get('data', {}).get('has_more', False),
            },
            "meta": {"request_id": request_id}
        }

    except Exception as e:
        import traceback
        print(f"DEBUG BROWSER SEARCH ERROR: {traceback.format_exc()}")
        return {"success": False, "error": {"code": "BROWSER_SEARCH_FAILED", "message": str(e)}}


@app.post("/api/search")
async def search_notes('''

if search_endpoint in content:
    content = content.replace(search_endpoint, browser_search_code)
    with open('/app/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully added /api/search/browser endpoint")
else:
    print("ERROR: Could not find search endpoint marker")
    # Debug: show what we have
    if '@app.post("/api/search")' in content:
        print("Found @app.post but pattern doesn't match exactly")
        import re
        match = re.search(r'@app\.post\("/api/search"\)[^\n]*\nasync def search_notes\([^)]*\)', content)
        if match:
            print(f"Actual pattern: {match.group()[:200]}")
