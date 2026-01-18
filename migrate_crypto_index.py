#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crypto Index数据迁移脚本：从SQLite迁移到JSONL
"""

import sqlite3
import sys
import os
from datetime import datetime
import pytz

# 添加source_code到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'source_code'))

from crypto_index_jsonl_manager import CryptoIndexJSONLManager

beijing_tz = pytz.timezone('Asia/Shanghai')

def migrate_crypto_index_data():
    """迁移Crypto Index数据"""
    print("="*60)
    print("开始迁移Crypto Index数据...")
    print("="*60)
    
    db_file = 'crypto_data.db'
    if not os.path.exists(db_file):
        print(f"❌ 数据库文件不存在: {db_file}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 创建JSONL管理器
        manager = CryptoIndexJSONLManager()
        
        # 1. 迁移基准价格
        print("\n📊 迁移基准价格...")
        try:
            cursor.execute('''
                SELECT coin_id, base_price
                FROM crypto_index_base_prices
            ''')
            
            base_count = 0
            for row in cursor.fetchall():
                success = manager.set_base_price(
                    coin_id=row['coin_id'],
                    base_price=row['base_price']
                )
                if success:
                    base_count += 1
            
            print(f"✅ 基准价格: {base_count} 条记录")
        except sqlite3.OperationalError as e:
            print(f"⚠️  基准价格表不存在或为空: {e}")
        
        # 2. 迁移K线数据（最近1000条）
        print("\n📊 迁移K线数据...")
        try:
            cursor.execute('''
                SELECT timestamp, open_price, high_price, low_price, 
                       close_price, index_value
                FROM crypto_index_klines
                ORDER BY timestamp DESC
                LIMIT 1000
            ''')
            
            kline_count = 0
            rows = cursor.fetchall()
            
            # 反转顺序，从旧到新插入
            for row in reversed(rows):
                success = manager.add_kline(
                    timestamp=row['timestamp'],
                    open_price=row['open_price'],
                    high_price=row['high_price'],
                    low_price=row['low_price'],
                    close_price=row['close_price'],
                    index_value=row['index_value']
                )
                if success:
                    kline_count += 1
            
            print(f"✅ K线数据: {kline_count} 条记录")
        except sqlite3.OperationalError as e:
            print(f"⚠️  K线表不存在或为空: {e}")
        
        # 获取统计信息
        stats = manager.get_statistics()
        print(f"\n📈 迁移后统计:")
        print(f"   - K线总数: {stats['total_klines']}")
        print(f"   - 基准价格数: {stats['base_prices_count']}")
        if stats['latest_value']:
            print(f"   - 最新指数: {stats['latest_value']}")
            print(f"   - 最新时间: {stats['latest_timestamp']}")
        
        conn.close()
        print("\n✅ Crypto Index数据迁移完成")
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("🚀 开始Crypto Index数据迁移 (SQLite -> JSONL)")
    print(f"⏰ 时间: {datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = migrate_crypto_index_data()
    
    print("\n" + "="*60)
    if success:
        print("✅ 数据迁移完成！")
    else:
        print("⚠️  数据迁移失败，请检查日志")
    print("="*60)
