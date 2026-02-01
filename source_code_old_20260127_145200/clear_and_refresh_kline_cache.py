#!/usr/bin/env python3
"""
清除旧K线缓存并重新获取新数据
Clear old K-line cache and fetch fresh data from OKEx API
"""

import sqlite3
import requests
import time
from datetime import datetime, timezone, timedelta

# 配置
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP',
    'SOL-USDT-SWAP', 'DOGE-USDT-SWAP', 'DOT-USDT-SWAP', 'UNI-USDT-SWAP',
    'LINK-USDT-SWAP', 'LTC-USDT-SWAP', 'FIL-USDT-SWAP', 'ETC-USDT-SWAP',
    'TRX-USDT-SWAP', 'APT-USDT-SWAP', 'SUI-USDT-SWAP', 'TAO-USDT-SWAP',
    'AAVE-USDT-SWAP', 'BCH-USDT-SWAP', 'CFX-USDT-SWAP', 'CRO-USDT-SWAP',
    'CRV-USDT-SWAP', 'HBAR-USDT-SWAP', 'LDO-USDT-SWAP', 'NEAR-USDT-SWAP',
    'STX-USDT-SWAP', 'TON-USDT-SWAP', 'XLM-USDT-SWAP'
]

TIMEFRAMES = {
    '5m': {'bar': '5m', 'limit': 300},
    '1H': {'bar': '1H', 'limit': 300}
}

DB_PATH = 'crypto_data.db'
API_BASE = 'https://www.okx.com/api/v5/market/candles'

def clear_kline_tables():
    """清空K线表数据"""
    print("\n" + "=" * 60)
    print("🗑️  清除旧K线缓存")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空5分钟K线表
    cursor.execute("DELETE FROM okex_kline_5m")
    count_5m = cursor.rowcount
    print(f"✅ 已删除 {count_5m} 条 5分钟K线记录")
    
    # 清空1小时K线表
    cursor.execute("DELETE FROM okex_kline_1h")
    count_1h = cursor.rowcount
    print(f"✅ 已删除 {count_1h} 条 1小时K线记录")
    
    conn.commit()
    conn.close()
    
    print(f"📊 总计删除: {count_5m + count_1h} 条记录")
    return count_5m, count_1h

def fetch_kline_from_okex(symbol, bar, limit=300):
    """从OKEx API获取K线数据"""
    url = f"{API_BASE}?instId={symbol}&bar={bar}&limit={limit}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == '0' and 'data' in data:
            return data['data']
        else:
            print(f"❌ API返回错误: {data}")
            return []
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return []

def save_kline_to_db(symbol, timeframe, kline_data):
    """保存K线数据到数据库"""
    table_name = f"okex_kline_{timeframe}"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved_count = 0
    for candle in kline_data:
        try:
            timestamp = int(candle[0])
            open_price = float(candle[1])
            high_price = float(candle[2])
            low_price = float(candle[3])
            close_price = float(candle[4])
            volume = float(candle[5])
            vol_currency = float(candle[6]) if len(candle) > 6 else None
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO {table_name}
                (symbol, timestamp, open, high, low, close, volume, vol_currency, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (symbol, timestamp, open_price, high_price, low_price, 
                  close_price, volume, vol_currency))
            
            saved_count += 1
        except Exception as e:
            print(f"❌ 保存K线失败 [{symbol}]: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    return saved_count

def refresh_kline_data():
    """重新获取K线数据"""
    print("\n" + "=" * 60)
    print("📥 重新获取K线数据")
    print("=" * 60)
    
    total_fetched = 0
    total_saved = 0
    
    for symbol in SYMBOLS:
        print(f"\n📊 处理: {symbol}")
        print("-" * 40)
        
        for tf_key, tf_config in TIMEFRAMES.items():
            bar = tf_config['bar']
            limit = tf_config['limit']
            
            # 从API获取数据
            kline_data = fetch_kline_from_okex(symbol, bar, limit)
            
            if kline_data:
                # 保存到数据库
                saved_count = save_kline_to_db(symbol, tf_key.lower(), kline_data)
                total_fetched += len(kline_data)
                total_saved += saved_count
                
                print(f"  ✅ {tf_key:3} | 获取: {len(kline_data):3}条 | 保存: {saved_count:3}条")
            else:
                print(f"  ❌ {tf_key:3} | 获取失败")
            
            # 避免API限流
            time.sleep(0.2)
    
    print("\n" + "=" * 60)
    print(f"✅ 数据刷新完成!")
    print(f"📊 总计获取: {total_fetched} 条")
    print(f"💾 总计保存: {total_saved} 条")
    print("=" * 60)
    
    return total_fetched, total_saved

def verify_data():
    """验证数据完整性"""
    print("\n" + "=" * 60)
    print("🔍 数据验证")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查5分钟K线
    print("\n5分钟K线数据:")
    print("-" * 60)
    cursor.execute("""
        SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp)
        FROM okex_kline_5m
        GROUP BY symbol
        ORDER BY symbol
    """)
    
    for symbol, count, min_ts, max_ts in cursor.fetchall():
        min_time = datetime.fromtimestamp(min_ts/1000, tz=timezone(timedelta(hours=8)))
        max_time = datetime.fromtimestamp(max_ts/1000, tz=timezone(timedelta(hours=8)))
        print(f"{symbol:20} | {count:3}条 | {min_time.strftime('%Y-%m-%d %H:%M')} ~ {max_time.strftime('%Y-%m-%d %H:%M')}")
    
    # 检查1小时K线
    print("\n1小时K线数据:")
    print("-" * 60)
    cursor.execute("""
        SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp)
        FROM okex_kline_1h
        GROUP BY symbol
        ORDER BY symbol
    """)
    
    for symbol, count, min_ts, max_ts in cursor.fetchall():
        min_time = datetime.fromtimestamp(min_ts/1000, tz=timezone(timedelta(hours=8)))
        max_time = datetime.fromtimestamp(max_ts/1000, tz=timezone(timedelta(hours=8)))
        print(f"{symbol:20} | {count:3}条 | {min_time.strftime('%Y-%m-%d %H:%M')} ~ {max_time.strftime('%Y-%m-%d %H:%M')}")
    
    conn.close()
    print("=" * 60)

def main():
    """主函数"""
    print("\n" + "🔄 " * 15)
    print("K线缓存清理与刷新工具")
    print("=" * 60)
    print(f"⏰ 执行时间: {datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print("=" * 60)
    
    # 步骤1: 清除旧数据
    clear_kline_tables()
    
    # 步骤2: 获取新数据
    refresh_kline_data()
    
    # 步骤3: 验证数据
    verify_data()
    
    print("\n✅ 所有操作完成!")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
