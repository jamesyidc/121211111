#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格涨速数据JSONL管理器
用于管理1分钟涨跌速监控数据的JSONL存储
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz

class PriceSpeedJSONLManager:
    def __init__(self, data_dir='data/price_speed_jsonl'):
        """
        初始化JSONL管理器
        :param data_dir: JSONL文件存储目录
        """
        self.data_dir = data_dir
        self.latest_file = os.path.join(data_dir, 'latest_price_speed.jsonl')
        self.history_file = os.path.join(data_dir, 'price_speed_history.jsonl')
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 创建目录
        os.makedirs(data_dir, exist_ok=True)
        
        # 创建文件（如果不存在）
        for file in [self.latest_file, self.history_file]:
            if not os.path.exists(file):
                open(file, 'w').close()
    
    def add_latest_record(self, symbol: str, current_price: float, previous_price: float,
                         change_percent: float, alert_level: str, alert_type: str, 
                         timestamp: str) -> bool:
        """
        添加或更新最新状态记录（每个币种只保留最新一条）
        """
        try:
            # 读取所有现有记录
            existing_records = {}
            if os.path.exists(self.latest_file) and os.path.getsize(self.latest_file) > 0:
                with open(self.latest_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            existing_records[record['symbol']] = record
            
            # 更新或添加新记录
            existing_records[symbol] = {
                'symbol': symbol,
                'current_price': current_price,
                'previous_price': previous_price,
                'change_percent': change_percent,
                'alert_level': alert_level,
                'alert_type': alert_type,
                'timestamp': timestamp,
                'updated_at': datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 重写文件
            with open(self.latest_file, 'w', encoding='utf-8') as f:
                for record in existing_records.values():
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
        except Exception as e:
            print(f"添加最新记录失败: {e}")
            return False
    
    def add_history_record(self, symbol: str, current_price: float, previous_price: float,
                          change_percent: float, alert_level: str, alert_type: str,
                          timestamp: str) -> bool:
        """
        添加历史记录
        """
        try:
            record = {
                'symbol': symbol,
                'current_price': current_price,
                'previous_price': previous_price,
                'change_percent': change_percent,
                'alert_level': alert_level,
                'alert_type': alert_type,
                'timestamp': timestamp,
                'created_at': datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
        except Exception as e:
            print(f"添加历史记录失败: {e}")
            return False
    
    def get_latest_all(self) -> List[Dict]:
        """获取所有币种的最新状态"""
        try:
            records = []
            if os.path.exists(self.latest_file) and os.path.getsize(self.latest_file) > 0:
                with open(self.latest_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            records.append(json.loads(line))
            
            # 按币种名称排序
            records.sort(key=lambda x: x['symbol'])
            return records
        except Exception as e:
            print(f"读取最新记录失败: {e}")
            return []
    
    def get_latest_by_symbol(self, symbol: str) -> Optional[Dict]:
        """获取指定币种的最新状态"""
        try:
            if os.path.exists(self.latest_file) and os.path.getsize(self.latest_file) > 0:
                with open(self.latest_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            if record['symbol'] == symbol:
                                return record
            return None
        except Exception as e:
            print(f"读取币种记录失败: {e}")
            return None
    
    def get_history(self, symbol: Optional[str] = None, limit: int = 100,
                   start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Dict]:
        """
        获取历史记录
        :param symbol: 币种（可选，不指定则返回所有）
        :param limit: 返回记录数限制
        :param start_time: 开始时间（可选）
        :param end_time: 结束时间（可选）
        """
        try:
            records = []
            if os.path.exists(self.history_file) and os.path.getsize(self.history_file) > 0:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            
                            # 过滤币种
                            if symbol and record['symbol'] != symbol:
                                continue
                            
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
            print(f"读取历史记录失败: {e}")
            return []
    
    def get_alerts_by_level(self, alert_level: str, limit: int = 50) -> List[Dict]:
        """获取指定预警级别的记录"""
        try:
            records = []
            if os.path.exists(self.history_file) and os.path.getsize(self.history_file) > 0:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            if record['alert_level'] == alert_level:
                                records.append(record)
            
            # 按时间倒序排序
            records.sort(key=lambda x: x['timestamp'], reverse=True)
            return records[:limit]
        except Exception as e:
            print(f"读取预警记录失败: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 7):
        """清理N天前的历史数据"""
        try:
            cutoff_time = (datetime.now(self.beijing_tz) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 读取所有记录
            records = []
            if os.path.exists(self.history_file) and os.path.getsize(self.history_file) > 0:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            # 只保留在保留期内的记录
                            if record['timestamp'] >= cutoff_time:
                                records.append(record)
            
            # 重写文件
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            removed_count = self.get_total_history_count() - len(records)
            print(f"清理完成: 删除 {removed_count} 条历史记录")
            return removed_count
        except Exception as e:
            print(f"清理历史数据失败: {e}")
            return 0
    
    def get_total_history_count(self) -> int:
        """获取历史记录总数"""
        try:
            count = 0
            if os.path.exists(self.history_file) and os.path.getsize(self.history_file) > 0:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            count += 1
            return count
        except:
            return 0
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        try:
            latest_records = self.get_latest_all()
            total_count = len(latest_records)
            
            # 统计各类预警数量
            alert_stats = {
                'UP': 0,
                'DOWN': 0,
                'NORMAL': 0
            }
            
            for record in latest_records:
                alert_type = record.get('alert_type', 'NORMAL')
                if alert_type in alert_stats:
                    alert_stats[alert_type] += 1
            
            # 获取最新更新时间
            update_time = None
            if latest_records:
                update_time = max(record.get('timestamp', '') for record in latest_records)
            
            return {
                'total_count': total_count,
                'alert_up': alert_stats['UP'],
                'alert_down': alert_stats['DOWN'],
                'alert_normal': alert_stats['NORMAL'],
                'update_time': update_time,
                'history_count': self.get_total_history_count()
            }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {
                'total_count': 0,
                'alert_up': 0,
                'alert_down': 0,
                'alert_normal': 0,
                'update_time': None,
                'history_count': 0
            }


if __name__ == '__main__':
    # 测试
    manager = PriceSpeedJSONLManager()
    
    # 添加测试数据
    manager.add_latest_record(
        symbol='BTC',
        current_price=95450.0,
        previous_price=95400.0,
        change_percent=0.05,
        alert_level='normal',
        alert_type='NORMAL',
        timestamp='2026-01-16 10:30:00'
    )
    
    # 获取最新数据
    latest = manager.get_latest_all()
    print(f"最新记录数: {len(latest)}")
    if latest:
        print(f"示例: {latest[0]}")
    
    # 获取统计信息
    stats = manager.get_statistics()
    print(f"统计信息: {stats}")
