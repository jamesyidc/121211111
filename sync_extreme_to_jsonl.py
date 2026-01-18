#!/usr/bin/env python3
"""
同步数据库中的极值记录到JSONL文件
将 anchor_real_profit_records 表数据同步到 data/anchor_jsonl/anchor_real_profit_records.jsonl
"""

import sqlite3
import json
import os
from datetime import datetime

# 配置
DB_PATH = 'databases/anchor_system.db'
JSONL_PATH = 'data/anchor_jsonl/anchor_real_profit_records.jsonl'

def sync_extreme_records():
    """同步数据库极值记录到JSONL"""
    
    print("=" * 80)
    print("🔄 同步极值记录：数据库 → JSONL")
    print("=" * 80)
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 查询所有极值记录
    cursor.execute("""
        SELECT 
            inst_id,
            pos_side,
            record_type,
            profit_rate,
            timestamp,
            pos_size,
            avg_price,
            mark_price,
            upl,
            margin,
            leverage,
            created_at,
            updated_at
        FROM anchor_real_profit_records
        ORDER BY inst_id, pos_side, record_type
    """)
    
    records = cursor.fetchall()
    conn.close()
    
    print(f"\n📊 从数据库读取到 {len(records)} 条记录")
    
    # 备份旧文件
    if os.path.exists(JSONL_PATH):
        backup_path = f"{JSONL_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(JSONL_PATH, backup_path)
        print(f"💾 旧文件已备份到: {backup_path}")
    
    # 写入JSONL
    with open(JSONL_PATH, 'w', encoding='utf-8') as f:
        for record in records:
            inst_id, pos_side, record_type, profit_rate, timestamp, pos_size, avg_price, mark_price, upl, margin, leverage, created_at, updated_at = record
            
            jsonl_record = {
                'inst_id': inst_id,
                'pos_side': pos_side,
                'record_type': record_type,
                'profit_rate': profit_rate,
                'timestamp': timestamp,
                'pos_size': pos_size,
                'avg_price': avg_price,
                'mark_price': mark_price,
                'upl': upl,
                'margin': margin,
                'leverage': leverage,
                'created_at': created_at,
                'updated_at': updated_at
            }
            
            f.write(json.dumps(jsonl_record, ensure_ascii=False) + '\n')
    
    print(f"✅ 已写入 {len(records)} 条记录到: {JSONL_PATH}")
    
    # 显示部分数据验证
    print("\n📈 数据验证 - 部分币种示例:")
    print("-" * 80)
    
    test_symbols = ['CFX', 'FIL', 'STX', 'SOL', 'AAVE']
    for symbol in test_symbols:
        inst_id_pattern = f"{symbol}-USDT-SWAP"
        matching = [r for r in records if r[0] == inst_id_pattern]
        if matching:
            print(f"\n{symbol}:")
            for record in matching:
                pos_side, record_type, profit_rate = record[1], record[2], record[3]
                side_name = "做多" if pos_side == "long" else "做空"
                type_name = "最大盈利" if record_type == "max_profit" else "最大亏损"
                print(f"  {side_name} {type_name}: {profit_rate:+.2f}%")
    
    print("\n" + "=" * 80)
    print("✅ 同步完成！")
    print("=" * 80)

if __name__ == '__main__':
    sync_extreme_records()
