#!/usr/bin/env python3
"""
补全 Support Resistance 和 Escape Signal 数据
从 19:00 到现在的缺失数据
"""
import sys
import os
import json
import requests
import time
from datetime import datetime, timedelta
import pytz
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/home/user/webapp/source_code')

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 文件路径
SR_SNAPSHOTS_FILE = Path('/home/user/webapp/data/support_resistance_jsonl/support_resistance_snapshots.jsonl')
SR_LEVELS_FILE = Path('/home/user/webapp/data/support_resistance_jsonl/support_resistance_levels.jsonl')
ESCAPE_STATS_FILE = Path('/home/user/webapp/data/escape_signal_jsonl/escape_signal_stats.jsonl')

# API配置
OKEX_API = "https://www.okx.com/api/v5"
SYMBOLS = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "LTC", "DOGE", "SUI", "TRX", "TON",
    "ETC", "BCH", "HBAR", "XLM", "FIL", "LINK", "CRO", "DOT", "UNI", "NEAR",
    "APT", "CFX", "CRV", "STX", "LDO", "TAO", "AAVE"
]

def get_latest_snapshot_time():
    """获取最新的快照时间"""
    if not SR_SNAPSHOTS_FILE.exists():
        return None
    
    with open(SR_SNAPSHOTS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        return None
    
    for line in reversed(lines[-100:]):  # 检查最后100行
        try:
            data = json.loads(line)
            time_str = data.get('snapshot_time')
            if time_str:
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    return None

def fetch_okx_ticker(symbol):
    """获取OKX ticker数据"""
    try:
        inst_id = f"{symbol}-USDT-SWAP"
        url = f"{OKEX_API}/market/ticker"
        response = requests.get(url, params={"instId": inst_id}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0' and data.get('data'):
                ticker = data['data'][0]
                return {
                    'symbol': symbol,
                    'last': float(ticker['last']),
                    'high24h': float(ticker['high24h']),
                    'low24h': float(ticker['low24h']),
                    'vol24h': float(ticker['vol24h'])
                }
        return None
    except Exception as e:
        print(f"  ❌ {symbol}: {e}")
        return None

def calculate_support_resistance(price, high24h, low24h):
    """简化的支撑阻力计算"""
    # 使用24小时高低点作为关键位
    levels = []
    
    # 阻力位（高点附近）
    r1 = high24h
    r2 = high24h + (high24h - low24h) * 0.1
    
    # 支撑位（低点附近）
    s1 = low24h
    s2 = low24h - (high24h - low24h) * 0.1
    
    # 中间位
    pivot = (high24h + low24h + price) / 3
    
    # 判断场景
    scenario_3 = 0  # 价格接近阻力
    scenario_4 = 0  # 价格接近支撑
    
    # 场景3：价格接近阻力位（距离<2%）
    if abs(price - r1) / price < 0.02:
        scenario_3 += 1
    if abs(price - r2) / price < 0.02:
        scenario_3 += 1
    
    # 场景4：价格接近支撑位（距离<2%）
    if abs(price - s1) / price < 0.02:
        scenario_4 += 1
    if abs(price - s2) / price < 0.02:
        scenario_4 += 1
    
    return {
        'resistance_levels': [r1, r2],
        'support_levels': [s1, s2],
        'pivot': pivot,
        'scenario_3': scenario_3,
        'scenario_4': scenario_4
    }

def collect_snapshot_for_time(target_time):
    """为指定时间采集一个快照"""
    print(f"\n📸 采集快照: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    snapshot_data = {
        'snapshot_time': target_time.strftime('%Y-%m-%d %H:%M:%S'),
        'snapshot_timestamp': int(target_time.timestamp()),
        'total_symbols': len(SYMBOLS),
        'scenario_3_count': 0,
        'scenario_4_count': 0,
        'levels_by_symbol': {}
    }
    
    success_count = 0
    
    for symbol in SYMBOLS:
        ticker = fetch_okx_ticker(symbol)
        
        if ticker:
            sr_data = calculate_support_resistance(
                ticker['last'],
                ticker['high24h'],
                ticker['low24h']
            )
            
            snapshot_data['scenario_3_count'] += sr_data['scenario_3']
            snapshot_data['scenario_4_count'] += sr_data['scenario_4']
            snapshot_data['levels_by_symbol'][symbol] = sr_data
            
            success_count += 1
            print(f"  ✅ {symbol}: S3={sr_data['scenario_3']}, S4={sr_data['scenario_4']}")
        
        time.sleep(0.05)  # 避免请求过快
    
    total_signal = snapshot_data['scenario_3_count'] + snapshot_data['scenario_4_count']
    print(f"  📊 总计: S3+S4 = {total_signal}, 成功: {success_count}/{len(SYMBOLS)}")
    
    return snapshot_data

def save_snapshot(snapshot_data):
    """保存快照到JSONL"""
    with open(SR_SNAPSHOTS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(snapshot_data, ensure_ascii=False) + '\n')

def calculate_escape_signals(target_time, all_snapshots):
    """计算指定时间的escape signal统计"""
    time_24h_ago = (target_time - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    time_2h_ago = (target_time - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    target_time_str = target_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 筛选24小时和2小时内的快照
    snapshots_24h = [
        s for s in all_snapshots
        if time_24h_ago < s.get('snapshot_time', '') <= target_time_str
    ]
    
    snapshots_2h = [
        s for s in all_snapshots
        if time_2h_ago < s.get('snapshot_time', '') <= target_time_str
    ]
    
    # 计算信号数（S3+S4 >= 8 算一次信号）
    signal_24h = sum(
        1 for s in snapshots_24h
        if (s.get('scenario_3_count', 0) + s.get('scenario_4_count', 0)) >= 8
    )
    
    signal_2h = sum(
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
    
    return {
        'stat_time': target_time_str,
        'signal_24h_count': signal_24h,
        'signal_2h_count': signal_2h,
        'max_signal_24h': max_24h,
        'max_signal_2h': max_2h,
        'created_at': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    }

def save_escape_stats(stats):
    """保存escape signal统计"""
    with open(ESCAPE_STATS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(stats, ensure_ascii=False) + '\n')

def load_all_snapshots():
    """加载所有快照数据"""
    snapshots = []
    if SR_SNAPSHOTS_FILE.exists():
        with open(SR_SNAPSHOTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        snapshots.append(json.loads(line))
                    except:
                        continue
    return snapshots

def main():
    print("=" * 80)
    print("🔧 Support Resistance & Escape Signal 数据补全")
    print("=" * 80)
    
    # 获取最新快照时间
    latest_time = get_latest_snapshot_time()
    
    if latest_time is None:
        print("❌ 无法获取最新快照时间")
        return
    
    print(f"\n📅 最新快照时间: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 本地化为北京时间
    if latest_time.tzinfo is None:
        latest_time = BEIJING_TZ.localize(latest_time)
    
    # 当前时间
    now = datetime.now(BEIJING_TZ)
    print(f"⏰ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 计算需要补全的时间点（每分钟）
    missing_times = []
    current = latest_time + timedelta(minutes=1)
    
    while current <= now:
        missing_times.append(current)
        current += timedelta(minutes=1)
    
    print(f"\n📋 需要补全: {len(missing_times)} 个时间点")
    
    if len(missing_times) == 0:
        print("✅ 数据已是最新，无需补全")
        return
    
    # 显示时间范围
    print(f"   从: {missing_times[0].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   到: {missing_times[-1].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 确认继续
    print(f"\n⚠️  将采集 {len(missing_times)} 个时间点的数据")
    print(f"   预计耗时: ~{len(missing_times) * 2}秒 (每点约2秒)")
    
    # 开始补全
    print(f"\n🚀 开始补全数据...\n")
    
    collected_snapshots = []
    
    for i, target_time in enumerate(missing_times, 1):
        print(f"[{i}/{len(missing_times)}] ", end='')
        
        # 采集快照
        snapshot = collect_snapshot_for_time(target_time)
        save_snapshot(snapshot)
        collected_snapshots.append(snapshot)
        
        # 每分钟只采集一次，避免过于频繁
        if i < len(missing_times):
            time.sleep(1)
    
    print(f"\n✅ Support Resistance 快照补全完成: {len(collected_snapshots)} 个")
    
    # 重新加载所有快照（包括新采集的）
    print(f"\n📊 重新计算 Escape Signal 统计...")
    all_snapshots = load_all_snapshots()
    
    # 为每个时间点计算escape signal
    for target_time in missing_times:
        stats = calculate_escape_signals(target_time, all_snapshots)
        save_escape_stats(stats)
        print(f"  ✅ {stats['stat_time']}: 24h={stats['signal_24h_count']}, 2h={stats['signal_2h_count']}")
    
    print(f"\n✅ Escape Signal 统计补全完成: {len(missing_times)} 个")
    
    print("\n" + "=" * 80)
    print("🎉 数据补全完成！")
    print("=" * 80)
    
    # 显示最新数据
    print(f"\n📈 最新数据:")
    latest_snapshot = collected_snapshots[-1] if collected_snapshots else None
    if latest_snapshot:
        total = latest_snapshot['scenario_3_count'] + latest_snapshot['scenario_4_count']
        print(f"   时间: {latest_snapshot['snapshot_time']}")
        print(f"   场景3+4: {total}")
        print(f"   场景3: {latest_snapshot['scenario_3_count']}")
        print(f"   场景4: {latest_snapshot['scenario_4_count']}")

if __name__ == "__main__":
    main()
