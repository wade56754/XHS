"""
补丁脚本：为 main.py 添加飞书 Cookie 登录支持
运行方式: 在容器内执行此脚本
"""

FEISHU_COOKIE_MODULE = '''
# ============ 飞书 Cookie 集成 ============
import httpx

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_APP_TOKEN = os.environ.get("FEISHU_APP_TOKEN", "")
FEISHU_COOKIE_TABLE_ID = os.environ.get("FEISHU_COOKIE_TABLE_ID", "tblYa2d2a5lypzqz")
FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"

_feishu_token_cache = {"token": None}

def get_feishu_tenant_token():
    """获取飞书 tenant_access_token"""
    if _feishu_token_cache["token"]:
        return _feishu_token_cache["token"]

    url = f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}

    with httpx.Client(timeout=10) as client:
        resp = client.post(url, json=payload)
        data = resp.json()

    if data.get("code") != 0:
        raise Exception(f"Failed to get Feishu token: {data}")

    _feishu_token_cache["token"] = data["tenant_access_token"]
    return _feishu_token_cache["token"]


def get_cookies_from_feishu():
    """从飞书表格获取 active 状态的 Cookie"""
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET or not FEISHU_APP_TOKEN:
        logger.warning("Feishu credentials not configured")
        return None

    try:
        token = get_feishu_tenant_token()
        url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_COOKIE_TABLE_ID}/records"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"filter": 'CurrentValue.[状态] = "active"', "page_size": 1}

        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=headers, params=params)
            data = resp.json()

        if data.get("code") != 0:
            logger.error(f"Feishu API error: {data}")
            return None

        items = data.get("data", {}).get("items", [])
        if not items:
            logger.warning("No active cookie in Feishu")
            return None

        fields = items[0].get("fields", {})
        record_id = items[0].get("record_id")

        # 获取 cookie 值
        cookie_value = None
        for key in ["cookie_value", "Cookie", "cookie", "cookies"]:
            if key in fields:
                val = fields[key]
                if isinstance(val, list):
                    cookie_value = val[0].get("text", "") if val else ""
                else:
                    cookie_value = str(val)
                break

        if not cookie_value:
            logger.error(f"Cookie field not found. Fields: {list(fields.keys())}")
            return None

        # 解析 cookie
        cookies = []
        cookie_value = cookie_value.strip()

        if cookie_value.startswith("["):
            try:
                parsed = json.loads(cookie_value)
                for c in parsed:
                    if "name" in c and "value" in c:
                        cookies.append({
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c.get("domain", ".xiaohongshu.com"),
                            "path": c.get("path", "/")
                        })
                return {"cookies": cookies, "record_id": record_id}
            except:
                pass

        for item in cookie_value.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookies.append({
                    "name": key.strip(),
                    "value": value.strip(),
                    "domain": ".xiaohongshu.com",
                    "path": "/"
                })

        logger.info(f"Got {len(cookies)} cookies from Feishu")
        return {"cookies": cookies, "record_id": record_id}

    except Exception as e:
        logger.error(f"Failed to get cookies from Feishu: {e}")
        return None


def update_feishu_cookie_status(record_id: str, status: str, error_msg: str = ""):
    """更新飞书表格中的 Cookie 状态"""
    try:
        token = get_feishu_tenant_token()
        url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_COOKIE_TABLE_ID}/records/{record_id}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "fields": {
                "状态": status,
                "最后检查": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        if error_msg:
            payload["fields"]["错误信息"] = error_msg

        with httpx.Client(timeout=10) as client:
            resp = client.put(url, headers=headers, json=payload)
            data = resp.json()

        return data.get("code") == 0
    except Exception as e:
        logger.error(f"Failed to update Feishu cookie status: {e}")
        return False

'''

FEISHU_REFRESH_ENDPOINT = '''

# 飞书刷新端点的记录 ID 缓存
_current_feishu_record_id = None

@app.post("/api/login/feishu")
async def login_from_feishu(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """从飞书获取 Cookie 并登录"""
    global _current_feishu_record_id
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        result = get_cookies_from_feishu()
        if not result:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No active cookie in Feishu"}
            )

        cookies = result["cookies"]
        _current_feishu_record_id = result.get("record_id")

        await init_xhs_client(cookies)

        # 更新飞书状态
        if _current_feishu_record_id:
            update_feishu_cookie_status(_current_feishu_record_id, "active")

        return {
            "success": True,
            "data": {
                "message": "Login successful from Feishu",
                "cookie_count": len(cookies),
                "crawler_ready": True
            }
        }
    except Exception as e:
        logger.error(f"[{request_id}] Feishu login failed: {e}")
        if _current_feishu_record_id:
            update_feishu_cookie_status(_current_feishu_record_id, "invalid", str(e))
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

'''


def patch_main_py():
    """修改 main.py 添加飞书集成"""
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 检查是否已经添加过
    if "FEISHU_APP_ID" in content:
        print("Feishu integration already exists")
        return False

    # 1. 在 "# ============ 日志配置 ============" 之前插入飞书模块
    marker1 = "# ============ 日志配置 ============"
    if marker1 in content:
        content = content.replace(marker1, FEISHU_COOKIE_MODULE + "\n" + marker1)
        print("Added Feishu cookie module")
    else:
        print("Warning: Could not find logging config marker")
        return False

    # 2. 修改 lifespan 函数，优先从飞书获取 cookie
    old_lifespan = '''        # 检查环境变量中的 cookies
        xhs_cookies_str = os.environ.get("XHS_COOKIES")
        if xhs_cookies_str:
            try:
                cookies = json.loads(xhs_cookies_str)
                await init_xhs_client(cookies)
            except Exception as e:
                logger.error(f"Failed to init XHS client: {e}")'''

    new_lifespan = '''        # 优先从飞书获取 cookies
        feishu_result = get_cookies_from_feishu()
        if feishu_result:
            try:
                cookies = feishu_result["cookies"]
                await init_xhs_client(cookies)
                logger.info("Initialized XHS client with Feishu cookies")
            except Exception as e:
                logger.error(f"Failed to init XHS client from Feishu: {e}")
        else:
            # 回退到环境变量
            xhs_cookies_str = os.environ.get("XHS_COOKIES")
            if xhs_cookies_str:
                try:
                    cookies = json.loads(xhs_cookies_str)
                    await init_xhs_client(cookies)
                except Exception as e:
                    logger.error(f"Failed to init XHS client: {e}")'''

    if old_lifespan in content:
        content = content.replace(old_lifespan, new_lifespan)
        print("Updated lifespan function")
    else:
        print("Warning: Could not find lifespan cookie loading code")

    # 3. 在文件末尾添加飞书刷新端点 (在最后一个端点之后)
    # 找到合适的位置插入
    if "@app.post(\"/api/login/feishu\")" not in content:
        # 找到最后一个 @app 装饰器的位置
        import re
        matches = list(re.finditer(r'@app\.(get|post|put|delete)\([^\)]+\)', content))
        if matches:
            # 在文件末尾添加
            content = content.rstrip() + "\n" + FEISHU_REFRESH_ENDPOINT
            print("Added /api/login/feishu endpoint")

    # 写回文件
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(content)

    print("Patch completed successfully!")
    return True


if __name__ == "__main__":
    patch_main_py()
