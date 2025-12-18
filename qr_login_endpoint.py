"""
QR Code Login Endpoint for XHS MediaCrawler API
Add this to main.py to enable one-time QR login for server deployment
"""

import asyncio
import base64
import httpx
from io import BytesIO
from PIL import Image, ImageDraw
from pydantic import BaseModel
from typing import Optional

# ============ Request/Response Models ============
class QRLoginResponse(BaseModel):
    success: bool
    qrcode_base64: Optional[str] = None
    session_id: Optional[str] = None
    message: str

class QRLoginStatusResponse(BaseModel):
    success: bool
    status: str  # "waiting", "scanned", "confirmed", "expired", "error"
    message: str
    crawler_ready: bool = False


# ============ QR Login Implementation ============

async def get_qrcode_from_page(page) -> tuple[str, str]:
    """从页面获取二维码图片和会话ID"""
    # 等待二维码出现
    try:
        qr_element = await page.wait_for_selector(
            'img[src*="qrcode"], img[src*="data:image"]',
            timeout=10000
        )
        qr_src = await qr_element.get_attribute("src")

        if qr_src.startswith("data:image"):
            # Base64 encoded
            qr_base64 = qr_src.split(",")[1] if "," in qr_src else qr_src
        elif qr_src.startswith("http"):
            # URL - need to fetch
            async with httpx.AsyncClient() as client:
                resp = await client.get(qr_src)
                qr_base64 = base64.b64encode(resp.content).decode()
        else:
            raise Exception(f"Unknown QR code format: {qr_src[:50]}")

        # Generate a session ID
        import hashlib
        import time
        session_id = hashlib.md5(f"{time.time()}".encode()).hexdigest()[:16]

        return qr_base64, session_id
    except Exception as e:
        raise Exception(f"Failed to get QR code: {e}")


async def add_qrcode_border(qr_base64: str) -> str:
    """给二维码添加白色边框以便扫描"""
    qr_bytes = base64.b64decode(qr_base64)
    image = Image.open(BytesIO(qr_bytes))

    # Add white border
    width, height = image.size
    new_image = Image.new("RGB", (width + 40, height + 40), color=(255, 255, 255))
    new_image.paste(image, (20, 20))

    # Add thin black border
    draw = ImageDraw.Draw(new_image)
    draw.rectangle((5, 5, width + 34, height + 34), outline=(0, 0, 0), width=2)

    # Convert back to base64
    buffer = BytesIO()
    new_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


async def check_login_status(page, browser_context) -> tuple[str, bool]:
    """检查登录状态
    Returns: (status, is_logged_in)
    """
    # Check if we're still on the login page
    current_url = page.url

    if "login" not in current_url.lower():
        # No longer on login page - might be logged in
        # Check for user-specific elements
        try:
            # Check if user avatar exists (indicates logged in)
            user_element = await page.query_selector('[class*="user"], [class*="avatar"]')
            if user_element:
                return "confirmed", True

            # Check cookies for login indicators
            cookies = await browser_context.cookies()
            cookie_names = [c["name"] for c in cookies]

            if "web_session" in cookie_names or "xsecappid" in cookie_names:
                return "confirmed", True

            # Page changed but not sure if logged in
            return "scanned", False
        except:
            return "scanned", False

    # Still on login page
    # Check if QR code has been scanned
    try:
        # Look for "已扫描" (scanned) text or similar
        scanned_text = await page.query_selector('text="已扫描"')
        if scanned_text:
            return "scanned", False

        # Check if QR code expired
        expired_text = await page.query_selector('text="二维码已过期"')
        if expired_text:
            return "expired", False
    except:
        pass

    return "waiting", False


# ============ API Endpoints (add to main.py) ============

