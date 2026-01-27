#!/usr/bin/env python3
"""
v6.0功能验证脚本
测试差值曲线、高亮标记、时间戳等核心功能
"""

import requests
import json
from datetime import datetime

API_BASE = 'http://localhost:5001'

def test_crypto_data():
    """测试主数据API"""
    print("\n" + "="*60)
    print("测试 1: 主数据API")
    print("="*60)
    
    response = requests.get(f'{API_BASE}/api/crypto-data')
    data = response.json()
    
    if data['success']:
        print(f"✅ API响应成功")
        print(f"   币种数量: {len(data['data'])}")
        print(f"   文件时间: {data['updateTime']}")
        print(f"   文件名: {data['filename']}")
        
        stats = data['stats']
        print(f"\n📊 统计数据:")
        print(f"   急涨: {stats['rushUp']}")
        print(f"   急跌: {stats['rushDown']}")
        print(f"   差值: {stats['diff']}")
        print(f"   比值: {stats['ratio']}")
        
        # 验证差值计算
        rush_up = int(stats['rushUp'])
        rush_down = int(stats['rushDown'])
        expected_diff = rush_up - rush_down
        actual_diff = int(stats['diff'])
        
        if expected_diff == actual_diff:
            print(f"✅ 差值计算正确: {rush_up} - {rush_down} = {actual_diff}")
        else:
            print(f"❌ 差值计算错误: 期望 {expected_diff}, 实际 {actual_diff}")
    else:
        print(f"❌ API失败: {data.get('error', '未知错误')}")

def test_history_chart():
    """测试历史图表API"""
    print("\n" + "="*60)
    print("测试 2: 历史图表API")
    print("="*60)
    
    response = requests.get(f'{API_BASE}/api/history-chart')
    data = response.json()
    
    if data['success']:
        history = data['history']
        print(f"✅ 历史数据加载成功")
        print(f"   数据点总数: {len(history)}")
        
        # 分析高亮条件
        highlight_stats = {
            'rush_up_10': 0,
            'rush_down_10': 0,
            'diff_50': 0,
            'diff_neg_50': 0
        }
        
        for item in history:
            rush_up = int(item['rushUp'])
            rush_down = int(item['rushDown'])
            diff = rush_up - rush_down
            
            if rush_up >= 10:
                highlight_stats['rush_up_10'] += 1
            if rush_down >= 10:
                highlight_stats['rush_down_10'] += 1
            if diff >= 50:
                highlight_stats['diff_50'] += 1
            if diff <= -50:
                highlight_stats['diff_neg_50'] += 1
        
        print(f"\n🎯 高亮条件统计:")
        print(f"   急涨≥10的点: {highlight_stats['rush_up_10']} 个")
        print(f"   急跌≥10的点: {highlight_stats['rush_down_10']} 个")
        print(f"   差值≥50的点: {highlight_stats['diff_50']} 个")
        print(f"   差值≤-50的点: {highlight_stats['diff_neg_50']} 个")
        print(f"   总高亮点数: {highlight_stats['rush_up_10'] + highlight_stats['rush_down_10'] + highlight_stats['diff_50'] + highlight_stats['diff_neg_50']} 个")
        
        # 显示前3个和后3个数据点
        print(f"\n📋 前3个数据点:")
        for item in history[:3]:
            rush_up = int(item['rushUp'])
            rush_down = int(item['rushDown'])
            diff = rush_up - rush_down
            print(f"   {item['time']}: 急涨={rush_up}, 急跌={rush_down}, 差值={diff}")
        
        print(f"\n📋 最后3个数据点:")
        for item in history[-3:]:
            rush_up = int(item['rushUp'])
            rush_down = int(item['rushDown'])
            diff = rush_up - rush_down
            print(f"   {item['time']}: 急涨={rush_up}, 急跌={rush_down}, 差值={diff}")
    else:
        print(f"❌ 历史数据加载失败")

def test_timestamp_logic():
    """测试时间戳逻辑"""
    print("\n" + "="*60)
    print("测试 3: 时间戳逻辑")
    print("="*60)
    
    response = requests.get(f'{API_BASE}/api/crypto-data')
    data = response.json()
    
    if data['success']:
        file_time_str = data['updateTime']
        file_time = datetime.strptime(file_time_str, '%Y-%m-%d %H:%M:%S')
        
        # 计算更新时间（文件时间+1分钟）
        from datetime import timedelta
        update_time = file_time + timedelta(minutes=1)
        
        print(f"✅ 时间戳验证:")
        print(f"   TXT文件时间: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   更新时间(+1分钟): {update_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   下次更新(+10分钟): {(update_time + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n💡 前端应该:")
        print(f"   1. 图表X轴显示: {update_time.strftime('%H:%M')}")
        print(f"   2. 倒计时基于: 下次更新时间 - 当前时间")
        print(f"   3. 不使用浏览器本地时间")

def test_highlight_conditions():
    """详细测试高亮条件"""
    print("\n" + "="*60)
    print("测试 4: 高亮条件详细验证")
    print("="*60)
    
    # 测试用例
    test_cases = [
        {'rushUp': 10, 'rushDown': 5, 'expected': ['急涨高亮']},
        {'rushUp': 9, 'rushDown': 10, 'expected': ['急跌高亮']},
        {'rushUp': 60, 'rushDown': 5, 'expected': ['急涨高亮', '差值高亮(≥50)']},
        {'rushUp': 5, 'rushDown': 60, 'expected': ['急跌高亮', '差值高亮(≤-50)']},
        {'rushUp': 15, 'rushDown': 12, 'expected': ['急涨高亮', '急跌高亮']},
        {'rushUp': 5, 'rushDown': 3, 'expected': ['无高亮']},
    ]
    
    print("\n测试场景:")
    for i, case in enumerate(test_cases, 1):
        rush_up = case['rushUp']
        rush_down = case['rushDown']
        diff = rush_up - rush_down
        
        actual = []
        if rush_up >= 10:
            actual.append('急涨高亮')
        if rush_down >= 10:
            actual.append('急跌高亮')
        if diff >= 50:
            actual.append('差值高亮(≥50)')
        if diff <= -50:
            actual.append('差值高亮(≤-50)')
        if not actual:
            actual.append('无高亮')
        
        expected = case['expected']
        status = "✅" if set(actual) == set(expected) else "❌"
        
        print(f"\n场景 {i}: {status}")
        print(f"  急涨={rush_up}, 急跌={rush_down}, 差值={diff}")
        print(f"  期望: {', '.join(expected)}")
        print(f"  实际: {', '.join(actual)}")

def main():
    print("\n" + "🚀 " + "="*58)
    print("🎯 v6.0 功能全面验证")
    print("="*60)
    print("测试内容:")
    print("  1. 主数据API (29币种 + 统计)")
    print("  2. 历史图表API (历史数据 + 差值)")
    print("  3. 时间戳逻辑 (文件时间+1分钟)")
    print("  4. 高亮条件 (急涨≥10, 急跌≥10, 差值≥50/≤-50)")
    
    try:
        test_crypto_data()
        test_history_chart()
        test_timestamp_logic()
        test_highlight_conditions()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        print("\n📖 下一步:")
        print("   1. 访问页面查看图表效果")
        print("   2. 打开浏览器控制台查看日志")
        print("   3. 验证大点(10px)是否正确显示")
        print("   4. 确认颜色: 绿(急涨), 红(急跌), 橙(差值)")
        print("\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print("   请确保服务器正在运行: python3 crypto_server_demo.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == '__main__':
    main()
