#!/usr/bin/env python3
"""Add x-xray-traceid header to sign_with_playwright return"""

# Read the file
with open('/app/xhs_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add x-xray-traceid to sign_with_playwright return
old_return = '''    return {
        "x-s": x_s,
        "x-t": x_t,
        "x-s-common": _build_xs_common(a1, b1, x_s, x_t),
        "x-b3-traceid": get_trace_id(),
    }'''

new_return = '''    trace_id = get_trace_id()
    return {
        "x-s": x_s,
        "x-t": x_t,
        "x-s-common": _build_xs_common(a1, b1, x_s, x_t),
        "x-b3-traceid": trace_id,
        "x-xray-traceid": trace_id,
    }'''

if old_return in content:
    content = content.replace(old_return, new_return)
    print("Added x-xray-traceid to return dict")
else:
    print("WARNING: Could not find return block in sign_with_playwright")

# Add x-xray-traceid to request headers
old_headers_update = """        headers.update({
            'X-S': sign_result.get('x-s', ''),
            'X-T': sign_result.get('x-t', str(int(time.time() * 1000))),
            'x-S-Common': sign_result.get('x-s-common', ''),
            'X-B3-Traceid': sign_result.get('x-b3-traceid', ''),
        })"""

new_headers_update = """        headers.update({
            'X-S': sign_result.get('x-s', ''),
            'X-T': sign_result.get('x-t', str(int(time.time() * 1000))),
            'x-S-Common': sign_result.get('x-s-common', ''),
            'X-B3-Traceid': sign_result.get('x-b3-traceid', ''),
            'x-xray-traceid': sign_result.get('x-xray-traceid', ''),
        })"""

if old_headers_update in content:
    content = content.replace(old_headers_update, new_headers_update)
    print("Added x-xray-traceid to request headers")
else:
    print("WARNING: Could not find headers update block")

# Write back
with open('/app/xhs_client.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch complete")
