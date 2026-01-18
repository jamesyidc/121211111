#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Google Drive批量导入历史数据到数据库
"""

import asyncio
import sys
import os
from datetime import datetime
from playwright.async_api import async_playwright
from crypto_database import CryptoDatabase

# Google Drive文件夹配置
ROOT_FOLDER_ID = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'
ROOT_FOLDER_URL = f'https://drive.google.com/drive/folders/{ROOT_FOLDER_ID}'

def parse_home_data(content):
    """解析首页数据内容"""
    lines = content.strip().split('\n')
    
    stats = {}
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
                    stats['rushUp'] = value.split('：')[1] if '：' in value else value
                elif '急跌总和' in key:
                    stats['rushDown'] = value.split('：')[1] if '：' in value else value
                elif '五种状态' in key:
                    stats['status'] = value.split('：')[1] if '：' in value else value
                elif '急涨急跌比值' in key:
                    stats['ratio'] = value.split('：')[1] if '：' in value else value
                elif '绿色数量' in key:
                    stats['greenCount'] = value
                elif '百分比' in key:
                    stats['percentage'] = value
                elif '计次' in key:
                    stats['count'] = value
                elif '差值结果' in key:
                    stats['diff'] = value.split('：')[1] if '：' in value else value
        
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
                    'index': parts[0],
                    'symbol': parts[1],
                    'change': parts[2],
                    'rushUp': parts[3],
                    'rushDown': parts[4],
                    'updateTime': parts[5],
                    'highPrice': parts[6],
                    'highTime': parts[7],
                    'decline': parts[8],
                    'change24h': parts[9],
                    'rank': parts[12],
                    'currentPrice': parts[13],
                    'ratio1': parts[14],
                    'ratio2': parts[15]
                }
                coins.append(coin)
    
    # 获取更新时间
    update_time = coins[0]['updateTime'] if coins else ''
    
    return {
        'stats': stats,
        'coins': coins,
        'updateTime': update_time
    }

async def get_all_date_folders(page):
    """获取所有日期文件夹"""
    print(f"\n{'='*60}")
    print(f"1. 访问根文件夹...")
    print(f"{'='*60}")
    
    await page.goto(ROOT_FOLDER_URL, wait_until='networkidle', timeout=60000)
    await page.wait_for_timeout(3000)
    
    # 获取所有日期文件夹（格式: 2025-12-03）
    date_folders = []
    
    # 获取页面文本内容
    content = await page.content()
    
    # 查找所有匹配日期格式的文件夹名
    import re
    pattern = r'2025-\d{2}-\d{2}'
    matches = re.findall(pattern, content)
    
    # 去重
    date_folders = list(set(matches))
    date_folders.sort(reverse=True)  # 降序排列（最新的在前）
    
    print(f"\n找到 {len(date_folders)} 个日期文件夹:")
    for folder in date_folders[:10]:  # 只显示前10个
        print(f"   - {folder}")
    if len(date_folders) > 10:
        print(f"   ... 还有 {len(date_folders) - 10} 个文件夹")
    
    return date_folders

async def get_files_in_date_folder(page, date_str):
    """获取指定日期文件夹中的所有文件"""
    print(f"\n{'='*60}")
    print(f"处理日期: {date_str}")
    print(f"{'='*60}")
    
    # 回到根文件夹
    await page.goto(ROOT_FOLDER_URL, wait_until='networkidle', timeout=60000)
    await page.wait_for_timeout(2000)
    
    # 查找并点击日期文件夹
    try:
        folder_locator = page.locator(f'text="{date_str}"').first
        await folder_locator.dblclick(timeout=10000)
        await page.wait_for_timeout(3000)
        print(f"✅ 已进入 {date_str} 文件夹")
    except Exception as e:
        print(f"❌ 无法进入文件夹 {date_str}: {e}")
        return []
    
    # 点击排序按钮
    try:
        sort_button = page.locator('button[aria-label*="Sort"], button[aria-label*="排序"]').first
        await sort_button.click(timeout=5000)
        await page.wait_for_timeout(1000)
        
        # 点击"修改时间"选项
        modified_option = page.locator('text="Modified", text="修改时间"').first
        await modified_option.click(force=True, timeout=5000)
        await page.wait_for_timeout(2000)
        print("✅ 已按修改时间排序")
    except Exception as e:
        print(f"⚠️ 排序失败（将使用默认顺序）: {e}")
    
    # 获取页面内容并提取文件名
    content = await page.content()
    
    import re
    pattern = rf'{date_str}_\d{{4}}\.txt'
    matches = re.findall(pattern, content)
    
    # 去重并排序
    files = list(set(matches))
    files.sort()  # 按时间排序
    
    print(f"找到 {len(files)} 个TXT文件")
    
    return files

async def read_file_content(page, filename):
    """读取指定文件的内容"""
    try:
        # 查找并点击文件
        file_locator = page.locator(f'text="{filename}"').first
        await file_locator.click(timeout=10000)
        await page.wait_for_timeout(3000)
        
        # 尝试从iframe中读取内容
        frames = page.frames
        
        for i, frame in enumerate(frames):
            try:
                frame_url = frame.url
                if 'docs.google.com' in frame_url or 'drive.google.com' in frame_url:
                    text_content = await frame.content()
                    
                    # 检查是否包含关键数据
                    if '[超级列表框_首页开始]' in text_content or 'BTC' in text_content:
                        # 提取纯文本
                        import re
                        # 移除HTML标签
                        clean_text = re.sub(r'<[^>]+>', '\n', text_content)
                        clean_text = re.sub(r'\n+', '\n', clean_text)
                        
                        # 查找数据区域
                        if '[超级列表框_首页开始]' in clean_text:
                            start_idx = clean_text.find('[超级列表框_首页开始]')
                            end_idx = clean_text.find('[超级列表框_首页结束]', start_idx)
                            
                            if end_idx > start_idx:
                                data_section = clean_text[start_idx:end_idx + len('[超级列表框_首页结束]')]
                                
                                # 也包含统计数据（在数据区域之前）
                                stats_start = max(0, start_idx - 2000)
                                full_content = clean_text[stats_start:end_idx + len('[超级列表框_首页结束]')]
                                
                                return full_content
            except Exception as frame_error:
                continue
        
        return None
        
    except Exception as e:
        print(f"   ❌ 读取文件失败: {e}")
        return None
    finally:
        # 关闭预览（按ESC键）
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(1000)

async def import_all_history():
    """导入所有历史数据"""
    db = CryptoDatabase()
    
    print("="*60)
    print("开始导入Google Drive历史数据")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 1. 获取所有日期文件夹
            date_folders = await get_all_date_folders(page)
            
            if not date_folders:
                print("❌ 未找到任何日期文件夹")
                return
            
            total_imported = 0
            total_skipped = 0
            
            # 2. 逐个处理日期文件夹
            for date_str in date_folders:
                print(f"\n{'='*60}")
                print(f"正在处理: {date_str}")
                print(f"{'='*60}")
                
                # 获取该日期下的所有文件
                files = await get_files_in_date_folder(page, date_str)
                
                if not files:
                    print(f"⚠️ {date_str} 文件夹为空")
                    continue
                
                # 3. 逐个读取文件
                for idx, filename in enumerate(files, 1):
                    # 解析文件名获取时间
                    # 格式: 2025-12-03_1012.txt -> 2025-12-03 10:12:00
                    parts = filename.replace('.txt', '').split('_')
                    if len(parts) != 2:
                        continue
                    
                    date_part = parts[0]
                    time_part = parts[1]
                    
                    # 格式化时间
                    hour = time_part[:2]
                    minute = time_part[2:]
                    snapshot_time = f"{date_part} {hour}:{minute}:00"
                    
                    # 检查是否已存在
                    existing = db.get_snapshot_by_time(snapshot_time)
                    if existing:
                        print(f"   [{idx}/{len(files)}] ⏭️  {filename} (已存在，跳过)")
                        total_skipped += 1
                        continue
                    
                    print(f"   [{idx}/{len(files)}] 📥 正在导入: {filename}")
                    
                    # 读取文件内容
                    content = await read_file_content(page, filename)
                    
                    if not content:
                        print(f"      ❌ 无法读取内容")
                        continue
                    
                    # 解析数据
                    try:
                        parsed_data = parse_home_data(content)
                        
                        if not parsed_data['coins']:
                            print(f"      ❌ 解析失败（无币种数据）")
                            continue
                        
                        # 保存到数据库
                        snapshot_id = db.save_snapshot(
                            data=parsed_data['coins'],
                            stats=parsed_data['stats'],
                            snapshot_time=snapshot_time,
                            filename=filename
                        )
                        
                        print(f"      ✅ 已保存 (ID: {snapshot_id}, {len(parsed_data['coins'])}个币种)")
                        total_imported += 1
                        
                    except Exception as parse_error:
                        print(f"      ❌ 解析/保存失败: {parse_error}")
                        continue
                    
                    # 每5个文件休息一下
                    if idx % 5 == 0:
                        await page.wait_for_timeout(2000)
            
            print(f"\n{'='*60}")
            print(f"导入完成!")
            print(f"{'='*60}")
            print(f"✅ 成功导入: {total_imported} 个快照")
            print(f"⏭️  跳过已存在: {total_skipped} 个快照")
            print(f"📊 总计处理: {total_imported + total_skipped} 个快照")
            
            # 显示数据库统计
            stats = db.get_statistics()
            print(f"\n数据库统计:")
            print(f"   快照总数: {stats['total_snapshots']}")
            print(f"   最早时间: {stats['earliest_time']}")
            print(f"   最晚时间: {stats['latest_time']}")
            
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(import_all_history())
