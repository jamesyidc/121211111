#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 liquidation_30days 表
从 panic_wash_index 表聚合每天的爆仓数据
"""

import sqlite3
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = 'crypto_data.db'

def create_liquidation_30days_table():
    """创建 liquidation_30days 表（如果不存在）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS liquidation_30days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            long_amount REAL DEFAULT 0,
            short_amount REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ liquidation_30days 表已创建/确认存在")

def aggregate_daily_liquidation():
    """
    从 panic_wash_index 表聚合每天的爆仓数据
    计算每天的总爆仓金额（使用24小时数据的最大值）
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取最近30天的日期范围
    cursor.execute("""
        SELECT DISTINCT record_date 
        FROM panic_wash_index 
        WHERE record_date IS NOT NULL
        ORDER BY record_date DESC 
        LIMIT 30
    """)
    
    dates = [row[0] for row in cursor.fetchall()]
    
    if not dates:
        logger.warning("⚠️ panic_wash_index 表中没有数据")
        conn.close()
        return
    
    logger.info(f"📅 找到 {len(dates)} 天的数据，开始聚合...")
    
    # 对每一天进行聚合
    for date in dates:
        # 获取该天的最大24小时爆仓金额（单位：亿美元）
        cursor.execute("""
            SELECT MAX(hour_24_amount) as max_24h
            FROM panic_wash_index
            WHERE record_date = ?
            AND hour_24_amount IS NOT NULL
        """, (date,))
        
        row = cursor.fetchone()
        max_24h_yi = row[0] if row and row[0] else 0.0
        
        # 转换为美元（从亿美元）
        total_amount_usd = max_24h_yi * 100_000_000
        
        # 由于我们没有多空分离的数据，暂时设置为 0
        # 未来如果有多空数据可以从其他API获取
        long_amount_usd = 0
        short_amount_usd = 0
        
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 插入或更新记录
        cursor.execute("""
            INSERT OR REPLACE INTO liquidation_30days 
            (date, long_amount, short_amount, total_amount, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (date, long_amount_usd, short_amount_usd, total_amount_usd, updated_at))
        
        logger.info(f"  ✅ {date}: 总爆仓 ${total_amount_usd:,.0f} (${max_24h_yi:.2f}亿)")
    
    conn.commit()
    conn.close()
    logger.info(f"✅ 成功聚合 {len(dates)} 天的数据到 liquidation_30days 表")

def verify_data():
    """验证生成的数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM liquidation_30days
    """)
    count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT date, total_amount, updated_at 
        FROM liquidation_30days 
        ORDER BY date DESC 
        LIMIT 5
    """)
    
    logger.info(f"\n📊 liquidation_30days 表验证:")
    logger.info(f"   总记录数: {count}")
    logger.info(f"\n   最新5条记录:")
    
    for row in cursor.fetchall():
        date, total_amount, updated_at = row
        total_yi = total_amount / 100_000_000
        logger.info(f"   {date}: ${total_amount:,.0f} (${total_yi:.2f}亿) - 更新于 {updated_at}")
    
    conn.close()

def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 开始生成 liquidation_30days 表")
    logger.info("=" * 80)
    
    try:
        # 1. 创建表
        create_liquidation_30days_table()
        
        # 2. 聚合数据
        aggregate_daily_liquidation()
        
        # 3. 验证数据
        verify_data()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ liquidation_30days 表生成完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
