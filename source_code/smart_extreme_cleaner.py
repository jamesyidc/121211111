#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能极值数据清理工具 - 删除异常高的盈利记录
基于实际持仓情况，清理不合理的历史极值
"""

import sqlite3
import sys
sys.path.insert(0, '/home/user/webapp')
from extreme_correction_system import DB_PATH, init_correction_system, backup_current_data

# 配置阈值
MAX_REASONABLE_PROFIT = 50.0  # 最大合理盈利率 50%
MAX_REASONABLE_LOSS = -50.0   # 最大合理亏损率 -50%

def detect_unreasonable_records():
    """检测不合理的极值记录"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 查找超过阈值的盈利记录
    cursor.execute('''
    SELECT id, inst_id, pos_side, record_type, profit_rate, timestamp
    FROM anchor_profit_records
    WHERE (record_type = 'max_profit' AND profit_rate > ?)
       OR (record_type = 'max_loss' AND profit_rate < ?)
    ORDER BY ABS(profit_rate) DESC
    ''', (MAX_REASONABLE_PROFIT, MAX_REASONABLE_LOSS))
    
    unreasonable_records = cursor.fetchall()
    conn.close()
    
    return unreasonable_records


def clean_unreasonable_records():
    """清理不合理的极值记录"""
    print("\n" + "=" * 60)
    print("🔧 智能极值清理 - 删除异常数据")
    print("=" * 60)
    print(f"\n清理标准:")
    print(f"  • 盈利记录 > {MAX_REASONABLE_PROFIT}% 视为异常")
    print(f"  • 亏损记录 < {MAX_REASONABLE_LOSS}% 视为异常")
    print()
    
    # 初始化系统
    from anchor_system import init_database
    init_database()
    init_correction_system()
    
    # 备份
    print("[1/4] 备份当前数据...")
    backup_count = backup_current_data()
    
    # 检测
    print("\n[2/4] 检测不合理记录...")
    unreasonable_records = detect_unreasonable_records()
    
    if not unreasonable_records:
        print("✅ 没有发现不合理记录，数据正常！")
        return
    
    print(f"\n检测到 {len(unreasonable_records)} 条不合理记录:\n")
    for record in unreasonable_records:
        record_id, inst_id, pos_side, record_type, profit_rate, timestamp = record
        print(f"⚠️  [{record_id}] {inst_id} {pos_side} {record_type}: {profit_rate:+.2f}%")
    
    # 删除
    print(f"\n[3/4] 删除不合理记录...")
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    deleted_count = 0
    for record in unreasonable_records:
        record_id, inst_id, pos_side, record_type, profit_rate, timestamp = record
        
        # 记录到日志
        cursor.execute('''
        INSERT INTO extreme_corrections_log (
            correction_type, inst_id, pos_side, record_type,
            old_profit_rate, new_profit_rate, reason
        ) VALUES (?, ?, ?, ?, ?, NULL, ?)
        ''', ('delete', inst_id, pos_side, record_type, profit_rate, 
              f'智能清理：超出合理范围 ({MAX_REASONABLE_PROFIT}%)'))
        
        # 删除记录
        cursor.execute('DELETE FROM anchor_profit_records WHERE id = ?', (record_id,))
        deleted_count += 1
        print(f"🗑️  已删除: {inst_id} {pos_side} {record_type} ({profit_rate:+.2f}%)")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 共删除 {deleted_count} 条不合理记录")
    
    # 统计
    print("\n[4/4] 清理后统计...")
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT COUNT(*),
           AVG(CASE WHEN record_type = 'max_profit' THEN profit_rate END),
           MAX(CASE WHEN record_type = 'max_profit' THEN profit_rate END),
           AVG(CASE WHEN record_type = 'max_loss' THEN profit_rate END),
           MIN(CASE WHEN record_type = 'max_loss' THEN profit_rate END)
    FROM anchor_profit_records
    ''')
    
    total, avg_profit, max_profit, avg_loss, min_loss = cursor.fetchone()
    
    cursor.execute('''
    SELECT COUNT(*) FROM anchor_profit_records WHERE record_type = 'max_profit'
    ''')
    profit_count = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT COUNT(*) FROM anchor_profit_records WHERE record_type = 'max_loss'
    ''')
    loss_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n=== 清理后数据统计 ===")
    print(f"总记录数: {total}")
    print(f"盈利记录: {profit_count} 条")
    if avg_profit:
        print(f"  平均盈利: {avg_profit:+.2f}%")
        print(f"  最高盈利: {max_profit:+.2f}%")
    print(f"亏损记录: {loss_count} 条")
    if avg_loss:
        print(f"  平均亏损: {avg_loss:+.2f}%")
        print(f"  最大亏损: {min_loss:+.2f}%")
    
    print("\n" + "=" * 60)
    print("✅ 智能清理完成！")
    print("=" * 60)


if __name__ == '__main__':
    clean_unreasonable_records()
