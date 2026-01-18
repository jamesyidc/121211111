#!/usr/bin/env python3
"""
补全1月3日至1月9日的历史数据
使用OKX认证API的history-candles接口
"""

import json
import requests
import hmac
import base64
import hashlib
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# OKX API认证信息
API_KEY = "77465009-2c87-443c-83c8-08b35c7f14b2"
SECRET_KEY = "11647B2578630D28501D41C748B3D809"
PASSPHRASE = "Tencent@123"

# 27个币种
COINS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI',
    'TRX', 'TON', 'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK',
    'CRO', 'DOT', 'UNI', 'NEAR', 'APT', 'CFX', 'CRV', 'STX',
    'LDO', 'TAO', 'AAVE'
]

# 数据文件路径
DATA_FILE = Path(__file__).parent.parent / 'data' / 'coin_price_tracker' / 'coin_prices_30min.jsonl'
BEIJING_TZ = timezone(timedelta(hours=8))

def get_okx_signature(timestamp, method, request_path, body=''):
    """生成OKX API签名"""
    message = timestamp + method + request_path + body
    mac = hmac.new(
        bytes(SECRET_KEY, encoding='utf8'),
        bytes(message, encoding='utf-8'),
        digestmod=hashlib.sha256
    )
    return base64.b64encode(mac.digest()).decode()

