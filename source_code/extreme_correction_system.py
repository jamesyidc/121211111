#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极值数据纠错和回档系统
用于修正历史极值记录中的错误数据，并支持数据回档功能
"""

import sqlite3
import json
from datetime import datetime
import pytz

# 配置
import sys
import os

# 从 anchor_system 加载配置
sys.path.insert(0, '/home/user/webapp')
from anchor_system import DB_PATH as ANCHOR_DB_PATH

DB_PATH = ANCHOR_DB_PATH
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

print(f"📌 使用数据库: {DB_PATH}")

# 备份表名
BACKUP_TABLE = 'anchor_profit_records_backup'
CORRECTION_LOG_TABLE = 'extreme_corrections_log'


def init_correction_system():
    """初始化纠错系统数据库表"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 创建纠错日志表
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {CORRECTION_LOG_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        correction_type TEXT NOT NULL,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        record_type TEXT NOT NULL,
        old_profit_rate REAL,
        new_profit_rate REAL,
        reason TEXT,
        operator TEXT DEFAULT 'system',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        backup_snapshot TEXT
    )
    ''')
    
    # 创建备份表（如果不存在）
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {BACKUP_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        record_type TEXT NOT NULL,
        profit_rate REAL NOT NULL,
        timestamp TEXT NOT NULL,
        pos_size REAL,
        avg_price REAL,
        mark_price REAL,
        upl REAL,
        margin REAL,
        leverage REAL,
        snapshot_data TEXT,
        backup_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        original_created_at TEXT,
        original_updated_at TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 纠错系统初始化完成")


def backup_current_data():
    """备份当前所有极值数据"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    backup_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    # 复制当前数据到备份表
    cursor.execute(f'''
    INSERT INTO {BACKUP_TABLE} (
        inst_id, pos_side, record_type, profit_rate, timestamp,
        pos_size, avg_price, mark_price, upl, margin, leverage,
        snapshot_data, original_created_at, original_updated_at
    )
    SELECT 
        inst_id, pos_side, record_type, profit_rate, timestamp,
        pos_size, avg_price, mark_price, upl, margin, leverage,
        snapshot_data, created_at, updated_at
    FROM anchor_profit_records
    ''')
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ 已备份 {count} 条极值记录 (备份时间: {backup_time})")
    return count


def detect_error_records():
    """检测错误的极值记录（所有亏损记录都视为错误）"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 查找所有亏损记录（max_loss类型）
    cursor.execute('''
    SELECT id, inst_id, pos_side, record_type, profit_rate, timestamp,
           pos_size, avg_price, mark_price, margin
    FROM anchor_profit_records
    WHERE record_type = 'max_loss' AND profit_rate < 0
    ORDER BY profit_rate ASC
    ''')
    
    error_records = cursor.fetchall()
    conn.close()
    
    print(f"\n=== 检测到 {len(error_records)} 条错误极值记录 ===")
    for record in error_records:
        record_id, inst_id, pos_side, record_type, profit_rate, timestamp, pos_size, avg_price, mark_price, margin = record
        print(f"⚠️  [{record_id}] {inst_id} {pos_side} {record_type}: {profit_rate:+.2f}%")
        print(f"     时间: {timestamp}")
        print(f"     持仓: {pos_size} 张, 开仓价: ${avg_price:.4f}, 标记价: ${mark_price:.4f}")
    
    return error_records


def delete_error_records(records, reason="错误数据清理"):
    """删除错误的极值记录"""
    if not records:
        print("⚠️  没有需要删除的记录")
        return 0
    
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    deleted_count = 0
    for record in records:
        record_id, inst_id, pos_side, record_type, profit_rate = record[:5]
        
        # 记录到纠错日志
        cursor.execute(f'''
        INSERT INTO {CORRECTION_LOG_TABLE} (
            correction_type, inst_id, pos_side, record_type,
            old_profit_rate, new_profit_rate, reason
        ) VALUES (?, ?, ?, ?, ?, NULL, ?)
        ''', ('delete', inst_id, pos_side, record_type, profit_rate, reason))
        
        # 删除记录
        cursor.execute('''
        DELETE FROM anchor_profit_records
        WHERE id = ?
        ''', (record_id,))
        
        deleted_count += 1
        print(f"🗑️  已删除: {inst_id} {pos_side} {record_type} ({profit_rate:+.2f}%)")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 共删除 {deleted_count} 条错误记录")
    return deleted_count


def rollback_from_backup(backup_time=None):
    """从备份恢复数据"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 如果指定了时间，查询该时间点的备份
    if backup_time:
        cursor.execute(f'''
        SELECT COUNT(*) FROM {BACKUP_TABLE}
        WHERE backup_timestamp >= datetime(?)
        ''', (backup_time,))
    else:
        cursor.execute(f'''
        SELECT COUNT(*) FROM {BACKUP_TABLE}
        ''')
    
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("⚠️  没有找到备份数据")
        conn.close()
        return 0
    
    print(f"⚠️  准备从备份恢复 {count} 条记录")
    print("⚠️  这将清空当前所有极值记录并恢复备份数据")
    
    # 清空当前数据
    cursor.execute('DELETE FROM anchor_profit_records')
    
    # 恢复备份数据
    if backup_time:
        cursor.execute(f'''
        INSERT INTO anchor_profit_records (
            inst_id, pos_side, record_type, profit_rate, timestamp,
            pos_size, avg_price, mark_price, upl, margin, leverage,
            snapshot_data, created_at, updated_at
        )
        SELECT 
            inst_id, pos_side, record_type, profit_rate, timestamp,
            pos_size, avg_price, mark_price, upl, margin, leverage,
            snapshot_data, original_created_at, original_updated_at
        FROM {BACKUP_TABLE}
        WHERE backup_timestamp >= datetime(?)
        ''', (backup_time,))
    else:
        cursor.execute(f'''
        INSERT INTO anchor_profit_records (
            inst_id, pos_side, record_type, profit_rate, timestamp,
            pos_size, avg_price, mark_price, upl, margin, leverage,
            snapshot_data, created_at, updated_at
        )
        SELECT 
            inst_id, pos_side, record_type, profit_rate, timestamp,
            pos_size, avg_price, mark_price, upl, margin, leverage,
            snapshot_data, original_created_at, original_updated_at
        FROM {BACKUP_TABLE}
        ORDER BY backup_timestamp DESC
        LIMIT {count}
        ''')
    
    restored = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ 已从备份恢复 {restored} 条记录")
    return restored


def view_correction_log(limit=20):
    """查看纠错日志"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute(f'''
    SELECT id, correction_type, inst_id, pos_side, record_type,
           old_profit_rate, new_profit_rate, reason, created_at
    FROM {CORRECTION_LOG_TABLE}
    ORDER BY created_at DESC
    LIMIT ?
    ''', (limit,))
    
    logs = cursor.fetchall()
    conn.close()
    
    print(f"\n=== 最近 {len(logs)} 条纠错日志 ===")
    for log in logs:
        log_id, correction_type, inst_id, pos_side, record_type, old_rate, new_rate, reason, created_at = log
        print(f"[{log_id}] {created_at}")
        print(f"  类型: {correction_type}")
        print(f"  标的: {inst_id} {pos_side} {record_type}")
        print(f"  变更: {old_rate:+.2f}% → {new_rate if new_rate else 'DELETED'}")
        print(f"  原因: {reason}")
        print()


def get_statistics():
    """获取当前极值统计"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 统计总数
    cursor.execute('SELECT COUNT(*) FROM anchor_profit_records')
    total = cursor.fetchone()[0]
    
    # 统计盈利记录
    cursor.execute('''
    SELECT COUNT(*), AVG(profit_rate), MAX(profit_rate)
    FROM anchor_profit_records
    WHERE record_type = 'max_profit'
    ''')
    profit_stats = cursor.fetchone()
    
    # 统计亏损记录
    cursor.execute('''
    SELECT COUNT(*), AVG(profit_rate), MIN(profit_rate)
    FROM anchor_profit_records
    WHERE record_type = 'max_loss'
    ''')
    loss_stats = cursor.fetchone()
    
    conn.close()
    
    print("\n=== 极值数据统计 ===")
    print(f"总记录数: {total}")
    print(f"盈利记录 (max_profit): {profit_stats[0]} 条")
    if profit_stats[0] > 0:
        print(f"  平均盈利: {profit_stats[1]:+.2f}%")
        print(f"  最高盈利: {profit_stats[2]:+.2f}%")
    print(f"亏损记录 (max_loss): {loss_stats[0]} 条")
    if loss_stats[0] > 0:
        print(f"  平均亏损: {loss_stats[1]:+.2f}%")
        print(f"  最大亏损: {loss_stats[2]:+.2f}%")
    
    return {
        'total': total,
        'profit_count': profit_stats[0],
        'loss_count': loss_stats[0]
    }


def auto_clean_mode():
    """自动清理模式：删除所有亏损记录"""
    print("\n" + "=" * 60)
    print("🔧 启动自动清理模式")
    print("=" * 60)
    
    # 0. 确保主表存在
    from anchor_system import init_database
    init_database()
    
    # 1. 初始化纠错系统
    init_correction_system()
    
    # 2. 备份当前数据
    print("\n[1/4] 备份当前数据...")
    backup_current_data()
    
    # 3. 检测错误记录
    print("\n[2/4] 检测错误记录...")
    error_records = detect_error_records()
    
    if not error_records:
        print("\n✅ 没有发现错误记录，数据正常！")
        return
    
    # 4. 删除错误记录
    print("\n[3/4] 删除错误记录...")
    deleted = delete_error_records(error_records, "自动清理：删除所有亏损极值记录")
    
    # 5. 显示清理后统计
    print("\n[4/4] 清理后统计...")
    get_statistics()
    
    print("\n" + "=" * 60)
    print("✅ 自动清理完成！")
    print("=" * 60)


def interactive_mode():
    """交互模式：提供多种操作选项"""
    print("\n" + "=" * 60)
    print("🛠️  极值数据纠错系统 - 交互模式")
    print("=" * 60)
    
    while True:
        print("\n请选择操作：")
        print("1. 查看当前统计")
        print("2. 检测错误记录")
        print("3. 备份当前数据")
        print("4. 删除所有亏损记录")
        print("5. 从备份恢复")
        print("6. 查看纠错日志")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-6): ").strip()
        
        if choice == '0':
            print("👋 退出系统")
            break
        elif choice == '1':
            get_statistics()
        elif choice == '2':
            detect_error_records()
        elif choice == '3':
            backup_current_data()
        elif choice == '4':
            init_correction_system()
            error_records = detect_error_records()
            if error_records:
                confirm = input(f"\n⚠️  确认删除 {len(error_records)} 条记录？(yes/no): ").strip().lower()
                if confirm == 'yes':
                    delete_error_records(error_records)
                else:
                    print("❌ 取消操作")
        elif choice == '5':
            init_correction_system()
            rollback_from_backup()
        elif choice == '6':
            init_correction_system()
            view_correction_log()
        else:
            print("❌ 无效选项")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'auto':
        # 自动清理模式
        auto_clean_mode()
    else:
        # 交互模式
        interactive_mode()