"""
Add these endpoints to your FastAPI app:

@app.post("/api/login/qrcode")
async def start_qr_login(
    request: Request,
    api_key: str = Security(verify_api_key)
):
    '''开始二维码登录流程 - 返回二维码图片'''
    global browser_context, page
    request_id = request.headers.get("X-Request-ID", "unknown")

    if not browser_context or not page:
        return {"success": False, "message": "Browser not initialized"}

    try:
        # Navigate to login page
        await page.goto(
            "https://www.xiaohongshu.com/login/qrcode",
            wait_until="domcontentloaded",
            timeout=30000
        )
        await asyncio.sleep(2)

        # Get QR code
        qr_base64, session_id = await get_qrcode_from_page(page)
        qr_base64_bordered = await add_qrcode_border(qr_base64)

        return {
            "success": True,
            "qrcode_base64": qr_base64_bordered,
            "session_id": session_id,
            "message": "Please scan the QR code with XiaoHongShu app within 120 seconds"
        }
    except Exception as e:
        logger.error(f"[{request_id}] QR login start error: {e}")
        return {"success": False, "message": str(e)}


@app.get("/api/login/status")
async def check_qr_login_status(
    request: Request,
    api_key: str = Security(verify_api_key)
):
    '''检查二维码登录状态'''
    global browser_context, page, xhs_client, crawler_ready
    request_id = request.headers.get("X-Request-ID", "unknown")

    if not browser_context or not page:
        return {"success": False, "status": "error", "message": "Browser not initialized", "crawler_ready": False}

    try:
        status, is_logged_in = await check_login_status(page, browser_context)

        if is_logged_in:
            # Initialize XHS client with new session
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

            return {
                "success": True,
                "status": "confirmed",
                "message": "Login successful! Crawler is ready.",
                "crawler_ready": True
            }

        return {
            "success": True,
            "status": status,
            "message": f"Login status: {status}",
            "crawler_ready": False
        }
    except Exception as e:
        logger.error(f"[{request_id}] QR login status error: {e}")
        return {"success": False, "status": "error", "message": str(e), "crawler_ready": False}


@app.post("/api/login/qrcode/poll")
async def poll_qr_login(
    request: Request,
    timeout_seconds: int = 120,
    api_key: str = Security(verify_api_key)
):
    '''轮询等待二维码登录完成 - 用于 n8n/自动化场景'''
    global browser_context, page, xhs_client, crawler_ready
    request_id = request.headers.get("X-Request-ID", "unknown")

    if not browser_context or not page:
        return {"success": False, "message": "Browser not initialized"}

    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        try:
            status, is_logged_in = await check_login_status(page, browser_context)

            if is_logged_in:
                # Same initialization as above
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
                    "message": "Login successful! Crawler is ready.",
                    "crawler_ready": True
                }

            if status == "expired":
                return {
                    "success": False,
                    "message": "QR code expired. Please restart the login process.",
                    "crawler_ready": False
                }

            # Wait before next check
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"[{request_id}] Poll error: {e}")
            await asyncio.sleep(2)

    return {
        "success": False,
        "message": f"Login timeout after {timeout_seconds} seconds",
        "crawler_ready": False
    }
"""


# ============ Alternative: Cookie Import with Session Restore ============

"""
For n8n integration without QR login, you can export cookies + localStorage from a logged-in browser:

1. Login to XHS in your browser
2. Open DevTools > Application > Cookies
3. Export all cookies for xiaohongshu.com
4. Also get localStorage.b1 value
5. POST to /api/crawler/cookies with cookies + b1 value

Modified cookie endpoint to support b1:

@app.post("/api/crawler/session")
async def set_crawler_session(
    request: Request,
    body: dict,  # {cookies: [...], b1: "..."}
    api_key: str = Security(verify_api_key)
):
    '''设置完整的爬虫会话 (cookies + b1)'''
    cookies = body.get("cookies", [])
    b1 = body.get("b1", "")

    # Set cookies
    await browser_context.add_cookies(cookies)

    # Navigate and set b1 in localStorage
    await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
    if b1:
        await page.evaluate(f'localStorage.setItem("b1", "{b1}")')
    await page.reload()
    await asyncio.sleep(3)

    # Initialize client...
"""
