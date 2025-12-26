import asyncio
import json
import hashlib
import time
import httpx
from playwright.async_api import async_playwright

async def test_fresh_session():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )

        await context.add_init_script('''
            Object.defineProperty(navigator, "webdriver", {get: () => undefined});
        ''')

        page = await context.new_page()

        print('Navigating to XHS...')
        await page.goto('https://www.xiaohongshu.com/explore', wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3)

        print('Page OK:', await page.title())

        all_cookies = await context.cookies()
        cookie_dict = {c['name']: c['value'] for c in all_cookies}
        print('Got', len(cookie_dict), 'cookies')

        a1 = cookie_dict.get('a1', '')
        print('a1:', a1[:30] if a1 else 'None')

        uri = '/api/sns/web/v1/search/notes'
        search_id = hashlib.md5(f'test{time.time()}'.encode()).hexdigest()[:16]
        data = {'keyword': '编程', 'page': 1, 'page_size': 3, 'search_id': search_id, 'sort': 'general', 'note_type': 0}
        sign_str = uri + json.dumps(data, separators=(',', ':'), ensure_ascii=False)

        # Escape for JS
        sign_str_escaped = sign_str.replace('\\', '\\\\').replace('"', '\\"')
        sign_result = await page.evaluate(f'window._webmsxyw("{sign_str_escaped}")')
        print('Sign result:', json.dumps(sign_result) if sign_result else 'None')

        if sign_result:
            # Get b1 from localStorage
            b1 = await page.evaluate('localStorage.getItem("b1")') or ''
            print('b1:', b1[:30] if b1 else 'None')

            # Build x-s-common
            import base64
            x_s = sign_result.get('X-s', '')
            x_t = str(sign_result.get('X-t', ''))

            # Simple CRC32 implementation for x9
            def mrc(e):
                CRC32_TABLE = [0, 1996959894, 3993919788, 2567524794, 124634137, 1886057615, 3915621685, 2657392035, 249268274, 2044508324, 3772115230, 2547177864, 162941995, 2125561021, 3887607047, 2428444049, 498536548, 1789927666, 4089016648, 2227061214, 450548861, 1843258603, 4107580753, 2211677639, 325883990, 1684777152, 4251122042, 2321926636, 335633487, 1661365465, 4195302755, 2366115317, 997073096, 1281953886, 3579855332, 2724688242, 1006888145, 1258607687, 3524101629, 2768942443, 901097722, 1119000684, 3686517206, 2898065728, 853044451, 1172266101, 3705015759, 2882616665, 651767980, 1373503546, 3369554304, 3218104598, 565507253, 1454621731, 3485111705, 3099436303, 671266974, 1594198024, 3322730930, 2970347812, 795835527, 1483230225, 3244367275, 3060149565, 1994146192, 31158534, 2563907772, 4023717930, 1907459465, 112637215, 2680153253, 3904427059, 2013776290, 251722036, 2517215374, 3775830040, 2137656763, 141376813, 2439277719, 3865271297, 1802195444, 476864866, 2238001368, 4066508878, 1812370925, 453092731, 2181625025, 4111451223, 1706088902, 314042704, 2344532202, 4240017532, 1658658271, 366619977, 2362670323, 4224994405, 1303535960, 984961486, 2747007092, 3569037538, 1256170817, 1037604311, 2765210733, 3554079995, 1131014506, 879679996, 2909243462, 3663771856, 1141124467, 855842277, 2852801631, 3708648649, 1342533948, 654459306, 3188396048, 3373015174, 1466479909, 544179635, 3110523913, 3462522015, 1591671054, 702138776, 2966460450, 3352799412, 1504918807, 783551873, 3082640443, 3233442989, 3988292384, 2596254646, 62317068, 1957810842, 3939845945, 2647816111, 81470997, 1943803523, 3814918930, 2489596804, 225274430, 2053790376, 3826175755, 2466906013, 167816743, 2097651377, 4027552580, 2265490386, 503444072, 1762050814, 4150417245, 2154129355, 426522225, 1852507879, 4275313526, 2312317920, 282753626, 1742555852, 4189708143, 2394877945, 397917763, 1622183637, 3604390888, 2714866558, 953729732, 1340076626, 3518719985, 2797360999, 1068828381, 1219638859, 3624741850, 2936675148, 906185462, 1090812512, 3747672003, 2825379669, 829329135, 1181335161, 3412177804, 3160834842, 628085408, 1382605366, 3423369109, 3138078467, 570562233, 1426400815, 3317316542, 2998733608, 733239954, 1555261956, 3268935591, 3050360625, 752459403, 1541320221, 2607071920, 3965973030, 1969922972, 40735498, 2617837225, 3943577151, 1913087877, 83908371, 2512341634, 3803740692, 2075208622, 213261112, 2463272603, 3855990285, 2094854071, 198958881, 2262029012, 4057260610, 1759359992, 534414190, 2176718541, 4139329115, 1873836001, 414664567, 2282248934, 4279200368, 1711684554, 285281116, 2405801727, 4167216745, 1634467795, 376229701, 2685067896, 3608007406, 1308918612, 956543938, 2808555105, 3495958263, 1231636301, 1047427035, 2932959818, 3654703836, 1088359270, 936918000, 2847714899, 3736837829, 1202900863, 817233897, 3183342108, 3401237130, 1404277552, 615818150, 3134207493, 3453421203, 1423857449, 601450431, 3009837614, 3294710456, 1567103746, 711928724, 3020668471, 3272380065, 1510334235, 755167117]
                import ctypes
                o = -1
                for n in range(min(57, len(e))):
                    o = CRC32_TABLE[(o & 255) ^ ord(e[n])] ^ (ctypes.c_uint32(o).value >> 8)
                return o ^ -1 ^ 3988292384

            xs_common_payload = {
                "s0": 3, "s1": "", "x0": "1", "x1": "4.2.2", "x2": "Mac OS",
                "x3": "xhs-pc-web", "x4": "4.74.0", "x5": a1, "x6": x_t, "x7": x_s,
                "x8": b1, "x9": mrc(x_t + x_s + b1), "x10": 154, "x11": "normal",
            }
            # Custom base64 encode
            BASE64_CHARS = "ZmserbBoHQtNP+wOcza/LpngG8yJq42KWYj0DSfdikx3VT16IlUAFM97hECvuRX5"
            def b64_enc(data):
                result = []
                length = len(data)
                remaining = length % 3
                for i in range(0, length - remaining, 3):
                    chunk = (data[i] << 16) + (data[i + 1] << 8) + data[i + 2]
                    result.append(BASE64_CHARS[(chunk >> 18) & 63] + BASE64_CHARS[(chunk >> 12) & 63] + BASE64_CHARS[(chunk >> 6) & 63] + BASE64_CHARS[chunk & 63])
                if remaining == 1:
                    chunk = data[length - 1] << 16
                    result.append(BASE64_CHARS[(chunk >> 18) & 63] + BASE64_CHARS[(chunk >> 12) & 63] + "==")
                elif remaining == 2:
                    chunk = (data[length - 2] << 16) + (data[length - 1] << 8)
                    result.append(BASE64_CHARS[(chunk >> 18) & 63] + BASE64_CHARS[(chunk >> 12) & 63] + BASE64_CHARS[(chunk >> 6) & 63] + "=")
                return "".join(result)

            xs_common = b64_enc(json.dumps(xs_common_payload, separators=(',', ':')).encode('utf-8'))
            print('x-s-common:', xs_common[:50] + '...')

            cookie_str = '; '.join([f'{k}={v}' for k, v in cookie_dict.items()])
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Origin': 'https://www.xiaohongshu.com',
                'Referer': 'https://www.xiaohongshu.com/',
                'Content-Type': 'application/json;charset=UTF-8',
                'Cookie': cookie_str,
                'X-S': x_s,
                'X-T': x_t,
                'x-S-Common': xs_common,
                'X-B3-Traceid': hashlib.md5(str(time.time()).encode()).hexdigest()[:16],
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post('https://edith.xiaohongshu.com' + uri, headers=headers, json=data, timeout=30)
                result = resp.json()
                print('API response - code:', result.get('code', 'N/A'), 'success:', result.get('success', 'N/A'))
                if result.get('success'):
                    items = result.get('data', {}).get('items', [])
                    print('Found', len(items), 'notes!')
                    for item in items[:2]:
                        note = item.get('note_card', item)
                        title = note.get('title', 'No title')[:50]
                        print('  -', title)
                else:
                    print('Error:', result.get('msg', 'Unknown'))

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_fresh_session())
