#!/usr/bin/env python3
"""
完整补全27种币的历史数据 (2026-01-03 to 2026-01-16)
使用OKX API作为主数据源，确保所有27个币种的数据都被正确填充
"""

import json
import time
import hmac
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List
import requests

# OKX API配置
API_KEY = "cd4f64e6-9b9e-44e3-b2d5-3e95ceba4ab9"
SECRET_KEY = "46CE94DFAF3CDB2C1B31B6E13B3FCC89"
PASSPHRASE = "AIdrive@1234"
BASE_URL = "https://www.okx.com"

# 27个币种的OKX永续合约映射
COINS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
    'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK', 'CRO', 'DOT', 'AAVE', 'UNI',
    'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
]

OKX_SYMBOLS = {
    'BTC': 'BTC-USDT-SWAP', 'ETH': 'ETH-USDT-SWAP', 'XRP': 'XRP-USDT-SWAP',
    'BNB': 'BNB-USDT-SWAP', 'SOL': 'SOL-USDT-SWAP', 'LTC': 'LTC-USDT-SWAP',
    'DOGE': 'DOGE-USDT-SWAP', 'SUI': 'SUI-USDT-SWAP', 'TRX': 'TRX-USDT-SWAP',
    'TON': 'TON-USDT-SWAP', 'ETC': 'ETC-USDT-SWAP', 'BCH': 'BCH-USDT-SWAP',
    'HBAR': 'HBAR-USDT-SWAP', 'XLM': 'XLM-USDT-SWAP', 'FIL': 'FIL-USDT-SWAP',
    'LINK': 'LINK-USDT-SWAP', 'CRO': 'CRO-USDT-SWAP', 'DOT': 'DOT-USDT-SWAP',
    'AAVE': 'AAVE-USDT-SWAP', 'UNI': 'UNI-USDT-SWAP', 'NEAR': 'NEAR-USDT-SWAP',
    'APT': 'APT-USDT-SWAP', 'CFX': 'CFX-USDT-SWAP', 'CRV': 'CRV-USDT-SWAP',
    'STX': 'STX-USDT-SWAP', 'LDO': 'LDO-USDT-SWAP', 'TAO': 'TAO-USDT-SWAP'
}

DATA_FILE = "/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl"

