#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极解决方案：通过URL参数直接指定排序方式
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def get_latest_with_url_sort():
    """使用URL参数排序"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"{'='*60}")
    print(f"获取最新文件内容（URL排序方案）")
    print(f"{'='*60}")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 步骤1: 先访问获取今天的文件夹ID
            print(f"1. 获取今天文件夹ID...")
            root_url = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            await page.goto(root_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            folder_id = await page.evaluate(f'''() => {{
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
            
            if not folder_id:
                print(f"❌ 未找到文件夹")
                return None
            
            print(f"✅ 文件夹ID: {folder_id}")
            
            # 步骤2: 使用带排序参数的URL访问
            # 使用键盘快捷键 'm' 来打开排序菜单
            sorted_url = f"https://drive.google.com/drive/folders/{folder_id}"
            print(f"\n2. 访问文件夹...")
            await page.goto(sorted_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # 使用键盘快捷键排序
            print(f"3. 使用键盘排序...")
            # 按 'r' 键可能会触发排序选项
            await page.keyboard.press('m')  # 打开菜单
            await asyncio.sleep(1)
            
            # 或者直接通过JavaScript修改排序
            await page.evaluate('''() => {
                // 尝试触发排序
                const sortButtons = document.querySelectorAll('button, [role="button"]');
                for (let btn of sortButtons) {
                    const text = btn.textContent || '';
                    if (text.includes('Sort') || text.includes('排序')) {
                        btn.click();
                        break;
                    }
                }
            }''')
            await asyncio.sleep(2)
            
            # 点击Modified
            await page.evaluate('''() => {
                const items = document.querySelectorAll('[role="menuitem"], [role="option"], div, span');
                for (let item of items) {
                    const text = item.textContent || '';
                    if (text.trim() === 'Modified' || text.trim() === '修改时间') {
                        item.click();
                        break;
                    }
                }
            }''')
            await asyncio.sleep(3)
            
            # 步骤3: 获取文件列表
            print(f"4. 获取文件列表...")
            content = await page.content()
            pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
            matches = re.findall(pattern, content)
            unique_files = sorted(set(matches), reverse=True)
            
            print(f"✅ 找到 {len(unique_files)} 个文件")
            print(f"\n前10个文件:")
            for i, f in enumerate(unique_files[:10], 1):
                m = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', f)
                if m:
                    print(f"   {i}. {f} ({m.group(2)[:2]}:{m.group(2)[2:]})")
            
            latest_filename = unique_files[0]
            
            # 计算时间差
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', latest_filename)
            date_str = match.group(1)
            time_str = match.group(2)
            file_time = datetime.strptime(f"{date_str} {time_str[:2]}:{time_str[2:]}", "%Y-%m-%d %H:%M")
            time_diff = (now.replace(tzinfo=None) - file_time).total_seconds() / 60
            
            print(f"\n最新文件: {latest_filename}")
            print(f"时间差: {time_diff:.1f} 分钟")
            
            # 步骤4: 选中第一个文件（最新的）并打开
            print(f"\n5. 打开最新文件...")
            
            # 方法：按Tab选中第一项，然后Enter打开
            await page.keyboard.press('Tab')
            await asyncio.sleep(0.5)
            await page.keyboard.press('Enter')
            await asyncio.sleep(6)  # 等待预览加载
            
            # 步骤5: 读取内容
            print(f"6. 读取内容...")
            
            for i, frame in enumerate(page.frames):
                try:
                    text = await frame.evaluate('() => document.body.innerText')
                    if text and len(text) > 100 and ('透明标签' in text or '[超级列表框_首页开始]' in text):
                        print(f"✅ 从Frame {i} 获取到内容 (长度: {len(text)})")
                        
                        # 提取数据部分
                        lines = text.split('\n')
                        data_lines = []
                        recording = False
                        
                        for line in lines:
                            if '透明标签' in line:
                                recording = True
                            if recording:
                                data_lines.append(line)
                            if '[超级列表框_首页结束]' in line:
                                break
                        
                        clean_data = '\n'.join(data_lines)
                        
                        return {
                            'filename': latest_filename,
                            'content': clean_data,
                            'time_diff': time_diff,
                            'folder_id': folder_id
                        }
                except:
                    pass
            
            print("⚠️ 未能读取内容，但已找到最新文件")
            return {
                'filename': latest_filename,
                'content': None,
                'time_diff': time_diff,
                'folder_id': folder_id
            }
            
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            await browser.close()

async def main():
    result = await get_latest_with_url_sort()
    
    if result:
        print(f"\n{'='*60}")
        print(f"结果")
        print(f"{'='*60}")
        print(f"文件名: {result['filename']}")
        print(f"时间差: {result['time_diff']:.1f} 分钟")
        
        if result['content']:
            print(f"内容长度: {len(result['content'])}")
            with open('/home/user/webapp/latest_data.txt', 'w', encoding='utf-8') as f:
                f.write(result['content'])
            print(f"✅ 已保存: latest_data.txt")
            
            print(f"\n内容预览:")
            print(result['content'][:500])

if __name__ == "__main__":
    asyncio.run(main())
