#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加演示历史数据 - 用于测试图表显示
"""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'crypto_data.db'

def add_demo_data():
    """添加演示历史数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取当前最早的记录时间
    cursor.execute('SELECT MIN(record_time) FROM stats_history')
    min_time = cursor.fetchone()[0]
    
    if min_time:
        start_time = datetime.strptime(min_time, '%Y-%m-%d %H:%M:%S')
        print(f"当前最早记录: {min_time}")
    else:
        start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    
    # 向前添加记录，每10分钟一条
    print(f"\n开始添加演示数据...")
    added = 0
    
    # 从08:00开始，添加到最早记录之前
    current = start_time.replace(hour=8, minute=0, second=0, microsecond=0)
    
    while current < start_time:
        filename = current.strftime('%Y-%m-%d_%H%M.txt')
        record_time = current.strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查是否已存在
        cursor.execute('SELECT id FROM stats_history WHERE filename = ?', (filename,))
        if cursor.fetchone():
            print(f"  跳过: {record_time} (已存在)")
            current += timedelta(minutes=10)
            continue
        
        # 生成随机但合理的数据
        rush_up = random.randint(4, 10)
        rush_down = random.randint(3, 8)
        status_list = ['震荡无序', '多头洗盘', '空头洗盘', '强势上涨', '弱势下跌']
        status = random.choice(status_list)
        green_count = random.randint(25, 29)
        
        try:
            # 插入统计数据
            cursor.execute('''
                INSERT INTO stats_history 
                (filename, record_time, rush_up, rush_down, status, ratio, green_count, percentage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename,
                record_time,
                rush_up,
                rush_down,
                status,
                '数据不足',
                green_count,
                f'计次=2'
            ))
            
            stats_id = cursor.lastrowid
            
            # 添加简化的币种数据（只添加BTC作为示例）
            cursor.execute('''
                INSERT INTO coin_history 
                (stats_id, filename, record_time, index_num, symbol, change, rush_up, rush_down,
                 update_time, high_price, high_time, decline, change_24h, rank, current_price,
                 ratio1, ratio2)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stats_id, filename, record_time, 1, 'BTC', 0.1, 0, 0,
                record_time, 126259.48, '2025-10-07', -26.5, 7.0, 18,
                92000.0, '73%', '113%'
            ))
            
            conn.commit()
            print(f"  ✅ 添加: {record_time} - 急涨:{rush_up}, 急跌:{rush_down}")
            added += 1
            
        except Exception as e:
            print(f"  ❌ 失败: {record_time} - {str(e)}")
            conn.rollback()
        
        current += timedelta(minutes=10)
    
    conn.close()
    
    print(f"\n✅ 共添加 {added} 条演示数据")
    
    # 显示最终统计
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM stats_history')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM stats_history')
    time_range = cursor.fetchone()
    conn.close()
    
    print(f"\n📊 数据库总计:")
    print(f"   统计记录: {total}")
    print(f"   时间范围: {time_range[0]} ~ {time_range[1]}")

if __name__ == '__main__':
    add_demo_data()
