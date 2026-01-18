#!/usr/bin/env python3
"""
补全2025-12-22的历史数据
从Google Drive获取所有文件并导入数据库
"""

import os
import sys
import json
import requests
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 配置
FOLDER_ID = "1HFIluWjpmtGyfvrC7hmlItZE7wPC8Hdn"  # 2025-12-22文件夹
DB_PATH = "crypto_data.db"

def get_files_from_gdrive(folder_id):
    """从Google Drive获取文件列表"""
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html = response.text
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        entries = soup.find_all('div', class_='flip-entry')
        
        files = []
        for entry in entries:
            entry_id = entry.get('id', '')
            if not entry_id.startswith('entry-'):
                continue
                
            file_id = entry_id.replace('entry-', '')
            
            # 获取文件名
            title_div = entry.find('div', class_='flip-entry-title')
            if title_div:
                filename = title_div.get_text(strip=True)
            else:
                link = entry.find('a', href=True)
                filename = link.get_text(strip=True) if link else file_id
            
            # 只处理TXT文件
            if filename.endswith('.txt'):
                files.append({
                    'id': file_id,
                    'name': filename
                })
        
        return files
        
    except Exception as e:
        print(f"❌ 获取文件列表失败: {e}")
        return []

def download_file(file_id, filename):
    """下载文件内容"""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # TXT文件，直接解析文本
        text = response.text
        
        # 解析JSON格式的文本
        data = json.loads(text)
        return data
        
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return None

def parse_snapshot_data(data, filename):
    """解析快照数据"""
    try:
        # 从文件名提取时间 (格式: YYYY-MM-DD_HHMM.txt)
        parts = filename.replace('.txt', '').split('_')
        if len(parts) >= 2:
            date_str = parts[0]  # YYYY-MM-DD
            time_str = parts[1]  # HHMM
            # 转换为 HH:MM 格式
            hour = time_str[:2]
            minute = time_str[2:]
            snapshot_time = f"{date_str} {hour}:{minute}:00"
        else:
            return None
        
        snapshot_date = date_str
        
        # 解析数据
        snapshot = {
            'snapshot_time': snapshot_time,
            'snapshot_date': snapshot_date,
            'rush_up': data.get('急涨数量', 0),
            'rush_down': data.get('急跌数量', 0),
            'diff': data.get('涨跌差', 0),
            'count': data.get('计次', 0),
            'ratio': data.get('涨跌比', 0.0),
            'status': data.get('状态', ''),
            'green_count': data.get('绿盘数量', 0),
            'percentage': data.get('绿盘占比', ''),
            'filename': filename,
            'round_rush_up': data.get('急涨数量（完整指标）', 0),
            'round_rush_down': data.get('急跌数量（完整指标）', 0),
            'price_lowest': data.get('新低价格数量', 0),
            'price_newhigh': data.get('新高价格数量', 0),
            'ratio_diff': data.get('涨跌比差', 0.0),
            'init_rush_up': data.get('初涨数量', 0),
            'init_rush_down': data.get('初跌数量', 0),
            'count_score_display': data.get('计次评分', ''),
            'count_score_type': data.get('计次类型', ''),
            'rise_24h_count': data.get('24h上涨数量', 0),
            'fall_24h_count': data.get('24h下跌数量', 0)
        }
        
        # 解析币种数据
        coins = []
        coin_data = data.get('币种数据', [])
        for coin in coin_data:
            coins.append({
                'symbol': coin.get('symbol', ''),
                'price': coin.get('price', 0.0),
                'change_24h': coin.get('24h涨跌幅', 0.0),
                'volume_24h': coin.get('24h成交量', 0.0),
                'rush_type': coin.get('急涨急跌', ''),
                'snapshot_time': snapshot_time
            })
        
        return snapshot, coins
        
    except Exception as e:
        print(f"  ❌ 解析失败: {e}")
        return None

