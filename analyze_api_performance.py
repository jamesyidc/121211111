#!/usr/bin/env python3
"""
检查所有首页API的响应大小和时间
找出需要在服务器端优化的API
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

apis = [
    '/api/depth-scores?timeframe=24&limit=50',
    '/api/fear-greed/latest',
    '/api/gdrive-detector/status',
    '/api/gdrive-detector/txt-files',
    '/api/kline-indicators/collector-status',
    '/api/market-average-score?timeframe=24',
    '/api/modules/stats',
    '/api/monitor/status',
    '/api/okex-crypto-index',
    '/api/opening-logic/suggestion',
    '/api/position/summary',
    '/api/price-comparison/breakthrough-stats',
    '/api/price-speed/latest',
    '/api/star-system/data',
    '/api/stats',
    '/api/support-resistance/latest',
    '/api/trading-signals/analyze',
    '/api/trading/positions/opens',
    '/api/v1v2/latest',
]

print("=" * 80)
print("首页API性能分析")
print("=" * 80)
print(f"{'API路径':<50} {'状态':<8} {'大小':<12} {'时间':<10}")
print("-" * 80)

results = []

for api in sorted(apis):
    try:
        start = time.time()
        response = requests.get(BASE_URL + api, timeout=5)
        elapsed = time.time() - start
        
        size = len(response.content)
        status = response.status_code
        
        # 尝试解析JSON并分析结构
        try:
            data = response.json()
            data_type = "JSON"
            
            # 检查是否返回大量数据
            if isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], list):
                    data_count = len(data['data'])
                    data_type = f"JSON ({data_count} items)"
                elif 'coins' in data and isinstance(data['coins'], list):
                    data_count = len(data['coins'])
                    data_type = f"JSON ({data_count} coins)"
        except:
            data_type = "HTML/TEXT"
        
        results.append({
            'api': api,
            'status': status,
            'size': size,
            'time': elapsed,
            'type': data_type
        })
        
        # 标记慢速或大数据API
        marker = ""
        if elapsed > 0.5:
            marker = "🐌 SLOW"
        elif size > 50000:
            marker = "📦 LARGE"
        elif size > 10000:
            marker = "📄 BIG"
        
        print(f"{api:<50} {status:<8} {size:>8}B    {elapsed:>6.3f}s  {marker}")
        
    except Exception as e:
        print(f"{api:<50} ERROR    {str(e)[:30]}")
        results.append({
            'api': api,
            'status': 'ERROR',
            'size': 0,
            'time': 0,
            'type': str(e)
        })

print("=" * 80)
print("\n📊 统计摘要:")
print(f"总API数: {len(apis)}")
print(f"正常响应: {sum(1 for r in results if r['status'] == 200)}")
print(f"错误响应: {sum(1 for r in results if r['status'] != 200 and r['status'] != 'ERROR')}")
print(f"请求失败: {sum(1 for r in results if r['status'] == 'ERROR')}")

# 找出最慢的API
slow_apis = sorted([r for r in results if isinstance(r['time'], float) and r['time'] > 0.1], 
                   key=lambda x: x['time'], reverse=True)[:5]
if slow_apis:
    print("\n🐌 最慢的5个API:")
    for r in slow_apis:
        print(f"  {r['api']}: {r['time']:.3f}s")

# 找出最大的API
large_apis = sorted([r for r in results if isinstance(r['size'], int) and r['size'] > 1000], 
                    key=lambda x: x['size'], reverse=True)[:5]
if large_apis:
    print("\n📦 数据量最大的5个API:")
    for r in large_apis:
        print(f"  {r['api']}: {r['size']/1024:.1f} KB")

print("\n✅ 分析完成！")
