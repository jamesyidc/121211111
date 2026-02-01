#!/usr/bin/env python3
"""
27币种价格追踪器 - 历史数据回填
从1月3日到1月16日，每30分钟一个节点
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
import pytz
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, '/home/user/webapp/source_code')

# OKX API配置
OKX_API_BASE = "https://www.okx.com/api/v5"

# 27个币种列表
SYMBOLS = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "LTC", "DOGE", "SUI", "TRX", "TON",
    "ETC", "BCH", "HBAR", "XLM", "FIL", "LINK", "CRO", "DOT", "UNI", "NEAR",
    "APT", "CFX", "CRV", "STX", "LDO", "TAO", "AAVE"
]

# 数据存储路径
DATA_DIR = '/home/user/webapp/data/coin_price_tracker'
JSONL_FILE = os.path.join(DATA_DIR, 'coin_prices_30min.jsonl')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 时区
TZ = pytz.timezone('Asia/Shanghai')

def get_price_at_time(symbol, target_time):
    """获取指定时间点的价格（使用30分钟K线）"""
    try:
        inst_id = f"{symbol}-USDT-SWAP"
        target_ts = int(target_time.timestamp() * 1000)
        
        # 使用30分钟K线，获取历史数据
        url = f"{OKX_API_BASE}/market/candles"
        params = {
            "instId": inst_id,
            "bar": "30m",  # 30分钟K线
            "before": str(target_ts + 1800000),  # 目标时间后30分钟
            "limit": 3  # 获取3根K线
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            logger.debug(f"{symbol} HTTP错误: {response.status_code}")
            return None
        
        data = response.json()
        if data.get("code") != "0":
            logger.debug(f"{symbol} API错误: {data.get('msg')}")
            return None
        
        if not data.get("data"):
            logger.debug(f"{symbol} 无数据")
            return None
        
        # K线数据: [ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]
        klines = data["data"]
        
        # 找到最接近target_ts的K线
        best_kline = None
        min_diff = float('inf')
        
        for kline in klines:
            kline_ts = int(kline[0])
            diff = abs(kline_ts - target_ts)
            
            if diff < min_diff:
                min_diff = diff
                best_kline = kline
        
        if best_kline:
            # 使用收盘价
            price = float(best_kline[4])
            return price
        
        return None
        
    except Exception as e:
        logger.error(f"获取 {symbol} 在 {target_time} 的价格失败: {e}")
        return None

def backfill_historical_data():
    """回填历史数据：从2026-01-03到2026-01-16"""
    
    logger.info("""
╔═══════════════════════════════════════════════════════════════════╗
║        27币种价格追踪器 - 历史数据回填（30分钟粒度）              ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    # 回填时间范围：2026-01-03 00:00 到 2026-01-16 23:30
    start_date = TZ.localize(datetime(2026, 1, 3, 0, 0, 0))
    end_date = TZ.localize(datetime(2026, 1, 16, 23, 30, 0))
    
    # 计算总数据点数
    total_points = int((end_date - start_date).total_seconds() / 1800) + 1  # 30分钟 = 1800秒
    
    logger.info(f"📅 回填时间范围: {start_date} 到 {end_date}")
    logger.info(f"📊 币种数量: {len(SYMBOLS)}")
    logger.info(f"⏰ 采集间隔: 30分钟")
    logger.info(f"📈 预计数据点: {total_points}")
    logger.info("")
    
    # 读取已有数据，避免重复
    existing_times = set()
    if os.path.exists(JSONL_FILE):
        with open(JSONL_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    existing_times.add(record.get('collect_time'))
    
    logger.info(f"📝 已有数据点: {len(existing_times)}")
    logger.info("")
    
    # 逐日回填
    current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    completed = 0
    skipped = 0
    
    while current_date <= end_date.replace(hour=23, minute=59):
        # 获取这一天的基准价格（00:00）
        logger.info(f"🔄 处理日期: {current_date.strftime('%Y-%m-%d')}")
        
        base_prices = {}
        logger.info(f"  📊 获取基准价格（00:00）...")
        
        for symbol in SYMBOLS:
            price = get_price_at_time(symbol, current_date)
            if price:
                base_prices[symbol] = price
                logger.info(f"    ✅ {symbol}: ${price:.8f}")
            else:
                logger.warning(f"    ❌ {symbol}: 获取失败")
            time.sleep(0.05)  # 避免请求过快
        
        if len(base_prices) < len(SYMBOLS):
            logger.warning(f"  ⚠️  基准价格不完整: {len(base_prices)}/{len(SYMBOLS)}")
        
        # 生成这一天的所有30分钟节点
        time_points = []
        t = current_date
        while t.date() == current_date.date():
            time_points.append(t)
            t += timedelta(minutes=30)
        
        logger.info(f"  📈 生成 {len(time_points)} 个时间节点...")
        
        # 逐个时间点采集数据
        for idx, point_time in enumerate(time_points):
            collect_time_str = point_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 检查是否已存在
            if collect_time_str in existing_times:
                skipped += 1
                continue
            
            # 获取当前时间点的价格
            current_prices = {}
            for symbol in SYMBOLS:
                price = get_price_at_time(symbol, point_time)
                if price:
                    current_prices[symbol] = price
                time.sleep(0.05)
            
            # 计算涨跌幅
            changes = {}
            for symbol in SYMBOLS:
                if symbol in base_prices and symbol in current_prices:
                    base_price = base_prices[symbol]
                    current_price = current_prices[symbol]
                    
                    if base_price > 0:
                        change_pct = ((current_price - base_price) / base_price) * 100
                        changes[symbol] = {
                            "base_price": base_price,
                            "current_price": current_price,
                            "change_pct": round(change_pct, 4)
                        }
                    else:
                        changes[symbol] = {
                            "base_price": 0,
                            "current_price": current_price,
                            "change_pct": 0
                        }
                else:
                    changes[symbol] = {
                        "base_price": base_prices.get(symbol, 0),
                        "current_price": 0,
                        "change_pct": 0
                    }
            
            # 统计
            valid_count = sum(1 for v in changes.values() if v['current_price'] > 0)
            
            # 构建记录
            record = {
                "collect_time": collect_time_str,
                "timestamp": int(point_time.timestamp()),
                "base_date": current_date.strftime("%Y-%m-%d"),
                "coins": changes,
                "total_coins": len(SYMBOLS),
                "valid_coins": valid_count
            }
            
            # 保存
            with open(JSONL_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            completed += 1
            
            # 进度输出（每10个点输出一次）
            if (idx + 1) % 10 == 0:
                progress = ((completed + skipped) / total_points) * 100
                logger.info(f"    进度: {progress:.1f}% | 已完成: {completed} | 跳过: {skipped} | 时间: {collect_time_str}")
        
        logger.info(f"  ✅ {current_date.strftime('%Y-%m-%d')} 完成！")
        logger.info("")
        
        # 移到下一天
        current_date += timedelta(days=1)
    
    logger.info("╔═══════════════════════════════════════════════════════════════════╗")
    logger.info(f"║  ✅ 历史数据回填完成！")
    logger.info(f"║  📊 总数据点: {total_points}")
    logger.info(f"║  ✅ 新增点数: {completed}")
    logger.info(f"║  ⏭️  跳过点数: {skipped}")
    logger.info(f"║  📁 数据文件: {JSONL_FILE}")
    logger.info("╚═══════════════════════════════════════════════════════════════════╝")

if __name__ == "__main__":
    backfill_historical_data()
