#!/usr/bin/env python3
"""
OKX 27币种涨跌历史数据回填脚本（小时粒度）
从2026-01-03开始，每小时回填一个数据点
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
    """获取指定时间的K线数据"""
    try:
        inst_id = f"{symbol}-USDT-SWAP"
        target_ts = int(target_time.timestamp() * 1000)
        
        # 获取1小时K线
        url = f"{OKX_API_BASE}/market/candles"
        params = {
            "instId": inst_id,
            "bar": "1H",
            "before": str(target_ts + 3600000),
            "limit": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        
        data = response.json()
        if data.get("code") != "0" or not data.get("data"):
            return None
        
        kline = data["data"][0]
        close_price = float(kline[4])
        
        # 获取当天UTC+8开盘价
        target_date = target_time.astimezone(pytz.timezone('Asia/Shanghai')).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_start_ts = int(target_date.timestamp() * 1000)
        
        params_day = {
            "instId": inst_id,
            "bar": "1D",
            "before": str(day_start_ts + 86400000),
            "limit": 1
        }
        
        response_day = requests.get(url, params=params_day, timeout=10)
        if response_day.status_code == 200:
            data_day = response_day.json()
            if data_day.get("code") == "0" and data_day.get("data"):
                day_kline = data_day["data"][0]
                open_utc8 = float(day_kline[1])
                return {"price": close_price, "open_utc8": open_utc8}
        
        return {"price": close_price, "open_utc8": close_price}
        
    except Exception as e:
        return None

def collect_at_time(target_time):
    """采集指定时间点的数据"""
    day_changes = {}
    success_count = 0
    failed_symbols = []
    
    for symbol in SYMBOLS:
        data = fetch_okx_kline_at_time(symbol, target_time)
        
        if data and data["open_utc8"] > 0:
            day_change = ((data["price"] - data["open_utc8"]) / data["open_utc8"]) * 100
            day_changes[f"{symbol}-USDT-SWAP"] = day_change
            success_count += 1
        else:
            day_changes[f"{symbol}-USDT-SWAP"] = 0
            failed_symbols.append(f"{symbol}-USDT-SWAP")
        
        time.sleep(0.05)
    
    total_change = sum(day_changes.values())
    average_change = total_change / len(day_changes) if day_changes else 0
    
    # 保存记录
    manager.save_day_change(
        total_change=total_change,
        average_change=average_change,
        day_changes=day_changes,
        success_count=success_count,
        failed_count=len(failed_symbols),
        record_time=target_time  # 使用历史时间
    )
    
    record = {
        "record_time": target_time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_change": round(total_change, 4),
        "average_change": round(average_change, 4),
        "day_changes": day_changes,
        "total_symbols": len(SYMBOLS),
        "success_count": success_count,
        "failed_symbols": failed_symbols
    }
    
    return record

def main():
    """主函数 - 按小时回填"""
    tz = pytz.timezone('Asia/Shanghai')
    
    # 起始时间：2026-01-03 00:00:00
    start_time = tz.localize(datetime(2026, 1, 3, 0, 0, 0))
    
    # 结束时间：昨天23:00（避免覆盖今天的实时数据）
    end_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
    end_time = end_time.replace(minute=0, second=0, microsecond=0)
    
    total_hours = int((end_time - start_time).total_seconds() / 3600)
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║        OKX 27币种涨跌历史数据回填（小时粒度）                    ║
╚═══════════════════════════════════════════════════════════════════╝

⏰ 回填时间范围:
   起始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
   结束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}

📊 币种数量: {len(SYMBOLS)}
⏱️  采集间隔: 1小时
📈 预计数据点: {total_hours}

{'='*70}
开始回填...
""")
    
    current_time = start_time
    total_points = 0
    success_points = 0
    
    start_ts = time.time()
    
    while current_time <= end_time:
        try:
            print(f"\n⏰ {current_time.strftime('%Y-%m-%d %H:%M')} ", end="", flush=True)
            
            record = collect_at_time(current_time)
            total_points += 1
            
            if record["success_count"] > 0:
                success_points += 1
                print(f"✅ 总涨跌:{record['total_change']:+.2f}% (成功{record['success_count']}/{len(SYMBOLS)})")
            else:
                print(f"❌ 失败")
            
            # 每10个点显示进度
            if total_points % 10 == 0:
                elapsed = time.time() - start_ts
                progress = ((current_time - start_time).total_seconds() / 
                           (end_time - start_time).total_seconds()) * 100
                eta = (elapsed / total_points) * (total_hours - total_points) if total_points > 0 else 0
                print(f"\n📈 进度: {progress:.1f}% | "
                      f"已采集: {total_points}/{total_hours} | "
                      f"成功: {success_points} | "
                      f"耗时: {elapsed/60:.1f}分 | "
                      f"预计剩余: {eta/60:.1f}分")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        current_time += timedelta(hours=1)
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
    
💡 提示: 数据已按小时粒度回填，实时采集器仍在按分钟采集最新数据
""")

if __name__ == "__main__":
    main()
