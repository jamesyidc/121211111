#!/usr/bin/env python3
"""
计次得分计算模块
根据时间段和计次值计算星级评分
"""
from datetime import datetime
import pytz

def calculate_count_score(count, snapshot_time=None):
    """
    计算计次得分
    
    参数:
        count: 计次值
        snapshot_time: 快照时间（字符串格式 'YYYY-MM-DD HH:MM:SS'）
        
    返回:
        (display, score_type) - 显示字符串和得分类型
    """
    if snapshot_time is None:
        beijing_tz = pytz.timezone('Asia/Shanghai')
        current_time = datetime.now(beijing_tz)
    else:
        # 解析时间字符串
        current_time = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S')
    
    hour = current_time.hour
    
    # 根据时间段选择规则
    if hour < 6:  # 00:00 - 05:59 使用6点前的规则
        return calculate_before_6(count)
    elif hour < 12:  # 06:00 - 11:59 使用12点前的规则
        return calculate_before_12(count)
    elif hour < 18:  # 12:00 - 17:59 使用18点前的规则
        return calculate_before_18(count)
    else:  # 18:00 - 23:59 使用22点前的规则
        return calculate_before_22(count)

def calculate_before_6(count):
    """6点前的计次得分"""
    if count <= 1:
        return ('★★★', '实心3星')
    elif 1 < count <= 2:
        return ('★★☆', '实心2星')
    elif 2 < count <= 3:
        return ('★☆☆', '实心1星')
    elif 3 < count <= 4:
        return ('☆☆☆', '空心1星')
    elif 4 < count <= 5:
        return ('☆☆---', '空心2星')
    else:  # count > 5
        return ('☆---', '空心3星')

def calculate_before_12(count):
    """12点前的计次得分"""
    if count <= 2:
        return ('★★★', '实心3星')
    elif 2 < count <= 3:
        return ('★★☆', '实心2星')
    elif 3 < count <= 4:
        return ('★☆☆', '实心1星')
    elif 4 < count <= 5:
        return ('☆☆☆', '空心1星')
    elif 5 < count <= 6:
        return ('☆☆---', '空心2星')
    else:  # count > 6
        return ('☆---', '空心3星')

def calculate_before_18(count):
    """18点前的计次得分"""
    if count <= 3:
        return ('★★★', '实心3星')
    elif 3 < count <= 4:
        return ('★★☆', '实心2星')
    elif 4 < count <= 5:
        return ('★☆☆', '实心1星')
    elif 5 < count <= 6:
        return ('☆☆☆', '空心1星')
    elif 6 < count <= 7:
        return ('☆☆---', '空心2星')
    else:  # count > 7
        return ('☆---', '空心3星')

def calculate_before_22(count):
    """22点前的计次得分"""
    if count <= 4:
        return ('★★★', '实心3星')
    elif 4 < count <= 5:
        return ('★★☆', '实心2星')
    elif 5 < count <= 6:
        return ('★☆☆', '实心1星')
    elif 6 < count <= 7:
        return ('☆☆☆', '空心1星')
    elif 7 < count <= 8:
        return ('☆☆---', '空心2星')
    else:  # count > 8
        return ('☆---', '空心3星')

if __name__ == '__main__':
    # 测试代码
    test_cases = [
        ('2025-12-07 05:00:00', 1),   # 6点前, 计次1
        ('2025-12-07 05:00:00', 3),   # 6点前, 计次3
        ('2025-12-07 05:00:00', 6),   # 6点前, 计次6
        ('2025-12-07 10:00:00', 2),   # 12点前, 计次2
        ('2025-12-07 10:00:00', 4),   # 12点前, 计次4
        ('2025-12-07 10:00:00', 7),   # 12点前, 计次7
        ('2025-12-07 15:00:00', 3),   # 18点前, 计次3
        ('2025-12-07 15:00:00', 5),   # 18点前, 计次5
        ('2025-12-07 15:00:00', 9),   # 18点前, 计次9
        ('2025-12-07 20:00:00', 4),   # 22点前, 计次4
        ('2025-12-07 20:00:00', 6),   # 22点前, 计次6
        ('2025-12-07 20:00:00', 12),  # 22点前, 计次12
    ]
    
    print("计次得分测试:")
    for time_str, count in test_cases:
        display, score_type = calculate_count_score(count, time_str)
        hour = int(time_str.split()[1].split(':')[0])
        period = ''
        if hour < 6:
            period = '6点前'
        elif hour < 12:
            period = '12点前'
        elif hour < 18:
            period = '18点前'
        else:
            period = '22点前'
        print(f"  {period:8s} 计次{count:2d} → {display:8s} ({score_type})")
