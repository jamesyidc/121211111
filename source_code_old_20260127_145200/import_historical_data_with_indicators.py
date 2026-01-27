#!/usr/bin/env python3
"""
导入历史K线数据并计算完整技术指标
- 从 OKEx API 获取历史 OHLCV 数据
- 计算 RSI, SAR, 布林带等技术指标
- 存储到 okex_technical_indicators 表
"""

import requests
import sqlite3
import talib
import numpy as np
from datetime import datetime, timedelta
import time
import sys

# 27个币种
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP', 
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

def fetch_historical_klines(symbol, bar='5m', limit=300):
    """
    从 OKEx API 获取历史K线数据
    
    返回格式: [[timestamp, open, high, low, close, volume], ...]
    """
    url = 'https://www.okx.com/api/v5/market/candles'
    params = {
        'instId': symbol,
        'bar': bar,
        'limit': limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '0' and data['data']:
                # 返回格式: [timestamp, open, high, low, close, volume, ...]
                # 只取前6个字段
                klines = []
                for candle in data['data']:
                    klines.append([
                        int(candle[0]),  # timestamp (ms)
                        float(candle[1]),  # open
                        float(candle[2]),  # high
                        float(candle[3]),  # low
                        float(candle[4]),  # close
                        float(candle[5])   # volume
                    ])
                return klines[::-1]  # 反转为时间正序
        return []
    except Exception as e:
        print(f"❌ 获取 {symbol} {bar} K线失败: {e}")
        return []

def calculate_indicators(klines):
    """
    计算技术指标
    
    参数:
        klines: [[timestamp, open, high, low, close, volume], ...]
        
    返回:
        字典，包含 RSI, SAR, BB 等指标
    """
    if len(klines) < 20:
        return None
    
    closes = np.array([float(k[4]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    
    current_price = closes[-1]
    
    # RSI(14)
    rsi = talib.RSI(closes, timeperiod=14)
    rsi_14 = rsi[-1] if not np.isnan(rsi[-1]) else None
    
    # Parabolic SAR
    sar = talib.SAR(highs, lows, acceleration=0.02, maximum=0.2)
    sar_value = sar[-1] if not np.isnan(sar[-1]) else None
    
    # SAR 位置和计数
    if sar_value:
        sar_position = 'bullish' if current_price > sar_value else 'bearish'
        
        # 计算连续周期数
        count = 1
        for i in range(len(sar) - 2, -1, -1):
            if np.isnan(sar[i]):
                break
            prev_position = 'bullish' if closes[i] > sar[i] else 'bearish'
            if prev_position == sar_position:
                count += 1
            else:
                break
        
        sar_count_label = f"{'多头' if sar_position == 'bullish' else '空头'}{count:02d}"
        
        # SAR 象限
        bb_upper, bb_middle, bb_lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)
        
        if not np.isnan(bb_upper[-1]):
            if sar_value > bb_upper[-1]:
                sar_quadrant = 1
            elif sar_value > bb_middle[-1]:
                sar_quadrant = 2
            elif sar_value > bb_lower[-1]:
                sar_quadrant = 3
            else:
                sar_quadrant = 4
        else:
            sar_quadrant = None
    else:
        sar_position = None
        sar_count_label = None
        sar_quadrant = None
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)
    bb_upper_val = bb_upper[-1] if not np.isnan(bb_upper[-1]) else None
    bb_middle_val = bb_middle[-1] if not np.isnan(bb_middle[-1]) else None
    bb_lower_val = bb_lower[-1] if not np.isnan(bb_lower[-1]) else None
    
    return {
        'current_price': current_price,
        'rsi_14': rsi_14,
        'sar': sar_value,
        'sar_position': sar_position,
        'sar_quadrant': sar_quadrant,
        'sar_count_label': sar_count_label,
        'bb_upper': bb_upper_val,
        'bb_middle': bb_middle_val,
        'bb_lower': bb_lower_val
    }

def save_to_database(symbol, timeframe, klines):
    """
    保存K线数据到数据库 okex_indicators_history 表
    
    每根K线创建一条记录，同时为每根K线计算指标
    """
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 确保 okex_indicators_history 表存在
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS okex_indicators_history (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            current_price REAL,
            rsi_14 REAL,
            sar REAL,
            sar_position TEXT,
            sar_count_label TEXT,
            bb_upper REAL,
            bb_middle REAL,
            bb_lower REAL,
            created_at TEXT,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    ''')
    
    saved_count = 0
    
    # 为每根K线计算指标并保存
    for i in range(len(klines)):
        # 使用从开始到当前K线的所有数据来计算指标
        current_klines = klines[:i+1]
        
        if len(current_klines) < 20:
            # 数据不足，无法计算指标
            continue
        
        # 计算当前K线的指标
        indicators = calculate_indicators(current_klines)
        
        if not indicators:
            continue
        
        kline = klines[i]
        timestamp = kline[0]
        created_at = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO okex_indicators_history 
                (symbol, timeframe, timestamp, current_price, rsi_14, sar, sar_position,
                 sar_count_label, bb_upper, bb_middle, bb_lower, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                timeframe,
                timestamp,
                indicators['current_price'],
                indicators['rsi_14'],
                indicators['sar'],
                indicators['sar_position'],
                indicators['sar_count_label'],
                indicators['bb_upper'],
                indicators['bb_middle'],
                indicators['bb_lower'],
                created_at
            ))
            saved_count += 1
        except Exception as e:
            print(f"  ⚠️  保存失败: {created_at} - {e}")
    
    conn.commit()
    conn.close()
    
    return saved_count

def import_data_for_symbol(symbol, timeframe, bar, limit=300):
    """
    为单个币种导入数据
    """
    print(f"\n{'='*60}")
    print(f"📊 {symbol} - {timeframe}")
    print(f"{'='*60}")
    
    # 1. 获取历史K线
    print(f"  🔍 获取最近 {limit} 根K线...")
    klines = fetch_historical_klines(symbol, bar, limit)
    
    if not klines:
        print(f"  ❌ 无法获取K线数据")
        return 0
    
    print(f"  ✅ 获取到 {len(klines)} 根K线")
    
    if len(klines) < 20:
        print(f"  ❌ 数据不足(< 20根)，无法计算指标")
        return 0
    
    # 2. 保存到数据库（会为每根K线计算指标）
    print(f"  💾 保存到数据库并计算指标...")
    saved = save_to_database(symbol, timeframe, klines)
    
    if saved > 0:
        # 显示最新K线的指标
        last_indicators = calculate_indicators(klines)
        if last_indicators:
            print(f"  ✅ 保存 {saved}/{len(klines)} 条记录")
            print(f"  📊 最新指标:")
            print(f"     - Price: {last_indicators['current_price']:.2f}")
            print(f"     - RSI(14): {last_indicators['rsi_14']:.2f}" if last_indicators['rsi_14'] else "     - RSI(14): N/A")
            print(f"     - SAR: {last_indicators['sar']:.2f} ({last_indicators['sar_count_label']})" if last_indicators['sar'] else "     - SAR: N/A")
            print(f"     - BB: [{last_indicators['bb_upper']:.2f}, {last_indicators['bb_middle']:.2f}, {last_indicators['bb_lower']:.2f}]" if last_indicators['bb_upper'] else "     - BB: N/A")
        else:
            print(f"  ✅ 保存 {saved}/{len(klines)} 条记录")
    else:
        print(f"  ⚠️  保存 0 条记录")
    
    return saved

def main():
    """主函数"""
    print("\n" + "="*80)
    print("📥 历史K线数据导入工具 (含完整技术指标)")
    print("="*80)
    
    # 统计信息
    total_imported = 0
    success_count = 0
    
    # 导入配置
    timeframes = [
        ('5m', '5m', 1440),   # 5分钟，1440根 ≈ 5天
        ('1H', '1H', 240)      # 1小时，240根 = 10天
    ]
    
    print(f"\n📋 导入配置:")
    print(f"  - 币种数量: {len(SYMBOLS)}")
    print(f"  - 时间周期: 5分钟(1440根≈5天), 1小时(240根=10天)")
    print(f"  - 预计导入: {len(SYMBOLS) * sum(t[2] for t in timeframes)} 条记录")
    
    # 逐个币种导入
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n\n{'#'*80}")
        print(f"# [{i}/{len(SYMBOLS)}] {symbol}")
        print(f"{'#'*80}")
        
        for timeframe, bar, limit in timeframes:
            try:
                count = import_data_for_symbol(symbol, timeframe, bar, limit)
                total_imported += count
                if count > 0:
                    success_count += 1
            except Exception as e:
                print(f"  ❌ 导入失败: {e}")
            
            # 避免请求过快
            time.sleep(0.2)
    
    # 输出统计
    print("\n\n" + "="*80)
    print("✅ 导入完成！")
    print("="*80)
    print(f"  - 总导入: {total_imported} 条记录")
    print(f"  - 成功: {success_count}/{len(SYMBOLS) * len(timeframes)} 个任务")
    print(f"  - 币种: {len(SYMBOLS)}")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
