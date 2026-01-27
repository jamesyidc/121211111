#!/usr/bin/env python3
"""
测试维护后的平均价格计算
"""

# 示例数据
original_size = 12.0  # 原持仓
original_price = 0.8346  # 原开仓价格
current_price = 0.603  # 当前价格（补仓价格）

# 维护逻辑
add_size = original_size * 10  # 补仓10倍
total_after_add = original_size + add_size

# 计算平均价格
original_cost = original_size * original_price
add_cost = add_size * current_price
total_cost = original_cost + add_cost
average_price = total_cost / total_after_add

# 计算保留量（1U保证金）
target_remaining_margin = 1.0
remain_size = (target_remaining_margin * 10) / current_price
close_size = total_after_add - remain_size
close_percent = (close_size / total_after_add) * 100

print("=" * 60)
print("锚点单维护 - 平均价格计算示例")
print("=" * 60)
print(f"\n【原持仓】")
print(f"  持仓量: {original_size:.4f} 张")
print(f"  开仓价: {original_price:.4f} USDT")
print(f"  持仓成本: {original_cost:.4f} USDT")

print(f"\n【补仓操作（10倍）】")
print(f"  补仓量: {add_size:.4f} 张")
print(f"  补仓价: {current_price:.4f} USDT")
print(f"  补仓成本: {add_cost:.4f} USDT")

print(f"\n【补仓后总计】")
print(f"  总持仓: {total_after_add:.4f} 张")
print(f"  总成本: {total_cost:.4f} USDT")
print(f"  平均价格: {average_price:.4f} USDT")

print(f"\n【平仓操作（保留1U）】")
print(f"  平仓量: {close_size:.4f} 张 ({close_percent:.1f}%)")
print(f"  保留量: {remain_size:.4f} 张")
print(f"  保留保证金: ~{remain_size * current_price / 10:.4f} USDT")

print(f"\n【维护后结果】")
print(f"  最终持仓: {remain_size:.4f} 张")
print(f"  开仓价格: {original_price:.4f} → {average_price:.4f} USDT")
print(f"  价格变化: {((average_price - original_price) / original_price * 100):.2f}%")

print(f"\n【盈亏对比】")
# 假设后续价格涨到 0.65
future_price = 0.65
old_profit_rate = (future_price - original_price) / original_price * 100
new_profit_rate = (future_price - average_price) / average_price * 100
print(f"  假设价格涨到 {future_price} USDT:")
print(f"    使用原价 {original_price:.4f}: 盈亏率 {old_profit_rate:.2f}%")
print(f"    使用均价 {average_price:.4f}: 盈亏率 {new_profit_rate:.2f}%")

print("=" * 60)
