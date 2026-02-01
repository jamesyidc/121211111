import asyncio
from playwright.async_api import async_playwright
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

async def analyze():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
        await page.goto(folder_url, timeout=30000)
        await asyncio.sleep(3)
        
        html = await page.content()
        
        # 保存HTML
        with open('drive_folder.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML已保存到 drive_folder.html ({len(html)} 字节)")
        
        # 查找所有时间戳
        timestamps = re.findall(r'2025-12-06_(\d{4})', html)
        unique_times = sorted(set(timestamps), reverse=True)
        
        print(f"\n找到 {len(unique_times)} 个唯一时间戳:")
        for t in unique_times[:10]:
            print(f"  {t}")
        
        # 查找 "1220" 或 "1210" 附近的内容
        search_times = ['1220', '1210', '1200', '1150']
        
        for t in search_times:
            if t in html:
                # 查找该时间戳周围300个字符的内容
                pos = html.find(t)
                snippet = html[max(0, pos-150):min(len(html), pos+150)]
                
                print(f"\n时间 {t} 周围的内容片段:")
                print(f"  ...{snippet}...")
                
                # 查找附近的data-id
                snippet_larger = html[max(0, pos-500):min(len(html), pos+500)]
                id_match = re.search(r'data-id="([^"]+)"', snippet_larger)
                if id_match:
                    print(f"  附近的 data-id: {id_match.group(1)}")
        
        await browser.close()

asyncio.run(analyze())
