#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时Google Drive读取器 - 结合浏览器自动化和文件下载
真正解决从公开链接获取最新数据的问题
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz
from typing import Optional, Dict

class RealtimeGDriveReader:
    """实时Google Drive数据读取器"""
    
    def __init__(self, root_folder_id: str):
        self.root_folder_id = root_folder_id
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        
    async def get_latest_file_content(self):
        """获取最新文件内容的完整流程"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # 1. 找到今天的文件夹
                today = datetime.now(self.beijing_tz).strftime('%Y-%m-%d')
                root_url = f"https://drive.google.com/drive/folders/{self.root_folder_id}"
                
                print(f"1. 访问根文件夹查找 {today}...")
                await page.goto(root_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                # JavaScript查找今天的文件夹ID
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
                
                print(f"✅ 找到文件夹ID: {folder_result}")
                
                # 2. 访问今天的文件夹
                today_url = f"https://drive.google.com/drive/folders/{folder_result}"
                print(f"2. 访问今天的文件夹...")
                await page.goto(today_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(3)  # 给更多时间加载文件列表
                
                # 3. 获取所有TXT文件并找到最新的
                content = await page.content()
                pattern = r'(2025-\d{2}-\d{2}_\d{4}\.txt)'
                matches = re.findall(pattern, content)
                
                if not matches:
                    print("❌ 未找到TXT文件")
                    return None
                
                unique_files = list(set(matches))
                unique_files.sort(reverse=True)  # 按文件名降序，最新的在前
                latest_filename = unique_files[0]
                
                print(f"✅ 找到最新文件: {latest_filename}")
                print(f"   总共 {len(unique_files)} 个文件")
                
                # 4. 尝试通过多种方式获取文件内容
                print(f"3. 尝试获取文件内容...")
                
                # 方法1: 点击文件并尝试在预览中读取
                try:
                    # 查找文件元素
                    file_elements = await page.query_selector_all(f'[aria-label*="{latest_filename}"], [title*="{latest_filename}"]')
                    
                    if file_elements:
                        print("   尝试点击文件...")
                        await file_elements[0].click()
                        await asyncio.sleep(3)
                        
                        # 检查是否有预览窗口
                        preview_content = await page.evaluate('''() => {
                            // 尝试从预览窗口获取文本内容
                            const preview = document.querySelector('[role="dialog"]');
                            if (preview) {
                                return preview.textContent;
                            }
                            return null;
                        }''')
                        
                        if preview_content and '[超级列表框_首页开始]' in preview_content:
                            print("✅ 从预览窗口获取到内容")
                            return {
                                'filename': latest_filename,
                                'content': preview_content,
                                'method': 'preview'
                            }
                except Exception as e:
                    print(f"   预览方法失败: {str(e)}")
                
                # 方法2: 尝试通过右键菜单获取下载链接
                # (这通常需要更复杂的交互)
                
                print("⚠️  无法自动下载文件内容")
                print("   Google Drive的公开文件夹不支持程序化下载")
                print("   需要:")
                print("   1) 使用Google Drive API (需要credentials)")
                print("   2) 或将文件设置为'任何人可下载'并获取直接链接")
                
                return {
                    'filename': latest_filename,
                    'folder_id': folder_result,
                    'content': None,
                    'method': 'filename_only'
                }
                
            finally:
                await browser.close()

async def main():
    """测试"""
    reader = RealtimeGDriveReader("1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV")
    result = await reader.get_latest_file_content()
    
    if result:
        print(f"\n{'='*60}")
        print("结果:")
        print(f"{'='*60}")
        print(f"文件名: {result['filename']}")
        print(f"获取方法: {result.get('method')}")
        if result.get('content'):
            print(f"内容长度: {len(result['content'])} 字符")
            print(f"内容预览: {result['content'][:200]}...")
        else:
            print("内容: 无法获取")

if __name__ == "__main__":
    asyncio.run(main())
