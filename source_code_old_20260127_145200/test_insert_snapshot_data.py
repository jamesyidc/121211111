#!/usr/bin/env python3
"""
测试脚本: 插入一些历史快照数据用于演示
仅用于测试时间轴功能,不影响生产数据
"""

import sqlite3
import json
from datetime import datetime, timedelta
import random

def generate_test_snapshots():
    """生成24小时的测试快照数据 (每3分钟一次)"""
    
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 获取当前时间
    base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    inserted_count = 0
    
    # 生成今天00:00到现在的数据 (每3分钟)
    for i in range(480):  # 24小时 * 60分钟 / 3分钟 = 480个点
        snapshot_time = base_time + timedelta(minutes=i * 3)
        
        # 如果超过当前时间,停止
        if snapshot_time > datetime.now():
            break
        
        # 模拟波动的数据 (使用正弦波 + 随机噪声)
        hour = snapshot_time.hour
        
        # 情况1和2 (支撑线) 在凌晨多,白天少
        base_scenario_1 = int(5 * (1 + 0.5 * abs(12 - hour) / 12))
        base_scenario_2 = int(3 * (1 + 0.5 * abs(12 - hour) / 12))
        
        # 情况3和4 (压力线) 在白天多,凌晨少
        base_scenario_3 = int(4 * (1 - 0.5 * abs(12 - hour) / 12))
        base_scenario_4 = int(2 * (1 - 0.5 * abs(12 - hour) / 12))
        
        # 添加随机波动
        scenario_1 = max(0, base_scenario_1 + random.randint(-2, 2))
        scenario_2 = max(0, base_scenario_2 + random.randint(-1, 1))
        scenario_3 = max(0, base_scenario_3 + random.randint(-2, 2))
        scenario_4 = max(0, base_scenario_4 + random.randint(-1, 1))
        
        # 生成示例币种列表
        def gen_coins(count):
            symbols = ['BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'ADA', 'DOGE', 'TRX', 'LINK', 'MATIC']
            selected = random.sample(symbols, min(count, len(symbols)))
            return json.dumps([{
                'symbol': f'{s}USDT',
                'current_price': random.uniform(0.5, 100000),
                'position': random.uniform(0, 5) if count in [scenario_1, scenario_2] else random.uniform(95, 100),
                'support_1': 0,
                'support_2': 0,
                'resistance_1': 0,
                'resistance_2': 0
            } for s in selected])
        
        # 插入数据
        cursor.execute('''
            INSERT INTO support_resistance_snapshots 
            (snapshot_date, snapshot_time, total_coins, 
             scenario_1_count, scenario_1_coins,
             scenario_2_count, scenario_2_coins,
             scenario_3_count, scenario_3_coins,
             scenario_4_count, scenario_4_coins)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot_time.strftime('%Y-%m-%d'),
            snapshot_time.strftime('%Y-%m-%d %H:%M:%S'),
            27,
            scenario_1, gen_coins(scenario_1),
            scenario_2, gen_coins(scenario_2),
            scenario_3, gen_coins(scenario_3),
            scenario_4, gen_coins(scenario_4)
        ))
        
        inserted_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ 成功插入 {inserted_count} 条测试快照数据")
    print(f"📅 时间范围: {base_time.strftime('%Y-%m-%d %H:%M')} - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"⏱️  采样间隔: 3分钟")

if __name__ == '__main__':
    print("🔧 生成测试快照数据...")
    print("警告: 这将向数据库插入测试数据,仅用于演示时间轴功能")
    
    generate_test_snapshots()
    
    # 验证数据
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM support_resistance_snapshots')
    total = cursor.fetchone()[0]
    print(f"\n📊 数据库当前总快照数: {total}")
    
    # 显示最新5条
    cursor.execute('''
        SELECT snapshot_time, scenario_1_count, scenario_2_count, scenario_3_count, scenario_4_count
        FROM support_resistance_snapshots
        ORDER BY snapshot_time DESC
        LIMIT 5
    ''')
    print("\n📈 最新5条快照:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: 情况1={row[1]}, 情况2={row[2]}, 情况3={row[3]}, 情况4={row[4]}")
    
    conn.close()
