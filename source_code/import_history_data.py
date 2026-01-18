#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据导入脚本 - 从Google Drive批量导入所有历史TXT文件
"""

import asyncio
import sqlite3
import sys
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_PATH = 'crypto_data.db'
ROOT_FOLDER_ID = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'

def parse_filename_datetime(filename):
    """从文件名解析日期时间"""
    # 例如: 2025-12-03_1012.txt -> 2025-12-03 10:12:00
    match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.txt', filename)
    if match:
        date_part = match.group(1)
        hour = match.group(2)
        minute = match.group(3)
        return f"{date_part} {hour}:{minute}:00"
    return None

def parse_home_data(content):
    """解析首页数据内容"""
    lines = content.strip().split('\n')
    
    stats = {
        'rushUp': 0,
        'rushDown': 0,
        'status': '',
        'ratio': '',
        'greenCount': 0,
        'percentage': ''
    }
    coins = []
    
    in_coin_section = False
    
    for line in lines:
        line = line.strip()
        
        # 解析统计数据
        if line.startswith('透明标签_'):
            parts = line.split('=')
            if len(parts) == 2:
                key = parts[0].replace('透明标签_', '')
                value = parts[1]
                
                if '急涨总和' in key:
                    stats['rushUp'] = int(value.split('：')[1]) if '：' in value else 0
                elif '急跌总和' in key:
                    stats['rushDown'] = int(value.split('：')[1]) if '：' in value else 0
                elif '五种状态' in key:
                    stats['status'] = value.split('：')[1] if '：' in value else value
                elif '急涨急跌比值' in key:
                    stats['ratio'] = value.split('：')[1] if '：' in value else value
                elif '绿色数量' in key:
                    match = re.search(r'\d+', value)
                    stats['greenCount'] = int(match.group()) if match else 0
                elif '百分比' in key:
                    stats['percentage'] = value
        
        # 币种数据
        if '[超级列表框_首页开始]' in line:
            in_coin_section = True
            continue
        
        if '[超级列表框_首页结束]' in line:
            break
        
        if in_coin_section and '|' in line:
            parts = line.split('|')
            if len(parts) >= 16:
                coin = {
                    'index': int(parts[0]) if parts[0].isdigit() else 0,
                    'symbol': parts[1],
                    'change': float(parts[2]) if parts[2] else 0,
                    'rushUp': int(parts[3]) if parts[3].isdigit() else 0,
                    'rushDown': int(parts[4]) if parts[4].isdigit() else 0,
                    'updateTime': parts[5],
                    'highPrice': float(parts[6]) if parts[6] else 0,
                    'highTime': parts[7],
                    'decline': float(parts[8]) if parts[8] else 0,
                    'change24h': float(parts[9]) if parts[9] else 0,
                    'rank': int(parts[12]) if parts[12].isdigit() else 0,
                    'currentPrice': float(parts[13]) if parts[13] else 0,
                    'ratio1': parts[14],
                    'ratio2': parts[15]
                }
                coins.append(coin)
    
    return stats, coins

def save_to_database(filename, record_time, stats, coins):
    """保存数据到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查是否已存在
        cursor.execute('SELECT id FROM stats_history WHERE filename = ?', (filename,))
        existing = cursor.fetchone()
        
        if existing:
            return False, "已存在"
        
        # 插入统计数据
        cursor.execute('''
            INSERT INTO stats_history 
            (filename, record_time, rush_up, rush_down, status, ratio, green_count, percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename,
            record_time,
            stats['rushUp'],
            stats['rushDown'],
            stats['status'],
            stats['ratio'],
            stats['greenCount'],
            stats['percentage']
        ))
        
        stats_id = cursor.lastrowid
        
        # 批量插入币种数据
        coin_records = [
            (
                stats_id,
                filename,
                record_time,
                coin['index'],
                coin['symbol'],
                coin['change'],
                coin['rushUp'],
                coin['rushDown'],
                coin['updateTime'],
                coin['highPrice'],
                coin['highTime'],
                coin['decline'],
                coin['change24h'],
                coin['rank'],
                coin['currentPrice'],
                coin['ratio1'],
                coin['ratio2']
            )
            for coin in coins
        ]
        
        cursor.executemany('''
            INSERT INTO coin_history 
            (stats_id, filename, record_time, index_num, symbol, change, rush_up, rush_down,
             update_time, high_price, high_time, decline, change_24h, rank, current_price,
             ratio1, ratio2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', coin_records)
        
        conn.commit()
        return True, f"成功导入 {len(coins)} 条币种数据"
        
    except Exception as e:
        conn.rollback()
        return False, f"数据库错误: {str(e)}"
    finally:
        conn.close()

async def get_all_txt_files_from_folder(folder_url):
    """获取文件夹中所有TXT文件列表"""
    print(f"\n🔍 正在扫描文件夹...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(folder_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # 点击排序
            await page.click('text="Sort"', timeout=10000)
            await page.wait_for_timeout(1000)
            
            # 选择修改时间排序
            await page.click('text="Modified"', timeout=10000)
            await page.wait_for_timeout(2000)
            
            # 获取页面内容
            content = await page.content()
            
            # 提取所有文件名
            pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
            files = list(set(re.findall(pattern, content)))
            files.sort(reverse=True)  # 从最新到最旧
            
            await browser.close()
            
            print(f"✅ 找到 {len(files)} 个TXT文件")
            return files
            
        except Exception as e:
            print(f"❌ 扫描失败: {str(e)}")
            await browser.close()
            return []

async def read_file_content(folder_url, filename):
    """读取单个文件内容"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(folder_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # 点击排序（确保文件列表已加载）
            await page.click('text="Sort"', timeout=10000)
            await page.wait_for_timeout(1000)
            await page.click('text="Modified"', timeout=10000)
            await page.wait_for_timeout(2000)
            
            # 点击文件
            await page.click(f'text="{filename}"', timeout=10000)
            await page.wait_for_timeout(3000)
            
            # 读取内容
            frames = page.frames
            for frame in frames:
                try:
                    content = await frame.content()
                    if '[超级列表框_首页开始]' in content or 'BTC' in content:
                        # 提取纯文本
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
            return None

async def import_all_history():
    """导入所有历史数据"""
    print("="*80)
    print("📥 开始导入历史数据")
    print("="*80)
    
    # 1. 扫描今天的文件夹
    today = datetime.now().strftime('%Y-%m-%d')
    today_folder_url = f"https://drive.google.com/drive/folders/1Ej3JlFylpaxRtcLIe1yD_MOxcxNck5mh"
    
    print(f"\n📅 扫描日期: {today}")
    files = await get_all_txt_files_from_folder(today_folder_url)
    
    if not files:
        print("❌ 没有找到任何文件")
        return
    
    # 2. 逐个处理文件
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    print(f"\n开始处理 {len(files)} 个文件...")
    print("-" * 80)
    
    for i, filename in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 处理文件: {filename}")
        
        # 解析时间
        record_time = parse_filename_datetime(filename)
        if not record_time:
            print(f"   ⚠️  无法解析时间，跳过")
            skip_count += 1
            continue
        
        print(f"   记录时间: {record_time}")
        
        # 读取内容
        print(f"   正在读取内容...")
        content = await read_file_content(today_folder_url, filename)
        
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
    asyncio.run(import_all_history())
