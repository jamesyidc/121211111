#!/usr/bin/env python3
"""
按日期读取锚点数据的工具类
支持按需加载，避免一次性加载大量数据
"""

import json
import gzip
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class AnchorDailyReader:
    """按日期读取锚点数据"""
    
    def __init__(self, data_dir: str = None):
        """初始化读取器"""
        if data_dir is None:
            data_dir = "/home/user/webapp/data/anchor_daily"
        
        self.data_dir = data_dir
        self.index_file = os.path.join(data_dir, "date_index.json")
        self.index_data = None
        self._load_index()
    
    def _load_index(self):
        """加载索引文件"""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index_data = json.load(f)
    
    def get_available_dates(self) -> List[str]:
        """
        获取可用的日期列表
        
        Returns:
            日期列表 (YYYY-MM-DD格式)
        """
        if self.index_data:
            return [d["date"] for d in self.index_data["dates"]]
        
        # 如果没有索引，扫描目录
        dates = []
        for filename in os.listdir(self.data_dir):
            if filename.startswith("anchor_data_") and filename.endswith(".jsonl.gz"):
                date = filename.replace("anchor_data_", "").replace(".jsonl.gz", "")
                dates.append(date)
        
        return sorted(dates)
    
    def get_date_data(self, date: str, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取指定日期的数据
        
        Args:
            date: 日期 (YYYY-MM-DD格式)
            data_type: 数据类型过滤 (profit_stats, monitors, alerts等)
        
        Returns:
            记录列表
        """
        # 构建文件路径（优先使用压缩文件）
        gz_file = os.path.join(self.data_dir, f"anchor_data_{date}.jsonl.gz")
        normal_file = os.path.join(self.data_dir, f"anchor_data_{date}.jsonl")
        
        # 选择存在的文件
        if os.path.exists(gz_file):
            file_path = gz_file
            use_gzip = True
        elif os.path.exists(normal_file):
            file_path = normal_file
            use_gzip = False
        else:
            return []
        
        # 读取数据
        records = []
        
        if use_gzip:
            f = gzip.open(file_path, 'rt', encoding='utf-8')
        else:
            f = open(file_path, 'r', encoding='utf-8')
        
        try:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    
                    # 类型过滤
                    if data_type and record.get("_data_type") != data_type:
                        continue
                    
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        finally:
            f.close()
        
        return records
    
    def get_today_data(self, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取今天的数据
        
        Args:
            data_type: 数据类型过滤
        
        Returns:
            记录列表
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_date_data(today, data_type)
    
    def get_recent_days(self, days: int = 7, data_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取最近N天的数据
        
        Args:
            days: 天数
            data_type: 数据类型过滤
        
        Returns:
            {日期: 记录列表} 字典
        """
        result = {}
        
        # 计算日期范围
        end_date = datetime.now()
        
        for i in range(days):
            date = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
            data = self.get_date_data(date, data_type)
            if data:
                result[date] = data
        
        return result
    
    def get_date_statistics(self, date: str) -> Dict[str, Any]:
        """
        获取指定日期的统计信息
        
        Args:
            date: 日期 (YYYY-MM-DD格式)
        
        Returns:
            统计信息字典
        """
        if self.index_data:
            for date_info in self.index_data["dates"]:
                if date_info["date"] == date:
                    return date_info
        
        # 如果没有索引，读取文件统计
        records = self.get_date_data(date)
        
        # 统计数据类型
        type_counts = {}
        for record in records:
            data_type = record.get("_data_type", "unknown")
            type_counts[data_type] = type_counts.get(data_type, 0) + 1
        
        return {
            "date": date,
            "records": len(records),
            "data_types": type_counts
        }
    
    def get_profit_stats_summary(self, date: str) -> Dict[str, Any]:
        """
        获取指定日期的盈利统计摘要
        
        Args:
            date: 日期 (YYYY-MM-DD格式)
        
        Returns:
            盈利统计摘要
        """
        records = self.get_date_data(date, data_type="profit_stats")
        
        if not records:
            return {
                "date": date,
                "has_data": False
            }
        
        # 获取最新的统计
        latest = records[-1]
        stats_data = latest.get("stats", {})
        
        # 检查是否有long/short分类
        if "long" in stats_data:
            return {
                "date": date,
                "has_data": True,
                "long": stats_data["long"],
                "short": stats_data["short"],
                "timestamp": latest.get("_timestamp"),
                "datetime": datetime.fromtimestamp(latest.get("_timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {
                "date": date,
                "has_data": True,
                "stats": stats_data,
                "timestamp": latest.get("_timestamp"),
                "datetime": datetime.fromtimestamp(latest.get("_timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
            }


def demo():
    """演示用法"""
    print("=" * 60)
    print("🔧 按日期读取锚点数据 - 演示")
    print("=" * 60)
    print()
    
    reader = AnchorDailyReader()
    
    # 1. 获取可用日期
    print("📅 可用日期列表:")
    print("-" * 60)
    available_dates = reader.get_available_dates()
    for date in available_dates:
        print(f"   {date}")
    print()
    
    # 2. 获取今天的数据
    print("📊 今天的数据:")
    print("-" * 60)
    today = datetime.now().strftime("%Y-%m-%d")
    today_stats = reader.get_date_statistics(today)
    print(f"日期: {today}")
    print(f"记录数: {today_stats.get('records', 0):,}")
    if 'data_types' in today_stats:
        for dtype, count in today_stats['data_types'].items():
            print(f"  {dtype}: {count}")
    print()
    
    # 3. 获取盈利统计摘要
    print("💰 今天的盈利统计:")
    print("-" * 60)
    profit_summary = reader.get_profit_stats_summary(today)
    if profit_summary.get("has_data"):
        print(f"最后更新: {profit_summary.get('datetime')}")
        if "long" in profit_summary:
            long_stats = profit_summary["long"]
            short_stats = profit_summary["short"]
            print(f"多单: 总{long_stats.get('total', 0)}单, "
                  f"≥120%: {long_stats.get('gte_120', 0)}, "
                  f"≥80%: {long_stats.get('gte_80', 0)}, "
                  f"亏损: {long_stats.get('loss', 0)}")
            print(f"空单: 总{short_stats.get('total', 0)}单, "
                  f"≥120%: {short_stats.get('gte_120', 0)}, "
                  f"≥80%: {short_stats.get('gte_80', 0)}, "
                  f"亏损: {short_stats.get('loss', 0)}")
    else:
        print("暂无数据")
    print()
    
    # 4. 获取最近7天的统计
    print("📈 最近7天统计:")
    print("-" * 60)
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        stats = reader.get_date_statistics(date)
        print(f"{date}: {stats.get('records', 0):5,} 条记录")
    
    print()
    print("=" * 60)
    print("✅ 演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
