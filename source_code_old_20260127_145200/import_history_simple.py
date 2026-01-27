#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版历史数据导入 - 使用已有的成功脚本批量导入
"""

import asyncio
import sqlite3
import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdrive_home_data_reader import get_latest_file_by_sorting

DB_PATH = 'crypto_data.db'

def parse_filename_datetime(filename):
    """从文件名解析日期时间"""
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
        'percentage': '',
        'difference': '',
        'priceLowest': '',
        'priceNewHigh': '',
        'countTimes': 0,
        'rushDownCount': 0
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
                elif '差值结果' in key:
                    # 差值：9 ★
                    stats['difference'] = value.split('：')[1] if '：' in value else value
                elif '比价最低得分' in key:
                    # 比价最低 0 0
                    stats['priceLowest'] = value.replace('比价最低', '').strip()
                elif '仓位得分' in key:
                    # 比价创新高 0 0
                    stats['priceNewHigh'] = value.replace('比价创新高', '').strip()
                elif '计次' in key and key == '计次':
                    # 透明标签_计次=2
                    match = re.search(r'\d+', value)
                    stats['countTimes'] = int(match.group()) if match else 0
                elif '急跌数量' in key:
                    # 急跌数量 计次 5 6
                    parts = value.split()
                    if len(parts) >= 3:
                        try:
                            stats['rushDownCount'] = int(parts[2])  # 5 = 急跌币种数量
                        except:
                            pass
        
        # 币种数据
        if '[超级列表框_首页开始]' in line:
            in_coin_section = True
            continue
        
        if '[超级列表框_首页结束]' in line:
            break
        
        if in_coin_section and '|' in line:
            parts = line.split('|')
            if len(parts) >= 16:
                try:
                    coin = {
                        'index': int(parts[0]) if parts[0].isdigit() else 0,
                        'symbol': parts[1],
                        'change': float(parts[2]) if parts[2] and parts[2] != '' else 0,
                        'rushUp': int(parts[3]) if parts[3].isdigit() else 0,
                        'rushDown': int(parts[4]) if parts[4].isdigit() else 0,
                        'updateTime': parts[5],
                        'highPrice': float(parts[6]) if parts[6] and parts[6] != '' else 0,
                        'highTime': parts[7],
                        'decline': float(parts[8]) if parts[8] and parts[8] != '' else 0,
                        'change24h': float(parts[9]) if parts[9] and parts[9] != '' else 0,
                        'rank': int(parts[12]) if parts[12].isdigit() else 0,
                        'currentPrice': float(parts[13]) if parts[13] and parts[13] != '' else 0,
                        'ratio1': parts[14],
                        'ratio2': parts[15]
                    }
                    coins.append(coin)
                except:
                    continue
    
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
        
        # 计算本轮急涨急跌（与前一条记录对比）
        this_round_rush_up = 0
        this_round_rush_down = 0
        
        cursor.execute('''
            SELECT rush_up, rush_down 
            FROM stats_history 
            ORDER BY record_time DESC 
            LIMIT 1
        ''')
        prev_record = cursor.fetchone()
        if prev_record:
            this_round_rush_up = stats['rushUp'] - prev_record[0]
            this_round_rush_down = stats['rushDown'] - prev_record[1]
        
        # 插入统计数据
        cursor.execute('''
            INSERT INTO stats_history 
            (filename, record_time, rush_up, rush_down, status, ratio, green_count, percentage,
             difference, price_lowest, price_new_high, count_times, rush_down_count,
             this_round_rush_up, this_round_rush_down)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename,
            record_time,
            stats['rushUp'],
            stats['rushDown'],
            stats['status'],
            stats['ratio'],
            stats['greenCount'],
            stats['percentage'],
            stats['difference'],
            stats['priceLowest'],
            stats['priceNewHigh'],
            stats['countTimes'],
            stats['rushDownCount'],
            this_round_rush_up,
            this_round_rush_down
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

async def import_current_data():
    """导入当前最新数据（测试用）"""
    print("="*80)
    print("📥 导入最新数据到数据库")
    print("="*80)
    
    # 获取最新数据
    print("\n正在获取最新数据...")
    result = await get_latest_file_by_sorting()
    
    if not result or not result.get('content'):
        print("❌ 获取数据失败")
        return
    
    filename = result['filename']
    content = result['content']
    
    print(f"✅ 获取成功: {filename}")
    print(f"   内容长度: {len(content)} 字符")
    
    # 解析时间
    record_time = parse_filename_datetime(filename)
    if not record_time:
        print(f"❌ 无法解析时间")
        return
    
    print(f"   记录时间: {record_time}")
    
    # 解析数据
    try:
        stats, coins = parse_home_data(content)
        print(f"   解析结果: 急涨={stats['rushUp']}, 急跌={stats['rushDown']}, 币种={len(coins)}")
    except Exception as e:
        print(f"❌ 解析失败: {str(e)}")
        return
    
    # 保存到数据库
    success, msg = save_to_database(filename, record_time, stats, coins)
    if success:
        print(f"✅ {msg}")
    else:
        print(f"⏭️  {msg}")
    
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
    asyncio.run(import_current_data())
