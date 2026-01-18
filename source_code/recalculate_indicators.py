#!/usr/bin/env python3
"""
重新计算技术指标（SAR、RSI、布林带）
基于okex_kline_ohlc表的OHLC数据计算
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import sys

# 27个监控币种
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'BNB-USDT-SWAP', 'XRP-USDT-SWAP',
    'SOL-USDT-SWAP', 'DOGE-USDT-SWAP', 'ADA-USDT-SWAP', 'TRX-USDT-SWAP',
    'AVAX-USDT-SWAP', 'SHIB-USDT-SWAP', 'DOT-USDT-SWAP', 'LINK-USDT-SWAP',
    'BCH-USDT-SWAP', 'UNI-USDT-SWAP', 'LTC-USDT-SWAP', 'APT-USDT-SWAP',
    'ARB-USDT-SWAP', 'FIL-USDT-SWAP', 'AAVE-USDT-SWAP', 'ETC-USDT-SWAP',
    'OP-USDT-SWAP', 'CRV-USDT-SWAP', 'STX-USDT-SWAP', 'CFX-USDT-SWAP',
    'LDO-USDT-SWAP', 'TAO-USDT-SWAP', 'CRO-USDT-SWAP'
]

TIMEFRAMES = ['5m', '1H']

def calculate_rsi(prices, period=14):
    """计算RSI指标"""
    if len(prices) < period + 1:
        return [None] * len(prices)
    
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = None
    rsi[period] = 100. - 100. / (1. + rs)
    
    for i in range(period + 1, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
        
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    
    return rsi.tolist()

def calculate_sar(highs, lows, closes, af=0.02, max_af=0.2):
    """计算抛物线SAR指标"""
    if len(highs) < 5:
        return [None] * len(highs)
    
    sar = [None] * len(highs)
    ep = highs[0]
    sar[0] = lows[0]
    trend = 1  # 1: 上升趋势, -1: 下降趋势
    current_af = af
    
    for i in range(1, len(highs)):
        # 计算SAR
        if i == 1:
            sar[i] = sar[i-1] + current_af * (ep - sar[i-1])
        else:
            sar[i] = sar[i-1] + current_af * (ep - sar[i-1])
        
        # 上升趋势
        if trend == 1:
            if closes[i] < sar[i]:
                # 趋势反转
                trend = -1
                sar[i] = ep
                ep = lows[i]
                current_af = af
            else:
                if highs[i] > ep:
                    ep = highs[i]
                    current_af = min(current_af + af, max_af)
        # 下降趋势
        else:
            if closes[i] > sar[i]:
                # 趋势反转
                trend = 1
                sar[i] = ep
                ep = highs[i]
                current_af = af
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    current_af = min(current_af + af, max_af)
    
    return sar

def calculate_bollinger_bands(closes, period=20, std_dev=2):
    """计算布林带"""
    if len(closes) < period:
        return [None]*len(closes), [None]*len(closes), [None]*len(closes)
    
    df = pd.DataFrame({'close': closes})
    df['middle'] = df['close'].rolling(window=period).mean()
    df['std'] = df['close'].rolling(window=period).std()
    df['upper'] = df['middle'] + (std_dev * df['std'])
    df['lower'] = df['middle'] - (std_dev * df['std'])
    
    return df['upper'].tolist(), df['middle'].tolist(), df['lower'].tolist()

def recalculate_indicators_for_symbol(symbol, timeframe, conn):
    """为指定币种重新计算指标"""
    cursor = conn.cursor()
    
    # 获取K线数据
    cursor.execute("""
        SELECT timestamp, open, high, low, close, volume
        FROM okex_kline_ohlc
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    """, (symbol, timeframe))
    
    klines = cursor.fetchall()
    if not klines:
        print(f"  ⚠️  没有K线数据: {symbol} {timeframe}")
        return 0
    
    timestamps = [row[0] for row in klines]
    opens = [row[1] for row in klines]
    highs = [row[2] for row in klines]
    lows = [row[3] for row in klines]
    closes = [row[4] for row in klines]
    
    # 计算指标
    rsi_values = calculate_rsi(closes, period=14)
    sar_values = calculate_sar(highs, lows, closes)
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes, period=20, std_dev=2)
    
    # 删除旧数据
    cursor.execute("""
        DELETE FROM okex_indicators_history
        WHERE symbol = ? AND timeframe = ?
    """, (symbol, timeframe))
    
    deleted = cursor.rowcount
    
    # 插入新数据
    inserted = 0
    for i in range(len(timestamps)):
        # 跳过前20个数据点（布林带需要20个周期）
        if i < 20:
            continue
        
        try:
            cursor.execute("""
                INSERT INTO okex_indicators_history
                (symbol, timeframe, timestamp, current_price, rsi_14, sar, 
                 bb_upper, bb_middle, bb_lower, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                symbol,
                timeframe,
                timestamps[i],
                closes[i],
                rsi_values[i] if rsi_values[i] is not None else None,
                sar_values[i] if sar_values[i] is not None else None,
                bb_upper[i] if bb_upper[i] is not None else None,
                bb_middle[i] if bb_middle[i] is not None else None,
                bb_lower[i] if bb_lower[i] is not None else None
            ))
            inserted += 1
        except Exception as e:
            print(f"    ❌ 插入失败 {timestamps[i]}: {e}")
    
    conn.commit()
    return inserted, deleted

def main():
    print("=" * 80)
    print("技术指标重新计算工具")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"监控币种: {len(SYMBOLS)} 个")
    print(f"时间周期: {TIMEFRAMES}")
    print("=" * 80)
    
    conn = sqlite3.connect('crypto_data.db')
    
    total_inserted = 0
    total_deleted = 0
    
    for symbol in SYMBOLS:
        print(f"\n处理: {symbol}")
        
        for timeframe in TIMEFRAMES:
            print(f"  {timeframe}: ", end="", flush=True)
            
            try:
                inserted, deleted = recalculate_indicators_for_symbol(symbol, timeframe, conn)
                print(f"✅ 删除 {deleted} 条, 新增 {inserted} 条")
                total_inserted += inserted
                total_deleted += deleted
            except Exception as e:
                print(f"❌ 失败: {e}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总计删除: {total_deleted} 条")
    print(f"总计新增: {total_inserted} 条")
    print("=" * 80)

if __name__ == "__main__":
    main()
