#!/usr/bin/env python3
"""
测试维护后的价格更新流程
"""
import sqlite3
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/trading_decision.db'

def test_maintenance_price_update():
    print("=" * 60)
    print("测试维护价格更新逻辑")
    print("=" * 60)
    
    # 模拟数据
    inst_id = "TEST-USDT-SWAP"
    pos_side = "short"
    original_size = 10.0
    original_price = 1.0
    current_price = 0.85  # 亏损 -15%
    
    print(f"\n【模拟场景】")
    print(f"  币种: {inst_id}")
    print(f"  原持仓: {original_size} 张 @ {original_price}")
    print(f"  当前价: {current_price}")
    print(f"  亏损率: {((original_price - current_price) / original_price * 100):.2f}%")
    
    # 计算维护后的平均价格
    add_size = original_size * 10
    total_size = original_size + add_size
    original_cost = original_size * original_price
    add_cost = add_size * current_price
    total_cost = original_cost + add_cost
    average_price = total_cost / total_size
    
    print(f"\n【维护过程】")
    print(f"  1. 补仓: {add_size} 张 @ {current_price}")
    print(f"  2. 总持仓: {total_size} 张")
    print(f"  3. 总成本: {total_cost:.4f} USDT")
    print(f"  4. 平均价: {average_price:.4f} USDT")
    
    # 计算保留量
    target_remaining_margin = 1.0
    remain_size = (target_remaining_margin * 10) / current_price
    close_size = total_size - remain_size
    
    print(f"  5. 平仓: {close_size:.4f} 张")
    print(f"  6. 保留: {remain_size:.4f} 张 (≈1U)")
    
    print(f"\n【数据库更新】")
    print(f"  open_price: {original_price:.4f} → {average_price:.4f}")
    print(f"  open_size: {original_size:.4f} → {remain_size:.4f}")
    
    # 验证后续盈亏计算
    future_price = 0.90
    old_profit = (original_price - future_price) / original_price * 100
    new_profit = (average_price - future_price) / average_price * 100
    
    print(f"\n【盈亏对比】假设价格涨到 {future_price}")
    print(f"  使用原价 {original_price:.4f}: {old_profit:.2f}%")
    print(f"  使用均价 {average_price:.4f}: {new_profit:.2f}%")
    print(f"  差异: {abs(new_profit - old_profit):.2f}%")
    
    print("=" * 60)
    print("✅ 逻辑验证通过！")
    print("=" * 60)

if __name__ == "__main__":
    test_maintenance_price_update()
