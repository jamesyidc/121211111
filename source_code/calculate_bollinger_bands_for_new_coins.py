#!/usr/bin/env python3
"""
为12个新币种计算布林带指标
解决用户报告的"布林带数据都没有"的问题
"""

import sqlite3
import pandas as pd
from datetime import datetime

# 12个新添加的币种
NEW_SYMBOLS = [
    'HBAR-USDT-SWAP', 'FIL-USDT-SWAP', 'CRO-USDT-SWAP', 
    'AAVE-USDT-SWAP', 'UNI-USDT-SWAP', 'NEAR-USDT-SWAP',
    'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

def calculate_bollinger_bands(close_prices, period=20, std_dev=2):
    """
    计算布林带
    
    Args:
        close_prices: 收盘价列表
        period: 周期（默认20）
        std_dev: 标准差倍数（默认2）
    
    Returns:
        (bb_upper, bb_middle, bb_lower) 或 (None, None, None)
    """
    if len(close_prices) < period:
        return None, None, None
    
    # 使用pandas计算移动平均和标准差
    df = pd.DataFrame({'close': close_prices})
    df['bb_middle'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
    df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
    
    # 返回最后一个值
    return (
        df['bb_upper'].iloc[-1],
        df['bb_middle'].iloc[-1],
        df['bb_lower'].iloc[-1]
    )

def process_symbol(conn, symbol, timeframe='5m'):
    """处理单个币种的布林带计算"""
    cursor = conn.cursor()
    
    print(f"\n处理 {symbol} ({timeframe})...")
    
    # 获取所有OHLC数据，按时间升序
    cursor.execute("""
        SELECT timestamp, close
        FROM okex_kline_ohlc
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    """, (symbol, timeframe))
    
    ohlc_rows = cursor.fetchall()
    
    if not ohlc_rows:
        print(f"  ❌ 没有OHLC数据")
        return 0
    
    print(f"  📊 找到 {len(ohlc_rows)} 条OHLC数据")
    
    # 构建时间戳到收盘价的映射
    ts_to_close = {row[0]: row[1] for row in ohlc_rows}
    
    # 获取需要更新的技术指标记录
    cursor.execute("""
        SELECT id, timestamp
        FROM kline_technical_markers
        WHERE symbol = ? AND timeframe = ? AND bb_upper IS NULL
        ORDER BY timestamp ASC
    """, (symbol, timeframe))
    
    marker_rows = cursor.fetchall()
    
    if not marker_rows:
        print(f"  ✅ 所有记录已有布林带数据")
        return 0
    
    print(f"  🔄 需要更新 {len(marker_rows)} 条记录")
    
    updated_count = 0
    
    for marker_id, timestamp in marker_rows:
        # 获取该时间点之前的20个收盘价（包括当前时间点）
        # 找到所有小于等于当前时间戳的OHLC数据
        historical_closes = []
        for ts in sorted(ts_to_close.keys()):
            if ts <= timestamp:
                historical_closes.append(ts_to_close[ts])
        
        if len(historical_closes) >= 20:
            # 计算布林带（使用最后20个数据点）
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
                historical_closes[-40:],  # 使用最后40个点以确保计算准确
                period=20,
                std_dev=2
            )
            
            if bb_upper is not None:
                # 更新数据库
                cursor.execute("""
                    UPDATE kline_technical_markers
                    SET bb_upper = ?, bb_middle = ?, bb_lower = ?, updated_at = ?
                    WHERE id = ?
                """, (bb_upper, bb_middle, bb_lower, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), marker_id))
                
                updated_count += 1
                
                if updated_count % 100 == 0:
                    conn.commit()
                    print(f"    已更新 {updated_count} 条...")
    
    conn.commit()
    print(f"  ✅ 完成，共更新 {updated_count} 条记录")
    
    return updated_count

def main():
    print("="*80)
    print("为12个新币种计算布林带指标")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn = sqlite3.connect('crypto_data.db')
    
    total_updated = 0
    
    for symbol in NEW_SYMBOLS:
        try:
            # 5分钟周期
            count_5m = process_symbol(conn, symbol, '5m')
            total_updated += count_5m
            
            # 1小时周期
            count_1h = process_symbol(conn, symbol, '1H')
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
