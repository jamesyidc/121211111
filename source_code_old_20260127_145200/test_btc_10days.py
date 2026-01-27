#!/usr/bin/env python3
"""
导入完整10天K线数据 - 使用分页获取
"""

import requests
import sqlite3
import talib
import numpy as np
from datetime import datetime, timedelta
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

def fetch_klines_paginated(symbol, bar='5m', target_count=2880):
    """
    分页获取K线数据
    OKEx API每次最多返回300根，需要多次请求
    
    参数:
        target_count: 目标K线数量 (5分钟10天=2880根, 1小时10天=240根)
    """
    all_klines = []
    url = 'https://www.okx.com/api/v5/market/candles'
    
    # 第一次请求
    params = {'instId': symbol, 'bar': bar, 'limit': 300}
    
    page = 1
    while len(all_klines) < target_count:
        try:
            print(f"    Page {page}: 获取300根K线...", end='')
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f" ❌ HTTP {response.status_code}")
                break
            
            data = response.json()
            if data['code'] != '0' or not data['data']:
                print(f" ❌ No data")
                break
            
            # 转换数据格式
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
            
            print(f" ✅ {len(batch_klines)}根")
            
            # 添加到总列表（注意：API返回的是倒序，新到旧）
            all_klines.extend(batch_klines)
            
            # 如果这批数据少于300根，说明已经到头了
            if len(batch_klines) < 300:
                print(f"    到达数据起点，总共获取 {len(all_klines)} 根")
                break
            
            # 已经足够了
            if len(all_klines) >= target_count:
                print(f"    已达到目标数量 {target_count}")
                break
            
            # 准备下一页：使用最后一根K线的时间戳作为'after'参数
            # OKEx的'after'参数表示"获取这个时间之前的数据"
            oldest_timestamp = batch_klines[-1][0]
            params['after'] = str(oldest_timestamp)
            
            page += 1
            time.sleep(0.2)  # 避免请求过快
            
        except Exception as e:
            print(f" ❌ 请求失败: {e}")
            break
    
    # 反转为时间正序（旧到新）
    all_klines.reverse()
    
    # 只返回目标数量
    return all_klines[-target_count:] if len(all_klines) > target_count else all_klines

