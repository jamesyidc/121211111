#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接用浏览器访问用户提供的链接
模拟真实的人工访问
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def access_with_real_browser():
    """用真实浏览器访问"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    
    print(f"{'='*60}")
    print(f"用浏览器直接访问Google Drive")
    print(f"{'='*60}")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        # 使用更真实的浏览器配置
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN'
        )
        
        # 隐藏自动化特征
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        try:
            # 访问用户提供的链接
            url = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            
            print(f"1. 访问链接: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # 点击进入2025-12-03文件夹
            print(f"2. 查找并进入 2025-12-03 文件夹...")
            today = now.strftime('%Y-%m-%d')
            
            # 尝试点击文件夹
            try:
                folder_selector = f'[data-tooltip*="{today}"]'
                await page.locator(folder_selector).first.dblclick()
                print(f"✅ 已进入 {today} 文件夹")
                await asyncio.sleep(4)  # 等待文件列表加载
            except Exception as e:
                print(f"❌ 无法进入文件夹: {str(e)}")
                return None
            
            # 获取当前页面的所有文本内容
            print(f"3. 读取文件列表...")
            page_content = await page.content()
            
            # 提取所有TXT文件
            pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
            matches = re.findall(pattern, page_content)
            
            if matches:
                unique_files = sorted(set(matches), reverse=True)
                print(f"✅ 找到 {len(unique_files)} 个文件")
                
                print(f"\n所有TXT文件（按时间倒序）:")
                for i, filename in enumerate(unique_files, 1):
                    match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
                    if match:
                        time_str = f"{match.group(2)[:2]}:{match.group(2)[2:]}"
                        print(f"   {i:2d}. {filename} (时间: {time_str})")
                
                # 最新文件
                latest = unique_files[0]
                match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', latest)
                if match:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    file_time = datetime.strptime(f"{date_str} {time_str[:2]}:{time_str[2:]}", "%Y-%m-%d %H:%M")
                    time_diff = (now.replace(tzinfo=None) - file_time).total_seconds() / 60
                    
                    print(f"\n{'='*60}")
                    print(f"最新文件")
                    print(f"{'='*60}")
                    print(f"文件名: {latest}")
                    print(f"文件时间: {time_str[:2]}:{time_str[2:]}")
                    print(f"当前时间: {now.strftime('%H:%M')}")
                    print(f"时间差: {time_diff:.1f} 分钟")
                    
                    if time_diff < 15:
                        print(f"✅ 数据新鲜（<15分钟）")
                    else:
                        print(f"⚠️ 数据较旧（{time_diff:.1f}分钟）")
                    
                    return {
                        'filename': latest,
                        'all_files': unique_files,
                        'total': len(unique_files),
                        'time_diff': time_diff
                    }
            else:
                print("❌ 未找到任何TXT文件")
                
                # 保存页面用于调试
                with open('/home/user/webapp/page_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_content)
                print("已保存页面HTML: page_debug.html")
                
                return None
                
        finally:
            await browser.close()

async def main():
    result = await access_with_real_browser()
    
    if result:
        print(f"\n{'='*60}")
        print(f"总结")
        print(f"{'='*60}")
        print(f"总共找到: {result['total']} 个文件")
        print(f"最新文件: {result['filename']}")
        print(f"数据延迟: {result['time_diff']:.1f} 分钟")

if __name__ == "__main__":
    asyncio.run(main())
