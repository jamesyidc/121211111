import requests

# Get kline data
kline_resp = requests.get("http://localhost:5000/api/symbol/FIL/kline?timeframe=5m")
kline_data = kline_resp.json()

# Get indicators data  
ind_resp = requests.get("http://localhost:5000/api/symbol/FIL/indicators?timeframe=5m")
ind_data = ind_resp.json()

# Get last 144 records
klines = kline_data['data'][-144:]
indicators = ind_data['data'][-144:]

# Check price ranges
kline_prices = []
for k in klines:
    kline_prices.extend(k['data'])  # OHLC values

ind_prices = [i['price'] for i in indicators if i['price']]
sar_values = [i['sar'] for i in indicators if i['sar']]
bb_upper = [i['bb_upper'] for i in indicators if i['bb_upper']]
bb_lower = [i['bb_lower'] for i in indicators if i['bb_lower']]

print("Price Ranges (Last 144 records):")
print(f"K-line OHLC: {min(kline_prices):.4f} - {max(kline_prices):.4f}")
print(f"Indicator Price: {min(ind_prices):.4f} - {max(ind_prices):.4f}")
print(f"SAR: {min(sar_values):.4f} - {max(sar_values):.4f}")
print(f"BB Upper: {min(bb_upper):.4f} - {max(bb_upper):.4f}")
print(f"BB Lower: {min(bb_lower):.4f} - {max(bb_lower):.4f}")

print(f"\nFirst 3 K-lines timestamps:")
for k in klines[:3]:
    print(f"  {k['timestamp']}: OHLC = {k['data']}")

print(f"\nFirst 3 Indicators timestamps:")
for i in indicators[:3]:
    print(f"  {i['timestamp']}: price={i['price']}, sar={i['sar']:.4f}, bb_upper={i['bb_upper']:.4f}")
