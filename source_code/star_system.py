#!/usr/bin/env python3
"""
星星系统评估模块
根据各项指标计算星级评分
"""
from datetime import datetime
import pytz

def calculate_star_system(data):
    """
    计算所有14个指标的星级评分
    
    参数:
        data: 包含所有指标数据的字典
    
    返回:
        评分结果字典，包含每个指标的星级和统计信息
    """
    results = {}
    solid_stars = 0  # 实心星总数
    hollow_stars = 0  # 空心星总数
    
    # 1. 急涨提醒
    rush_up = data.get('rush_up', 0)
    if rush_up >= 100:
        results['rush_up'] = {'stars': 3, 'type': '实心', 'display': '★★★'}
        solid_stars += 3
    elif rush_up >= 50:
        results['rush_up'] = {'stars': 2, 'type': '实心', 'display': '★★☆'}
        solid_stars += 2
    elif rush_up >= 10:
        results['rush_up'] = {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        solid_stars += 1
    else:
        results['rush_up'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 2. 急跌系统
    rush_down = data.get('rush_down', 0)
    if rush_down >= 100:
        results['rush_down'] = {'stars': 3, 'type': '空心', 'display': '☆☆☆'}
        hollow_stars += 3
    elif rush_down >= 50:
        results['rush_down'] = {'stars': 2, 'type': '空心', 'display': '☆☆---'}
        hollow_stars += 2
    elif rush_down >= 10:
        results['rush_down'] = {'stars': 1, 'type': '空心', 'display': '☆---'}
        hollow_stars += 1
    else:
        results['rush_down'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 3. 差值正值
    diff = data.get('diff', 0)
    if diff >= 50:
        results['diff_positive'] = {'stars': 3, 'type': '实心', 'display': '★★★'}
        solid_stars += 3
    elif diff >= 20:
        results['diff_positive'] = {'stars': 2, 'type': '实心', 'display': '★★☆'}
        solid_stars += 2
    elif diff >= 10:
        results['diff_positive'] = {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        solid_stars += 1
    else:
        results['diff_positive'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 4. 差值负值
    if diff <= -50:
        results['diff_negative'] = {'stars': 3, 'type': '空心', 'display': '☆☆☆'}
        hollow_stars += 3
    elif diff <= -20:
        results['diff_negative'] = {'stars': 2, 'type': '空心', 'display': '☆☆---'}
        hollow_stars += 2
    elif diff <= -10:
        results['diff_negative'] = {'stars': 1, 'type': '空心', 'display': '☆---'}
        hollow_stars += 1
    else:
        results['diff_negative'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 5. 全网持仓量（输入单位：元，需转换为亿进行评分）
    holdings_raw = data.get('holdings', 0)
    holdings = holdings_raw / 100000000  # 转换为亿
    if holdings <= 91:
        results['holdings'] = {'stars': 3, 'type': '实心', 'display': '★★★'}
        solid_stars += 3
    elif 91 < holdings < 95:
        results['holdings'] = {'stars': 2, 'type': '实心', 'display': '★★☆'}
        solid_stars += 2
    elif 95 <= holdings < 100:
        results['holdings'] = {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        solid_stars += 1
    else:
        results['holdings'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 6. 做多信号
    long_signals = data.get('long_signals', 0)
    if long_signals >= 100:
        results['long_signals'] = {'stars': 3, 'type': '实心', 'display': '★★★'}
        solid_stars += 3
    elif 50 <= long_signals < 100:
        results['long_signals'] = {'stars': 2, 'type': '实心', 'display': '★★☆'}
        solid_stars += 2
    elif 20 <= long_signals < 50:
        results['long_signals'] = {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        solid_stars += 1
    else:
        results['long_signals'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 7. 做空信号
    short_signals = data.get('short_signals', 0)
    if short_signals >= 120:
        results['short_signals'] = {'stars': 3, 'type': '空心', 'display': '☆☆☆'}
        hollow_stars += 3
    elif 50 <= short_signals < 120:
        results['short_signals'] = {'stars': 2, 'type': '空心', 'display': '☆☆---'}
        hollow_stars += 2
    elif 30 <= short_signals < 50:
        results['short_signals'] = {'stars': 1, 'type': '空心', 'display': '☆---'}
        hollow_stars += 1
    else:
        results['short_signals'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 8. 只有急涨没有急跌
    only_rush_up_count = data.get('only_rush_up_count', 0)
    results['only_rush_up'] = {
        'count': only_rush_up_count,
        'display': f'{only_rush_up_count}个币种'
    }
    
    # 9. 急涨大于急跌
    rush_up_gt_down_count = data.get('rush_up_gt_down_count', 0)
    results['rush_up_gt_down'] = {
        'count': rush_up_gt_down_count,
        'display': f'{rush_up_gt_down_count}个币种'
    }
    
    # 10. 优先级≥4（即等级1、2、3、4）
    priority_high_count = data.get('priority_high_count', 0)
    results['priority_high'] = {
        'count': priority_high_count,
        'display': f'{priority_high_count}个币种'
    }
    
    # 11. 只有急跌
    only_rush_down_count = data.get('only_rush_down_count', 0)
    results['only_rush_down'] = {
        'count': only_rush_down_count,
        'display': f'{only_rush_down_count}个币种'
    }
    
    # 12. 急跌大于急涨
    rush_down_gt_up_count = data.get('rush_down_gt_up_count', 0)
    results['rush_down_gt_up'] = {
        'count': rush_down_gt_up_count,
        'display': f'{rush_down_gt_up_count}个币种'
    }
    
    # 13. 今天创新低记录
    new_low_today = data.get('new_low_today', 0)
    if new_low_today > 10:
        results['new_low_today'] = {'stars': 3, 'type': '空心', 'display': '☆☆☆'}
        hollow_stars += 3
    elif 3 <= new_low_today <= 10:
        results['new_low_today'] = {'stars': 2, 'type': '空心', 'display': '☆☆---'}
        hollow_stars += 2
    elif 1 <= new_low_today < 3:
        results['new_low_today'] = {'stars': 1, 'type': '空心', 'display': '☆---'}
        hollow_stars += 1
    else:
        results['new_low_today'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 14. 今天创新高记录
    new_high_today = data.get('new_high_today', 0)
    if new_high_today > 10:
        results['new_high_today'] = {'stars': 3, 'type': '实心', 'display': '★★★'}
        solid_stars += 3
    elif 3 <= new_high_today <= 10:
        results['new_high_today'] = {'stars': 2, 'type': '实心', 'display': '★★☆'}
        solid_stars += 2
    elif 1 <= new_high_today < 3:
        results['new_high_today'] = {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        solid_stars += 1
    else:
        results['new_high_today'] = {'stars': 0, 'type': '无', 'display': '---'}
    
    # 15. 计次得分（根据时间段）
    count = data.get('count', 0)
    snapshot_time = data.get('snapshot_time')
    if snapshot_time:
        hour = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S').hour
    else:
        beijing_tz = pytz.timezone('Asia/Shanghai')
        hour = datetime.now(beijing_tz).hour
    
    count_score = calculate_count_score_stars(count, hour)
    results['count_score'] = count_score
    if count_score['type'] == '实心':
        solid_stars += count_score['stars']
    elif count_score['type'] == '空心':
        hollow_stars += count_score['stars']
    
    # 添加统计信息
    results['summary'] = {
        'solid_stars': solid_stars,
        'hollow_stars': hollow_stars,
        'total_stars': solid_stars + hollow_stars
    }
    
    return results

def calculate_count_score_stars(count, hour):
    """
    计算计次得分的星级
    
    规则说明:
    - 截止6点前:   ≤1→3实心★★★  1<x≤2→2实心★★☆  2<x≤3→1实心★☆☆  3<x≤4→1空心☆  4<x≤5→2空心☆☆  >5→3空心☆☆☆
    - 截止12点前:  ≤2→3实心★★★  2<x≤3→2实心★★☆  3<x≤4→1实心★☆☆  4<x≤5→1空心☆  5<x≤6→2空心☆☆  >6→3空心☆☆☆
    - 截止18点前:  ≤3→3实心★★★  3<x≤4→2实心★★☆  4<x≤5→1实心★☆☆  5<x≤6→1空心☆  6<x≤7→2空心☆☆  >7→3空心☆☆☆
    - 截止24点前:  ≤4→3实心★★★  4<x≤5→2实心★★☆  5<x≤6→1实心★☆☆  6<x≤7→1空心☆  7<x≤8→2空心☆☆  >8→3空心☆☆☆
    """
    if hour < 6:
        # 截止6点前
        if count <= 1:
            return {'stars': 3, 'type': '实心', 'display': '★★★'}
        elif 1 < count <= 2:
            return {'stars': 2, 'type': '实心', 'display': '★★☆'}
        elif 2 < count <= 3:
            return {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        elif 3 < count <= 4:
            return {'stars': 1, 'type': '空心', 'display': '☆'}
        elif 4 < count <= 5:
            return {'stars': 2, 'type': '空心', 'display': '☆☆'}
        else:  # count > 5
            return {'stars': 3, 'type': '空心', 'display': '☆☆☆'}
    
    elif hour < 12:
        # 截止12点前
        if count <= 2:
            return {'stars': 3, 'type': '实心', 'display': '★★★'}
        elif 2 < count <= 3:
            return {'stars': 2, 'type': '实心', 'display': '★★☆'}
        elif 3 < count <= 4:
            return {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        elif 4 < count <= 5:
            return {'stars': 1, 'type': '空心', 'display': '☆'}
        elif 5 < count <= 6:
            return {'stars': 2, 'type': '空心', 'display': '☆☆'}
        else:  # count > 6
            return {'stars': 3, 'type': '空心', 'display': '☆☆☆'}
    
    elif hour < 18:
        # 截止18点前
        if count <= 3:
            return {'stars': 3, 'type': '实心', 'display': '★★★'}
        elif 3 < count <= 4:
            return {'stars': 2, 'type': '实心', 'display': '★★☆'}
        elif 4 < count <= 5:
            return {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        elif 5 < count <= 6:
            return {'stars': 1, 'type': '空心', 'display': '☆'}
        elif 6 < count <= 7:
            return {'stars': 2, 'type': '空心', 'display': '☆☆'}
        else:  # count > 7
            return {'stars': 3, 'type': '空心', 'display': '☆☆☆'}
    
    else:  # hour >= 18 (18-24点)
        # 截止24点前
        if count <= 4:
            return {'stars': 3, 'type': '实心', 'display': '★★★'}
        elif 4 < count <= 5:
            return {'stars': 2, 'type': '实心', 'display': '★★☆'}
        elif 5 < count <= 6:
            return {'stars': 1, 'type': '实心', 'display': '★☆☆'}
        elif 6 < count <= 7:
            return {'stars': 1, 'type': '空心', 'display': '☆'}
        elif 7 < count <= 8:
            return {'stars': 2, 'type': '空心', 'display': '☆☆'}
        else:  # count > 8
            return {'stars': 3, 'type': '空心', 'display': '☆☆☆'}

if __name__ == '__main__':
    # 测试
    test_data = {
        'rush_up': 55,
        'rush_down': 12,
        'diff': 25,
        'holdings': 93,
        'long_signals': 75,
        'short_signals': 35,
        'only_rush_up_count': 5,
        'rush_up_gt_down_count': 18,
        'priority_high_count': 12,
        'only_rush_down_count': 3,
        'new_low_today': 2,
        'new_high_today': 5,
        'count': 3,
        'snapshot_time': '2025-12-07 13:00:00'
    }
    
    results = calculate_star_system(test_data)
    print("星星系统测试:")
    print(f"1. 急涨提醒: {results['rush_up']['display']}")
    print(f"2. 急跌系统: {results['rush_down']['display']}")
    print(f"3. 差值正值: {results['diff_positive']['display']}")
    print(f"4. 差值负值: {results['diff_negative']['display']}")
    print(f"5. 全网持仓量: {results['holdings']['display']}")
    print(f"6. 做多信号: {results['long_signals']['display']}")
    print(f"7. 做空信号: {results['short_signals']['display']}")
    print(f"8. 只有急涨: {results['only_rush_up']['display']}")
    print(f"9. 急涨>急跌: {results['rush_up_gt_down']['display']}")
    print(f"10. 优先级高: {results['priority_high']['display']}")
    print(f"11. 只有急跌: {results['only_rush_down']['display']}")
    print(f"12. 创新低: {results['new_low_today']['display']}")
    print(f"13. 创新高: {results['new_high_today']['display']}")
    print(f"14. 计次得分: {results['count_score']['display']}")
    print(f"\n总计: 实心星{results['summary']['solid_stars']}个, 空心星{results['summary']['hollow_stars']}个")
