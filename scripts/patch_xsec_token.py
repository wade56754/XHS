#!/usr/bin/env python3
"""
补丁脚本：修改 MediaCrawler 的人工搜索功能，添加 xsec_token 提取
"""
import re

# 需要替换的旧代码片段
OLD_EXTRACT_JS = '''                // 只要有 ID 或标题就添加
                if (noteId || (title && title.length > 2)) {
                    results.push({
                        note_id: noteId || null,
                        title: title || '无标题',
                        author: author || '未知',
                        likes: likes || '0',
                        cover: cover || null,
                        raw_html: card.outerHTML?.substring(0, 200)  // 调试用
                    });
                }'''

# 新代码：添加 xsec_token 提取
NEW_EXTRACT_JS = '''                // 提取 xsec_token - 从链接的 URL 参数中获取
                let xsecToken = null;
                const allLinksForToken = card.querySelectorAll('a[href]');
                for (const link of allLinksForToken) {
                    const href = link.href || link.getAttribute('href') || '';
                    // 尝试从 URL 参数中提取 xsec_token
                    const tokenMatch = href.match(/xsec_token=([^&]+)/);
                    if (tokenMatch) {
                        xsecToken = decodeURIComponent(tokenMatch[1]);
                        break;
                    }
                }

                // 备用方案：从 data 属性中提取
                if (!xsecToken) {
                    xsecToken = card.getAttribute('data-xsec-token') ||
                                card.getAttribute('data-token') ||
                                null;
                }

                // 只要有 ID 或标题就添加
                if (noteId || (title && title.length > 2)) {
                    results.push({
                        note_id: noteId || null,
                        xsec_token: xsecToken,
                        title: title || '无标题',
                        author: author || '未知',
                        likes: likes || '0',
                        cover: cover || null,
                        raw_html: card.outerHTML?.substring(0, 200)  // 调试用
                    });
                }'''

def apply_patch(content: str) -> str:
    """应用补丁"""
    if 'xsec_token: xsecToken' in content:
        print("补丁已应用，跳过")
        return content

    # 查找并替换
    if OLD_EXTRACT_JS.strip() in content:
        new_content = content.replace(OLD_EXTRACT_JS.strip(), NEW_EXTRACT_JS.strip())
        print("成功应用 xsec_token 提取补丁")
        return new_content
    else:
        # 尝试更宽松的匹配
        pattern = r"// 只要有 ID 或标题就添加\s+if \(noteId \|\| \(title && title\.length > 2\)\) \{[^}]+\}"
        if re.search(pattern, content, re.DOTALL):
            new_content = re.sub(pattern, NEW_EXTRACT_JS.strip(), content, flags=re.DOTALL)
            print("使用正则表达式成功应用补丁")
            return new_content
        else:
            print("警告：未找到匹配的代码片段，无法应用补丁")
            return content

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python patch_xsec_token.py <main.py路径>")
        sys.exit(1)

    filepath = sys.argv[1]

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = apply_patch(content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"已保存到 {filepath}")
    else:
        print("无需修改")
