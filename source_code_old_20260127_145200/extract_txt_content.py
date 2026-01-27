#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Google Drive提取TXT文件的纯文本内容
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def extract_txt_file_content(folder_id: str, filename: str):
    """
    打开TXT文件并提取纯文本内容
    """
    async with async_playwright() as p:
        # 使用非无头模式看看到底发生了什么
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            print(f"访问: {folder_url}")
            
            await page.goto(folder_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            print(f"查找并打开文件: {filename}")
            
            # 找到文件元素
            file_locator = page.locator(f'[data-tooltip*="{filename}"]').first
            
            # 双击打开
            await file_locator.dblclick()
            print("已双击文件，等待预览加载...")
            await asyncio.sleep(5)
            
            # TXT文件在Google Drive中会以纯文本预览
            # 查找包含文本内容的iframe或元素
            
            # 方法1: 检查所有iframe
            print("检查iframe...")
            frames = page.frames
            print(f"找到 {len(frames)} 个frame")
            
            for i, frame in enumerate(frames):
                try:
                    frame_url = frame.url
                    print(f"  Frame {i}: {frame_url[:80]}...")
                    
                    # TXT预览通常在一个iframe中
                    if 'docs.google.com' in frame_url or 'drive.google.com' in frame_url:
                        # 尝试获取文本
                        text_content = await frame.evaluate('() => document.body.innerText')
                        
                        if text_content and len(text_content) > 50:
                            # 检查是否包含我们期待的内容
                            if '[超级列表框_首页开始]' in text_content or ('|' in text_content and 'BTC' in text_content):
                                print(f"✅ 找到TXT内容! (Frame {i}, 长度: {len(text_content)})")
                                return text_content
                            elif len(text_content) > 200:
                                print(f"  Frame {i} 有文本但不匹配 (长度: {len(text_content)})")
                                print(f"  预览: {text_content[:100]}")
                except Exception as e:
                    print(f"  Frame {i} 错误: {str(e)}")
            
            # 方法2: 查找特定的文本预览元素
            print("\n尝试查找预览元素...")
            selectors = [
                'pre',  # TXT文件通常在<pre>标签中
                '[role="textbox"]',
                '.docs-text-rendering',
                '[data-id="text-content"]'
            ]
            
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    print(f"  选择器 '{selector}': {len(elements)} 个元素")
                    for el in elements:
                        text = await el.text_content()
                        if text and len(text) > 50:
                            if '[超级列表框_首页开始]' in text or ('|' in text and 'BTC' in text):
                                print(f"✅ 从元素读取到内容! (选择器: {selector})")
                                return text
                except Exception as e:
                    print(f"  选择器 '{selector}' 错误: {str(e)}")
            
            # 方法3: 等待特定内容出现
            print("\n等待特定内容出现...")
            try:
                await page.wait_for_function(
                    '''() => document.body.innerText.includes('[超级列表框_首页开始]') || 
                           document.body.innerText.includes('透明标签')''',
                    timeout=10000
                )
                text_content = await page.evaluate('() => document.body.innerText')
                print(f"✅ 内容已加载! (长度: {len(text_content)})")
                return text_content
            except:
                print("  等待超时")
            
            # 方法4: 使用正则从页面源码提取
            print("\n从页面源码提取...")
            page_content = await page.content()
            
            # 查找可能包含文本的JSON数据
            json_matches = re.findall(r'"([^"]*\[超级列表框_首页开始\][^"]*)"', page_content)
            if json_matches:
                print(f"✅ 从JSON提取到内容!")
                # 解码转义字符
                content = json_matches[0]
                content = content.replace('\\n', '\n').replace('\\t', '\t')
                return content
            
            print("❌ 无法提取文本内容")
            await page.screenshot(path='/home/user/webapp/txt_preview_debug.png', full_page=True)
            print("已保存完整页面截图: txt_preview_debug.png")
            
            return None
            
        finally:
            await browser.close()

async def main():
    beijing_tz = pytz.timezone('Asia/Shanghai')
    today = datetime.now(beijing_tz).strftime('%Y-%m-%d')
    
    # 这是2025-12-03文件夹的ID
    folder_id = "1Ej3JlFylpaxRtcLIe1yD_MOxcxNck5mh"
    filename = "2025-12-03_0821.txt"
    
    print(f"{'='*60}")
    print(f"提取TXT文件内容")
    print(f"{'='*60}")
    print(f"文件夹: {folder_id}")
    print(f"文件名: {filename}")
    print(f"{'='*60}\n")
    
    content = await extract_txt_file_content(folder_id, filename)
    
    print(f"\n{'='*60}")
    print("结果")
    print(f"{'='*60}")
    
    if content:
        print(f"✅ 成功提取内容!")
        print(f"内容长度: {len(content)} 字符")
        print(f"\n前500个字符:")
        print(content[:500])
        print(f"\n后500个字符:")
        print(content[-500:])
        
        # 保存到文件
        with open('/home/user/webapp/extracted_content.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✅ 已保存到: extracted_content.txt")
    else:
        print("❌ 提取失败")

if __name__ == "__main__":
    asyncio.run(main())
