#!/usr/bin/env python3
"""
同步Google Drive数据到Query数据
将gdrive_jsonl的数据同步到query_jsonl，供查询页面使用
"""
import json
import os
from datetime import datetime
import sys

# 添加路径
sys.path.insert(0, '/home/user/webapp/source_code')
sys.path.insert(0, '/home/user/webapp')

from query_jsonl_manager import QueryJSONLManager
from gdrive_jsonl_manager import GDriveJSONLManager

def sync_snapshots():
    """同步快照数据"""
    print("🔄 开始同步快照数据...")
    
    # 初始化管理器
    gdrive_manager = GDriveJSONLManager()
    query_manager = QueryJSONLManager()
    
    # 读取gdrive数据
    gdrive_snapshots = gdrive_manager.read_all_snapshots()
    print(f"📊 从GDrive读取到 {len(gdrive_snapshots)} 条快照记录")
    
    if not gdrive_snapshots:
        print("❌ 没有可同步的数据")
        return
    
    # 读取现有query数据
    existing_snapshots = query_manager.read_all_snapshots()
    existing_times = {s.get('snapshot_time') for s in existing_snapshots}
    print(f"📊 Query已有 {len(existing_snapshots)} 条快照记录")
    
    # 同步新数据
    new_count = 0
    for snapshot in gdrive_snapshots:
        snapshot_time = snapshot.get('snapshot_time')
        
        # 跳过已存在的
        if snapshot_time in existing_times:
            continue
        
        # 准备query格式的数据
        query_snapshot = {
            'snapshot_date': snapshot.get('snapshot_date', ''),
            'snapshot_time': snapshot_time,
            'rush_up': snapshot.get('rush_up', 0),
            'rush_down': snapshot.get('rush_down', 0),
            'diff': snapshot.get('diff', 0),
            'count': snapshot.get('count', 0),
            'ratio': snapshot.get('ratio', 0.0),
            'status': snapshot.get('status', ''),
            'round_rush_up': snapshot.get('round_rush_up', 0),
            'round_rush_down': snapshot.get('round_rush_down', 0),
            'price_lowest': snapshot.get('price_lowest', 0),
            'price_newhigh': snapshot.get('price_newhigh', 0),
            'count_score_display': snapshot.get('count_score_display', ''),
            'count_score_type': snapshot.get('count_score_type', ''),
            'rise_24h_count': snapshot.get('rise_24h_count', 0),
            'fall_24h_count': snapshot.get('fall_24h_count', 0),
            'created_at': snapshot.get('created_at')
        }
        
        # 插入新记录
        query_manager.upsert_snapshot(query_snapshot)
        new_count += 1
        
        if new_count % 100 == 0:
            print(f"  已同步 {new_count} 条新记录...")
    
    print(f"✅ 同步完成！新增 {new_count} 条快照记录")
    
    # 显示最新数据
    latest = query_manager.get_latest_snapshot()
    if latest:
        print(f"\n📊 最新数据:")
        print(f"  时间: {latest.get('snapshot_time')}")
        print(f"  急涨: {latest.get('rush_up')}, 急跌: {latest.get('rush_down')}")
        print(f"  状态: {latest.get('status')}")

def main():
    """主函数"""
    try:
        print("=" * 60)
        print("🔄 Query数据同步工具")
        print("=" * 60)
        print()
        
        sync_snapshots()
        
        print()
        print("=" * 60)
        print("✅ 同步完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
