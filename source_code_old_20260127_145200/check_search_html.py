import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 搜索最新文件
        filename = "2025-12-06_1210.txt"
        search_url = f"https://drive.google.com/drive/search?q={filename}"
        
        print(f"访问搜索 URL: {search_url}")
        await page.goto(search_url, timeout=30000)
        await asyncio.sleep(3)
        
        html = await page.content()
        
        # 保存 HTML
        with open('search_result.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\nHTML 已保存到 search_result.html")
        print(f"HTML 长度: {len(html)} 字节")
        
        # 检查文件名是否在HTML中
        if filename in html:
            print(f"✓ 文件名在 HTML 中找到")
        else:
            print(f"✗ 文件名不在 HTML 中")
        
        # 查找可能的文件ID模式
        import re
        id_patterns = [
            r'data-id="([^"]+)"',
            r'data-target="([^"]+)"',
            r'id="([A-Za-z0-9_-]{20,})"',
            r'/file/d/([A-Za-z0-9_-]+)/',
        ]
        
        print(f"\n查找文件ID模式:")
        for pattern in id_patterns:
            matches = re.findall(pattern, html)
            if matches:
                print(f"  模式 {pattern}: 找到 {len(matches)} 个匹配")
                for match in matches[:3]:  # 只打印前3个
                    print(f"    - {match}")
        
        # 查找所有链接
        links = re.findall(r'href="([^"]*drive[^"]*)"', html)
        print(f"\n找到 {len(links)} 个 Drive 链接:")
        for link in links[:5]:  # 只打印前5个
            print(f"  {link}")
        
        await browser.close()

asyncio.run(check())
