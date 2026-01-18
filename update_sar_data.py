#!/usr/bin/env python3
"""
SAR数据更新脚本 - 使用现有数据库结构
从OKEx获取最新5分钟K线数据并计算SAR指标
"""
import sqlite3
import requests
import time
from datetime import datetime
import json

# 配置
DB_PATH = 'databases/sar_slope_data.db'
SYMBOLS = [
    'AAVE', 'CRV', 'XRP', 'SUI', 'HBAR', 'DOT', 'NEAR', 'APT', 'TAO', 'LDO',
    'BTC', 'ETH', 'BNB', 'SOL', 'LTC', 'DOGE', 'TRX', 'TON', 'ETC', 'BCH',
    'XLM', 'FIL', 'LINK', 'CRO', 'UNI', 'CFX', 'STX'
]

def calculate_sar(highs, lows, closes, af_start=0.02, af_max=0.2):
    """计算SAR指标"""
    if len(highs) < 2:
        return None, None
    
    sar = []
    ep = highs[0]  # Extreme Point
    af = af_start
    position = 'long'  # 初始假设为多头
    
    sar.append(lows[0])
    
    for i in range(1, len(highs)):
        # 更新SAR值
        if position == 'long':
            new_sar = sar[-1] + af * (ep - sar[-1])
            new_sar = min(new_sar, lows[i-1])
            if i > 1:
                new_sar = min(new_sar, lows[i-2])
            
            # 检查是否反转
            if lows[i] < new_sar:
                position = 'short'
                new_sar = ep
                ep = lows[i]
                af = af_start
            else:
                # 更新EP和AF
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_start, af_max)
        else:  # short
            new_sar = sar[-1] + af * (ep - sar[-1])
            new_sar = max(new_sar, highs[i-1])
            if i > 1:
                new_sar = max(new_sar, highs[i-2])
            
            # 检查是否反转
            if highs[i] > new_sar:
                position = 'long'
                new_sar = ep
                ep = highs[i]
                af = af_start
            else:
                # 更新EP和AF
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_start, af_max)
        
        sar.append(new_sar)
    
    return sar[-1], position

def get_okex_klines(symbol, bar='5m', limit=100):
    """从OKEx获取K线数据"""
    try:
        instId = f"{symbol}-USDT-SWAP"
        url = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar={bar}&limit={limit}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('code') != '0':
            print(f"  ✗ {symbol}: API错误 - {data.get('msg')}")
            return None
        
        klines = data.get('data', [])
        if not klines:
            print(f"  ✗ {symbol}: 无数据")
            return None
        
        # 解析K线数据
        parsed_klines = []
        for k in reversed(klines):  # OKEx返回的数据是逆序的
            parsed_klines.append({
                'timestamp': int(k[0]),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            })
        
        return parsed_klines
        
    except Exception as e:
        print(f"  ✗ {symbol}: 获取数据失败 - {e}")
        return None

def update_symbol_data(symbol):
    """更新单个币种的SAR数据"""
    try:
        # 获取K线数据
        klines = get_okex_klines(symbol, bar='5m', limit=50)
        if not klines:
            return False
        
        # 提取价格数据
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        closes = [k['close'] for k in klines]
        
        # 计算SAR
        sar_value, sar_direction = calculate_sar(highs, lows, closes)
        
        if sar_value is None:
            print(f"  ✗ {symbol}: SAR计算失败")
            return False
        
        # 获取最新K线
        latest = klines[-1]
        timestamp_ms = latest['timestamp']
        
        # 连接数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("""
            SELECT COUNT(*) FROM sar_conversion_points 
            WHERE symbol = ? AND timestamp = ?
        """, (symbol, timestamp_ms))
        
        if cursor.fetchone()[0] > 0:
            print(f"  ⚠ {symbol}: 数据已存在 (时间戳 {timestamp_ms})")
            conn.close()
            return True
        
        # 计算连续变化次数（简化版本）
        cursor.execute("""
            SELECT sar_direction FROM sar_conversion_points
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (symbol,))
        
        result = cursor.fetchone()
        consecutive_changes = 1
        if result and result[0] == sar_direction:
            cursor.execute("""
                SELECT consecutive_changes FROM sar_conversion_points
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (symbol,))
            prev_consecutive = cursor.fetchone()
            if prev_consecutive:
                consecutive_changes = prev_consecutive[0] + 1
        
        # 插入新数据
        dt_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            INSERT INTO sar_conversion_points 
            (symbol, timestamp, kline_time, interval_type, open_price, high_price, 
             low_price, close_price, sar_value, sar_direction, consecutive_changes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, timestamp_ms, dt_str, '5m',
            latest['open'], latest['high'], latest['low'], latest['close'],
            sar_value, sar_direction, consecutive_changes
        ))
        
        conn.commit()
        conn.close()
        
        print(f"  ✓ {symbol}: 更新成功 | SAR={sar_value:.4f} | {sar_direction} | 连续{consecutive_changes}次 | {dt_str}")
        return True
        
    except Exception as e:
        print(f"  ✗ {symbol}: 更新失败 - {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print(f"\n{'='*70}")
    print(f"  SAR数据更新开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    success_count = 0
    failed_count = 0
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"[{i}/{len(SYMBOLS)}] 更新 {symbol}:")
        if update_symbol_data(symbol):
            success_count += 1
        else:
            failed_count += 1
        
        # 避免请求过快
        if i < len(SYMBOLS):
            time.sleep(0.5)
    
    print(f"\n{'='*70}")
    print(f"  更新完成: 成功 {success_count}/{len(SYMBOLS)} | 失败 {failed_count}")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
