#!/usr/bin/env python3
"""
持续时间自动更新可视化演示
展示前端如何每30秒自动更新持续时间
"""

import time
from datetime import datetime

def clear_screen():
    print("\033[2J\033[H", end="")

def format_duration(seconds):
    """格式化持续时间并返回颜色"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    days = hours // 24
    remain_hours = hours % 24
    
    if hours < 1:
        color = '\033[92m'  # 绿色
        text = f"{minutes}分钟"
    elif hours < 24:
        color = '\033[94m'  # 蓝色
        text = f"{hours}小时{minutes}分"
    elif days == 1:
        color = '\033[93m'  # 黄色
        text = f"{days}天{remain_hours}小时"
    elif days == 2:
        color = '\033[33m'  # 橙色
        text = f"{days}天{remain_hours}小时"
    else:
        color = '\033[91m'  # 红色
        text = f"{days}天{remain_hours}小时"
    
    return f"{color}{text}\033[0m"

def main():
    print("\n" + "="*100)
    print("持续时间自动更新可视化演示".center(100))
    print("每30秒自动更新一次（演示用：每5秒）".center(100))
    print("="*100 + "\n")
    
    # 模拟不同时间点的记录
    base_time = datetime.now()
    test_cases = [
        {'name': 'UNI-USDT-SWAP', 'profit': '+52.97%', 'age_seconds': 2820},   # 47分钟
        {'name': 'CRO-USDT-SWAP', 'profit': '+24.45%', 'age_seconds': 2700},   # 45分钟
        {'name': 'DOT-USDT-SWAP', 'profit': '+43.13%', 'age_seconds': 155700}, # 43小时15分
        {'name': 'BCH-USDT-SWAP', 'profit': '+28.30%', 'age_seconds': 86400},  # 1天
        {'name': 'FIL-USDT-SWAP', 'profit': '+25.13%', 'age_seconds': 172800}, # 2天
        {'name': 'STX-USDT-SWAP', 'profit': '+31.38%', 'age_seconds': 259200}, # 3天
    ]
    
    print("⏰ 页面加载完成，启动定时器...\n")
    time.sleep(2)
    
    for cycle in range(4):
        clear_screen()
        
        current_time = datetime.now()
        time_diff = int((current_time - base_time).total_seconds())
        
        print("\n" + "="*100)
        print(f"第 {cycle+1} 次更新".center(100))
        print(f"当前时间: {current_time.strftime('%H:%M:%S')}".center(100))
        print("="*100 + "\n")
        
        print(f"{'币种':<20} {'收益率':<12} {'持续时间':<30} {'颜色等级':<15}")
        print("-"*100)
        
        for case in test_cases:
            age = case['age_seconds'] + time_diff
            duration = format_duration(age)
            
            hours = age // 3600
            days = hours // 24
            
            if hours < 1:
                level = "🟢 新鲜"
            elif hours < 24:
                level = "🔵 较新"
            elif days == 1:
                level = "🟡 一般"
            elif days == 2:
                level = "🟠 较旧"
            else:
                level = "🔴 陈旧"
            
            print(f"{case['name']:<20} {case['profit']:<12} {duration:<45} {level:<15}")
        
        print("\n" + "="*100)
        
        if cycle == 0:
            print("📊 初始加载完成")
        else:
            print(f"⏰ 第 {cycle} 次自动更新完成（已运行 {time_diff} 秒）")
            print("💡 updateDurations() 函数已执行，仅更新了持续时间列")
        
        print("="*100 + "\n")
        
        if cycle < 3:
            print("⏰ 等待 5 秒后自动更新...\n")
            time.sleep(5)
    
    print("\n" + "="*100)
    print("✅ 演示完成！".center(100))
    print("="*100)
    print("\n前端实现逻辑：")
    print("  1️⃣  页面加载：loadData() → renderRecordsTable() → 显示初始持续时间")
    print("  2️⃣  定时器1（30秒）：refreshData() → 重新获取数据并渲染")
    print("  3️⃣  定时器2（30秒）：updateDurations() → 仅更新持续时间列")
    print("\n性能优势：")
    print("  🚀 不重新渲染整个表格，只更新持续时间单元格")
    print("  🚀 不需要调用 API，完全在前端计算")
    print("  🚀 减少 DOM 操作，降低 CPU 使用")
    print("\n访问地址：")
    print("  🔗 https://5000-iawcy3xxhnan90u0qd9wq-cc2fbc16.sandbox.novita.ai/anchor-system-real")
    print("\n" + "="*100 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  演示已中断\n")
