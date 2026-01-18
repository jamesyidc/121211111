#!/usr/bin/env python3
"""
极值监控测试脚本
使用模拟数据测试极值更新和Telegram通知功能
"""

import sys
sys.path.insert(0, '/home/user/webapp/source_code')

from extreme_monitor_jsonl import ExtremeMonitorJSONL

def test_with_mock_data():
    """使用模拟数据测试"""
    
    monitor = ExtremeMonitorJSONL()
    
    # 模拟一个持仓数据（创新高的情况）
    mock_position_high = {
        'instId': 'BTC-USDT-SWAP',
        'posSide': 'long',
        'pos': '10',
        'avgPx': '90000',
        'markPx': '95000',
        'upl': '500',  # 未实现盈亏
        'margin': '1000',  # 保证金
        'lever': '10'
    }
    
    # 模拟一个持仓数据（创新低的情况）
    mock_position_low = {
        'instId': 'ETH-USDT-SWAP',
        'posSide': 'short',
        'pos': '20',
        'avgPx': '3500',
        'markPx': '3800',
        'upl': '-600',  # 未实现盈亏
        'margin': '1000',  # 保证金
        'lever': '10'
    }
    
    print("=" * 80)
    print("📊 测试极值监控功能")
    print("=" * 80)
    
    # 测试1: 检查并更新创新高的情况
    print("\n【测试1】检查BTC做多创新高...")
    update_info_high = monitor.check_and_update_extreme(mock_position_high)
    
    if update_info_high:
        print(f"✅ 检测到创新高: {update_info_high['new_value']:.2f}%")
        print("📤 发送Telegram通知...")
        monitor.send_telegram_notification(update_info_high)
    else:
        print("⏸️ 未达到新高，无需更新")
    
    # 测试2: 检查并更新创新低的情况
    print("\n【测试2】检查ETH做空创新低...")
    update_info_low = monitor.check_and_update_extreme(mock_position_low)
    
    if update_info_low:
        print(f"✅ 检测到创新低: {update_info_low['new_value']:.2f}%")
        print("📤 发送Telegram通知...")
        monitor.send_telegram_notification(update_info_low)
    else:
        print("⏸️ 未达到新低，无需更新")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)


if __name__ == '__main__':
    test_with_mock_data()
