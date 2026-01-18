#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入历史极值记录
"""
import sqlite3
from datetime import datetime

# 数据库路径
DB_PATH = 'databases/trading_decision.db'

# 历史极值数据
extreme_records = [
    # 格式: (编号, 币种, 方向, 类型, 收益率, 持仓量, 开仓价, 标记价, 时间, 持续时间)
    ("NO.13", "AAVE-USDT-SWAP", "long", "max_loss", -12.73, 0.5, 147.7538, 145.51, "2026-01-01 00:42:34", "4天12小时"),
    ("NO.13", "AAVE-USDT-SWAP", "long", "max_profit", 141.83, 0.5, 148.69, 165.9, "2026-01-03 09:38:55", "2天3小时"),
    ("NO.16", "APT-USDT-SWAP", "long", "max_loss", -24.49, 349.0, 1.714, 1.672, "2025-12-30 04:42:21", "6天8小时"),
    ("NO.16", "APT-USDT-SWAP", "long", "max_profit", 132.15, 4.0, 1.72, 1.868, "2026-01-02 06:08:16", "3天7小时"),
    ("NO.16", "APT-USDT-SWAP", "short", "max_loss", -41.29, 4.0, 1.7939, 1.868, "2026-01-02 06:08:16", "3天7小时"),
    ("NO.16", "APT-USDT-SWAP", "short", "max_profit", 34.80, 4.0, 1.7939, 1.808, "2026-01-02 22:35:34", "2天14小时"),
    ("NO.17", "BCH-USDT-SWAP", "long", "max_loss", -8.67, 0.2, 597.2765, 592.1, "2025-12-31 05:36:47", "5天7小时"),
    ("NO.17", "BCH-USDT-SWAP", "long", "max_profit", 10.62, 0.1, 595.8752, 602.2, "2025-12-31 19:44:32", "4天17小时"),
    ("NO.17", "BCH-USDT-SWAP", "short", "max_loss", -35.66, 0.2, 620.6, 660.3, "2026-01-04 04:47:51", "1天8小时"),
    ("NO.17", "BCH-USDT-SWAP", "short", "max_profit", 56.07, 0.1, 620.6, 585.8, "2026-01-02 11:09:57", "3天2小时"),
    ("NO.12", "BNB-USDT-SWAP", "short", "max_loss", -16.61, 1.0, 872.3, 890.8, "2026-01-03 01:19:31", "2天11小时"),
    ("NO.12", "BNB-USDT-SWAP", "short", "max_profit", 18.00, 1.0, 872.3, 869.0, "2026-01-02 17:12:40", "2天20小时"),
    ("NO.1", "CFX-USDT-SWAP", "long", "max_loss", -21.18, 13.0, 0.07, 0.0685, "2026-01-01 00:42:39", "4天12小时"),
    ("NO.1", "CFX-USDT-SWAP", "long", "max_profit", 173.49, 11.0, 0.0692, 0.0813, "2026-01-05 01:17:19", "11小时58分"),
    ("NO.1", "CFX-USDT-SWAP", "short", "max_loss", -44.53, 14.0, 0.0753, 0.0751, "2026-01-02 17:12:40", "2天20小时"),
    ("NO.1", "CFX-USDT-SWAP", "short", "max_profit", 19.87, 8.0, 0.0753, 0.079, "2026-01-05 12:42:45", "32分钟"),
    ("NO.3", "CRO-USDT-SWAP", "long", "max_loss", -10.06, 11.0, 0.0908, 0.0899, "2026-01-01 01:02:09", "4天12小时"),
    ("NO.3", "CRO-USDT-SWAP", "long", "max_profit", 192.76, 8.0, 0.0915, 0.1058, "2026-01-04 22:02:02", "15小时13分"),
    ("NO.3", "CRO-USDT-SWAP", "short", "max_loss", -28.44, 6.0, 0.0944, 0.1022, "2026-01-03 12:25:38", "2天0小时"),
    ("NO.3", "CRO-USDT-SWAP", "short", "max_profit", 41.91, 7.0, 0.0944, 0.0979, "2026-01-03 20:18:05", "1天16小时"),
    ("NO.5", "CRV-USDT-SWAP", "long", "max_loss", -12.05, 269.0, 0.3701, 0.3656, "2026-01-01 00:25:56", "4天12小时"),
    ("NO.5", "CRV-USDT-SWAP", "long", "max_profit", 173.59, 20.0, 0.378, 0.4221, "2026-01-04 22:02:02", "15小时13分"),
    ("NO.5", "CRV-USDT-SWAP", "short", "max_loss", -64.12, 27.0, 0.4024, 0.4328, "2026-01-04 03:13:59", "1天10小时"),
    ("NO.5", "CRV-USDT-SWAP", "short", "max_profit", 52.54, 0.0, 0.0, 0.0, "2026-01-02 01:00:14", "3天12小时"),
    ("--", "DOGE-USDT-SWAP", "short", "max_loss", -4.53, 157.5423, 0.1264, 0.127, "2025-12-29 17:02:11", "6天20小时"),
    ("NO.14", "DOT-USDT-SWAP", "long", "max_loss", -18.62, 4.0, 1.8004, 1.767, "2026-01-01 00:42:36", "4天12小时"),
    ("NO.14", "DOT-USDT-SWAP", "long", "max_profit", 246.12, 5.0, 1.7783, 2.216, "2026-01-03 08:52:35", "2天4小时"),
    ("NO.14", "DOT-USDT-SWAP", "short", "max_loss", -70.48, 3.0, 1.9127, 2.145, "2026-01-03 06:05:30", "2天7小时"),
    ("NO.14", "DOT-USDT-SWAP", "short", "max_profit", 45.04, 3.0, 1.9127, 2.109, "2026-01-03 17:15:47", "1天19小时"),
    ("NO.2", "FIL-USDT-SWAP", "long", "max_loss", -23.66, 829.0, 1.3018, 1.271, "2026-01-01 00:42:32", "4天12小时"),
    ("NO.2", "FIL-USDT-SWAP", "long", "max_profit", 241.57, 48.0, 1.325, 1.572, "2026-01-03 10:52:26", "2天2小时"),
    ("NO.2", "FIL-USDT-SWAP", "short", "max_loss", -18.45, 65.0, 1.3663, 1.546, "2026-01-02 01:12:35", "3天12小时"),
    ("NO.2", "FIL-USDT-SWAP", "short", "max_profit", 65.88, 65.0, 1.3663, 1.418, "2026-01-02 19:45:44", "2天17小时"),
    ("NO.10", "HBAR-USDT-SWAP", "short", "max_loss", -18.34, 0.8, 0.1167, 0.1221, "2026-01-03 06:05:30", "2天7小时"),
    ("NO.10", "HBAR-USDT-SWAP", "short", "max_profit", 19.49, 0.7, 0.1167, 0.1248, "2026-01-05 12:42:45", "32分钟"),
    ("NO.6", "LDO-USDT-SWAP", "long", "max_loss", -18.41, 18.0, 0.5766, 0.566, "2026-01-01 00:42:36", "4天12小时"),
    ("NO.6", "LDO-USDT-SWAP", "long", "max_profit", 107.27, 7.0, 0.5857, 0.6301, "2026-01-04 22:02:02", "15小时13分"),
    ("NO.6", "LDO-USDT-SWAP", "short", "max_loss", -25.72, 15.0, 0.6148, 0.6439, "2026-01-05 01:17:19", "11小时58分"),
    ("NO.6", "LDO-USDT-SWAP", "short", "max_profit", 31.40, 0.0, 0.0, 0.0, "2026-01-02 01:00:14", "3天12小时"),
    ("NO.18", "LINK-USDT-SWAP", "short", "max_loss", -19.23, 0.9, 12.9433, 13.337, "2026-01-03 01:02:41", "2天12小时"),
    ("NO.18", "LINK-USDT-SWAP", "short", "max_profit", 18.75, 0.9, 12.9433, 12.84, "2026-01-02 22:35:34", "2天14小时"),
    ("NO.15", "STX-USDT-SWAP", "long", "max_loss", -24.29, 18.5, 0.2475, 0.2415, "2026-01-01 01:40:58", "4天11小时"),
    ("NO.15", "STX-USDT-SWAP", "long", "max_profit", 534.96, 2.8, 0.2526, 0.3684, "2026-01-05 05:20:04", "7小时55分"),
    ("NO.15", "STX-USDT-SWAP", "short", "max_loss", -60.23, 1.7, 0.2673, 0.3526, "2026-01-05 02:27:19", "10小时48分"),
    ("NO.15", "STX-USDT-SWAP", "short", "max_profit", 55.36, 0.0, 0.0, 0.0, "2026-01-02 01:00:14", "3天12小时"),
    ("--", "SUI-USDT-SWAP", "short", "max_loss", -9.57, 2.0, 1.4142, 1.4277, "2025-12-28 00:01:44", "8天13小时"),
    ("--", "SUI-USDT-SWAP", "short", "max_profit", 2.94, 2.0, 1.4142, 1.41, "2025-12-27 21:22:28", "8天15小时"),
    ("NO.11", "TAO-USDT-SWAP", "short", "max_loss", -15.35, 5.0, 241.5909, 245.3, "2026-01-02 17:49:36", "2天19小时"),
    ("NO.11", "TAO-USDT-SWAP", "short", "max_profit", 26.57, 5.0, 241.5909, 238.9, "2026-01-02 23:24:15", "2天13小时"),
    ("NO.9", "TON-USDT-SWAP", "long", "max_loss", -9.27, 54.0, 1.6129, 1.598, "2025-12-31 13:31:53", "4天23小时"),
    ("NO.9", "TON-USDT-SWAP", "long", "max_profit", 24.31, 8.0, 1.6001, 1.639, "2025-12-31 18:17:40", "4天18小时"),
    ("NO.9", "TON-USDT-SWAP", "short", "max_loss", -85.45, 5.0, 1.6836, 1.88, "2026-01-03 01:30:02", "2天11小时"),
    ("NO.9", "TON-USDT-SWAP", "short", "max_profit", 28.93, 5.0, 1.6836, 1.779, "2026-01-03 15:57:00", "1天21小时"),
    ("--", "TRX-USDT-SWAP", "short", "max_loss", -5.58, 0.1, 0.2834, 0.285, "2025-12-28 07:47:18", "8天5小时"),
    ("--", "TRX-USDT-SWAP", "short", "max_profit", 6.63, 0.01, 0.2851, 0.2832, "2025-12-28 19:55:51", "7天17小时"),
    ("NO.4", "UNI-USDT-SWAP", "long", "max_loss", -14.39, 2.0, 5.7903, 5.707, "2026-01-01 00:42:38", "4天12小时"),
    ("NO.4", "UNI-USDT-SWAP", "long", "max_profit", 83.42, 1.0, 5.972, 6.116, "2026-01-03 09:47:59", "2天3小时"),
    ("NO.4", "UNI-USDT-SWAP", "short", "max_loss", -32.27, 1.0, 6.0372, 6.232, "2025-12-28 12:18:39", "8天0小时"),
    ("NO.4", "UNI-USDT-SWAP", "short", "max_profit", 112.15, 1.0, 6.3828, 5.667, "2026-01-02 10:23:38", "3天2小时"),
    ("NO.7", "XLM-USDT-SWAP", "long", "max_loss", -11.52, 0.4, 0.2075, 0.2051, "2025-12-31 23:12:32", "4天14小时"),
    ("NO.7", "XLM-USDT-SWAP", "long", "max_profit", 178.00, 0.5, 0.2053, 0.2346, "2026-01-04 22:02:02", "15小时13分"),
    ("NO.7", "XLM-USDT-SWAP", "short", "max_loss", -28.79, 0.4, 0.2269, 0.2272, "2026-01-03 12:56:53", "2天0小时"),
    ("NO.7", "XLM-USDT-SWAP", "short", "max_profit", 13.70, 0.4, 0.2269, 0.2272, "2026-01-03 12:53:51", "2天0小时"),
    ("NO.8", "XRP-USDT-SWAP", "short", "max_profit", 38.21, 3.48, 1.9738, 1.8984, "2025-12-29 17:02:09", "6天20小时"),
]

def create_extreme_records_table():
    """创建历史极值记录表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS position_extreme_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anchor_number TEXT,
            inst_id TEXT NOT NULL,
            pos_side TEXT NOT NULL,
            record_type TEXT NOT NULL,
            profit_rate REAL NOT NULL,
            pos_size REAL,
            open_price REAL,
            mark_price REAL,
            record_time TEXT,
            duration TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_extreme_inst_side 
        ON position_extreme_records(inst_id, pos_side, record_type)
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 表创建成功: position_extreme_records")

