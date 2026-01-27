#!/usr/bin/env python3
"""
测试计次得分计算的所有场景
"""

def calculate_count_score(count_times, current_hour):
    """
    根据计次和当前时间计算得分
    返回: (星级数量, 星级类型, 描述)
    """
    if current_hour < 6:
        period = "00-06点"
        if count_times <= 1:
            return (3, "实心", "★★★", period)
        elif 1 < count_times <= 2:
            return (2, "实心", "★★☆", period)
        elif 2 < count_times <= 3:
            return (1, "实心", "★☆☆", period)
        elif 3 < count_times <= 4:
            return (1, "空心", "☆--", period)
        elif 4 < count_times <= 5:
            return (2, "空心", "☆☆-", period)
        else:
            return (3, "空心", "☆☆☆", period)
            
    elif 6 <= current_hour < 12:
        period = "06-12点"
        if count_times <= 2:
            return (3, "实心", "★★★", period)
        elif 2 < count_times <= 3:
            return (2, "实心", "★★☆", period)
        elif 3 < count_times <= 4:
            return (1, "实心", "★☆☆", period)
        elif 4 < count_times <= 5:
            return (0, "中性", "---", period)
        elif 5 < count_times <= 6:
            return (1, "空心", "☆--", period)
        elif 6 < count_times <= 7:
            return (2, "空心", "☆☆-", period)
        else:
            return (3, "空心", "☆☆☆", period)
            
    elif 12 <= current_hour < 18:
        period = "12-18点"
        if count_times <= 3:
            return (3, "实心", "★★★", period)
        elif 3 < count_times <= 4:
            return (2, "实心", "★★☆", period)
        elif 4 < count_times <= 5:
            return (1, "实心", "★☆☆", period)
        elif 5 < count_times <= 7:
            return (0, "中性", "---", period)
        elif 7 < count_times <= 8:
            return (1, "空心", "☆--", period)
        elif 8 < count_times <= 9:
            return (2, "空心", "☆☆-", period)
        else:
            return (3, "空心", "☆☆☆", period)
            
    else:
        period = "18-22点"
        if count_times <= 4:
            return (3, "实心", "★★★", period)
        elif 4 < count_times <= 5:
            return (2, "实心", "★★☆", period)
        elif 5 < count_times <= 6:
            return (1, "实心", "★☆☆", period)
        elif 6 < count_times <= 9:
            return (0, "中性", "---", period)
        elif 9 < count_times <= 10:
            return (1, "空心", "☆--", period)
        elif 10 < count_times <= 11:
            return (2, "空心", "☆☆-", period)
        else:
            return (3, "空心", "☆☆☆", period)

def test_all_scenarios():
    """测试所有时段和计次组合"""
    print("="*80)
    print("计次得分测试 - 所有场景")
    print("="*80)
    
    # 测试用例：(小时, 计次值列表)
    test_cases = [
        (3, [0, 1, 2, 3, 4, 5, 6, 10]),    # 00-06点
        (9, [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]),  # 06-12点
        (15, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15]),  # 12-18点
        (20, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15]),  # 18-22点
    ]
    
    for hour, count_values in test_cases:
        print(f"\n{'='*80}")
        print(f"时段: {hour}点")
        print(f"{'='*80}")
        print(f"{'计次':>4s} | {'星级':^8s} | {'类型':^6s} | 显示")
        print("-" * 40)
        
        for count in count_values:
            star_count, star_type, display, period = calculate_count_score(count, hour)
            print(f"{count:4d} | {star_count:^8d} | {star_type:^6s} | {display}")

def test_current_value():
    """测试当前实际值"""
    print("\n" + "="*80)
    print("当前实际数据测试")
    print("="*80)
    
    current_hour = 13
    count_times = 10
    
    star_count, star_type, display, period = calculate_count_score(count_times, current_hour)
    
    print(f"当前时间: {current_hour}点 ({period})")
    print(f"计次值: {count_times}")
    print(f"评分结果: {star_count}颗{star_type} {display}")
    print()
    print("✅ 验证: 13点属于12-18点时段，计次=10，大于9，应该是3颗空心星")

if __name__ == '__main__':
    test_all_scenarios()
    test_current_value()
