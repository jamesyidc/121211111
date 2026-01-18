#!/usr/bin/env python3
"""
10天历史K线数据下载脚本
下载所有27个币种的5分钟和1小时K线数据
"""

import requests
import sqlite3
import time
from datetime import datetime, timedelta
import sys

# OKEx API配置
OKEX_API_BASE = "https://www.okx.com"

# 目标币种列表（27个）
TARGET_SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP', 'XRP-USDT-SWAP',
    'DOGE-USDT-SWAP', 'ADA-USDT-SWAP', 'AVAX-USDT-SWAP', 'SHIB-USDT-SWAP',
    'TON-USDT-SWAP', 'DOT-USDT-SWAP', 'LINK-USDT-SWAP', 'TRX-USDT-SWAP',
    'MATIC-USDT-SWAP', 'BCH-USDT-SWAP', 'UNI-USDT-SWAP', 'LTC-USDT-SWAP',
    'ICP-USDT-SWAP', 'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'STX-USDT-SWAP',
    'FIL-USDT-SWAP', 'ARB-USDT-SWAP', 'OP-USDT-SWAP', 'SUI-USDT-SWAP',
    'HBAR-USDT-SWAP', 'LDO-USDT-SWAP', 'CFX-USDT-SWAP'
]

# 时间周期
TIMEFRAMES = {
    '5m': '5m',   # 5分钟
    '1H': '1H'    # 1小时
}

# 数据库路径
DB_PATH = '/home/user/webapp/crypto_data.db'

def get_kline_data(symbol, timeframe, after=None, limit=300):
    """
    从OKEx获取K线数据
    
    Args:
        symbol: 交易对 (如 'BTC-USDT-SWAP')
        timeframe: 时间周期 ('5m' 或 '1H')
        after: 获取此时间戳之前（更早）的数据（毫秒）
        limit: 返回数据条数（最大300）
    
    Returns:
        list: K线数据列表
    """
    url = f"{OKEX_API_BASE}/api/v5/market/history-candles"
    
    params = {
        'instId': symbol,
        'bar': timeframe,
        'limit': str(limit)
    }
    
    if after:
        params['after'] = str(after)
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == '0':
            if data.get('data'):
                return data['data']
            else:
                # 空数据可能意味着已经到达历史数据的末尾
                return []
        else:
            print(f"  ⚠️ API返回错误: code={data.get('code')}, msg={data.get('msg', 'Unknown')}")
            return []
    
    except requests.exceptions.RequestException as e:
        print(f"  ✗ 请求失败: {e}")
        return []

def save_kline_to_db(conn, symbol, timeframe, kline_data):
    """
    保存K线数据到数据库
    
    Args:
        conn: 数据库连接
        symbol: 交易对
        timeframe: 时间周期
        kline_data: K线数据列表
    
    Returns:
        int: 保存的数据条数
    """
    cursor = conn.cursor()
    saved_count = 0
    
    for candle in kline_data:
        timestamp = int(candle[0])
        open_price = float(candle[1])
        high_price = float(candle[2])
        low_price = float(candle[3])
        close_price = float(candle[4])
        volume = float(candle[5])
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO okex_kline_ohlc 
                (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (symbol, timeframe, timestamp, open_price, high_price, 
                  low_price, close_price, volume))
            saved_count += 1
        except Exception as e:
            print(f"  ⚠️ 保存数据失败 (ts={timestamp}): {e}")
    
    conn.commit()
    return saved_count

