#!/usr/bin/env python3
"""
生成历史快照数据
从按日期存储的level数据生成快照数据
时区：统一使用北京时间 (UTC+8)
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import pytz

sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')

from support_resistance_daily_manager import SupportResistanceDailyManager

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


def calculate_alert_scenarios(data):
    """计算4种预警情景"""
    position_7d = data.get('position_7d', 0) or 0
    position_48h = data.get('position_48h', 0) or 0
    
    # 情景1: 7天位置 <= 10%
    alert_scenario_1 = position_7d <= 10
    
    # 情景2: 7天位置 <= 10%
    alert_scenario_2 = position_7d <= 10
    
    # 情景3: 48h位置 <= 10%
    alert_scenario_3 = position_48h <= 10
    
    # 情景4: 48h位置 >= 90%
    alert_scenario_4 = position_48h >= 90
    
    return alert_scenario_1, alert_scenario_2, alert_scenario_3, alert_scenario_4


def analyze_scenarios(data_list):
    """分析4种情况的统计数据"""
    scenario_1_coins = []
    scenario_2_coins = []
    scenario_3_coins = []
    scenario_4_coins = []
    
    for data in data_list:
        symbol = data.get('symbol', '')
        current_price = data.get('current_price', 0)
        position_7d = data.get('position_7d', 0) or 0
        position_48h = data.get('position_48h', 0) or 0
        
        alert_1, alert_2, alert_3, alert_4 = calculate_alert_scenarios(data)
        
        # 情景1: 7天位置 <= 10%
        if alert_1:
            scenario_1_coins.append({
                'symbol': symbol,
                'current_price': current_price,
                'position': position_7d,
                'support_2': data.get('support_line_2', 0),
                'resistance_1': data.get('resistance_line_1', 0)
            })
        
        # 情景2: 7天位置 <= 10%
        if alert_2:
            scenario_2_coins.append({
                'symbol': symbol,
                'current_price': current_price,
                'position': position_7d,
                'support_1': data.get('support_line_1', 0),
                'resistance_2': data.get('resistance_line_2', 0)
            })
        
        # 情景3: 48h位置 <= 10%
        if alert_3:
            scenario_3_coins.append({
                'symbol': symbol,
                'current_price': current_price,
                'position': position_48h,
                'support_1': data.get('support_line_1', 0),
                'resistance_2': data.get('resistance_line_2', 0)
            })
        
        # 情景4: 48h位置 >= 90%
        if alert_4:
            scenario_4_coins.append({
                'symbol': symbol,
                'current_price': current_price,
                'position': position_48h,
                'support_1': data.get('support_line_1', 0),
                'resistance_1': data.get('resistance_line_1', 0)
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
        'total_coins': len(data_list)
    }


def generate_snapshots_for_date(manager, date_str, interval_hours=1):
    """
    为指定日期生成快照数据
    
    Args:
        manager: SupportResistanceDailyManager实例
        date_str: 日期字符串（YYYYMMDD）
        interval_hours: 快照间隔（小时）
    """
    print(f"\n📅 处理日期: {date_str}")
    
    # 读取该日期的所有level数据
    all_levels = manager.read_date_records(date_str, record_type='level')
    
    if not all_levels:
        print(f"  ⚠️  该日期无level数据")
        return 0
    
    print(f"  📊 读取到 {len(all_levels)} 条level记录")
    
    # 按时间分组
    # 将记录按symbol分组，保留每个symbol的最后一条记录
    symbol_latest_data = {}
    
    for level in all_levels:
        data = level.get('data', {})
        symbol = data.get('symbol')
        timestamp = level.get('timestamp', '')
        
        if not symbol:
            continue
        
        # 保留每个symbol的最新记录
        if symbol not in symbol_latest_data or timestamp > symbol_latest_data[symbol]['timestamp']:
            symbol_latest_data[symbol] = {
                'timestamp': timestamp,
                'data': data
            }
    
    # 如果没有有效数据，跳过
    if not symbol_latest_data:
        print(f"  ⚠️  该日期无有效symbol数据")
        return 0
    
    # 提取所有币种的最新数据
    latest_data_list = [item['data'] for item in symbol_latest_data.values()]
    
    # 分析情景
    analysis = analyze_scenarios(latest_data_list)
    
    # 构建快照时间（使用该日期的中午12:00）
    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])
    
    snapshot_time_dt = datetime(year, month, day, 12, 0, 0, tzinfo=BEIJING_TZ)
    snapshot_time = snapshot_time_dt.strftime('%Y-%m-%d %H:%M:%S')
    snapshot_date = snapshot_time_dt.strftime('%Y-%m-%d')
    
    # 构建快照数据
    snapshot_data = {
        'snapshot_time': snapshot_time,
        'snapshot_date': snapshot_date,
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
        'snapshot_time_beijing': snapshot_time,
        'created_at_beijing': snapshot_time,
        'generated_from_history': True  # 标记为历史生成
    }
    
    # 直接写入指定日期的文件（不使用write_snapshot_record，因为它会使用当前日期）
    file_path = manager.get_file_path(date_str)
    
    # 构建记录
    record = {
        "type": "snapshot",
        "timestamp": snapshot_time,
        "date": date_str,
        "time": "12:00:00",
        "data": snapshot_data
    }
    
    # 追加写入JSONL
    import json
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"  ✅ 生成快照: {snapshot_time}")
    print(f"     情况1: {analysis['scenario_1']['count']} | 情况2: {analysis['scenario_2']['count']} | 情况3: {analysis['scenario_3']['count']} | 情况4: {analysis['scenario_4']['count']}")
    
    return 1


def main():
    """主函数"""
    print("="*70)
    print("🎯 生成历史快照数据")
    print("="*70)
    print()
    
    manager = SupportResistanceDailyManager()
    
    # 获取所有可用日期
    available_dates = manager.get_available_dates()
    
    if not available_dates:
        print("❌ 未找到任何日期数据")
        return
    
    print(f"📊 发现 {len(available_dates)} 个日期")
    print(f"   最早: {available_dates[0]}")
    print(f"   最晚: {available_dates[-1]}")
    print()
    
    # 跳过今天（今天已经有实时快照在运行）
    today_str = datetime.now(BEIJING_TZ).strftime('%Y%m%d')
    dates_to_process = [d for d in available_dates if d < today_str]
    
    print(f"🔄 将处理 {len(dates_to_process)} 个历史日期（跳过今天 {today_str}）")
    print()
    
    total_generated = 0
    
    for date_str in dates_to_process:
        try:
            generated = generate_snapshots_for_date(manager, date_str)
            total_generated += generated
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            continue
    
    print()
    print("="*70)
    print(f"✅ 生成完成！")
    print(f"   总计生成: {total_generated} 个快照")
    print(f"   覆盖日期: {len(dates_to_process)} 天")
    print("="*70)


if __name__ == '__main__':
    main()
