#!/usr/bin/env python3
"""
从Google Drive导入信号历史数据
从 信号.txt 文件读取历史数据并导入到数据库
数据格式: 做空|变化|做多|变化|时间
"""
import requests
import sqlite3
from datetime import datetime
import re

def fetch_signal_txt():
    """
    从外部API获取信号.txt的内容
    基于 https://8080-ieo4kftymfy546kbm6o33-2e77fc33.sandbox.novita.ai/filtered-signals.html
    """
    # 尝试多个可能的URL
    possible_urls = [
        "https://8080-ieo4kftymfy546kbm6o33-2e77fc33.sandbox.novita.ai/signal_data/信号.txt",
        "https://8080-ieo4kftymfy546kbm6o33-2e77fc33.sandbox.novita.ai/信号.txt",
        "https://8080-ieo4kftymfy546kbm6o33-2e77fc33.sandbox.novita.ai/data/信号.txt",
    ]
    
    for url in possible_urls:
        try:
            print(f"尝试URL: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ 成功获取文件")
                return response.text
        except Exception as e:
            print(f"   失败: {e}")
            continue
    
    return None

def parse_signal_line(line):
    """
    解析一行信号数据
    格式: 做空|变化|做多|变化|时间
    例如: 119|0|0|0|2025-12-03 12:28:31
    返回: (short_count, short_change, long_count, long_change, record_time)
    """
    parts = line.strip().split('|')
    if len(parts) != 5:
        return None
    
    try:
        short_count = int(parts[0])
        short_change = int(parts[1])
        long_count = int(parts[2])
        long_change = int(parts[3])
        record_time = parts[4].strip()
        
        # 验证时间格式
        datetime.strptime(record_time, '%Y-%m-%d %H:%M:%S')
        
        return {
            'short_count': short_count,
            'short_change': short_change,
            'long_count': long_count,
            'long_change': long_change,
            'record_time': record_time
        }
    except Exception as e:
        print(f"⚠️  解析失败: {line} - {e}")
        return None

def import_to_database(records):
    """导入记录到数据库"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    
    for record in records:
        # 检查记录是否已存在
        cursor.execute(
            'SELECT id FROM signal_stats_history WHERE record_time = ?',
            (record['record_time'],)
        )
        if cursor.fetchone():
            skipped += 1
            continue
        
        # 计算总数和细分统计
        total_count = record['short_count'] + record['long_count']
        
        # 插入记录
        cursor.execute('''
            INSERT INTO signal_stats_history 
            (record_time, total_count, long_count, short_count,
             chaodi_count, dibu_count, dingbu_count, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record['record_time'],
            total_count,
            record['long_count'],
            record['short_count'],
            0,  # 暂时没有细分数据
            0,
            0,
            'signal.txt'
        ))
        
        imported += 1
    
    conn.commit()
    conn.close()
    
    return imported, skipped

def main():
    """主函数"""
    print("=" * 70)
    print("导入信号历史数据（从 信号.txt）")
    print("=" * 70)
    
    # 方案1: 尝试从API获取
    print("\n1. 尝试从API获取 信号.txt...")
    content = fetch_signal_txt()
    
    if not content:
        print("\n⚠️  无法从API获取文件，请提供文件内容")
        print("\n请将 信号.txt 的内容复制粘贴到这里，输入完成后按 Ctrl+D:")
        print("-" * 70)
        
        import sys
        content = sys.stdin.read()
    
    # 解析数据
    print("\n2. 解析数据...")
    lines = content.strip().split('\n')
    records = []
    
    for line in lines:
        if line.strip():
            record = parse_signal_line(line)
            if record:
                records.append(record)
    
    print(f"✅ 成功解析 {len(records)} 条记录")
    
    if records:
        # 显示时间范围
        times = [r['record_time'] for r in records]
        print(f"   时间范围: {min(times)} ~ {max(times)}")
        
        # 显示前3条和后3条
        print("\n前3条:")
        for r in records[:3]:
            print(f"   {r['record_time']}: 做空={r['short_count']}, 做多={r['long_count']}, 总计={r['short_count']+r['long_count']}")
        
        print("\n后3条:")
        for r in records[-3:]:
            print(f"   {r['record_time']}: 做空={r['short_count']}, 做多={r['long_count']}, 总计={r['short_count']+r['long_count']}")
    
    # 导入到数据库
    print("\n3. 导入到数据库...")
    imported, skipped = import_to_database(records)
    
    print(f"✅ 导入完成")
    print(f"   新增: {imported} 条")
    print(f"   跳过: {skipped} 条（已存在）")
    
    # 显示数据库统计
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM signal_stats_history')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM signal_stats_history')
    time_range = cursor.fetchone()
    
    conn.close()
    
    print(f"\n📊 数据库统计:")
    print(f"   总记录数: {total}")
    print(f"   时间范围: {time_range[0]} ~ {time_range[1]}")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
