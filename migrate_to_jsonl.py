#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：从SQLite迁移到JSONL
迁移价格涨速和V1V2成交额数据
"""

import sqlite3
import sys
import os
from datetime import datetime
import pytz

# 添加source_code到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'source_code'))

from price_speed_jsonl_manager import PriceSpeedJSONLManager
from v1v2_jsonl_manager import V1V2JSONLManager

beijing_tz = pytz.timezone('Asia/Shanghai')

def migrate_price_speed_data():
    """迁移价格涨速数据"""
    print("="*60)
    print("开始迁移价格涨速数据...")
    print("="*60)
    
    db_file = 'price_speed_data.db'
    if not os.path.exists(db_file):
        print(f"❌ 数据库文件不存在: {db_file}")
        return False
    
    # 检查数据库大小
    db_size = os.path.getsize(db_file)
    if db_size == 0:
        print(f"⚠️  数据库文件为空，跳过迁移")
        return True
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 创建JSONL管理器
        manager = PriceSpeedJSONLManager()
        
        # 1. 迁移最新状态数据
        print("\n📊 迁移最新状态数据...")
        cursor.execute('''
            SELECT symbol, current_price, previous_price, change_percent,
                   alert_level, alert_type, timestamp, updated_at
            FROM latest_price_speed
            ORDER BY symbol
        ''')
        
        latest_count = 0
        for row in cursor.fetchall():
            success = manager.add_latest_record(
                symbol=row['symbol'],
                current_price=row['current_price'],
                previous_price=row['previous_price'],
                change_percent=row['change_percent'],
                alert_level=row['alert_level'],
                alert_type=row['alert_type'],
                timestamp=row['timestamp']
            )
            if success:
                latest_count += 1
        
        print(f"✅ 最新状态: {latest_count} 条记录")
        
        # 2. 迁移历史数据（最近1000条）
        print("\n📊 迁移历史数据...")
        cursor.execute('''
            SELECT symbol, current_price, previous_price, change_percent,
                   alert_level, alert_type, timestamp
            FROM price_speed_alerts
            ORDER BY timestamp DESC
            LIMIT 10000
        ''')
        
        history_count = 0
        for row in cursor.fetchall():
            success = manager.add_history_record(
                symbol=row['symbol'],
                current_price=row['current_price'],
                previous_price=row['previous_price'],
                change_percent=row['change_percent'],
                alert_level=row['alert_level'],
                alert_type=row['alert_type'],
                timestamp=row['timestamp']
            )
            if success:
                history_count += 1
        
        print(f"✅ 历史记录: {history_count} 条记录")
        
        # 获取统计信息
        stats = manager.get_statistics()
        print(f"\n📈 迁移后统计:")
        print(f"   - 总币种数: {stats['total_count']}")
        print(f"   - 上涨预警: {stats['alert_up']}")
        print(f"   - 下跌预警: {stats['alert_down']}")
        print(f"   - 正常状态: {stats['alert_normal']}")
        print(f"   - 历史记录: {stats['history_count']}")
        print(f"   - 更新时间: {stats['update_time']}")
        
        conn.close()
        print("\n✅ 价格涨速数据迁移完成")
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_v1v2_data():
    """迁移V1V2成交额数据"""
    print("\n" + "="*60)
    print("开始迁移V1V2成交额数据...")
    print("="*60)
    
    db_file = 'v1v2_data.db'
    if not os.path.exists(db_file):
        print(f"❌ 数据库文件不存在: {db_file}")
        return False
    
    # 检查数据库大小
    db_size = os.path.getsize(db_file)
    if db_size == 0:
        print(f"⚠️  数据库文件为空，跳过迁移")
        return True
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 创建JSONL管理器
        manager = V1V2JSONLManager()
        
        # 获取所有表名（每个币种一个表）
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'volume_%'
        ''')
        tables = [row['name'] for row in cursor.fetchall()]
        
        if not tables:
            print("⚠️  没有找到任何数据表")
            return True
        
        print(f"📊 找到 {len(tables)} 个币种表")
        
        # 定义阈值（从v1v2_collector.py中的配置）
        COINS_CONFIG = {
            'BTC': {'v1': 200000, 'v2': 100000},
            'ETH': {'v1': 1300000, 'v2': 500000},
            'XRP': {'v1': 200000, 'v2': 87000},
            'SOL': {'v1': 351620, 'v2': 246380},
            'BNB': {'v1': 2388300, 'v2': 1737500},
            'LTC': {'v1': 50000, 'v2': 15000},
            'DOGE': {'v1': 150000, 'v2': 60000},
            'SUI': {'v1': 2000000, 'v2': 800000},
            'TRX': {'v1': 13280, 'v2': 6022},
            'TON': {'v1': 350000, 'v2': 200000},
            'ETC': {'v1': 12000, 'v2': 2000},
            'BCH': {'v1': 103500, 'v2': 50000},
            'HBAR': {'v1': 103500, 'v2': 40000},
            'XLM': {'v1': 103500, 'v2': 30000},
            'FIL': {'v1': 5003500, 'v2': 3700000},
            'ADA': {'v1': 67210, 'v2': 44230},
            'LINK': {'v1': 280000, 'v2': 200000},
            'CRO': {'v1': 100000, 'v2': 40000},
            'DOT': {'v1': 300000, 'v2': 250000},
            'UNI': {'v1': 140000, 'v2': 100000},
            'NEAR': {'v1': 100000, 'v2': 50000},
            'APT': {'v1': 300000, 'v2': 200000},
            'CFX': {'v1': 300000, 'v2': 250000},
            'CRV': {'v1': 1500000, 'v2': 1000000},
            'STX': {'v1': 50000, 'v2': 30000},
            'LDO': {'v1': 1000000, 'v2': 600000},
            'TAO': {'v1': 300000, 'v2': 180000}
        }
        
        latest_count = 0
        history_count = 0
        
        for table in tables:
            # 提取币种名称（volume_btc -> BTC）
            symbol = table.replace('volume_', '').upper()
            
            # 获取阈值
            config = COINS_CONFIG.get(symbol, {'v1': 100000, 'v2': 50000})
            v1_threshold = config['v1']
            v2_threshold = config['v2']
            
            # 获取最新记录
            cursor.execute(f'''
                SELECT volume, level, timestamp
                FROM {table}
                ORDER BY timestamp DESC
                LIMIT 1
            ''')
            
            latest_row = cursor.fetchone()
            if latest_row:
                success = manager.add_latest_record(
                    symbol=symbol,
                    volume=latest_row['volume'],
                    v1_threshold=v1_threshold,
                    v2_threshold=v2_threshold,
                    level=latest_row['level'],
                    timestamp=latest_row['timestamp']
                )
                if success:
                    latest_count += 1
            
            # 获取历史记录（最近100条）
            cursor.execute(f'''
                SELECT volume, level, timestamp
                FROM {table}
                ORDER BY timestamp DESC
                LIMIT 100
            ''')
            
            for row in cursor.fetchall():
                success = manager.add_history_record(
                    symbol=symbol,
                    volume=row['volume'],
                    v1_threshold=v1_threshold,
                    v2_threshold=v2_threshold,
                    level=row['level'],
                    timestamp=row['timestamp']
                )
                if success:
                    history_count += 1
        
        print(f"✅ 最新状态: {latest_count} 条记录")
        print(f"✅ 历史记录: {history_count} 条记录")
        
        # 获取统计信息
        stats = manager.get_statistics()
        print(f"\n📈 迁移后统计:")
        print(f"   - 总币种数: {stats['total_count']}")
        print(f"   - V1级别: {stats['v1_count']}")
        print(f"   - V2级别: {stats['v2_count']}")
        print(f"   - 无级别: {stats['none_count']}")
        print(f"   - 历史记录: {stats['history_count']}")
        print(f"   - 更新时间: {stats['update_time']}")
        
        # 显示V1V2币种
        v1v2 = manager.get_v1v2_coins()
        if v1v2['v1_coins']:
            print(f"\n🔥 V1级别币种: {', '.join(v1v2['v1_coins'])}")
        if v1v2['v2_coins']:
            print(f"⚡ V2级别币种: {', '.join(v1v2['v2_coins'])}")
        
        conn.close()
        print("\n✅ V1V2成交额数据迁移完成")
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("🚀 开始数据迁移 (SQLite -> JSONL)")
    print(f"⏰ 时间: {datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 迁移价格涨速数据
    success1 = migrate_price_speed_data()
    
    # 迁移V1V2数据
    success2 = migrate_v1v2_data()
    
    print("\n" + "="*60)
    if success1 and success2:
        print("✅ 所有数据迁移完成！")
    else:
        print("⚠️  部分数据迁移失败，请检查日志")
    print("="*60)
