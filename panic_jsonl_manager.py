#!/usr/bin/env python3
"""
恐慌清洗指数 JSONL 数据管理器
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class PanicJSONLManager:
    """恐慌清洗指数 JSONL 数据管理器"""
    
    def __init__(self, base_dir: str = '/home/user/webapp/data/panic_jsonl'):
        self.base_dir = base_dir
        self.tables = {
            'panic_wash_index': 'panic_wash_index.jsonl',
            'sar_bias_stats': 'sar_bias_stats.jsonl',  # SAR多空占比统计
            'crypto_index': 'crypto_index.jsonl',  # 加密货币指数
            'position_system': 'position_system.jsonl',  # 持仓系统
            'v1v2_monitor': 'v1v2_monitor.jsonl'  # V1V2监控
        }
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保目录存在"""
        os.makedirs(self.base_dir, exist_ok=True)
    
    def _get_file_path(self, table_name: str) -> str:
        """获取文件路径"""
        if table_name not in self.tables:
            raise ValueError(f"Unknown table: {table_name}")
        return os.path.join(self.base_dir, self.tables[table_name])
    
    def append_record(self, table_name: str, record: Dict[str, Any]) -> bool:
        """追加记录到JSONL文件"""
        try:
            file_path = self._get_file_path(table_name)
            
            # 添加时间戳
            if 'created_at' not in record:
                record['created_at'] = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
        except Exception as e:
            print(f"Error appending record: {e}")
            return False
    
    def read_records(self, 
                     table_name: str, 
                     limit: Optional[int] = None,
                     reverse: bool = True) -> List[Dict[str, Any]]:
        """读取JSONL记录"""
        try:
            file_path = self._get_file_path(table_name)
            
            if not os.path.exists(file_path):
                return []
            
            records = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            
            if reverse:
                records = list(reversed(records))
            
            if limit:
                records = records[:limit]
            
            return records
        except Exception as e:
            print(f"Error reading records: {e}")
            return []
    
    def get_latest(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取最新记录"""
        records = self.read_records(table_name, limit=1, reverse=True)
        return records[0] if records else None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {}
        
        for table_name, filename in self.tables.items():
            file_path = self._get_file_path(table_name)
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    count = sum(1 for _ in f)
                stats[table_name] = {
                    'total_records': count,
                    'file_path': file_path
                }
            else:
                stats[table_name] = {
                    'total_records': 0,
                    'file_path': file_path
                }
        
        return stats


if __name__ == '__main__':
    # 测试
    manager = PanicJSONLManager()
    
    print("📊 恐慌指数JSONL管理器测试")
    print("\n统计信息:")
    stats = manager.get_statistics()
    for table, info in stats.items():
        print(f"  {table}: {info['total_records']} 条记录")
    
    # 测试写入
    test_record = {
        'record_time': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
        'panic_index': 1.23,
        'wash_index': 4.56
    }
    
    print(f"\n测试写入: {test_record}")
    success = manager.append_record('panic_wash_index', test_record)
    print(f"写入结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 读取最新记录
    latest = manager.get_latest('panic_wash_index')
    print(f"\n最新记录: {latest}")
