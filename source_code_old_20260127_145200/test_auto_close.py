#!/usr/bin/env python3
"""测试自动平仓功能"""

import sqlite3
from auto_close_positions import AutoClosePositions

def test_check_positions():
    """测试检查待平仓持仓（模拟allow_short=false）"""
    print("=" * 60)
    print("测试自动平仓检查")
    print("=" * 60)
    
    # 临时修改配置为不允许开空单
    conn = sqlite3.connect('trading_decision.db')
    cursor = conn.cursor()
    
    # 保存当前配置
    cursor.execute('SELECT allow_short FROM market_config ORDER BY updated_at DESC LIMIT 1')
    original_allow_short = cursor.fetchone()[0]
    
    # 临时设置为不允许开空单
    cursor.execute('''
        UPDATE market_config 
        SET allow_short = 0
        WHERE id = (SELECT id FROM market_config ORDER BY updated_at DESC LIMIT 1)
    ''')
    conn.commit()
    
    print("\n📋 临时配置: allow_short=false (模拟测试)\n")
    
    # 检查需要平仓的持仓
    closer = AutoClosePositions()
    to_close = closer.check_positions_to_close(dry_run=True)
    
    print(f"需要平仓的持仓数: {len(to_close)}\n")
    
    if len(to_close) > 0:
        print("详细列表:")
        print("-" * 80)
        print(f"{'币种':<20} {'方向':<8} {'锚点单':<8} {'总仓位':<12} {'平仓':<12} {'保留':<12}")
        print("-" * 80)
        
        total_close = 0
        for pos in to_close:
            anchor_str = "是" if pos['is_anchor'] else "否"
            print(f"{pos['inst_id']:<20} {pos['pos_side']:<8} {anchor_str:<8} "
                  f"{pos['total_size']:<12.4f} {pos['close_size']:<12.4f} {pos['keep_size']:<12.4f}")
            print(f"  原因: {pos['close_reason']}")
            total_close += pos['close_size']
        
        print("-" * 80)
        print(f"总计需要平仓: {total_close:.4f} USDT")
    else:
        print("✅ 无需平仓")
    
    # 恢复原始配置
    cursor.execute('''
        UPDATE market_config 
        SET allow_short = ?
        WHERE id = (SELECT id FROM market_config ORDER BY updated_at DESC LIMIT 1)
    ''', (original_allow_short,))
    conn.commit()
    conn.close()
    
    print("\n✅ 配置已恢复")
    print("=" * 60)

if __name__ == '__main__':
    test_check_positions()
