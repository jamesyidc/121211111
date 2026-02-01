#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优先级计算函数
根据最高点比和最低点比计算优先级等级
"""

def parse_ratio(ratio_str):
    """解析比例字符串，例如 "73.69%" -> 73.69"""
    if not ratio_str or ratio_str == '-':
        return 0
    try:
        return float(ratio_str.replace('%', ''))
    except:
        return 0

def calculate_priority(ratio1_str, ratio2_str):
    """
    计算优先级等级
    
    参数:
        ratio1_str: 最高点比（字符串，如 "73.69%"）
        ratio2_str: 最低点比（字符串，如 "113.56%"）
    
    返回:
        等级数字 (1-6) 和等级描述
    
    等级规则:
        等级1: 最高占比>90  且 最低占比>120
        等级2: 最高占比>80  且 最低占比>120
        等级3: 最高占比>90  且 最低占比>110
        等级4: 最高占比>70  且 最低占比>120
        等级5: 最高占比>80  且 最低占比>110
        等级6: 最高占比<80  或 最低占比<110
    """
    ratio1 = parse_ratio(ratio1_str)  # 最高点比
    ratio2 = parse_ratio(ratio2_str)  # 最低点比
    
    # 按优先级顺序判断（从高到低）
    if ratio1 > 90 and ratio2 > 120:
        return 1, "等级1"
    elif ratio1 > 80 and ratio2 > 120:
        return 2, "等级2"
    elif ratio1 > 90 and ratio2 > 110:
        return 3, "等级3"
    elif ratio1 > 70 and ratio2 > 120:
        return 4, "等级4"
    elif ratio1 > 80 and ratio2 > 110:
        return 5, "等级5"
    else:
        return 6, "等级6"

def get_priority_color(level):
    """获取等级对应的颜色"""
    colors = {
        1: '#ff0000',  # 红色 - 最高优先级
        2: '#ff6600',  # 橙红色
        3: '#ff9900',  # 橙色
        4: '#ffcc00',  # 黄色
        5: '#99cc00',  # 黄绿色
        6: '#666666',  # 灰色 - 最低优先级
    }
    return colors.get(level, '#999999')

def get_priority_badge(level):
    """获取等级徽章文本"""
    badges = {
        1: "⭐⭐⭐⭐⭐",
        2: "⭐⭐⭐⭐",
        3: "⭐⭐⭐",
        4: "⭐⭐",
        5: "⭐",
        6: "—",
    }
    return badges.get(level, "—")

if __name__ == '__main__':
    # 测试用例
    test_cases = [
        ("95%", "125%", "应该是等级1"),
        ("85%", "125%", "应该是等级2"),
        ("95%", "115%", "应该是等级3"),
        ("75%", "125%", "应该是等级4"),
        ("85%", "115%", "应该是等级5"),
        ("75%", "105%", "应该是等级6"),
        ("50%", "90%", "应该是等级6"),
    ]
    
    print("优先级计算测试:\n")
    print(f"{'最高点比':<10} {'最低点比':<10} {'等级':<8} {'星级':<15} {'预期':<15}")
    print("-" * 70)
    
    for ratio1, ratio2, expected in test_cases:
        level, desc = calculate_priority(ratio1, ratio2)
        badge = get_priority_badge(level)
        print(f"{ratio1:<10} {ratio2:<10} {desc:<8} {badge:<15} {expected:<15}")
