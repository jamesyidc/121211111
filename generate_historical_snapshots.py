#!/usr/bin/env python3
"""
从历史level数据生成快照数据
用于填补2025-12-25到2026-01-27期间缺失的快照数据
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')

from support_resistance_daily_manager import SupportResistanceDailyManager

def analyze_levels_for_snapshot(levels: List[Dict]) -> Dict:
    """
    从level数据分析生成快照统计
    
    Args:
        levels: level数据列表（每个币种的最新数据）
    
    Returns:
        快照统计数据
    """
    scenario_1_coins = []
    scenario_2_coins = []
    scenario_3_coins = []
    scenario_4_coins = []
    
    for level in levels:
        data = level.get('data', level)
        symbol = data.get('symbol', '')
        current_price = data.get('current_price', 0)
        
        # 获取位置百分比
        position_7d = data.get('position_7d', 0) or 0
        position_48h = data.get('position_48h', 0) or 0
        
        # 情况1: 7天位置 <= 10% (接近支撑线2，7天最低点)
        if position_7d <= 10:
            scenario_1_coins.append({
                'symbol': symbol,
                'current_price': current_price,
                'position': position_7d,
                'support_line_2': data.get('support_line_2', 0),
                'resistance_line_1': data.get('resistance_line_1', 0)
            })
        
        # 情况2: 7天位置 <= 10% (也是接近支撑线1)
        if position_7d <= 10:
            scenario_2_coins.append({
                'symbol': symbol,
                'current_price': current_price,
                'position': position_7d,
                'support_line_1': data.get('support_line_1', 0),
                'resistance_line_2': data.get('resistance_line_2', 0)
            })
        
        # 情况3: 48小时位置 >= 90% (接近压力线2，48小时最高点)
        if position_48h >= 90:
            scenario_3_coins.append({
                'symbol': symbol,
                'current_price': current_price,
                'position': position_48h,
                'support_line_1': data.get('support_line_1', 0),
                'resistance_line_2': data.get('resistance_line_2', 0)
            })
        
        # 情况4: 48小时位置 >= 90% (也是接近压力线1)
        if position_48h >= 90:
            scenario_4_coins.append({
                'symbol': symbol,
                'current_price': current_price,
                'position': position_48h,
                'support_line_1': data.get('support_line_1', 0),
                'resistance_line_1': data.get('resistance_line_1', 0)
            })
    
    return {
        'scenario_1': {
            'count': len(scenario_1_coins),
            'coins': scenario_1_coins
        },
        'scenario_2': {
            'count': len(scenario_2_coins),
            'coins': scenario_2_coins
        },
        'scenario_3': {
            'count': len(scenario_3_coins),
            'coins': scenario_3_coins
        },
        'scenario_4': {
            'count': len(scenario_4_coins),
            'coins': scenario_4_coins
        },
        'total_coins': len(levels)
    }

def generate_snapshots_for_date(manager: SupportResistanceDailyManager, date_str: str, interval_minutes: int = 60):
    """
    为指定日期生成快照数据
    
    Args:
        manager: 数据管理器
        date_str: 日期字符串（YYYYMMDD）
        interval_minutes: 快照间隔（分钟），默认60分钟
    """
    print(f"\n📅 处理日期: {date_str}")
    
    # 读取该日期的所有level数据
    all_levels = manager.read_date_records(date_str, record_type='level')
    
    if not all_levels:
        print(f"  ⚠️  没有level数据，跳过")
        return 0
    
    print(f"  📊 找到 {len(all_levels)} 条level记录")
    
    # 按时间戳分组（每个interval_minutes一组）
    # 提取所有时间戳
    timestamps = []
    for level in all_levels:
        ts_str = level.get('timestamp', '')
        if ts_str:
            try:
                # 解析时间戳
                if 'T' in ts_str:
                    # ISO格式: 2026-01-23T00:00:01
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                else:
                    # 其他格式
                    ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                timestamps.append(ts)
            except:
                pass
    
    if not timestamps:
        print(f"  ⚠️  无法解析时间戳，跳过")
        return 0
    
    # 确定时间范围
    min_time = min(timestamps)
    max_time = max(timestamps)
    
    print(f"  ⏰ 时间范围: {min_time} 至 {max_time}")
    
    # 生成快照时间点（每interval_minutes一个）
    current_time = min_time.replace(minute=0, second=0, microsecond=0)
    snapshot_count = 0
    
    while current_time <= max_time:
        # 找到该时间点前后的所有level数据（取最接近的）
        time_window_start = current_time
        time_window_end = current_time + timedelta(minutes=interval_minutes)
        
        # 按币种分组，每个币种取该时间窗口内最后一条记录
        symbol_latest = {}
        
        for level in all_levels:
            ts_str = level.get('timestamp', '')
            if not ts_str:
                continue
            
            try:
                if 'T' in ts_str:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                else:
                    ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                
                # 如果时间戳在窗口内
                if time_window_start <= ts < time_window_end:
                    data = level.get('data', level)
                    symbol = data.get('symbol', '')
                    
                    if symbol:
                        # 保留最新的记录
                        if symbol not in symbol_latest or ts > symbol_latest[symbol]['ts']:
                            symbol_latest[symbol] = {
                                'ts': ts,
                                'level': level
                            }
            except:
                pass
        
        # 如果该时间窗口有数据，生成快照
        if symbol_latest:
            levels = [item['level'] for item in symbol_latest.values()]
            
            # 分析生成快照
            analysis = analyze_levels_for_snapshot(levels)
            
            # 快照时间使用窗口开始时间
            snapshot_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
            snapshot_date = current_time.strftime('%Y-%m-%d')
            
            # 构建快照数据
            snapshot_data = {
                'snapshot_time': snapshot_time,
                'snapshot_date': snapshot_date,
                'snapshot_time_beijing': snapshot_time,
                'snapshot_date_beijing': snapshot_date,
                'scenario_1_count': analysis['scenario_1']['count'],
                'scenario_2_count': analysis['scenario_2']['count'],
                'scenario_3_count': analysis['scenario_3']['count'],
                'scenario_4_count': analysis['scenario_4']['count'],
                'scenario_1_coins': analysis['scenario_1']['coins'],
                'scenario_2_coins': analysis['scenario_2']['coins'],
                'scenario_3_coins': analysis['scenario_3']['coins'],
                'scenario_4_coins': analysis['scenario_4']['coins'],
                'total_coins': analysis['total_coins'],
                'created_at': snapshot_time,
                'created_at_beijing': snapshot_time
            }
            
            # 写入快照
            manager.write_snapshot_record(snapshot_data)
            snapshot_count += 1
            
            # 每10个快照打印一次进度
            if snapshot_count % 10 == 0:
                print(f"  ✅ 已生成 {snapshot_count} 个快照 (最新: {snapshot_time})")
        
        # 移动到下一个时间窗口
        current_time += timedelta(minutes=interval_minutes)
    
    print(f"  ✅ 完成! 共生成 {snapshot_count} 个快照")
    return snapshot_count

def main():
    """主函数"""
    print("="*80)
    print("🎯 从历史level数据生成快照")
    print("="*80)
    
    manager = SupportResistanceDailyManager()
    
    # 获取所有可用日期
    available_dates = manager.get_available_dates()
    print(f"\n📊 发现 {len(available_dates)} 个日期")
    print(f"   最早: {available_dates[0]}")
    print(f"   最晚: {available_dates[-1]}")
    
    # 排除今天（2026-01-28），因为今天已经有实时快照采集器在运行
    today = datetime.now().strftime('%Y%m%d')
    dates_to_process = [d for d in available_dates if d < today]
    
    print(f"\n🎯 需要处理的日期: {len(dates_to_process)} 个")
    print(f"   (排除今天 {today}，因为有实时采集器)")
    
    if not dates_to_process:
        print("\n✅ 没有需要处理的日期")
        return
    
    # 确认
    print("\n" + "="*80)
    print("⚠️  准备生成快照数据，每小时生成一个快照")
    print("="*80)
    
    response = input("\n是否继续? (y/n): ")
    if response.lower() != 'y':
        print("❌ 取消操作")
        return
    
    # 开始处理
    total_snapshots = 0
    start_time = datetime.now()
    
    for date_str in dates_to_process:
        snapshots = generate_snapshots_for_date(manager, date_str, interval_minutes=60)
        total_snapshots += snapshots
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*80)
    print("✅ 全部完成!")
    print("="*80)
    print(f"📊 处理日期数: {len(dates_to_process)}")
    print(f"📸 生成快照数: {total_snapshots}")
    print(f"⏱️  耗时: {duration:.1f} 秒")
    print(f"⚡ 平均速度: {total_snapshots/duration:.1f} 快照/秒")
    print("="*80)

if __name__ == '__main__':
    main()
