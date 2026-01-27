#!/usr/bin/env python3
"""
修复12个新币种的sar_quadrant格式问题
将'Q1', 'Q2', 'Q3', 'Q4'转换为整数1, 2, 3, 4
"""

import sqlite3
from datetime import datetime

# 12个新添加的币种
NEW_SYMBOLS = [
    'HBAR-USDT-SWAP', 'FIL-USDT-SWAP', 'CRO-USDT-SWAP', 
    'AAVE-USDT-SWAP', 'UNI-USDT-SWAP', 'NEAR-USDT-SWAP',
    'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

def fix_symbol(conn, symbol, timeframe='5m'):
    """修复单个币种的sar_quadrant格式"""
    cursor = conn.cursor()
    
    print(f"\n处理 {symbol} ({timeframe})...")
    
    # 查询所有需要修复的记录
    cursor.execute("""
        SELECT id, sar_quadrant
        FROM kline_technical_markers
        WHERE symbol = ? AND timeframe = ? 
          AND typeof(sar_quadrant) = 'text'
          AND sar_quadrant IS NOT NULL
    """, (symbol, timeframe))
    
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  ✅ 没有需要修复的记录")
        return 0
    
    print(f"  🔄 需要修复 {len(rows)} 条记录")
    
    updated_count = 0
    
    for record_id, sar_quadrant in rows:
        # 提取数字部分: 'Q1' -> 1, 'Q2' -> 2, etc.
        if sar_quadrant and sar_quadrant.startswith('Q'):
            try:
                quadrant_num = int(sar_quadrant[1:])
                
                cursor.execute("""
                    UPDATE kline_technical_markers
                    SET sar_quadrant = ?, updated_at = ?
                    WHERE id = ?
                """, (quadrant_num, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), record_id))
                
                updated_count += 1
                
                if updated_count % 100 == 0:
                    conn.commit()
                    print(f"    已更新 {updated_count} 条...")
            except ValueError:
                print(f"    ⚠️  无法转换: {sar_quadrant}")
    
    conn.commit()
    print(f"  ✅ 完成，共更新 {updated_count} 条记录")
    
    return updated_count

def main():
    print("="*80)
    print("修复12个新币种的sar_quadrant格式")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn = sqlite3.connect('crypto_data.db')
    
    total_updated = 0
    
    for symbol in NEW_SYMBOLS:
        try:
            # 5分钟周期
            count_5m = fix_symbol(conn, symbol, '5m')
            total_updated += count_5m
            
            # 1小时周期
            count_1h = fix_symbol(conn, symbol, '1H')
            total_updated += count_1h
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    conn.close()
    
    print("\n" + "="*80)
    print(f"✅ 完成！共更新 {total_updated} 条记录")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == '__main__':
    main()
