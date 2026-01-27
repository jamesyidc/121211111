#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟人工操作：点击排序按钮，按修改时间排序
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def get_latest_file_by_sorting():
    """通过点击排序获取最新文件"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"{'='*60}")
    print(f"模拟人工操作获取最新文件")
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
            await asyncio.sleep(4)
            
            # 3. 查找并点击排序按钮
            print(f"3. 点击排序选项...")
            
            # 尝试多种排序按钮选择器
            sort_selectors = [
                '[aria-label*="Sort"]',
                '[aria-label*="排序"]',
                'button:has-text("Sort")',
                'button:has-text("排序")',
                '[data-tooltip*="Sort"]',
                '[data-tooltip*="排序"]',
                'text=Sort',
                'text=排序'
            ]
            
            clicked = False
            for selector in sort_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.click()
                        print(f"   ✅ 点击了排序按钮 (选择器: {selector})")
                        await asyncio.sleep(2)
                        clicked = True
                        break
                except:
                    pass
            
            if not clicked:
                print(f"   ⚠️ 未找到排序按钮，尝试右键菜单...")
                # 尝试右键点击文件列表区域
                try:
                    await page.mouse.click(500, 300, button='right')
                    await asyncio.sleep(1)
                except:
                    pass
            
            # 4. 选择"按修改时间排序"
            print(f"4. 选择按修改时间排序...")
            
            modified_selectors = [
                'text="Modified"',
                'text="修改时间"',
                'text="Date modified"',
                '[role="menuitem"]:has-text("Modified")',
                '[role="menuitem"]:has-text("修改")'
            ]
            
            for selector in modified_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.click()
                        print(f"   ✅ 选择了修改时间排序")
                        await asyncio.sleep(3)
                        break
                except:
                    pass
            
            # 5. 获取文件列表
            print(f"5. 读取文件列表...")
            content = await page.content()
            pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
            matches = re.findall(pattern, content)
            unique_files = sorted(set(matches), reverse=True)
            
            print(f"✅ 找到 {len(unique_files)} 个文件")
            
            # 显示前20个
            print(f"\n前20个文件:")
            for i, filename in enumerate(unique_files[:20], 1):
                match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
                if match:
                    time_str = f"{match.group(2)[:2]}:{match.group(2)[2:]}"
                    print(f"   {i:2d}. {filename} (时间: {time_str})")
            
            # 检查最新文件
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
                    
                    # 打开文件并读取内容
                    print(f"\n6. 打开第一个文件...")
                    # 先点击第一个文件，确保它被选中
                    try:
                        await page.locator(f'text="{latest}"').first.click()
                        print(f"   ✅ 点击了文件: {latest}")
                        await asyncio.sleep(1)
                    except:
                        print(f"   ⚠️ 无法直接点击，尝试Tab+Enter...")
                        await page.keyboard.press('Tab')
                        await asyncio.sleep(0.5)
                    
                    # 按Enter打开
                    await page.keyboard.press('Enter')
                    print(f"   等待文件预览加载...")
                    await asyncio.sleep(8)  # 等待更长时间
                    
                    # 从frame读取
                    print(f"   检查 {len(page.frames)} 个frame...")
                    for i, frame in enumerate(page.frames):
                        try:
                            frame_url = frame.url
                            print(f"   Frame {i}: {frame_url[:60]}...")
                            
                            text = await frame.evaluate('() => document.body.innerText')
                            if text and len(text) > 100:
                                # 使用更宽松的检测条件
                                has_data = ('[超级列表框_首页开始]' in text or 
                                           '透明标签' in text or 
                                           ('|' in text and 'BTC' in text))
                                
                                if has_data:
                                    print(f"   ✅ Frame {i} 包含数据 (长度: {len(text)})")
                                    
                                    # 提取数据部分
                                    lines = text.split('\n')
                                    data_lines = []
                                    recording = False
                                    for line in lines:
                                        if '透明标签' in line or '[超级列表框_首页开始]' in line:
                                            recording = True
                                        if recording:
                                            data_lines.append(line)
                                        if '[超级列表框_首页结束]' in line:
                                            break
                                    
                                    clean_content = '\n'.join(data_lines)
                                    
                                    return {
                                        'filename': latest,
                                        'folder_id': '1Ej3JlFylpaxRtcLIe1yD_MOxcxNck5mh',
                                        'time_diff': time_diff,
                                        'content': clean_content,
                                        'raw_text': text  # 保留原始文本用于调试
                                    }
                                elif len(text) > 200:
                                    print(f"   Frame {i} 有文本但不匹配 (长度: {len(text)})")
                                    # 显示部分内容用于调试
                                    print(f"   前200字符: {text[:200]}")
                        except Exception as e:
                            print(f"   Frame {i} 错误: {str(e)}")
                    
                    print(f"   ⚠️ 未能读取文件内容")
                    return {
                        'filename': latest,
                        'folder_id': '1Ej3JlFylpaxRtcLIe1yD_MOxcxNck5mh',
                        'time_diff': time_diff,
                        'content': None
                    }
            
        finally:
            await browser.close()

async def main():
    result = await get_latest_file_by_sorting()
    
    if result:
        print(f"\n{'='*60}")
        print(f"最终结果")
        print(f"{'='*60}")
        print(f"文件名: {result['filename']}")
        print(f"时间差: {result['time_diff']:.1f} 分钟")
        
        if result.get('content'):
            print(f"内容长度: {len(result['content'])} 字符")
            with open('/home/user/webapp/FINAL_SUCCESS.txt', 'w', encoding='utf-8') as f:
                f.write(result['content'])
            print(f"✅ 已保存: FINAL_SUCCESS.txt")
            print(f"\n内容预览:")
            print(result['content'][:500])
            return True
        else:
            print("❌ 未获取到内容")
            return False

if __name__ == "__main__":
    asyncio.run(main())
