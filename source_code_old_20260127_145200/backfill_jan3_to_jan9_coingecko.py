#!/usr/bin/env python3
"""
使用CoinGecko API补全1月3日至1月9日的历史数据
策略：
1. 从CoinGecko获取小时级数据
2. 使用线性插值生成30分钟级数据
3. 合并到现有数据文件
"""

import json
import requests
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# CoinGecko币种映射（CoinGecko ID -> 我们的符号）
COINGECKO_MAPPING = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'ripple': 'XRP',
    'binancecoin': 'BNB',
    'solana': 'SOL',
    'litecoin': 'LTC',
    'dogecoin': 'DOGE',
    'sui': 'SUI',
    'tron': 'TRX',
    'the-open-network': 'TON',
    'ethereum-classic': 'ETC',
    'bitcoin-cash': 'BCH',
    'hedera-hashgraph': 'HBAR',
    'stellar': 'XLM',
    'filecoin': 'FIL',
    'chainlink': 'LINK',
    'crypto-com-chain': 'CRO',
    'polkadot': 'DOT',
    'uniswap': 'UNI',
    'near': 'NEAR',
    'aptos': 'APT',
    'conflux-token': 'CFX',
    'curve-dao-token': 'CRV',
    'stacks': 'STX',
    'lido-dao': 'LDO',
    'bittensor': 'TAO',
    'aave': 'AAVE'
}

DATA_FILE = Path(__file__).parent.parent / 'data' / 'coin_price_tracker' / 'coin_prices_30min.jsonl'
BEIJING_TZ = timezone(timedelta(hours=8))

