#!/usr/bin/env python3
"""
测试：持续时间每30秒自动更新演示
"""

import time
from datetime import datetime, timedelta

def format_duration(record_time_str):
    """计算持续时间并格式化"""
    record_time = datetime.strptime(record_time_str, '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    diff = now - record_time
    
    total_hours = diff.total_seconds() / 3600
    hours = int(total_hours)
    minutes = int((diff.total_seconds() % 3600) / 60)
    days = hours // 24
    remain_hours = hours % 24
    
    if hours < 1:
        color = '绿色'
        text = f"{minutes}分钟"
    elif hours < 24:
        color = '蓝色'
        text = f"{hours}小时{minutes}分"
    elif days == 1:
        color = '黄色'
        text = f"{days}天{remain_hours}小时"
    elif days == 2:
        color = '橙色'
        text = f"{days}天{remain_hours}小时"
    else:
        color = '红色'
        text = f"{days}天{remain_hours}小时"
    
    return text, color

print("\n" + "="*80)
print("持续时间自动更新演示（每30秒更新一次）")
print("="*80 + "\n")

# 模拟一些历史记录
test_records = [
    {'inst_id': 'UNI-USDT-SWAP', 'time': '2025-12-29 20:16:10', 'profit': '+52.97%'},
    {'inst_id': 'CRO-USDT-SWAP', 'time': '2025-12-29 20:18:22', 'profit': '+24.45%'},
    {'inst_id': 'HBAR-USDT-SWAP', 'time': '2025-12-29 17:02:11', 'profit': '-5.40%'},
]

for i in range(3):
    print(f"{'第' + str(i+1) + '次更新' if i > 0 else '初始加载'} (当前时间: {datetime.now().strftime('%H:%M:%S')})")
    print("-" * 80)
    
    for record in test_records:
        duration_text, color = format_duration(record['time'])
        print(f"  {record['inst_id']:20} {record['profit']:10} | 持续时间: {duration_text:20} ({color})")
    
    print()
    
    if i < 2:
        print("⏰ 等待30秒后更新...\n")
        time.sleep(30)

print("="*80)
print("✅ 演示完成！前端实现：")
print("   1. 页面加载时：loadData() → 获取数据 → renderRecordsTable() → 显示持续时间")
print("   2. 每30秒：updateDurations() → 仅更新持续时间列（不重新渲染整个表格）")
print("   3. 每30秒：refreshData() → 重新获取数据并渲染（包括持续时间）")
print("="*80 + "\n")
