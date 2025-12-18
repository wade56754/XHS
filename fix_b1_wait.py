"""Fix the b1 wait code in main.py"""

filepath = "/app/main.py"

with open(filepath, "r") as f:
    content = f.read()

# Remove the broken patch (all on one line)
broken_line = '# 等待 b1 生成 (最多 10 秒)    logger.info("Waiting for b1 to be generated...")    for _i in range(10):        await asyncio.sleep(1)        _b1 = await page.evaluate("localStorage.getItem(\\"b1\\")")        if _b1:            logger.info(f"b1 generated after {_i+1}s")            break    else:        logger.warning("b1 not generated after 10s")'

content = content.replace(broken_line + "\n", "")

# Find the correct location to insert
marker = "    # 验证签名函数是否可用\n    sign_func_type = await page.evaluate"

b1_wait_code = '''    # 等待 b1 生成 (最多 10 秒)
    logger.info("Waiting for b1 to be generated...")
    for _i in range(10):
        await asyncio.sleep(1)
        _b1 = await page.evaluate('localStorage.getItem("b1")')
        if _b1:
            logger.info(f"b1 generated after {_i+1}s")
            break
    else:
        logger.warning("b1 not generated after 10s")

    # 验证签名函数是否可用
    sign_func_type = await page.evaluate'''

if "Waiting for b1" not in content:
    content = content.replace(marker, b1_wait_code)

    with open(filepath, "w") as f:
        f.write(content)
    print("Successfully fixed b1 wait code")
else:
    print("b1 wait code already present")
