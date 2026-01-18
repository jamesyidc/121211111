#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单自动调整到1U
将所有不符合1U标准的锚点单调整到接近1U保证金
"""

import sqlite3
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/trading_decision.db'

def get_all_anchors():
    """获取所有锚点单"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT inst_id, pos_side, open_size, margin, mark_price, lever, profit_rate
        FROM position_opens
        WHERE is_anchor = 1
    """)
    
    anchors = []
    for row in cursor.fetchall():
        anchors.append({
            'inst_id': row[0],
            'pos_side': row[1],
            'current_size': row[2],
            'current_margin': row[3],
            'mark_price': row[4],
            'lever': row[5],
            'profit_rate': row[6]
        })
    
    conn.close()
    return anchors

def calculate_adjustment(anchor):
    """
    计算需要如何调整
    
    目标：保证金接近1U
    方法：根据当前保证金和目标保证金，计算需要调整的仓位
    """
    target_margin = 1.0  # 目标1U
    current_margin = anchor['current_margin']
    current_size = anchor['current_size']
    mark_price = anchor['mark_price']
    lever = anchor['lever']
    
    # 计算目标仓位
    # 保证金 = (张数 * 价格) / 杠杆
    # 张数 = (保证金 * 杠杆) / 价格
    target_size = (target_margin * lever) / mark_price
    
    # 计算需要调整的数量
    adjust_size = target_size - current_size
    
    # 判断操作类型
    if abs(current_margin - target_margin) < 0.05:  # 误差在0.05U以内
        action = 'skip'
        reason = f'保证金已接近1U ({current_margin:.4f}U)'
    elif current_margin > target_margin:
        action = 'close'  # 平掉一部分
        reason = f'保证金{current_margin:.4f}U > 1U，需要平仓'
    elif current_margin < target_margin:
        action = 'add'  # 加仓
        reason = f'保证金{current_margin:.4f}U < 1U，需要加仓'
    else:
        action = 'skip'
        reason = '保证金正常'
    
    return {
        'action': action,
        'current_size': current_size,
        'current_margin': current_margin,
        'target_size': target_size,
        'target_margin': target_margin,
        'adjust_size': adjust_size,
        'adjust_percent': (adjust_size / current_size * 100) if current_size > 0 else 0,
        'reason': reason
    }

def main():
    print("="*80)
    print("🔧 锚点单自动调整到1U")
    print("="*80)
    print()
    
    # 获取所有锚点单
    anchors = get_all_anchors()
    print(f"📊 找到 {len(anchors)} 个锚点单")
    print()
    
    # 分析每个锚点单
    adjustments = []
    
    for anchor in anchors:
        plan = calculate_adjustment(anchor)
        
        if plan['action'] != 'skip':
            adjustments.append({
                'inst_id': anchor['inst_id'],
                'pos_side': anchor['pos_side'],
                'current_margin': plan['current_margin'],
                'target_margin': plan['target_margin'],
                'current_size': plan['current_size'],
                'target_size': plan['target_size'],
                'adjust_size': plan['adjust_size'],
                'action': plan['action'],
                'reason': plan['reason']
            })
    
    print("="*80)
    print(f"📋 需要调整的锚点单: {len(adjustments)} 个")
    print("="*80)
    print()
    
    if len(adjustments) == 0:
        print("✅ 所有锚点单保证金都已接近1U，无需调整")
        return
    
    # 显示调整计划
    print(f"{'币种':<20} {'当前':<12} {'目标':<12} {'操作':<10} {'调整量'}")
    print("-"*80)
    
    for adj in adjustments:
        action_text = {
            'close': '🔴 平仓',
            'add': '🟢 加仓',
            'skip': '⚪ 跳过'
        }.get(adj['action'], adj['action'])
        
        adjust_text = f"{adj['adjust_size']:+.4f} 张 ({adj['adjust_size']/adj['current_size']*100:+.1f}%)"
        
        print(f"{adj['inst_id']:<20} "
              f"{adj['current_margin']:.4f}U    "
              f"1.0000U    "
              f"{action_text:<10} "
              f"{adjust_text}")
    
    print()
    print("="*80)
    print("⚠️  注意事项")
    print("="*80)
    print()
    print("1. 本脚本目前只显示调整计划，不执行实际交易")
    print("2. 实际执行需要对接OKEx API进行平仓/加仓操作")
    print("3. 建议在模拟盘测试通过后再用于实盘")
    print()
    
    # 保存调整计划到数据库
    save_adjustment_plan(adjustments)

def save_adjustment_plan(adjustments):
    """保存调整计划到数据库"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 创建调整计划表（如果不存在）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anchor_adjustment_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inst_id TEXT,
            pos_side TEXT,
            current_margin REAL,
            target_margin REAL,
            current_size REAL,
            target_size REAL,
            adjust_size REAL,
            action TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    for adj in adjustments:
        cursor.execute("""
            INSERT INTO anchor_adjustment_plans 
            (inst_id, pos_side, current_margin, target_margin, 
             current_size, target_size, adjust_size, action, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            adj['inst_id'],
            adj['pos_side'],
            adj['current_margin'],
            adj['target_margin'],
            adj['current_size'],
            adj['target_size'],
            adj['adjust_size'],
            adj['action'],
            adj['reason'],
            timestamp
        ))
    
    conn.commit()
    conn.close()
    
    print(f"💾 调整计划已保存到数据库 (anchor_adjustment_plans 表)")
    print()

if __name__ == "__main__":
    main()
