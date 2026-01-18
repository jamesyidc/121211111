#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
恐惧贪婪指数 JSONL 数据管理器
数据来源: https://history.btc123.fans/zhishu/
"""

import json
import os
from datetime import datetime
import pytz

class FearGreedJSONLManager:
    """恐惧贪婪指数 JSONL 数据管理器"""
    
    def __init__(self, jsonl_dir='data/fear_greed_jsonl'):
        """初始化管理器"""
        self.jsonl_dir = jsonl_dir
        self.jsonl_file = os.path.join(jsonl_dir, 'fear_greed_index.jsonl')
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 确保目录存在
        os.makedirs(jsonl_dir, exist_ok=True)
        
        # 确保文件存在
        if not os.path.exists(self.jsonl_file):
            open(self.jsonl_file, 'w', encoding='utf-8').close()
    
    def add_record(self, record):
        """添加单条记录"""
        # 添加时间戳
        now = datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        record['created_at'] = now
        record['updated_at'] = now
        
        # 写入文件
        with open(self.jsonl_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def add_records(self, records):
        """批量添加记录"""
        for record in records:
            self.add_record(record)
    
    def get_all_records(self):
        """获取所有记录"""
        records = []
        if not os.path.exists(self.jsonl_file):
            return records
            
        with open(self.jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records
    
    def get_latest_record(self):
        """获取最新记录"""
        records = self.get_all_records()
        if not records:
            return None
        
        # 按日期排序，返回最新的
        records.sort(key=lambda x: x.get('datetime', ''), reverse=True)
        return records[0] if records else None
    
    def get_records_by_date_range(self, start_date, end_date):
        """根据日期范围获取记录"""
        records = self.get_all_records()
        filtered = []
        
        for r in records:
            record_date = r.get('datetime', '')
            if start_date <= record_date <= end_date:
                filtered.append(r)
        
        # 按日期排序
        filtered.sort(key=lambda x: x.get('datetime', ''))
        return filtered
    
    def get_latest_n_records(self, limit=30):
        """获取最近N条记录"""
        records = self.get_all_records()
        if not records:
            return []
        
        # 按日期排序
        records.sort(key=lambda x: x.get('datetime', ''), reverse=True)
        return records[:limit]
    
    def record_exists(self, datetime_str):
        """检查指定日期的记录是否存在"""
        records = self.get_all_records()
        for r in records:
            if r.get('datetime') == datetime_str:
                return True
        return False
    
    def update_record(self, datetime_str, new_data):
        """更新指定日期的记录"""
        records = self.get_all_records()
        updated = False
        
        # 更新记录
        for r in records:
            if r.get('datetime') == datetime_str:
                r.update(new_data)
                r['updated_at'] = datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
                updated = True
                break
        
        if updated:
            # 重写文件
            with open(self.jsonl_file, 'w', encoding='utf-8') as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + '\n')
        
        return updated
    
    def clear_all(self):
        """清空所有记录"""
        with open(self.jsonl_file, 'w', encoding='utf-8') as f:
            f.truncate(0)
    
    def get_statistics(self):
        """获取统计信息"""
        records = self.get_all_records()
        if not records:
            return {
                'total': 0,
                'latest_date': None,
                'earliest_date': None,
                'avg_value': 0,
                'max_value': 0,
                'min_value': 0
            }
        
        # 排序
        records.sort(key=lambda x: x.get('datetime', ''))
        
        values = [int(r.get('value', 0)) for r in records if r.get('value')]
        
        return {
            'total': len(records),
            'latest_date': records[-1].get('datetime'),
            'earliest_date': records[0].get('datetime'),
            'avg_value': sum(values) / len(values) if values else 0,
            'max_value': max(values) if values else 0,
            'min_value': min(values) if values else 0
        }


if __name__ == '__main__':
    # 测试
    manager = FearGreedJSONLManager()
    
    # 测试添加记录
    test_record = {
        'datetime': '2026-01-14',
        'value': '48',
        'result': '正常'
    }
    
    print("Testing FearGreedJSONLManager...")
    print(f"File: {manager.jsonl_file}")
    
    # 获取统计
    stats = manager.get_statistics()
    print(f"\nStatistics: {stats}")
    
    # 获取最新记录
    latest = manager.get_latest_record()
    if latest:
        print(f"\nLatest record: {latest['datetime']} - {latest['value']} - {latest['result']}")
