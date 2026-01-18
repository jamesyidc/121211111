#!/usr/bin/env python3
"""
补全1月17日16:30后的缺失数据
回填时间点：17:05、17:35、18:05
"""
import os
import sys
import time
import json
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

# 时区
TZ = pytz.timezone('Asia/Shanghai')

# OKX API配置
OKX_API_BASE = 'https://www.okx.com/api/v5'

# 27个币种
SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
    'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK', 'CRO', 'DOT', 'UNI',
    'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO', 'AAVE'
]

# 数据目录
DATA_DIR = '/home/user/webapp/data/coin_price_tracker'
JSONL_FILE = os.path.join(DATA_DIR, 'coin_prices_30min.jsonl')

def get_okx_price(symbol):
    """获取OKX永续合约价格"""
    try:
        url = f"{OKX_API_BASE}/market/ticker"
        params = {'instId': f'{symbol}-USDT-SWAP'}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0' and data.get('data'):
                last_price = float(data['data'][0]['last'])
                return last_price
        return None
    except Exception as e:
        logger.error(f"获取 {symbol} 价格失败: {e}")
        return None

def get_base_prices(target_date):
    """从历史数据中获取当天00:00的基准价格"""
    base_prices = {}
    
    # 读取JSONL文件，找到最接近00:00的记录
    try:
        with open(JSONL_FILE, 'r') as f:
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            for line in f:
                record = json.loads(line.strip())
                collect_time = record['collect_time']
                
                # 如果是目标日期且时间在00:00-01:00之间
                if collect_time.startswith(target_date_str):
                    base_date = record.get('base_date')
                    if base_date == target_date_str:
                        # 这是我们需要的基准价格
                        for symbol in SYMBOLS:
                            if symbol in record['coins']:
                                base_prices[symbol] = record['coins'][symbol].get('base_price')
                        
                        if len(base_prices) == 27:
                            logger.info(f"✅ 从历史数据获取到 {target_date_str} 的基准价格")
                            return base_prices
        
        logger.warning(f"未找到 {target_date_str} 的基准价格")
        return None
        
    except Exception as e:
        logger.error(f"读取基准价格失败: {e}")
        return None

def collect_at_time(collect_time, base_prices):
    """在指定时间点采集数据"""
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 开始回填数据: {collect_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*70}")
    
    # 获取当前价格
    coins_data = {}
    success_count = 0
    
    for symbol in SYMBOLS:
        current_price = get_okx_price(symbol)
        
        if current_price is not None and symbol in base_prices:
            base_price = base_prices[symbol]
            change_pct = ((current_price - base_price) / base_price) * 100
            
            coins_data[symbol] = {
                'base_price': base_price,
                'current_price': current_price,
                'change_pct': change_pct
            }
            success_count += 1
            logger.info(f"  ✅ {symbol}: ${current_price:.8f} ({change_pct:+.2f}%)")
        else:
            logger.warning(f"  ❌ {symbol}: 获取失败")
        
        time.sleep(0.1)  # 限速
    
    # 构建记录
    if success_count > 0:
        record = {
            'timestamp': int(collect_time.timestamp()),
            'collect_time': collect_time.strftime('%Y-%m-%d %H:%M:%S'),
            'base_date': collect_time.strftime('%Y-%m-%d'),
            'coins': coins_data
        }
        
        logger.info(f"✅ 回填完成: {success_count}/{len(SYMBOLS)} 个币种")
        return record
    
    return None

def insert_record_sorted(record):
    """将记录按时间顺序插入到JSONL文件中"""
    try:
        # 读取所有现有记录
        all_records = []
        with open(JSONL_FILE, 'r') as f:
            for line in f:
                all_records.append(json.loads(line.strip()))
        
        # 添加新记录
        all_records.append(record)
        
        # 按时间戳排序
        all_records.sort(key=lambda x: x['timestamp'])
        
        # 写回文件
        with open(JSONL_FILE, 'w') as f:
            for rec in all_records:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ 记录已插入文件: {record['collect_time']}")
        return True
        
    except Exception as e:
        logger.error(f"插入记录失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("="*70)
    logger.info("🔄 开始回填1月17日16:30后的缺失数据")
    logger.info("="*70)
    
    # 目标日期
    target_date = datetime(2026, 1, 17, tzinfo=TZ)
    
    # 获取基准价格
    base_prices = get_base_prices(target_date)
    if not base_prices:
        logger.error("❌ 无法获取基准价格，退出")
        return
    
    # 需要回填的时间点
    backfill_times = [
        datetime(2026, 1, 17, 17, 5, 0, tzinfo=TZ),   # 17:05
        datetime(2026, 1, 17, 17, 35, 0, tzinfo=TZ),  # 17:35
        datetime(2026, 1, 17, 18, 5, 0, tzinfo=TZ),   # 18:05
    ]
    
    success_count = 0
    
    for collect_time in backfill_times:
        record = collect_at_time(collect_time, base_prices)
        
        if record:
            if insert_record_sorted(record):
                success_count += 1
            time.sleep(2)  # 每次采集间隔2秒
    
    logger.info("\n" + "="*70)
    logger.info(f"🎉 回填完成! 成功: {success_count}/{len(backfill_times)}")
    logger.info("="*70)

if __name__ == '__main__':
    main()
