#!/usr/bin/env python3
"""
按日期读取逃顶信号数据的工具类
支持总图关键点和日线图详细数据
"""

import json
import gzip
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class EscapeSignalDailyReader:
    """按日期读取逃顶信号数据"""
    
    def __init__(self, data_dir: str = None):
        """初始化读取器"""
        if data_dir is None:
            data_dir = "/home/user/webapp/data/escape_signal_daily"
        
        self.data_dir = data_dir
        self.index_file = os.path.join(data_dir, "date_index.json")
        self.keypoints_file = os.path.join(data_dir, "escape_signal_keypoints.jsonl.gz")
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
        if self.index_data and "dates" in self.index_data:
            return [d["date"] for d in self.index_data["dates"]]
        
        # 如果没有索引，扫描目录
        dates = []
        for filename in os.listdir(self.data_dir):
            if filename.startswith("escape_signal_") and filename.endswith(".jsonl.gz"):
                date = filename.replace("escape_signal_", "").replace(".jsonl.gz", "")
                if date != "keypoints":
                    dates.append(date)
        
        return sorted(dates)
    
    def get_keypoints(self) -> List[Dict[str, Any]]:
        """
        获取关键点数据（用于总图）
        
        Returns:
            关键点列表（约2000个点）
        """
        if not os.path.exists(self.keypoints_file):
            return []
        
        records = []
        with gzip.open(self.keypoints_file, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        return records
    
    def get_date_data(self, date: str) -> List[Dict[str, Any]]:
        """
        获取指定日期的完整数据（用于日线图）
        
        Args:
            date: 日期 (YYYY-MM-DD格式)
        
        Returns:
            记录列表
        """
        # 构建文件路径
        gz_file = os.path.join(self.data_dir, f"escape_signal_{date}.jsonl.gz")
        
        if not os.path.exists(gz_file):
            return []
        
        # 读取数据
        records = []
        with gzip.open(gz_file, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        return records
    
    def get_today_data(self) -> List[Dict[str, Any]]:
        """
        获取今天的数据
        
        Returns:
            记录列表
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_date_data(today)
    
    def get_date_range_data(self, start_date: str, end_date: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取日期范围内的数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            {日期: 记录列表} 字典
        """
        result = {}
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            data = self.get_date_data(date_str)
            if data:
                result[date_str] = data
            current += timedelta(days=1)
        
        return result
    
    def get_date_statistics(self, date: str) -> Dict[str, Any]:
        """
        获取指定日期的统计信息
        
        Args:
            date: 日期 (YYYY-MM-DD格式)
        
        Returns:
            统计信息字典
        """
        if self.index_data and "dates" in self.index_data:
            for date_info in self.index_data["dates"]:
                if date_info["date"] == date:
                    return date_info
        
        # 如果没有索引，读取文件统计
        records = self.get_date_data(date)
        
        if not records:
            return {"date": date, "records": 0}
        
        # 统计信号值
        signal_24h = [r.get("signal_24h_count", 0) for r in records]
        signal_2h = [r.get("signal_2h_count", 0) for r in records]
        
        return {
            "date": date,
            "records": len(records),
            "max_signal_24h": max(signal_24h) if signal_24h else 0,
            "max_signal_2h": max(signal_2h) if signal_2h else 0,
            "avg_signal_24h": sum(signal_24h) / len(signal_24h) if signal_24h else 0,
            "avg_signal_2h": sum(signal_2h) / len(signal_2h) if signal_2h else 0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取数据总览
        
        Returns:
            总览信息
        """
        if self.index_data:
            return {
                "total_records": self.index_data.get("total_records", 0),
                "keypoints_count": self.index_data.get("keypoints_count", 0),
                "total_days": self.index_data.get("total_days", 0),
                "date_range": self.index_data.get("date_range", {}),
                "generated_at": self.index_data.get("generated_at", "")
            }
        
        return {}


def demo():
    """演示用法"""
    print("=" * 60)
    print("🔧 按日期读取逃顶信号数据 - 演示")
    print("=" * 60)
    print()
    
    reader = EscapeSignalDailyReader()
    
    # 1. 获取总览信息
    print("📊 数据总览:")
    print("-" * 60)
    summary = reader.get_summary()
    print(f"总记录数: {summary.get('total_records', 0):,}")
    print(f"关键点数: {summary.get('keypoints_count', 0):,}")
    print(f"总天数: {summary.get('total_days', 0)}")
    print(f"日期范围: {summary.get('date_range', {}).get('start')} ~ {summary.get('date_range', {}).get('end')}")
    print()
    
    # 2. 获取关键点（用于总图）
    print("🎯 关键点数据（用于总图）:")
    print("-" * 60)
    keypoints = reader.get_keypoints()
    print(f"关键点数量: {len(keypoints):,}")
    if keypoints:
        print(f"第一个点: {keypoints[0].get('stat_time')} - 24h信号: {keypoints[0].get('signal_24h_count')}")
        print(f"最后一个点: {keypoints[-1].get('stat_time')} - 24h信号: {keypoints[-1].get('signal_24h_count')}")
    print()
    
    # 3. 获取今天的数据（用于日线图）
    print("📅 今天的数据（用于日线图）:")
    print("-" * 60)
    today = datetime.now().strftime("%Y-%m-%d")
    today_data = reader.get_today_data()
    print(f"日期: {today}")
    print(f"记录数: {len(today_data):,}")
    
    if today_data:
        stats = reader.get_date_statistics(today)
        print(f"最大24h信号: {stats.get('max_signal_24h', 0)}")
        print(f"最大2h信号: {stats.get('max_signal_2h', 0)}")
        print(f"平均24h信号: {stats.get('avg_signal_24h', 0):.1f}")
    print()
    
    # 4. 获取可用日期列表
    print("📆 可用日期列表:")
    print("-" * 60)
    dates = reader.get_available_dates()
    print(f"总天数: {len(dates)}")
    print(f"最早: {dates[0] if dates else 'N/A'}")
    print(f"最新: {dates[-1] if dates else 'N/A'}")
    
    print()
    print("=" * 60)
    print("✅ 演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
