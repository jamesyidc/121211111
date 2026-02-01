#!/usr/bin/env python3
"""
导入真实OHLC K线数据
创建新表存储完整的OHLC数据
"""

import requests
import sqlite3
import talib
import numpy as np
from datetime import datetime
import time

SYMBOLS_ALL = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP', 
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

# 导入全部27个币种
SYMBOLS = SYMBOLS_ALL

def init_ohlc_table():
    """创建OHLC K线表"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS okex_kline_ohlc (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            created_at TEXT,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ OHLC表初始化完成")

def fetch_klines_paginated(symbol, bar='5m', target_count=1440):
    """分页获取K线数据"""
    all_klines = []
    url = 'https://www.okx.com/api/v5/market/candles'
    params = {'instId': symbol, 'bar': bar, 'limit': 300}
    
    page = 1
    while len(all_klines) < target_count:
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                break
            
            data = response.json()
            if data['code'] != '0' or not data['data']:
                break
            
            batch_klines = []
            for candle in data['data']:
                batch_klines.append([
                    int(candle[0]),      # timestamp (ms)
                    float(candle[1]),    # open
                    float(candle[2]),    # high
                    float(candle[3]),    # low
                    float(candle[4]),    # close
                    float(candle[5])     # volume
                ])
            
            all_klines.extend(batch_klines)
            
            if len(batch_klines) < 300:
                break
            
            if len(all_klines) >= target_count:
                break
            
            oldest_timestamp = batch_klines[-1][0]
            params['after'] = str(oldest_timestamp)
            
            page += 1
            time.sleep(0.2)
            
        except Exception as e:
            print(f"  ⚠️  请求失败: {e}")
            break
    
    all_klines.reverse()
    return all_klines[-target_count:] if len(all_klines) > target_count else all_klines

def save_ohlc_batch(symbol, timeframe, klines):
    """批量保存OHLC数据"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    saved_count = 0
    for kline in klines:
        timestamp = kline[0]
        created_at = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO okex_kline_ohlc 
                (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, timeframe, timestamp,
                kline[1],  # open
                kline[2],  # high
                kline[3],  # low
                kline[4],  # close
                kline[5],  # volume
                created_at
            ))
            saved_count += 1
        except Exception as e:
            pass
    
    conn.commit()
    conn.close()
    
    return saved_count

def import_symbol_ohlc(symbol, timeframe, bar, target_count):
    """导入单个币种的OHLC数据"""
    print(f"\n{'='*70}")
    print(f"📊 {symbol} - {timeframe}")
    print(f"{'='*70}")
    
    print(f"  🔍 获取 {target_count} 根K线...")
    klines = fetch_klines_paginated(symbol, bar, target_count)
    
    if not klines:
        print(f"  ❌ 无法获取K线数据")
        return 0
    
    print(f"  ✅ 获取到 {len(klines)} 根K线")
    
    # 显示价格范围
    opens = [k[1] for k in klines]
    highs = [k[2] for k in klines]
    lows = [k[3] for k in klines]
    closes = [k[4] for k in klines]
    
    print(f"  📊 价格范围:")
    print(f"     最高: ${max(highs):.4f}")
    print(f"     最低: ${min(lows):.4f}")
    print(f"     振幅: ${max(highs) - min(lows):.4f} ({(max(highs) - min(lows)) / sum(closes) * len(closes) * 100:.2f}%)")
    
    # 显示最新K线
    last = klines[-1]
    last_time = datetime.fromtimestamp(last[0] / 1000).strftime('%Y-%m-%d %H:%M')
    print(f"  📈 最新K线 ({last_time}):")
    print(f"     O: ${last[1]:.4f}, H: ${last[2]:.4f}, L: ${last[3]:.4f}, C: ${last[4]:.4f}")
    print(f"     振幅: ${last[2] - last[3]:.4f}")
    
    print(f"  💾 保存到数据库...")
    saved = save_ohlc_batch(symbol, timeframe, klines)
    print(f"  ✅ 保存 {saved}/{len(klines)} 条记录")
    
    return saved

def main():
    """主函数"""
    print("\n" + "="*80)
    print("📥 真实OHLC K线数据导入")
    print("="*80)
    
    # 初始化表
    init_ohlc_table()
    
    # 导入配置
    configs = [
        ('5m', '5m', 1440),  # 5分钟
        ('1H', '1H', 240)    # 1小时
    ]
    
    print(f"\n📋 导入配置:")
    print(f"  - 币种: {len(SYMBOLS)} 个")
    print(f"  - 5分钟: 1440根")
    print(f"  - 1小时: 240根")
    print(f"\n开始导入...\n")
    
    total_saved = 0
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n\n{'#'*80}")
        print(f"# [{i}/{len(SYMBOLS)}] {symbol}")
        print(f"{'#'*80}")
        
        for timeframe, bar, target_count in configs:
            try:
                count = import_symbol_ohlc(symbol, timeframe, bar, target_count)
                total_saved += count
            except Exception as e:
                print(f"  ❌ 导入失败: {e}")
            
            time.sleep(0.3)
    
    print("\n\n" + "="*80)
    print("✅ 导入完成！")
    print("="*80)
    print(f"  - 总导入: {total_saved} 条OHLC记录")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
