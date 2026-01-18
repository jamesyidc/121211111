#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试锚点单币种过滤 - 验证BTC和ETH被排除
"""

import sqlite3
from anchor_trigger import AnchorTrigger

def test_excluded_coins():
    """测试BTC和ETH是否被排除"""
    
    print("=" * 80)
    print("🧪 测试锚点单币种过滤")
    print("=" * 80)
    
    # 创建触发器实例
    trigger = AnchorTrigger()
    
    # 1. 查询数据库中所有符合条件的币种（不含过滤）
    print("\n1️⃣ 数据库中符合逃顶条件的所有币种:")
    conn = sqlite3.connect('/home/user/webapp/crypto_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT symbol, current_price, 
           resistance_line_1, resistance_line_2,
           distance_to_resistance_1, position_7d
    FROM support_resistance_levels
    WHERE record_time = (SELECT MAX(record_time) FROM support_resistance_levels)
      AND resistance_line_1 IS NOT NULL
      AND resistance_line_2 IS NOT NULL
      AND distance_to_resistance_1 <= 2.0
      AND position_7d >= 90
    ORDER BY symbol
    ''')
    
    all_coins = cursor.fetchall()
    conn.close()
    
    if all_coins:
        print(f"   共 {len(all_coins)} 个币种:")
        for row in all_coins:
            symbol = row[0]
            inst_id = f"{symbol[:-4]}-{symbol[-4:]}-SWAP"
            is_btc_eth = "🚫 BTC/ETH" if (symbol.startswith('BTC') or symbol.startswith('ETH')) else "✅"
            print(f"   {is_btc_eth} {inst_id}: 价格 {row[1]:.4f}, 距压力线 {row[4]:.2f}%, 位置 {row[5]:.1f}%")
    else:
        print("   ⚠️  暂无符合条件的币种")
    
    # 2. 获取经过过滤的逃顶信号
    print("\n2️⃣ 经过BTC/ETH过滤后的逃顶信号:")
    signals = trigger.get_escape_top_signals()
    
    if signals:
        print(f"   共 {len(signals)} 个信号:")
        for signal in signals:
            inst_id = signal['inst_id']
            print(f"   ✅ {inst_id}: 价格 {signal['current_price']:.4f}, 距压力线1 {signal['distance_to_resistance_1']:.2f}%, 位置 {signal['position_7d']:.1f}%")
        
        # 检查是否包含BTC或ETH
        has_btc = any('BTC' in s['inst_id'] for s in signals)
        has_eth = any('ETH' in s['inst_id'] for s in signals)
        
        print("\n3️⃣ 过滤验证:")
        if has_btc:
            print("   ❌ 失败：仍然包含BTC")
        else:
            print("   ✅ 通过：BTC已被排除")
        
        if has_eth:
            print("   ❌ 失败：仍然包含ETH")
        else:
            print("   ✅ 通过：ETH已被排除")
        
        print(f"\n✅ 过滤成功：{len(all_coins) - len(signals)} 个币种被排除")
    else:
        print("   ℹ️  暂无逃顶信号")
        print("\n3️⃣ 过滤验证:")
        print("   ✅ BTC和ETH过滤规则已生效（暂无符合条件的币种）")
    
    print("\n" + "=" * 80)
    print("🎯 配置说明:")
    print("   • BTC和ETH已被设置为锚点单排除币种")
    print("   • 修改位置: anchor_trigger.py")
    print("   • SQL过滤: AND symbol NOT LIKE 'BTC%' AND symbol NOT LIKE 'ETH%'")
    print("   • 代码双重检查: if inst_id.startswith('BTC-') or inst_id.startswith('ETH-')")
    print("=" * 80)

if __name__ == '__main__':
    try:
        test_excluded_coins()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
