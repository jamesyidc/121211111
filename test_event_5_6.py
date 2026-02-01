#!/usr/bin/env python3
"""
测试事件5和事件6的触发逻辑
"""
import sys
sys.path.insert(0, '/home/user/webapp/major-events-system')

from major_events_monitor import MajorEventsMonitor

def test_event_logic():
    """测试事件触发逻辑"""
    print("=" * 60)
    print("测试事件5和事件6的触发逻辑")
    print("=" * 60)
    
    monitor = MajorEventsMonitor()
    
    # 获取当前状态
    print("\n1. 当前profit_marks_history:")
    history = monitor.event_states.get('profit_marks_history', [])
    for i, mark in enumerate(history):
        color_emoji = "🔴" if mark['mark'] == 'red' else "🟢"
        print(f"   [{i}] {color_emoji} {mark['mark']} at {mark['datetime']}")
        print(f"       - 空单盈利≥120%: {mark.get('short_profit_120', 0)}")
        print(f"       - 空单亏损: {mark.get('short_loss', 0)}")
    
    # 显示事件触发规则
    print("\n2. 事件触发规则:")
    print("   事件5 (红→绿)：")
    print("      - 前一个标记是红色（空单盈利≥3）")
    print("      - 当前标记转为绿色（空单亏损≥3）")
    print("      - 操作：开空单")
    print("      - 含义：市场从强势转弱势")
    print()
    print("   事件6 (绿→红)：")
    print("      - 前一个标记是绿色（空单亏损≥3）")
    print("      - 当前标记转为红色（空单盈利≥3）")
    print("      - 操作：开多单")
    print("      - 含义：市场从弱势转强势")
    
    # 检查是否会触发事件
    print("\n3. 当前状态分析:")
    if len(history) >= 2:
        last = history[-1]
        prev = history[-2]
        
        last_emoji = "🔴" if last['mark'] == 'red' else "🟢"
        prev_emoji = "🔴" if prev['mark'] == 'red' else "🟢"
        
        print(f"   前一个: {prev_emoji} {prev['mark']}")
        print(f"   当前: {last_emoji} {last['mark']}")
        
        if last['mark'] != prev['mark']:
            if last['mark'] == 'green' and prev['mark'] == 'red':
                print(f"\n   ✅ 会触发事件5！")
                print(f"   🔴 → 🟢 (红转绿)")
                print(f"   操作：开空单")
            elif last['mark'] == 'red' and prev['mark'] == 'green':
                print(f"\n   ✅ 会触发事件6！")
                print(f"   🟢 → 🔴 (绿转红)")
                print(f"   操作：开多单")
        else:
            print(f"\n   ❌ 不会触发事件（颜色相同）")
    else:
        print("   历史标记少于2个，无法触发事件")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    test_event_logic()
