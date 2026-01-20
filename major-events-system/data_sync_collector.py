#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重大事件数据同步器
从其他采集器的JSONL读取数据，同步到major-events-system/data目录
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/data-sync-collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DataSyncCollector')

class DataSyncCollector:
    """数据同步收集器"""
    
    def __init__(self):
        self.base_dir = Path('/home/user/webapp')
        self.data_dir = self.base_dir / 'major-events-system' / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 源数据路径
        self.panic_jsonl = self.base_dir / 'data' / 'panic_jsonl' / 'panic_wash_index.jsonl'
        self.coin_price_jsonl = self.base_dir / 'data' / 'coin_price_tracker' / 'coin_prices_30min.jsonl'
        self.sar_slope_api = 'http://localhost:5000/api/sar-slope/latest'
        
        # 输出文件路径
        self.liquidation_file = self.data_dir / 'liquidation_data.jsonl'
        self.coin_prices_file = self.data_dir / 'coin_prices.jsonl'
        self.sar_slope_file = self.data_dir / 'sar_slope_data.jsonl'
        
        logger.info("数据同步收集器初始化完成")
    
    def sync_liquidation_data(self):
        """同步爆仓数据"""
        try:
            if not self.panic_jsonl.exists():
                logger.warning(f"Panic数据文件不存在: {self.panic_jsonl}")
                return False
            
            # 读取最后一行
            with open(self.panic_jsonl, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if not lines:
                    logger.warning("Panic数据文件为空")
                    return False
                
                panic_data = json.loads(lines[-1])
                # hour_1_amount 单位是万美元，转换为美元
                liquidation_amount = panic_data.get('hour_1_amount', 0) * 10000
            
            # 写入输出文件
            output = {
                'timestamp': int(time.time()),
                'time_range': '1h',
                'liquidation_amount': float(liquidation_amount),
                'unit': 'USD',
                'collected_at': panic_data.get('record_time', datetime.now().isoformat())
            }
            
            with open(self.liquidation_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(output, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ 爆仓数据同步完成: ${liquidation_amount:,.0f}")
            return True
            
        except Exception as e:
            logger.error(f"同步爆仓数据失败: {e}")
            return False
    
    def sync_coin_prices(self):
        """同步币种价格数据"""
        try:
            if not self.coin_price_jsonl.exists():
                logger.warning(f"币价数据文件不存在: {self.coin_price_jsonl}")
                return False
            
            # 读取最后一行
            with open(self.coin_price_jsonl, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if not lines:
                    logger.warning("币价数据文件为空")
                    return False
                
                coin_data = json.loads(lines[-1])
                total_change = coin_data.get('total_change', 0)
            
            # 写入输出文件
            output = {
                'timestamp': coin_data.get('timestamp', int(time.time())),
                'coins': [],  # 简化版本，不包含每个币种的详细数据
                'total_change': float(total_change),
                'coins_count': coin_data.get('success_count', 27),
                'collected_at': coin_data.get('collect_time', datetime.now().isoformat())
            }
            
            with open(self.coin_prices_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(output, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ 币价数据同步完成: 总涨跌幅 {total_change:.2f}%")
            return True
            
        except Exception as e:
            logger.error(f"同步币价数据失败: {e}")
            return False
    
    def sync_sar_slope_data(self):
        """同步SAR斜率数据（从API读取）"""
        try:
            import requests
            
            response = requests.get(self.sar_slope_api, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"SAR API返回错误: {response.status_code}")
                return False
            
            api_data = response.json()
            
            if not api_data.get('success'):
                logger.warning(f"SAR API失败: {api_data.get('message')}")
                return False
            
            # 统计见顶信号
            top_signal_count = 0
            detected_symbols = []
            
            for coin_data in api_data.get('data', []):
                sar_position = coin_data.get('sar_position', '')
                slope_direction = coin_data.get('slope_direction', '')
                sar_quadrant = coin_data.get('sar_quadrant', '')
                symbol = coin_data.get('symbol', '')
                
                # 见顶条件：多头 + 斜率向下 + Q1或Q2象限
                if (sar_position == 'bullish' and 
                    slope_direction == 'down' and 
                    sar_quadrant in ('Q1', 'Q2')):
                    top_signal_count += 1
                    detected_symbols.append(symbol)
            
            # 写入输出文件
            output = {
                'timestamp': int(time.time()),
                'timeframe': '2h',
                'signal_type': 'top_signal',
                'count': top_signal_count,
                'symbols': detected_symbols,
                'time_range': '1h',
                'collected_at': datetime.now().isoformat()
            }
            
            with open(self.sar_slope_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(output, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ SAR数据同步完成: {top_signal_count}个见顶信号")
            return True
            
        except Exception as e:
            logger.error(f"同步SAR数据失败: {e}")
            return False
    
    def sync_all(self):
        """同步所有数据"""
        logger.info("=" * 60)
        logger.info("开始数据同步")
        
        results = {
            'liquidation': self.sync_liquidation_data(),
            'coin_prices': self.sync_coin_prices(),
            'sar_slope': self.sync_sar_slope_data()
        }
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"数据同步完成: {success_count}/3 成功")
        
        return results
    
    def run(self, interval=300):
        """运行同步服务（默认5分钟间隔）"""
        logger.info(f"数据同步服务启动，同步间隔: {interval}秒")
        
        while True:
            try:
                self.sync_all()
                logger.info(f"等待 {interval} 秒后进行下一次同步...")
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("收到停止信号，退出...")
                break
            except Exception as e:
                logger.error(f"同步出错: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(60)  # 出错后等待1分钟

def main():
    """主函数"""
    import sys
    
    collector = DataSyncCollector()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 单次运行
        collector.sync_all()
    else:
        # 持续运行
        interval = int(sys.argv[1]) if len(sys.argv) > 1 else 300
        collector.run(interval=interval)

if __name__ == '__main__':
    main()
