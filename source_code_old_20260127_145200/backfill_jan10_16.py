#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回填1月10-16日数据 - 使用OKX API
时间显示：北京时间（UTC+8）
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
import pytz

# 配置
DATA_DIR = "/home/user/webapp/data/coin_price_tracker"
JSONL_FILE = os.path.join(DATA_DIR, "coin_prices_30min.jsonl")
LOG_DIR = "/home/user/webapp/logs"
LOG_FILE = os.path.join(LOG_DIR, "backfill_jan10_16.log")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# 北京时间
TZ = pytz.timezone('Asia/Shanghai')
RATE_LIMIT_DELAY = 0.05  # 50ms

# 27个币种
SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE',
    'SUI', 'TRX', 'TON', 'ETC', 'BCH', 'HBAR', 'XLM',
    'FIL', 'LINK', 'CRO', 'DOT', 'UNI', 'NEAR', 'APT',
    'CFX', 'CRV', 'STX', 'LDO', 'TAO', 'AAVE'
]

def log(message, level="INFO"):
    """写入日志 - 北京时间"""
    timestamp = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)
    sys.stdout.flush()
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except Exception as e:
        print(f"写入日志失败: {e}")

def get_klines_for_date(symbol, date):
    """
    获取指定日期的所有30分钟K线
    
    Args:
        symbol: 币种
        date: 日期（datetime对象，北京时间）
    
    Returns:
        list: K线数据
    """
    # 获取当天的所有K线（最多48条）
    params = {
        'instId': f'{symbol}-USDT-SWAP',
        'bar': '30m',
        'limit': '300'  # 获取足够多的数据
    }
    
    try:
        response = requests.get('https://www.okx.com/api/v5/market/candles', params=params, timeout=10)
        
        if response.status_code != 200:
            log(f"❌ {symbol} HTTP错误: {response.status_code}", "ERROR")
            return []
        
        data = response.json()
        
        if data.get('code') != '0':
            log(f"❌ {symbol} API错误: {data.get('msg')}", "ERROR")
            return []
        
        klines = data.get('data', [])
        
        # 过滤出指定日期的K线
        date_klines = []
        for kline in klines:
            kline_time = datetime.fromtimestamp(int(kline[0])/1000, TZ)
            if kline_time.date() == date.date():
                date_klines.append(kline)
        
        return date_klines
        
    except Exception as e:
        log(f"❌ {symbol} 请求异常: {e}", "ERROR")
        return []

def main_backfill():
    """主回填函数"""
    log("=" * 80)
    log("🚀 开始回填1月10-16日数据")
    log("🕐 时区：北京时间（UTC+8）")
    log("=" * 80)
    
    # 清空现有数据
    if os.path.exists(JSONL_FILE):
        os.remove(JSONL_FILE)
        log("🗑️  已清空现有数据文件")
    
    # 时间范围：1月10日00:00 到 1月16日23:30（北京时间）
    start_date = datetime(2026, 1, 10, 0, 0, 0, tzinfo=TZ)
    end_date = datetime(2026, 1, 16, 23, 30, 0, tzinfo=TZ)
    
    log(f"📅 时间范围: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
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
    dates = []
    current_date = start_date.date()
    while current_date <= end_date.date():
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    # 为每个日期获取所有币种的数据
    log("📡 开始获取历史数据...")
    log("")
    
    all_data = {}  # {symbol: {timestamp: price}}
    
    for symbol in SYMBOLS:
        log(f"📡 获取 {symbol} 的数据...")
        
        symbol_data = {}
        
        for date in dates:
            date_dt = datetime.combine(date, datetime.min.time())
            date_dt = TZ.localize(date_dt)
            
            klines = get_klines_for_date(symbol, date_dt)
            
            for kline in klines:
                ts = int(kline[0])
                price = float(kline[4])  # 收盘价
                symbol_data[ts] = price
            
            time.sleep(RATE_LIMIT_DELAY)
        
        all_data[symbol] = symbol_data
        log(f"✅ {symbol}: {len(symbol_data)} 个价格点")
    
    log("")
    log("=" * 80)
    log("📝 生成数据记录...")
    log("=" * 80)
    
    # 为每个时间节点生成记录
    added_count = 0
    
    for date in dates:
        # 获取当天00:00的基准价格
        day_start = datetime.combine(date, datetime.min.time())
        day_start = TZ.localize(day_start)
        base_ts = int(day_start.timestamp() * 1000)
        
        base_prices = {}
        for symbol in SYMBOLS:
            symbol_data = all_data[symbol]
            if symbol_data:
                # 找最接近00:00的价格
                closest_ts = min(symbol_data.keys(), key=lambda ts: abs(ts - base_ts))
                base_prices[symbol] = symbol_data[closest_ts]
            else:
                base_prices[symbol] = 0
        
        # 为当天的每个30分钟节点生成记录
        day_nodes = [n for n in all_nodes if n.date() == date]
        
        for node in day_nodes:
            node_ts = int(node.timestamp() * 1000)
            time_str = node.strftime('%Y-%m-%d %H:%M:%S')
            
            coins_data = {}
            valid_count = 0
            
            for symbol in SYMBOLS:
                base_price = base_prices.get(symbol, 0)
                symbol_data = all_data[symbol]
                
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
                'base_date': date.strftime('%Y-%m-%d'),
                'coins': coins_data,
                'total_coins': len(SYMBOLS),
                'valid_coins': valid_count
            }
            
            # 写入文件
            with open(JSONL_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            added_count += 1
        
        log(f"✅ {date.strftime('%Y-%m-%d')}: {len(day_nodes)} 条记录")
    
    log("")
    log("=" * 80)
    log("✅ 回填完成！")
    log("=" * 80)
    log(f"📊 总记录数: {added_count}")
    log(f"💾 数据文件: {JSONL_FILE}")
    log(f"🕐 所有时间均为北京时间（UTC+8）")
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
