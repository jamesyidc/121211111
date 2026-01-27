#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入比价系统的初始基准数据
"""

from price_comparison_system import PriceComparisonSystem

# 初始基准数据（从用户提供的数据解析）
BASELINE_DATA = [
    {'symbol': 'OKB', 'highest_price': 235.51972, 'highest_count': 2839, 'lowest_price': 93.75352, 'lowest_count': 737},
    {'symbol': 'DOT', 'highest_price': 4.883676056338, 'highest_count': 4319, 'lowest_price': 1.97723, 'lowest_count': 265},
    {'symbol': 'LINK', 'highest_price': 26.37, 'highest_count': 7530, 'lowest_price': 11.69141, 'lowest_count': 737},
    {'symbol': 'ADA', 'highest_price': 0.953985915493, 'highest_count': 5100, 'lowest_price': 0.37093, 'lowest_count': 260},
    {'symbol': 'FIL', 'highest_price': 2.656661971831, 'highest_count': 5101, 'lowest_price': 1.42787, 'lowest_count': 285},
    {'symbol': 'XLM', 'highest_price': 0.41770, 'highest_count': 7530, 'lowest_price': 0.21873, 'lowest_count': 737},
    {'symbol': 'HBAR', 'highest_price': 0.2552676056338, 'highest_count': 5100, 'lowest_price': 0.12379, 'lowest_count': 737},
    {'symbol': 'BCH', 'highest_price': 650.823943662, 'highest_count': 4390, 'lowest_price': 450.20845, 'lowest_count': 737},
    {'symbol': 'ETC', 'highest_price': 24.32, 'highest_count': 7529, 'lowest_price': 12.67108, 'lowest_count': 245},
    {'symbol': 'TON', 'highest_price': 3.392, 'highest_count': 7529, 'lowest_price': 1.44342, 'lowest_count': 268},
    {'symbol': 'TRX', 'highest_price': 0.36644, 'highest_count': 7529, 'lowest_price': 0.27335, 'lowest_count': 562},
    {'symbol': 'SUI', 'highest_price': 3.981056338028, 'highest_count': 4356, 'lowest_price': 1.3108, 'lowest_count': 257},
    {'symbol': 'DOGE', 'highest_price': 0.3071549295775, 'highest_count': 5100, 'lowest_price': 0.13187, 'lowest_count': 260},
    {'symbol': 'SOL', 'highest_price': 253.3591549296, 'highest_count': 4367, 'lowest_price': 122.8831, 'lowest_count': 738},
    {'symbol': 'LTC', 'highest_price': 135.56901, 'highest_count': 2396, 'lowest_price': 74.85493, 'lowest_count': 263},
    {'symbol': 'BNB', 'highest_price': 1377.4831, 'highest_count': 2297, 'lowest_price': 796.78451, 'lowest_count': 738},
    {'symbol': 'XRP', 'highest_price': 3.190211267606, 'highest_count': 5121, 'lowest_price': 1.83979, 'lowest_count': 738},
    {'symbol': 'ETH', 'highest_price': 4830, 'highest_count': 7531, 'lowest_price': 2642, 'lowest_count': 738},
    {'symbol': 'BTC', 'highest_price': 125370.20986, 'highest_count': 2833, 'lowest_price': 81359.05775, 'lowest_count': 738},
    {'symbol': 'CRO', 'highest_price': 0.3857746478873, 'highest_count': 7331, 'lowest_price': 0.09308, 'lowest_count': 737},
    {'symbol': 'CFX', 'highest_price': 0.1878309859155, 'highest_count': 4356, 'lowest_price': 0.06834, 'lowest_count': 254},
    {'symbol': 'CRV', 'highest_price': 0.8628732394366, 'highest_count': 4960, 'lowest_price': 0.36473, 'lowest_count': 600},
    {'symbol': 'APT', 'highest_price': 5.49327, 'highest_count': 2832, 'lowest_price': 1.81623, 'lowest_count': 250},
    {'symbol': 'NEAR', 'highest_price': 3.324084507042, 'highest_count': 4101, 'lowest_price': 1.59283, 'lowest_count': 268},
    {'symbol': 'UNI', 'highest_price': 10.3711971831, 'highest_count': 5101, 'lowest_price': 5.37062, 'lowest_count': 168},
    {'symbol': 'AAVE', 'highest_price': 322.6535211268, 'highest_count': 5181, 'lowest_price': 150.39577, 'lowest_count': 737},
    {'symbol': 'STX', 'highest_price': 0.7021126760563, 'highest_count': 4960, 'lowest_price': 0.27828, 'lowest_count': 245},
    {'symbol': 'TAO', 'highest_price': 476.82394, 'highest_count': 2109, 'lowest_price': 255.50563, 'lowest_count': 254},
    {'symbol': 'LDO', 'highest_price': 1.354929577465, 'highest_count': 4178, 'lowest_price': 0.55338, 'lowest_count': 198}
]

def main():
    print("=" * 60)
    print("开始导入比价系统基准数据")
    print("=" * 60)
    
    # 初始化系统
    system = PriceComparisonSystem()
    
    # 导入数据
    count = system.import_baseline_data(BASELINE_DATA)
    
    print(f"\n✅ 导入完成！共导入 {count} 个币种")
    print("\n基准数据预览：")
    
    # 显示前5条数据
    baseline = system.get_baseline_data()
    for i, coin in enumerate(baseline[:5]):
        print(f"\n{i+1}. {coin['symbol']}")
        print(f"   最高价: {coin['highest_price']:.8f} (计次: {coin['highest_count']})")
        print(f"   最低价: {coin['lowest_price']:.8f} (计次: {coin['lowest_count']})")
        print(f"   最高占比: {coin['highest_ratio']:.2f}%")
        print(f"   最低占比: {coin['lowest_ratio']:.2f}%")
    
    print(f"\n... 还有 {len(baseline) - 5} 个币种")
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
