#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只查找最新的TXT文件，不提取内容
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def find_latest_txt_file():
    """只查找最新的TXT文件"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"{'='*60}")
    print(f"查找最新TXT文件")
    print(f"{'='*60}")
    print(f"当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"查找日期: {today}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 1. 访问根文件夹
            root_folder_id = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            root_url = f"https://drive.google.com/drive/folders/{root_folder_id}"
            
            print(f"1. 访问根文件夹...")
            await page.goto(root_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # 2. 查找今天的文件夹
            print(f"2. 查找今天的文件夹 ({today})...")
            folder_result = await page.evaluate(f'''() => {{
                const elements = document.querySelectorAll('[data-id]');
                for (let el of elements) {{
                    const text = el.textContent || '';
                    const id = el.getAttribute('data-id');
                    if (text.includes('{today}') && id) {{
                        return id;
                    }}
                }}
                return null;
            }}''')
            
            if not folder_result:
                print(f"❌ 未找到 {today} 文件夹")
                return None
            
            print(f"✅ 找到文件夹")
            print(f"   文件夹ID: {folder_result}")
            
            # 3. 访问今天的文件夹
            today_url = f"https://drive.google.com/drive/folders/{folder_result}"
            print(f"\n3. 访问今天的文件夹...")
            await page.goto(today_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)  # 给足够时间加载
            
            # 4. 获取所有TXT文件
            print(f"4. 获取文件列表...")
            content = await page.content()
            pattern = r'(2025-\d{2}-\d{2}_\d{4}\.txt)'
            matches = re.findall(pattern, content)
            
            if not matches:
                print("❌ 未找到任何TXT文件")
                return None
            
            # 去重并排序
            unique_files = sorted(set(matches), reverse=True)
            
            print(f"✅ 找到 {len(unique_files)} 个TXT文件")
            
            # 显示所有文件
            print(f"\n文件列表（按时间倒序）:")
            for i, filename in enumerate(unique_files[:10], 1):
                # 提取时间
                match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
                if match:
                    time_str = f"{match.group(2)[:2]}:{match.group(2)[2:]}"
                    print(f"   {i}. {filename} (时间: {time_str})")
            
            if len(unique_files) > 10:
                print(f"   ... 还有 {len(unique_files) - 10} 个文件")
            
            # 5. 获取最新文件
            latest_filename = unique_files[0]
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', latest_filename)
            
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                file_time = datetime.strptime(f"{date_str} {time_str[:2]}:{time_str[2:]}", "%Y-%m-%d %H:%M")
                time_diff = (now.replace(tzinfo=None) - file_time).total_seconds() / 60
                
                print(f"\n{'='*60}")
                print(f"最新文件")
                print(f"{'='*60}")
                print(f"文件名: {latest_filename}")
                print(f"文件时间: {time_str[:2]}:{time_str[2:]}")
                print(f"当前时间: {now.strftime('%H:%M')}")
                print(f"时间差: {time_diff:.1f} 分钟")
                
                if time_diff < 15:
                    print(f"状态: ✅ 数据较新（<15分钟）")
                else:
                    print(f"状态: ⚠️ 数据较旧（{time_diff:.1f}分钟）")
                
                return {
                    'filename': latest_filename,
                    'folder_id': folder_result,
                    'file_time': file_time,
                    'time_diff_minutes': time_diff,
                    'total_files': len(unique_files)
                }
            
        finally:
            await browser.close()

async def main():
    result = await find_latest_txt_file()
    
    if not result:
        print(f"\n{'='*60}")
        print("查找失败")
        print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
