import requests
import json

# Test both kline and indicators APIs for FIL
symbol = "FIL"
base_url = "http://localhost:5000"

print("Testing FIL APIs...")
print("=" * 50)

# Test kline API
kline_url = f"{base_url}/api/symbol/{symbol}/kline?timeframe=5m"
print(f"\n1. Testing Kline API: {kline_url}")
try:
    kline_resp = requests.get(kline_url, timeout=10)
    kline_data = kline_resp.json()
    print(f"   Status: {kline_resp.status_code}")
    print(f"   Success: {kline_data.get('success')}")
    print(f"   Data length: {len(kline_data.get('data', []))}")
    if kline_data.get('data'):
        print(f"   First timestamp: {kline_data['data'][0].get('timestamp')}")
        print(f"   Last timestamp: {kline_data['data'][-1].get('timestamp')}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test indicators API
indicators_url = f"{base_url}/api/symbol/{symbol}/indicators?timeframe=5m"
print(f"\n2. Testing Indicators API: {indicators_url}")
try:
    indicators_resp = requests.get(indicators_url, timeout=10)
    indicators_data = indicators_resp.json()
    print(f"   Status: {indicators_resp.status_code}")
    print(f"   Success: {indicators_data.get('success')}")
    print(f"   Data length: {len(indicators_data.get('data', []))}")
    if indicators_data.get('data'):
        print(f"   First timestamp: {indicators_data['data'][0].get('timestamp')}")
        print(f"   Last timestamp: {indicators_data['data'][-1].get('timestamp')}")
except Exception as e:
    print(f"   ERROR: {e}")

# Check data alignment
print(f"\n3. Data Alignment Check:")
if kline_data.get('data') and indicators_data.get('data'):
    kline_len = len(kline_data['data'])
    indicators_len = len(indicators_data['data'])
    print(f"   Kline records: {kline_len}")
    print(f"   Indicators records: {indicators_len}")
    print(f"   Match: {kline_len == indicators_len}")
    if kline_len != indicators_len:
        print(f"   ⚠️  LENGTH MISMATCH! Difference: {abs(kline_len - indicators_len)}")
else:
    print(f"   ⚠️  Cannot check alignment - missing data")

print("=" * 50)
