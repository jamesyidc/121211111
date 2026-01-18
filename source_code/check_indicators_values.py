import requests

resp = requests.get("http://localhost:5000/api/symbol/FIL/indicators?timeframe=5m")
data = resp.json()

if data['success']:
    indicators = data['data']
    print(f"Total indicators: {len(indicators)}")
    print(f"\nChecking data validity:")
    
    # Check last 5 records
    valid_sar = 0
    valid_bb = 0
    null_sar = 0
    null_bb = 0
    
    for item in indicators[-144:]:  # Last 144 records
        if item.get('sar') is not None:
            valid_sar += 1
        else:
            null_sar += 1
            
        if item.get('bb_upper') is not None and item.get('bb_middle') is not None and item.get('bb_lower') is not None:
            valid_bb += 1
        else:
            null_bb += 1
    
    print(f"\nLast 144 records:")
    print(f"  Valid SAR: {valid_sar}")
    print(f"  Null SAR: {null_sar}")
    print(f"  Valid Bollinger: {valid_bb}")
    print(f"  Null Bollinger: {null_bb}")
    
    print(f"\nSample data (last 3 records):")
    for i, item in enumerate(indicators[-3:]):
        print(f"\nRecord {i+1}:")
        print(f"  timestamp: {item.get('timestamp')}")
        print(f"  price: {item.get('price')}")
        print(f"  sar: {item.get('sar')}")
        print(f"  bb_upper: {item.get('bb_upper')}")
        print(f"  bb_middle: {item.get('bb_middle')}")
        print(f"  bb_lower: {item.get('bb_lower')}")
else:
    print("Failed to get data")
