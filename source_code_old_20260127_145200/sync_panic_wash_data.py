#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恐慌清洗指标数据同步器
定期从Google Drive读取并保存到数据库
"""

import asyncio
import sqlite3
from datetime import datetime
import pytz
from panic_wash_reader import get_panic_wash_data

def save_to_database(data):
    """保存数据到数据库"""
    if not data:
        print("❌ 没有数据可保存")
        return False
    
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 解析恐慌指标和颜色
        panic_indicator_str = data['panic_indicator']  # 例如: "10.77-绿"
        parts = panic_indicator_str.split('-')
        panic_indicator = float(parts[0])
        panic_color = parts[1] if len(parts) > 1 else None
        
        # 解析其他数据
        trend_rating = int(data['trend_rating'])
        market_zone = data['market_zone']
        liquidation_24h_people = int(data['liquidation_24h_people'])
        liquidation_24h_amount = float(data['liquidation_24h_amount'])
        total_position = float(data['total_position'])
        record_time = data['update_time']
        
        # 插入数据（如果记录时间已存在则忽略）
        cursor.execute('''
            INSERT OR IGNORE INTO panic_wash_history 
            (record_time, panic_indicator, panic_color, trend_rating, market_zone,
             liquidation_24h_people, liquidation_24h_amount, total_position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (record_time, panic_indicator, panic_color, trend_rating, market_zone,
              liquidation_24h_people, liquidation_24h_amount, total_position))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ 成功保存数据到数据库")
            print(f"   记录时间: {record_time}")
            print(f"   恐慌指标: {panic_indicator} ({panic_color})")
            print(f"   持仓量: {total_position} 亿")
            return True
        else:
            print(f"⚠️  数据已存在，跳过")
            return False
        
    except Exception as e:
        print(f"❌ 保存数据失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

async def sync_panic_wash_data():
    """同步恐慌清洗数据"""
    print(f"\n{'='*70}")
    print(f"开始同步恐慌清洗指标数据")
    print(f"时间: {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    # 1. 从Google Drive获取数据
    data = await get_panic_wash_data()
    
    if data:
        # 2. 保存到数据库
        save_to_database(data)
        
        # 3. 显示数据库统计
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM panic_wash_history")
        count = cursor.fetchone()[0]
        print(f"\n📊 数据库统计: 共 {count} 条记录")
        
        # 显示最近5条记录
        cursor.execute("""
            SELECT record_time, panic_indicator, panic_color, total_position
            FROM panic_wash_history
            ORDER BY record_time DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        print(f"\n📋 最近5条记录:")
        for row in rows:
            print(f"   {row[0]} | 指标:{row[1]:6.2f}-{row[2]:2s} | 持仓:{row[3]:6.2f}亿")
        
        conn.close()
        return True
    else:
        print("❌ 数据获取失败")
        return False

if __name__ == '__main__':
    success = asyncio.run(sync_panic_wash_data())
    if success:
        print(f"\n{'='*70}")
        print("✅ 同步完成")
        print(f"{'='*70}")
    else:
        print(f"\n{'='*70}")
        print("❌ 同步失败")
        print(f"{'='*70}")
