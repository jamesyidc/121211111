"""
优先级和计次得分计算模块
"""
from datetime import datetime

def calculate_priority_level(max_ratio, min_ratio):
    """
    计算优先级等级（1-6）
    
    参数:
    - max_ratio: 最高占比
    - min_ratio: 最低占比
    
    返回:
    - level: 等级数字 (1-6)
    - level_name: 等级名称 (例如: "等级1")
    """
    # 等级1: 最高占比>90 且 最低占比>120
    if max_ratio > 90 and min_ratio > 120:
        return 1, "等级1"
    
    # 等级2: 最高占比>80 且 最低占比>120
    if max_ratio > 80 and min_ratio > 120:
        return 2, "等级2"
    
    # 等级3: 最高占比>90 且 最低占比>110
    if max_ratio > 90 and min_ratio > 110:
        return 3, "等级3"
    
    # 等级4: 最高占比>70 且 最低占比>120
    if max_ratio > 70 and min_ratio > 120:
        return 4, "等级4"
    
    # 等级5: 最高占比>80 且 最低占比>110
    if max_ratio > 80 and min_ratio > 110:
        return 5, "等级5"
    
    # 等级6: 其他情况（最高占比<80 或 最低占比<110）
    return 6, "等级6"

def calculate_count_score(count, current_hour=None):
    """
    计算计次得分（仅对等级6）
    
    参数:
    - count: 计次值
    - current_hour: 当前小时数（0-23），如果为None则自动获取
    
    返回:
    - score_display: 星级显示 (例如: "★★★", "☆☆")
    - score_value: 星级数值 (1-3表示实心星，-1到-3表示空心星)
    - score_type: "solid"(实心) 或 "hollow"(空心)
    """
    if current_hour is None:
        current_hour = datetime.now().hour
    
    # 根据时间段选择计次规则
    # 6点前（00:00-06:00）
    if 0 <= current_hour < 6:
        if count <= 1:
            return "★★★", 3, "solid"
        elif count <= 2:
            return "★★", 2, "solid"
        elif count <= 3:
            return "★", 1, "solid"
        elif count <= 4:
            return "☆", -1, "hollow"
        elif count <= 5:
            return "☆☆", -2, "hollow"
        else:  # >5
            return "☆☆☆", -3, "hollow"
    
    # 12点前（06:00-12:00）
    elif 6 <= current_hour < 12:
        if count <= 2:
            return "★★★", 3, "solid"
        elif count <= 3:
            return "★★", 2, "solid"
        elif count <= 4:
            return "★", 1, "solid"
        elif count <= 6:
            return "☆", -1, "hollow"
        elif count <= 7:
            return "☆☆", -2, "hollow"
        else:  # >7
            return "☆☆☆", -3, "hollow"
    
    # 18点前（12:00-18:00）
    elif 12 <= current_hour < 18:
        if count <= 3:
            return "★★★", 3, "solid"
        elif count <= 4:
            return "★★", 2, "solid"
        elif count <= 5:
            return "★", 1, "solid"
        elif count <= 8:
            return "☆", -1, "hollow"
        elif count <= 9:
            return "☆☆", -2, "hollow"
        else:  # >9
            return "☆☆☆", -3, "hollow"
    
    # 24点前（18:00-24:00）
    else:  # 18 <= current_hour < 24
        if count <= 4:
            return "★★★", 3, "solid"
        elif count <= 5:
            return "★★", 2, "solid"
        elif count <= 6:
            return "★", 1, "solid"
        elif count <= 10:
            return "☆", -1, "hollow"
        elif count <= 11:
            return "☆☆", -2, "hollow"
        else:  # >11
            return "☆☆☆", -3, "hollow"

def calculate_priority_and_score(max_ratio, min_ratio, count, current_hour=None):
    """
    综合计算优先级和计次得分
    
    参数:
    - max_ratio: 最高占比
    - min_ratio: 最低占比
    - count: 计次值
    - current_hour: 当前小时数（0-23），如果为None则自动获取
    
    返回字典:
    {
        'priority': 等级数字 (1-6),
        'priority_name': 等级名称,
        'count_score_display': 星级显示 (仅等级6有值),
        'count_score_value': 星级数值 (仅等级6有值),
        'count_score_type': 星级类型 (仅等级6有值)
    }
    """
    level, level_name = calculate_priority_level(max_ratio, min_ratio)
    
    result = {
        'priority': level,
        'priority_name': level_name,
        'count_score_display': None,
        'count_score_value': None,
        'count_score_type': None
    }
    
    # 只有等级6才计算计次得分
    if level == 6:
        score_display, score_value, score_type = calculate_count_score(count, current_hour)
        result['count_score_display'] = score_display
        result['count_score_value'] = score_value
        result['count_score_type'] = score_type
    
    return result

if __name__ == "__main__":
    # 测试代码
    print("=== 优先级计算测试 ===\n")
    
    test_cases = [
        (95, 125, 5, "等级1"),
        (85, 125, 8, "等级2"),
        (92, 115, 3, "等级3"),
        (75, 125, 10, "等级4"),
        (82, 112, 6, "等级5"),
        (70, 100, 2, "等级6 (应该有计次得分)"),
    ]
    
    for max_ratio, min_ratio, count, description in test_cases:
        result = calculate_priority_and_score(max_ratio, min_ratio, count, current_hour=10)
        print(f"{description}:")
        print(f"  最高占比={max_ratio}%, 最低占比={min_ratio}%, 计次={count}")
        print(f"  结果: {result['priority_name']}")
        if result['count_score_display']:
            print(f"  计次得分: {result['count_score_display']} ({result['count_score_type']})")
        print()
    
    print("=== 不同时间段的计次得分测试 ===\n")
    
    time_periods = [
        (3, "6点前(03:00)"),
        (9, "12点前(09:00)"),
        (15, "18点前(15:00)"),
        (21, "24点前(21:00)")
    ]
    
    test_counts = [1, 3, 5, 7, 10]
    
    for hour, period_name in time_periods:
        print(f"{period_name}:")
        for count in test_counts:
            score_display, score_value, score_type = calculate_count_score(count, current_hour=hour)
            print(f"  计次={count}: {score_display} (value={score_value}, type={score_type})")
        print()
