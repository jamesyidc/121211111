#!/usr/bin/env python3
"""
补充48小时数据脚本
为12个新币种补充额外的历史数据，使其达到48小时（576条记录）
"""

import sqlite3
import requests
import time
from datetime import datetime, timedelta
import pandas_ta as ta
import pandas as pd

DB_PATH = 'crypto_data.db'
OKEX_API = "https://www.okx.com/api/v5/market/candles"

# 12个需要补充数据的币种
COINS_TO_BACKFILL = [
    'HBAR-USDT-SWAP', 'FIL-USDT-SWAP', 'CRO-USDT-SWAP', 'AAVE-USDT-SWAP',
    'UNI-USDT-SWAP', 'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP',
    'CRV-USDT-SWAP', 'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

TIMEFRAMES = ['5m', '1H']  # Both 5-minute and 1-hour data

def get_existing_count(symbol, timeframe):
    """获取现有记录数"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM kline_technical_markers
        WHERE symbol = ? AND timeframe = ? AND sar IS NOT NULL
    """, (symbol, timeframe))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_earliest_timestamp(symbol, timeframe):
    """获取最早的时间戳"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MIN(timestamp) FROM kline_technical_markers
        WHERE symbol = ? AND timeframe = ?
    """, (symbol, timeframe))
    result = cursor.fetchone()[0]
    conn.close()
    return result

