#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据收集器 - 从API获取数据并保存为JSONL格式
为重大事件监控系统提供数据支持
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/unified-collector-out.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('UnifiedDataCollector')

class UnifiedDataCollector:
    """统一数据收集器"""
    
    def __init__(self):
        self.base_dir = Path('/home/user/webapp')
        self.data_dir = self.base_dir / 'major-events-system' / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # JSONL文件路径
        self.sar_slope_file = self.data_dir / 'sar_slope_data.jsonl'
        self.liquidation_file = self.data_dir / 'liquidation_data.jsonl'
        self.coin_prices_file = self.data_dir / 'coin_prices.jsonl'
        
        # API端点
        self.api_base = 'http://localhost:5000'
        
        # 27个交易对
        self.coins = [
            'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'DOGE', 'SUI', 'TRX', 'LINK',
            'DOT', 'UNI', 'LTC', 'BCH', 'NEAR', 'AAVE', 'APT', 'FIL', 'TON',
            'XLM', 'HBAR', 'STX', 'LDO', 'CRV', 'CRO', 'CFX', 'TAO', 'AVAX'
        ]
        
        logger.info("统一数据收集器初始化完成")
    
    def collect_sar_slope_data(self):
        """收集SAR斜率数据（2h见顶信号）"""
        try:
            # 从API获取SAR斜率数据
            response = requests.get(
                f"{self.api_base}/api/sar-slope/latest",
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"SAR API返回错误状态: {response.status_code}")
                return None
            
            api_data = response.json()
            
            if not api_data.get('success'):
                logger.warning(f"SAR API失败: {api_data.get('message')}")
                return None
            
            # 统计2h级别见顶信号的币种数量
            # 见顶信号判断条件：
            # 1. sar_position = 'bullish' (多头位置)
            # 2. slope_direction = 'down' (斜率向下)
            # 3. sar_quadrant in ('Q1', 'Q2') (在Q1或Q2象限)
            top_signal_count = 0
            detected_symbols = []
            
            for coin_data in api_data.get('data', []):
                # 检查是否满足见顶信号条件
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
            
            data = {
                'timestamp': int(time.time()),
                'timeframe': '2h',
                'signal_type': 'top_signal',
                'count': top_signal_count,
                'symbols': detected_symbols,
                'time_range': '1h',
                'collected_at': datetime.now().isoformat()
            }
            
            # 保存到JSONL
            with open(self.sar_slope_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            
            if top_signal_count > 0:
                logger.info(f"✅ 2h见顶信号数据收集完成: {top_signal_count}个 ({', '.join(detected_symbols)})")
            else:
                logger.info(f"✅ 2h见顶信号数据收集完成: {top_signal_count}个")
            return data
            
        except Exception as e:
            logger.error(f"收集SAR斜率数据失败: {e}")
            return None
    
    def collect_liquidation_data(self):
        """收集爆仓数据"""
        try:
            # 从API获取爆仓数据 - 尝试多个可能的端点
            endpoints = [
                '/api/liquidation/latest',
                '/api/liquidation/1h',
                '/api/liquidation-data'
            ]
            
            api_data = None
            for endpoint in endpoints:
                try:
                    response = requests.get(
                        f"{self.api_base}{endpoint}",
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        api_data = response.json()
                        if api_data:
                            break
                except:
                    continue
            
            if not api_data:
                # 如果API不可用，使用模拟数据
                logger.warning("爆仓API不可用，使用模拟数据")
                liquidation_amount = 0
            else:
                # 从API数据中提取爆仓金额
                if isinstance(api_data, dict):
                    liquidation_amount = api_data.get('liquidation_amount', 0)
                    if isinstance(liquidation_amount, str):
                        liquidation_amount = float(liquidation_amount.replace(',', ''))
                else:
                    liquidation_amount = 0
            
            data = {
                'timestamp': int(time.time()),
                'time_range': '1h',
                'liquidation_amount': float(liquidation_amount),
                'unit': 'USD',
                'collected_at': datetime.now().isoformat()
            }
            
            # 保存到JSONL
            with open(self.liquidation_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ 1h爆仓金额数据收集完成: ${liquidation_amount:,.0f}")
            return data
            
        except Exception as e:
            logger.error(f"收集爆仓数据失败: {e}")
            return None
    
    def collect_coin_prices(self):
        """收集27个币种的价格涨跌幅"""
        try:
            # 从API获取价格数据
            response = requests.get(
                f"{self.api_base}/api/price-speed/latest",
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"价格API返回错误状态: {response.status_code}")
                return None
            
            api_data = response.json()
            
            if not api_data.get('success'):
                logger.warning(f"价格API失败: {api_data.get('message')}")
                return None
            
            price_changes = []
            total_change = 0
            
            # 提取27个币种的涨跌幅
            for coin in self.coins:
                symbol = f"{coin}-USDT-SWAP"
                # 查找对应币种的数据
                coin_data = None
                for item in api_data.get('data', []):
                    if item.get('inst_id') == symbol or item.get('symbol') == symbol:
                        coin_data = item
                        break
                
                if coin_data:
                    change = coin_data.get('day_change', 0)
                    if isinstance(change, str):
                        change = float(change.replace('%', ''))
                else:
                    change = 0
                
                price_changes.append({
                    'symbol': symbol,
                    'change_percent': float(change)
                })
                total_change += float(change)
            
            data = {
                'timestamp': int(time.time()),
                'coins': price_changes,
                'total_change': total_change,
                'coins_count': len(self.coins),
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
        logger.info(f"统一数据收集服务启动，采集间隔: {interval}秒")
        
        while True:
            try:
                self.collect_all()
                logger.info(f"等待 {interval} 秒后进行下一次采集...")
                time.sleep(interval)
            except Exception as e:
                logger.error(f"数据收集出错: {e}")
                time.sleep(60)  # 出错后等待1分钟重试

if __name__ == '__main__':
    collector = UnifiedDataCollector()
    
    # 如果有命令行参数，执行一次采集后退出
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        collector.collect_all()
    else:
        collector.run(interval=300)  # 每5分钟采集一次
