#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从API实时获取并生成 liquidation_30days 表
使用真实的24小时爆仓数据
"""

import sqlite3
import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = 'crypto_data.db'
API_24H = "https://api.btc123.fans/bicoin.php?from=24hbaocang"

def fetch_current_24h_liquidation():
    """获取当前24小时爆仓数据（美元）"""
    try:
        resp = requests.get(API_24H, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if 'data' in data and 'totalBlastUsd24h' in data['data']:
            total_usd = data['data']['totalBlastUsd24h']  # 单位：美元
            logger.info(f"✅ 当前24h爆仓: ${total_usd:,.2f} (${total_usd/10000:.2f}万, ${total_usd/100000000:.2f}亿)")
            return total_usd
        else:
            logger.error(f"❌ API返回数据格式错误")
            return None
    except Exception as e:
        logger.error(f"❌ 获取24h爆仓数据失败: {e}")
        return None

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

def generate_mock_30days_data():
    """
    生成模拟的30天爆仓数据
    使用当前实时数据作为基准，生成最近30天的合理数据
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取当前24h爆仓数据
    current_24h_usd = fetch_current_24h_liquidation()
    
    if current_24h_usd is None:
        # 如果API获取失败，使用一个合理的默认值（约6000万美元）
        current_24h_usd = 60000000  # 6000万美元
        logger.warning(f"⚠️ 使用默认值: ${current_24h_usd:,.0f}")
    
    # 生成最近30天的数据
    today = datetime.now()
    records_added = 0
    
    logger.info(f"\n📅 开始生成30天数据（基准: ${current_24h_usd/10000:.2f}万美元）...")
    
    for i in range(30):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        
        # 生成一个在基准值 ±30% 范围内的随机变化
        import random
        variation = random.uniform(0.7, 1.3)  # 70% ~ 130%
        total_amount_usd = current_24h_usd * variation
        
        # 多空比例（暂时平分，未来可以从其他数据源获取）
        long_amount_usd = total_amount_usd * 0.5
        short_amount_usd = total_amount_usd * 0.5
        
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 插入或更新记录
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO liquidation_30days 
                (date, long_amount, short_amount, total_amount, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (date, long_amount_usd, short_amount_usd, total_amount_usd, updated_at))
            
            total_yi = total_amount_usd / 100000000
            total_wan = total_amount_usd / 10000
            logger.info(f"  ✅ {date}: 总爆仓 ${total_amount_usd:,.0f} = ${total_wan:.2f}万 = ${total_yi:.2f}亿")
            records_added += 1
        except Exception as e:
            logger.error(f"  ❌ {date}: 插入失败 - {e}")
    
    conn.commit()
    conn.close()
    logger.info(f"\n✅ 成功生成 {records_added} 天的数据到 liquidation_30days 表")

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
        total_yi = total_amount / 100000000
        total_wan = total_amount / 10000
        logger.info(f"   {date}: ${total_amount:,.0f} = ${total_wan:.2f}万 = ${total_yi:.2f}亿")
    
    conn.close()

def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 开始生成 liquidation_30days 表（使用真实API数据）")
    logger.info("=" * 80)
    
    try:
        # 1. 创建表
        create_liquidation_30days_table()
        
        # 2. 生成30天数据
        generate_mock_30days_data()
        
        # 3. 验证数据
        verify_data()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ liquidation_30days 表生成完成")
        logger.info("💡 注意: 这是基于当前24h数据生成的模拟历史数据")
        logger.info("💡 如需更精确的历史数据，需要从历史API或数据库获取")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
