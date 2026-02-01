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
rsi_above_50 = [r for r in rsi_values if r >= 50]
rsi_below_50 = [r for r in rsi_values if r < 50]

print("=" * 80)
print("RSI 统计:")
print("=" * 80)
print(f"RSI >= 50: {len(rsi_above_50)} 个 ({len(rsi_above_50)/len(rsi_values)*100:.1f}%)")
print(f"RSI < 50:  {len(rsi_below_50)} 个 ({len(rsi_below_50)/len(rsi_values)*100:.1f}%)")
print(f"RSI 范围:  {min(rsi_values):.2f} ~ {max(rsi_values):.2f}")
print(f"RSI 平均:  {sum(rsi_values)/len(rsi_values):.2f}")

# 找到所有RSI >= 50的高点（相对于前后30根）
print("\n" + "=" * 80)
print("分析潜在的卖点1（需要RSI >= 50的相对高点）:")
print("=" * 80)

# 获取价格数据
prices = [item['price'] for item in data]

potential_sell_points = []
for i in range(30, len(data) - 6):  # 从第30根开始，确保后面还有6根
    # 找前30根的最高点
    window_start = i - 29
    window_end = i + 1
    max_high_in_window = max(prices[window_start:window_end])
    max_high_idx_in_window = window_start + prices[window_start:window_end].index(max_high_in_window)
    
    # 如果当前位置是最高点
    if max_high_idx_in_window == i:
        rsi_at_high = rsi_values[i]
        timestamp = data[i]['timestamp']
        dt = datetime.fromtimestamp(timestamp / 1000)
        
        if rsi_at_high >= 50:
            # 检查后面6根K线的RSI
            future_rsis = rsi_values[i+1:i+7]
            sell_point_idx = i + 6
            sell_point_rsi = rsi_values[sell_point_idx]
            
            potential_sell_points.append({
                'high_idx': i,
                'high_price': prices[i],
                'high_rsi': rsi_at_high,
                'high_time': dt.strftime('%m/%d %H:%M'),
                'sell_idx': sell_point_idx,
                'sell_rsi': sell_point_rsi,
                'future_rsis': future_rsis
            })

print(f"\n找到 {len(potential_sell_points)} 个符合RSI >= 50条件的相对高点:")
print("-" * 80)

if potential_sell_points:
    for idx, point in enumerate(potential_sell_points[:10], 1):  # 只显示前10个
        print(f"\n{idx}. 最高点位置: #{point['high_idx']}")
        print(f"   时间: {point['high_time']}")
        print(f"   价格: ${point['high_price']:.4f}")
        print(f"   最高点RSI: {point['high_rsi']:.2f}")
        print(f"   标记点(+6)RSI: {point['sell_rsi']:.2f}")
        print(f"   后续6根RSI: {', '.join([f'{r:.1f}' for r in point['future_rsis']])}")
else:
    print("\n⚠️ 在当前数据中未找到符合条件的卖点！")
    print("   这说明UNI当前处于弱势，大部分高点的RSI都 < 50")

# 分析最近的价格高点情况
print("\n" + "=" * 80)
print("最近10个相对高点的RSI情况（不管是否 >= 50）:")
print("=" * 80)

recent_highs = []
for i in range(30, len(data) - 6):
    window_start = i - 29
    window_end = i + 1
    max_high_in_window = max(prices[window_start:window_end])
    max_high_idx_in_window = window_start + prices[window_start:window_end].index(max_high_in_window)
    
    if max_high_idx_in_window == i:
        rsi_at_high = rsi_values[i]
        timestamp = data[i]['timestamp']
        dt = datetime.fromtimestamp(timestamp / 1000)
        recent_highs.append({
            'idx': i,
            'price': prices[i],
            'rsi': rsi_at_high,
            'time': dt.strftime('%m/%d %H:%M'),
            'passed': '✅' if rsi_at_high >= 50 else '❌'
        })

# 显示最后10个
for high in recent_highs[-10:]:
    print(f"{high['passed']} 位置#{high['idx']:<4} {high['time']} "
          f"价格:${high['price']:.4f} RSI:{high['rsi']:5.2f}")

print("\n" + "=" * 80)
print("结论:")
print("=" * 80)
print(f"在最近{len(recent_highs)}个相对高点中:")
passed = len([h for h in recent_highs if h['rsi'] >= 50])
failed = len([h for h in recent_highs if h['rsi'] < 50])
print(f"  - RSI >= 50 (通过过滤): {passed} 个 ({passed/len(recent_highs)*100:.1f}%)")
print(f"  - RSI < 50 (被过滤):   {failed} 个 ({failed/len(recent_highs)*100:.1f}%)")
print(f"\nRSI >= 50 过滤器正在工作，过滤掉了 {failed/len(recent_highs)*100:.1f}% 的弱势高点！")
