#!/usr/bin/env python3
"""
创建信号统计历史数据表
"""
import sqlite3

def create_tables():
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 创建信号统计历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_stats_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_time DATETIME NOT NULL,
            total_count INTEGER DEFAULT 0,
            long_count INTEGER DEFAULT 0,
            short_count INTEGER DEFAULT 0,
            chaodi_count INTEGER DEFAULT 0,
            dibu_count INTEGER DEFAULT 0,
            dingbu_count INTEGER DEFAULT 0,
            source_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(record_time)
        )
    ''')
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_signal_stats_record_time 
        ON signal_stats_history(record_time)
    ''')
    
    conn.commit()
    
    print("✅ 信号统计历史表创建成功")
    print("\n表结构:")
    cursor.execute("PRAGMA table_info(signal_stats_history)")
    for row in cursor.fetchall():
        print(f"  {row[1]}: {row[2]}")
    
    conn.close()

if __name__ == '__main__':
    create_tables()