def import_records():
    """导入历史极值记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    imported_count = 0
    for record in extreme_records:
        try:
            cursor.execute('''
                INSERT INTO position_extreme_records 
                (anchor_number, inst_id, pos_side, record_type, profit_rate, 
                 pos_size, open_price, mark_price, record_time, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', record)
            imported_count += 1
        except Exception as e:
            print(f"❌ 导入失败: {record[1]} {record[2]} - {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ 成功导入 {imported_count} 条记录")

def show_statistics():
    """显示统计信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 总记录数
    cursor.execute("SELECT COUNT(*) FROM position_extreme_records")
    total = cursor.fetchone()[0]
    print(f"\n📊 总记录数: {total}")
    
    # 按类型统计
    cursor.execute('''
        SELECT record_type, COUNT(*) 
        FROM position_extreme_records 
        GROUP BY record_type
    ''')
    print("\n按类型统计:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}条")
    
    # 按币种统计
    cursor.execute('''
        SELECT inst_id, COUNT(*) 
        FROM position_extreme_records 
        GROUP BY inst_id 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    ''')
    print("\n前10个币种:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}条")
    
    # 最高盈利TOP5
    cursor.execute('''
        SELECT inst_id, pos_side, profit_rate, record_time
        FROM position_extreme_records 
        WHERE record_type = 'max_profit'
        ORDER BY profit_rate DESC 
        LIMIT 5
    ''')
    print("\n🏆 最高盈利TOP5:")
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]}: {row[2]:.2f}% ({row[3]})")
    
    # 最大亏损TOP5
    cursor.execute('''
        SELECT inst_id, pos_side, profit_rate, record_time
        FROM position_extreme_records 
        WHERE record_type = 'max_loss'
        ORDER BY profit_rate ASC 
        LIMIT 5
    ''')
    print("\n📉 最大亏损TOP5:")
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]}: {row[2]:.2f}% ({row[3]})")
    
    conn.close()

if __name__ == '__main__':
    print("="*60)
    print("导入历史极值记录")
    print("="*60)
    
    # 创建表
    create_extreme_records_table()
    
    # 导入数据
    import_records()
    
    # 显示统计
    show_statistics()
    
    print("\n✅ 导入完成!")

