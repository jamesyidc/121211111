import requests
import json

print("=" * 80)
print("测试所有前端状态API")
print("=" * 80)

base_url = "http://localhost:5000"

apis = [
    {
        "name": "决策K线指标系统",
        "url": f"{base_url}/api/kline-indicators/collector-status"
    },
    {
        "name": "支撑阻力快照",
        "url": f"{base_url}/api/support-resistance/snapshots?all=true"
    },
    {
        "name": "交易信号监控",
        "url": f"{base_url}/api/trading-signals/latest"
    },
    {
        "name": "Panic Wash指数",
        "url": f"{base_url}/api/panic-wash/latest"
    },
    {
        "name": "Google Drive监控",
        "url": f"{base_url}/api/crypto/snapshots/latest"
    }
]

for api in apis:
    print(f"\n{'='*60}")
    print(f"测试: {api['name']}")
    print(f"URL: {api['url']}")
    print('-' * 60)
    try:
        response = requests.get(api['url'], timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 状态码: {response.status_code}")
            
            # 根据不同API显示关键信息
            if 'status' in data:
                print(f"  系统状态: {data['status']}")
            if 'minutes_since_last' in data:
                print(f"  数据延迟: {data['minutes_since_last']:.1f} 分钟")
            if 'last_collection_time' in data:
                print(f"  最后采集: {data['last_collection_time']}")
            if 'data' in data and isinstance(data['data'], dict):
                if 'record_time' in data['data']:
                    print(f"  记录时间: {data['data']['record_time']}")
                if 'panic_index' in data['data']:
                    print(f"  恐慌指数: {data['data']['panic_index']}")
                if 'snapshot_time' in data['data']:
                    print(f"  快照时间: {data['data']['snapshot_time']}")
            
            # 显示部分响应数据
            print(f"  响应数据: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
        else:
            print(f"✗ 状态码: {response.status_code}")
            print(f"  响应: {response.text[:200]}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
