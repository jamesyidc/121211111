#!/usr/bin/env python3
"""
OKX 27币种当日涨跌采集器 - 1分钟级别
持续监控OKX交易页面上27种币的当日涨跌幅,并计算总和作为市场趋势指标
数据存储格式: JSONL
"""

import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime
import logging
from okx_trading_jsonl_manager import OKXTradingJSONLManager

# 添加项目根目录到路径
sys.path.insert(0, '/home/user/webapp/source_code')

# 日志配置
LOG_DIR = Path('/home/user/webapp/logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / 'okx_day_change_collector.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# OKX 27个交易对
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP', 'BNB-USDT-SWAP',
    'XRP-USDT-SWAP', 'DOGE-USDT-SWAP', 'ADA-USDT-SWAP', 'TRX-USDT-SWAP',
    'LINK-USDT-SWAP', 'AVAX-USDT-SWAP', 'DOT-USDT-SWAP', 'BCH-USDT-SWAP',
    'UNI-USDT-SWAP', 'LTC-USDT-SWAP', 'NEAR-USDT-SWAP', 'MATIC-USDT-SWAP',
    'ICP-USDT-SWAP', 'APT-USDT-SWAP', 'FIL-USDT-SWAP', 'ARB-USDT-SWAP',
    'OP-USDT-SWAP', 'ATOM-USDT-SWAP', 'STX-USDT-SWAP', 'AAVE-USDT-SWAP',
    'CRV-USDT-SWAP', 'ETC-USDT-SWAP', 'MKR-USDT-SWAP'
]

def get_day_change_sum():
    """
    获取27个币种的当日涨跌幅总和
    """
    try:
        # OKX API endpoint for ticker data
        api_url = 'https://www.okx.com/api/v5/market/tickers'
        params = {
            'instType': 'SWAP'
        }
        
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') != '0':
            logger.error(f"❌ OKX API返回错误: {data.get('msg')}")
            return None
        
        tickers = data.get('data', [])
        
        # 构建ticker字典，方便查找
        ticker_dict = {item['instId']: item for item in tickers}
        
        # 收集涨跌数据
        day_changes = {}
        total_change = 0
        success_count = 0
        failed_symbols = []
        
        for symbol in SYMBOLS:
            if symbol in ticker_dict:
                ticker = ticker_dict[symbol]
                try:
                    # 获取当前价格和UTC+8开盘价,计算涨跌幅
                    last_price = float(ticker.get('last', 0))
                    open_price_utc8 = float(ticker.get('sodUtc8', 0))
                    
                    if open_price_utc8 > 0:
                        # 计算涨跌幅 = (当前价 - 开盘价) / 开盘价 × 100
                        day_change_pct = ((last_price - open_price_utc8) / open_price_utc8) * 100
                        day_changes[symbol] = round(day_change_pct, 4)
                        total_change += day_change_pct
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ {symbol} 开盘价为0")
                        day_changes[symbol] = 0
                        failed_symbols.append(symbol)
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ {symbol} 涨跌幅计算失败: {e}")
                    day_changes[symbol] = 0
                    failed_symbols.append(symbol)
            else:
                logger.warning(f"⚠️ {symbol} 在API返回数据中未找到")
                day_changes[symbol] = 0
                failed_symbols.append(symbol)
        
        result = {
            'total_change': round(total_change, 4),
            'average_change': round(total_change / len(SYMBOLS), 4),
            'day_changes': day_changes,
            'success_count': success_count,
            'failed_count': len(failed_symbols),
            'failed_symbols': failed_symbols,
            'total_symbols': len(SYMBOLS)
        }
        
        logger.info(f"✅ 采集成功: 总涨跌 {result['total_change']:.2f}%, "
                   f"平均涨跌 {result['average_change']:.2f}%, "
                   f"成功 {success_count}/{len(SYMBOLS)}")
        
        if failed_symbols:
            logger.warning(f"⚠️ 失败币种: {', '.join(failed_symbols)}")
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"❌ 网络请求失败: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 采集失败: {e}", exc_info=True)
        return None

def run_collector(interval=60):
    """
    运行采集器
    :param interval: 采集间隔(秒), 默认60秒
    """
    manager = OKXTradingJSONLManager()
    
    logger.info(f"🚀 OKX涨跌采集器启动 (间隔: {interval}秒)")
    logger.info(f"📊 监控币种数量: {len(SYMBOLS)}")
    logger.info(f"💾 数据存储路径: {manager.data_dir}")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 开始第 {cycle_count} 次采集...")
            
            # 采集数据
            result = get_day_change_sum()
            
            if result:
                # 保存到JSONL
                saved = manager.save_day_change(
                    total_change=result['total_change'],
                    average_change=result['average_change'],
                    day_changes=result['day_changes'],
                    success_count=result['success_count'],
                    failed_count=result['failed_count']
                )
                
                if saved:
                    logger.info(f"💾 数据已保存到JSONL")
                else:
                    logger.error(f"❌ 数据保存失败")
            else:
                logger.error(f"❌ 本次采集失败")
            
            logger.info(f"⏰ 等待 {interval} 秒后进行下一次采集...")
            logger.info(f"{'='*60}\n")
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("⚠️ 收到中断信号,停止采集器")
            break
        except Exception as e:
            logger.error(f"❌ 采集器运行出错: {e}", exc_info=True)
            logger.info(f"⏰ 等待 {interval} 秒后重试...")
            time.sleep(interval)

if __name__ == '__main__':
    import sys
    
    # 如果命令行参数是 'once',只执行一次
    if len(sys.argv) > 1 and sys.argv[1] == 'once':
        logger.info("🔄 执行单次采集...")
        result = get_day_change_sum()
        if result:
            manager = OKXTradingJSONLManager()
            saved = manager.save_day_change(
                total_change=result['total_change'],
                average_change=result['average_change'],
                day_changes=result['day_changes'],
                success_count=result['success_count'],
                failed_count=result['failed_count']
            )
            if saved:
                logger.info("✅ 单次采集完成并保存")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                logger.error("❌ 数据保存失败")
        else:
            logger.error("❌ 采集失败")
    else:
        # 持续运行
        run_collector(interval=60)
