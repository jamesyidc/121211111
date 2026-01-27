#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库表结构定义
"""

import sqlite3
from datetime import datetime

DB_PATH = 'crypto_data.db'

def init_database():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建统计数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            record_time DATETIME NOT NULL,
            rush_up INTEGER DEFAULT 0,
            rush_down INTEGER DEFAULT 0,
            status TEXT,
            ratio TEXT,
            green_count INTEGER DEFAULT 0,
            percentage TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_time ON stats_history(record_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_filename ON stats_history(filename)')
    
    # 创建币种数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coin_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stats_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            record_time DATETIME NOT NULL,
            index_num INTEGER,
            symbol TEXT NOT NULL,
            change REAL,
            rush_up INTEGER DEFAULT 0,
            rush_down INTEGER DEFAULT 0,
            update_time DATETIME,
            high_price REAL,
            high_time DATE,
            decline REAL,
            change_24h REAL,
            rank INTEGER,
            current_price REAL,
            ratio1 TEXT,
            ratio2 TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stats_id) REFERENCES stats_history(id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coin_record_time ON coin_history(record_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coin_symbol ON coin_history(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coin_stats_id ON coin_history(stats_id)')
    
    conn.commit()
    conn.close()
    
    print("✅ 数据库表结构创建成功")
    print(f"   数据库路径: {DB_PATH}")
    print(f"   表: stats_history (统计数据)")
    print(f"   表: coin_history (币种数据)")

def get_db_stats():
    """获取数据库统计信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM stats_history')
    stats_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM coin_history')
    coin_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM stats_history')
    time_range = cursor.fetchone()
    
    conn.close()
    
    return {
        'stats_count': stats_count,
        'coin_count': coin_count,
        'earliest': time_range[0],
        'latest': time_range[1]
    }

if __name__ == '__main__':
    init_database()
    
    # 显示统计信息
    stats = get_db_stats()
    print(f"\n📊 数据库统计:")
    print(f"   统计记录数: {stats['stats_count']}")
    print(f"   币种记录数: {stats['coin_count']}")
    if stats['earliest']:
        print(f"   时间范围: {stats['earliest']} ~ {stats['latest']}")
