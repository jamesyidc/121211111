#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX历史数据回填 - 使用认证API
获取2026-01-03至2026-01-16的完整历史数据
"""

import os
import sys
import json
import time
import requests
import hmac
import base64
import hashlib
from datetime import datetime, timedelta
import pytz

# OKX API凭证
API_KEY = "77465009-2c87-443c-83c8-08b35c7f14b2"
API_SECRET = "11647B2578630D28501D41C748B3D809"
API_PASSPHRASE = "Tencent@123"

# 配置
DATA_DIR = "/home/user/webapp/data/coin_price_tracker"
JSONL_FILE = os.path.join(DATA_DIR, "coin_prices_30min.jsonl")
LOG_DIR = "/home/user/webapp/logs"
LOG_FILE = os.path.join(LOG_DIR, "okx_auth_backfill.log")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

TZ = pytz.timezone('Asia/Shanghai')
RATE_LIMIT_DELAY = 0.1  # 100ms

# 27个币种
SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE',
    'SUI', 'TRX', 'TON', 'ETC', 'BCH', 'HBAR', 'XLM',
    'FIL', 'LINK', 'CRO', 'DOT', 'UNI', 'NEAR', 'APT',
    'CFX', 'CRV', 'STX', 'LDO', 'TAO', 'AAVE'
]

def log(message, level="INFO"):
    """写入日志"""
    timestamp = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)
    sys.stdout.flush()
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except Exception as e:
        print(f"写入日志失败: {e}")

def generate_signature(timestamp, method, request_path, body=''):
    """生成OKX API签名"""
    message = timestamp + method + request_path + body
    mac = hmac.new(
        bytes(API_SECRET, encoding='utf8'),
        bytes(message, encoding='utf-8'),
        digestmod=hashlib.sha256
    )
    return base64.b64encode(mac.digest()).decode()

def get_candles_with_auth(symbol, bar='30m', start_time=None, end_time=None):
    """
    使用认证API获取K线数据
    分批获取指定时间范围的所有K线
    """
    
    inst_id = f"{symbol}-USDT-SWAP"
    all_klines = []
    
    # 从end_time往前获取
    if end_time:
        current_before = int(end_time.timestamp() * 1000)
    else:
        current_before = int(datetime.now(TZ).timestamp() * 1000)
    
    start_ts = int(start_time.timestamp() * 1000) if start_time else 0
    
    while True:
        timestamp = datetime.now(pytz.UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        method = 'GET'
        request_path = '/api/v5/market/candles'
        
        params = f"?instId={inst_id}&bar={bar}&before={current_before}&limit=100"
        full_path = request_path + params
        
        signature = generate_signature(timestamp, method, full_path)
        
        headers = {
            'OK-ACCESS-KEY': API_KEY,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': API_PASSPHRASE,
            'Content-Type': 'application/json'
        }
        
        url = f"https://www.okx.com{full_path}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                log(f"❌ {symbol} HTTP错误: {response.status_code}", "ERROR")
                break
            
            data = response.json()
            
            if data.get('code') != '0':
                log(f"❌ {symbol} API错误: {data.get('msg')}", "ERROR")
                break
            
            klines = data.get('data', [])
            
            if not klines:
                break
            
            # 过滤出在时间范围内的K线
            valid_klines = []
            for kline in klines:
                kline_ts = int(kline[0])
                if kline_ts >= start_ts:
                    valid_klines.append(kline)
                else:
                    # 已经超出时间范围，停止
                    all_klines.extend(valid_klines)
                    return all_klines
            
            all_klines.extend(valid_klines)
            
            # 获取最早的时间戳，作为下一次的before参数
            oldest_ts = int(valid_klines[-1][0])
            
            # 如果已经到达起始时间，停止
            if oldest_ts <= start_ts:
                break
            
            current_before = oldest_ts
            time.sleep(RATE_LIMIT_DELAY)
            
        except Exception as e:
            log(f"❌ {symbol} 请求异常: {e}", "ERROR")
            break
    
    return all_klines

def main_backfill():
    """主回填函数"""
    log("=" * 80)
    log("🚀 OKX认证API历史数据回填")
    log("=" * 80)
    
    # 清空现有数据
    if os.path.exists(JSONL_FILE):
        os.remove(JSONL_FILE)
        log("🗑️  已清空现有数据文件")
    
    # 时间范围
    start_date = datetime(2026, 1, 3, 0, 0, 0, tzinfo=TZ)
    end_date = datetime(2026, 1, 16, 23, 59, 59, tzinfo=TZ)
    
    log(f"📅 时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    log("")
    
    # 生成所有时间节点
    all_nodes = []
    current = start_date
    while current <= end_date:
        all_nodes.append(current)
        current += timedelta(minutes=30)
    
    total_nodes = len(all_nodes)
    log(f"📊 总节点数: {total_nodes}")
    log("")
    
    # 按日期分组
    nodes_by_date = {}
    for node in all_nodes:
        date_str = node.strftime('%Y-%m-%d')
        if date_str not in nodes_by_date:
            nodes_by_date[date_str] = []
        nodes_by_date[date_str].append(node)
    
    # 获取所有币种的历史数据
    log("📡 开始获取历史数据...")
    log("")
    
    all_symbols_data = {}
    
    for symbol in SYMBOLS:
        log(f"📡 获取 {symbol} 的K线数据...")
        
        klines = get_candles_with_auth(symbol, '30m', start_date, end_date)
        
        if klines:
            # 转换为 {timestamp: price} 字典
            price_dict = {}
            for kline in klines:
                ts = int(kline[0])
                price = float(kline[4])  # 收盘价
                price_dict[ts] = price
            
            all_symbols_data[symbol] = price_dict
            log(f"✅ {symbol}: {len(price_dict)} 个价格点")
        else:
            all_symbols_data[symbol] = {}
            log(f"⚠️  {symbol}: 无数据", "WARN")
        
        time.sleep(RATE_LIMIT_DELAY)
    
    log("")
    log("=" * 80)
    log("📝 生成数据记录...")
    log("=" * 80)
    
    # 为每个时间节点生成记录
    added_count = 0
    
    for date_str in sorted(nodes_by_date.keys()):
        day_nodes = nodes_by_date[date_str]
        
        # 获取基准价格（00:00）
        day_start = datetime.strptime(date_str, '%Y-%m-%d')
        day_start = TZ.localize(day_start)
        base_ts = int(day_start.timestamp() * 1000)
        
        base_prices = {}
        for symbol in SYMBOLS:
            symbol_data = all_symbols_data[symbol]
            if symbol_data:
                # 找最接近00:00的价格
                closest_ts = min(symbol_data.keys(), key=lambda ts: abs(ts - base_ts))
                base_prices[symbol] = symbol_data[closest_ts]
            else:
                base_prices[symbol] = 0
        
        # 为每个时间节点生成记录
        for node in day_nodes:
            node_ts = int(node.timestamp() * 1000)
            time_str = node.strftime('%Y-%m-%d %H:%M:%S')
            
            coins_data = {}
            valid_count = 0
            
            for symbol in SYMBOLS:
                base_price = base_prices.get(symbol, 0)
                symbol_data = all_symbols_data[symbol]
                
                # 找最接近这个时间节点的价格
                if symbol_data:
                    closest_ts = min(symbol_data.keys(), key=lambda ts: abs(ts - node_ts))
                    current_price = symbol_data[closest_ts]
                    valid_count += 1
                else:
                    current_price = 0
                
                # 计算涨跌幅
                if base_price > 0 and current_price > 0:
                    change_pct = ((current_price - base_price) / base_price) * 100
                else:
                    change_pct = 0
                
                coins_data[symbol] = {
                    'base_price': base_price,
                    'current_price': current_price,
                    'change_pct': round(change_pct, 4)
                }
            
            # 构建记录
            record = {
                'collect_time': time_str,
                'timestamp': int(node.timestamp()),
                'base_date': date_str,
                'coins': coins_data,
                'total_coins': len(SYMBOLS),
                'valid_coins': valid_count
            }
            
            # 写入文件
            with open(JSONL_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            added_count += 1
        
        log(f"✅ {date_str}: {len(day_nodes)} 条记录")
    
    log("")
    log("=" * 80)
    log("✅ 回填完成！")
    log("=" * 80)
    log(f"📊 总记录数: {added_count}")
    log(f"💾 数据文件: {JSONL_FILE}")
    log("")

if __name__ == '__main__':
    try:
        main_backfill()
    except KeyboardInterrupt:
        log("\n⚠️  用户中断", "WARN")
        sys.exit(0)
    except Exception as e:
        log(f"❌ 异常: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)