def generate_signature(timestamp: str, method: str, request_path: str, body: str = '') -> str:
    """生成OKX API签名"""
    message = timestamp + method + request_path + body
    mac = hmac.new(bytes(SECRET_KEY, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def get_okx_headers(method: str, request_path: str, body: str = '') -> dict:
    """生成OKX API请求头"""
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    signature = generate_signature(timestamp, method, request_path, body)
    
    return {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }

def fetch_okx_candles(symbol: str, after_ts: int, limit: int = 100) -> List[list]:
    """
    获取OKX K线数据
    返回格式: [[ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm], ...]
    """
    request_path = f"/api/v5/market/history-candles?instId={symbol}&bar=30m&after={after_ts}&limit={limit}"
    headers = get_okx_headers('GET', request_path)
    
    try:
        response = requests.get(BASE_URL + request_path, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == '0' and data.get('data'):
            return data['data']
        else:
            print(f"⚠️  {symbol} API返回异常: code={data.get('code')}, msg={data.get('msg')}")
            return []
    except Exception as e:
        print(f"❌ {symbol} 请求失败: {e}")
        return []

def beijing_to_timestamp(beijing_time_str: str) -> int:
    """北京时间字符串转时间戳(毫秒)"""
    dt = datetime.strptime(beijing_time_str, '%Y-%m-%d %H:%M:%S')
    utc_dt = dt - timedelta(hours=8)  # 北京时间转UTC
    return int(utc_dt.timestamp() * 1000)

def timestamp_to_beijing(ts_ms: int) -> str:
    """时间戳(毫秒)转北京时间字符串"""
    utc_dt = datetime.utcfromtimestamp(ts_ms / 1000)
    beijing_dt = utc_dt + timedelta(hours=8)
    return beijing_dt.strftime('%Y-%m-%d %H:%M:%S')

def generate_time_nodes(start_date: str, end_date: str) -> List[dict]:
    """生成30分钟间隔的时间节点"""
    nodes = []
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(minutes=30)
    
    current_dt = start_dt
    while current_dt <= end_dt:
        beijing_time = current_dt.strftime('%Y-%m-%d %H:%M:%S')
        base_date = current_dt.strftime('%Y-%m-%d')
        timestamp = beijing_to_timestamp(beijing_time)
        
        nodes.append({
            'timestamp': timestamp // 1000,  # 秒级时间戳
            'collect_time': beijing_time,
            'base_date': base_date
        })
        
        current_dt += timedelta(minutes=30)
    
    return nodes

def fetch_coin_prices_for_period(coin: str, start_beijing: str, end_beijing: str) -> Dict[int, float]:
    """
    获取指定币种在时间段内的价格数据
    返回: {timestamp_sec: close_price}
    """
    symbol = OKX_SYMBOLS.get(coin)
    if not symbol:
        print(f"⚠️  {coin} 没有对应的OKX交易对")
        return {}
    
    start_ts = beijing_to_timestamp(start_beijing)
    end_ts = beijing_to_timestamp(end_beijing)
    
    prices = {}
    after_ts = end_ts
    retry_count = 0
    max_retries = 3
    
    while after_ts > start_ts and retry_count < max_retries:
        candles = fetch_okx_candles(symbol, after_ts, limit=300)
        
        if not candles:
            print(f"⚠️  {coin} 在 after={after_ts} 时无数据，重试 {retry_count + 1}/{max_retries}")
            retry_count += 1
            time.sleep(1)
            continue
        
        retry_count = 0  # 重置重试计数
        
        for candle in candles:
            ts_ms = int(candle[0])
            ts_sec = ts_ms // 1000
            close_price = float(candle[4])
            
            if ts_ms >= start_ts and ts_ms <= end_ts:
                prices[ts_sec] = close_price
        
        # 更新after参数为最早的时间戳
        oldest_ts = int(candles[-1][0]) if candles else after_ts
        if oldest_ts >= after_ts:
            break
        after_ts = oldest_ts
        
        time.sleep(0.2)  # 限流保护
    
    return prices

def calculate_change_pct(base_price: float, current_price: float) -> float:
    """计算涨跌幅百分比"""
    if base_price == 0:
        return 0.0
    return ((current_price - base_price) / base_price) * 100

def main():
    print("=" * 80)
    print("🚀 开始完整补全27种币的历史数据 (2026-01-03 至 2026-01-16)")
    print("=" * 80)
    
    # 1. 生成所有时间节点
    start_date = "2026-01-03"
    end_date = "2026-01-16"
    time_nodes = generate_time_nodes(start_date, end_date)
    print(f"\n✅ 生成时间节点: {len(time_nodes)} 个 (每30分钟一个)")
    
    # 2. 分两段处理数据
    # 段1: 2026-01-03 00:00:00 到 2026-01-09 23:30:00 (需要补全)
    # 段2: 2026-01-10 00:00:00 到 2026-01-16 23:30:00 (已有OKX数据)
    
    split_time = "2026-01-10 00:00:00"
    split_ts = beijing_to_timestamp(split_time) // 1000
    
    nodes_to_fill = [n for n in time_nodes if n['timestamp'] < split_ts]
    nodes_existing = [n for n in time_nodes if n['timestamp'] >= split_ts]
    
    print(f"\n📊 数据分段:")
    print(f"   - 需要补全: {len(nodes_to_fill)} 个节点 (1月3-9日)")
    print(f"   - 已有数据: {len(nodes_existing)} 个节点 (1月10-16日)")
    
    # 3. 获取每个币种的历史价格数据
    print(f"\n🔄 开始获取27种币的历史价格...")
    coin_prices_data = {}
    
    for i, coin in enumerate(COINS, 1):
        print(f"\n[{i}/27] 正在获取 {coin} 的数据...")
        prices = fetch_coin_prices_for_period(coin, "2026-01-03 00:00:00", "2026-01-09 23:30:00")
        coin_prices_data[coin] = prices
        print(f"   ✅ {coin}: 获取到 {len(prices)} 个价格点")
        time.sleep(0.3)  # API限流保护
    
    # 4. 构建完整数据集
    print(f"\n📝 开始构建完整数据集...")
    all_records = []
    
    for node in nodes_to_fill:
        timestamp = node['timestamp']
        collect_time = node['collect_time']
        base_date = node['base_date']
        
        # 计算当天00:00的时间戳
        base_dt = datetime.strptime(base_date, '%Y-%m-%d')
        base_ts = int(base_dt.replace(hour=0, minute=0, second=0).timestamp())
        
        coins_data = {}
        
        for coin in COINS:
            prices = coin_prices_data.get(coin, {})
            
            # 获取基准价格 (当天00:00)
            base_price = prices.get(base_ts, 0.0)
            
            # 获取当前价格
            current_price = prices.get(timestamp, 0.0)
            
            # 如果没有精确匹配，尝试找最近的价格点
            if current_price == 0.0 and prices:
                # 找最近的时间戳
                closest_ts = min(prices.keys(), key=lambda x: abs(x - timestamp))
                if abs(closest_ts - timestamp) <= 1800:  # 30分钟内
                    current_price = prices[closest_ts]
            
            if base_price == 0.0 and prices:
                # 找当天最早的价格作为基准
                day_prices = {ts: p for ts, p in prices.items() if ts >= base_ts and ts < base_ts + 86400}
                if day_prices:
                    base_price = list(day_prices.values())[0]
            
            change_pct = calculate_change_pct(base_price, current_price)
            
            coins_data[coin] = {
                "base_price": base_price,
                "current_price": current_price,
                "change_pct": change_pct
            }
        
        record = {
            "timestamp": timestamp,
            "collect_time": collect_time,
            "base_date": base_date,
            "coins": coins_data
        }
        
        all_records.append(record)
    
    # 5. 读取已有的1月10-16日数据
    print(f"\n📖 读取已有的1月10-16日数据...")
    existing_records = []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                record = json.loads(line.strip())
                if record['timestamp'] >= split_ts:
                    existing_records.append(record)
        print(f"   ✅ 读取到 {len(existing_records)} 条现有记录")
    except FileNotFoundError:
        print(f"   ⚠️  数据文件不存在，将创建新文件")
    
    # 6. 合并并排序所有记录
    all_records.extend(existing_records)
    all_records.sort(key=lambda x: x['timestamp'])
    
    print(f"\n💾 总记录数: {len(all_records)} 条")
    
    # 7. 写入文件
    print(f"\n✍️  写入数据文件...")
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    # 8. 数据质量统计
    print(f"\n" + "=" * 80)
    print("📊 数据质量统计报告")
    print("=" * 80)
    
    # 统计每个币种的有效数据点
    coin_stats = {coin: 0 for coin in COINS}
    for record in all_records:
        for coin in COINS:
            if record['coins'][coin]['current_price'] > 0:
                coin_stats[coin] += 1
    
    print(f"\n币种数据覆盖情况:")
    for coin in COINS:
        coverage = (coin_stats[coin] / len(all_records)) * 100
        print(f"   {coin:6s}: {coin_stats[coin]:3d}/{len(all_records)} ({coverage:5.1f}%)")
    
    # 按日期统计
    date_stats = {}
    for record in all_records:
        date = record['base_date']
        if date not in date_stats:
            date_stats[date] = 0
        date_stats[date] += 1
    
    print(f"\n每日数据点数:")
    for date in sorted(date_stats.keys()):
        print(f"   {date}: {date_stats[date]} 个节点")
    
    # 检查零值比例
    zero_count = 0
    total_coin_points = len(all_records) * len(COINS)
    for record in all_records:
        for coin in COINS:
            if record['coins'][coin]['current_price'] == 0:
                zero_count += 1
    
    zero_ratio = (zero_count / total_coin_points) * 100
    print(f"\n零值数据点: {zero_count}/{total_coin_points} ({zero_ratio:.1f}%)")
    
    print(f"\n" + "=" * 80)
    print("✅ 数据补全完成！")
    print("=" * 80)
    print(f"📁 数据文件: {DATA_FILE}")
    print(f"📅 时间范围: {start_date} 00:00:00 ~ {end_date} 23:30:00")
    print(f"⏰ 数据粒度: 30分钟")
    print(f"💰 币种数量: 27")
    print(f"📈 总节点数: {len(all_records)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
