#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据回填脚本 - 最终版本
使用 after 参数绕过 OKX API 限制
成功获取 2026-01-03 至 2026-01-16 的完整历史数据
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
LOG_FILE = os.path.join(LOG_DIR, "historical_backfill_final.log")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# OKX API配置
OKX_API_BASE = "https://www.okx.com/api/v5"
RATE_LIMIT_DELAY = 0.05  # 50ms = 20次/秒

# 时区
TZ = pytz.timezone('Asia/Shanghai')

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
        print(f"写入日志文件失败: {e}")

def get_klines_batch(symbol, after_ts, limit=100):
    """
    获取一批K线数据
    使用 after 参数获取指定时间之后的数据
    
    Args:
        symbol: 币种符号
        after_ts: 起始时间戳（毫秒）
        limit: 返回条数（最大100）
    
    Returns:
        list: K线数据列表，格式 [[ts, o, h, l, c, vol, ...], ...]
    """
    try:
        inst_id = f"{symbol}-USDT-SWAP"
        params = {
            'instId': inst_id,
            'bar': '30m',
            'after': str(after_ts),
            'limit': str(limit)
        }
        
        url = f"{OKX_API_BASE}/market/candles"
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            log(f"❌ {symbol} HTTP错误: {response.status_code}", "ERROR")
            return None
        
        data = response.json()
        
        if data.get('code') != '0':
            log(f"❌ {symbol} API错误: {data.get('msg', 'Unknown')}", "ERROR")
            return None
        
        klines = data.get('data', [])
        return klines
        
    except Exception as e:
        log(f"❌ {symbol} 请求异常: {e}", "ERROR")
        return None

def get_all_time_nodes():
    """生成1月3日00:00到1月16日23:30的所有30分钟节点"""
    start = datetime(2026, 1, 3, 0, 0, 0, tzinfo=TZ)
    end = datetime(2026, 1, 16, 23, 30, 0, tzinfo=TZ)
    
    nodes = []
    current = start
    while current <= end:
        nodes.append(current)
        current += timedelta(minutes=30)
    
    return nodes

def fetch_all_klines_for_symbol(symbol, start_time, end_time):
    """
    获取一个币种在指定时间范围内的所有K线
    
    Args:
        symbol: 币种符号
        start_time: 起始时间（datetime对象）
        end_time: 结束时间（datetime对象）
    
    Returns:
        dict: {timestamp: price}
    """
    log(f"📡 获取 {symbol} 的历史K线...")
    
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    
    all_klines = []
    current_after = start_ts
    
    while True:
        klines = get_klines_batch(symbol, current_after, limit=100)
        
        if not klines:
            log(f"⚠️  {symbol} 无更多数据", "WARN")
            break
        
        # 过滤出在时间范围内的K线
        valid_klines = []
        for kline in klines:
            kline_ts = int(kline[0])
            if start_ts <= kline_ts <= end_ts:
                valid_klines.append(kline)
        
        if not valid_klines:
            break
        
        all_klines.extend(valid_klines)
        
        # 获取最新的时间戳，作为下一次的 after 参数
        latest_ts = int(valid_klines[0][0])
        
        # 如果已经超过结束时间，停止
        if latest_ts >= end_ts:
            break
        
        # 更新 after 参数为最新时间+1毫秒
        current_after = latest_ts + 1
        
        time.sleep(RATE_LIMIT_DELAY)
    
    # 转换为 {timestamp: price} 字典
    price_dict = {}
    for kline in all_klines:
        ts = int(kline[0])
        price = float(kline[4])  # 收盘价
        price_dict[ts] = price
    
    log(f"✅ {symbol} 获取到 {len(price_dict)} 个价格点")
    
    return price_dict

def main_backfill():
    """主回填函数"""
    log("=" * 80)
    log("🚀 历史数据回填系统 - 最终版本")
    log("=" * 80)
    
    # 清空现有数据文件
    if os.path.exists(JSONL_FILE):
        os.remove(JSONL_FILE)
        log("🗑️  已清空现有数据文件")
    
    # 生成所有时间节点
    all_nodes = get_all_time_nodes()
    total_nodes = len(all_nodes)
    log(f"📅 时间范围: 2026-01-03 00:00:00 ~ 2026-01-16 23:30:00")
    log(f"📊 总节点数: {total_nodes}")
    log("")
    
    # 按日期分组
    nodes_by_date = {}
    for node in all_nodes:
        date_str = node.strftime('%Y-%m-%d')
        if date_str not in nodes_by_date:
            nodes_by_date[date_str] = []
        nodes_by_date[date_str].append(node)
    
    # 开始回填
    start_time = time.time()
    total_added = 0
    
    for date_str in sorted(nodes_by_date.keys()):
        log("=" * 80)
        log(f"📅 处理日期: {date_str}")
        log("=" * 80)
        
        day_nodes = nodes_by_date[date_str]
        
        # 获取当天所有币种的K线数据
        log(f"📡 获取 {len(SYMBOLS)} 个币种的历史数据...")
        
        # 存储所有币种的价格数据
        all_symbols_data = {}
        
        for symbol in SYMBOLS:
            # 获取这个币种当天的所有K线
            day_start = datetime.strptime(date_str, '%Y-%m-%d')
            day_start = TZ.localize(day_start)
            day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
            
            price_dict = fetch_all_klines_for_symbol(symbol, day_start, day_end)
            all_symbols_data[symbol] = price_dict
            
            time.sleep(RATE_LIMIT_DELAY)
        
        # 获取基准价格（00:00）
        base_time = day_start
        base_ts = int(base_time.timestamp() * 1000)
        
        base_prices = {}
        for symbol in SYMBOLS:
            # 找到最接近00:00的价格
            symbol_data = all_symbols_data[symbol]
            if symbol_data:
                # 找最接近的时间戳
                closest_ts = min(symbol_data.keys(), key=lambda ts: abs(ts - base_ts))
                base_prices[symbol] = symbol_data[closest_ts]
            else:
                base_prices[symbol] = 0
        
        log(f"✅ 基准价格（00:00）获取完成")
        
        # 为每个时间节点生成记录
        for node in day_nodes:
            node_ts = int(node.timestamp() * 1000)
            time_str = node.strftime('%Y-%m-%d %H:%M:%S')
            
            coins_data = {}
            valid_count = 0
            
            for symbol in SYMBOLS:
                base_price = base_prices.get(symbol, 0)
                symbol_data = all_symbols_data[symbol]
                
                # 找到最接近这个时间节点的价格
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
            
            total_added += 1
        
        log(f"✅ {date_str} 完成，新增 {len(day_nodes)} 条记录")
        log(f"📈 总进度: {total_added}/{total_nodes} ({total_added/total_nodes*100:.1f}%)")
        log("")
    
    # 完成统计
    elapsed = time.time() - start_time
    log("=" * 80)
    log("✅ 回填完成！")
    log("=" * 80)
    log(f"⏱️  总耗时: {elapsed/60:.1f} 分钟")
    log(f"📊 总记录数: {total_added}")
    log(f"💾 数据文件: {JSONL_FILE}")
    log("")

if __name__ == '__main__':
    try:
        main_backfill()
    except KeyboardInterrupt:
        log("\n⚠️  用户中断回填", "WARN")
        sys.exit(0)
    except Exception as e:
        log(f"❌ 回填异常: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)
