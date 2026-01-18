#!/usr/bin/env python3
"""
补充缺失币种的10天历史数据和技术指标
币种: HBAR, FIL, CRO, AAVE, UNI, NEAR, APT, CFX, CRV, STX, LDO, TAO
周期: 5m (5分钟) 和 1H (1小时)
时长: 10天
"""

import sqlite3
import requests
import time
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import pandas_ta as ta

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
OKEX_BASE_URL = "https://www.okx.com"
OKEX_CANDLES_ENDPOINT = "/api/v5/market/candles"
DB_FILE = 'crypto_data.db'

# 12个缺失的币种
MISSING_SYMBOLS = [
    'HBAR-USDT-SWAP', 'FIL-USDT-SWAP', 'CRO-USDT-SWAP', 'AAVE-USDT-SWAP',
    'UNI-USDT-SWAP', 'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP',
    'CRV-USDT-SWAP', 'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

# 两个周期
TIMEFRAMES = ['5m', '1H']

def fetch_okex_klines(inst_id: str, bar: str, limit: int = 300):
    """从OKEx获取K线数据"""
    url = f"{OKEX_BASE_URL}{OKEX_CANDLES_ENDPOINT}"
    params = {
        'instId': inst_id,
        'bar': bar,
        'limit': limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['code'] == '0' and data['data']:
            return data['data']
        else:
            print(f"  ⚠️  API返回错误: {data.get('msg', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        return None

def calculate_technical_indicators(df: pd.DataFrame):
    """计算技术指标"""
    try:
        # RSI
        df['rsi_14'] = ta.rsi(df['close'], length=14)
        
        # SAR (Parabolic SAR)
        sar = ta.psar(df['high'], df['low'], df['close'])
        if sar is not None and not sar.empty:
            df['sar'] = sar['PSARl_0.02_0.2'].fillna(sar['PSARs_0.02_0.2'])
        else:
            df['sar'] = df['close']
        
        # 计算SAR位置（多头/空头）
        df['sar_position'] = df.apply(
            lambda row: 'bullish' if row['close'] > row['sar'] else 'bearish',
            axis=1
        )
        
        # 计算SAR象限 (1-4)
        df['sar_quadrant'] = df.apply(
            lambda row: calculate_sar_quadrant(row['close'], row['sar'], row['sar_position']),
            axis=1
        )
        
        # 布林带
        bbands = ta.bbands(df['close'], length=20, std=2)
        if bbands is not None and not bbands.empty:
            df['bb_upper'] = bbands['BBU_20_2.0']
            df['bb_middle'] = bbands['BBM_20_2.0']
            df['bb_lower'] = bbands['BBL_20_2.0']
        
        return df
    except Exception as e:
        print(f"  ⚠️  指标计算错误: {e}")
        return df

def calculate_sar_quadrant(close, sar, position):
    """计算SAR象限"""
    if position == 'bullish':
        diff_percent = ((close - sar) / sar) * 100
        if diff_percent >= 3:
            return 4
        elif diff_percent >= 1:
            return 3
        else:
            return 2
    else:  # bearish
        diff_percent = ((sar - close) / close) * 100
        if diff_percent >= 3:
            return 1
        elif diff_percent >= 1:
            return 2
        else:
            return 3

def save_to_database(symbol: str, timeframe: str, df: pd.DataFrame):
    """保存数据到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        # 检查是否已存在
        cursor.execute("""
            SELECT id FROM kline_technical_markers
            WHERE symbol = ? AND timeframe = ? AND timestamp = ?
        """, (symbol, timeframe, row['timestamp']))
        
        if cursor.fetchone():
            skipped += 1
            continue
        
        # 插入OHLC数据
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO okex_kline_ohlc 
                (symbol, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, timeframe, row['timestamp'], 
                  row['open'], row['high'], row['low'], row['close'], row['volume']))
        except:
            pass
        
        # 插入技术指标数据 (不包含OHLC，只有指标)
        try:
            cursor.execute("""
                INSERT INTO kline_technical_markers (
                    symbol, timeframe, timestamp,
                    rsi_14, sar, sar_position, sar_quadrant,
                    bb_upper, bb_middle, bb_lower
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, timeframe, row['timestamp'],
                row.get('rsi_14'), row.get('sar'), row.get('sar_position'), row.get('sar_quadrant'),
                row.get('bb_upper'), row.get('bb_middle'), row.get('bb_lower')
            ))
            inserted += 1
        except Exception as e:
            print(f"    插入失败 (ts={row['timestamp']}): {e}")
    
    conn.commit()
    conn.close()
    
    return inserted, skipped

def process_symbol_timeframe(symbol: str, timeframe: str):
    """处理单个币种的单个周期"""
    print(f"\n{'='*60}")
    print(f"处理 {symbol} - {timeframe}")
    print(f"{'='*60}")
    
    # 计算需要获取的批次数
    if timeframe == '5m':
        # 10天 * 24小时 * 12个5分钟 = 2880条
        # OKEx每次最多300条，需要10批
        batches = 10
        total_needed = 2880
    else:  # 1H
        # 10天 * 24小时 = 240条
        batches = 1
        total_needed = 240
    
    all_data = []
    
    for batch in range(batches):
        print(f"  批次 {batch+1}/{batches}...")
        
        # 获取数据
        klines = fetch_okex_klines(symbol, timeframe, limit=300)
        if not klines:
            print(f"  ⚠️  批次{batch+1}获取失败，跳过")
            continue
        
        all_data.extend(klines)
        time.sleep(0.3)  # 避免API限流
    
    if not all_data:
        print(f"  ❌ 没有获取到任何数据")
        return 0
    
    print(f"  ✅ 共获取 {len(all_data)} 条K线")
    
    # 转换为DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 
        'volume', 'volume_currency', 'volume_quote', 'confirm'
    ])
    
    # 数据类型转换
    df['timestamp'] = df['timestamp'].astype(int)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    # 时间转换
    df['datetime_utc'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['datetime_beijing'] = df['datetime_utc'].dt.tz_localize('UTC').dt.tz_convert(BEIJING_TZ)
    df['datetime_beijing'] = df['datetime_beijing'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['datetime_utc'] = df['datetime_utc'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # 按时间排序（旧到新）
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 计算技术指标
    print(f"  📊 计算技术指标...")
    df = calculate_technical_indicators(df)
    
    # 保存到数据库
    print(f"  💾 保存到数据库...")
    inserted, skipped = save_to_database(symbol, timeframe, df)
    
    print(f"  ✅ 完成: 插入{inserted}条, 跳过{skipped}条")
    return inserted

def main():
    print("\n" + "="*70)
    print("🚀 开始补充缺失币种的10天历史数据")
    print("="*70)
    print(f"⏰ 开始时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 币种数量: {len(MISSING_SYMBOLS)}")
    print(f"📊 周期: {', '.join(TIMEFRAMES)}")
    print(f"📅 时长: 10天")
    print()
    
    total_inserted = 0
    success_count = 0
    
    for symbol in MISSING_SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                count = process_symbol_timeframe(symbol, timeframe)
                if count > 0:
                    success_count += 1
                    total_inserted += count
            except Exception as e:
                print(f"\n❌ {symbol} - {timeframe} 处理失败: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "="*70)
    print("📊 补充完成统计")
    print("="*70)
    print(f"✅ 成功任务: {success_count}/{len(MISSING_SYMBOLS) * len(TIMEFRAMES)}")
    print(f"📈 总插入记录: {total_inserted:,} 条")
    print(f"⏰ 结束时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
