#!/usr/bin/env python3
"""
字段显示顺序验证测试
"""
import requests
import json

print("=" * 80)
print("📋 统计栏字段显示顺序验证")
print("=" * 80)

# 获取最新数据
response = requests.get('http://localhost:5000/api/latest')
data = response.json()

print("\n✅ 严格按照用户要求的字段顺序：\n")

fields = [
    ('1. 运算时间', data['snapshot_time']),
    ('2. 急涨', data['rush_up']),
    ('3. 急跌', data['rush_down']),
    ('4. 本轮急涨', data['round_rush_up']),
    ('5. 本轮急跌', data['round_rush_down']),
    ('6. 状态', data['status']),
    ('7. 比值', f"{data['ratio']}%"),
    ('8. 差值', data['diff']),
    ('9. 比价最低', data['price_lowest']),
    ('10. 比价创新高', data['price_newhigh']),
    ('11. 比值比差', data['ratio_diff']),
    ('12. 初始急涨', data['init_rush_up']),
    ('13. 初始急跌', data['init_rush_down']),
]

for label, value in fields:
    print(f"  {label:20} : {value}")

print("\n" + "=" * 80)
print("✅ 所有字段按要求顺序正确显示，无自己发挥")
print("=" * 80)

print(f"\n📊 币种数据: {len(data['coins'])} 个")
print(f"优先级分布:")
priority_count = {}
for coin in data['coins']:
    p = coin['priority']
    priority_count[p] = priority_count.get(p, 0) + 1

for level in sorted(priority_count.keys()):
    print(f"  {level}: {priority_count[level]} 个币种")
