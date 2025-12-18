"""
Script to add QR login endpoints to main.py
Run this inside the container to patch main.py
"""

NEW_ENDPOINTS = '''

# ============ QR 登录端点 ============

import base64
from io import BytesIO
from PIL import Image, ImageDraw

async def get_qrcode_from_page(page) -> tuple:
    """从页面获取二维码图片"""
    import httpx
    try:
        qr_element = await page.wait_for_selector(
            'img.qrcode-img, img[class*="qrcode"], canvas.qrcode-canvas',
            timeout=15000
        )

        # Try to get src attribute
        qr_src = await qr_element.get_attribute("src")

        if qr_src and qr_src.startswith("data:image"):
            qr_base64 = qr_src.split(",")[1] if "," in qr_src else qr_src
        elif qr_src and qr_src.startswith("http"):
            async with httpx.AsyncClient() as client:
                resp = await client.get(qr_src, timeout=10)
                qr_base64 = base64.b64encode(resp.content).decode()
        else:
            # Try to capture canvas as image
            qr_base64 = await page.evaluate("""
                () => {
                    const canvas = document.querySelector('canvas.qrcode-canvas, canvas');
                    if (canvas) {
                        return canvas.toDataURL('image/png').split(',')[1];
                    }
                    const img = document.querySelector('img.qrcode-img, img[class*="qrcode"]');
                    if (img && img.src) {
                        return img.src.includes('data:') ? img.src.split(',')[1] : null;
                    }
                    return null;
                }
            """)

        if not qr_base64:
            raise Exception("Could not extract QR code image")

        return qr_base64
    except Exception as e:
        raise Exception(f"Failed to get QR code: {e}")


def add_qrcode_border(qr_base64: str) -> str:
    """给二维码添加白色边框"""
    qr_bytes = base64.b64decode(qr_base64)
    image = Image.open(BytesIO(qr_bytes))

    width, height = image.size
    new_image = Image.new("RGB", (width + 40, height + 40), color=(255, 255, 255))
    new_image.paste(image, (20, 20))

    draw = ImageDraw.Draw(new_image)
    draw.rectangle((5, 5, width + 34, height + 34), outline=(0, 0, 0), width=2)

    buffer = BytesIO()
    new_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


async def check_xhs_login_status(page, browser_context) -> tuple:
    """检查登录状态 - 返回 (status, is_logged_in)"""
    current_url = page.url

    # Check if redirected away from login page
    if "login" not in current_url.lower() and "explore" in current_url.lower():
        # Check cookies for login indicators
        cookies = await browser_context.cookies()
        cookie_names = [c["name"] for c in cookies]

        if "web_session" in cookie_names:
            return "confirmed", True
        return "scanned", False

    # Still on login page - check for status
    try:
        scanned = await page.query_selector('text="已扫码"')
        if scanned:
            return "scanned", False

        expired = await page.query_selector('text="二维码已过期"')
        if expired:
            return "expired", False
    except:
        pass

    return "waiting", False


@app.post("/api/login/qrcode")
async def start_qr_login(
    request: Request,
    api_key: str = Security(verify_api_key)
):
    """开始二维码登录流程 - 返回二维码图片 (base64)"""
    global browser_context, page
    request_id = request.headers.get("X-Request-ID", "unknown")

    if not browser_context or not page:
        return {
            "success": False,
            "error": {"code": "BROWSER_NOT_READY", "message": "Browser not initialized"},
            "meta": {"request_id": request_id}
        }

    try:
        logger.info(f"[{request_id}] Starting QR login...")

        # Navigate to login page
        await page.goto(
            "https://www.xiaohongshu.com",
            wait_until="domcontentloaded",
            timeout=30000
        )
        await asyncio.sleep(2)

        # Click login button if exists
        try:
            login_btn = await page.query_selector('text="登录"')
            if login_btn:
                await login_btn.click()
                await asyncio.sleep(2)
        except:
            pass

        # Try to find QR code tab
        try:
            qr_tab = await page.query_selector('text="扫码登录"')
            if qr_tab:
                await qr_tab.click()
                await asyncio.sleep(2)
        except:
            pass

        # Get QR code
        qr_base64 = await get_qrcode_from_page(page)
        qr_base64_bordered = add_qrcode_border(qr_base64)

        return {
            "success": True,
            "data": {
                "qrcode_base64": qr_base64_bordered,
                "qrcode_url": f"data:image/png;base64,{qr_base64_bordered}",
                "expires_in": 120,
                "message": "请使用小红书 App 扫描二维码登录 (120秒内有效)"
            },
            "meta": {"request_id": request_id}
        }
    except Exception as e:
        logger.error(f"[{request_id}] QR login start error: {e}")
        return {
            "success": False,
            "error": {"code": "QR_LOGIN_ERROR", "message": str(e)},
            "meta": {"request_id": request_id}
        }


@app.get("/api/login/status")
async def check_qr_login_status(
    request: Request,
    api_key: str = Security(verify_api_key)
):
    """检查二维码登录状态"""
    global browser_context, page, xhs_client, crawler_ready
    request_id = request.headers.get("X-Request-ID", "unknown")

    if not browser_context or not page:
        return {
            "success": False,
            "data": {"status": "error", "crawler_ready": False},
            "error": {"code": "BROWSER_NOT_READY", "message": "Browser not initialized"},
            "meta": {"request_id": request_id}
        }

    try:
        status, is_logged_in = await check_xhs_login_status(page, browser_context)

        if is_logged_in:
            # Initialize XHS client with new session
            logger.info(f"[{request_id}] Login confirmed, initializing client...")

            await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Get cookies and initialize client
            all_cookies = await browser_context.cookies()
            cookie_str, cookie_dict = convert_cookies(all_cookies)

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Cookie": cookie_str,
                "Origin": "https://www.xiaohongshu.com",
                "Referer": "https://www.xiaohongshu.com/",
                "Content-Type": "application/json;charset=UTF-8",
            }

            xhs_client = XiaoHongShuClient(
                timeout=60,
                headers=headers,
                playwright_page=page,
                cookie_dict=cookie_dict,
            )
            crawler_ready = True

            logger.info(f"[{request_id}] XHS client initialized after QR login")

            return {
                "success": True,
                "data": {
                    "status": "confirmed",
                    "crawler_ready": True,
                    "message": "登录成功！爬虫已就绪。"
                },
                "meta": {"request_id": request_id}
            }

        return {
            "success": True,
            "data": {
                "status": status,
                "crawler_ready": False,
                "message": f"登录状态: {status}"
            },
            "meta": {"request_id": request_id}
        }
    except Exception as e:
        logger.error(f"[{request_id}] QR login status error: {e}")
        return {
            "success": False,
            "data": {"status": "error", "crawler_ready": False},
            "error": {"code": "STATUS_CHECK_ERROR", "message": str(e)},
            "meta": {"request_id": request_id}
        }


@app.post("/api/login/qrcode/wait")
async def wait_for_qr_login(
    request: Request,
    timeout_seconds: int = 120,
    api_key: str = Security(verify_api_key)
):
    """等待二维码登录完成 - 适用于自动化场景"""
    global browser_context, page, xhs_client, crawler_ready
    request_id = request.headers.get("X-Request-ID", "unknown")

    if not browser_context or not page:
        return {
            "success": False,
            "error": {"code": "BROWSER_NOT_READY", "message": "Browser not initialized"},
            "meta": {"request_id": request_id}
        }

    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        try:
            status, is_logged_in = await check_xhs_login_status(page, browser_context)

            if is_logged_in:
                # Initialize client
                await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                all_cookies = await browser_context.cookies()
                cookie_str, cookie_dict = convert_cookies(all_cookies)

                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Cookie": cookie_str,
                    "Origin": "https://www.xiaohongshu.com",
                    "Referer": "https://www.xiaohongshu.com/",
                    "Content-Type": "application/json;charset=UTF-8",
                }

                xhs_client = XiaoHongShuClient(
                    timeout=60,
                    headers=headers,
                    playwright_page=page,
                    cookie_dict=cookie_dict,
                )
                crawler_ready = True

                return {
                    "success": True,
                    "data": {
                        "message": "登录成功！爬虫已就绪。",
                        "crawler_ready": True,
                        "waited_seconds": int(time.time() - start_time)
                    },
                    "meta": {"request_id": request_id}
                }

            if status == "expired":
                return {
                    "success": False,
                    "error": {"code": "QR_EXPIRED", "message": "二维码已过期，请重新获取"},
                    "meta": {"request_id": request_id}
                }

            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"[{request_id}] Poll error: {e}")
            await asyncio.sleep(2)

    return {
        "success": False,
        "error": {"code": "LOGIN_TIMEOUT", "message": f"登录超时 ({timeout_seconds}秒)"},
        "meta": {"request_id": request_id}
    }

'''

# Read current main.py
filepath = "/app/main.py"

with open(filepath, "r") as f:
    content = f.read()

# Find insertion point (before "if __name__")
insertion_marker = 'if __name__ == "__main__":'
if insertion_marker not in content:
    print("ERROR: Could not find insertion point")
    exit(1)

# Insert new endpoints
new_content = content.replace(
    insertion_marker,
    NEW_ENDPOINTS + "\n\n" + insertion_marker
)

# Write back
with open(filepath, "w") as f:
    f.write(new_content)

print("Successfully added QR login endpoints to main.py")
