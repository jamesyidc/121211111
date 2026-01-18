#!/usr/bin/env python3
"""
逃顶信号JSONL管理器
提供对escape_signal_stats JSONL文件的读写操作
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import pytz


class EscapeSignalJSONLManager:
    """逃顶信号JSONL数据管理器"""
    
    def __init__(self, data_dir: str = '/home/user/webapp/data/escape_signal_jsonl'):
        self.data_dir = data_dir
        self.stats_file = os.path.join(data_dir, 'escape_signal_stats.jsonl')
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
    
    def read_records(self, limit: Optional[int] = None, reverse: bool = True) -> List[Dict[str, Any]]:
        """
        读取记录
        
        参数:
            limit: 返回记录数，None表示返回所有数据
            reverse: 是否倒序（最新记录在前）
        """
        if not os.path.exists(self.stats_file):
            return []
        
        records = []
        
        # 如果需要倒序且limit较小，使用tail优化
        if reverse and limit and limit <= 10000:
            records = self._read_last_n_lines(limit)
        else:
            # 常规读取
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
            
            if reverse:
                records.reverse()
            
            if limit:
                records = records[:limit]
        
        return records
    
    def _read_last_n_lines(self, n: int) -> List[Dict[str, Any]]:
        """使用tail读取最后N行（优化大文件读取）"""
        import subprocess
        
        try:
            result = subprocess.run(
                ['tail', '-n', str(n), self.stats_file],
                capture_output=True,
                text=True,
                check=True
            )
            
            records = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue
            
            records.reverse()  # tail给出的是正序，需要倒序
            return records
        except Exception:
            # 如果tail失败，回退到普通读取
            return []
    
    def get_latest_stats(self) -> Optional[Dict[str, Any]]:
        """获取最新的统计记录"""
        records = self.read_records(limit=1, reverse=True)
        return records[0] if records else None
    
    def get_stats_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        获取指定日期的统计记录
        
        参数:
            date: 日期字符串，格式: YYYY-MM-DD
        """
        all_records = self.read_records(limit=5000, reverse=False)  # 获取最近5000条
        return [r for r in all_records if r.get('stat_time', '').startswith(date)]
    
    def get_stats_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        获取指定日期范围的统计记录
        
        参数:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
        """
        all_records = self.read_records(reverse=False)
        return [
            r for r in all_records 
            if start_date <= r.get('stat_time', '')[:10] <= end_date
        ]
    
    def append_record(self, record: Dict[str, Any]) -> bool:
        """追加一条新记录到JSONL文件"""
        try:
            with open(self.stats_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            print(f"Error appending record: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not os.path.exists(self.stats_file):
            return {
                'total_records': 0,
                'file_size_mb': 0,
                'latest_time': None
            }
        
        # 计算文件大小
        file_size = os.path.getsize(self.stats_file)
        
        # 计算记录总数
        with open(self.stats_file, 'r', encoding='utf-8') as f:
            total_records = sum(1 for _ in f)
        
        # 获取最新时间
        latest = self.get_latest_stats()
        latest_time = latest.get('stat_time') if latest else None
        
        return {
            'total_records': total_records,
            'file_size_mb': file_size / (1024 * 1024),
            'latest_time': latest_time,
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)'
        }


if __name__ == '__main__':
    # 测试代码
    manager = EscapeSignalJSONLManager()
    
    print("📊 逃顶信号JSONL管理器测试")
    print("=" * 60)
    
    # 获取统计信息
    stats = manager.get_statistics()
    print(f"\n统计信息:")
    print(f"  总记录数: {stats['total_records']:,}")
    print(f"  文件大小: {stats['file_size_mb']:.2f} MB")
    print(f"  最新时间: {stats['latest_time']}")
    
    # 获取最新记录
    latest = manager.get_latest_stats()
    if latest:
        print(f"\n最新记录:")
        print(f"  时间: {latest.get('stat_time')}")
        print(f"  24h信号: {latest.get('signal_24h_count')}")
        print(f"  2h信号: {latest.get('signal_2h_count')}")
        print(f"  最大24h: {latest.get('max_signal_24h')}")
        print(f"  最大2h: {latest.get('max_signal_2h')}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
