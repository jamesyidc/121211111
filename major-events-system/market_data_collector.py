#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据收集器 - 将数据库中的数据转换为JSONL格式
"""

import os
import sys
import json
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/market-collector-out.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MarketDataCollector')

class MarketDataCollector:
    """市场数据收集器"""
    
    def __init__(self):
        self.base_dir = Path('/home/user/webapp')
        self.data_dir = self.base_dir / 'major-events-system' / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # JSONL文件路径
        self.sar_slope_file = self.data_dir / 'sar_slope_data.jsonl'
        self.liquidation_file = self.data_dir / 'liquidation_data.jsonl'
        self.coin_prices_file = self.data_dir / 'coin_prices.jsonl'
        
        # 数据库路径
        self.sar_db = self.base_dir / 'databases' / 'sar_slope_data.db'
        self.signal_db = self.base_dir / 'databases' / 'signal_data.db'
        
        logger.info("市场数据收集器初始化完成")
    
    def collect_sar_slope_data(self):
        """收集SAR斜率数据（2h见顶信号）"""
        try:
            if not self.sar_db.exists():
                logger.warning(f"SAR数据库不存在: {self.sar_db}")
                return None
            
            conn = sqlite3.connect(str(self.sar_db))
            cursor = conn.cursor()
            
            # 获取最近1小时的数据
            one_hour_ago = int((datetime.now() - timedelta(hours=1)).timestamp())
            
            # 查询2h级别的见顶信号
            cursor.execute("""
                SELECT COUNT(*) 
                FROM sar_slope_data 
                WHERE timeframe = '2h' 
                AND signal_type = 'top_signal'
                AND timestamp >= ?
            """, (one_hour_ago,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            data = {
                'timestamp': int(time.time()),
                'timeframe': '2h',
                'signal_type': 'top_signal',
                'count': count,
                'time_range': '1h',
                'collected_at': datetime.now().isoformat()
            }
            
            # 保存到JSONL
            with open(self.sar_slope_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ 2h见顶信号数据收集完成: {count}个")
            return data
            
        except Exception as e:
            logger.error(f"收集SAR斜率数据失败: {e}")
            return None
    
    def collect_liquidation_data(self):
        """收集爆仓数据"""
        try:
            if not self.signal_db.exists():
                logger.warning(f"信号数据库不存在: {self.signal_db}")
                return None
            
            conn = sqlite3.connect(str(self.signal_db))
            cursor = conn.cursor()
            
            # 获取最近1小时的爆仓金额
            one_hour_ago = int((datetime.now() - timedelta(hours=1)).timestamp())
            
            cursor.execute("""
                SELECT SUM(liquidation_amount)
                FROM liquidation_data
                WHERE timestamp >= ?
            """, (one_hour_ago,))
            
            result = cursor.fetchone()
            amount = result[0] if result and result[0] else 0
            conn.close()
            
            data = {
                'timestamp': int(time.time()),
                'time_range': '1h',
                'liquidation_amount': float(amount),
                'unit': 'USD',
                'collected_at': datetime.now().isoformat()
            }
            
            # 保存到JSONL
            with open(self.liquidation_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ 1h爆仓金额数据收集完成: ${amount:,.0f}")
            return data
            
        except Exception as e:
            logger.error(f"收集爆仓数据失败: {e}")
            return None
    
    def collect_coin_prices(self):
        """收集27个币种的价格涨跌幅"""
        try:
            coins = [
                'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'DOGE', 'SUI', 'TRX', 'LINK',
                'DOT', 'UNI', 'LTC', 'BCH', 'NEAR', 'AAVE', 'APT', 'FIL', 'TON',
                'XLM', 'HBAR', 'STX', 'LDO', 'CRV', 'CRO', 'CFX', 'TAO', 'AVAX'
            ]
            
            # 这里应该从API获取实时价格，暂时使用数据库
            if not self.signal_db.exists():
                logger.warning(f"信号数据库不存在: {self.signal_db}")
                return None
            
            conn = sqlite3.connect(str(self.signal_db))
            cursor = conn.cursor()
            
            # 获取最近24小时的价格变化
            one_day_ago = int((datetime.now() - timedelta(hours=24)).timestamp())
            
            price_changes = []
            total_change = 0
            
            for coin in coins:
                cursor.execute("""
                    SELECT price_change_percent 
                    FROM coin_prices 
                    WHERE symbol = ? 
                    AND timestamp >= ?
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (f"{coin}-USDT", one_day_ago))
                
                result = cursor.fetchone()
                change = result[0] if result else 0
                price_changes.append({
                    'symbol': f"{coin}-USDT",
                    'change_percent': float(change)
                })
                total_change += float(change)
            
            conn.close()
            
            data = {
                'timestamp': int(time.time()),
                'coins': price_changes,
                'total_change': total_change,
                'coins_count': len(coins),
                'collected_at': datetime.now().isoformat()
            }
            
            # 保存到JSONL
            with open(self.coin_prices_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ 币种价格数据收集完成: 总涨跌幅 {total_change:.2f}%")
            return data
            
        except Exception as e:
            logger.error(f"收集币种价格数据失败: {e}")
            return None
    
    def collect_all(self):
        """收集所有数据"""
        logger.info("=" * 60)
        logger.info("开始数据收集")
        
        results = {
            'sar_slope': self.collect_sar_slope_data(),
            'liquidation': self.collect_liquidation_data(),
            'coin_prices': self.collect_coin_prices()
        }
        
        success_count = sum(1 for v in results.values() if v is not None)
        logger.info(f"数据收集完成: {success_count}/3 成功")
        
        return results
    
    def run(self, interval=300):
        """运行数据收集服务"""
        logger.info(f"市场数据收集服务启动，采集间隔: {interval}秒")
        
        while True:
            try:
                self.collect_all()
                logger.info(f"等待 {interval} 秒后进行下一次采集...")
                time.sleep(interval)
            except Exception as e:
                logger.error(f"数据收集出错: {e}")
                time.sleep(60)  # 出错后等待1分钟重试

if __name__ == '__main__':
    collector = MarketDataCollector()
    
    # 如果有命令行参数，执行一次采集后退出
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        collector.collect_all()
    else:
        collector.run(interval=300)  # 每5分钟采集一次
