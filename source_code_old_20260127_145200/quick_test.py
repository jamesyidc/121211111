import asyncio
from playwright.async_api import async_playwright
import re

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await (await browser.new_context(viewport={'width': 1920, 'height': 1080})).new_page()
        
        try:
            await page.goto("https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV", wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            await page.locator('[data-tooltip*="2025-12-03"]').first.dblclick()
            await asyncio.sleep(3)
            
            # 使用之前成功的方法
            await page.locator('button:has-text("Sort")').first.click()
            await asyncio.sleep(2)
            await page.locator('text="Modified"').first.click()
            await asyncio.sleep(3)
            
            content = await page.content()
            files = sorted(set(re.findall(r'2025-\d{2}-\d{2}_\d{4}\.txt', content)), reverse=True)
            print(f"找到 {len(files)} 个文件")
            print(f"最新: {files[0] if files else '无'}")
            
            # 按Enter打开第一个
            await page.keyboard.press('Enter')
            await asyncio.sleep(6)
            
            # 读取
            for frame in page.frames:
                try:
                    text = await frame.evaluate('() => document.body.innerText')
                    if '透明标签' in text:
                        print(f"✅ 成功获取内容，长度: {len(text)}")
                        with open('/home/user/webapp/final_result.txt', 'w', encoding='utf-8') as f:
                            f.write(text)
                        print("✅ 已保存: final_result.txt")
                        return True
                except:
                    pass
            
            print("❌ 未读取到内容")
            return False
            
        finally:
            await browser.close()

asyncio.run(test())
