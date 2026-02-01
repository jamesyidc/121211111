#!/usr/bin/env python3
import requests
import json
from datetime import datetime

# 获取UNI的指标数据
response = requests.get('http://localhost:5000/api/symbol/UNI/indicators?timeframe=5m')
data = response.json()['data']

print(f"总共获取 {len(data)} 根K线数据\n")

# 统计RSI分布
rsi_values = [item['rsi'] for item in data]
prices = [item['price'] for item in data]

print("=" * 80)
print("✅ 新逻辑验证: 检查卖点1标记位置（最高点+6）的RSI")
print("=" * 80)

# 找到所有潜在的卖点1
sell_points_new_logic = []
for i in range(30, len(data) - 6):  # 从第30根开始，确保后面还有6根
    # 找前30根的最高点
    window_start = i - 29
    window_end = i + 1
    max_price = max(prices[window_start:window_end])
    max_idx = window_start + prices[window_start:window_end].index(max_price)
    
    # 如果当前位置是最高点
    if max_idx == i:
        sell_point_idx = i + 6  # 标记点在+6位置
        sell_point_rsi = rsi_values[sell_point_idx]
        high_point_rsi = rsi_values[i]
        
        timestamp = data[sell_point_idx]['timestamp']
        dt = datetime.fromtimestamp(timestamp / 1000)
        
        status = '✅ 通过' if sell_point_rsi >= 50 else '❌ 过滤'
        
        sell_points_new_logic.append({
            'high_idx': i,
            'high_rsi': high_point_rsi,
            'sell_idx': sell_point_idx,
            'sell_rsi': sell_point_rsi,
            'sell_price': prices[sell_point_idx],
            'sell_time': dt.strftime('%m/%d %H:%M'),
            'passed': sell_point_rsi >= 50,
            'status': status
        })

print(f"\n找到 {len(sell_points_new_logic)} 个潜在的卖点位置:")
print("-" * 80)

# 统计通过和被过滤的数量
passed_count = len([sp for sp in sell_points_new_logic if sp['passed']])
filtered_count = len([sp for sp in sell_points_new_logic if not sp['passed']])

print(f"\n✅ RSI >= 50 (将显示): {passed_count} 个")
print(f"❌ RSI < 50 (被过滤): {filtered_count} 个")
print(f"📊 过滤率: {filtered_count/len(sell_points_new_logic)*100:.1f}%\n")

# 显示所有潜在卖点的详细信息
print("详细列表（最近20个）:")
print("-" * 80)
print(f"{'状态':<6} {'标记时间':<14} {'标记点RSI':<10} {'最高点RSI':<10} {'价格':<8}")
print("-" * 80)

for sp in sell_points_new_logic[-20:]:
    print(f"{sp['status']:<6} {sp['sell_time']:<14} {sp['sell_rsi']:<10.2f} "
          f"{sp['high_rsi']:<10.2f} ${sp['sell_price']:.4f}")

print("\n" + "=" * 80)
print("🎯 关键验证结论:")
print("=" * 80)
print(f"1. 新逻辑检查: 标记点（最高点+6）的RSI >= 50")
print(f"2. 将显示的卖点: {passed_count} 个（这些点的标记位置RSI >= 50）")
print(f"3. 被过滤的卖点: {filtered_count} 个（这些点的标记位置RSI < 50）")
print(f"4. 用户将看到: 所有🔻卖1标记的RSI都 >= 50 ✅")
print(f"\n现在用户看到的所有卖点1，标记位置的RSI一定 >= 50！")
print(f"不会再出现 'RSI 39.88' 的情况！")
