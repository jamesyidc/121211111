#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从根文件夹找到今天日期的子文件夹
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def find_today_folder():
    """从根文件夹找到今天的日期文件夹"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    today = datetime.now(beijing_tz).strftime('%Y-%m-%d')
    
    print(f"查找日期文件夹: {today}")
    print(f"根文件夹: 1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            url = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            print(f"\n访问: {url}")
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            print("✅ 页面加载完成")
            
            await asyncio.sleep(3)
            
            content = await page.content()
            print(f"页面大小: {len(content)} bytes")
            
            # 查找今天的文件夹
            # 尝试找到文件夹ID的模式
            patterns = [
                rf'"{today}"[^"]*?"([A-Za-z0-9_-]{{20,}})"',
                rf'"({today})".*?"id":\s*"([A-Za-z0-9_-]{{20,}})"',
                rf'data-id="([A-Za-z0-9_-]{{20,}})"[^>]*>{today}',
            ]
            
            folder_ids = {}
            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    print(f"模式匹配到: {len(matches)} 个")
                    for match in matches:
                        if isinstance(match, tuple):
                            for item in match:
                                if len(item) > 20:
                                    folder_ids[item] = folder_ids.get(item, 0) + 1
                        elif len(match) > 20:
                            folder_ids[match] = folder_ids.get(match, 0) + 1
            
            # 尝试通过JavaScript获取
            js_result = await page.evaluate('''() => {
                const folders = [];
                const elements = document.querySelectorAll('[data-id]');
                elements.forEach(el => {
                    const text = el.textContent || '';
                    const id = el.getAttribute('data-id');
                    if (text.includes('2025-12-03') && id) {
                        folders.push({text: text.trim(), id: id});
                    }
                });
                return folders;
            }''')
            
            if js_result:
                print(f"\n✅ JavaScript找到 {len(js_result)} 个匹配:")
                for item in js_result:
                    print(f"  文本: {item['text'][:50]}")
                    print(f"  ID: {item['id']}")
                    folder_ids[item['id']] = folder_ids.get(item['id'], 0) + 10
            
            # 按出现次数排序
            if folder_ids:
                sorted_ids = sorted(folder_ids.items(), key=lambda x: x[1], reverse=True)
                print(f"\n找到 {len(sorted_ids)} 个可能的文件夹ID:")
                for folder_id, count in sorted_ids[:5]:
                    print(f"  {folder_id} (出现 {count} 次)")
                
                # 测试第一个
                best_id = sorted_ids[0][0]
                print(f"\n测试最可能的ID: {best_id}")
                
                # 访问该文件夹
                test_url = f"https://drive.google.com/drive/folders/{best_id}"
                await page.goto(test_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                test_content = await page.content()
                
                # 查找TXT文件
                txt_files = re.findall(r'2025-\d{2}-\d{2}_\d{4}\.txt', test_content)
                if txt_files:
                    print(f"✅ 确认！找到 {len(set(txt_files))} 个TXT文件")
                    print(f"最新的5个:")
                    for f in sorted(set(txt_files), reverse=True)[:5]:
                        print(f"  - {f}")
                    return best_id
                else:
                    print(f"❌ 该文件夹没有TXT文件")
            else:
                print("\n❌ 未找到任何文件夹ID")
                
        finally:
            await browser.close()
    
    return None

async def main():
    folder_id = await find_today_folder()
    if folder_id:
        print(f"\n{'='*60}")
        print(f"✅ 成功！今天的文件夹ID: {folder_id}")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"❌ 未找到今天的文件夹")
        print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
