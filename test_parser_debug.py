#!/usr/bin/env python3
"""
调试TXT解析问题
"""
import sys
sys.path.insert(0, '/home/user/webapp')

from txt_parser_enhanced import parse_txt_file_enhanced
from priority_calculator import calculate_priority_and_score, calculate_count_score
from datetime import datetime

# 测试不同格式的TXT内容
test_cases = [
    {
        "name": "V5.5 格式（有透明标签和数据）",
        "content": """透明标签_急涨总和=急涨：34
透明标签_急跌总和=急跌：8
透明标签_五种状态=状态：震荡无序
透明标签_急涨急跌比值=比值：3.25
透明标签_计次=6
透明标签_差值结果=差值：26
透明标签_比价最低得分=比价最低 0 0
透明标签_仓位得分=比价创新高 仓位加10% 0

[超级列表框_首页开始]
1|BTC|1|0|2026-01-14 22:49:00|150000|2025-10-10|15.5|-2.5|5.0|-3.0|13|91098.9|72.66%|111.97%
2|ETH|1|0|2026-01-14 22:49:00|5000|2025-11-15|8.2|-3.3|4.2|-2.8|4|3419.08|68.48%|112.26%
"""
    },
    {
        "name": "只有透明标签，没有数据行",
        "content": """透明标签_急涨总和=急涨：34
透明标签_急跌总和=急跌：8
透明标签_五种状态=状态：震荡无序
透明标签_急涨急跌比值=比值：3.25
透明标签_计次=6
透明标签_差值结果=差值：26
透明标签_比价最低得分=比价最低 0 0
透明标签_仓位得分=比价创新高 仓位加10% 0

[超级列表框_首页开始]
"""
    },
    {
        "name": "空内容",
        "content": ""
    }
]

print("=" * 80)
print("TXT 解析调试测试")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    print(f"\n测试 {i}: {test['name']}")
    print("-" * 80)
    
    aggregate_data, coin_records, error = parse_txt_file_enhanced(
        test['content'], 
        "2026-01-14 22:49:00"
    )
    
    if error:
        print(f"❌ 解析失败: {error}")
    else:
        print(f"✅ 解析成功")
        print(f"\n📊 聚合数据:")
        for key, value in aggregate_data.items():
            print(f"   {key}: {value}")
        
        print(f"\n💰 币种记录: {len(coin_records)} 条")
        for j, record in enumerate(coin_records[:3], 1):
            print(f"   {j}. {record.get('inst_id', 'N/A')}: "
                  f"急涨={record.get('rush_up', 0)}, "
                  f"急跌={record.get('rush_down', 0)}, "
                  f"最高占比={record.get('max_ratio', 0):.2f}%, "
                  f"最低占比={record.get('min_ratio', 0):.2f}%")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
