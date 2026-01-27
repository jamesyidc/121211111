import requests

resp = requests.get("http://localhost:5000/api/symbol/FIL/indicators?timeframe=5m")
data = resp.json()

print(f"Success: {data['success']}")
print(f"Data length: {len(data['data'])}")
print(f"\nFirst 3 records:")
for i, record in enumerate(data['data'][:3]):
    print(f"{i+1}. {record}")
print(f"\nLast 3 records:")
for i, record in enumerate(data['data'][-3:]):
    print(f"{len(data['data'])-2+i}. {record}")
