#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终工作版本：在一个浏览器会话中完成所有操作
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def get_latest_file_content():
    """获取最新文件内容 - 完整流程"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"开始获取最新数据... {now.strftime('%H:%M:%S')}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. 访问根文件夹并进入今天的文件夹
            print("1. 访问文件夹...")
            url = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            print("2. 进入今天文件夹...")
            await page.locator(f'[data-tooltip*="{today}"]').first.dblclick()
            await asyncio.sleep(4)
            
            # 2. 点击排序按钮
            print("3. 点击排序...")
            sort_selectors = [
                'button:has-text("Sort")',
                'button:has-text("排序")'
            ]
            
            for selector in sort_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.click()
                        print("   ✅ 点击了排序按钮")
                        await asyncio.sleep(2)
                        break
                except:
                    pass
            
            # 3. 选择按修改时间排序
            print("4. 选择按修改时间排序...")
            modified_selectors = [
                'text="Modified"',
                'text="修改时间"',
                '[role="menuitem"]:has-text("Modified")'
            ]
            
            for selector in modified_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.click()
                        print("   ✅ 选择了修改时间排序")
                        await asyncio.sleep(3)
                        break
                except:
                    pass
            
            # 4. 获取最新文件名
            print("5. 获取文件列表...")
            content = await page.content()
            pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
            matches = re.findall(pattern, content)
            unique_files = sorted(set(matches), reverse=True)
            
            if not unique_files:
                print("❌ 未找到文件")
                return None
            
            latest_filename = unique_files[0]
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', latest_filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                file_time = datetime.strptime(f"{date_str} {time_str[:2]}:{time_str[2:]}", "%Y-%m-%d %H:%M")
                time_diff = (now.replace(tzinfo=None) - file_time).total_seconds() / 60
                
                print(f"✅ 最新文件: {latest_filename}")
                print(f"   文件时间: {time_str[:2]}:{time_str[2:]}")
                print(f"   时间差: {time_diff:.1f} 分钟\n")
            
            # 5. 打开第一个文件（现在已经是最新的了）
            print("6. 打开文件...")
            # 按Enter键打开第一个选中的文件
            await page.keyboard.press('Enter')
            print("   等待文件预览加载...")
            await asyncio.sleep(6)
            
            # 6. 从所有frame中读取内容
            print("7. 读取文件内容...")
            frames = page.frames
            print(f"   检查 {len(frames)} 个frame...")
            
            for i, frame in enumerate(frames):
                try:
                    text_content = await frame.evaluate('() => document.body.innerText')
                    
                    if text_content and len(text_content) > 50:
                        # 检查是否包含我们需要的数据
                        if '[超级列表框_首页开始]' in text_content or ('透明标签' in text_content and '|' in text_content):
                            print(f"   ✅ Frame {i} 包含数据 (长度: {len(text_content)})")
                            
                            # 提取核心数据部分
                            lines = text_content.split('\n')
                            data_lines = []
                            in_data_section = False
                            
                            for line in lines:
                                if '透明标签' in line or '[超级列表框_首页开始]' in line:
                                    in_data_section = True
                                
                                if in_data_section:
                                    data_lines.append(line)
                                
                                if '[超级列表框_首页结束]' in line:
                                    break
                            
                            clean_content = '\n'.join(data_lines)
                            
                            return {
                                'filename': latest_filename,
                                'content': clean_content,
                                'raw_content': text_content,
                                'time_diff': time_diff
                            }
                except Exception as e:
                    pass
            
            print("   ❌ 未能从任何frame读取到数据")
            return None
            
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            await browser.close()

async def main():
    result = await get_latest_file_content()
    
    if result and result['content']:
        print(f"\n{'='*60}")
        print("✅ 成功！")
        print(f"{'='*60}")
        print(f"文件名: {result['filename']}")
        print(f"内容长度: {len(result['content'])} 字符")
        print(f"时间差: {result['time_diff']:.1f} 分钟")
        
        # 保存到文件
        with open('/home/user/webapp/latest_home_content.txt', 'w', encoding='utf-8') as f:
            f.write(result['content'])
        print(f"✅ 已保存到: latest_home_content.txt")
        
        # 显示前500个字符
        print(f"\n内容预览:")
        print(result['content'][:500])
        print(f"\n... (共 {len(result['content'])} 字符)")
        
        return True
    else:
        print(f"\n{'='*60}")
        print("❌ 失败")
        print(f"{'='*60}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
