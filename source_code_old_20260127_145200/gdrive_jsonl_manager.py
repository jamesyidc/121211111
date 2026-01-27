#!/usr/bin/env python3
"""
Google Drive 数据 JSONL 管理器
负责读写加密货币快照数据到JSONL文件
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import shutil

class GDriveJSONLManager:
    """Google Drive数据JSONL管理器"""
    
    def __init__(self, data_dir='/home/user/webapp/data/gdrive_jsonl'):
        """初始化管理器
        
        Args:
            data_dir: JSONL数据目录
        """
        self.data_dir = data_dir
        self.snapshots_file = os.path.join(data_dir, 'crypto_snapshots.jsonl')
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
    
    def read_all_snapshots(self) -> List[Dict]:
        """读取所有快照记录
        
        Returns:
            List[Dict]: 快照记录列表
        """
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
    
    def write_all_snapshots(self, records: List[Dict], backup=True):
        """写入所有快照记录（覆盖模式）
        
        Args:
            records: 快照记录列表
            backup: 是否备份旧文件
        """
        try:
            # 备份旧文件
            if backup and os.path.exists(self.snapshots_file):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"{self.snapshots_file}.backup_{timestamp}"
                shutil.copy2(self.snapshots_file, backup_file)
                print(f"💾 已备份到: {backup_file}")
            
            # 写入新数据
            with open(self.snapshots_file, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            print(f"✅ 已写入 {len(records)} 条记录到JSONL")
        except Exception as e:
            print(f"❌ 写入快照失败: {e}")
            raise
    
    def append_snapshots(self, records: List[Dict]):
        """追加快照记录
        
        Args:
            records: 要追加的记录列表
        """
        try:
            with open(self.snapshots_file, 'a', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            print(f"✅ 已追加 {len(records)} 条记录到JSONL")
        except Exception as e:
            print(f"❌ 追加快照失败: {e}")
            raise
    
    def get_snapshots_by_date(self, snapshot_date: str) -> List[Dict]:
        """获取指定日期的快照
        
        Args:
            snapshot_date: 日期字符串，格式: YYYY-MM-DD
            
        Returns:
            List[Dict]: 快照记录列表
        """
        all_records = self.read_all_snapshots()
        return [r for r in all_records if r.get('snapshot_date') == snapshot_date]
    
    def get_snapshots_by_time(self, snapshot_time: str) -> List[Dict]:
        """获取指定时间的快照
        
        Args:
            snapshot_time: 时间字符串，格式: YYYY-MM-DD HH:MM:SS
            
        Returns:
            List[Dict]: 快照记录列表
        """
        all_records = self.read_all_snapshots()
        return [r for r in all_records if r.get('snapshot_time') == snapshot_time]
    
    def get_latest_snapshot_time(self) -> Optional[str]:
        """获取最新快照时间
        
        Returns:
            Optional[str]: 最新快照时间字符串，如果没有数据返回None
        """
        all_records = self.read_all_snapshots()
        if not all_records:
            return None
        
        # 按snapshot_time降序排序
        sorted_records = sorted(all_records, key=lambda x: x.get('snapshot_time', ''), reverse=True)
        return sorted_records[0].get('snapshot_time') if sorted_records else None
    
    def get_snapshot_by_inst_id_and_time(self, inst_id: str, snapshot_time: str) -> Optional[Dict]:
        """获取指定币种和时间的快照
        
        Args:
            inst_id: 币种ID
            snapshot_time: 时间字符串
            
        Returns:
            Optional[Dict]: 快照记录，如果不存在返回None
        """
        all_records = self.read_all_snapshots()
        for record in all_records:
            if record.get('inst_id') == inst_id and record.get('snapshot_time') == snapshot_time:
                return record
        return None
    
    def upsert_snapshots(self, records: List[Dict]):
        """更新或插入快照记录（基于inst_id和snapshot_time唯一性）
        
        Args:
            records: 要更新或插入的记录列表
        """
        try:
            # 读取所有现有记录
            all_records = self.read_all_snapshots()
            
            # 创建索引: (inst_id, snapshot_time) -> record
            existing_map = {
                (r.get('inst_id'), r.get('snapshot_time')): i
                for i, r in enumerate(all_records)
            }
            
            # 更新或追加
            for new_record in records:
                key = (new_record.get('inst_id'), new_record.get('snapshot_time'))
                if key in existing_map:
                    # 更新现有记录
                    idx = existing_map[key]
                    all_records[idx] = new_record
                else:
                    # 追加新记录
                    all_records.append(new_record)
            
            # 写回文件（禁用备份以节省空间）
            self.write_all_snapshots(all_records, backup=False)
        except Exception as e:
            print(f"❌ Upsert快照失败: {e}")
            raise
    
    def delete_old_snapshots(self, days_to_keep: int = 30):
        """删除旧快照数据
        
        Args:
            days_to_keep: 保留最近几天的数据
        """
        from datetime import timedelta
        
        try:
            all_records = self.read_all_snapshots()
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            
            # 过滤保留的记录
            kept_records = [r for r in all_records if r.get('snapshot_date', '') >= cutoff_date]
            deleted_count = len(all_records) - len(kept_records)
            
            if deleted_count > 0:
                self.write_all_snapshots(kept_records, backup=False)
                print(f"🗑️ 已删除 {deleted_count} 条旧记录（保留 {days_to_keep} 天）")
            else:
                print(f"✅ 无需删除，所有记录都在 {days_to_keep} 天内")
        except Exception as e:
            print(f"❌ 删除旧快照失败: {e}")
            raise
    
    def get_statistics(self) -> Dict:
        """获取数据统计信息
        
        Returns:
            Dict: 包含各项统计信息的字典
        """
        all_records = self.read_all_snapshots()
        
        if not all_records:
            return {
                'total_records': 0,
                'unique_dates': 0,
                'unique_times': 0,
                'unique_inst_ids': 0,
                'latest_snapshot_time': None,
                'oldest_snapshot_time': None
            }
        
        dates = set(r.get('snapshot_date') for r in all_records if r.get('snapshot_date'))
        times = set(r.get('snapshot_time') for r in all_records if r.get('snapshot_time'))
        inst_ids = set(r.get('inst_id') for r in all_records if r.get('inst_id'))
        
        sorted_times = sorted([r.get('snapshot_time', '') for r in all_records if r.get('snapshot_time')])
        
        return {
            'total_records': len(all_records),
            'unique_dates': len(dates),
            'unique_times': len(times),
            'unique_inst_ids': len(inst_ids),
            'latest_snapshot_time': sorted_times[-1] if sorted_times else None,
            'oldest_snapshot_time': sorted_times[0] if sorted_times else None
        }


if __name__ == '__main__':
    # 测试代码
    manager = GDriveJSONLManager()
    stats = manager.get_statistics()
    print(f"📊 数据统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
