#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能数据回填系统 v3.0
功能：
1. 记录失败的币种和时间点
2. 下次优先重试失败的数据
3. 符合OKX限流策略（20次/秒）
4. 生成失败数据清单
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
FAILED_FILE = os.path.join(DATA_DIR, "failed_records.json")
LOG_DIR = "/home/user/webapp/logs"
LOG_FILE = os.path.join(LOG_DIR, "smart_backfill.log")

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

# 日志函数
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

# 加载失败记录
def load_failed_records():
    """加载失败记录"""
    if not os.path.exists(FAILED_FILE):
        return {}
    
    try:
        with open(FAILED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"加载失败记录出错: {e}", "ERROR")
        return {}

# 保存失败记录
def save_failed_records(failed_records):
    """保存失败记录"""
    try:
        with open(FAILED_FILE, 'w', encoding='utf-8') as f:
            json.dump(failed_records, f, ensure_ascii=False, indent=2)
        log(f"💾 已保存失败记录: {len(failed_records)} 个时间点")
    except Exception as e:
        log(f"保存失败记录出错: {e}", "ERROR")

# 获取30分钟K线价格
def get_price_30m(symbol, target_time):
    """
    获取指定时间点的30分钟K线价格
    
    Args:
        symbol: 币种符号（如 BTC）
        target_time: 目标时间（datetime对象，Asia/Shanghai时区）
    
    Returns:
        float or None: 返回收盘价，失败返回None
    """
    try:
        # 将时间转换为毫秒时间戳
        target_ts = int(target_time.timestamp() * 1000)
        
        # 构建请求参数
        inst_id = f"{symbol}-USDT-SWAP"
        params = {
            'instId': inst_id,
            'bar': '30m',  # 30分钟K线
            'before': str(target_ts + 1800000),  # 目标时间 + 30分钟
            'limit': '3'
        }
        
        # 发送请求
        url = f"{OKX_API_BASE}/market/candles"
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            log(f"❌ {symbol} HTTP错误: {response.status_code}", "ERROR")
            return None
        
        data = response.json()
        
        # 检查API返回
        if data.get('code') != '0':
            log(f"❌ {symbol} API错误: {data.get('msg', 'Unknown')}", "ERROR")
            return None
        
        if not data.get('data'):
            log(f"⚠️  {symbol} 无K线数据", "WARN")
            return None
        
        # 找到最接近目标时间的K线
        klines = data['data']
        best_kline = None
        min_diff = float('inf')
        
        for kline in klines:
            kline_ts = int(kline[0])
            diff = abs(kline_ts - target_ts)
            
            if diff < min_diff:
                min_diff = diff
                best_kline = kline
        
        if best_kline:
            price = float(best_kline[4])  # 收盘价
            return price
        else:
            log(f"⚠️  {symbol} 未找到合适的K线", "WARN")
            return None
            
    except Exception as e:
        log(f"❌ {symbol} 获取价格异常: {e}", "ERROR")
        return None

