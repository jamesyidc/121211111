#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的Google Drive读取器
1. 点击排序获取最新文件名
2. 打开文件读取内容
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def get_latest_file_content():
    """获取最新文件的完整内容"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"{'='*60}")
    print(f"获取Google Drive最新文件内容")
    print(f"{'='*60}")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 步骤1: 访问并进入文件夹
            url = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            print(f"1. 访问根文件夹...")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            print(f"2. 进入 {today} 文件夹...")
            await page.locator(f'[data-tooltip*="{today}"]').first.dblclick()
            await asyncio.sleep(4)
            
            # 步骤2: 点击排序
            print(f"3. 按修改时间排序...")
            await page.locator('button:has-text("Sort")').first.click()
            await asyncio.sleep(2)
            await page.locator('text="Modified"').first.click()
            await asyncio.sleep(3)
            
            # 步骤3: 获取最新文件名
            print(f"4. 获取最新文件名...")
            content = await page.content()
            pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
            matches = re.findall(pattern, content)
            unique_files = sorted(set(matches), reverse=True)
            
            if not unique_files:
                print("❌ 未找到文件")
                return None
            
            latest_filename = unique_files[0]
            print(f"✅ 最新文件: {latest_filename}")
            
            # 计算时间差
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', latest_filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                file_time = datetime.strptime(f"{date_str} {time_str[:2]}:{time_str[2:]}", "%Y-%m-%d %H:%M")
                time_diff = (now.replace(tzinfo=None) - file_time).total_seconds() / 60
                print(f"   时间差: {time_diff:.1f} 分钟")
            
            # 步骤4: 打开文件
            print(f"\n5. 打开文件...")
            
            # 等待文件元素出现并点击
            try:
                # 方法1: 通过文本定位
                await page.get_by_text(latest_filename, exact=True).first.dblclick(timeout=10000)
                print(f"✅ 已打开文件")
            except:
                print("   方法1失败，尝试方法2...")
                # 方法2: 通过部分文本
                try:
                    await page.locator(f'text={latest_filename}').first.dblclick(timeout=10000)
                    print(f"✅ 已打开文件")
                except:
                    print("   方法2失败，尝试方法3...")
                    # 方法3: 直接找第一个文件（已经是最新的）
                    await page.keyboard.press('Enter')
                    print(f"✅ 已打开第一个文件")
            
            await asyncio.sleep(5)
            
            # 步骤5: 从iframe读取内容
            print(f"6. 读取文件内容...")
            
            frames = page.frames
            print(f"   找到 {len(frames)} 个frame")
            
            for i, frame in enumerate(frames):
                try:
                    text_content = await frame.evaluate('() => document.body.innerText')
                    
                    if text_content and len(text_content) > 50:
                        # 检查是否包含我们期待的内容
                        if '[超级列表框_首页开始]' in text_content or ('透明标签' in text_content and '|' in text_content):
                            print(f"✅ 从Frame {i} 读取到内容 (长度: {len(text_content)})")
                            
                            # 清理内容：提取核心数据部分
                            lines = text_content.split('\n')
                            clean_lines = []
                            in_data_section = False
                            
                            for line in lines:
                                # 找到数据开始标记
                                if '透明标签' in line or '[超级列表框_首页开始]' in line:
                                    in_data_section = True
                                
                                if in_data_section:
                                    clean_lines.append(line)
                                
                                # 找到数据结束标记
                                if '[超级列表框_首页结束]' in line:
                                    break
                            
                            clean_content = '\n'.join(clean_lines)
                            
                            print(f"✅ 清理后内容长度: {len(clean_content)}")
                            print(f"\n前500个字符:")
                            print(clean_content[:500])
                            
                            return {
                                'filename': latest_filename,
                                'content': clean_content,
                                'raw_content': text_content,
                                'time_diff': time_diff
                            }
                except Exception as e:
                    pass
            
            print("❌ 未能读取文件内容")
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
    
    if result:
        print(f"\n{'='*60}")
        print(f"✅ 成功!")
        print(f"{'='*60}")
        print(f"文件名: {result['filename']}")
        print(f"内容长度: {len(result['content'])} 字符")
        print(f"时间差: {result['time_diff']:.1f} 分钟")
        
        # 保存到文件
        with open('/home/user/webapp/latest_data.txt', 'w', encoding='utf-8') as f:
            f.write(result['content'])
        print(f"\n✅ 已保存到: latest_data.txt")
        
        return result
    else:
        print(f"\n{'='*60}")
        print(f"❌ 失败")
        print(f"{'='*60}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
