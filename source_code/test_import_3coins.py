#!/usr/bin/env python3
"""
完整历史数据导入 - 优化版
一次性计算所有K线的指标，然后批量插入数据库
"""

import requests
import sqlite3
import talib
import numpy as np
from datetime import datetime
import time

# 27个币种
SYMBOLS_ALL = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP', 
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

def fetch_klines(symbol, bar, limit):
    """从 OKEx 获取K线"""
    url = 'https://www.okx.com/api/v5/market/candles'
    params = {'instId': symbol, 'bar': bar, 'limit': limit}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '0' and data['data']:
                klines = []
                for candle in data['data']:
                    klines.append([
                        int(candle[0]), float(candle[1]), float(candle[2]),
                        float(candle[3]), float(candle[4]), float(candle[5])
                    ])
                return klines[::-1]  # 反转为时间正序
        return []
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
        return []

def calculate_all_indicators(klines):
    """
    一次性计算所有K线的指标
    返回每根K线对应的指标列表
    """
    if len(klines) < 20:
        return []
    
    closes = np.array([float(k[4]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    
    # 计算所有指标
    rsi_array = talib.RSI(closes, timeperiod=14)
    sar_array = talib.SAR(highs, lows, acceleration=0.02, maximum=0.2)
    bb_upper, bb_middle, bb_lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)
    
    # 为每根K线构建指标字典
    indicators_list = []
    for i in range(len(klines)):
        current_price = closes[i]
        rsi_val = rsi_array[i] if not np.isnan(rsi_array[i]) else None
        sar_val = sar_array[i] if not np.isnan(sar_array[i]) else None
        
        # SAR位置和标签
        if sar_val and current_price:
            sar_position = 'bullish' if current_price > sar_val else 'bearish'
            
            # 计算连续周期数
            count = 1
            for j in range(i - 1, -1, -1):
                if np.isnan(sar_array[j]):
                    break
                prev_position = 'bullish' if closes[j] > sar_array[j] else 'bearish'
                if prev_position == sar_position:
                    count += 1
                else:
                    break
            
            sar_label = f"{'多头' if sar_position == 'bullish' else '空头'}{count:02d}"
        else:
            sar_position = None
            sar_label = None
        
        # Bollinger Bands
        bb_upper_val = bb_upper[i] if not np.isnan(bb_upper[i]) else None
        bb_middle_val = bb_middle[i] if not np.isnan(bb_middle[i]) else None
        bb_lower_val = bb_lower[i] if not np.isnan(bb_lower[i]) else None
        
        indicators_list.append({
            'timestamp': klines[i][0],
            'current_price': current_price,
            'rsi_14': rsi_val,
            'sar': sar_val,
            'sar_position': sar_position,
            'sar_label': sar_label,
            'bb_upper': bb_upper_val,
            'bb_middle': bb_middle_val,
            'bb_lower': bb_lower_val
        })
    
    return indicators_list

def save_indicators_batch(symbol, timeframe, indicators_list):
    """批量保存指标到数据库"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 确保表存在
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS okex_indicators_history (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            current_price REAL,
            rsi_14 REAL,
            sar REAL,
            sar_position TEXT,
            sar_label TEXT,
            bb_upper REAL,
            bb_middle REAL,
            bb_lower REAL,
            created_at TEXT,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    ''')
    
    # 批量插入
    saved_count = 0
    for ind in indicators_list:
        created_at = datetime.fromtimestamp(ind['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO okex_indicators_history 
                (symbol, timeframe, timestamp, current_price, rsi_14, sar, sar_position,
                 sar_label, bb_upper, bb_middle, bb_lower, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, timeframe, ind['timestamp'], ind['current_price'],
                ind['rsi_14'], ind['sar'], ind['sar_position'], ind['sar_label'],
                ind['bb_upper'], ind['bb_middle'], ind['bb_lower'], created_at
            ))
            saved_count += 1
        except Exception as e:
            print(f"    ⚠️  {created_at}: {e}")
    
    conn.commit()
    conn.close()
    
    return saved_count

def import_symbol_data(symbol, timeframe, bar, limit):
    """导入单个币种的数据"""
    print(f"\n{'='*70}")
    print(f"📊 {symbol} - {timeframe}")
    print(f"{'='*70}")
    
    # 1. 获取K线
    print(f"  🔍 获取最近 {limit} 根K线...")
    klines = fetch_klines(symbol, bar, limit)
    
    if not klines:
        print(f"  ❌ 无法获取K线数据")
        return 0
    
    print(f"  ✅ 获取到 {len(klines)} 根K线")
    
    if len(klines) < 20:
        print(f"  ❌ 数据不足(< 20根)")
        return 0
    
    # 2. 计算所有K线的指标
    print(f"  🧮 计算技术指标...")
    indicators_list = calculate_all_indicators(klines)
    
    if not indicators_list:
        print(f"  ❌ 指标计算失败")
        return 0
    
    valid_indicators = [x for x in indicators_list if x['rsi_14'] is not None]
    print(f"  ✅ 计算完成: {len(valid_indicators)}/{len(indicators_list)} 条有效指标")
    
    # 显示最新指标
    last_ind = indicators_list[-1]
    print(f"  📊 最新指标:")
    print(f"     Price: ${last_ind['current_price']:.2f}")
    if last_ind['rsi_14']:
        print(f"     RSI: {last_ind['rsi_14']:.2f}")
    if last_ind['sar']:
        print(f"     SAR: {last_ind['sar']:.2f} ({last_ind['sar_label']})")
    if last_ind['bb_middle']:
        print(f"     BB: [{last_ind['bb_upper']:.2f}, {last_ind['bb_middle']:.2f}, {last_ind['bb_lower']:.2f}]")
    
    # 3. 保存到数据库
    print(f"  💾 保存到数据库...")
    saved = save_indicators_batch(symbol, timeframe, indicators_list)
    print(f"  ✅ 保存 {saved}/{len(indicators_list)} 条记录")
    
    return saved

def main():
    """主函数"""
    print("\n" + "="*80)
    print("📥 完整历史数据导入工具 (优化版)")
    print("="*80)
    
    # 导入配置
    import_configs = [
        ('5m', '5m', 300),  # 5分钟，300根 ≈ 1天
        ('1H', '1H', 240)   # 1小时，240根 = 10天
    ]
    
    print(f"\n📋 导入配置:")
    print(f"  - 币种数量: {len(SYMBOLS)}")
    print(f"  - 时间周期: 5分钟(300根≈1天), 1小时(240根=10天)")
    print(f"  - 预计导入: {len(SYMBOLS) * sum(c[2] for c in import_configs)} 条记录")
    print(f"\n开始导入...\n")
    
    total_saved = 0
    success_count = 0
    
    SYMBOLS = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n\n{'#'*80}")
        print(f"# [{i}/{len(SYMBOLS)}] {symbol}")
        print(f"{'#'*80}")
        
        for timeframe, bar, limit in import_configs:
            try:
                count = import_symbol_data(symbol, timeframe, bar, limit)
                total_saved += count
                if count > 0:
                    success_count += 1
            except Exception as e:
                print(f"  ❌ 导入失败: {e}")
            
            # 避免请求过快
            time.sleep(0.3)
    
    # 统计输出
    print("\n\n" + "="*80)
    print("✅ 导入完成！")
    print("="*80)
    print(f"  - 总导入: {total_saved} 条记录")
    print(f"  - 成功: {success_count}/{len(SYMBOLS) * len(import_configs)} 个任务")
    print(f"  - 币种: {len(SYMBOLS)}")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
