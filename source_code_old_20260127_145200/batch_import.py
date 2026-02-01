#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量导入历史数据 - 导入指定数量的最新文件
"""

import asyncio
import sqlite3
import sys
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_history_simple import parse_filename_datetime, parse_home_data, save_to_database

DB_PATH = 'crypto_data.db'

async def read_file_content_by_index(files, index):
    """读取指定索引的文件内容"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 访问根文件夹
            url = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # 进入今天的文件夹
            folder_selector = f'[data-tooltip*="{today}"]'
            await page.locator(folder_selector).first.dblclick()
            await asyncio.sleep(4)
            
            # 点击排序
            sort_selectors = [
                'button:has-text("Sort")',
                '[aria-label*="Sort"]',
            ]
            
            for selector in sort_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.click()
                        await asyncio.sleep(2)
                        break
                except:
                    pass
            
            # 选择修改时间排序
            modified_selectors = ['text="Modified"']
            for selector in modified_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.click()
                        await asyncio.sleep(3)
                        break
                except:
                    pass
            
            # 点击指定文件
            filename = files[index]
            await page.click(f'text="{filename}"', timeout=15000)
            await asyncio.sleep(3)
            
            # 读取内容
            frames = page.frames
            for frame in frames:
                try:
                    content = await frame.content()
                    if '[超级列表框_首页开始]' in content or 'BTC' in content:
                        text = await frame.evaluate('''() => {
                            const pre = document.querySelector('pre');
                            if (pre) return pre.textContent;
                            const textbox = document.querySelector('[role="textbox"]');
                            if (textbox) return textbox.textContent;
                            return document.body.textContent;
                        }''')
                        
                        await browser.close()
                        return text
                except:
                    continue
            
            await browser.close()
            return None
            
        except Exception as e:
            await browser.close()
            print(f"   ❌ 读取失败: {str(e)}")
            return None

async def batch_import(count=10):
    """批量导入指定数量的文件"""
    print("="*80)
    print(f"📥 批量导入历史数据（最新 {count} 个文件）")
    print("="*80)
    
    # 1. 获取文件列表
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    today = now.strftime('%Y-%m-%d')
    
    print(f"\n1. 获取文件列表...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            url = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            folder_selector = f'[data-tooltip*="{today}"]'
            await page.locator(folder_selector).first.dblclick()
            await asyncio.sleep(4)
            
            # 排序
            await page.locator('button:has-text("Sort")').first.click()
            await asyncio.sleep(2)
            await page.locator('text="Modified"').first.click()
            await asyncio.sleep(3)
            
            # 获取文件列表
            content = await page.content()
            pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
            files = list(set(re.findall(pattern, content)))
            
            await browser.close()
            
            # 解析时间并排序
            file_times = []
            for f in files:
                match = re.match(r'2025-\d{2}-\d{2}_(\d{2})(\d{2})\.txt', f)
                if match:
                    time_val = int(match.group(1)) * 60 + int(match.group(2))
                    file_times.append((f, time_val))
            
            file_times.sort(key=lambda x: x[1], reverse=True)
            files = [f[0] for f in file_times[:count]]
            
            print(f"✅ 找到 {len(files)} 个文件")
            for i, f in enumerate(files, 1):
                print(f"   {i}. {f}")
            
        except Exception as e:
            print(f"❌ 获取文件列表失败: {str(e)}")
            await browser.close()
            return
    
    # 2. 逐个处理文件
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    print(f"\n2. 开始处理文件...")
    print("-" * 80)
    
    for i, filename in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 处理: {filename}")
        
        # 检查是否已存在
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM stats_history WHERE filename = ?', (filename,))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            print(f"   ⏭️  已存在，跳过")
            skip_count += 1
            continue
        
        # 解析时间
        record_time = parse_filename_datetime(filename)
        if not record_time:
            print(f"   ⚠️  无法解析时间")
            fail_count += 1
            continue
        
        # 读取内容
        print(f"   正在读取...")
        content = await read_file_content_by_index(files, i-1)
        
        if not content:
            print(f"   ❌ 读取失败")
            fail_count += 1
            continue
        
        print(f"   ✅ 读取成功 ({len(content)} 字符)")
        
        # 解析数据
        try:
            stats, coins = parse_home_data(content)
            print(f"   解析: 急涨={stats['rushUp']}, 急跌={stats['rushDown']}, 币种={len(coins)}")
        except Exception as e:
            print(f"   ❌ 解析失败: {str(e)}")
            fail_count += 1
            continue
        
        # 保存到数据库
        success, msg = save_to_database(filename, record_time, stats, coins)
        if success:
            print(f"   ✅ {msg}")
            success_count += 1
        else:
            print(f"   ⏭️  {msg}")
            skip_count += 1
        
        # 避免请求过快
        await asyncio.sleep(2)
    
    # 3. 显示汇总
    print("\n" + "="*80)
    print("📊 导入完成统计")
    print("="*80)
    print(f"✅ 成功: {success_count}")
    print(f"⏭️  跳过: {skip_count}")
    print(f"❌ 失败: {fail_count}")
    print(f"📁 总计: {len(files)}")
    
    # 显示数据库统计
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM stats_history')
    total_stats = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM coin_history')
    total_coins = cursor.fetchone()[0]
    cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM stats_history')
    time_range = cursor.fetchone()
    conn.close()
    
    print(f"\n📈 数据库总计:")
    print(f"   统计记录: {total_stats}")
    print(f"   币种记录: {total_coins}")
    if time_range[0]:
        print(f"   时间范围: {time_range[0]} ~ {time_range[1]}")
    
    print("="*80)

if __name__ == '__main__':
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(batch_import(count))
