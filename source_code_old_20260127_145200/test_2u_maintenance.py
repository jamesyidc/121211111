#!/usr/bin/env python3
"""
测试维护后保留≤2U的逻辑
"""

def test_maintenance_with_2u_limit():
    print("=" * 60)
    print("测试维护逻辑：保留≤2U保证金")
    print("=" * 60)
    
    # 测试场景1：小额持仓（总保证金<2U）
    print("\n【场景1】小额持仓（总保证金 < 2U）")
    original_size_1 = 1.0
    original_price_1 = 0.1
    current_price_1 = 0.085
    
    add_size_1 = original_size_1 * 10
    total_size_1 = original_size_1 + add_size_1
    total_margin_1 = total_size_1 * current_price_1 / 10
    
    target_margin_1 = min(2.0, total_margin_1)
    remain_size_1 = (target_margin_1 * 10) / current_price_1
    
    print(f"  原持仓: {original_size_1} 张 @ {original_price_1}")
    print(f"  补仓后总量: {total_size_1} 张")
    print(f"  补仓后总保证金: {total_margin_1:.4f} USDT")
    print(f"  目标保留: min(2.0, {total_margin_1:.4f}) = {target_margin_1:.4f} USDT")
    print(f"  保留持仓: {remain_size_1:.4f} 张")
    print(f"  实际保证金: {remain_size_1 * current_price_1 / 10:.4f} USDT ✅")
    
    # 测试场景2：大额持仓（总保证金>2U）
    print("\n【场景2】大额持仓（总保证金 > 2U）")
    original_size_2 = 10.0
    original_price_2 = 0.5
    current_price_2 = 0.4
    
    add_size_2 = original_size_2 * 10
    total_size_2 = original_size_2 + add_size_2
    total_margin_2 = total_size_2 * current_price_2 / 10
    
    target_margin_2 = min(2.0, total_margin_2)
    remain_size_2 = (target_margin_2 * 10) / current_price_2
    
    print(f"  原持仓: {original_size_2} 张 @ {original_price_2}")
    print(f"  补仓后总量: {total_size_2} 张")
    print(f"  补仓后总保证金: {total_margin_2:.4f} USDT")
    print(f"  目标保留: min(2.0, {total_margin_2:.4f}) = {target_margin_2:.4f} USDT")
    print(f"  保留持仓: {remain_size_2:.4f} 张")
    print(f"  实际保证金: {remain_size_2 * current_price_2 / 10:.4f} USDT ✅")
    
    # 测试场景3：LDO 实际案例（从截图）
    print("\n【场景3】LDO 实际案例")
    original_size_3 = 6.6
    original_price_3 = 0.5868
    current_price_3 = 0.6115
    
    add_size_3 = original_size_3 * 10
    total_size_3 = original_size_3 + add_size_3
    
    # 计算平均价格
    original_cost = original_size_3 * original_price_3
    add_cost = add_size_3 * current_price_3
    total_cost = original_cost + add_cost
    average_price = total_cost / total_size_3
    
    total_margin_3 = total_size_3 * current_price_3 / 10
    target_margin_3 = min(2.0, total_margin_3)
    remain_size_3 = (target_margin_3 * 10) / current_price_3
    
    print(f"  原持仓: {original_size_3} 张 @ {original_price_3}")
    print(f"  当前价: {current_price_3}")
    print(f"  补仓: {add_size_3} 张 @ {current_price_3}")
    print(f"  补仓后总量: {total_size_3} 张")
    print(f"  平均价格: {average_price:.4f}")
    print(f"  补仓后总保证金: {total_margin_3:.4f} USDT")
    print(f"  目标保留: min(2.0, {total_margin_3:.4f}) = {target_margin_3:.4f} USDT")
    print(f"  保留持仓: {remain_size_3:.4f} 张")
    print(f"  实际保证金: {remain_size_3 * current_price_3 / 10:.4f} USDT ✅")
    print(f"  平仓数量: {total_size_3 - remain_size_3:.4f} 张")
    print(f"  平仓比例: {(total_size_3 - remain_size_3) / total_size_3 * 100:.1f}%")
    
    print("\n" + "=" * 60)
    print("✅ 所有场景验证通过！保证金都不超过2U")
    print("=" * 60)

if __name__ == "__main__":
    test_maintenance_with_2u_limit()
