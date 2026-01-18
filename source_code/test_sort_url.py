import asyncio
from playwright.async_api import async_playwright
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 尝试不同的排序 URL
        urls = [
            f"https://drive.google.com/drive/folders/{FOLDER_ID}",
            f"https://drive.google.com/drive/folders/{FOLDER_ID}?sort=13&direction=d",  # 按修改时间降序
            f"https://drive.google.com/drive/u/0/folders/{FOLDER_ID}?sort=13&direction=d",
        ]
        
        for test_url in urls:
            print(f"\n{'='*70}")
            print(f"测试 URL: {test_url}")
            print(f"{'='*70}")
            
            try:
                await page.goto(test_url, timeout=30000)
                await asyncio.sleep(3)
                
                # 多次滚动加载更多文件
                for i in range(5):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1)
                
                html = await page.content()
                
                # 查找所有 .txt 文件
                txt_files = re.findall(r'2025-12-06_(\d{4})\.txt', html)
                
                if txt_files:
                    unique_times = sorted(set(txt_files), reverse=True)
                    print(f"找到 {len(unique_times)} 个唯一时间戳:")
                    for time in unique_times[:10]:  # 只显示前10个
                        print(f"  {time}")
                    print(f"\n最新: 2025-12-06_{unique_times[0]}.txt")
                    print(f"最旧: 2025-12-06_{unique_times[-1]}.txt")
                else:
                    print("未找到任何 .txt 文件")
                
            except Exception as e:
                print(f"错误: {e}")
        
        await browser.close()

asyncio.run(test())
