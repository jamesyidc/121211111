#!/usr/bin/env python3
"""
解析逃顶信号统计TXT文件并导入数据库
"""

import re
import sqlite3
from datetime import datetime

def parse_signal_count(text):
    """解析 '50 个信号' 格式，返回数字"""
    match = re.search(r'(\d+)\s*个信号', text)
    return int(match.group(1)) if match else 0

def parse_level(text):
    """解析强度等级 '0级 正常' 或 '📈 3级 高'"""
    if '0级' in text or '正常' in text:
        return 0
    match = re.search(r'(\d+)级', text)
    return int(match.group(1)) if match else 0

def parse_txt_file(file_path):
    """解析TXT文件"""
    records = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到数据开始行（"记录时间"标题行之后）
    data_started = False
    for line in lines:
        line = line.strip()
        
        if '记录时间' in line and '24小时信号数' in line:
            data_started = True
            continue
        
        if not data_started or not line:
            continue
        
        # 解析数据行，使用tab分隔
        parts = line.split('\t')
        if len(parts) < 6:
            continue
        
        try:
            stat_time = parts[0].strip()
            signal_24h = parse_signal_count(parts[1])
            signal_2h = parse_signal_count(parts[2])
            decline_level = parse_level(parts[3])
            rise_level = parse_level(parts[4])
            # status = parts[5] 不需要存储
            
            # 验证时间格式
            datetime.strptime(stat_time, '%Y-%m-%d %H:%M:%S')
            
            records.append({
                'stat_time': stat_time,
                'signal_24h_count': signal_24h,
                'signal_2h_count': signal_2h,
                'decline_strength_level': decline_level,
                'rise_strength_level': rise_level
            })
        except Exception as e:
            # print(f"跳过行: {line[:50]}... 错误: {e}")
            continue
    
    return records

def import_to_database(records):
    """导入数据到数据库"""
    db_path = '/home/user/webapp/databases/crypto_data.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for record in records:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO escape_signal_stats 
                (stat_time, signal_24h_count, signal_2h_count, 
                 decline_strength_level, rise_strength_level)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                record['stat_time'],
                record['signal_24h_count'],
                record['signal_2h_count'],
                record['decline_strength_level'],
                record['rise_strength_level']
            ))
            
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
                
        except Exception as e:
            print(f"导入失败 {record['stat_time']}: {e}")
            skipped += 1
    
    conn.commit()
    conn.close()
    
    return inserted, skipped

def main():
    file_path = '/home/user/uploaded_files/0106034逃顶信号统计.txt'
    
    print("="*100)
    print("开始解析文件...")
    print("="*100)
    
    records = parse_txt_file(file_path)
    print(f"\n✅ 解析完成: {len(records)} 条记录")
    
    if records:
        # 显示前5条
        print("\n前5条记录:")
        for i, r in enumerate(records[:5], 1):
            print(f"{i}. {r['stat_time']}: 24h={r['signal_24h_count']}, 2h={r['signal_2h_count']}, "
                  f"下跌={r['decline_strength_level']}, 上涨={r['rise_strength_level']}")
        
        # 显示时间范围
        print(f"\n时间范围:")
        print(f"  最早: {records[-1]['stat_time']}")
        print(f"  最晚: {records[0]['stat_time']}")
        
        print("\n开始导入数据库...")
        inserted, skipped = import_to_database(records)
        
        print("\n" + "="*100)
        print("导入完成")
        print("="*100)
        print(f"✅ 成功导入: {inserted} 条")
        print(f"⏭️  已存在跳过: {skipped} 条")
        print(f"📊 总记录数: {len(records)} 条")
    else:
        print("\n❌ 没有解析到数据")

if __name__ == "__main__":
    main()
