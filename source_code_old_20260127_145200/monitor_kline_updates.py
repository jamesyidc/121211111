#!/usr/bin/env python3
"""监控K线数据更新"""
import sqlite3
import time
from datetime import datetime

def check_latest_kline():
    db = sqlite3.connect('crypto_data.db')
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT symbol, timestamp, close, created_at
        FROM okex_kline_ohlc
        WHERE timeframe = '5m'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    print(f"\n{'='*80}")
    print(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    print("\n🔍 最新5条K线数据:\n")
    
    for row in cursor.fetchall():
        symbol, ts, close, created_at = row
        dt = datetime.fromtimestamp(ts/1000)
        age = (datetime.now() - datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')).total_seconds() / 60
        status = "🟢 新" if age < 10 else "🔴 旧"
        print(f"  {status} {symbol:20s} | ${close:10.4f} | K线:{dt.strftime('%H:%M')} | 导入:{created_at} | {age:.1f}分钟前")
    
    db.close()

if __name__ == "__main__":
    while True:
        check_latest_kline()
        time.sleep(60)  # 每分钟检查一次
