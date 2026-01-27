#!/usr/bin/env python3
"""手动从Google Drive获取数据"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import pytz

async def fetch_data():
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"开始获取 {today} 的数据...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 访问根文件夹
            url = "https://drive.google.com/drive/folders/1-IfqZxMV9VCSg3ct6XVMyFtAbuCV3huQ"
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # 查找今天的文件夹
            folder = await page.locator(f'[data-tooltip*="{today}"]').first
            await folder.dblclick()
            await asyncio.sleep(4)
            
            # 查找恐慌清洗.txt文件
            file_elem = await page.locator('[data-tooltip*="恐慌清洗.txt"]').first
            await file_elem.click()
            await asyncio.sleep(3)
            
            # 获取页面内容
            content = await page.content()
            
            # 尝试多种方法提取数据
            # 方法1: 查找包含竖线的行
            import re
            pattern = r'(\d+\.?\d*-[^|]+)\|([^<]+)'
            matches = re.findall(pattern, content)
            
            if matches:
                print(f"\n找到 {len(matches)} 条数据")
                for match in matches[:3]:  # 只显示前3条
                    print(f"数据: {match[0]}|{match[1]}")
                
                # 保存第一条（最新）数据
                if matches:
                    latest = f"{matches[0][0]}|{matches[0][1]}"
                    with open('/home/user/webapp/panic_wash_latest.txt', 'w') as f:
                        f.write(latest)
                    print(f"\n✅ 已保存到 panic_wash_latest.txt")
                    print(f"内容: {latest}")
            else:
                print("❌ 未找到数据")
                
        except Exception as e:
            print(f"错误: {e}")
        finally:
            await browser.close()

asyncio.run(fetch_data())
