#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密货币指数JSONL管理器
用于管理27币种加权指数数据的JSONL存储
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz

class CryptoIndexJSONLManager:
    def __init__(self, data_dir='data/crypto_index_jsonl'):
        """
        初始化JSONL管理器
        :param data_dir: JSONL文件存储目录
        """
        self.data_dir = data_dir
        self.klines_file = os.path.join(data_dir, 'crypto_index_klines.jsonl')
        self.base_prices_file = os.path.join(data_dir, 'crypto_index_base_prices.jsonl')
        self.latest_file = os.path.join(data_dir, 'latest_crypto_index.jsonl')
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 创建目录
        os.makedirs(data_dir, exist_ok=True)
        
        # 创建文件（如果不存在）
        for file in [self.klines_file, self.base_prices_file, self.latest_file]:
            if not os.path.exists(file):
                open(file, 'w').close()
    
    def add_kline(self, timestamp: str, open_price: float, high_price: float,
                  low_price: float, close_price: float, index_value: float) -> bool:
        """
        添加K线数据
        """
        try:
            record = {
                'timestamp': timestamp,
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'close_price': close_price,
                'index_value': index_value,
                'created_at': datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.klines_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            # 同时更新最新记录
            self.update_latest(record)
            
            return True
        except Exception as e:
            print(f"添加K线数据失败: {e}")
            return False
    
    def save_kline(self, kline_data: Dict) -> bool:
        """
        保存K线数据（支持包含位置信息的完整记录）
        
        :param kline_data: 包含timestamp, open_price, high_price, low_price, 
                          close_price, index_value, position_4h, position_12h, 
                          position_24h, position_48h的字典
        """
        try:
            # 添加创建时间
            kline_data['created_at'] = datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.klines_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(kline_data, ensure_ascii=False) + '\n')
            
            # 同时更新最新记录
            self.update_latest(kline_data)
            
            return True
        except Exception as e:
            print(f"保存K线数据失败: {e}")
            return False
    
    def update_latest(self, record: Dict) -> bool:
        """更新最新指数记录"""
        try:
            with open(self.latest_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            print(f"更新最新记录失败: {e}")
            return False
    
    def get_latest(self) -> Optional[Dict]:
        """获取最新指数记录"""
        try:
            if os.path.exists(self.latest_file) and os.path.getsize(self.latest_file) > 0:
                with open(self.latest_file, 'r', encoding='utf-8') as f:
                    line = f.readline().strip()
                    if line:
                        return json.loads(line)
            return None
        except Exception as e:
            print(f"读取最新记录失败: {e}")
            return None
    
    def get_klines(self, limit: int = 100, start_time: Optional[str] = None,
                   end_time: Optional[str] = None) -> List[Dict]:
        """
        获取K线历史数据
        :param limit: 返回记录数限制
        :param start_time: 开始时间（可选）
        :param end_time: 结束时间（可选）
        """
        try:
            records = []
            if os.path.exists(self.klines_file) and os.path.getsize(self.klines_file) > 0:
                with open(self.klines_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            
                            # 过滤时间范围
                            if start_time and record['timestamp'] < start_time:
                                continue
                            if end_time and record['timestamp'] > end_time:
                                continue
                            
                            records.append(record)
            
            # 按时间倒序排序，返回最新的N条
            records.sort(key=lambda x: x['timestamp'], reverse=True)
            return records[:limit]
        except Exception as e:
            print(f"读取K线数据失败: {e}")
            return []
    
    def get_klines_by_time_range(self, start_time: str, end_time: str) -> List[Dict]:
        """
        根据时间范围获取K线数据
        
        :param start_time: 开始时间（格式: 'YYYY-MM-DD HH:MM:SS'）
        :param end_time: 结束时间（格式: 'YYYY-MM-DD HH:MM:SS'）
        :return: K线数据列表
        """
        try:
            records = []
            if os.path.exists(self.klines_file) and os.path.getsize(self.klines_file) > 0:
                with open(self.klines_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            timestamp = record.get('timestamp', '')
                            
                            # 筛选时间范围
                            if start_time <= timestamp <= end_time:
                                records.append(record)
            
            # 按时间正序排序
            records.sort(key=lambda x: x['timestamp'])
            return records
        except Exception as e:
            print(f"根据时间范围读取K线数据失败: {e}")
            return []
    
    def set_base_price(self, coin_id: str, base_price: float) -> bool:
        """设置基准价格"""
        try:
            # 读取所有基准价格
            base_prices = {}
            if os.path.exists(self.base_prices_file) and os.path.getsize(self.base_prices_file) > 0:
                with open(self.base_prices_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            base_prices[record['coin_id']] = record
            
            # 更新或添加
            base_prices[coin_id] = {
                'coin_id': coin_id,
                'base_price': base_price,
                'updated_at': datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 重写文件
            with open(self.base_prices_file, 'w', encoding='utf-8') as f:
                for record in base_prices.values():
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
        except Exception as e:
            print(f"设置基准价格失败: {e}")
            return False
    
    def get_base_prices(self) -> Dict[str, float]:
        """获取所有基准价格"""
        try:
            base_prices = {}
            if os.path.exists(self.base_prices_file) and os.path.getsize(self.base_prices_file) > 0:
                with open(self.base_prices_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            base_prices[record['coin_id']] = record['base_price']
            return base_prices
        except Exception as e:
            print(f"读取基准价格失败: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30):
        """清理N天前的历史K线数据"""
        try:
            cutoff_time = (datetime.now(self.beijing_tz) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 读取所有记录
            records = []
            if os.path.exists(self.klines_file) and os.path.getsize(self.klines_file) > 0:
                with open(self.klines_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            # 只保留在保留期内的记录
                            if record['timestamp'] >= cutoff_time:
                                records.append(record)
            
            # 重写文件
            with open(self.klines_file, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            removed_count = self.get_total_klines_count() - len(records)
            print(f"清理完成: 删除 {removed_count} 条K线记录")
            return removed_count
        except Exception as e:
            print(f"清理历史数据失败: {e}")
            return 0
    
    def get_total_klines_count(self) -> int:
        """获取K线总数"""
        try:
            count = 0
            if os.path.exists(self.klines_file) and os.path.getsize(self.klines_file) > 0:
                with open(self.klines_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            count += 1
            return count
        except:
            return 0
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        try:
            latest = self.get_latest()
            total_klines = self.get_total_klines_count()
            base_prices_count = len(self.get_base_prices())
            
            return {
                'total_klines': total_klines,
                'base_prices_count': base_prices_count,
                'latest_value': latest.get('index_value') if latest else None,
                'latest_timestamp': latest.get('timestamp') if latest else None
            }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {
                'total_klines': 0,
                'base_prices_count': 0,
                'latest_value': None,
                'latest_timestamp': None
            }


if __name__ == '__main__':
    # 测试
    manager = CryptoIndexJSONLManager()
    
    # 添加测试K线数据
    manager.add_kline(
        timestamp='2026-01-16 10:00:00',
        open_price=1000.0,
        high_price=1005.0,
        low_price=995.0,
        close_price=1002.0,
        index_value=1002.0
    )
    
    # 获取最新数据
    latest = manager.get_latest()
    print(f"最新记录: {latest}")
    
    # 获取统计信息
    stats = manager.get_statistics()
    print(f"统计信息: {stats}")
