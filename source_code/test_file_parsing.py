#!/usr/bin/env python3
"""
测试文件名解析逻辑
验证是否能正确识别和排序时间戳格式的文件名
"""

import re
from datetime import datetime

def test_filename_parsing():
    """测试文件名解析"""
    
    # 模拟的文件列表（你的 Google Drive 文件夹中的文件）
    test_files = [
        "2025-12-02_1917.txt",
        "2025-12-02_1927.txt",
        "2025-12-02_1937.txt",
        "2025-12-02_1947.txt",
        "2025-12-02_2238.txt",  # 最新的
        "2025-12-02_2228.txt",
        "2025-12-02_2218.txt",
        "2025-12-02_2128.txt",
        "信号.txt",  # 没有时间戳的文件
    ]
    
    print("="*80)
    print("📁 文件列表（共 {} 个文件）".format(len(test_files)))
    print("="*80)
    for i, filename in enumerate(test_files, 1):
        print(f"{i:2d}. {filename}")
    
    print("\n" + "="*80)
    print("🔍 解析时间戳并排序")
    print("="*80)
    
    timestamped_files = []
    
    for filename in test_files:
        # 尝试从文件名提取时间戳：YYYY-MM-DD_HHMM
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
        if match:
            date_str = match.group(1)  # 2025-12-02
            time_str = match.group(2)  # 2238
            timestamp_str = f"{date_str} {time_str[:2]}:{time_str[2:]}"  # 2025-12-02 22:38
            timestamped_files.append((filename, timestamp_str))
            print(f"✅ {filename:30s} → {timestamp_str}")
        else:
            print(f"⚠️  {filename:30s} → 无时间戳格式")
    
    if timestamped_files:
        print("\n" + "="*80)
        print("📊 按时间戳排序（最新在前）")
        print("="*80)
        
        # 按时间戳降序排序
        timestamped_files.sort(key=lambda x: x[1], reverse=True)
        
        for i, (filename, timestamp) in enumerate(timestamped_files, 1):
            marker = "🏆 最新" if i == 1 else "  "
            print(f"{marker} {i:2d}. {timestamp} - {filename}")
        
        latest_file, latest_time = timestamped_files[0]
        print("\n" + "="*80)
        print(f"✨ 系统将使用: {latest_file}")
        print(f"   时间戳: {latest_time}")
        print("="*80)
    else:
        print("\n❌ 没有找到时间戳格式的文件")

def test_content_parsing():
    """测试文件内容解析"""
    
    print("\n\n" + "="*80)
    print("📄 测试文件内容解析")
    print("="*80)
    
    # 模拟文件内容（你的 TXT 文件格式）
    test_content = "146|0|0|0|2025-12-02 22:38:00"
    
    print(f"\n文件内容: {test_content}")
    print("\n解析结果:")
    print("-"*80)
    
    # 解析格式：做空信号|变化|做多信号|变化|时间
    parts = test_content.strip().split('|')
    
    if len(parts) >= 5:
        short_signal = int(parts[0])
        short_change = int(parts[1])
        long_signal = int(parts[2])
        long_change = int(parts[3])
        update_time = parts[4]
        
        print(f"🔴 做空信号: {short_signal}")
        print(f"   变化: {short_change:+d}")
        print(f"🟢 做多信号: {long_signal}")
        print(f"   变化: {long_change:+d}")
        print(f"📅 更新时间: {update_time}")
        
        result = {
            'short': short_signal,
            'short_change': short_change,
            'long': long_signal,
            'long_change': long_change,
            'update_time': update_time
        }
        
        print("\n返回的数据字典:")
        print(result)
    else:
        print(f"❌ 格式错误，期望5个字段，实际得到 {len(parts)} 个")
    
    print("-"*80)

if __name__ == '__main__':
    test_filename_parsing()
    test_content_parsing()
    
    print("\n\n" + "="*80)
    print("✅ 测试完成")
    print("="*80)
    print("\n📝 总结:")
    print("1. 系统会按北京时间查找今天的文件夹（如 2025-12-02）")
    print("2. 在文件夹中查找所有 .txt 文件")
    print("3. 按文件名中的时间戳排序（YYYY-MM-DD_HHMM.txt）")
    print("4. 选择时间最新的文件")
    print("5. 读取并解析内容（格式：做空|变化|做多|变化|时间）")
    print("\n")
