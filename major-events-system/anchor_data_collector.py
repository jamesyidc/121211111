#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚定系统数据收集器
定期从锚定系统获取盈利统计数据并保存为JSONL
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AnchorDataCollector')

class AnchorDataCollector:
    """锚定系统数据收集器"""
    
    def __init__(self, data_dir='/home/user/webapp/major-events-system/data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # JSONL文件路径
        self.profit_stats_file = self.data_dir / 'anchor_profit_stats.jsonl'
        
        # API配置
        self.api_base = 'http://localhost:5000'
        
        logger.info("锚定系统数据收集器初始化完成")
    
    def fetch_current_positions(self, trade_mode='real'):
        """
        获取当前持仓
        """
        try:
            url = f'{self.api_base}/api/anchor-system/current-positions'
            params = {'trade_mode': trade_mode}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('positions', [])
            
            return []
            
        except Exception as e:
            logger.error(f"获取当前持仓失败: {e}")
            return []
    
    def calculate_profit_stats(self, positions):
        """
        计算盈利统计
        """
        stats = {
            'long': {
                'lte_40': 0,    # 盈利 ≤ 40%
                'loss': 0,       # 亏损
                'gte_80': 0,     # 盈利 ≥ 80%
                'gte_120': 0     # 盈利 ≥ 120%
            },
            'short': {
                'lte_40': 0,
                'loss': 0,
                'gte_80': 0,
                'gte_120': 0
            },
            'total_long': 0,
            'total_short': 0
        }
        
        for pos in positions:
            pos_side = pos.get('pos_side', '').lower()
            
            # 计算盈利率
            upl = float(pos.get('upl', 0))
            margin = float(pos.get('margin', 1))
            profit_rate = (upl / margin * 100) if margin > 0 else 0
            
            # 统计分类
            if pos_side == 'long':
                stats['total_long'] += 1
                
                if profit_rate < 0:
                    stats['long']['loss'] += 1
                elif profit_rate <= 40:
                    stats['long']['lte_40'] += 1
                elif profit_rate >= 120:
                    stats['long']['gte_120'] += 1
                elif profit_rate >= 80:
                    stats['long']['gte_80'] += 1
                    
            elif pos_side == 'short':
                stats['total_short'] += 1
                
                if profit_rate < 0:
                    stats['short']['loss'] += 1
                elif profit_rate <= 40:
                    stats['short']['lte_40'] += 1
                elif profit_rate >= 120:
                    stats['short']['gte_120'] += 1
                elif profit_rate >= 80:
                    stats['short']['gte_80'] += 1
        
        return stats
    
    def collect_and_save(self, trade_mode='real'):
        """
        收集数据并保存到JSONL
        """
        try:
            # 获取当前持仓
            positions = self.fetch_current_positions(trade_mode)
            
            if not positions:
                logger.warning("未获取到持仓数据")
                return False
            
            # 计算统计
            stats = self.calculate_profit_stats(positions)
            
            # 构建数据记录
            record = {
                'timestamp': int(datetime.now().timestamp()),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'trade_mode': trade_mode,
                'stats': stats,
                'positions_count': len(positions),
                'collected_at': datetime.now().isoformat()
            }
            
            # 保存到JSONL
            with open(self.profit_stats_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ 数据已保存: {stats['total_long']}多 {stats['total_short']}空, " +
                       f"空单盈利≥120%: {stats['short']['gte_120']}, " +
                       f"空单亏损: {stats['short']['loss']}")
            
            return True
            
        except Exception as e:
            logger.error(f"收集并保存数据失败: {e}", exc_info=True)
            return False
    
    def get_latest_stats(self):
        """
        获取最新的统计数据
        """
        try:
            if not self.profit_stats_file.exists():
                return None
            
            # 读取最后一行
            with open(self.profit_stats_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if not lines:
                return None
            
            last_line = lines[-1].strip()
            return json.loads(last_line)
            
        except Exception as e:
            logger.error(f"读取最新统计失败: {e}")
            return None
    
    def get_recent_stats(self, hours=24):
        """
        获取最近N小时的统计数据
        """
        try:
            if not self.profit_stats_file.exists():
                return []
            
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            stats_list = []
            
            with open(self.profit_stats_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if record['timestamp'] >= cutoff_time:
                            stats_list.append(record)
                    except:
                        continue
            
            return stats_list
            
        except Exception as e:
            logger.error(f"读取历史统计失败: {e}")
            return []
    
    def run(self, interval=300, trade_mode='real'):
        """
        运行数据收集器
        interval: 收集间隔（秒），默认5分钟
        """
        logger.info(f"锚定系统数据收集器启动，间隔: {interval}秒")
        
        try:
            while True:
                logger.info("=" * 60)
                logger.info("开始数据收集")
                
                self.collect_and_save(trade_mode)
                
                logger.info(f"等待 {interval} 秒...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("数据收集器停止")
        except Exception as e:
            logger.error(f"数据收集器异常: {e}", exc_info=True)


if __name__ == '__main__':
    collector = AnchorDataCollector()
    collector.run(interval=300)  # 每5分钟收集一次
