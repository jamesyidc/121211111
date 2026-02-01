#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建首页数据缓存表
"""
import sqlite3
from datetime import datetime

db_path = '/home/user/webapp/crypto_data.db'

def create_home_cache_table():
    """创建首页数据缓存表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建首页数据缓存表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS home_data_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            time_diff REAL,
            rush_up INTEGER,
            rush_down INTEGER,
            status TEXT,
            ratio REAL,
            green_count INTEGER,
            percentage REAL,
            coin_data TEXT,  -- JSON格式存储币种数据
            update_time TEXT NOT NULL,
            cached_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_home_cache_time 
        ON home_data_cache(update_time DESC)
    """)
    
    conn.commit()
    print("✅ 首页数据缓存表创建成功")
    
    # 查看表结构
    cursor.execute("PRAGMA table_info(home_data_cache)")
    columns = cursor.fetchall()
    
    print("\n表结构:")
    for col in columns:
        print(f"  - {col[1]:<20} {col[2]:<10}")
    
    conn.close()

if __name__ == '__main__':
    create_home_cache_table()
