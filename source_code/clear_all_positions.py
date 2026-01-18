#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空所有持仓
⚠️ 警告：此操作将删除数据库中所有持仓记录，无法恢复！
"""

import sqlite3
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/trading_decision.db'

def backup_positions():
    """备份现有持仓到历史表"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 创建历史表（如果不存在）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS position_opens_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER,
            inst_id TEXT,
            pos_side TEXT,
            open_price REAL,
            open_size REAL,
            open_percent REAL,
            granularity REAL,
            total_positions INTEGER,
            is_anchor INTEGER,
            timestamp TEXT,
            created_at TEXT,
            lever INTEGER,
            margin REAL,
            mark_price REAL,
            profit_rate REAL,
            upl REAL,
            updated_time TEXT,
            closed_at TEXT,
            closed_reason TEXT
        )
    """)
    
    # 备份所有持仓
    cursor.execute("""
        INSERT INTO position_opens_history 
        SELECT 
            NULL as id,
            id as original_id,
            inst_id, pos_side, open_price, open_size, open_percent,
            granularity, total_positions, is_anchor, timestamp, created_at,
            lever, margin, mark_price, profit_rate, upl, updated_time,
            ? as closed_at,
            '手动清空' as closed_reason
        FROM position_opens
    """, (datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),))
    
    backup_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return backup_count

def clear_all_positions():
    """清空所有持仓"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 获取持仓数量
    cursor.execute("SELECT COUNT(*) FROM position_opens")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("✅ 数据库中没有持仓记录")
        conn.close()
        return 0
    
    # 删除所有持仓
    cursor.execute("DELETE FROM position_opens")
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    return deleted_count

def main():
    print("="*80)
    print("⚠️  清空所有持仓")
    print("="*80)
    print()
    
    # 查看当前持仓
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT inst_id, pos_side, open_size, margin, profit_rate, is_anchor
        FROM position_opens
        ORDER BY margin DESC
    """)
    
    positions = cursor.fetchall()
    total_margin = sum(p[3] for p in positions)
    
    print(f"📊 当前持仓: {len(positions)} 个")
    print(f"💰 总保证金: {total_margin:.4f} USDT")
    print()
    
    if len(positions) > 0:
        print("持仓明细:")
        print(f"{'币种':<20} {'方向':<8} {'张数':<12} {'保证金':<12} {'盈亏':<10} {'类型'}")
        print("-"*80)
        for inst_id, pos_side, size, margin, profit, is_anchor in positions:
            pos_type = "锚点单" if is_anchor == 1 else "普通单"
            print(f"{inst_id:<20} {pos_side:<8} {size:<12.4f} {margin:<12.4f} {profit:+7.2f}%  {pos_type}")
        print()
    
    conn.close()
    
    if len(positions) == 0:
        print("✅ 数据库中没有持仓，无需清空")
        return
    
    # 确认操作
    print("="*80)
    print("⚠️  警告：即将执行以下操作")
    print("="*80)
    print()
    print("1. 备份所有持仓到 position_opens_history 表")
    print("2. 删除 position_opens 表中的所有记录")
    print()
    print("⚠️  注意：")
    print("   • 这个操作只清空数据库记录")
    print("   • 不会在OKEx交易所实际平仓")
    print("   • 如需在OKEx平仓，请手动操作或使用API")
    print()
    
    # 需要用户确认
    response = input("确认要清空所有持仓吗？(输入 'YES' 确认): ")
    
    if response != 'YES':
        print()
        print("❌ 操作已取消")
        return
    
    print()
    print("="*80)
    print("🔄 执行清空操作")
    print("="*80)
    print()
    
    # 步骤1: 备份
    print("步骤1: 备份持仓...")
    backup_count = backup_positions()
    print(f"✅ 已备份 {backup_count} 条记录到 position_opens_history 表")
    print()
    
    # 步骤2: 清空
    print("步骤2: 清空持仓...")
    deleted_count = clear_all_positions()
    print(f"✅ 已删除 {deleted_count} 条持仓记录")
    print()
    
    # 验证
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM position_opens")
    remaining = cursor.fetchone()[0]
    conn.close()
    
    print("="*80)
    print("📊 清空结果")
    print("="*80)
    print()
    print(f"原有持仓: {len(positions)} 个")
    print(f"已备份: {backup_count} 条")
    print(f"已删除: {deleted_count} 条")
    print(f"剩余持仓: {remaining} 个")
    print()
    
    if remaining == 0:
        print("🎉 所有持仓已成功清空！")
        print()
        print("💡 提示:")
        print("   • 数据库持仓已清空")
        print("   • 备份保存在 position_opens_history 表")
        print("   • 可以开始创建新的锚点单了")
    else:
        print("⚠️  警告: 还有持仓未清空")

if __name__ == "__main__":
    main()
