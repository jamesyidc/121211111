#!/usr/bin/env python3
"""
对齐 Coin Price Tracker 和 Escape Signal 数据的时间点
- Coin Price Tracker: 每30分钟
- Escape Signal: 每分钟 -> 聚合为每30分钟
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

TZ = pytz.timezone('Asia/Shanghai')

# 文件路径
COIN_TRACKER_FILE = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl'
ESCAPE_SIGNAL_FILE = '/home/user/webapp/data/escape_signal_jsonl/escape_signal_stats.jsonl'
ALIGNED_OUTPUT_FILE = '/home/user/webapp/data/aligned_data_30min.jsonl'

def round_to_30min(time_str):
    """将时间四舍五入到最近的30分钟"""
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    dt = TZ.localize(dt) if dt.tzinfo is None else dt
    
    # 向下对齐到30分钟
    minute = (dt.minute // 30) * 30
    aligned = dt.replace(minute=minute, second=0, microsecond=0)
    
    return aligned.strftime("%Y-%m-%d %H:%M:%S")

def aggregate_escape_signals_30min():
    """将Escape Signal数据按30分钟聚合"""
    print("📊 聚合 Escape Signal 数据...")
    
    aggregated = defaultdict(lambda: {
        'signal_24h_counts': [],
        'signal_2h_counts': [],
        'decline_levels': [],
        'rise_levels': [],
        'count': 0
    })
    
    with open(ESCAPE_SIGNAL_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  跳过第{line_num}行（JSON解析错误）")
                    continue
                
                stat_time = data.get('stat_time', '')
                
                if not stat_time:
                    continue
                
                # 对齐到30分钟
                aligned_time = round_to_30min(stat_time)
                
                # 聚合数据
                aggregated[aligned_time]['signal_24h_counts'].append(data.get('signal_24h_count', 0))
                aggregated[aligned_time]['signal_2h_counts'].append(data.get('signal_2h_count', 0))
                aggregated[aligned_time]['decline_levels'].append(data.get('decline_strength_level', 0))
                aggregated[aligned_time]['rise_levels'].append(data.get('rise_strength_level', 0))
                aggregated[aligned_time]['count'] += 1
    
    # 计算每个30分钟时间段的统计值
    result = {}
    for time_key, data in aggregated.items():
        result[time_key] = {
            'stat_time': time_key,
            'signal_24h_count_avg': round(sum(data['signal_24h_counts']) / len(data['signal_24h_counts']), 2) if data['signal_24h_counts'] else 0,
            'signal_24h_count_max': max(data['signal_24h_counts']) if data['signal_24h_counts'] else 0,
            'signal_24h_count_min': min(data['signal_24h_counts']) if data['signal_24h_counts'] else 0,
            'signal_2h_count_avg': round(sum(data['signal_2h_counts']) / len(data['signal_2h_counts']), 2) if data['signal_2h_counts'] else 0,
            'signal_2h_count_max': max(data['signal_2h_counts']) if data['signal_2h_counts'] else 0,
            'signal_2h_count_min': min(data['signal_2h_counts']) if data['signal_2h_counts'] else 0,
            'decline_level_avg': round(sum(data['decline_levels']) / len(data['decline_levels']), 2) if data['decline_levels'] else 0,
            'rise_level_avg': round(sum(data['rise_levels']) / len(data['rise_levels']), 2) if data['rise_levels'] else 0,
            'sample_count': data['count']
        }
    
    print(f"✅ 聚合完成，共 {len(result)} 个30分钟时间点")
    return result

def load_coin_tracker_data():
    """加载 Coin Price Tracker 数据"""
    print("📊 加载 Coin Price Tracker 数据...")
    
    result = {}
    with open(COIN_TRACKER_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                collect_time = data.get('collect_time', '')
                if collect_time:
                    result[collect_time] = data
    
    print(f"✅ 加载完成，共 {len(result)} 条记录")
    return result

def merge_data():
    """合并两个数据源"""
    print("\n🔗 合并数据源...")
    
    # 加载数据
    coin_data = load_coin_tracker_data()
    escape_data = aggregate_escape_signals_30min()
    
    # 找出共同的时间点
    coin_times = set(coin_data.keys())
    escape_times = set(escape_data.keys())
    common_times = sorted(coin_times & escape_times)
    
    print(f"\n📈 数据统计:")
    print(f"  Coin Tracker 时间点: {len(coin_times)}")
    print(f"  Escape Signal 时间点: {len(escape_times)}")
    print(f"  共同时间点: {len(common_times)}")
    
    # 合并数据
    merged_records = []
    for time_key in sorted(coin_times | escape_times):
        record = {
            'time': time_key,
            'timestamp': int(datetime.strptime(time_key, "%Y-%m-%d %H:%M:%S").timestamp())
        }
        
        # 添加 Coin Tracker 数据
        if time_key in coin_data:
            record['coin_tracker'] = {
                'total_change': coin_data[time_key].get('total_change', 0),
                'average_change': coin_data[time_key].get('average_change', 0),
                'valid_coins': coin_data[time_key].get('valid_coins', 0),
                'base_date': coin_data[time_key].get('base_date', '')
            }
        else:
            record['coin_tracker'] = None
        
        # 添加 Escape Signal 数据
        if time_key in escape_data:
            record['escape_signal'] = escape_data[time_key]
        else:
            record['escape_signal'] = None
        
        # 标记数据来源
        record['has_coin_data'] = time_key in coin_data
        record['has_escape_data'] = time_key in escape_data
        record['is_aligned'] = time_key in common_times
        
        merged_records.append(record)
    
    # 保存合并后的数据
    print(f"\n💾 保存合并数据到: {ALIGNED_OUTPUT_FILE}")
    with open(ALIGNED_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for record in merged_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ 保存完成，共 {len(merged_records)} 条记录")
    
    # 显示示例
    print(f"\n📋 最近5条对齐数据:")
    print("-" * 100)
    print(f"{'时间':<20} {'27币总和':>12} {'24h信号':>10} {'2h信号':>10} {'对齐':>8}")
    print("-" * 100)
    
    for record in merged_records[-5:]:
        time_str = record['time']
        coin_change = record['coin_tracker']['total_change'] if record['coin_tracker'] else None
        signal_24h = record['escape_signal']['signal_24h_count_avg'] if record['escape_signal'] else None
        signal_2h = record['escape_signal']['signal_2h_count_avg'] if record['escape_signal'] else None
        aligned = '✓' if record['is_aligned'] else '✗'
        
        coin_str = f"{coin_change:+.2f}%" if coin_change is not None else "-"
        signal_24h_str = f"{signal_24h:.1f}" if signal_24h is not None else "-"
        signal_2h_str = f"{signal_2h:.1f}" if signal_2h is not None else "-"
        
        print(f"{time_str:<20} {coin_str:>12} {signal_24h_str:>10} {signal_2h_str:>10} {aligned:>8}")
    
    return merged_records

def main():
    print("=" * 100)
    print("🔧 数据时间点对齐工具")
    print("=" * 100)
    
    merged_records = merge_data()
    
    print("\n" + "=" * 100)
    print("✅ 对齐完成！")
    print("=" * 100)
    
    # 统计信息
    aligned_count = sum(1 for r in merged_records if r['is_aligned'])
    only_coin = sum(1 for r in merged_records if r['has_coin_data'] and not r['has_escape_data'])
    only_escape = sum(1 for r in merged_records if r['has_escape_data'] and not r['has_coin_data'])
    
    print(f"\n📊 最终统计:")
    print(f"  总记录数: {len(merged_records)}")
    print(f"  完全对齐: {aligned_count} ({aligned_count/len(merged_records)*100:.1f}%)")
    print(f"  仅币价数据: {only_coin}")
    print(f"  仅信号数据: {only_escape}")
    print(f"\n💾 输出文件: {ALIGNED_OUTPUT_FILE}")

if __name__ == "__main__":
    main()
