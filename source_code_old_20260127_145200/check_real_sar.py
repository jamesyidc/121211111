import sqlite3
from datetime import datetime

conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()

# 获取FIL最新的K线和指标数据
cursor.execute("""
    SELECT k.timestamp, k.close, i.sar, i.sar_position
    FROM okex_kline_5m k
    LEFT JOIN (
        SELECT symbol, timeframe, sar, sar_position, record_time
        FROM okex_technical_indicators
        WHERE symbol = 'FIL-USDT-SWAP' AND timeframe = '5m'
    ) i ON k.symbol = i.symbol
    WHERE k.symbol = 'FIL-USDT-SWAP'
    ORDER BY k.timestamp DESC
    LIMIT 20
""")

print("FIL K线与SAR对比（最新20条）:")
print("="*80)
print(f"{'时间':<20} {'收盘价':<10} {'SAR值':<10} {'SAR位置':<10}")
print("-"*80)

for row in cursor.fetchall():
    ts = datetime.fromtimestamp(row[0]/1000) if row[0] else None
    close = row[1]
    sar = row[2] if row[2] else 'N/A'
    sar_pos = row[3] if row[3] else 'N/A'
    
    print(f"{ts} {close:<10.4f} {sar if sar == 'N/A' else f'{sar:<10.4f}'} {sar_pos}")

conn.close()
