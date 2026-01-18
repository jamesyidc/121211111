import sqlite3
from datetime import datetime

conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()

symbol = 'FIL-USDT-SWAP'

print(f"Checking FIL data in database...")
print("=" * 60)

# Check 5m kline data
cursor.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM okex_kline_5m WHERE symbol = ?", (symbol,))
row = cursor.fetchone()
count_5m = row[0]
min_ts = row[1]
max_ts = row[2]

print(f"\n1. okex_kline_5m (FIL-USDT-SWAP):")
print(f"   Total records: {count_5m}")
if min_ts and max_ts:
    print(f"   Time range: {datetime.fromtimestamp(min_ts/1000)} to {datetime.fromtimestamp(max_ts/1000)}")
    days = (max_ts - min_ts) / (1000 * 60 * 60 * 24)
    print(f"   Days covered: {days:.2f}")

# Check indicators data
cursor.execute("SELECT COUNT(*), MIN(record_time), MAX(record_time) FROM okex_technical_indicators WHERE symbol = ? AND timeframe = '5m'", (symbol,))
row = cursor.fetchone()
count_ind = row[0]

print(f"\n2. okex_technical_indicators (FIL-USDT-SWAP, 5m):")
print(f"   Total records: {count_ind}")
if row[1] and row[2]:
    print(f"   Time range: {row[1]} to {row[2]}")

print(f"\n3. Data Comparison:")
print(f"   Kline records: {count_5m}")
print(f"   Indicator records: {count_ind}")
print(f"   Difference: {abs(count_5m - count_ind)}")

if count_5m == 1440:
    print(f"\n⚠️  Kline data is only 1440 records (5 days), not 2880 (10 days)!")
    print(f"   This is why the API returns 1440 instead of 2880.")

conn.close()
print("=" * 60)