def get_history_candles(symbol, start_ts, end_ts):
    """
    获取历史K线数据
    注意：history-candles的before参数表示获取此时间之后的数据
    """
    url = "https://www.okx.com/api/v5/market/history-candles"
    
    all_candles = []
    current_ts = start_ts
    
    while current_ts < end_ts:
        params = {
            'instId': f'{symbol}-USDT-SWAP',
            'bar': '30m',
            'before': str(current_ts),  # 获取此时间之后的数据
            'limit': '100'
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        request_path = f"/api/v5/market/history-candles?{query_string}"
        
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        signature = get_okx_signature(timestamp, 'GET', request_path)
        
        headers = {
            'OK-ACCESS-KEY': API_KEY,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': PASSPHRASE,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == '0':
                    candles = result.get('data', [])
                    
                    if not candles:
                        break
                    
                    # 过滤出目标时间范围内的K线
                    for candle in candles:
                        candle_ts = int(candle[0])
                        if start_ts <= candle_ts < end_ts:
                            all_candles.append(candle)
                    
                    # 更新current_ts为最新的时间戳+1
                    if candles:
                        current_ts = int(candles[0][0]) + 1
                    else:
                        break
                else:
                    print(f"⚠️  API错误: {result.get('msg')}")
                    break
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                break
                
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            break
        
        time.sleep(0.05)  # 限流：20次/秒
    
    return all_candles

def get_base_price(symbol, date_str):
    """获取指定日期00:00的基准价格"""
    date_time = datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S")
    date_time = date_time.replace(tzinfo=BEIJING_TZ)
    ts = int(date_time.timestamp() * 1000)
    
    params = {
        'instId': f'{symbol}-USDT-SWAP',
        'bar': '30m',
        'before': str(ts + 1800000),  # before参数：获取此时间之后的第一根K线
        'limit': '1'
    }
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    request_path = f"/api/v5/market/history-candles?{query_string}"
    
    timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    signature = get_okx_signature(timestamp, 'GET', request_path)
    
    headers = {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            "https://www.okx.com/api/v5/market/history-candles",
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == '0' and result.get('data'):
                candle = result['data'][0]
                return float(candle[4])  # 收盘价
    except:
        pass
    
    return 0.0

def main():
    print("=" * 80)
    print("🚀 开始补全1月3日至1月9日历史数据")
    print("=" * 80)
    
    # 时间范围：2026-01-03 00:00:00 ~ 2026-01-10 00:00:00 (北京时间)
    start_time = datetime(2026, 1, 3, 0, 0, 0, tzinfo=BEIJING_TZ)
    end_time = datetime(2026, 1, 10, 0, 0, 0, tzinfo=BEIJING_TZ)
    
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    
    print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"总天数: 7天")
    print(f"预计节点数: {7 * 48} = 336个")
    print(f"币种数量: {len(COINS)}个")
    print()
    
    # 生成所有30分钟节点
    all_nodes = []
    current = start_time
    while current < end_time:
        all_nodes.append(current)
        current += timedelta(minutes=30)
    
    print(f"✅ 生成了 {len(all_nodes)} 个时间节点")
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
    
    # 按日期回填
    new_records = []
    
    for day_offset in range(7):
        date = start_time + timedelta(days=day_offset)
        date_str = date.strftime('%Y-%m-%d')
        
        print(f"📅 处理日期: {date_str}")
        print("-" * 80)
        
        # 获取基准价（00:00）
        base_prices = {}
        print("   🔍 获取基准价格（00:00）...")
        
        for coin in COINS:
            base_price = get_base_price(coin, date_str)
            base_prices[coin] = base_price
            print(f"   {coin}: ${base_price:,.2f}")
            time.sleep(0.05)
        
        print()
        
        # 获取当天的所有30分钟节点
        day_nodes = [n for n in all_nodes if n.date() == date.date()]
        
        for node_idx, node_time in enumerate(day_nodes):
            collect_time_str = node_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 跳过已存在的数据
            if collect_time_str in existing_data:
                continue
            
            # 构建数据记录
            record = {
                'timestamp': int(node_time.timestamp()),
                'collect_time': collect_time_str,
                'base_date': date_str,
                'coins': {}
            }
            
            # 获取每个币种的当前价格
            node_ts = int(node_time.timestamp() * 1000)
            
            for coin in COINS:
                # 获取该时间点的K线
                params = {
                    'instId': f'{coin}-USDT-SWAP',
                    'bar': '30m',
                    'before': str(node_ts + 1800000),
                    'limit': '1'
                }
                
                query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                request_path = f"/api/v5/market/history-candles?{query_string}"
                
                timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                signature = get_okx_signature(timestamp, 'GET', request_path)
                
                headers = {
                    'OK-ACCESS-KEY': API_KEY,
                    'OK-ACCESS-SIGN': signature,
                    'OK-ACCESS-TIMESTAMP': timestamp,
                    'OK-ACCESS-PASSPHRASE': PASSPHRASE,
                    'Content-Type': 'application/json'
                }
                
                try:
                    response = requests.get(
                        "https://www.okx.com/api/v5/market/history-candles",
                        params=params,
                        headers=headers,
                        timeout=10
                    )
                    
                    current_price = 0.0
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('code') == '0' and result.get('data'):
                            candle = result['data'][0]
                            current_price = float(candle[4])
                    
                    base_price = base_prices.get(coin, 0.0)
                    change_pct = 0.0
                    if base_price > 0:
                        change_pct = ((current_price - base_price) / base_price) * 100
                    
                    record['coins'][coin] = {
                        'base_price': base_price,
                        'current_price': current_price,
                        'change_pct': change_pct
                    }
                    
                except Exception as e:
                    # 使用基准价作为当前价
                    base_price = base_prices.get(coin, 0.0)
                    record['coins'][coin] = {
                        'base_price': base_price,
                        'current_price': base_price,
                        'change_pct': 0.0
                    }
                
                time.sleep(0.05)
            
            new_records.append(record)
            
            # 计算总和
            total_sum = sum([c['change_pct'] for c in record['coins'].values()])
            
            print(f"   ✅ {collect_time_str} | 27币总和: {total_sum:+.2f}%")
        
        print()
    
    if not new_records:
        print("✅ 所有数据已存在，无需补全！")
        return
    
    # 合并并排序所有数据
    print("📝 保存数据...")
    all_records = list(existing_data.values()) + new_records
    all_records.sort(key=lambda x: x['timestamp'])
    
    # 写入文件
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ 成功保存 {len(all_records)} 条记录")
    print(f"✅ 新增记录: {len(new_records)} 条")
    print()
    
    print("=" * 80)
    print("🎉 1月3-9日历史数据补全完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()
