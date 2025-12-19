#!/usr/bin/env python3
"""
添加 /api/publish 端点到 MediaCrawler API
通过 Playwright 模拟用户操作发布内容到小红书创作者中心

使用方法:
docker cp add_publish_api.py media-crawler-api:/app/
docker exec media-crawler-api python3 /app/add_publish_api.py
docker restart media-crawler-api
"""

import re

MAIN_PY_PATH = "/app/main.py"

# 新增的发布请求模型
PUBLISH_MODEL = '''
class PublishRequest(BaseModel):
    """发布请求模型"""
    title: str                          # 笔记标题
    content: str                        # 笔记正文
    images: list[str] = []              # 图片URL列表 (最多9张)
    note_type: str = "normal"           # 笔记类型: normal(图文) / video(视频)
    topics: list[str] = []              # 话题标签
    at_users: list[str] = []            # @的用户
    location: str = ""                  # 位置信息
'''

# 发布端点代码
PUBLISH_ENDPOINT = '''
@app.post("/api/publish")
async def publish_note(request: PublishRequest, api_key: str = Depends(verify_api_key)):
    """
    发布笔记到小红书

    通过 Playwright 模拟用户操作，自动填写内容并发布
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Publish request: title={request.title[:20]}...")

    if not crawler_ready:
        raise HTTPException(status_code=503, detail="Crawler not ready. Please login first.")

    if not page or not browser_context:
        raise HTTPException(status_code=503, detail="Browser not initialized")

    # 验证图片数量
    if len(request.images) > 9:
        raise HTTPException(status_code=400, detail="Maximum 9 images allowed")

    try:
        # 1. 导航到创作者中心发布页
        creator_url = "https://creator.xiaohongshu.com/publish/publish"
        logger.info(f"[{request_id}] Navigating to creator center...")

        await page.goto(creator_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)

        # 检查是否需要登录
        current_url = page.url
        if "login" in current_url.lower():
            raise HTTPException(status_code=401, detail="Not logged in to creator center")

        # 2. 上传图片
        if request.images:
            logger.info(f"[{request_id}] Uploading {len(request.images)} images...")

            # 下载图片到临时目录
            import tempfile
            import httpx

            temp_files = []
            async with httpx.AsyncClient() as client:
                for i, img_url in enumerate(request.images):
                    try:
                        response = await client.get(img_url, timeout=30)
                        if response.status_code == 200:
                            # 确定文件扩展名
                            content_type = response.headers.get("content-type", "image/jpeg")
                            ext = ".jpg" if "jpeg" in content_type else ".png" if "png" in content_type else ".jpg"

                            # 保存到临时文件
                            temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                            temp_file.write(response.content)
                            temp_file.close()
                            temp_files.append(temp_file.name)
                            logger.info(f"[{request_id}] Downloaded image {i+1}: {temp_file.name}")
                    except Exception as e:
                        logger.warning(f"[{request_id}] Failed to download image {i+1}: {e}")

            if temp_files:
                # 找到上传按钮并上传
                upload_input = await page.query_selector('input[type="file"]')
                if upload_input:
                    await upload_input.set_input_files(temp_files)
                    logger.info(f"[{request_id}] Uploaded {len(temp_files)} images")
                    await asyncio.sleep(5)  # 等待上传完成

                # 清理临时文件
                import os
                for f in temp_files:
                    try:
                        os.unlink(f)
                    except:
                        pass

        # 3. 填写标题
        logger.info(f"[{request_id}] Filling title...")
        title_input = await page.query_selector('[placeholder*="标题"], input[class*="title"], .title-input input')
        if title_input:
            await title_input.click()
            await title_input.fill(request.title)
            await asyncio.sleep(0.5)
        else:
            logger.warning(f"[{request_id}] Title input not found")

        # 4. 填写正文
        logger.info(f"[{request_id}] Filling content...")
        content_input = await page.query_selector('[placeholder*="正文"], .content-input, [class*="editor"], [contenteditable="true"]')
        if content_input:
            await content_input.click()
            await content_input.fill(request.content)
            await asyncio.sleep(0.5)
        else:
            # 尝试其他选择器
            await page.keyboard.press("Tab")
            await page.keyboard.type(request.content)

        # 5. 添加话题标签
        if request.topics:
            logger.info(f"[{request_id}] Adding {len(request.topics)} topics...")
            for topic in request.topics[:5]:  # 最多5个话题
                topic_btn = await page.query_selector('[class*="topic"], [class*="hashtag"], button:has-text("#")')
                if topic_btn:
                    await topic_btn.click()
                    await asyncio.sleep(0.5)
                    await page.keyboard.type(topic)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(0.3)

        # 6. 点击发布按钮
        logger.info(f"[{request_id}] Clicking publish button...")
        publish_btn = await page.query_selector('button:has-text("发布"), button:has-text("发 布"), .publish-btn, [class*="submit"]')

        if not publish_btn:
            # 尝试其他选择器
            publish_btn = await page.query_selector('button.red-btn, button[type="submit"]')

        if publish_btn:
            await publish_btn.click()
            logger.info(f"[{request_id}] Publish button clicked")

            # 7. 等待发布结果
            await asyncio.sleep(5)

            # 检查是否发布成功 (URL 变化或成功提示)
            current_url = page.url
            success_text = await page.query_selector('[class*="success"], .toast-success, [class*="complete"]')

            if success_text or "success" in current_url.lower() or "complete" in current_url.lower():
                # 尝试获取新笔记ID
                note_id = None
                note_url = None

                # 从URL或页面中提取
                match = re.search(r'/([a-f0-9]{24})', current_url)
                if match:
                    note_id = match.group(1)
                    note_url = f"https://www.xiaohongshu.com/explore/{note_id}"

                logger.info(f"[{request_id}] Publish successful! note_id={note_id}")

                return {
                    "success": True,
                    "data": {
                        "note_id": note_id,
                        "note_url": note_url,
                        "message": "笔记发布成功",
                        "status": "published"
                    },
                    "meta": {"request_id": request_id}
                }
            else:
                # 检查是否有错误提示
                error_text = await page.query_selector('[class*="error"], .toast-error, [class*="fail"]')
                error_msg = await error_text.inner_text() if error_text else "Unknown error"

                return {
                    "success": False,
                    "error": {
                        "code": "PUBLISH_FAILED",
                        "message": f"发布失败: {error_msg}"
                    },
                    "meta": {"request_id": request_id}
                }
        else:
            raise HTTPException(status_code=500, detail="Publish button not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Publish error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": {
                "code": "PUBLISH_ERROR",
                "message": str(e)
            },
            "meta": {"request_id": request_id}
        }


@app.get("/api/publish/status/{note_id}")
async def get_publish_status(note_id: str, api_key: str = Depends(verify_api_key)):
    """
    查询笔记发布状态

    发布后可能需要审核，此接口用于查询审核状态
    """
    request_id = str(uuid.uuid4())[:8]

    if not crawler_ready or not xhs_client:
        raise HTTPException(status_code=503, detail="Crawler not ready")

    try:
        # 调用笔记详情API查看状态
        result = await xhs_client.get_note_by_id(note_id)

        if result:
            return {
                "success": True,
                "data": {
                    "note_id": note_id,
                    "status": "published",
                    "title": result.get("title", ""),
                    "likes": result.get("liked_count", 0),
                    "comments": result.get("comment_count", 0)
                },
                "meta": {"request_id": request_id}
            }
        else:
            return {
                "success": True,
                "data": {
                    "note_id": note_id,
                    "status": "pending_review",
                    "message": "笔记可能在审核中"
                },
                "meta": {"request_id": request_id}
            }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "STATUS_CHECK_FAILED",
                "message": str(e)
            },
            "meta": {"request_id": request_id}
        }
'''


