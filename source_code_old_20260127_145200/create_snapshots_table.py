#!/usr/bin/env python3
"""
创建support_resistance_snapshots表并生成初始快照
用于支撑压力线系统的历史数据记录
"""
import sqlite3
import json
from datetime import datetime
import pytz

def create_table_and_initial_snapshot():
    db = sqlite3.connect('crypto_data.db')
    cursor = db.cursor()

    # 创建表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_resistance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_time TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            scenario_1_count INTEGER DEFAULT 0,
            scenario_2_count INTEGER DEFAULT 0,
            scenario_3_count INTEGER DEFAULT 0,
            scenario_4_count INTEGER DEFAULT 0,
            scenario_1_coins TEXT,
            scenario_2_coins TEXT,
            scenario_3_coins TEXT,
            scenario_4_coins TEXT,
            total_coins INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    print("✅ support_resistance_snapshots表已创建")

    # 从support_resistance_levels生成快照
    cursor.execute('''
        SELECT symbol, current_price, support_line_1, support_line_2, 
               resistance_line_1, resistance_line_2,
               distance_to_support_1, distance_to_support_2,
               distance_to_resistance_1, distance_to_resistance_2,
               alert_scenario_1, alert_scenario_2, alert_scenario_3, alert_scenario_4,
               record_time
        FROM support_resistance_levels
        ORDER BY record_time DESC
        LIMIT 100
    ''')

    levels = cursor.fetchall()

    if not levels:
        print("⚠️  没有支撑压力数据")
        db.close()
        return

    # 按币种分组，取最新记录
    latest_by_symbol = {}
    for row in levels:
        symbol = row[0]
        if symbol not in latest_by_symbol:
            latest_by_symbol[symbol] = row

    # 统计4种情况
    scenario_1_coins = []
    scenario_2_coins = []
    scenario_3_coins = []
    scenario_4_coins = []

    for symbol, data in latest_by_symbol.items():
        (sym, price, s1, s2, r1, r2, ds1, ds2, dr1, dr2, 
         alert1, alert2, alert3, alert4, rec_time) = data
        
        if alert1:
            scenario_1_coins.append(sym)
        if alert2:
            scenario_2_coins.append(sym)
        if alert3:
            scenario_3_coins.append(sym)
        if alert4:
            scenario_4_coins.append(sym)

    # 生成快照
    latest_time = levels[0][14]
    beijing_tz = pytz.timezone('Asia/Shanghai')
    snapshot_dt = datetime.strptime(latest_time, '%Y-%m-%d %H:%M:%S')
    snapshot_dt = beijing_tz.localize(snapshot_dt)

    cursor.execute('''
        INSERT INTO support_resistance_snapshots
        (snapshot_time, snapshot_date, scenario_1_count, scenario_2_count, 
         scenario_3_count, scenario_4_count, scenario_1_coins, scenario_2_coins,
         scenario_3_coins, scenario_4_coins, total_coins)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        snapshot_dt.strftime('%Y-%m-%d %H:%M:%S'),
        snapshot_dt.strftime('%Y-%m-%d'),
        len(scenario_1_coins),
        len(scenario_2_coins),
        len(scenario_3_coins),
        len(scenario_4_coins),
        json.dumps(scenario_1_coins),
        json.dumps(scenario_2_coins),
        json.dumps(scenario_3_coins),
        json.dumps(scenario_4_coins),
        len(latest_by_symbol)
    ))

    db.commit()
    db.close()

    print(f"✅ 快照已生成")
    print(f"⏰ 快照时间: {snapshot_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 情况1: {len(scenario_1_coins)}, 情况2: {len(scenario_2_coins)}")
    print(f"   情况3: {len(scenario_3_coins)}, 情况4: {len(scenario_4_coins)}")
    print(f"   总币种: {len(latest_by_symbol)}")

if __name__ == '__main__':
    create_table_and_initial_snapshot()
