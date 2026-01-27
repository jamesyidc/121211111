#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复比价系统数据完整性问题

问题分析:
1. TRX的最高价格被错误更新为0.28346，而初始基准是0.36644
2. 导致当前价格0.27977相对于错误的0.28346显示为"接近最高价"
3. 实际上当前价格只是真实最高价0.36644的77.3%

解决方案:
1. 恢复所有币种的正确基准价格
2. 删除错误的突破事件记录
3. 验证数据完整性
"""

import sqlite3
from datetime import datetime

# 正确的基准数据（来自import_baseline_data.py）
BASELINE_DATA = [
    {'symbol': 'OKB', 'highest_price': 235.51972, 'highest_count': 2839, 'lowest_price': 93.75352, 'lowest_count': 737},
    {'symbol': 'DOT', 'highest_price': 4.883676056338, 'highest_count': 4319, 'lowest_price': 1.97723, 'lowest_count': 265},
    {'symbol': 'LINK', 'highest_price': 26.37, 'highest_count': 7530, 'lowest_price': 11.69141, 'lowest_count': 737},
    {'symbol': 'ADA', 'highest_price': 0.953985915493, 'highest_count': 5100, 'lowest_price': 0.37093, 'lowest_count': 260},
    {'symbol': 'FIL', 'highest_price': 2.656661971831, 'highest_count': 5101, 'lowest_price': 1.42787, 'lowest_count': 285},
    {'symbol': 'XLM', 'highest_price': 0.41770, 'highest_count': 7530, 'lowest_price': 0.21873, 'lowest_count': 737},
    {'symbol': 'HBAR', 'highest_price': 0.2552676056338, 'highest_count': 5100, 'lowest_price': 0.12379, 'lowest_count': 737},
    {'symbol': 'BCH', 'highest_price': 650.823943662, 'highest_count': 4390, 'lowest_price': 450.20845, 'lowest_count': 737},
    {'symbol': 'ETC', 'highest_price': 24.32, 'highest_count': 7529, 'lowest_price': 12.67108, 'lowest_count': 245},
    {'symbol': 'TON', 'highest_price': 3.392, 'highest_count': 7529, 'lowest_price': 1.44342, 'lowest_count': 268},
    {'symbol': 'TRX', 'highest_price': 0.36644, 'highest_count': 7529, 'lowest_price': 0.27335, 'lowest_count': 562},
    {'symbol': 'SUI', 'highest_price': 3.981056338028, 'highest_count': 4356, 'lowest_price': 1.3108, 'lowest_count': 257},
    {'symbol': 'DOGE', 'highest_price': 0.3071549295775, 'highest_count': 5100, 'lowest_price': 0.13187, 'lowest_count': 260},
    {'symbol': 'SOL', 'highest_price': 253.3591549296, 'highest_count': 4367, 'lowest_price': 122.8831, 'lowest_count': 738},
    {'symbol': 'LTC', 'highest_price': 135.56901, 'highest_count': 2396, 'lowest_price': 74.85493, 'lowest_count': 263},
    {'symbol': 'BNB', 'highest_price': 1377.4831, 'highest_count': 2297, 'lowest_price': 796.78451, 'lowest_count': 738},
    {'symbol': 'XRP', 'highest_price': 3.190211267606, 'highest_count': 5121, 'lowest_price': 1.83979, 'lowest_count': 738},
    {'symbol': 'ETH', 'highest_price': 4830, 'highest_count': 7531, 'lowest_price': 2642, 'lowest_count': 738},
    {'symbol': 'BTC', 'highest_price': 125370.20986, 'highest_count': 2833, 'lowest_price': 81359.05775, 'lowest_count': 738},
    {'symbol': 'CRO', 'highest_price': 0.3857746478873, 'highest_count': 7331, 'lowest_price': 0.09308, 'lowest_count': 737},
    {'symbol': 'CFX', 'highest_price': 0.1878309859155, 'highest_count': 4356, 'lowest_price': 0.06834, 'lowest_count': 254},
    {'symbol': 'CRV', 'highest_price': 0.8628732394366, 'highest_count': 4960, 'lowest_price': 0.36473, 'lowest_count': 600},
    {'symbol': 'APT', 'highest_price': 5.49327, 'highest_count': 2832, 'lowest_price': 1.81623, 'lowest_count': 250},
    {'symbol': 'NEAR', 'highest_price': 3.324084507042, 'highest_count': 4101, 'lowest_price': 1.59283, 'lowest_count': 268},
    {'symbol': 'UNI', 'highest_price': 10.3711971831, 'highest_count': 5101, 'lowest_price': 5.37062, 'lowest_count': 168},
    {'symbol': 'AAVE', 'highest_price': 322.6535211268, 'highest_count': 5181, 'lowest_price': 150.39577, 'lowest_count': 737},
    {'symbol': 'STX', 'highest_price': 0.7021126760563, 'highest_count': 4960, 'lowest_price': 0.27828, 'lowest_count': 245},
    {'symbol': 'TAO', 'highest_price': 476.82394, 'highest_count': 2109, 'lowest_price': 255.50563, 'lowest_count': 254},
    {'symbol': 'LDO', 'highest_price': 1.354929577465, 'highest_count': 4178, 'lowest_price': 0.55338, 'lowest_count': 198}
]

def check_data_integrity(conn):
    """检查数据完整性"""
    cursor = conn.cursor()
    issues = []
    
    print("=" * 60)
    print("检查数据完整性...")
    print("=" * 60)
    
    for baseline in BASELINE_DATA:
        symbol = baseline['symbol']
        expected_highest = baseline['highest_price']
        expected_lowest = baseline['lowest_price']
        
        cursor.execute("""
            SELECT highest_price, lowest_price, highest_count, lowest_count
            FROM price_comparison
            WHERE coin_name = ?
        """, (symbol,))
        
        row = cursor.fetchone()
        if not row:
            issues.append(f"{symbol}: 数据不存在")
            continue
        
        current_highest, current_lowest, high_count, low_count = row
        
        # 检查最高价是否被错误降低（允许5%误差）
        if current_highest < expected_highest * 0.95:
            diff_percent = ((expected_highest - current_highest) / expected_highest) * 100
            issues.append({
                'symbol': symbol,
                'type': 'highest_price',
                'expected': expected_highest,
                'current': current_highest,
                'diff_percent': diff_percent
            })
            print(f"❌ {symbol}: 最高价异常")
            print(f"   期望: ${expected_highest:.8f}")
            print(f"   当前: ${current_highest:.8f}")
            print(f"   差距: {diff_percent:.2f}%\n")
        
        # 检查最低价是否被错误提高
        if current_lowest > expected_lowest * 1.05:
            diff_percent = ((current_lowest - expected_lowest) / expected_lowest) * 100
            issues.append({
                'symbol': symbol,
                'type': 'lowest_price',
                'expected': expected_lowest,
                'current': current_lowest,
                'diff_percent': diff_percent
            })
            print(f"❌ {symbol}: 最低价异常")
            print(f"   期望: ${expected_lowest:.8f}")
            print(f"   当前: ${current_lowest:.8f}")
            print(f"   差距: {diff_percent:.2f}%\n")
    
    if not issues:
        print("✅ 所有币种数据正常!\n")
    else:
        print(f"⚠️  发现 {len(issues)} 个数据异常\n")
    
    return issues

def fix_data(conn, issues):
    """修复数据"""
    if not issues:
        print("✅ 无需修复\n")
        return 0
    
    cursor = conn.cursor()
    fixed_count = 0
    
    print("=" * 60)
    print("开始修复数据...")
    print("=" * 60)
    
    for issue in issues:
        if isinstance(issue, dict):
            symbol = issue['symbol']
            
            # 查找对应的基准数据
            baseline = next((b for b in BASELINE_DATA if b['symbol'] == symbol), None)
            if not baseline:
                continue
            
            print(f"🔧 修复 {symbol}...")
            
            # 恢复正确的基准价格和计次
            cursor.execute("""
                UPDATE price_comparison
                SET highest_price = ?,
                    highest_count = ?,
                    lowest_price = ?,
                    lowest_count = ?
                WHERE coin_name = ?
            """, (baseline['highest_price'], baseline['highest_count'],
                  baseline['lowest_price'], baseline['lowest_count'], symbol))
            
            # 删除错误的突破事件（价格低于基准最高价的"创新高"事件）
            cursor.execute("""
                DELETE FROM price_breakthrough_events
                WHERE coin_name = ? 
                  AND event_type = 'new_high' 
                  AND price < ?
            """, (symbol, baseline['highest_price']))
            
            deleted_high = cursor.rowcount
            
            # 删除错误的突破事件（价格高于基准最低价的"创新低"事件）
            cursor.execute("""
                DELETE FROM price_breakthrough_events
                WHERE coin_name = ? 
                  AND event_type = 'new_low' 
                  AND price > ?
            """, (symbol, baseline['lowest_price']))
            
            deleted_low = cursor.rowcount
            
            print(f"   ✅ 恢复基准价格")
            print(f"   ✅ 删除 {deleted_high} 条错误创新高事件")
            print(f"   ✅ 删除 {deleted_low} 条错误创新低事件\n")
            
            fixed_count += 1
    
    conn.commit()
    print(f"✅ 修复完成! 共修复 {fixed_count} 个币种\n")
    return fixed_count

def verify_fix(conn):
    """验证修复结果"""
    print("=" * 60)
    print("验证修复结果...")
    print("=" * 60)
    
    cursor = conn.cursor()
    
    # 验证几个关键币种
    test_coins = ['TRX', 'BTC', 'ETH', 'XRP']
    
    for symbol in test_coins:
        baseline = next((b for b in BASELINE_DATA if b['symbol'] == symbol), None)
        if not baseline:
            continue
        
        cursor.execute("""
            SELECT coin_name, highest_price, highest_count, lowest_price, lowest_count
            FROM price_comparison
            WHERE coin_name = ?
        """, (symbol,))
        
        row = cursor.fetchone()
        if row:
            print(f"\n{row[0]}:")
            print(f"  最高价: ${row[1]:.8f} (基准: ${baseline['highest_price']:.8f})")
            print(f"  最高计次: {row[2]} (基准: {baseline['highest_count']})")
            print(f"  最低价: ${row[3]:.8f} (基准: ${baseline['lowest_price']:.8f})")
            print(f"  最低计次: {row[4]} (基准: {baseline['lowest_count']})")
            
            # 验证是否匹配
            if abs(row[1] - baseline['highest_price']) < 0.0001:
                print(f"  ✅ 最高价匹配")
            else:
                print(f"  ❌ 最高价不匹配")
    
    # 统计突破事件
    cursor.execute("""
        SELECT event_type, COUNT(*) 
        FROM price_breakthrough_events
        GROUP BY event_type
    """)
    
    print("\n突破事件统计:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 次")
    
    print()

def main():
    print("\n" + "=" * 60)
    print("比价系统数据完整性修复工具")
    print("=" * 60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    conn = sqlite3.connect('crypto_data.db')
    
    try:
        # 1. 检查数据完整性
        issues = check_data_integrity(conn)
        
        # 2. 修复数据
        fixed_count = fix_data(conn, issues)
        
        # 3. 验证修复结果
        verify_fix(conn)
        
        print("=" * 60)
        print("修复完成!")
        print("=" * 60)
        print(f"问题数量: {len(issues)}")
        print(f"修复数量: {fixed_count}")
        print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()
