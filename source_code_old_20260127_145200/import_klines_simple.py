#!/usr/bin/env python3
"""简化版历史K线导入 - 直接获取最近10天数据"""
import requests
import sqlite3
import time
from datetime import datetime

def fetch_and_import_klines(symbol, bar, target_count):
    """
    获取并导入K线数据
    
    Args:
        symbol: 交易对
        bar: K线周期（5m或1H）
        target_count: 目标K线数量
    """
    url = "https://www.okx.com/api/v5/market/candles"
    all_klines = []
    after_ts = None
    
    print(f"  获取 {symbol} {bar} K线...")
    
    # 批量获取数据
    while len(all_klines) < target_count:
        params = {
            'instId': symbol,
            'bar': bar,
            'limit': '300'
        }
        
        if after_ts:
            params['after'] = after_ts
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data['code'] != '0' or not data.get('data'):
                break
            
            klines = data['data']
            all_klines.extend(klines)
            
            # 更新after为当前批次最旧的时间戳
            after_ts = klines[-1][0]
            
            print(f"    已获取 {len(all_klines)} 根...")
            
            if len(klines) < 300:  # 没有更多数据了
                break
            
            time.sleep(0.2)  # 避免请求过快
            
        except Exception as e:
            print(f"    ❌ 错误: {e}")
            break
    
    # 只保留目标数量
    all_klines = all_klines[:target_count]
    
    # 导入数据库
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    imported = 0
    for kline in all_klines:
        try:
            timestamp_ms = int(kline[0])
            close_price = float(kline[4])
            
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            record_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # 检查是否已存在
            cursor.execute('''
                SELECT id FROM okex_technical_indicators
                WHERE symbol = ? AND timeframe = ? AND record_time = ?
            ''', (symbol, bar, record_time))
            
            if cursor.fetchone():
                continue
            
            # 插入数据
            cursor.execute('''
                INSERT INTO okex_technical_indicators
                (symbol, timeframe, current_price, record_time)
                VALUES (?, ?, ?, ?)
            ''', (symbol, bar, close_price, record_time))
            
            imported += 1
            
        except Exception as e:
            continue
    
    conn.commit()
    conn.close()
    
    print(f"    ✅ 导入 {imported}/{len(all_klines)} 条记录")
    return imported

def main():
    print("=" * 60)
    print("🚀 导入历史K线数据（10天）")
    print("=" * 60)
    
    # 导入BTC、ETH、SOL
    symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
    
    total_imported = 0
    
    for symbol in symbols:
        print(f"\n📊 {symbol}")
        
        # 5分钟K线：10天 = 2880根
        imported_5m = fetch_and_import_klines(symbol, '5m', 2880)
        total_imported += imported_5m
        
        time.sleep(1)
        
        # 1小时K线：10天 = 240根  
        imported_1h = fetch_and_import_klines(symbol, '1H', 240)
        total_imported += imported_1h
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print(f"✅ 总计导入 {total_imported} 条K线数据")
    print("=" * 60)

if __name__ == '__main__':
    main()
