import requests
import json

# Test query API
response = requests.get('http://localhost:5000/api/query?time=2025-12-06 14:48')
data = response.json()

if 'error' in data:
    print(f"错误: {data['error']}")
else:
    print("✅ 查询成功！")
    print(f"时间: {data['snapshot_time']}")
    print(f"急涨: {data['rush_up']}, 急跌: {data['rush_down']}, 差值: {data['diff']}, 计次: {data['count']}")
    print(f"状态: {data['status']}")
    print(f"币种数量: {len(data['coins'])}")
    
    print("\n特别关注 (等级2):")
    for coin in data['coins']:
        if '等级2' in coin['priority']:
            print(f"  {coin['symbol']}: {coin['priority']}")
            print(f"    涨跌: {coin['change']:.2f}%")
            print(f"    最高占比: {coin['ratio1']}, 最低占比: {coin['ratio2']}")
            print(f"    当前价格: ${coin['current_price']:.2f}")
