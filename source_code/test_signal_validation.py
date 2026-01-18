#!/usr/bin/env python3
"""
测试信号数据验证逻辑
"""
import sys
sys.path.insert(0, '/home/user/webapp')

from signal_collector import SignalCollector

def test_validation():
    collector = SignalCollector()
    
    print("="*60)
    print("测试信号数据验证逻辑")
    print("="*60)
    
    # 获取最后一条记录
    last = collector.get_last_signal()
    
    if last:
        print(f"\n📊 最后一条记录:")
        print(f"   时间: {last['record_time']}")
        print(f"   做多: {last['long_signals']}")
        print(f"   做空: {last['short_signals']}")
        print(f"   总计: {last['total_signals']}")
    else:
        print("\n⚠️  数据库中没有历史记录")
    
    # 测试场景1: 有效数据（有信号）
    print("\n" + "="*60)
    print("场景1: 新数据有信号（应该通过验证）")
    print("="*60)
    
    valid_data = {
        'long_signals': 138,
        'short_signals': 35,
        'total_signals': 173,
        'long_ratio': 79.77,
        'short_ratio': 20.23,
        'today_new_high': 10,
        'today_new_low': 5,
        'raw_data': '[]'
    }
    
    result = collector.validate_signal_data(valid_data)
    print(f"验证结果: {'✅ 通过' if result else '❌ 拒绝'}")
    
    # 测试场景2: 无效数据（上次有信号，这次为0）
    print("\n" + "="*60)
    print("场景2: 新数据全为0（如果上次有信号，应该拒绝）")
    print("="*60)
    
    invalid_data = {
        'long_signals': 0,
        'short_signals': 0,
        'total_signals': 0,
        'long_ratio': 0,
        'short_ratio': 0,
        'today_new_high': 0,
        'today_new_low': 0,
        'raw_data': '[]'
    }
    
    result = collector.validate_signal_data(invalid_data)
    print(f"验证结果: {'✅ 通过' if result else '❌ 拒绝'}")
    
    if not result and last and last['total_signals'] > 0:
        print("✅ 正确！检测到数据未刷新，拒绝保存")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    test_validation()
