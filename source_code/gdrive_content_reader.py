#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接从Google Drive页面读取文件预览内容
模拟人工浏览的方式
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def read_file_content_from_preview(folder_id: str, filename: str):
    """
    打开文件预览并读取内容
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            print(f"访问文件夹: {folder_url}")
            
            await page.goto(folder_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            print(f"查找文件: {filename}")
            
            # 找到文件并双击打开预览
            # 尝试多种选择器
            selectors = [
                f'[data-tooltip*="{filename}"]',
                f'[aria-label*="{filename}"]',
                f'[title*="{filename}"]',
                f'text="{filename}"'
            ]
            
            file_element = None
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        file_element = elements[0]
                        print(f"✅ 找到文件元素 (选择器: {selector})")
                        break
                except:
                    continue
            
            if not file_element:
                print("❌ 未找到文件元素，尝试搜索...")
                # 尝试使用搜索功能
                await page.keyboard.press('/')
                await asyncio.sleep(0.5)
                await page.keyboard.type(filename)
                await asyncio.sleep(2)
                await page.keyboard.press('Enter')
                await asyncio.sleep(3)
            else:
                # 双击打开文件
                print("双击打开文件...")
                await file_element.dblclick()
                await asyncio.sleep(5)  # 等待预览加载
            
            # 尝试从多个位置读取内容
            print("尝试读取预览内容...")
            
            # 方法1: 从iframe读取
            frames = page.frames
            for frame in frames:
                try:
                    content = await frame.content()
                    if len(content) > 1000 and ('[超级列表框_首页开始]' in content or '|' in content):
                        print(f"✅ 从iframe读取到内容 (长度: {len(content)})")
                        return content
                except:
                    pass
            
            # 方法2: 从主页面的预览区域读取
            preview_selectors = [
                '[role="dialog"]',
                '.docs-texteventtarget-iframe',
                '[data-id*="preview"]',
                'pre',
                'textarea'
            ]
            
            for selector in preview_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements:
                        text = await el.text_content()
                        if text and len(text) > 100:
                            print(f"✅ 从预览区域读取到内容 (选择器: {selector}, 长度: {len(text)})")
                            return text
                except:
                    pass
            
            # 方法3: 获取整个页面文本
            page_text = await page.evaluate('() => document.body.innerText')
            if '[超级列表框_首页开始]' in page_text:
                print(f"✅ 从页面文本读取到内容 (长度: {len(page_text)})")
                return page_text
            
            # 方法4: 直接构造预览URL
            print("尝试直接访问预览URL...")
            # 从当前URL获取文件ID
            current_url = page.url
            file_id_match = re.search(r'/file/d/([^/]+)', current_url)
            if file_id_match:
                file_id = file_id_match.group(1)
                preview_url = f"https://drive.google.com/file/d/{file_id}/preview"
                print(f"预览URL: {preview_url}")
                await page.goto(preview_url, wait_until='networkidle')
                await asyncio.sleep(3)
                
                # 从预览页读取
                for frame in page.frames:
                    try:
                        content = await frame.content()
                        if len(content) > 1000:
                            print(f"✅ 从预览页读取到内容 (长度: {len(content)})")
                            return content
                    except:
                        pass
            
            print("❌ 无法读取文件内容")
            # 保存截图用于调试
            await page.screenshot(path='/home/user/webapp/debug_preview.png')
            print("已保存截图: debug_preview.png")
            
            return None
            
        finally:
            await browser.close()

async def get_latest_file_content():
    """获取最新文件内容"""
    root_folder_id = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
    beijing_tz = pytz.timezone('Asia/Shanghai')
    today = datetime.now(beijing_tz).strftime('%Y-%m-%d')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 1. 找今天的文件夹
            root_url = f"https://drive.google.com/drive/folders/{root_folder_id}"
            print(f"1. 查找 {today} 文件夹...")
            await page.goto(root_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
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
            
            print(f"✅ 文件夹ID: {folder_result}")
            
            # 2. 获取最新文件名
            today_url = f"https://drive.google.com/drive/folders/{folder_result}"
            await page.goto(today_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            content = await page.content()
            pattern = r'(2025-\d{2}-\d{2}_\d{4}\.txt)'
            matches = re.findall(pattern, content)
            
            if not matches:
                print("❌ 未找到TXT文件")
                return None
            
            unique_files = sorted(set(matches), reverse=True)
            latest_filename = unique_files[0]
            
            print(f"✅ 最新文件: {latest_filename}")
            
        finally:
            await browser.close()
    
    # 3. 读取文件内容
    print(f"\n2. 读取文件内容...")
    content = await read_file_content_from_preview(folder_result, latest_filename)
    
    return {
        'filename': latest_filename,
        'folder_id': folder_result,
        'content': content
    }

async def main():
    result = await get_latest_file_content()
    
    print(f"\n{'='*60}")
    print("结果")
    print(f"{'='*60}")
    
    if result:
        print(f"文件名: {result['filename']}")
        if result['content']:
            print(f"内容长度: {len(result['content'])} 字符")
            print(f"\n内容预览:")
            print(result['content'][:500])
        else:
            print("内容: 无法读取")

if __name__ == "__main__":
    asyncio.run(main())
