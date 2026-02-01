#!/usr/bin/env python3
"""
演示文件名解析功能
不需要Google Drive API，用于测试文件名解析逻辑
"""

import re
from datetime import datetime
import pytz

def get_beijing_date():
    """获取北京时间的今天日期"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    beijing_time = datetime.now(beijing_tz)
    return beijing_time.strftime('%Y-%m-%d')

def parse_filename_timestamp(filename):
    """
    从文件名中解析时间戳
    格式: YYYY-MM-DD_HHMM.txt
    例如: 2025-12-02_1806.txt = 2025年12月2日 18:06
    """
    pattern = r'(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})\.txt'
    match = re.match(pattern, filename)
    
    if match:
        year, month, day, hour, minute = match.groups()
        try:
            dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
            beijing_tz = pytz.timezone('Asia/Shanghai')
            dt = beijing_tz.localize(dt)
            return dt
        except ValueError:
            return None
    return None

def find_latest_file(filenames):
    """找出文件名列表中最新的文件"""
    files_with_time = []
    
    for filename in filenames:
        timestamp = parse_filename_timestamp(filename)
        if timestamp:
            files_with_time.append((filename, timestamp))
    
    if not files_with_time:
        return None
    
    # 按时间戳降序排序
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    return files_with_time[0]

def demo():
    print("=" * 80)
    print("📁 文件名解析演示")
    print("=" * 80)
    print("文件命名格式: YYYY-MM-DD_HHMM.txt")
    print("=" * 80)
    
    # 示例文件列表
    example_files = [
        "2025-12-02_0830.txt",
        "2025-12-02_1245.txt",
        "2025-12-02_1806.txt",  # 最新的
        "2025-12-02_1530.txt",
        "2025-12-02_0915.txt",
    ]
    
    print(f"\n📅 今天的日期: {get_beijing_date()}")
    print(f"\n📄 示例文件列表 ({len(example_files)} 个文件):")
    for f in example_files:
        print(f"  - {f}")
    
    print("\n" + "=" * 80)
    print("🔍 解析结果:")
    print("=" * 80)
    
    # 解析每个文件
    files_with_time = []
    for filename in example_files:
        timestamp = parse_filename_timestamp(filename)
        if timestamp:
            files_with_time.append((filename, timestamp))
            hour = timestamp.strftime('%H')
            minute = timestamp.strftime('%M')
            print(f"\n{filename}")
            print(f"  → 时间: {timestamp.strftime('%Y-%m-%d %H:%M')} (北京时间)")
            print(f"  → 含义: {timestamp.year}年{timestamp.month}月{timestamp.day}日 {hour}点{minute}分")
    
    # 排序
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    print("\n" + "=" * 80)
    print("📋 按时间排序 (最新 → 最旧):")
    print("=" * 80)
    
    for idx, (filename, timestamp) in enumerate(files_with_time, 1):
        time_str = filename.split('_')[1].replace('.txt', '')
        hour = time_str[:2]
        minute = time_str[2:4]
        print(f"\n[{idx}] {filename}")
        print(f"    时间: {timestamp.strftime('%Y-%m-%d')} {hour}:{minute}")
    
    # 找出最新的
    latest = find_latest_file(example_files)
    
    if latest:
        filename, timestamp = latest
        time_str = filename.split('_')[1].replace('.txt', '')
        hour = time_str[:2]
        minute = time_str[2:4]
        
        print("\n" + "=" * 80)
        print("🎯 最新的txt文件:")
        print("=" * 80)
        print(f"文件名: {filename}")
        print(f"时间: {timestamp.strftime('%Y-%m-%d')} {hour}:{minute}")
        print(f"含义: {timestamp.year}年{timestamp.month}月{timestamp.day}日 {hour}点{minute}分")
        print("=" * 80)
        
        print("\n" + "=" * 80)
        print("📌 简洁答案:")
        print("=" * 80)
        print(f"最新txt文件是: {filename}")
        print(f"更新时间: {hour}点{minute}分")
        print("=" * 80)

if __name__ == "__main__":
    demo()