def download_history_for_symbol(conn, symbol, timeframe, days=10):
    """
    下载指定币种和周期的历史数据
    
    Args:
        conn: 数据库连接
        symbol: 交易对
        timeframe: 时间周期
        days: 下载天数（默认10天）
    
    Returns:
        int: 下载的总数据条数
    """
    print(f"\n{'='*60}")
    print(f"开始下载: {symbol} - {timeframe}")
    print(f"{'='*60}")
    
    # 计算时间范围（10天前到现在）
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # 转换为毫秒时间戳
    start_ts = int(start_time.timestamp() * 1000)
    
    print(f"目标时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"目标时间戳: >= {start_ts}")
    
    total_downloaded = 0
    batch_count = 0
    current_after = None  # None表示从最新数据开始
    
    # 循环获取数据直到达到开始时间
    while True:
        batch_count += 1
        
        if current_after:
            print(f"\n批次 {batch_count}: 获取 {datetime.fromtimestamp(current_after/1000).strftime('%Y-%m-%d %H:%M')} 之前的数据...", end=' ')
        else:
            print(f"\n批次 {batch_count}: 获取最新数据...", end=' ')
        
        # 获取一批数据（最多300条）
        kline_data = get_kline_data(symbol, timeframe, after=current_after, limit=300)
        
        if not kline_data:
            print("无数据返回（已达到历史数据末尾）")
            break
        
        print(f"获取到 {len(kline_data)} 条")
        
        # 检查最早的数据时间
        oldest_ts = int(kline_data[-1][0])
        oldest_dt = datetime.fromtimestamp(oldest_ts / 1000)
        newest_ts = int(kline_data[0][0])
        newest_dt = datetime.fromtimestamp(newest_ts / 1000)
        
        print(f"  数据时间: {oldest_dt.strftime('%Y-%m-%d %H:%M')} ~ {newest_dt.strftime('%Y-%m-%d %H:%M')}")
        
        # 保存到数据库
        saved = save_kline_to_db(conn, symbol, timeframe, kline_data)
        total_downloaded += saved
        print(f"  已保存 {saved} 条到数据库")
        
        # 如果最早的数据已经达到或超过开始时间，停止
        if oldest_ts <= start_ts:
            print(f"  ✓ 已达到目标时间 {start_time.strftime('%Y-%m-%d %H:%M')}")
            break
        
        # 更新after参数为当前批次最早的时间戳，用于获取更早的数据
        current_after = oldest_ts
        
        # 防止请求过快
        time.sleep(0.2)
    
    print(f"\n✓ 完成: {symbol} - {timeframe}")
    print(f"  总计下载: {total_downloaded} 条K线数据")
    print(f"  批次数: {batch_count}")
    
    return total_downloaded

def main():
    """主函数"""
    print("=" * 80)
    print("10天历史K线数据下载")
    print("=" * 80)
    print(f"目标币种: {len(TARGET_SYMBOLS)} 个")
    print(f"时间周期: {list(TIMEFRAMES.keys())}")
    print(f"下载天数: 10天")
    print(f"数据库: {DB_PATH}")
    print("=" * 80)
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    
    # 统计信息
    total_symbols = len(TARGET_SYMBOLS)
    total_tasks = total_symbols * len(TIMEFRAMES)
    completed_tasks = 0
    failed_tasks = []
    total_records = 0
    
    start_time = datetime.now()
    
    # 遍历所有币种和时间周期
    for i, symbol in enumerate(TARGET_SYMBOLS, 1):
        print(f"\n{'#'*80}")
        print(f"进度: {i}/{total_symbols} - {symbol}")
        print(f"{'#'*80}")
        
        for timeframe_key, timeframe_value in TIMEFRAMES.items():
            try:
                downloaded = download_history_for_symbol(conn, symbol, timeframe_value, days=10)
                total_records += downloaded
                completed_tasks += 1
                
                print(f"\n✓ 任务完成: {completed_tasks}/{total_tasks}")
                
            except Exception as e:
                print(f"\n✗ 下载失败: {symbol} - {timeframe_key}")
                print(f"  错误: {e}")
                failed_tasks.append(f"{symbol} - {timeframe_key}")
                completed_tasks += 1
            
            # 任务间隔
            time.sleep(0.5)
    
    # 关闭数据库连接
    conn.close()
    
    # 计算总耗时
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 打印总结
    print("\n" + "=" * 80)
    print("下载任务完成")
    print("=" * 80)
    print(f"总计币种: {total_symbols}")
    print(f"总计任务: {total_tasks}")
    print(f"成功完成: {completed_tasks - len(failed_tasks)}")
    print(f"失败任务: {len(failed_tasks)}")
    print(f"下载记录: {total_records} 条")
    print(f"总耗时: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")
    
    if failed_tasks:
        print(f"\n失败任务列表:")
        for task in failed_tasks:
            print(f"  - {task}")
    else:
        print(f"\n✓ 所有任务都成功完成！")
    
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断下载")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ 程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