def patch_main_py():
    """修补 main.py 添加发布端点"""

    with open(MAIN_PY_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经添加过
    if '/api/publish' in content:
        print("Publish endpoint already exists, skipping...")
        return False

    # 1. 在 BaseModel 类定义后添加 PublishRequest 模型
    # 找到最后一个 class XXXRequest(BaseModel) 的位置
    model_pattern = r'(class \w+Request\(BaseModel\):.*?(?=\n\n|\nclass |\n@app))'
    matches = list(re.finditer(model_pattern, content, re.DOTALL))

    if matches:
        last_model = matches[-1]
        insert_pos = last_model.end()
        content = content[:insert_pos] + "\n" + PUBLISH_MODEL + content[insert_pos:]
        print("Added PublishRequest model")
    else:
        # 如果没找到，在 imports 后添加
        import_end = content.rfind("from pydantic import")
        if import_end > 0:
            line_end = content.find("\n", import_end)
            content = content[:line_end+1] + PUBLISH_MODEL + content[line_end+1:]
            print("Added PublishRequest model after imports")

    # 2. 在文件末尾添加发布端点
    content = content.rstrip() + "\n\n" + PUBLISH_ENDPOINT + "\n"
    print("Added publish endpoints")

    # 写回文件
    with open(MAIN_PY_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Successfully patched main.py with publish endpoints!")
    return True


if __name__ == "__main__":
    patch_main_py()