def get_coingecko_history(coin_id, start_ts, end_ts):
    """从CoinGecko获取历史价格数据"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    
    params = {
        'vs_currency': 'usd',
        'from': start_ts,
        'to': end_ts
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            prices = data.get('prices', [])
            return prices
        else:
            print(f"  ⚠️  {coin_id}: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print(f"  ❌ {coin_id}: {e}")
        return []

def interpolate_30min(hourly_prices):
    """将小时级数据插值到30分钟级"""
    if not hourly_prices:
        return []
    
    result = []
    
    for i in range(len(hourly_prices) - 1):
        ts1, price1 = hourly_prices[i]
        ts2, price2 = hourly_prices[i + 1]
        
        # 添加当前小时的数据点
        result.append((ts1, price1))
        
        # 计算中间点（30分钟后）
        mid_ts = ts1 + (ts2 - ts1) // 2
        mid_price = (price1 + price2) / 2
        result.append((mid_ts, mid_price))
    
    # 添加最后一个点
    if hourly_prices:
        result.append(hourly_prices[-1])
    
    return result

def main():
    print("=" * 80)
    print("🚀 使用CoinGecko补全1月3-9日历史数据")
    print("=" * 80)
    print()
    
    # 时间范围：2026-01-03 00:00:00 ~ 2026-01-10 00:00:00 (北京时间)
    start_time = datetime(2026, 1, 3, 0, 0, 0, tzinfo=BEIJING_TZ)
    end_time = datetime(2026, 1, 10, 0, 0, 0, tzinfo=BEIJING_TZ)
    
    start_ts_sec = int(start_time.timestamp())
    end_ts_sec = int(end_time.timestamp())
    
    print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"总天数: 7天")
    print(f"数据来源: CoinGecko API (小时级 + 插值到30分钟)")
    print()
    
    # 读取已有数据
    existing_data = {}
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    collect_time = record.get('collect_time', '')
                    if collect_time:
                        existing_data[collect_time] = record
                except:
                    pass
    
    print(f"📊 已有数据: {len(existing_data)} 条")
    print()
    
    # 获取所有币种的历史数据
    print("🔍 从CoinGecko获取历史数据...")
    print("-" * 80)
    
    coin_prices = {}  # {symbol: [(ts, price), ...]}
    
    for coin_id, symbol in COINGECKO_MAPPING.items():
        print(f"  📥 {symbol:6s} ({coin_id})...", end=' ', flush=True)
        
        hourly_prices = get_coingecko_history(coin_id, start_ts_sec, end_ts_sec)
        
        if hourly_prices:
            # 插值到30分钟
            prices_30min = interpolate_30min(hourly_prices)
            coin_prices[symbol] = prices_30min
            print(f"✅ {len(hourly_prices)}小时 → {len(prices_30min)}点(30分钟)")
        else:
            print(f"❌ 无数据")
            coin_prices[symbol] = []
        
        time.sleep(1.5)  # CoinGecko限流：10-50次/分钟
    
    print()
    
    # 生成30分钟节点
    print("📝 生成30分钟数据节点...")
    print("-" * 80)
    
    all_nodes = []
    current = start_time
    while current < end_time:
        all_nodes.append(current)
        current += timedelta(minutes=30)
    
    print(f"✅ 生成了 {len(all_nodes)} 个时间节点")
    print()
    
    # 构建数据记录
    new_records = []
    
    for node_time in all_nodes:
        collect_time_str = node_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 跳过已存在的数据
        if collect_time_str in existing_data:
            continue
        
        node_ts_ms = int(node_time.timestamp() * 1000)
        date_str = node_time.strftime('%Y-%m-%d')
        
        # 构建数据记录
        record = {
            'timestamp': int(node_time.timestamp()),
            'collect_time': collect_time_str,
            'base_date': date_str,
            'coins': {}
        }
        
        # 获取基准价（当日00:00）
        base_time = node_time.replace(hour=0, minute=0, second=0)
        base_ts_ms = int(base_time.timestamp() * 1000)
        
        for symbol in COINGECKO_MAPPING.values():
            prices = coin_prices.get(symbol, [])
            
            if not prices:
                # 无数据，使用0
                record['coins'][symbol] = {
                    'base_price': 0.0,
                    'current_price': 0.0,
                    'change_pct': 0.0
                }
                continue
            
            # 查找最接近base_ts_ms的价格
            base_price = 0.0
            min_diff = float('inf')
            for ts, price in prices:
                diff = abs(ts - base_ts_ms)
                if diff < min_diff:
                    min_diff = diff
                    base_price = price
            
            # 查找最接近node_ts_ms的价格
            current_price = 0.0
            min_diff = float('inf')
            for ts, price in prices:
                diff = abs(ts - node_ts_ms)
                if diff < min_diff:
                    min_diff = diff
                    current_price = price
            
            # 计算涨跌幅
            change_pct = 0.0
            if base_price > 0:
                change_pct = ((current_price - base_price) / base_price) * 100
            
            record['coins'][symbol] = {
                'base_price': base_price,
                'current_price': current_price,
                'change_pct': change_pct
            }
        
        new_records.append(record)
        
        # 计算总和
        total_sum = sum([c['change_pct'] for c in record['coins'].values()])
        
        if len(new_records) % 10 == 0:
            print(f"  ✅ {collect_time_str} | 27币总和: {total_sum:+.2f}%")
    
    print()
    
    if not new_records:
        print("✅ 所有数据已存在，无需补全！")
        return
    
    # 合并并排序所有数据
    print(f"💾 保存数据... (新增 {len(new_records)} 条)")
    all_records = list(existing_data.values()) + new_records
    all_records.sort(key=lambda x: x['timestamp'])
    
    # 写入文件
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ 成功保存 {len(all_records)} 条记录")
    print(f"✅ 新增记录: {len(new_records)} 条")
    print()
    
    # 按日期统计
    print("📊 数据统计（按日期）")
    print("-" * 80)
    
    date_counts = {}
    for record in all_records:
        date = record['collect_time'][:10]
        date_counts[date] = date_counts.get(date, 0) + 1
    
    for date in sorted(date_counts.keys()):
        count = date_counts[date]
        expected = 48
        status = '✅' if count >= expected else '⚠️'
        print(f"{status} {date}: {count:3d} 个节点 ({count/expected*100:.1f}%)")
    
    print()
    print("=" * 80)
    print("🎉 1月3-9日历史数据补全完成！")
    print("=" * 80)
    print()
    print("⚠️  注意：")
    print("- 1月3-9日数据来自CoinGecko（小时级插值到30分钟）")
    print("- 1月10-16日数据来自OKX（原生30分钟K线）")
    print("- 精度：OKX数据更准确，CoinGecko数据为估算值")
    print()

if __name__ == '__main__':
    main()
