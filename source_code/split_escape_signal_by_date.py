#!/usr/bin/env python3
"""
按日期分片存储逃顶信号数据
支持总图关键点采样和日线图详细数据
"""

import json
import gzip
import os
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import numpy as np


# 源数据文件
SOURCE_FILE = "/home/user/webapp/data/escape_signal_jsonl/escape_signal_stats.jsonl"

# 输出目录
OUTPUT_DIR = "/home/user/webapp/data/escape_signal_daily"
KEYPOINTS_FILE = "/home/user/webapp/data/escape_signal_daily/escape_signal_keypoints.jsonl.gz"


def parse_stat_time(record: Dict[str, Any]) -> datetime:
    """解析stat_time字段"""
    try:
        stat_time = record.get("stat_time", "")
        return datetime.strptime(stat_time, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"⚠️  解析时间失败: {e}, record: {record}")
        return None


def extract_keypoints(records: List[Dict[str, Any]], target_count: int = 2000) -> List[Dict[str, Any]]:
    """
    提取关键点（智能采样）
    
    策略:
    1. 保留所有极端峰值（P99.9）
    2. 保留全局极值点
    3. 保留转折点（局部极值）
    4. 均匀填充剩余点
    """
    if len(records) <= target_count:
        return records
    
    keypoints = []
    keypoints_idx = set()
    
    # 1. 提取24h和2h信号值
    signal_24h = np.array([r.get("signal_24h_count", 0) for r in records])
    signal_2h = np.array([r.get("signal_2h_count", 0) for r in records])
    
    # 2. 保留极端峰值（P99.9）
    threshold_24h = np.percentile(signal_24h, 99.9)
    threshold_2h = np.percentile(signal_2h, 99.9)
    
    for i, record in enumerate(records):
        if (record.get("signal_24h_count", 0) >= threshold_24h or 
            record.get("signal_2h_count", 0) >= threshold_2h):
            keypoints.append(record)
            keypoints_idx.add(i)
    
    print(f"   极端峰值点: {len(keypoints)}")
    
    # 3. 保留全局极值
    max_24h_idx = int(np.argmax(signal_24h))
    max_2h_idx = int(np.argmax(signal_2h))
    
    if max_24h_idx not in keypoints_idx:
        keypoints.append(records[max_24h_idx])
        keypoints_idx.add(max_24h_idx)
    
    if max_2h_idx not in keypoints_idx:
        keypoints.append(records[max_2h_idx])
        keypoints_idx.add(max_2h_idx)
    
    print(f"   全局极值点: {len(keypoints)}")
    
    # 4. 保留局部极值（转折点）- 限制数量
    window = 30  # 30分钟窗口
    max_local_peaks = 200  # 最多200个局部峰值
    local_peaks = []
    
    for i in range(window, len(records) - window):
        if i in keypoints_idx:
            continue
        
        # 检查是否为局部峰值
        local_24h = signal_24h[i-window:i+window+1]
        local_2h = signal_2h[i-window:i+window+1]
        
        is_peak_24h = signal_24h[i] == np.max(local_24h)
        is_peak_2h = signal_2h[i] == np.max(local_2h)
        
        if is_peak_24h or is_peak_2h:
            # 计算峰值强度
            strength = signal_24h[i] + signal_2h[i] * 2
            local_peaks.append((i, strength))
    
    # 选择最强的局部峰值
    local_peaks.sort(key=lambda x: x[1], reverse=True)
    for idx, _ in local_peaks[:max_local_peaks]:
        keypoints.append(records[idx])
        keypoints_idx.add(idx)
    
    print(f"   局部峰值点: {len(keypoints)}")
    
    # 5. 均匀填充剩余点
    remaining = target_count - len(keypoints)
    if remaining > 0:
        available_idx = [i for i in range(len(records)) if i not in keypoints_idx]
        
        if len(available_idx) > remaining:
            # 均匀采样
            step = len(available_idx) / remaining
            selected_idx = [available_idx[int(i * step)] for i in range(remaining)]
        else:
            selected_idx = available_idx
        
        for idx in selected_idx:
            keypoints.append(records[idx])
            keypoints_idx.add(idx)
    
    print(f"   均匀填充点: {len(keypoints) - len([i for i in keypoints_idx if i < window or i >= len(records) - window])}")
    
    # 按时间排序
    keypoints.sort(key=lambda x: x.get("stat_time", ""))
    
    return keypoints


def split_by_date():
    """按日期分片存储数据"""
    print("=" * 60)
    print("🔧 按日期分片存储逃顶信号数据")
    print("=" * 60)
    print()
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 按日期分组
    print("📖 读取源数据...")
    date_records = defaultdict(list)
    all_records = []
    total_records = 0
    
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                dt = parse_stat_time(record)
                
                if dt:
                    date = dt.strftime("%Y-%m-%d")
                    date_records[date].append(record)
                    all_records.append(record)
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
        
        # 压缩版本
        output_file_gz = os.path.join(OUTPUT_DIR, f"escape_signal_{date}.jsonl.gz")
        with gzip.open(output_file_gz, 'wt', encoding='utf-8') as f:
            for record in records:
                json_line = json.dumps(record, ensure_ascii=False)
                f.write(json_line + '\n')
        
        gz_size = os.path.getsize(output_file_gz)
        
        date_stats.append({
            "date": date,
            "records": len(records),
            "gz_size": gz_size
        })
        
        print(f"   {date}: {len(records):5,} 条记录, {gz_size/1024:.1f}KB")
    
    print()
    
    # 生成关键点文件（用于总图）
    print("🎯 生成关键点文件（用于总图）...")
    print("-" * 60)
    
    keypoints = extract_keypoints(all_records, target_count=2000)
    
    with gzip.open(KEYPOINTS_FILE, 'wt', encoding='utf-8') as f:
        for record in keypoints:
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + '\n')
    
    keypoints_size = os.path.getsize(KEYPOINTS_FILE)
    
    print(f"✅ 关键点文件: {len(keypoints):,} 个点, {keypoints_size/1024:.1f}KB")
    print(f"   压缩率: {len(keypoints)/total_records*100:.2f}%")
    print()
    
    # 生成索引文件
    index_file = os.path.join(OUTPUT_DIR, "date_index.json")
    index_data = {
        "generated_at": datetime.now().isoformat(),
        "total_records": total_records,
        "keypoints_count": len(keypoints),
        "total_days": len(date_records),
        "date_range": {
            "start": min(date_records.keys()),
            "end": max(date_records.keys())
        },
        "dates": date_stats
    }
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)
    print("✅ 分片完成！")
    print("=" * 60)
    
    print(f"\n📋 索引文件: {index_file}")
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print(f"🎯 关键点文件: {KEYPOINTS_FILE}")
    print(f"📊 总计: {len(date_records)} 个日期, {total_records:,} 条记录")
    print()
    
    # 统计信息
    total_gz_size = sum(s["gz_size"] for s in date_stats) + keypoints_size
    
    print(f"💾 存储统计:")
    print(f"   日期分片: {sum(s['gz_size'] for s in date_stats)/1024/1024:.2f} MB")
    print(f"   关键点: {keypoints_size/1024:.1f} KB")
    print(f"   总计: {total_gz_size/1024/1024:.2f} MB")
    print()


def main():
    split_by_date()


if __name__ == "__main__":
    main()
