#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页数据监控JSONL管理器
管理从TXT文件提取的透明标签数据
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import shutil

class DashboardJSONLManager:
    """首页监控数据JSONL管理器"""
    
    def __init__(self, data_dir='/home/user/webapp/data/dashboard_jsonl'):
        """初始化管理器"""
        self.data_dir = data_dir
        self.snapshots_file = os.path.join(data_dir, 'dashboard_snapshots.jsonl')
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
    
    def read_all_snapshots(self) -> List[Dict]:
        """读取所有快照记录"""
        if not os.path.exists(self.snapshots_file):
            return []
        
        records = []
        try:
            with open(self.snapshots_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            print(f"❌ 读取快照失败: {e}")
            return []
        
        return records
    
    def write_snapshots(self, records: List[Dict], backup=True):
        """写入快照记录"""
        try:
            if backup and os.path.exists(self.snapshots_file):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"{self.snapshots_file}.backup_{timestamp}"
                shutil.copy2(self.snapshots_file, backup_file)
                print(f"✅ 已备份到: {backup_file}")
            
            with open(self.snapshots_file, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            print(f"✅ 已写入 {len(records)} 条快照记录")
        except Exception as e:
            print(f"❌ 写入快照失败: {e}")
            raise
    
    def upsert_snapshot(self, snapshot: Dict):
        """更新或插入快照（基于snapshot_time唯一性）"""
        all_snapshots = self.read_all_snapshots()
        
        # 查找是否存在
        found = False
        for i, s in enumerate(all_snapshots):
            if s.get('snapshot_time') == snapshot.get('snapshot_time'):
                all_snapshots[i] = snapshot
                found = True
                break
        
        if not found:
            all_snapshots.append(snapshot)
        
        # 按时间降序排序
        all_snapshots.sort(key=lambda x: x.get('snapshot_time', ''), reverse=True)
        
        self.write_snapshots(all_snapshots, backup=True)
    
    def get_latest_snapshot(self) -> Optional[Dict]:
        """获取最新快照记录"""
        all_snapshots = self.read_all_snapshots()
        if not all_snapshots:
            return None
        
        sorted_snapshots = sorted(all_snapshots, key=lambda x: x.get('snapshot_time', ''), reverse=True)
        return sorted_snapshots[0] if sorted_snapshots else None
    
    def get_snapshot_by_time(self, snapshot_time: str) -> Optional[Dict]:
        """根据时间获取快照"""
        all_snapshots = self.read_all_snapshots()
        for snapshot in all_snapshots:
            if snapshot.get('snapshot_time', '').startswith(snapshot_time):
                return snapshot
        return None
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        snapshots = self.read_all_snapshots()
        
        if not snapshots:
            return {
                'total_snapshots': 0,
                'latest_time': None,
                'unique_times': 0
            }
        
        times = set(s.get('snapshot_time') for s in snapshots)
        sorted_times = sorted(times, reverse=True)
        
        return {
            'total_snapshots': len(snapshots),
            'latest_time': sorted_times[0] if sorted_times else None,
            'unique_times': len(times)
        }


if __name__ == '__main__':
    # 测试代码
    manager = DashboardJSONLManager()
    stats = manager.get_statistics()
    print(f"📊 数据统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
