#!/usr/bin/env python3
"""
将Google Drive数据从SQLite迁移到JSONL
"""
import sys
sys.path.append('/home/user/webapp/source_code')

import sqlite3
import json
from gdrive_jsonl_manager import GDriveJSONLManager

DB_PATH = '/home/user/webapp/databases/crypto_data.db'

def migrate_db_to_jsonl():
    """将数据库数据迁移到JSONL"""
    print("=" * 80)
    print("🔄 Google Drive数据迁移: SQLite → JSONL")
    print("=" * 80)
    
    try:
        # 连接数据库
        print("\n1️⃣ 连接数据库...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 查询所有数据
        print("2️⃣ 读取数据库记录...")
        cursor.execute('''
            SELECT snapshot_date, snapshot_time, inst_id, last_price, vol_24h,
                   rush_up, rush_down, diff, count, status, change_24h, created_at,
                   high_24h, low_24h, count_score_display, count_score_type
            FROM crypto_snapshots
            ORDER BY snapshot_time DESC
        ''')
        
        rows = cursor.fetchall()
        print(f"   找到 {len(rows)} 条记录")
        
        if len(rows) == 0:
            print("⚠️  数据库为空，无需迁移")
            conn.close()
            return
        
        # 转换为字典格式
        print("3️⃣ 转换数据格式...")
        records = []
        for row in rows:
            record = {
                'snapshot_date': row[0],
                'snapshot_time': row[1],
                'inst_id': row[2],
                'last_price': float(row[3]) if row[3] is not None else None,
                'vol_24h': float(row[4]) if row[4] is not None else None,
                'rush_up': int(row[5]) if row[5] is not None else 0,
                'rush_down': int(row[6]) if row[6] is not None else 0,
                'diff': int(row[7]) if row[7] is not None else 0,
                'count': int(row[8]) if row[8] is not None else 0,
                'status': row[9] if row[9] else '',
                'change_24h': float(row[10]) if row[10] is not None else 0.0,
                'created_at': row[11] if row[11] else None,
                'high_24h': float(row[12]) if row[12] is not None else None,
                'low_24h': float(row[13]) if row[13] is not None else None,
                'count_score_display': row[14] if row[14] else None,
                'count_score_type': row[15] if row[15] else None
            }
            records.append(record)
        
        conn.close()
        
        # 写入JSONL
        print("4️⃣ 写入JSONL文件...")
        manager = GDriveJSONLManager()
        manager.write_all_snapshots(records, backup=False)
        
        # 验证数据
        print("\n5️⃣ 验证迁移结果...")
        stats = manager.get_statistics()
        print(f"   总记录数: {stats['total_records']}")
        print(f"   唯一日期数: {stats['unique_dates']}")
        print(f"   唯一时间点: {stats['unique_times']}")
        print(f"   唯一币种数: {stats['unique_inst_ids']}")
        print(f"   最新时间: {stats['latest_snapshot_time']}")
        print(f"   最旧时间: {stats['oldest_snapshot_time']}")
        
        # 抽样验证
        print("\n6️⃣ 抽样验证数据...")
        sample_records = records[:3]
        for i, record in enumerate(sample_records, 1):
            print(f"\n   样本 {i}:")
            print(f"   - 时间: {record['snapshot_time']}")
            print(f"   - 币种: {record['inst_id']}")
            print(f"   - 价格: {record['last_price']}")
            print(f"   - 24h涨幅: {record['change_24h']}%")
            print(f"   - 急涨: {record['rush_up']}, 急跌: {record['rush_down']}")
        
        print("\n" + "=" * 80)
        print("✅ 迁移完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    migrate_db_to_jsonl()
