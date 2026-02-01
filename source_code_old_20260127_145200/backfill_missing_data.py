#!/usr/bin/env python3
"""
补全缺失的历史数据
从Google Drive读取所有TXT文件并导入数据库
"""
import sqlite3
from datetime import datetime, timedelta
import asyncio
from playwright.async_api import async_playwright
import re
import time

async def get_all_files_from_gdrive():
    """从Google Drive获取所有TXT文件列表"""
    print("🔍 正在从 Google Drive 获取文件列表...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 访问今天的文件夹
            root_url = 'https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'
            await page.goto(root_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # 进入今天日期的文件夹
            today = datetime.now().strftime('%Y-%m-%d')
            folder_selector = f'div[data-id]:has-text("{today}")'
            await page.click(folder_selector, timeout=10000)
            await page.wait_for_timeout(2000)
            
            # 获取所有文件
            await page.wait_for_selector('div[data-id]', timeout=10000)
            elements = await page.locator('div[data-id]').all()
            
            files = []
            for elem in elements:
                try:
                    text = await elem.text_content()
                    # 匹配 TXT 文件
                    if text and re.match(r'\d{4}-\d{2}-\d{2}_\d{4}\.txt', text):
                        files.append(text.strip())
                except:
                    continue
            
            await browser.close()
            
            # 按文件名排序
            files.sort()
            print(f"✅ 找到 {len(files)} 个文件")
            return files
            
        except Exception as e:
            print(f"❌ 获取文件列表失败: {e}")
            await browser.close()
            return []

def parse_filename_to_time(filename):
    """从文件名解析时间"""
    # 文件名格式: 2025-12-03_1022.txt
    match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.txt', filename)
    if match:
        date = match.group(1)
        hour = match.group(2)
        minute = match.group(3)
        return f"{date} {hour}:{minute}:00"
    return None

def check_missing_files():
    """检查数据库中缺失的文件"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 获取已有的记录
    cursor.execute('SELECT record_time, filename FROM stats_history ORDER BY record_time')
    existing = cursor.fetchall()
    
    existing_times = set([r[0] for r in existing])
    existing_files = set([r[1] for r in existing])
    
    conn.close()
    
    return existing_times, existing_files

async def main():
    """主函数"""
    print("=" * 80)
    print("补全缺失的历史数据")
    print("=" * 80)
    
    # 1. 获取Google Drive上的所有文件
    all_files = await get_all_files_from_gdrive()
    
    if not all_files:
        print("❌ 未获取到文件列表")
        return
    
    # 2. 检查数据库中已有的记录
    print("\n📊 检查数据库中已有的记录...")
    existing_times, existing_files = check_missing_files()
    print(f"  数据库中已有 {len(existing_times)} 条记录")
    
    # 3. 找出缺失的文件
    print("\n🔎 分析缺失的文件...")
    missing_files = []
    for filename in all_files:
        if filename not in existing_files:
            record_time = parse_filename_to_time(filename)
            if record_time:
                missing_files.append((filename, record_time))
    
    print(f"  发现 {len(missing_files)} 个缺失的文件需要导入")
    
    if not missing_files:
        print("\n✅ 没有缺失的数据，无需补全")
        return
    
    # 4. 显示缺失的文件列表
    print("\n缺失的文件:")
    for filename, record_time in missing_files[:10]:
        print(f"  - {filename} -> {record_time}")
    if len(missing_files) > 10:
        print(f"  ... 还有 {len(missing_files) - 10} 个文件")
    
    # 5. 询问是否导入
    print(f"\n是否开始导入这 {len(missing_files)} 个文件？")
    print("注意：每个文件需要约90秒，总计约 {:.1f} 分钟".format(len(missing_files) * 90 / 60))
    print("=" * 80)

if __name__ == '__main__':
    asyncio.run(main())
