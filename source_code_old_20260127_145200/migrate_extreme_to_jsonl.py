#!/usr/bin/env python3
"""
历史极值数据迁移脚本
从SQLite迁移到JSONL
"""

import sqlite3
import sys
sys.path.insert(0, '/home/user/webapp/source_code')
from extreme_jsonl_manager import ExtremeJSONLManager

def migrate_extreme_records(trade_mode='real'):
    """
    迁移历史极值记录
    
    Args:
        trade_mode: 'real' 或 'paper'
    """
    print(f"开始迁移 {trade_mode} 模式的历史极值记录...")
    print("=" * 80)
    
    # 连接SQLite数据库
    conn = sqlite3.connect('/home/user/webapp/databases/anchor_system.db')
    cursor = conn.cursor()
    
    # 确定表名
    table_name = f'anchor_{trade_mode}_profit_records'
    
    # 查询所有记录
    cursor.execute(f"""
        SELECT id, inst_id, pos_side, record_type, profit_rate, 
               timestamp, pos_size, avg_price, mark_price, upl,
               margin, leverage, snapshot_data, created_at, updated_at
        FROM {table_name}
        ORDER BY created_at DESC
    """)
    
    records = cursor.fetchall()
    conn.close()
    
    print(f"从SQLite读取到 {len(records)} 条记录")
    
    # 初始化JSONL管理器
    manager = ExtremeJSONLManager(trade_mode)
    
    # 迁移记录
    success_count = 0
    for record in records:
        jsonl_record = {
            'id': record[0],
            'inst_id': record[1],
            'pos_side': record[2],
            'record_type': record[3],
            'profit_rate': record[4],
            'timestamp': record[5],
            'pos_size': record[6],
            'avg_price': record[7],
            'mark_price': record[8],
            'upl': record[9],
            'margin': record[10],
            'leverage': record[11],
            'snapshot_data': record[12],
            'created_at': record[13],
            'updated_at': record[14]
        }
        
        if manager.add_record(jsonl_record):
            success_count += 1
    
    print(f"成功迁移 {success_count}/{len(records)} 条记录")
    
    # 显示统计信息
    stats = manager.get_statistics()
    print(f"\nJSONL统计信息:")
    print(f"  总记录数: {stats['total_records']}")
    print(f"  币种数量: {stats['total_symbols']}")
    print(f"  文件大小: {stats['file_size_mb']} MB")
    print(f"  文件路径: {stats['file_path']}")
    
    # 显示最新几条记录
    print(f"\n最新10条记录:")
    latest = manager.get_latest_records(10)
    for i, rec in enumerate(latest, 1):
        print(f"  [{i:2}] {rec['inst_id']:20} {rec['pos_side']:5} "
              f"{rec['record_type']:15} 收益率: {rec['profit_rate']:8.2%} | {rec['created_at']}")
    
    print("\n" + "=" * 80)
    print(f"迁移完成！")

if __name__ == '__main__':
    # 迁移实盘数据
    migrate_extreme_records('real')
    
    print("\n")
    
    # 迁移模拟盘数据
    migrate_extreme_records('paper')
