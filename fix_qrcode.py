import re

filepath = "/home/wade/mediacrawler/MediaCrawler/tools/crawler_util.py"

with open(filepath, "r") as f:
    content = f.read()

# Fix the broken show_qrcode function
new_func = '''def show_qrcode(qr_code) -> None:  # type: ignore
    """parse base64 encode qrcode image and save it to file for headless servers"""
    if "," in qr_code:
        qr_code = qr_code.split(",")[1]
    qr_code = base64.b64decode(qr_code)
    image = Image.open(BytesIO(qr_code))

    # Add a square border around the QR code
    width, height = image.size
    new_image = Image.new("RGB", (width + 20, height + 20), color=(255, 255, 255))
    new_image.paste(image, (10, 10))
    draw = ImageDraw.Draw(new_image)
    draw.rectangle((0, 0, width + 19, height + 19), outline=(0, 0, 0), width=1)

    # Save to file for headless server
    qr_path = "/home/wade/mediacrawler/MediaCrawler/qrcode.png"
    new_image.save(qr_path)
    print("")
    print(f"[QR Code] Saved to: {qr_path}")
    print("[QR Code] Please download and scan this QR code with XiaoHongShu app")
    print(f"[QR Code] Download: scp wade@124.221.251.8:{qr_path} ./qrcode.png")
    print("")

    # Also try to show if display is available
    try:
        new_image.show()
    except Exception:
        pass


'''

# Find and replace the function
pattern = r"def show_qrcode\(qr_code\).*?(?=\ndef |\Z)"
content = re.sub(pattern, new_func, content, flags=re.DOTALL)

with open(filepath, "w") as f:
    f.write(content)

print("Fixed show_qrcode function")
