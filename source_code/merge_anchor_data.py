#!/usr/bin/env python3
"""
整合锚点系统数据到单一JSONL文件
将多个JSONL文件按时间轴合并，提高加载效率
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
import gzip

# 数据文件路径
DATA_DIR = "/home/user/webapp/data"
ANCHOR_JSONL_DIR = os.path.join(DATA_DIR, "anchor_jsonl")
ANCHOR_STATS_DIR = os.path.join(DATA_DIR, "anchor_profit_stats")

# 输出文件
OUTPUT_FILE = os.path.join(DATA_DIR, "anchor_unified/anchor_unified_data.jsonl")
OUTPUT_FILE_GZ = os.path.join(DATA_DIR, "anchor_unified/anchor_unified_data.jsonl.gz")

# 源文件映射
SOURCE_FILES = {
    "profit_stats": os.path.join(ANCHOR_STATS_DIR, "anchor_profit_stats.jsonl"),
    "monitors": os.path.join(ANCHOR_JSONL_DIR, "anchor_monitors.jsonl"),
    "alerts": os.path.join(ANCHOR_JSONL_DIR, "anchor_alerts.jsonl"),
    "real_profit": os.path.join(ANCHOR_JSONL_DIR, "anchor_real_profit_records.jsonl"),
    "profit_records": os.path.join(ANCHOR_JSONL_DIR, "anchor_profit_records.jsonl"),
}


def parse_timestamp(record: Dict[str, Any], data_type: str) -> int:
    """
    从记录中提取时间戳并转换为Unix时间戳
    """
    try:
        if data_type == "profit_stats":
            # 已经有timestamp字段
            if "timestamp" in record and isinstance(record["timestamp"], int):
                return record["timestamp"]
            # 使用datetime字段
            dt_str = record.get("datetime", "")
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            return int(dt.timestamp())
        
        elif data_type in ["monitors", "alerts"]:
            # 使用timestamp字段
            ts_str = record.get("timestamp", "")
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            return int(dt.timestamp())
        
        elif data_type in ["real_profit", "profit_records"]:
            # 使用timestamp或created_at字段
            ts_str = record.get("timestamp") or record.get("created_at", "")
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            return int(dt.timestamp())
        
        else:
            return 0
    except Exception as e:
        print(f"⚠️  解析时间戳失败: {e}, record: {record.get('timestamp', 'N/A')}")
        return 0


def read_jsonl(file_path: str, data_type: str) -> List[Dict[str, Any]]:
    """
    读取JSONL文件并添加数据类型标记
    """
    records = []
    if not os.path.exists(file_path):
        print(f"⚠️  文件不存在: {file_path}")
        return records
    
    print(f"📖 读取 {data_type} 数据: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                # 添加元数据
                record["_data_type"] = data_type
                record["_timestamp"] = parse_timestamp(record, data_type)
                records.append(record)
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON解析错误 (行 {line_num}): {e}")
                continue
    
    print(f"✅ 读取完成: {len(records)} 条记录")
    return records


def merge_and_sort_data() -> List[Dict[str, Any]]:
    """
    合并所有数据源并按时间排序
    """
    all_records = []
    
    for data_type, file_path in SOURCE_FILES.items():
        records = read_jsonl(file_path, data_type)
        all_records.extend(records)
        print(f"   累计记录数: {len(all_records)}")
    
    # 按时间戳排序
    print("\n🔄 排序数据...")
    all_records.sort(key=lambda x: x.get("_timestamp", 0))
    
    return all_records


def write_unified_jsonl(records: List[Dict[str, Any]]):
    """
    写入统一的JSONL文件（普通和压缩版本）
    """
    # 创建输出目录
    output_dir = os.path.dirname(OUTPUT_FILE)
    os.makedirs(output_dir, exist_ok=True)
    
    # 写入普通JSONL
    print(f"\n💾 写入统一JSONL: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for record in records:
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + '\n')
    
    # 写入压缩版本
    print(f"💾 写入压缩JSONL: {OUTPUT_FILE_GZ}")
    with gzip.open(OUTPUT_FILE_GZ, 'wt', encoding='utf-8') as f:
        for record in records:
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + '\n')
    
    # 统计信息
    file_size = os.path.getsize(OUTPUT_FILE)
    gz_size = os.path.getsize(OUTPUT_FILE_GZ)
    
    print(f"\n✅ 合并完成！")
    print(f"   总记录数: {len(records):,}")
    print(f"   普通文件大小: {file_size / 1024 / 1024:.2f} MB")
    print(f"   压缩文件大小: {gz_size / 1024 / 1024:.2f} MB")
    print(f"   压缩率: {(1 - gz_size / file_size) * 100:.1f}%")


def generate_statistics(records: List[Dict[str, Any]]):
    """
    生成数据统计信息
    """
    print("\n📊 数据统计:")
    
    # 按类型统计
    type_counts = {}
    for record in records:
        data_type = record.get("_data_type", "unknown")
        type_counts[data_type] = type_counts.get(data_type, 0) + 1
    
    for data_type, count in sorted(type_counts.items()):
        print(f"   {data_type:20s}: {count:6,} 条")
    
    # 时间范围
    if records:
        first_ts = records[0].get("_timestamp", 0)
        last_ts = records[-1].get("_timestamp", 0)
        
        first_dt = datetime.fromtimestamp(first_ts).strftime("%Y-%m-%d %H:%M:%S")
        last_dt = datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n⏱️  时间范围:")
        print(f"   开始: {first_dt}")
        print(f"   结束: {last_dt}")
        
        days = (last_ts - first_ts) / 86400
        print(f"   跨度: {days:.1f} 天")


def main():
    """
    主函数
    """
    print("=" * 60)
    print("🔧 锚点系统数据整合工具")
    print("=" * 60)
    print()
    
    # 1. 读取并合并数据
    print("📥 步骤 1: 读取所有数据源")
    print("-" * 60)
    records = merge_and_sort_data()
    
    # 2. 生成统计
    generate_statistics(records)
    
    # 3. 写入统一文件
    print("\n" + "-" * 60)
    print("📥 步骤 2: 写入统一文件")
    print("-" * 60)
    write_unified_jsonl(records)
    
    print("\n" + "=" * 60)
    print("✅ 全部完成！")
    print("=" * 60)
    print(f"\n输出文件:")
    print(f"  - {OUTPUT_FILE}")
    print(f"  - {OUTPUT_FILE_GZ}")
    print()


if __name__ == "__main__":
    main()
