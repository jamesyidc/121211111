#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示开仓和补仓流程
"""

import sys
sys.path.append('/home/user/webapp')

from position_manager import PositionManager
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')


def demo_open_positions():
    """演示开仓流程"""
    print("=" * 60)
    print("📊 演示开仓流程")
    print("=" * 60)
    print()
    
    manager = PositionManager()
    
    # 测试币种列表
    test_positions = [
        # 小颗粒币种
        {'inst_id': 'DOGE-USDT-SWAP', 'pos_side': 'short', 'price': 0.085, 'granularity': 'small'},
        {'inst_id': 'XRP-USDT-SWAP', 'pos_side': 'short', 'price': 0.625, 'granularity': 'small'},
        {'inst_id': 'ADA-USDT-SWAP', 'pos_side': 'short', 'price': 0.465, 'granularity': 'small'},
        # 中颗粒币种
        {'inst_id': 'BNB-USDT-SWAP', 'pos_side': 'short', 'price': 315.8, 'granularity': 'medium'},
        {'inst_id': 'SOL-USDT-SWAP', 'pos_side': 'short', 'price': 98.5, 'granularity': 'medium'},
        # 大颗粒币种
        {'inst_id': 'BTC-USDT-SWAP', 'pos_side': 'short', 'price': 43250.5, 'granularity': 'large'},
    ]
    
    available = manager.get_available_capital()
    print(f"可开仓资金: {available:.2f} USDT\n")
    
    for pos in test_positions:
        granularity = pos['granularity']
        config = manager.GRANULARITY_CONFIG[granularity]
        
        # 检查是否可以开仓
        can_open, message = manager.can_open_position(granularity)
        
        if can_open:
            # 计算开仓数量
            open_amount = available * config['add_percent'] / 100
            size = open_amount / pos['price']  # 简单计算
            
            # 记录开仓
            position_id = manager.record_open_position(
                inst_id=pos['inst_id'],
                pos_side=pos['pos_side'],
                size=size,
                price=pos['price'],
                granularity=granularity,
                open_percent=config['add_percent']
            )
            
            print(f"✅ 开仓成功 #{position_id}")
            print(f"   交易对: {pos['inst_id']}")
            print(f"   方向: {pos['pos_side']}")
            print(f"   颗粒度: {config['name']}")
            print(f"   金额: {open_amount:.2f} USDT ({config['add_percent']}%)")
            print(f"   价格: {pos['price']}")
            print(f"   数量: {size:.4f}")
            print()
        else:
            print(f"❌ 无法开仓: {pos['inst_id']}")
            print(f"   原因: {message}")
            print()
    
    # 显示汇总
    summary = manager.get_position_summary()
    print("\n" + "=" * 60)
    print("📈 开仓汇总")
    print("=" * 60)
    print(f"总持仓: {summary['total_positions']}个")
    print(f"小颗粒: {summary['small_granularity']['percent']}")
    print(f"中颗粒: {summary['medium_granularity']['percent']}")
    print(f"大颗粒: {summary['large_granularity']['percent']}")
    print()


def demo_add_positions():
    """演示补仓流程"""
    print("=" * 60)
    print("📊 演示补仓流程")
    print("=" * 60)
    print()
    
    manager = PositionManager()
    
    # 测试场景：DOGE-USDT-SWAP 亏损触发补仓
    test_cases = [
        {'inst_id': 'DOGE-USDT-SWAP', 'pos_side': 'short', 'profit_rate': -1.2, 'price': 0.086},
        {'inst_id': 'DOGE-USDT-SWAP', 'pos_side': 'short', 'profit_rate': -2.1, 'price': 0.087},
        {'inst_id': 'DOGE-USDT-SWAP', 'pos_side': 'short', 'profit_rate': -3.5, 'price': 0.088},
    ]
    
    available = manager.get_available_capital()
    
    for i, case in enumerate(test_cases):
        should_add, reason, add_percent = manager.should_add_position(
            case['inst_id'], case['pos_side'], case['profit_rate']
        )
        
        print(f"\n测试场景 {i+1}:")
        print(f"  交易对: {case['inst_id']}")
        print(f"  浮亏: {case['profit_rate']}%")
        print(f"  判断: {reason}")
        
        if should_add:
            # 计算补仓金额和数量
            add_amount = available * add_percent / 100
            add_size = add_amount / case['price']
            
            # 记录补仓
            add_id = manager.record_add_position(
                inst_id=case['inst_id'],
                pos_side=case['pos_side'],
                add_size=add_size,
                add_price=case['price'],
                add_level=i+1,
                profit_rate=case['profit_rate'],
                add_percent=add_percent,
                total_size_after=0  # 简化处理
            )
            
            print(f"  ✅ 补仓成功 #{add_id}")
            print(f"  补仓金额: {add_amount:.2f} USDT ({add_percent}%)")
            print(f"  补仓价格: {case['price']}")
            print(f"  补仓数量: {add_size:.4f}")
        else:
            print(f"  ⏸️  不需要补仓")


def main():
    print("\n")
    print("🚀 开仓和补仓系统演示")
    print("=" * 60)
    print()
    
    # Step 1: 演示开仓
    demo_open_positions()
    
    # Step 2: 演示补仓
    demo_add_positions()
    
    print("\n✅ 演示完成")
    print()


if __name__ == '__main__':
    main()
