#!/usr/bin/env python3
"""
SAR多空占比统计采集器
- 每3分钟统计一次所有币种的多空占比
- 记录偏多>80%和偏空>80%的币种数量
- 存储到JSONL文件
"""

import sys
import time
import requests
import logging
from datetime import datetime
import pytz

sys.path.insert(0, '/home/user/webapp')
from panic_jsonl_manager import PanicJSONLManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/sar_bias_collector.log'),
        logging.StreamHandler()
    ]
)

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 主流币种列表（可扩展）
MAIN_SYMBOLS = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'DOT',
    'MATIC', 'UNI', 'LTC', 'ATOM', 'ETC', 'XLM', 'NEAR', 'ALGO', 'FIL', 'APT'
]

class SARBiasCollector:
    """SAR多空占比统计采集器"""
    
    def __init__(self):
        self.manager = PanicJSONLManager()
        self.api_base = 'http://localhost:5000'
        logging.info("✅ SAR多空占比统计采集器已启动")
    
    def get_symbol_bias(self, symbol: str) -> dict:
        """获取单个币种的多空占比"""
        try:
            url = f'{self.api_base}/api/sar-slope/current-cycle/{symbol}'
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if data.get('success') and data.get('bias_statistics'):
                stats = data['bias_statistics']
                return {
                    'symbol': symbol,
                    'bullish_ratio': stats.get('bullish_ratio', 0),
                    'bearish_ratio': stats.get('bearish_ratio', 0),
                    'bullish_count': stats.get('recent_2hours', {}).get('bullish_count', 0),
                    'bearish_count': stats.get('recent_2hours', {}).get('bearish_count', 0)
                }
            else:
                logging.warning(f"⚠️ {symbol}: 无数据")
                return None
                
        except Exception as e:
            logging.error(f"❌ {symbol}: 获取失败 - {e}")
            return None
    
    def collect_all_symbols(self):
        """采集所有币种的多空占比"""
        bullish_over_80 = []
        bearish_over_80 = []
        all_stats = []
        
        logging.info(f"📡 开始采集 {len(MAIN_SYMBOLS)} 个币种的多空占比...")
        
        for symbol in MAIN_SYMBOLS:
            bias = self.get_symbol_bias(symbol)
            
            if bias:
                all_stats.append(bias)
                
                # 统计偏多>80%
                if bias['bullish_ratio'] > 80:
                    bullish_over_80.append(symbol)
                    logging.info(f"  📈 {symbol}: 偏多 {bias['bullish_ratio']:.2f}% ✅")
                
                # 统计偏空>80%
                if bias['bearish_ratio'] > 80:
                    bearish_over_80.append(symbol)
                    logging.info(f"  📉 {symbol}: 偏空 {bias['bearish_ratio']:.2f}% ✅")
            
            # 避免请求过快
            time.sleep(0.1)
        
        return {
            'bullish_over_80_count': len(bullish_over_80),
            'bearish_over_80_count': len(bearish_over_80),
            'bullish_over_80_symbols': bullish_over_80,
            'bearish_over_80_symbols': bearish_over_80,
            'all_stats': all_stats
        }
    
    def collect_once(self):
        """执行一次采集"""
        try:
            now = datetime.now(BEIJING_TZ)
            record_time = now.strftime('%Y-%m-%d %H:%M:%S')
            
            logging.info(f"\n{'='*60}")
            logging.info(f"🚀 开始采集SAR多空占比统计: {record_time}")
            logging.info(f"{'='*60}")
            
            # 采集数据
            result = self.collect_all_symbols()
            
            # 构建记录
            record = {
                'record_time': record_time,
                'bullish_over_80_count': result['bullish_over_80_count'],
                'bearish_over_80_count': result['bearish_over_80_count'],
                'bullish_over_80_symbols': ','.join(result['bullish_over_80_symbols']),
                'bearish_over_80_symbols': ','.join(result['bearish_over_80_symbols']),
                'total_symbols': len(MAIN_SYMBOLS),
                'stats_detail': result['all_stats']
            }
            
            # 保存到JSONL
            success = self.manager.append_record('sar_bias_stats', record)
            
            if success:
                logging.info(f"\n{'='*60}")
                logging.info(f"✅ 统计完成并保存到JSONL")
                logging.info(f"📊 偏多>80%币种数: {result['bullish_over_80_count']}")
                logging.info(f"   币种: {result['bullish_over_80_symbols']}")
                logging.info(f"📊 偏空>80%币种数: {result['bearish_over_80_count']}")
                logging.info(f"   币种: {result['bearish_over_80_symbols']}")
                logging.info(f"{'='*60}\n")
                return True
            else:
                logging.error("❌ 保存数据失败")
                return False
                
        except Exception as e:
            logging.error(f"❌ 采集过程出错: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return False
    
    def run(self, interval=180):
        """持续运行采集器"""
        logging.info(f"🔄 采集器已启动，采集间隔: {interval}秒 ({interval/60:.1f}分钟)")
        
        while True:
            try:
                self.collect_once()
                logging.info(f"😴 等待 {interval} 秒后进行下次采集...\n")
                time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("\n👋 采集器已停止")
                break
            except Exception as e:
                logging.error(f"❌ 运行出错: {e}")
                time.sleep(60)


if __name__ == '__main__':
    collector = SARBiasCollector()
    
    # 如果有命令行参数 'once'，只执行一次
    if len(sys.argv) > 1 and sys.argv[1] == 'once':
        collector.collect_once()
    else:
        collector.run(interval=180)  # 3分钟
