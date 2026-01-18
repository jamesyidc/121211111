#!/usr/bin/env python3
"""
数据验证和清理工具

规则：
1. 1天时间内，急涨数量不能变小（单调递增）
2. 1天时间内，急跌数量不能变小（单调递增）
3. 计次相邻最多只能增加1，不能减少，不能增加超过1
4. 时间间隔超过2小时，允许计次跳跃（认为是新的数据批次）
"""
import sqlite3
import sys
from datetime import datetime, timedelta

def validate_daily_data(date_str):
    """验证某一天的数据是否符合规则"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, snapshot_time, rush_up, rush_down, count, status, filename
        FROM crypto_snapshots 
        WHERE snapshot_date = ?
        ORDER BY snapshot_time ASC
    """, (date_str,))
    
    records = cursor.fetchall()
    conn.close()
    
    if not records:
        print(f"⚠️  日期 {date_str} 没有数据")
        return [], []
    
    print(f"\n{'='*100}")
    print(f"📊 验证日期: {date_str} ({len(records)} 条记录)")
    print(f"{'='*100}\n")
    print(f"{'时间':20s} | 急涨 | 急跌 | 计次 | 状态 | 文件名")
    print("-" * 100)
    
    violations = []
    invalid_ids = []
    prev_rush_up = None
    prev_rush_down = None
    prev_count = None
    prev_time = None
    
    for i, record in enumerate(records):
        record_id, time, rush_up, rush_down, count, status, filename = record
        time_str = time.split(' ')[1] if ' ' in time else time
        
        is_valid = True
        reasons = []
        
        # 解析时间
        try:
            current_time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                current_time = datetime.strptime(f"{date_str} {time}", '%Y-%m-%d %H:%M:%S')
            except:
                current_time = None
        
        # 计算时间间隔
        time_gap_hours = 0
        if prev_time and current_time:
            time_gap = current_time - prev_time
            time_gap_hours = time_gap.total_seconds() / 3600
        
        # 验证规则
        if prev_rush_up is not None:
            # 规则1: 急涨不能变小
            if rush_up < prev_rush_up:
                reasons.append(f"急涨从 {prev_rush_up} 降到 {rush_up}")
                is_valid = False
            
            # 规则2: 急跌不能变小
            if rush_down < prev_rush_down:
                reasons.append(f"急跌从 {prev_rush_down} 降到 {rush_down}")
                is_valid = False
            
            # 规则3: 计次最多增加1（如果时间间隔 < 2小时）
            count_diff = count - prev_count
            if time_gap_hours < 2:  # 只在连续时间段验证
                if count_diff > 1:
                    reasons.append(f"计次从 {prev_count} 增加到 {count} (+{count_diff}, 超过1)")
                    is_valid = False
                elif count_diff < 0:
                    reasons.append(f"计次从 {prev_count} 降到 {count}")
                    is_valid = False
            else:
                # 时间间隔超过2小时，标记为新批次
                if count_diff < 0:
                    reasons.append(f"计次从 {prev_count} 降到 {count} (跨 {time_gap_hours:.1f}小时)")
                    is_valid = False
        
        status_icon = "✅" if is_valid else "❌"
        print(f"{status_icon} {time_str:18s} | {rush_up:4d} | {rush_down:4d} | {count:4d} | {status:10s} | {filename or 'N/A'}")
        
        if not is_valid:
            violation = {
                'id': record_id,
                'time': time_str,
                'reasons': reasons,
                'data': (rush_up, rush_down, count)
            }
            violations.append(violation)
            invalid_ids.append(record_id)
            for reason in reasons:
                print(f"   ⚠️  {reason}")
        
        prev_rush_up = rush_up
        prev_rush_down = rush_down
        prev_count = count
        prev_time = current_time
    
    print("\n" + "=" * 100)
    if violations:
        print(f"❌ 发现 {len(violations)} 条违反规则的记录")
        print("=" * 100)
    else:
        print("✅ 所有数据符合规则！")
        print("=" * 100)
    
    return violations, invalid_ids

def delete_invalid_records(invalid_ids):
    """删除违反规则的记录"""
    if not invalid_ids:
        print("\n✅ 没有需要删除的记录")
        return
    
    print(f"\n{'='*100}")
    print(f"🗑️  准备删除 {len(invalid_ids)} 条违反规则的记录")
    print(f"{'='*100}")
    
    # 显示将要删除的记录
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    for record_id in invalid_ids:
        cursor.execute("""
            SELECT snapshot_time, rush_up, rush_down, count, filename
            FROM crypto_snapshots 
            WHERE id = ?
        """, (record_id,))
        record = cursor.fetchone()
        if record:
            time, rush_up, rush_down, count, filename = record
            print(f"   ID {record_id}: {time} (急涨:{rush_up} 急跌:{rush_down} 计次:{count}) - {filename or 'N/A'}")
    
    # 确认删除
    response = input(f"\n⚠️  确认删除这 {len(invalid_ids)} 条记录吗？(yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ 取消删除操作")
        conn.close()
        return
    
    # 删除记录
    deleted_count = 0
    for record_id in invalid_ids:
        cursor.execute("DELETE FROM crypto_snapshots WHERE id = ?", (record_id,))
        deleted_count += cursor.rowcount
        
        # 同时删除对应的币种数据
        cursor.execute("""
            DELETE FROM crypto_coin_data 
            WHERE snapshot_time IN (
                SELECT snapshot_time FROM crypto_snapshots WHERE id = ?
            )
        """, (record_id,))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 已删除 {deleted_count} 条快照记录及相关币种数据")

def main():
    if len(sys.argv) < 2:
        print("用法: python3 validate_and_clean_data.py <date> [--clean]")
        print("示例: python3 validate_and_clean_data.py 2025-12-09")
        print("示例: python3 validate_and_clean_data.py 2025-12-09 --clean  (验证并清理)")
        sys.exit(1)
    
    date_str = sys.argv[1]
    do_clean = '--clean' in sys.argv
    
    # 验证数据
    violations, invalid_ids = validate_daily_data(date_str)
    
    # 如果需要清理
    if do_clean and invalid_ids:
        delete_invalid_records(invalid_ids)
        
        # 重新验证
        print(f"\n\n{'='*100}")
        print("🔄 重新验证清理后的数据...")
        print(f"{'='*100}")
        validate_daily_data(date_str)
    elif invalid_ids:
        print(f"\n💡 提示: 使用 --clean 参数可以自动清理违规数据")
        print(f"   命令: python3 validate_and_clean_data.py {date_str} --clean")

if __name__ == '__main__':
    main()
