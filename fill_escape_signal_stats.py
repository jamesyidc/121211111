#!/usr/bin/env python3
"""
补全逃顶信号统计数据
从 support_resistance_snapshots JSONL 计算 24h/2h 信号数并填入 escape_signal_stats (SQLite + JSONL)
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
import pytz

def calculate_signal_counts_from_jsonl(snapshots, target_time):
    """
    从JSONL快照数据计算指定时间点的24h和2h信号数
    
    逃顶信号定义：(scenario_3 + scenario_4) >= 8
    24h信号数：过去24小时内触发逃顶信号的快照数
    2h信号数：过去2小时内触发逃顶信号的快照数
    """
    # 计算时间范围
    time_24h_ago = (target_time - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    time_2h_ago = (target_time - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    target_time_str = target_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 筛选24小时内的快照
    snapshots_24h = [
        s for s in snapshots
        if time_24h_ago < s.get('snapshot_time', '') <= target_time_str
    ]
    
    # 筛选2小时内的快照
    snapshots_2h = [
        s for s in snapshots
        if time_2h_ago < s.get('snapshot_time', '') <= target_time_str
    ]
    
    # 计算逃顶信号数（scenario_3 + scenario_4 >= 8）
    signal_24h_count = sum(
        1 for s in snapshots_24h
        if (s.get('scenario_3_count', 0) + s.get('scenario_4_count', 0)) >= 8
    )
    
    signal_2h_count = sum(
        1 for s in snapshots_2h
        if (s.get('scenario_3_count', 0) + s.get('scenario_4_count', 0)) >= 8
    )
    
    # 计算最大值
    max_24h = max(
        (s.get('scenario_3_count', 0) + s.get('scenario_4_count', 0) for s in snapshots_24h),
        default=0
    )
    
    max_2h = max(
        (s.get('scenario_3_count', 0) + s.get('scenario_4_count', 0) for s in snapshots_2h),
        default=0
    )
    
    return signal_24h_count, signal_2h_count, max_24h, max_2h

def main():
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    print(f"🕐 当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 读取support_resistance_snapshots JSONL
    snapshots_file = '/home/user/webapp/data/support_resistance_jsonl/support_resistance_snapshots.jsonl'
    print(f"📂 读取快照文件: {snapshots_file}")
    
    if not os.path.exists(snapshots_file):
        print(f"❌ 快照文件不存在: {snapshots_file}")
        return
    
    # 读取所有快照
    all_snapshots = []
    with open(snapshots_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                snapshot = json.loads(line)
                all_snapshots.append(snapshot)
            except json.JSONDecodeError:
                continue
    
    print(f"📊 读取到 {len(all_snapshots)} 条快照记录")
    
    if not all_snapshots:
        print("❌ 没有快照数据")
        return
    
    # 读取escape_signal_stats JSONL获取最新时间
    escape_stats_file = '/home/user/webapp/data/escape_signal_jsonl/escape_signal_stats.jsonl'
    os.makedirs(os.path.dirname(escape_stats_file), exist_ok=True)
    
    last_stat_time = None
    if os.path.exists(escape_stats_file):
        # 读取最后一行获取最新时间
        with open(escape_stats_file, 'rb') as f:
            try:
                f.seek(-min(10000, os.path.getsize(escape_stats_file)), 2)
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].decode('utf-8').strip()
                    if last_line:
                        last_record = json.loads(last_line)
                        last_stat_time_str = last_record.get('stat_time')
                        if last_stat_time_str:
                            last_stat_time = datetime.strptime(last_stat_time_str, '%Y-%m-%d %H:%M:%S')
                            last_stat_time = beijing_tz.localize(last_stat_time)
                            print(f"📊 escape_signal_stats 最新记录: {last_stat_time_str}")
            except:
                pass
    
    if not last_stat_time:
        # 如果没有记录，从最早的快照开始
        first_snapshot = min(all_snapshots, key=lambda s: s.get('snapshot_time', ''))
        first_time_str = first_snapshot.get('snapshot_time')
        last_stat_time = datetime.strptime(first_time_str, '%Y-%m-%d %H:%M:%S')
        last_stat_time = beijing_tz.localize(last_stat_time) - timedelta(minutes=1)
        print(f"📊 escape_signal_stats 为空，从 {first_time_str} 开始")
    
    # 获取所有新的快照（在 last_stat_time 之后）
    last_stat_time_str = last_stat_time.strftime('%Y-%m-%d %H:%M:%S')
    new_snapshots = [
        s for s in all_snapshots
        if s.get('snapshot_time', '') > last_stat_time_str
    ]
    new_snapshots.sort(key=lambda s: s.get('snapshot_time', ''))
    
    print(f"📈 找到 {len(new_snapshots)} 条新快照需要处理")
    
    if not new_snapshots:
        print("✅ 没有新数据需要补全")
        return
    
    # 连接SQLite数据库
    crypto_conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
    crypto_cursor = crypto_conn.cursor()
    
    # 处理每个快照
    inserted_count = 0
    with open(escape_stats_file, 'a', encoding='utf-8') as jsonl_f:
        for idx, snapshot in enumerate(new_snapshots):
            snapshot_time_str = snapshot.get('snapshot_time')
            snapshot_time = datetime.strptime(snapshot_time_str, '%Y-%m-%d %H:%M:%S')
            snapshot_time = beijing_tz.localize(snapshot_time)
            
            # 计算信号数
            signal_24h, signal_2h, max_24h, max_2h = calculate_signal_counts_from_jsonl(
                all_snapshots, snapshot_time
            )
            
            # 简单的强度等级计算
            decline_level = 0
            rise_level = 0
            
            # 插入SQLite
            crypto_cursor.execute('''
                INSERT INTO escape_signal_stats 
                (stat_time, signal_24h_count, signal_2h_count, 
                 decline_strength_level, rise_strength_level,
                 max_signal_24h, max_signal_2h, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_time.strftime('%Y-%m-%d %H:%M:%S'),
                signal_24h,
                signal_2h,
                decline_level,
                rise_level,
                max_24h,
                max_2h,
                now.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # 写入JSONL
            jsonl_record = {
                'stat_time': snapshot_time.strftime('%Y-%m-%d %H:%M:%S'),
                'signal_24h_count': signal_24h,
                'signal_2h_count': signal_2h,
                'decline_strength_level': decline_level,
                'rise_strength_level': rise_level,
                'max_signal_24h': max_24h,
                'max_signal_2h': max_2h,
                'created_at': now.strftime('%Y-%m-%d %H:%M:%S')
            }
            jsonl_f.write(json.dumps(jsonl_record, ensure_ascii=False) + '\n')
            
            inserted_count += 1
            
            # 每100条显示一次进度
            if (idx + 1) % 100 == 0:
                print(f"  处理中... {idx + 1}/{len(new_snapshots)}")
    
    # 提交SQLite更改
    crypto_conn.commit()
    
    print(f"\n✅ 成功补全 {inserted_count} 条记录（SQLite + JSONL）")
    
    # 验证最新数据
    crypto_cursor.execute('''
        SELECT stat_time, signal_24h_count, signal_2h_count
        FROM escape_signal_stats
        ORDER BY stat_time DESC
        LIMIT 5
    ''')
    
    print(f"\n📋 最新5条记录：")
    for row in crypto_cursor.fetchall():
        print(f"  {row[0]}: 24h={row[1]}, 2h={row[2]}")
    
    # 关闭连接
    crypto_conn.close()

if __name__ == '__main__':
    main()
