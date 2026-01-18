#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试空单统计逻辑修复
验证：
1. 空单盈利≤20% 只统计盈利>0的
2. 空单盈利≤10% 只统计盈利>0的  
3. 空单亏损 统计profit_rate<0的
"""

import sqlite3
from datetime import datetime

print("=" * 80)
print("🔍 测试空单统计逻辑修复")
print("=" * 80)

# 连接数据库
conn = sqlite3.connect('/home/user/webapp/anchor_system.db')
cursor = conn.cursor()

# 查询所有空单
cursor.execute("""
SELECT inst_id, pos_side, profit_rate, pos_size
FROM anchor_profit_records
WHERE pos_side = 'short'
ORDER BY profit_rate DESC
""")

positions = cursor.fetchall()

print(f"\n📊 总空单数量: {len(positions)}")
print("-" * 80)

# 按照修复后的逻辑统计
profit_above_70 = [p for p in positions if p[2] >= 70]
profit_above_60 = [p for p in positions if p[2] >= 60]
profit_above_50 = [p for p in positions if p[2] >= 50]
profit_above_40 = [p for p in positions if p[2] >= 40]

# 修复后的逻辑：只统计盈利>0的
profit_below_20 = [p for p in positions if 0 < p[2] <= 20]
profit_below_10 = [p for p in positions if 0 < p[2] <= 10]

# 亏损统计
loss_positions = [p for p in positions if p[2] < 0]
loss_below_10 = [p for p in positions if p[2] <= -10]

print("\n📈 高盈利统计：")
print(f"  空单盈利≥70%: {len(profit_above_70)} 个")
print(f"  空单盈利≥60%: {len(profit_above_60)} 个")
print(f"  空单盈利≥50%: {len(profit_above_50)} 个")
print(f"  空单盈利≥40%: {len(profit_above_40)} 个")

print("\n📉 低盈利统计 (修复后)：")
print(f"  空单盈利≤20% (且>0): {len(profit_below_20)} 个")
if profit_below_20:
    print(f"    盈利率范围: {min([p[2] for p in profit_below_20]):.2f}% ~ {max([p[2] for p in profit_below_20]):.2f}%")
    
print(f"  空单盈利≤10% (且>0): {len(profit_below_10)} 个")
if profit_below_10:
    print(f"    盈利率范围: {min([p[2] for p in profit_below_10]):.2f}% ~ {max([p[2] for p in profit_below_10]):.2f}%")

print("\n💸 亏损统计：")
print(f"  空单亏损 (<0): {len(loss_positions)} 个")
if loss_positions:
    print(f"    亏损范围: {min([p[2] for p in loss_positions]):.2f}% ~ {max([p[2] for p in loss_positions]):.2f}%")
    
print(f"  空单亏损≤-10%: {len(loss_below_10)} 个")

# 检查多头行情触发条件
print("\n" + "=" * 80)
print("🎯 多头行情触发条件检查：")
print("=" * 80)

conditions = [
    ("空单盈利≤20% (且>0) 的数量 ≥ 8", len(profit_below_20), 8),
    ("空单盈利≤10% (且>0) 的数量 ≥ 6", len(profit_below_10), 6),
    ("空单亏损的数量 ≥ 2", len(loss_positions), 2)
]

all_met = True
for desc, current, threshold in conditions:
    status = "✅" if current >= threshold else "❌"
    print(f"{status} {desc}: {current} (需要≥{threshold})")
    if current < threshold:
        all_met = False

print("\n" + "=" * 80)
if all_met:
    print("🚀 多头行情已触发！(蓝色状态栏)")
    print("   提示: 适合做多")
else:
    print("⏳ 多头行情未触发")
print("=" * 80)

# 显示一些样本数据
print("\n📋 样本数据 (低盈利/亏损持仓)：")
print("-" * 80)

print("\n🟡 盈利≤20% (且>0) 的持仓:")
for p in profit_below_20[:5]:
    print(f"  {p[0]:<20} 盈利率: {p[2]:>7.2f}%  持仓: {p[3]}")
if len(profit_below_20) > 5:
    print(f"  ... 还有 {len(profit_below_20) - 5} 个")

print("\n🔵 盈利≤10% (且>0) 的持仓:")
for p in profit_below_10[:5]:
    print(f"  {p[0]:<20} 盈利率: {p[2]:>7.2f}%  持仓: {p[3]}")
if len(profit_below_10) > 5:
    print(f"  ... 还有 {len(profit_below_10) - 5} 个")

print("\n🔴 亏损的持仓:")
for p in loss_positions[:5]:
    print(f"  {p[0]:<20} 盈利率: {p[2]:>7.2f}%  持仓: {p[3]}")
if len(loss_positions) > 5:
    print(f"  ... 还有 {len(loss_positions) - 5} 个")

# 验证页面访问
print("\n" + "=" * 80)
print("🌐 访问地址:")
print("   https://5000-iawcy3xxhnan90u0qd9wq-cc2fbc16.sandbox.novita.ai/anchor-system-real")
print("=" * 80)

print("\n✅ 测试完成！")
print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

conn.close()
