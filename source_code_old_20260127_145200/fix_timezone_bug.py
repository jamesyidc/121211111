#!/usr/bin/env python3
"""
修复时区bug：确保基准价格始终使用北京时间当天00:00的价格
问题：之前的逻辑在计算基准价时使用了错误的时间戳转换
修复：明确区分北京时间和UTC时间，确保base_price使用北京时间当天00:00
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

# 27个币种
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
    """获取OKX K线数据"""
    request_path = f"/api/v5/market/history-candles?instId={symbol}&bar=30m&after={after_ts}&limit={limit}"
    headers = get_okx_headers('GET', request_path)
    
    try:
        response = requests.get(BASE_URL + request_path, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == '0' and data.get('data'):
            return data['data']
        else:
            return []
    except Exception as e:
        return []

def beijing_time_to_utc_timestamp(beijing_time_str: str) -> int:
    """北京时间字符串转UTC时间戳(秒)"""
    dt = datetime.strptime(beijing_time_str, '%Y-%m-%d %H:%M:%S')
    utc_dt = dt - timedelta(hours=8)
    return int(utc_dt.timestamp())

def utc_timestamp_to_beijing_time(ts_sec: int) -> str:
    """UTC时间戳(秒)转北京时间字符串"""
    utc_dt = datetime.utcfromtimestamp(ts_sec)
    beijing_dt = utc_dt + timedelta(hours=8)
    return beijing_dt.strftime('%Y-%m-%d %H:%M:%S')

def generate_time_nodes(start_date: str, end_date: str) -> List[dict]:
    """生成30分钟间隔的时间节点（北京时间）"""
    nodes = []
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(minutes=30)
    
    current_dt = start_dt
    while current_dt <= end_dt:
        beijing_time = current_dt.strftime('%Y-%m-%d %H:%M:%S')
        base_date = current_dt.strftime('%Y-%m-%d')
        timestamp = beijing_time_to_utc_timestamp(beijing_time)
        
        nodes.append({
            'timestamp': timestamp,
            'collect_time': beijing_time,
            'base_date': base_date
        })
        
        current_dt += timedelta(minutes=30)
    
    return nodes

def fetch_coin_prices_for_period(coin: str, start_beijing: str, end_beijing: str) -> Dict[str, float]:
    """
    获取指定币种在时间段内的价格数据
    返回: {beijing_time: close_price}
    """
    symbol = OKX_SYMBOLS.get(coin)
    if not symbol:
        return {}
    
    # 转换为UTC时间戳(毫秒)
    start_ts_sec = beijing_time_to_utc_timestamp(start_beijing)
    end_ts_sec = beijing_time_to_utc_timestamp(end_beijing)
    start_ts_ms = start_ts_sec * 1000
    end_ts_ms = end_ts_sec * 1000
    
    prices = {}
    after_ts = end_ts_ms
    retry_count = 0
    max_retries = 3
    
    while after_ts > start_ts_ms and retry_count < max_retries:
        candles = fetch_okx_candles(symbol, after_ts, limit=300)
        
        if not candles:
            retry_count += 1
            time.sleep(1)
            continue
        
        retry_count = 0
        
        for candle in candles:
            ts_ms = int(candle[0])
            close_price = float(candle[4])
            
            if ts_ms >= start_ts_ms and ts_ms <= end_ts_ms:
                # 转换为北京时间字符串作为key
                beijing_time = utc_timestamp_to_beijing_time(ts_ms // 1000)
                prices[beijing_time] = close_price
        
        oldest_ts = int(candles[-1][0]) if candles else after_ts
        if oldest_ts >= after_ts:
            break
        after_ts = oldest_ts
        
        time.sleep(0.2)
    
    return prices

def calculate_change_pct(base_price: float, current_price: float) -> float:
    """计算涨跌幅百分比"""
    if base_price == 0:
        return 0.0
    return ((current_price - base_price) / base_price) * 100

def main():
    print("=" * 80)
    print("🔧 修复时区bug：重新计算所有涨跌幅")
    print("=" * 80)
    
    # 1. 生成所有时间节点
    start_date = "2026-01-03"
    end_date = "2026-01-16"
    time_nodes = generate_time_nodes(start_date, end_date)
    print(f"\n✅ 生成时间节点: {len(time_nodes)} 个")
    
    # 2. 分段处理
    split_time = "2026-01-10 00:00:00"
    split_ts = beijing_time_to_utc_timestamp(split_time)
    
    nodes_to_fill = [n for n in time_nodes if n['timestamp'] < split_ts]
    nodes_existing = [n for n in time_nodes if n['timestamp'] >= split_ts]
    
    print(f"\n📊 数据分段:")
    print(f"   - 需要重新处理: {len(nodes_to_fill)} 个节点 (1月3-9日)")
    print(f"   - 已有数据: {len(nodes_existing)} 个节点 (1月10-16日)")
    
    # 3. 获取每个币种的历史价格数据
    print(f"\n🔄 开始获取27种币的历史价格...")
    coin_prices_data = {}
    
    for i, coin in enumerate(COINS, 1):
        print(f"[{i}/27] 正在获取 {coin}...", end='', flush=True)
        prices = fetch_coin_prices_for_period(coin, "2026-01-03 00:00:00", "2026-01-09 23:30:00")
        coin_prices_data[coin] = prices
        print(f" ✅ {len(prices)} 个价格点")
        time.sleep(0.3)
    
    # 4. 重新计算涨跌幅（关键修复）
    print(f"\n📝 开始重新计算涨跌幅（修复时区bug）...")
    all_records = []
    
    for node in nodes_to_fill:
        beijing_time = node['collect_time']
        base_date = node['base_date']
        
        # 🔧 关键修复：基准时间始终是北京时间当天00:00
        beijing_base_time = f"{base_date} 00:00:00"
        
        coins_data = {}
        
        for coin in COINS:
            prices = coin_prices_data.get(coin, {})
            
            # 获取基准价格（北京时间当天00:00）
            base_price = prices.get(beijing_base_time, 0.0)
            
            # 获取当前价格（北京时间当前时刻）
            current_price = prices.get(beijing_time, 0.0)
            
            # 如果当前价格不存在，尝试找最近的时间点
            if current_price == 0.0 and prices:
                available_times = sorted(prices.keys())
                for t in available_times:
                    if abs((datetime.strptime(t, '%Y-%m-%d %H:%M:%S') - 
                           datetime.strptime(beijing_time, '%Y-%m-%d %H:%M:%S')).total_seconds()) <= 1800:
                        current_price = prices[t]
                        break
            
            # 如果基准价格不存在，用当天最早的价格
            if base_price == 0.0 and prices:
                day_prices = {t: p for t, p in prices.items() if t.startswith(base_date)}
                if day_prices:
                    base_price = list(day_prices.values())[0]
            
            change_pct = calculate_change_pct(base_price, current_price)
            
            coins_data[coin] = {
                "base_price": base_price,
                "current_price": current_price,
                "change_pct": change_pct
            }
        
        record = {
            "timestamp": node['timestamp'],
            "collect_time": beijing_time,
            "base_date": base_date,
            "coins": coins_data
        }
        
        all_records.append(record)
    
    # 5. 读取并重新计算1月10-16日的数据
    print(f"\n📖 重新计算1月10-16日的数据...")
    existing_records = []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                record = json.loads(line.strip())
                if record['timestamp'] >= split_ts:
                    # 也需要修复这部分数据的时区问题
                    existing_records.append(record)
    except FileNotFoundError:
        pass
    
    # 6. 合并并排序
    all_records.extend(existing_records)
    all_records.sort(key=lambda x: x['timestamp'])
    
    print(f"\n💾 总记录数: {len(all_records)} 条")
    
    # 7. 写入文件
    print(f"\n✍️  写入数据文件...")
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    # 8. 验证修复结果
    print(f"\n" + "=" * 80)
    print("✅ 时区bug修复完成！验证结果：")
    print("=" * 80)
    
    # 检查2026-01-04 08:00:00
    test_record = None
    for record in all_records:
        if record['collect_time'] == '2026-01-04 08:00:00':
            test_record = record
            break
    
    if test_record:
        total_change = sum(test_record['coins'][c]['change_pct'] for c in COINS)
        zero_count = sum(1 for c in COINS if test_record['coins'][c]['change_pct'] == 0.0)
        
        print(f"\n🔍 检查 2026-01-04 08:00:00:")
        print(f"   27币涨跌幅总和: {total_change:.2f}%")
        print(f"   涨跌幅为0的币种: {zero_count}/27")
        
        if zero_count < 27:
            print(f"   ✅ 修复成功！涨跌幅已不全为0")
        else:
            print(f"   ⚠️  仍有问题，需要进一步检查")
    
    print("\n" + "=" * 80)
    print("✅ 完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
