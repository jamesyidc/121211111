#!/usr/bin/env python3
"""
导入OKEx历史K线数据到数据库
支持5分钟和1小时K线，回溯10天
"""
import requests
import sqlite3
import time
from datetime import datetime, timedelta
import json

# OKEx API配置
OKEX_API_BASE = "https://www.okx.com"

# 交易对列表
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP', 'XRP-USDT-SWAP',
    'BNB-USDT-SWAP', 'DOGE-USDT-SWAP', 'ADA-USDT-SWAP', 'MATIC-USDT-SWAP',
    'DOT-USDT-SWAP', 'LTC-USDT-SWAP', 'UNI-USDT-SWAP', 'LINK-USDT-SWAP',
    'AAVE-USDT-SWAP', 'APT-USDT-SWAP', 'SUI-USDT-SWAP', 'NEAR-USDT-SWAP',
    'FIL-USDT-SWAP', 'HBAR-USDT-SWAP', 'RENDER-USDT-SWAP', 'TRX-USDT-SWAP',
    'SHIB-USDT-SWAP', 'BCH-USDT-SWAP', 'CRV-USDT-SWAP', 'LDO-USDT-SWAP',
    'ETC-USDT-SWAP', 'ORDI-USDT-SWAP', 'ONDO-USDT-SWAP'
]

def fetch_okex_klines(symbol, bar='5m', days=10):
    """
    从OKEx获取历史K线数据
    
    Args:
        symbol: 交易对，如 BTC-USDT-SWAP
        bar: K线周期，5m或1H
        days: 回溯天数
    
    Returns:
        list: K线数据列表
    """
    endpoint = f"{OKEX_API_BASE}/api/v5/market/candles"
    
    # 计算时间范围（毫秒时间戳）
    end_time = int(time.time() * 1000)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)
    
    all_klines = []
    current_before = end_time
    
    print(f"  获取 {symbol} {bar} K线数据...")
    
    while True:
        params = {
            'instId': symbol,
            'bar': bar,
            'before': str(current_before),
            'limit': '300'  # 每次最多300根K线
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            data = response.json()
            
            if data['code'] != '0':
                print(f"    ⚠️ API错误: {data.get('msg')}")
                break
            
            klines = data.get('data', [])
            if not klines:
                break
            
            # 过滤出时间范围内的K线
            valid_klines = [k for k in klines if int(k[0]) >= start_time]
            all_klines.extend(valid_klines)
            
            # 如果已经获取到开始时间之前的数据，停止
            if int(klines[-1][0]) < start_time:
                break
            
            # 更新before参数为最后一根K线的时间
            current_before = klines[-1][0]
            
            # 避免请求过快
            time.sleep(0.2)
            
            print(f"    已获取 {len(all_klines)} 根K线...")
            
            # 安全限制：最多获取3000根K线
            if len(all_klines) >= 3000:
                break
                
        except Exception as e:
            print(f"    ❌ 请求失败: {e}")
            break
    
    print(f"    ✅ 完成，共 {len(all_klines)} 根K线")
    return all_klines

def import_klines_to_db(symbol, klines, timeframe):
    """
    将K线数据导入数据库
    
    Args:
        symbol: 交易对
        klines: K线数据列表
        timeframe: 时间周期 (5m 或 1H)
    """
    if not klines:
        return 0
    
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    
    for kline in klines:
        try:
            # OKEx K线数据格式：[ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            timestamp_ms = int(kline[0])
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5])
            
            # 转换时间戳为datetime
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            record_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # 使用收盘价作为当前价格
            current_price = close_price
            
            # 检查是否已存在
            cursor.execute('''
                SELECT id FROM okex_technical_indicators
                WHERE symbol = ? AND timeframe = ? AND record_time = ?
            ''', (symbol, timeframe, record_time))
            
            if cursor.fetchone():
                skipped += 1
                continue
            
            # 插入数据（只插入价格，指标留空，后续由收集器更新）
            cursor.execute('''
                INSERT INTO okex_technical_indicators
                (symbol, timeframe, current_price, record_time)
                VALUES (?, ?, ?, ?)
            ''', (symbol, timeframe, current_price, record_time))
            
            imported += 1
            
        except Exception as e:
            print(f"    ⚠️ 导入失败: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    return imported

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 开始导入历史K线数据")
    print("=" * 60)
    
    total_imported = 0
    
    # 只导入BTC作为测试
    test_symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
    
    for symbol in test_symbols:
        print(f"\n📊 处理 {symbol}")
        
        # 导入5分钟K线
        print("  [5分钟K线]")
        klines_5m = fetch_okex_klines(symbol, bar='5m', days=10)
        imported_5m = import_klines_to_db(symbol, klines_5m, '5m')
        print(f"    ✅ 导入 {imported_5m} 条记录")
        total_imported += imported_5m
        
        time.sleep(1)
        
        # 导入1小时K线
        print("  [1小时K线]")
        klines_1h = fetch_okex_klines(symbol, bar='1H', days=10)
        imported_1h = import_klines_to_db(symbol, klines_1h, '1H')
        print(f"    ✅ 导入 {imported_1h} 条记录")
        total_imported += imported_1h
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print(f"✅ 导入完成！总计导入 {total_imported} 条K线数据")
    print("=" * 60)

if __name__ == '__main__':
    main()
