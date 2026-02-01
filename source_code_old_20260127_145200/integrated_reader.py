#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成的读取器：一个浏览器会话完成所有操作
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def read_latest_file():
    """完整流程：找到最新文件并读取内容"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"开始获取最新数据...{now.strftime('%H:%M:%S')}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. 访问根文件夹
            await page.goto("https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV", 
                          wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # 2. 进入今天的文件夹
            await page.locator(f'[data-tooltip*="{today}"]').first.dblclick()
            await asyncio.sleep(3)
            
            # 3. 触发排序（使用JavaScript直接点击）
            await page.evaluate('''() => {
                const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
                const sortBtn = buttons.find(b => (b.textContent || '').includes('Sort'));
                if (sortBtn) sortBtn.click();
            }''')
            await asyncio.sleep(1)
            
            # 4. 选择Modified排序
            await page.evaluate('''() => {
                const items = Array.from(document.querySelectorAll('[role="menuitem"], div, span'));
                const modItem = items.find(i => (i.textContent || '').trim() === 'Modified');
                if (modItem) modItem.click();
            }''')
            await asyncio.sleep(3)
            
            # 5. 获取最新文件名
            content = await page.content()
            matches = re.findall(r'2025-\d{2}-\d{2}_\d{4}\.txt', content)
            unique_files = sorted(set(matches), reverse=True)
            
            if not unique_files:
                print("❌ 未找到文件")
                return None
            
            latest_filename = unique_files[0]
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', latest_filename)
            time_str = match.group(2)
            print(f"✅ 最新文件: {latest_filename} ({time_str[:2]}:{time_str[2:]})")
            
            # 6. 直接按Enter打开第一个文件（已经是最新的了）
            await page.keyboard.press('Enter')
            await asyncio.sleep(6)
            
            # 7. 读取内容
            for frame in page.frames:
                try:
                    text = await frame.evaluate('() => document.body.innerText')
                    if text and len(text) > 100:
                        # 检查是否包含数据
                        if '透明标签' in text or '[超级列表框_首页开始]' in text:
                            print(f"✅ 获取到内容 (长度: {len(text)})")
                            
                            # 提取数据部分
                            lines = text.split('\n')
                            data_lines = []
                            in_data = False
                            
                            for line in lines:
                                if '透明标签' in line:
                                    in_data = True
                                if in_data:
                                    data_lines.append(line)
                                if '[超级列表框_首页结束]' in line:
                                    break
                            
                            clean_content = '\n'.join(data_lines)
                            
                            return {
                                'filename': latest_filename,
                                'content': clean_content,
                                'time': time_str
                            }
                except:
                    pass
            
            print("⚠️ 未能读取内容")
            return None
            
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            return None
        finally:
            await browser.close()

async def main():
    result = await read_latest_file()
    
    if result and result['content']:
        print(f"\n✅ 成功！")
        print(f"文件: {result['filename']}")
        print(f"内容长度: {len(result['content'])}")
        
        # 保存
        with open('/home/user/webapp/latest_home_data.txt', 'w', encoding='utf-8') as f:
            f.write(result['content'])
        print(f"✅ 已保存: latest_home_data.txt")
        
        # 显示前500个字符
        print(f"\n内容预览:")
        print(result['content'][:500])
        
        return True
    else:
        print("\n❌ 失败")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
