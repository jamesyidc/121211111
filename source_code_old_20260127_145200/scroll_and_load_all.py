#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滚动页面加载所有文件，包括最新的
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def load_all_files_with_scroll():
    """滚动加载所有文件"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"{'='*60}")
    print(f"滚动加载所有文件")
    print(f"{'='*60}")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            # 1. 访问根文件夹
            url = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            print(f"1. 访问根文件夹...")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # 2. 进入今天的文件夹
            print(f"2. 进入 {today} 文件夹...")
            folder_selector = f'[data-tooltip*="{today}"]'
            await page.locator(folder_selector).first.dblclick()
            await asyncio.sleep(3)
            
            # 3. 滚动页面到顶部，确保加载最新文件
            print(f"3. 滚动到页面顶部...")
            await page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(2)
            
            # 4. 多次获取内容，看文件数量变化
            print(f"4. 检查文件列表...")
            
            previous_count = 0
            max_attempts = 10
            
            for attempt in range(max_attempts):
                # 获取当前页面内容
                content = await page.content()
                pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
                matches = re.findall(pattern, content)
                unique_files = sorted(set(matches), reverse=True)
                current_count = len(unique_files)
                
                print(f"   尝试 {attempt + 1}: 找到 {current_count} 个文件", end='')
                
                if current_count > previous_count:
                    print(f" (新增 {current_count - previous_count})")
                    previous_count = current_count
                else:
                    print(f" (无变化)")
                
                # 如果找到最新的文件（比如09:21），停止
                if any('_09' in f for f in unique_files[:5]):
                    print(f"   ✅ 检测到最新文件!")
                    break
                
                # 向上滚动，触发加载
                await page.evaluate('window.scrollBy(0, -500)')
                await asyncio.sleep(1)
                
                # 刷新页面内容
                await page.keyboard.press('F5')
                await asyncio.sleep(3)
            
            # 5. 最终结果
            content = await page.content()
            pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
            matches = re.findall(pattern, content)
            unique_files = sorted(set(matches), reverse=True)
            
            print(f"\n✅ 最终找到 {len(unique_files)} 个文件")
            print(f"\n最新的20个文件:")
            for i, filename in enumerate(unique_files[:20], 1):
                match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
                if match:
                    time_str = f"{match.group(2)[:2]}:{match.group(2)[2:]}"
                    print(f"   {i:2d}. {filename} (时间: {time_str})")
            
            # 最新文件
            if unique_files:
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
                        print(f"✅ 数据新鲜!")
                    else:
                        print(f"⚠️ 数据较旧")
                    
                    return {
                        'filename': latest,
                        'all_files': unique_files,
                        'time_diff': time_diff
                    }
            
        finally:
            await browser.close()

async def main():
    await load_all_files_with_scroll()

if __name__ == "__main__":
    asyncio.run(main())
