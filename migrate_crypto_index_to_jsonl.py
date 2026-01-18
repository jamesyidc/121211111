#!/usr/bin/env python3
"""
将Crypto Index页面从SQLite迁移到JSONL数据源
"""

import sys
sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')

from gdrive_jsonl_manager import GDriveJSONLManager
from datetime import datetime, timedelta
import pytz

def get_crypto_index_history_from_jsonl(hours=12):
    """从JSONL获取加密货币指数历史数据"""
    manager = GDriveJSONLManager()
    beijing_tz = pytz.timezone('Asia/Shanghai')
    
    # 获取指定时间范围的快照
    end_time = datetime.now(beijing_tz)
    start_time = end_time - timedelta(hours=hours)
    
    start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
    
    snapshots = manager.get_snapshots_by_time_range(start_str, end_str)
    
    print(f"获取到 {len(snapshots)} 条快照数据")
    print(f"时间范围: {start_str} ~ {end_str}")
    
    if snapshots:
        print(f"\n最早: {snapshots[0].get('snapshot_time')}")
        print(f"最新: {snapshots[-1].get('snapshot_time')}")
        print(f"\n示例数据:")
        print(f"  急涨: {snapshots[-1].get('rush_up')}")
        print(f"  急跌: {snapshots[-1].get('rush_down')}")
        print(f"  计次: {snapshots[-1].get('count')}")
    
    return snapshots

if __name__ == '__main__':
    print("=" * 60)
    print("测试从JSONL获取Crypto Index数据")
    print("=" * 60)
    
    # 测试获取最近12小时数据
    data = get_crypto_index_history_from_jsonl(hours=12)
    print(f"\n✅ 成功获取 {len(data)} 条数据")