# 加载已存在的数据
def load_existing_data():
    """加载已存在的数据"""
    existing_times = set()
    
    if not os.path.exists(JSONL_FILE):
        return existing_times
    
    try:
        with open(JSONL_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        collect_time = record.get('collect_time')
                        if collect_time:
                            existing_times.add(collect_time)
                    except:
                        pass
        
        log(f"📊 已加载 {len(existing_times)} 个现有时间点")
        return existing_times
    except Exception as e:
        log(f"加载现有数据出错: {e}", "ERROR")
        return existing_times

# 生成所有时间节点
def generate_all_time_nodes():
    """生成1月3日至1月16日的所有30分钟节点"""
    start_date = datetime(2026, 1, 3, 0, 0, 0, tzinfo=TZ)
    end_date = datetime(2026, 1, 16, 23, 30, 0, tzinfo=TZ)
    
    time_nodes = []
    current = start_date
    
    while current <= end_date:
        time_nodes.append(current)
        current += timedelta(minutes=30)
    
    log(f"📅 生成 {len(time_nodes)} 个时间节点（1月3日 - 1月16日）")
    return time_nodes

# 获取基准价格（当天00:00的价格）
def get_base_prices_for_date(date_str, failed_records):
    """
    获取指定日期所有币种的基准价格（00:00时刻）
    
    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
        failed_records: 失败记录字典
    
    Returns:
        dict: {symbol: base_price}
    """
    base_prices = {}
    base_time_str = f"{date_str} 00:00:00"
    
    # 检查是否有失败记录
    if base_time_str in failed_records:
        log(f"🔄 优先重试失败的基准价格: {base_time_str}")
    
    # 构建00:00时间
    base_time = datetime.strptime(base_time_str, '%Y-%m-%d %H:%M:%S')
    base_time = TZ.localize(base_time)
    
    log(f"📌 获取 {date_str} 的基准价格（00:00）")
    
    failed_symbols = []
    
    for symbol in SYMBOLS:
        price = get_price_30m(symbol, base_time)
        
        if price is not None:
            base_prices[symbol] = price
            log(f"  ✅ {symbol}: ${price:.8f}")
        else:
            failed_symbols.append(symbol)
            log(f"  ❌ {symbol}: 获取失败", "ERROR")
        
        time.sleep(RATE_LIMIT_DELAY)  # 限流
    
    # 记录失败的币种
    if failed_symbols:
        if base_time_str not in failed_records:
            failed_records[base_time_str] = {}
        failed_records[base_time_str]['base_price_failed'] = failed_symbols
    
    return base_prices

# 回填单个时间点的数据
def backfill_single_timepoint(target_time, base_prices, failed_records, existing_times):
    """
    回填单个时间点的数据
    
    Args:
        target_time: 目标时间（datetime对象）
        base_prices: 基准价格字典
        failed_records: 失败记录字典
        existing_times: 已存在的时间点集合
    
    Returns:
        bool: 是否成功
    """
    time_str = target_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 跳过已存在的数据
    if time_str in existing_times:
        return True
    
    # 检查是否有失败记录
    is_retry = time_str in failed_records
    if is_retry:
        log(f"🔄 优先重试: {time_str}")
    
    coins_data = {}
    failed_symbols = []
    success_count = 0
    
    for symbol in SYMBOLS:
        # 获取当前价格
        current_price = get_price_30m(symbol, target_time)
        
        if current_price is not None:
            base_price = base_prices.get(symbol, 0)
            
            # 计算涨跌幅
            if base_price > 0:
                change_pct = ((current_price - base_price) / base_price) * 100
            else:
                change_pct = 0
            
            coins_data[symbol] = {
                'base_price': base_price,
                'current_price': current_price,
                'change_pct': round(change_pct, 4)
            }
            
            success_count += 1
        else:
            failed_symbols.append(symbol)
            # 记录失败，但仍然写入0值
            coins_data[symbol] = {
                'base_price': base_prices.get(symbol, 0),
                'current_price': 0,
                'change_pct': 0
            }
        
        time.sleep(RATE_LIMIT_DELAY)  # 限流
    
    # 构建记录
    record = {
        'collect_time': time_str,
        'timestamp': int(target_time.timestamp()),
        'base_date': target_time.strftime('%Y-%m-%d'),
        'coins': coins_data,
        'total_coins': len(SYMBOLS),
        'valid_coins': success_count
    }
    
    # 写入JSONL文件
    try:
        with open(JSONL_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception as e:
        log(f"❌ 写入文件失败: {e}", "ERROR")
        return False
    
    # 记录失败的币种
    if failed_symbols:
        if time_str not in failed_records:
            failed_records[time_str] = {}
        failed_records[time_str]['failed_symbols'] = failed_symbols
        log(f"⚠️  {time_str} 有 {len(failed_symbols)} 个币种获取失败: {', '.join(failed_symbols)}", "WARN")
    else:
        # 如果全部成功，从失败记录中移除
        if time_str in failed_records:
            del failed_records[time_str]
    
    return True

# 主回填函数
def main_backfill():
    """主回填函数"""
    log("=" * 80)
    log("🚀 智能数据回填系统 v3.0 启动")
    log("=" * 80)
    
    # 加载失败记录
    failed_records = load_failed_records()
    log(f"📋 加载失败记录: {len(failed_records)} 个时间点")
    
    # 加载已存在的数据
    existing_times = load_existing_data()
    
    # 生成所有时间节点
    all_time_nodes = generate_all_time_nodes()
    total_nodes = len(all_time_nodes)
    
    # 按日期分组
    dates_dict = {}
    for node in all_time_nodes:
        date_str = node.strftime('%Y-%m-%d')
        if date_str not in dates_dict:
            dates_dict[date_str] = []
        dates_dict[date_str].append(node)
    
    # 统计信息
    completed = len(existing_times)
    failed_count = len(failed_records)
    remaining = total_nodes - completed
    
    log(f"📊 数据统计:")
    log(f"   总节点数: {total_nodes}")
    log(f"   已完成: {completed} ({completed/total_nodes*100:.1f}%)")
    log(f"   失败节点: {failed_count}")
    log(f"   待回填: {remaining}")
    
    # 开始回填
    start_time = time.time()
    processed = 0
    newly_added = 0
    
    # 优先处理失败的节点
    priority_times = []
    normal_times = []
    
    for date_str in sorted(dates_dict.keys()):
        for time_node in dates_dict[date_str]:
            time_str = time_node.strftime('%Y-%m-%d %H:%M:%S')
            if time_str in failed_records:
                priority_times.append((date_str, time_node))
            else:
                normal_times.append((date_str, time_node))
    
    log(f"🎯 优先处理 {len(priority_times)} 个失败节点")
    log(f"📝 常规处理 {len(normal_times)} 个节点")
    
    # 合并处理列表（失败的优先）
    all_tasks = priority_times + normal_times
    
    # 按日期处理
    current_date = None
    base_prices = {}
    
    for date_str, time_node in all_tasks:
        # 如果是新的一天，获取基准价格
        if date_str != current_date:
            log("")
            log("=" * 80)
            log(f"📅 处理日期: {date_str}")
            log("=" * 80)
            
            base_prices = get_base_prices_for_date(date_str, failed_records)
            
            if len(base_prices) < len(SYMBOLS):
                log(f"⚠️  基准价格不完整: {len(base_prices)}/{len(SYMBOLS)}", "WARN")
            
            current_date = date_str
        
        # 回填时间点
        time_str = time_node.strftime('%Y-%m-%d %H:%M:%S')
        
        if time_str not in existing_times:
            success = backfill_single_timepoint(time_node, base_prices, failed_records, existing_times)
            
            if success:
                newly_added += 1
                existing_times.add(time_str)
        
        processed += 1
        
        # 进度显示
        if processed % 10 == 0:
            elapsed = time.time() - start_time
            progress = processed / total_nodes * 100
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total_nodes - processed) / rate if rate > 0 else 0
            
            log(f"📈 进度: {progress:.1f}% | 已处理: {processed}/{total_nodes} | "
                f"新增: {newly_added} | 速度: {rate:.1f}节点/秒 | 预计剩余: {eta/60:.1f}分钟")
        
        # 每完成一天，保存失败记录
        if time_str.endswith('23:30:00'):
            save_failed_records(failed_records)
    
    # 最终保存失败记录
    save_failed_records(failed_records)
    
    # 完成统计
    elapsed = time.time() - start_time
    log("")
    log("=" * 80)
    log("✅ 回填完成！")
    log("=" * 80)
    log(f"📊 最终统计:")
    log(f"   总耗时: {elapsed/60:.1f} 分钟")
    log(f"   总节点数: {total_nodes}")
    log(f"   新增数据: {newly_added}")
    log(f"   最终完成: {len(existing_times)} ({len(existing_times)/total_nodes*100:.1f}%)")
    log(f"   失败节点: {len(failed_records)}")
    log(f"   数据文件: {JSONL_FILE}")
    log(f"   失败清单: {FAILED_FILE}")
    
    # 显示失败清单摘要
    if failed_records:
        log("")
        log("⚠️  失败节点摘要（前10个）:")
        for i, (time_str, info) in enumerate(list(failed_records.items())[:10]):
            failed_syms = info.get('failed_symbols', [])
            base_failed = info.get('base_price_failed', [])
            log(f"   {i+1}. {time_str}: {len(failed_syms)} 个币种失败")
            if failed_syms:
                log(f"      币种: {', '.join(failed_syms[:5])}")
            if base_failed:
                log(f"      基准价失败: {', '.join(base_failed[:5])}")

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
