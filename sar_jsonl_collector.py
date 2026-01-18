#!/usr/bin/env python3
"""
SAR JSONL采集器
功能：
1. 从OKX获取5分钟K线数据
2. 计算SAR指标
3. 写入JSONL文件
4. 每5分钟更新一次
"""

import time
import logging
import sys
import os
from datetime import datetime, timedelta
import pytz
import requests

# 添加当前目录到Python路径
sys.path.insert(0, '/home/user/webapp')

from sar_jsonl_manager import SARJSONLManager

# 配置日志
LOG_DIR = '/home/user/webapp/logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/sar_jsonl_collector.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 监控的币种列表（27个）
SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL',
    'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
    'ETC', 'BCH', 'HBAR', 'XLM', 'FIL',
    'LINK', 'CRO', 'DOT', 'AAVE', 'UNI',
    'NEAR', 'APT', 'CFX', 'CRV', 'STX',
    'LDO', 'TAO'
]

# OKX API配置
OKX_BASE_URL = 'https://www.okx.com'

# 采集间隔（秒）
COLLECTION_INTERVAL = 5 * 60  # 5分钟


def calculate_sar(klines, af_start=0.02, af_increment=0.02, af_max=0.2):
    """
    计算SAR指标
    
    Args:
        klines: K线数据列表，每个元素为[timestamp, open, high, low, close, volume]
        af_start: 加速因子起始值
        af_increment: 加速因子增量
        af_max: 加速因子最大值
    
    Returns:
        带有SAR值的K线数据列表
    """
    if len(klines) < 2:
        return []
    
    result = []
    
    # 初始化
    position = 'long'  # 假设初始为多头
    sar = float(klines[0][3])  # 使用第一根K线的最低价
    ep = float(klines[0][2])   # 极值点（最高价）
    af = af_start
    
    for i, kline in enumerate(klines):
        timestamp = int(kline[0])
        open_price = float(kline[1])
        high = float(kline[2])
        low = float(kline[3])
        close = float(kline[4])
        
        # 计算SAR
        if i > 0:
            sar = sar + af * (ep - sar)
        
        # 判断是否转向
        if position == 'long':
            if low < sar:
                # 多转空
                position = 'short'
                sar = ep  # SAR设为之前的极值点
                ep = low  # 极值点设为当前最低价
                af = af_start
            else:
                # 更新极值点
                if high > ep:
                    ep = high
                    af = min(af + af_increment, af_max)
        else:  # position == 'short'
            if high > sar:
                # 空转多
                position = 'long'
                sar = ep  # SAR设为之前的极值点
                ep = high  # 极值点设为当前最高价
                af = af_start
            else:
                # 更新极值点
                if low < ep:
                    ep = low
                    af = min(af + af_increment, af_max)
        
        # 确保SAR不在当前K线范围内
        if position == 'long':
            sar = min(sar, low, float(klines[max(0, i-1)][3]) if i > 0 else low)
        else:
            sar = max(sar, high, float(klines[max(0, i-1)][2]) if i > 0 else high)
        
        result.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'sar': sar,
            'position': position
        })
    
    return result


