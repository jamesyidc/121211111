#!/usr/bin/env python3
"""
OKX 27币种涨跌历史数据回填脚本
从2026-01-03 00:00:00 回填到当前时间
每分钟一个数据点
"""
import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
import pytz

# 添加项目路径
sys.path.insert(0, '/home/user/webapp/source_code')
from okx_trading_jsonl_manager import OKXTradingJSONLManager

# OKX API配置
OKX_API_BASE = "https://www.okx.com/api/v5"

# 27个币种列表
SYMBOLS = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "LTC", "DOGE", "SUI", "TRX", "TON",
    "ETC", "BCH", "HBAR", "XLM", "FIL", "LINK", "CRO", "DOT", "UNI", "NEAR",
    "APT", "CFX", "CRV", "STX", "LDO", "TAO", "AAVE"
]

# 初始化管理器
manager = OKXTradingJSONLManager()

def fetch_okx_kline_at_time(symbol, target_time):
    """
    获取指定时间的K线数据（1分钟K线）
    
    Args:
        symbol: 币种符号
        target_time: 目标时间（datetime对象）
    
    Returns:
        dict: {price, open_utc8} 或 None
    """
    try:
        inst_id = f"{symbol}-USDT-SWAP"
        
        # 将目标时间转换为毫秒时间戳
        target_ts = int(target_time.timestamp() * 1000)
        
        # 获取K线数据（1分钟K线，获取2根以确保覆盖目标时间）
        url = f"{OKX_API_BASE}/market/candles"
        params = {
            "instId": inst_id,
            "bar": "1m",  # 1分钟K线
            "before": str(target_ts),  # 在这个时间之前
            "limit": 2
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"  ❌ {symbol}: HTTP {response.status_code}")
            return None
        
        data = response.json()
        if data.get("code") != "0" or not data.get("data"):
            print(f"  ❌ {symbol}: API返回错误或无数据")
            return None
        
        # K线数据格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        kline = data["data"][0]
        
        close_price = float(kline[4])  # 收盘价
        
        # 获取UTC+8开盘价（当天00:00的开盘价）
        # 计算当天UTC+8的00:00时刻
        target_date = target_time.astimezone(pytz.timezone('Asia/Shanghai')).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_start_ts = int(target_date.timestamp() * 1000)
        
        # 获取日K线（1天）
        params_day = {
            "instId": inst_id,
            "bar": "1D",
            "before": str(day_start_ts + 86400000),  # 第二天开始
            "limit": 1
        }
        
        response_day = requests.get(url, params=params_day, timeout=10)
        if response_day.status_code != 200:
            print(f"  ⚠️  {symbol}: 无法获取开盘价，使用当前价")
            return {"price": close_price, "open_utc8": close_price}
        
        data_day = response_day.json()
        if data_day.get("code") != "0" or not data_day.get("data"):
            print(f"  ⚠️  {symbol}: 无法获取开盘价，使用当前价")
            return {"price": close_price, "open_utc8": close_price}
        
        day_kline = data_day["data"][0]
        open_utc8 = float(day_kline[1])  # UTC+8开盘价
        
        return {
            "price": close_price,
            "open_utc8": open_utc8
        }
        
    except Exception as e:
        print(f"  ❌ {symbol}: {str(e)}")
        return None

def collect_at_time(target_time):
    """
    采集指定时间点的数据
    
    Args:
        target_time: datetime对象
    """
    print(f"\n{'='*80}")
    print(f"⏰ 采集时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    day_changes = {}
    success_count = 0
    failed_symbols = []
    
    for symbol in SYMBOLS:
        data = fetch_okx_kline_at_time(symbol, target_time)
        
        if data and data["open_utc8"] > 0:
            # 计算涨跌幅
            day_change = ((data["price"] - data["open_utc8"]) / data["open_utc8"]) * 100
            day_changes[f"{symbol}-USDT-SWAP"] = day_change
            success_count += 1
            print(f"  ✅ {symbol}: {day_change:+.4f}%")
        else:
            day_changes[f"{symbol}-USDT-SWAP"] = 0
            failed_symbols.append(f"{symbol}-USDT-SWAP")
            print(f"  ❌ {symbol}: 获取失败")
        
        # 避免请求过快
        time.sleep(0.05)
    
    # 计算总涨跌和平均涨跌
    total_change = sum(day_changes.values())
    average_change = total_change / len(day_changes) if day_changes else 0
    
    # 构建记录
    record = {
        "record_time": target_time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_change": round(total_change, 4),
        "average_change": round(average_change, 4),
        "day_changes": day_changes,
        "total_symbols": len(SYMBOLS),
        "success_count": success_count,
        "failed_symbols": failed_symbols
    }
    
    # 保存记录
    manager.add_day_change_record(record)
    
    print(f"\n📊 统计:")
    print(f"  总涨跌: {total_change:+.4f}%")
    print(f"  平均涨跌: {average_change:+.4f}%")
    print(f"  成功: {success_count}/{len(SYMBOLS)}")
    if failed_symbols:
        print(f"  失败: {', '.join(failed_symbols)}")
    
    return record

def main():
    """主函数"""
    # 设置时区
    tz = pytz.timezone('Asia/Shanghai')
    
    # 起始时间：2026-01-03 00:00:00
    start_time = tz.localize(datetime(2026, 1, 3, 0, 0, 0))
    
    # 结束时间：当前时间
    end_time = datetime.now(tz)
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║           OKX 27币种涨跌历史数据回填脚本                         ║
╚═══════════════════════════════════════════════════════════════════╝

⏰ 回填时间范围:
   起始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
   结束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}

📊 币种数量: {len(SYMBOLS)}
⏱️  采集间隔: 1分钟
📈 预计数据点: {int((end_time - start_time).total_seconds() / 60)}

{'='*70}
""")
    
    # 确认是否继续
    response = input("是否开始回填数据？(y/n): ")
    if response.lower() != 'y':
        print("❌ 已取消")
        return
    
    # 逐分钟回填
    current_time = start_time
    total_points = 0
    success_points = 0
    
    start_ts = time.time()
    
    while current_time <= end_time:
        try:
            record = collect_at_time(current_time)
            total_points += 1
            
            if record["success_count"] > 0:
                success_points += 1
            
            # 每10个点显示进度
            if total_points % 10 == 0:
                elapsed = time.time() - start_ts
                progress = ((current_time - start_time).total_seconds() / 
                           (end_time - start_time).total_seconds()) * 100
                print(f"\n📈 进度: {progress:.1f}% | "
                      f"已采集: {total_points} | "
                      f"成功: {success_points} | "
                      f"耗时: {elapsed/60:.1f}分钟")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断，正在保存数据...")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
        
        # 下一分钟
        current_time += timedelta(minutes=1)
        
        # 避免请求过快
        time.sleep(0.5)
    
    elapsed = time.time() - start_ts
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                        回填完成                                   ║
╚═══════════════════════════════════════════════════════════════════╝

📊 统计:
   总数据点: {total_points}
   成功: {success_points}
   失败: {total_points - success_points}
   
⏱️  耗时: {elapsed/60:.1f}分钟
📁 数据文件: {manager.day_change_jsonl_path}
""")

if __name__ == "__main__":
    main()