def fetch_okex_klines(symbol, timeframe, limit=300, before=None):
    """从OKEx API获取K线数据"""
    params = {
        'instId': symbol,
        'bar': timeframe,
        'limit': str(limit)
    }
    
    if before:
        params['before'] = str(before)
    
    try:
        response = requests.get(OKEX_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == '0' and data.get('data'):
            return data['data']
        else:
            print(f"  ⚠️  API返回错误: {data.get('msg', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"  ❌ API请求失败: {e}")
        return []

def calculate_indicators(df):
    """计算技术指标（SAR, RSI, BB）"""
    try:
        # Calculate SAR
        sar_result = ta.psar(
            high=df['high'],
            low=df['low'],
            close=df['close']
        )
        
        if sar_result is not None and not sar_result.empty:
            # pandas_ta returns a DataFrame with columns like PSARl_0.02_0.2 and PSARs_0.02_0.2
            long_col = [col for col in sar_result.columns if 'PSARl' in col]
            short_col = [col for col in sar_result.columns if 'PSARs' in col]
            
            if long_col and short_col:
                df['sar_long'] = sar_result[long_col[0]]
                df['sar_short'] = sar_result[short_col[0]]
                df['sar'] = df['sar_long'].fillna(df['sar_short'])
                
                # Determine position (bullish when sar_long exists, bearish when sar_short exists)
                df['sar_position'] = df.apply(
                    lambda row: 'bullish' if pd.notna(row['sar_long']) else 'bearish',
                    axis=1
                )
            else:
                df['sar'] = None
                df['sar_position'] = None
        else:
            df['sar'] = None
            df['sar_position'] = None
        
        # Calculate RSI
        df['rsi_14'] = ta.rsi(df['close'], length=14)
        
        # Calculate Bollinger Bands
        bb = ta.bbands(df['close'], length=20, std=2)
        if bb is not None and not bb.empty:
            df['bb_upper'] = bb['BBU_20_2.0']
            df['bb_middle'] = bb['BBM_20_2.0']
            df['bb_lower'] = bb['BBL_20_2.0']
        
        # Determine SAR quadrant based on position
        df['sar_quadrant'] = df['sar_position'].map({
            'bullish': 'Q1',
            'bearish': 'Q3'
        })
        
        return True
    except Exception as e:
        print(f"  ⚠️  指标计算错误: {e}")
        return False

def insert_kline_data(symbol, timeframe, kline_data):
    """将K线数据和指标插入数据库"""
    if not kline_data:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Prepare DataFrame
    df = pd.DataFrame(kline_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 
        'volume', 'volume_currency', 'volume_currency_quote', 'confirm'
    ])
    
    # Convert data types
    df['timestamp'] = df['timestamp'].astype(int)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    # Calculate indicators
    if not calculate_indicators(df):
        return 0
    
    inserted_count = 0
    
    for _, row in df.iterrows():
        try:
            # Insert into okex_kline_ohlc
            cursor.execute("""
                INSERT OR IGNORE INTO okex_kline_ohlc (
                    symbol, timeframe, timestamp, open, high, low, close, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, timeframe, int(row['timestamp']),
                row['open'], row['high'], row['low'], row['close'], row['volume']
            ))
            
            # Insert into kline_technical_markers (only if SAR exists)
            if pd.notna(row['sar']):
                cursor.execute("""
                    INSERT OR IGNORE INTO kline_technical_markers (
                        symbol, timeframe, timestamp,
                        rsi_14, sar, sar_position, sar_quadrant,
                        bb_upper, bb_middle, bb_lower
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, timeframe, int(row['timestamp']),
                    row['rsi_14'] if pd.notna(row['rsi_14']) else None,
                    row['sar'],
                    row['sar_position'],
                    row['sar_quadrant'],
                    row['bb_upper'] if pd.notna(row.get('bb_upper')) else None,
                    row['bb_middle'] if pd.notna(row.get('bb_middle')) else None,
                    row['bb_lower'] if pd.notna(row.get('bb_lower')) else None
                ))
                
                if cursor.rowcount > 0:
                    inserted_count += 1
        
        except Exception as e:
            continue
    
    conn.commit()
    conn.close()
    
    return inserted_count

def backfill_symbol(symbol, timeframe):
    """为单个币种和时间框架补充数据"""
    print(f"\n{'='*70}")
    print(f"📊 处理 {symbol} ({timeframe})")
    print(f"{'='*70}")
    
    # Check current status
    existing_count = get_existing_count(symbol, timeframe)
    target = 576 if timeframe == '5m' else 300
    
    print(f"  当前记录: {existing_count}")
    print(f"  目标记录: {target}")
    
    if existing_count >= target:
        print(f"  ✅ 数据已充足，跳过")
        return existing_count
    
    needed = target - existing_count
    print(f"  需要补充: {needed} 条")
    
    # Get earliest timestamp
    earliest_ts = get_earliest_timestamp(symbol, timeframe)
    if not earliest_ts:
        print(f"  ⚠️  无法获取最早时间戳")
        return 0
    
    print(f"  最早时间: {datetime.fromtimestamp(earliest_ts/1000).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Fetch historical data in batches
    total_inserted = 0
    fetch_before = earliest_ts
    batches_needed = (needed // 300) + 1
    
    print(f"  开始获取 {batches_needed} 批历史数据...")
    
    for batch in range(batches_needed):
        print(f"    批次 {batch + 1}/{batches_needed}...", end=' ', flush=True)
        
        klines = fetch_okex_klines(symbol, timeframe, limit=300, before=fetch_before)
        
        if not klines:
            print("❌ 无数据")
            break
        
        inserted = insert_kline_data(symbol, timeframe, klines)
        total_inserted += inserted
        
        print(f"✅ 插入 {inserted} 条")
        
        # Update fetch_before to the earliest timestamp in this batch
        fetch_before = int(klines[-1][0])  # Last item is the oldest
        
        # Check if we have enough
        new_count = get_existing_count(symbol, timeframe)
        if new_count >= target:
            print(f"  ✅ 已达到目标 {target} 条记录")
            break
        
        # Rate limiting
        time.sleep(0.5)
    
    final_count = get_existing_count(symbol, timeframe)
    print(f"\n  ✅ 完成！总记录: {final_count} ({final_count - existing_count} 条新增)")
    
    return total_inserted

def main():
    print("\n" + "="*80)
    print("🚀 补充48小时历史数据 - 12个新币种")
    print("="*80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 币种数量: {len(COINS_TO_BACKFILL)}")
    print(f"📊 时间框架: {TIMEFRAMES}")
    print(f"🎯 目标: 5m=576条, 1H=300条")
    
    total_inserted = 0
    task_count = 0
    success_count = 0
    
    for symbol in COINS_TO_BACKFILL:
        for timeframe in TIMEFRAMES:
            task_count += 1
            try:
                inserted = backfill_symbol(symbol, timeframe)
                if inserted > 0:
                    success_count += 1
                total_inserted += inserted
            except Exception as e:
                print(f"\n❌ {symbol} ({timeframe}) 处理失败: {e}")
                continue
    
    print("\n" + "="*80)
    print("📊 补充数据完成统计")
    print("="*80)
    print(f"✅ 成功任务: {success_count}/{task_count}")
    print(f"📈 新增记录: {total_inserted} 条")
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
