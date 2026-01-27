#!/usr/bin/env python3
"""
27币种历史数据分析与导出工具
用于分析1月3日到1月16日的完整数据集，并生成CSV导出
"""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import pytz

# 设置时区
TZ = pytz.timezone('Asia/Shanghai')

# 数据文件路径
DATA_FILE = Path('/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl')
OUTPUT_DIR = Path('/home/user/webapp/data/coin_price_tracker/exports')

# 目标币种
TARGET_COINS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 
    'TRX', 'TON', 'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK', 
    'CRO', 'DOT', 'UNI', 'NEAR', 'APT', 'CFX', 'CRV', 'STX', 
    'LDO', 'TAO', 'AAVE'
]

def parse_collect_time(time_str: str) -> datetime:
    """解析采集时间字符串"""
    try:
        # 尝试多种格式
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S%z']:
            try:
                return datetime.strptime(time_str, fmt)
            except:
                continue
        # 如果都失败，尝试ISO格式
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except Exception as e:
        print(f"⚠️  无法解析时间: {time_str}, 错误: {e}")
        return None

def load_data() -> List[Dict]:
    """加载JSONL数据"""
    data = []
    if not DATA_FILE.exists():
        print(f"❌ 数据文件不存在: {DATA_FILE}")
        return data
    
    print(f"📂 加载数据文件: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                data.append(record)
            except json.JSONDecodeError as e:
                print(f"⚠️  第{line_num}行JSON解析失败: {e}")
    
    print(f"✅ 成功加载 {len(data)} 条记录")
    return data

def analyze_data_coverage(data: List[Dict]) -> Dict:
    """分析数据覆盖情况"""
    print("\n" + "="*80)
    print("📊 数据覆盖分析")
    print("="*80)
    
    # 按日期分组
    date_records = defaultdict(list)
    time_records = defaultdict(lambda: defaultdict(dict))  # {date: {time: {coin: data}}}
    
    for record in data:
        collect_time_str = record.get('collect_time', '')
        if not collect_time_str:
            continue
        
        dt = parse_collect_time(collect_time_str)
        if not dt:
            continue
        
        date_key = dt.strftime('%Y-%m-%d')
        time_key = dt.strftime('%H:%M')
        
        date_records[date_key].append(record)
        
        # 记录每个币种的数据
        coins = record.get('coins', {})
        for coin_symbol, coin_data in coins.items():
            time_records[date_key][time_key][coin_symbol] = coin_data
    
    # 生成日期范围
    start_date = datetime(2026, 1, 3, tzinfo=TZ)
    end_date = datetime(2026, 1, 16, 23, 59, 59, tzinfo=TZ)
    
    # 48个时间点（每天00:00-23:30，每30分钟）
    expected_times = []
    for hour in range(24):
        for minute in [0, 30]:
            expected_times.append(f"{hour:02d}:{minute:02d}")
    
    print(f"\n📅 日期范围: {start_date.date()} 至 {end_date.date()}")
    print(f"⏰ 每天预期数据点: {len(expected_times)} 个 (30分钟粒度)")
    print(f"💰 币种数量: {len(TARGET_COINS)}")
    print(f"📈 预期总数据点: {14 * len(expected_times)} = {14 * 48} 个时间节点")
    
    # 统计每天的数据
    print("\n" + "-"*80)
    print("📊 每日数据统计")
    print("-"*80)
    
    missing_data = []  # 记录缺失的数据点
    
    current_date = start_date
    while current_date.date() <= end_date.date():
        date_key = current_date.strftime('%Y-%m-%d')
        records_count = len(date_records.get(date_key, []))
        
        # 检查每个时间点
        time_data = time_records.get(date_key, {})
        missing_times = []
        
        for time_key in expected_times:
            if time_key not in time_data:
                missing_times.append(time_key)
                for coin in TARGET_COINS:
                    missing_data.append({
                        'date': date_key,
                        'time': time_key,
                        'coin': coin,
                        'reason': '整个时间点缺失'
                    })
            else:
                # 检查每个币种
                coins_at_time = time_data[time_key]
                for coin in TARGET_COINS:
                    if coin not in coins_at_time:
                        missing_data.append({
                            'date': date_key,
                            'time': time_key,
                            'coin': coin,
                            'reason': '币种数据缺失'
                        })
        
        coverage = (len(expected_times) - len(missing_times)) / len(expected_times) * 100
        status = "✅" if coverage == 100 else "⚠️"
        
        print(f"{status} {date_key}: {records_count:3d} 条记录, "
              f"覆盖率: {coverage:5.1f}% ({len(expected_times) - len(missing_times)}/{len(expected_times)})")
        
        if missing_times and len(missing_times) <= 10:
            print(f"   缺失时间点: {', '.join(missing_times[:10])}")
        elif missing_times:
            print(f"   缺失时间点: {len(missing_times)} 个")
        
        current_date += timedelta(days=1)
    
    print("\n" + "="*80)
    print(f"📋 总计缺失数据点: {len(missing_data)} 个")
    
    return {
        'date_records': dict(date_records),
        'time_records': dict(time_records),
        'missing_data': missing_data,
        'expected_times': expected_times
    }

def export_full_csv(data: List[Dict], output_path: Path):
    """导出完整的CSV文件"""
    print("\n" + "="*80)
    print("📝 导出完整CSV文件")
    print("="*80)
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # CSV表头
    headers = ['日期', '时间', '时间戳', '币种', '基准价格(00:00)', '当前价格', '涨跌幅(%)']
    
    # 收集所有数据行
    rows = []
    for record in data:
        collect_time_str = record.get('collect_time', '')
        if not collect_time_str:
            continue
        
        dt = parse_collect_time(collect_time_str)
        if not dt:
            continue
        
        date_str = dt.strftime('%Y-%m-%d')
        time_str = dt.strftime('%H:%M:%S')
        timestamp = int(dt.timestamp())
        
        coins = record.get('coins', {})
        for coin_symbol in TARGET_COINS:
            coin_data = coins.get(coin_symbol, {})
            if not coin_data:
                continue
            
            base_price = coin_data.get('base_price', 0)
            current_price = coin_data.get('current_price', 0)
            change_pct = coin_data.get('change_pct', 0)
            
            rows.append([
                date_str,
                time_str,
                timestamp,
                coin_symbol,
                f"{base_price:.8f}",
                f"{current_price:.8f}",
                f"{change_pct:.4f}"
            ])
    
    # 按时间排序
    rows.sort(key=lambda x: (x[0], x[1], x[3]))
    
    # 写入CSV
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    
    print(f"✅ CSV文件已导出: {output_path}")
    print(f"📊 总行数: {len(rows)} 行 (不含表头)")
    
    return len(rows)

def export_summary_csv(analysis: Dict, output_path: Path):
    """导出27币涨跌幅总和汇总CSV"""
    print("\n" + "="*80)
    print("📝 导出27币涨跌幅总和CSV")
    print("="*80)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    headers = ['日期', '时间', '时间戳', '27币涨跌幅总和(%)']
    
    time_records = analysis['time_records']
    
    rows = []
    start_date = datetime(2026, 1, 3, tzinfo=TZ)
    end_date = datetime(2026, 1, 16, tzinfo=TZ)
    
    current_date = start_date
    while current_date.date() <= end_date.date():
        date_key = current_date.strftime('%Y-%m-%d')
        
        for time_key in analysis['expected_times']:
            hour, minute = map(int, time_key.split(':'))
            dt = current_date.replace(hour=hour, minute=minute, second=0)
            
            # 计算27币总和
            time_data = time_records.get(date_key, {}).get(time_key, {})
            total_change = sum(
                coin_data.get('change_pct', 0)
                for coin_symbol, coin_data in time_data.items()
                if coin_symbol in TARGET_COINS
            )
            
            rows.append([
                date_key,
                time_key,
                int(dt.timestamp()),
                f"{total_change:.4f}"
            ])
        
        current_date += timedelta(days=1)
    
    # 写入CSV
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    
    print(f"✅ 汇总CSV已导出: {output_path}")
    print(f"📊 总行数: {len(rows)} 行 (不含表头)")
    
    return len(rows)

def export_missing_data_csv(missing_data: List[Dict], output_path: Path):
    """导出缺失数据清单CSV"""
    print("\n" + "="*80)
    print("📝 导出缺失数据清单CSV")
    print("="*80)
    
    if not missing_data:
        print("✅ 没有缺失数据！")
        return 0
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    headers = ['日期', '时间', '币种', '原因']
    
    rows = []
    for item in missing_data:
        rows.append([
            item['date'],
            item['time'],
            item['coin'],
            item['reason']
        ])
    
    # 排序
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    
    # 写入CSV
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    
    print(f"✅ 缺失数据清单已导出: {output_path}")
    print(f"📊 总缺失: {len(rows)} 条")
    
    return len(rows)

def main():
    """主函数"""
    print("="*80)
    print("27币种历史数据分析与导出工具")
    print("日期范围: 2026-01-03 至 2026-01-16")
    print("数据粒度: 30分钟")
    print("="*80)
    
    # 加载数据
    data = load_data()
    if not data:
        print("❌ 没有数据可分析")
        return
    
    # 分析数据覆盖
    analysis = analyze_data_coverage(data)
    
    # 导出文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. 完整数据CSV
    full_csv = OUTPUT_DIR / f'coin_prices_full_{timestamp}.csv'
    export_full_csv(data, full_csv)
    
    # 2. 27币总和CSV
    summary_csv = OUTPUT_DIR / f'coin_sum_27_{timestamp}.csv'
    export_summary_csv(analysis, summary_csv)
    
    # 3. 缺失数据清单
    if analysis['missing_data']:
        missing_csv = OUTPUT_DIR / f'missing_data_{timestamp}.csv'
        export_missing_data_csv(analysis['missing_data'], missing_csv)
    
    print("\n" + "="*80)
    print("✅ 所有导出完成！")
    print("="*80)
    print(f"\n📁 导出目录: {OUTPUT_DIR}")
    print(f"\n文件列表:")
    print(f"  1. {full_csv.name} - 完整数据(所有币种所有时间点)")
    print(f"  2. {summary_csv.name} - 27币涨跌幅总和")
    if analysis['missing_data']:
        print(f"  3. {missing_csv.name} - 缺失数据清单(用于下次补采)")

if __name__ == '__main__':
    main()