def insert_snapshot(conn, snapshot, coins):
    """插入快照数据到数据库"""
    cursor = conn.cursor()
    
    try:
        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM crypto_snapshots WHERE snapshot_time = ?",
            (snapshot['snapshot_time'],)
        )
        
        if cursor.fetchone():
            return False, "已存在"
        
        # 插入快照
        cursor.execute("""
            INSERT INTO crypto_snapshots (
                snapshot_time, snapshot_date, rush_up, rush_down, diff, count, ratio,
                status, green_count, percentage, filename, created_at,
                round_rush_up, round_rush_down, price_lowest, price_newhigh, ratio_diff,
                init_rush_up, init_rush_down, count_score_display, count_score_type,
                rise_24h_count, fall_24h_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot['snapshot_time'], snapshot['snapshot_date'],
            snapshot['rush_up'], snapshot['rush_down'], snapshot['diff'],
            snapshot['count'], snapshot['ratio'], snapshot['status'],
            snapshot['green_count'], snapshot['percentage'], snapshot['filename'],
            datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            snapshot['round_rush_up'], snapshot['round_rush_down'],
            snapshot['price_lowest'], snapshot['price_newhigh'], snapshot['ratio_diff'],
            snapshot['init_rush_up'], snapshot['init_rush_down'],
            snapshot['count_score_display'], snapshot['count_score_type'],
            snapshot['rise_24h_count'], snapshot['fall_24h_count']
        ))
        
        snapshot_id = cursor.lastrowid
        
        # 插入币种数据
        if coins:
            cursor.executemany("""
                INSERT INTO crypto_snapshot_coins (
                    snapshot_id, symbol, price, change_24h, volume_24h, rush_type, snapshot_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                (snapshot_id, c['symbol'], c['price'], c['change_24h'], 
                 c['volume_24h'], c['rush_type'], c['snapshot_time'])
                for c in coins
            ])
        
        conn.commit()
        return True, "成功"
        
    except Exception as e:
        conn.rollback()
        return False, str(e)

def main():
    print("="*70)
    print("🔄 开始补全 2025-12-22 历史数据")
    print("="*70)
    print(f"📁 Google Drive 文件夹ID: {FOLDER_ID}")
    print(f"💾 数据库路径: {DB_PATH}")
    print()
    
    # 1. 获取文件列表
    print("📥 正在获取文件列表...")
    files = get_files_from_gdrive(FOLDER_ID)
    
    if not files:
        print("❌ 未找到任何文件")
        return
    
    print(f"✅ 找到 {len(files)} 个TXT文件")
    print()
    
    # 按文件名排序（时间顺序）
    files.sort(key=lambda x: x['name'])
    
    # 2. 连接数据库
    conn = sqlite3.connect(DB_PATH)
    
    # 3. 逐个处理文件
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, file in enumerate(files, 1):
        print(f"[{i}/{len(files)}] 📄 {file['name']}")
        
        # 下载文件
        data = download_file(file['id'], file['name'])
        if not data:
            error_count += 1
            continue
        
        # 解析数据
        result = parse_snapshot_data(data, file['name'])
        if not result:
            error_count += 1
            continue
        
        snapshot, coins = result
        
        # 插入数据库
        success, message = insert_snapshot(conn, snapshot, coins)
        
        if success:
            success_count += 1
            print(f"  ✅ {snapshot['snapshot_time']} | 急涨:{snapshot['rush_up']} 急跌:{snapshot['rush_down']} | {message}")
        elif "已存在" in message:
            skip_count += 1
            print(f"  ⏭️  {snapshot['snapshot_time']} | {message}")
        else:
            error_count += 1
            print(f"  ❌ {message}")
    
    conn.close()
    
    # 4. 总结
    print()
    print("="*70)
    print("📊 补全完成统计")
    print("="*70)
    print(f"✅ 成功导入: {success_count} 条")
    print(f"⏭️  已存在跳过: {skip_count} 条")
    print(f"❌ 失败: {error_count} 条")
    print(f"📈 总计处理: {len(files)} 个文件")
    print("="*70)

if __name__ == "__main__":
    main()