def get_okx_klines(symbol, bar='5m', limit=300):
    """
    从OKX获取K线数据
    
    Args:
        symbol: 币种符号，如'BTC'
        bar: K线周期，默认'5m'
        limit: 获取的K线数量
    
    Returns:
        K线数据列表
    """
    try:
        inst_id = f"{symbol}USDT-SWAP"
        url = f"{OKX_BASE_URL}/api/v5/market/candles"
        
        params = {
            'instId': inst_id,
            'bar': bar,
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data['code'] == '0' and data['data']:
            # OKX返回的数据是从新到旧，需要反转
            klines = data['data']
            klines.reverse()  # 反转为从旧到新
            return klines
        else:
            logger.error(f"OKX API返回错误: {data}")
            return None
    
    except Exception as e:
        logger.error(f"获取{symbol} K线数据失败: {e}")
        return None


def collect_symbol_data(symbol):
    """
    采集单个币种的数据
    
    Args:
        symbol: 币种符号
    
    Returns:
        成功返回True，失败返回False
    """
    try:
        logger.info(f"[{symbol}] 开始采集...")
        
        # 获取K线数据
        klines = get_okx_klines(symbol, bar='5m', limit=300)
        
        if not klines:
            logger.error(f"[{symbol}] 获取K线数据失败")
            return False
        
        logger.info(f"[{symbol}] 获取到 {len(klines)} 根K线")
        
        # 计算SAR
        sar_data = calculate_sar(klines)
        
        if not sar_data:
            logger.error(f"[{symbol}] 计算SAR失败")
            return False
        
        logger.info(f"[{symbol}] 计算SAR完成，共 {len(sar_data)} 条")
        
        # 获取JSONL管理器
        manager = SARJSONLManager(symbol)
        
        # 获取最后一条记录的时间戳，避免重复写入
        latest_record = manager.get_latest_record()
        last_timestamp = latest_record['timestamp'] if latest_record else 0
        
        # 写入新数据
        new_records = 0
        for data in sar_data:
            if data['timestamp'] > last_timestamp:
                # 转换时间戳为北京时间
                beijing_time = datetime.fromtimestamp(
                    data['timestamp'] / 1000,
                    tz=BEIJING_TZ
                ).strftime('%Y-%m-%d %H:%M:%S')
                
                # 计算序列号和持续时间
                # 简化版本：暂时使用固定值，后续可优化
                sequence = 1
                duration_minutes = 0
                
                if latest_record and latest_record.get('position') == data['position']:
                    sequence = latest_record.get('sequence', 0) + 1
                    duration_minutes = (data['timestamp'] - latest_record['timestamp']) // (1000 * 60)
                
                record = {
                    'symbol': symbol,
                    'timestamp': data['timestamp'],
                    'beijing_time': beijing_time,
                    'open': data['open'],
                    'high': data['high'],
                    'low': data['low'],
                    'close': data['close'],
                    'sar': data['sar'],
                    'position': data['position'],
                    'sequence': sequence,
                    'duration_minutes': duration_minutes
                }
                
                if manager.append_record(record):
                    new_records += 1
                    latest_record = record  # 更新latest_record用于下一次计算
        
        logger.info(f"[{symbol}] ✅ 成功写入 {new_records} 条新记录")
        
        return True
    
    except Exception as e:
        logger.error(f"[{symbol}] ❌ 采集失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def collect_all_symbols():
    """采集所有币种的数据"""
    logger.info("=" * 80)
    logger.info("🚀 开始采集所有币种SAR数据")
    logger.info(f"📅 时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📊 币种数量: {len(SYMBOLS)}")
    logger.info("=" * 80)
    
    success_count = 0
    fail_count = 0
    
    for i, symbol in enumerate(SYMBOLS, 1):
        logger.info(f"[{i}/{len(SYMBOLS)}] 处理 {symbol}...")
        
        if collect_symbol_data(symbol):
            success_count += 1
        else:
            fail_count += 1
        
        # 避免请求过快
        if i < len(SYMBOLS):
            time.sleep(1)
    
    logger.info("=" * 80)
    logger.info(f"✅ 采集完成: 成功 {success_count}, 失败 {fail_count}")
    logger.info("=" * 80)


def main():
    """主函数 - 守护进程模式"""
    logger.info("=" * 80)
    logger.info("SAR JSONL采集器 - 守护进程模式")
    logger.info(f"⏱️  采集间隔: {COLLECTION_INTERVAL // 60} 分钟")
    logger.info(f"📊 监控币种: {len(SYMBOLS)} 个")
    logger.info(f"💾 数据目录: /home/user/webapp/data/sar_jsonl/")
    logger.info("=" * 80)
    
    while True:
        try:
            collect_all_symbols()
            
            next_run = datetime.now(BEIJING_TZ) + timedelta(seconds=COLLECTION_INTERVAL)
            logger.info(f"⏰ 下次采集时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"💤 等待 {COLLECTION_INTERVAL // 60} 分钟...")
            
            time.sleep(COLLECTION_INTERVAL)
        
        except KeyboardInterrupt:
            logger.info("⚠️  收到中断信号，正在退出...")
            break
        
        except Exception as e:
            logger.error(f"❌ 主循环异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info("⏰ 等待60秒后重试...")
            time.sleep(60)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # 测试模式：只采集一次
        logger.info("🧪 测试模式：采集一次")
        collect_all_symbols()
    else:
        # 守护进程模式：持续采集
        main()
