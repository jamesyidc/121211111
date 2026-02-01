#!/usr/bin/env python3
"""
按日期分片存储锚点系统数据
每天一个JSONL文件，实现按需加载，避免一次性加载过大数据
"""

import json
import gzip
import os
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict


# 源数据文件
SOURCE_FILE = "/home/user/webapp/data/anchor_unified/anchor_unified_data.jsonl.gz"

# 输出目录
OUTPUT_DIR = "/home/user/webapp/data/anchor_daily"


def parse_date_from_record(record: Dict[str, Any]) -> str:
    """
    从记录中提取日期（YYYY-MM-DD格式）
    """
    try:
        timestamp = record.get("_timestamp", 0)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d")
        
        # 尝试从datetime字段解析
        datetime_str = record.get("datetime", "")
        if datetime_str:
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d")
        
        # 尝试从timestamp字段解析
        timestamp_str = record.get("timestamp", "")
        if timestamp_str and isinstance(timestamp_str, str):
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d")
        
        return "unknown"
    except Exception as e:
        print(f"⚠️  解析日期失败: {e}")
        return "unknown"


def split_by_date():
    """
    按日期分片存储数据
    """
    print("=" * 60)
    print("🔧 按日期分片存储锚点数据")
    print("=" * 60)
    print()
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 按日期分组
    print("📖 读取源数据...")
    date_records = defaultdict(list)
    total_records = 0
    
    with gzip.open(SOURCE_FILE, 'rt', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                date = parse_date_from_record(record)
                date_records[date].append(record)
                total_records += 1
                
                if total_records % 10000 == 0:
                    print(f"   已读取 {total_records:,} 条记录...")
            except json.JSONDecodeError:
                continue
    
    print(f"✅ 读取完成: 共 {total_records:,} 条记录")
    print(f"📅 覆盖日期数: {len(date_records)} 天")
    print()
    
    # 写入按日期分片的文件
    print("💾 写入日期分片文件...")
    print("-" * 60)
    
    date_stats = []
    
    for date in sorted(date_records.keys()):
        records = date_records[date]
        
        # 普通JSONL文件
        output_file = os.path.join(OUTPUT_DIR, f"anchor_data_{date}.jsonl")
        with open(output_file, 'w', encoding='utf-8') as f:
            for record in records:
                json_line = json.dumps(record, ensure_ascii=False)
                f.write(json_line + '\n')
        
        # 压缩版本
        output_file_gz = os.path.join(OUTPUT_DIR, f"anchor_data_{date}.jsonl.gz")
        with gzip.open(output_file_gz, 'wt', encoding='utf-8') as f:
            for record in records:
                json_line = json.dumps(record, ensure_ascii=False)
                f.write(json_line + '\n')
        
        file_size = os.path.getsize(output_file)
        gz_size = os.path.getsize(output_file_gz)
        
        date_stats.append({
            "date": date,
            "records": len(records),
            "size": file_size,
            "gz_size": gz_size
        })
        
        print(f"   {date}: {len(records):5,} 条记录, "
              f"{file_size/1024:.1f}KB → {gz_size/1024:.1f}KB "
              f"(压缩率 {(1-gz_size/file_size)*100:.1f}%)")
    
    print()
    print("=" * 60)
    print("✅ 分片完成！")
    print("=" * 60)
    
    # 生成索引文件
    index_file = os.path.join(OUTPUT_DIR, "date_index.json")
    index_data = {
        "generated_at": datetime.now().isoformat(),
        "total_records": total_records,
        "total_days": len(date_records),
        "dates": date_stats
    }
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📋 索引文件: {index_file}")
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print(f"📊 总计: {len(date_records)} 个日期, {total_records:,} 条记录")
    print()
    
    # 统计信息
    total_size = sum(s["size"] for s in date_stats)
    total_gz_size = sum(s["gz_size"] for s in date_stats)
    
    print(f"💾 存储统计:")
    print(f"   普通文件: {total_size/1024/1024:.2f} MB")
    print(f"   压缩文件: {total_gz_size/1024/1024:.2f} MB")
    print(f"   压缩率: {(1-total_gz_size/total_size)*100:.1f}%")
    print()


def main():
    split_by_date()


if __name__ == "__main__":
    main()
