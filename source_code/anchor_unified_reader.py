#!/usr/bin/env python3
"""
统一锚点数据读取器
提供高效的数据查询接口
"""

import json
import gzip
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class AnchorUnifiedReader:
    """统一锚点数据读取器"""
    
    def __init__(self, data_file: str = None):
        """初始化读取器"""
        if data_file is None:
            # 默认使用压缩文件（更快）
            data_file = "/home/user/webapp/data/anchor_unified/anchor_unified_data.jsonl.gz"
        
        self.data_file = data_file
        self.use_gzip = data_file.endswith('.gz')
        
        # 缓存统计信息
        self._total_records = None
        self._time_range = None
        self._data_types = None
    
    def _open_file(self):
        """打开数据文件（支持普通和压缩格式）"""
        if self.use_gzip:
            return gzip.open(self.data_file, 'rt', encoding='utf-8')
        else:
            return open(self.data_file, 'r', encoding='utf-8')
    
    def get_latest(self, data_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最新的N条记录
        
        Args:
            data_type: 数据类型过滤 (profit_stats, monitors, alerts, real_profit, profit_records)
            limit: 返回记录数量
        
        Returns:
            记录列表（按时间倒序）
        """
        records = []
        
        # 从文件末尾往前读
        with self._open_file() as f:
            lines = f.readlines()
            
            # 从后往前遍历
            for line in reversed(lines):
                if len(records) >= limit:
                    break
                
                try:
                    record = json.loads(line.strip())
                    
                    # 类型过滤
                    if data_type and record.get("_data_type") != data_type:
                        continue
                    
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        return records
    
    def get_by_time_range(
        self, 
        start_time: datetime, 
        end_time: datetime,
        data_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        按时间范围获取数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            data_type: 数据类型过滤
        
        Returns:
            记录列表
        """
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        records = []
        
        with self._open_file() as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    
                    # 时间过滤
                    ts = record.get("_timestamp", 0)
                    if ts < start_ts or ts > end_ts:
                        continue
                    
                    # 类型过滤
                    if data_type and record.get("_data_type") != data_type:
                        continue
                    
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        return records
    
    def get_profit_stats_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取最近N小时的盈利统计数据
        
        Args:
            hours: 小时数
        
        Returns:
            盈利统计记录列表
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        return self.get_by_time_range(start_time, end_time, data_type="profit_stats")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据统计信息
        
        Returns:
            统计信息字典
        """
        if self._total_records is not None:
            return {
                "total_records": self._total_records,
                "time_range": self._time_range,
                "data_types": self._data_types
            }
        
        # 统计数据
        type_counts = {}
        first_ts = None
        last_ts = None
        total = 0
        
        with self._open_file() as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    total += 1
                    
                    # 类型统计
                    data_type = record.get("_data_type", "unknown")
                    type_counts[data_type] = type_counts.get(data_type, 0) + 1
                    
                    # 时间范围
                    ts = record.get("_timestamp", 0)
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts
                    
                except json.JSONDecodeError:
                    continue
        
        # 缓存结果
        self._total_records = total
        self._time_range = {
            "start": datetime.fromtimestamp(first_ts).isoformat() if first_ts else None,
            "end": datetime.fromtimestamp(last_ts).isoformat() if last_ts else None,
            "days": (last_ts - first_ts) / 86400 if (first_ts and last_ts) else 0
        }
        self._data_types = type_counts
        
        return {
            "total_records": total,
            "time_range": self._time_range,
            "data_types": type_counts,
            "file_size_mb": os.path.getsize(self.data_file) / 1024 / 1024
        }


def demo():
    """演示用法"""
    print("=" * 60)
    print("🔧 统一锚点数据读取器 - 演示")
    print("=" * 60)
    print()
    
    reader = AnchorUnifiedReader()
    
    # 1. 获取统计信息
    print("📊 数据统计信息:")
    print("-" * 60)
    stats = reader.get_statistics()
    print(f"总记录数: {stats['total_records']:,}")
    print(f"文件大小: {stats['file_size_mb']:.2f} MB")
    print(f"时间范围: {stats['time_range']['start']} ~ {stats['time_range']['end']}")
    print(f"跨度天数: {stats['time_range']['days']:.1f} 天")
    print()
    print("数据类型分布:")
    for dtype, count in sorted(stats['data_types'].items()):
        print(f"  {dtype:20s}: {count:6,} 条")
    print()
    
    # 2. 获取最新的盈利统计
    print("💰 最新盈利统计 (最近5条):")
    print("-" * 60)
    latest_stats = reader.get_latest(data_type="profit_stats", limit=5)
    for i, record in enumerate(latest_stats, 1):
        dt = datetime.fromtimestamp(record['_timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        stats_data = record.get('stats', {})
        
        # 检查是否有long/short分类
        if 'long' in stats_data:
            long_stats = stats_data['long']
            short_stats = stats_data['short']
            print(f"{i}. {dt}")
            print(f"   多单: 总{long_stats.get('total', 0)}单, "
                  f"≥120%: {long_stats.get('gte_120', 0)}, "
                  f"≥80%: {long_stats.get('gte_80', 0)}, "
                  f"亏损: {long_stats.get('loss', 0)}")
            print(f"   空单: 总{short_stats.get('total', 0)}单, "
                  f"≥120%: {short_stats.get('gte_120', 0)}, "
                  f"≥80%: {short_stats.get('gte_80', 0)}, "
                  f"亏损: {short_stats.get('loss', 0)}")
        else:
            print(f"{i}. {dt} - 总{stats_data.get('total', 0)}单, "
                  f"≥120%: {stats_data.get('gte_120', 0)}, "
                  f"≥80%: {stats_data.get('gte_80', 0)}, "
                  f"亏损: {stats_data.get('loss', 0)}")
    print()
    
    # 3. 获取最近24小时的数据
    print("📅 最近24小时盈利统计:")
    print("-" * 60)
    last_24h = reader.get_profit_stats_history(hours=24)
    print(f"记录数: {len(last_24h)}")
    if last_24h:
        first = datetime.fromtimestamp(last_24h[0]['_timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        last = datetime.fromtimestamp(last_24h[-1]['_timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        print(f"时间范围: {first} ~ {last}")
    print()
    
    # 4. 获取最新的预警
    print("⚠️  最新预警 (最近3条):")
    print("-" * 60)
    latest_alerts = reader.get_latest(data_type="alerts", limit=3)
    for i, record in enumerate(latest_alerts, 1):
        dt = datetime.fromtimestamp(record['_timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{i}. {dt}")
        print(f"   币种: {record.get('inst_id', 'N/A')}")
        print(f"   方向: {record.get('pos_side', 'N/A')}")
        print(f"   盈利率: {record.get('profit_rate', 0):.2f}%")
        print(f"   类型: {record.get('alert_type', 'N/A')}")
    
    print()
    print("=" * 60)
    print("✅ 演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