def calculate_all_indicators(klines):
    """一次性计算所有K线的指标"""
    if len(klines) < 20:
        return []
    
    closes = np.array([float(k[4]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    
    # 计算所有指标
    rsi_array = talib.RSI(closes, timeperiod=14)
    sar_array = talib.SAR(highs, lows, acceleration=0.02, maximum=0.2)
    bb_upper, bb_middle, bb_lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)
    
    indicators_list = []
    for i in range(len(klines)):
        current_price = closes[i]
        rsi_val = rsi_array[i] if not np.isnan(rsi_array[i]) else None
        sar_val = sar_array[i] if not np.isnan(sar_array[i]) else None
        
        # SAR位置和标签
        if sar_val and current_price:
            sar_position = 'bullish' if current_price > sar_val else 'bearish'
            
            count = 1
            for j in range(i - 1, -1, -1):
                if np.isnan(sar_array[j]):
                    break
                prev_position = 'bullish' if closes[j] > sar_array[j] else 'bearish'
                if prev_position == sar_position:
                    count += 1
                else:
                    break
            
            sar_count_label = f"{'多头' if sar_position == 'bullish' else '空头'}{count:02d}"
        else:
            sar_position = None
            sar_count_label = None
        
        bb_upper_val = bb_upper[i] if not np.isnan(bb_upper[i]) else None
        bb_middle_val = bb_middle[i] if not np.isnan(bb_middle[i]) else None
        bb_lower_val = bb_lower[i] if not np.isnan(bb_lower[i]) else None
        
        indicators_list.append({
            'timestamp': klines[i][0],
            'current_price': current_price,
            'rsi_14': rsi_val,
            'sar': sar_val,
            'sar_position': sar_position,
            'sar_count_label': sar_count_label,
            'bb_upper': bb_upper_val,
            'bb_middle': bb_middle_val,
            'bb_lower': bb_lower_val
        })
    
    return indicators_list

def save_indicators_batch(symbol, timeframe, indicators_list):
    """批量保存指标到数据库"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    saved_count = 0
    for ind in indicators_list:
        created_at = datetime.fromtimestamp(ind['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO okex_indicators_history 
                (symbol, timeframe, timestamp, current_price, rsi_14, sar, sar_position,
                 sar_count_label, bb_upper, bb_middle, bb_lower, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, timeframe, ind['timestamp'], ind['current_price'],
                ind['rsi_14'], ind['sar'], ind['sar_position'], ind['sar_count_label'],
                ind['bb_upper'], ind['bb_middle'], ind['bb_lower'], created_at
            ))
            saved_count += 1
        except Exception as e:
            pass  # 忽略重复键错误
    
    conn.commit()
    conn.close()
    
    return saved_count

def import_symbol_data(symbol, timeframe, bar, target_count):
    """导入单个币种的数据"""
    print(f"\n{'='*70}")
    print(f"📊 {symbol} - {timeframe}")
    print(f"{'='*70}")
    
    # 1. 获取K线（分页）
    print(f"  🔍 分页获取 {target_count} 根K线...")
    klines = fetch_klines_paginated(symbol, bar, target_count)
    
    if not klines:
        print(f"  ❌ 无法获取K线数据")
        return 0
    
    print(f"  ✅ 总共获取 {len(klines)} 根K线")
    
    if len(klines) < 20:
        print(f"  ❌ 数据不足(< 20根)")
        return 0
    
    # 显示时间范围
    start_time = datetime.fromtimestamp(klines[0][0] / 1000).strftime('%Y-%m-%d %H:%M')
    end_time = datetime.fromtimestamp(klines[-1][0] / 1000).strftime('%Y-%m-%d %H:%M')
    print(f"  📅 时间范围: {start_time} → {end_time}")
    
    # 2. 计算指标
    print(f"  🧮 计算技术指标...")
    indicators_list = calculate_all_indicators(klines)
    
    if not indicators_list:
        print(f"  ❌ 指标计算失败")
        return 0
    
    valid_count = sum(1 for x in indicators_list if x['rsi_14'] is not None)
    print(f"  ✅ 完成: {valid_count}/{len(indicators_list)} 条有效指标")
    
    # 3. 保存
    print(f"  💾 保存到数据库...")
    saved = save_indicators_batch(symbol, timeframe, indicators_list)
    print(f"  ✅ 保存 {saved}/{len(indicators_list)} 条记录")
    
    return saved

def main():
    """主函数"""
    print("\n" + "="*80)
    print("📥 完整10天K线数据导入")
    print("="*80)
    
    # 导入配置
    configs = [
        ('5m', '5m', 2880),  # 5分钟，2880根 = 10天
        ('1H', '1H', 240)    # 1小时，240根 = 10天
    ]
    
    print(f"\n📋 导入配置:")
    print(f"  - 币种: {len(SYMBOLS)} 个")
    print(f"  - 5分钟: 2880根 = 10天")
    print(f"  - 1小时: 240根 = 10天")
    print(f"  - 总计: {len(SYMBOLS) * sum(c[2] for c in configs)} 条记录")
    print(f"\n开始导入...\n")
    
    total_saved = 0
    success_count = 0
    
    SYMBOLS = ['BTC-USDT-SWAP']  # 测试BTC
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n\n{'#'*80}")
        print(f"# [{i}/{len(SYMBOLS)}] {symbol}")
        print(f"{'#'*80}")
        
        for timeframe, bar, target_count in configs:
            try:
                count = import_symbol_data(symbol, timeframe, bar, target_count)
                total_saved += count
                if count > 0:
                    success_count += 1
            except Exception as e:
                print(f"  ❌ 导入失败: {e}")
            
            time.sleep(0.5)
    
    print("\n\n" + "="*80)
    print("✅ 导入完成！")
    print("="*80)
    print(f"  - 总导入: {total_saved} 条记录")
    print(f"  - 成功: {success_count}/{len(SYMBOLS) * len(configs)} 个任务")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
