#!/usr/bin/env python3
"""
测试后台数据采集周期是否正常工作
监控API日志，验证每3分钟执行一次数据更新
"""
import time
import re
from datetime import datetime

print("="*70)
print("📊 数据采集周期测试")
print("="*70)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("监控周期: 12分钟 (应该看到4次数据更新)")
print("="*70)

# 读取日志文件的当前位置
log_file = '/home/user/webapp/api_v2.log'
with open(log_file, 'r') as f:
    f.seek(0, 2)  # 移动到文件末尾
    current_pos = f.tell()

updates = []
start_time = time.time()
test_duration = 12 * 60  # 12分钟

print("\n🔍 开始监控日志...\n")

try:
    while time.time() - start_time < test_duration:
        with open(log_file, 'r') as f:
            f.seek(current_pos)
            new_lines = f.readlines()
            current_pos = f.tell()
            
            for line in new_lines:
                # 查找数据更新完成的日志
                if '数据更新完成' in line:
                    # 提取时间
                    time_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', line)
                    duration_match = re.search(r'耗时: ([\d.]+)秒', line)
                    
                    if time_match:
                        update_time = time_match.group(1)
                        duration = duration_match.group(1) if duration_match else 'N/A'
                        updates.append({
                            'time': update_time,
                            'duration': duration,
                            'timestamp': time.time()
                        })
                        
                        print(f"✅ 第{len(updates)}次更新:")
                        print(f"   时间: {update_time}")
                        print(f"   耗时: {duration}秒")
                        
                        # 计算与上次更新的间隔
                        if len(updates) > 1:
                            interval = updates[-1]['timestamp'] - updates[-2]['timestamp']
                            print(f"   间隔: {interval:.0f}秒 (预期: 180秒)")
                            
                            # 判断间隔是否正确
                            if 175 <= interval <= 185:
                                print(f"   ✅ 间隔正常")
                            else:
                                print(f"   ⚠️  间隔异常！")
                        print()
        
        time.sleep(1)  # 每秒检查一次

except KeyboardInterrupt:
    print("\n\n⏹️  测试中断")

print("\n" + "="*70)
print("📊 测试结果统计")
print("="*70)
print(f"测试时长: {(time.time() - start_time)/60:.1f}分钟")
print(f"捕获更新次数: {len(updates)}")

if len(updates) >= 2:
    intervals = []
    for i in range(1, len(updates)):
        interval = updates[i]['timestamp'] - updates[i-1]['timestamp']
        intervals.append(interval)
    
    avg_interval = sum(intervals) / len(intervals)
    print(f"\n平均更新间隔: {avg_interval:.0f}秒")
    print(f"预期间隔: 180秒")
    
    if 175 <= avg_interval <= 185:
        print("\n✅ 结论: 数据采集周期正常，每3分钟更新一次")
    else:
        print(f"\n⚠️  结论: 数据采集周期异常，实际间隔为 {avg_interval:.0f}秒")
else:
    print("\n⚠️  捕获的更新次数不足，无法计算间隔")

print("="*70)
