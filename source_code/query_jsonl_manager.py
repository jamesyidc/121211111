#!/usr/bin/env python3
"""
Query数据JSONL管理器
管理快照数据和币种详情数据
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import shutil

class QueryJSONLManager:
    """Query数据JSONL管理器"""
    
    def __init__(self, data_dir='/home/user/webapp/data/query_jsonl'):
        """初始化管理器"""
        self.data_dir = data_dir
        self.snapshots_file = os.path.join(data_dir, 'snapshots.jsonl')
        self.coins_file = os.path.join(data_dir, 'coins.jsonl')
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
    
    def calculate_priority(self, ratio1: float, ratio2: float) -> int:
        """计算优先级
        
        等级1: ratio1 > 90  且 ratio2 > 120
        等级2: ratio1 > 80  且 ratio2 > 120
        等级3: ratio1 > 90  且 ratio2 > 110
        等级4: ratio1 > 70  且 ratio2 > 120
        等级5: ratio1 > 80  且 ratio2 > 110
        等级6: ratio1 < 80  且 ratio2 < 110
        
        Args:
            ratio1: 最高占比
            ratio2: 最低占比
        
        Returns:
            int: 优先级 (1-6)
        """
        if ratio1 > 90 and ratio2 > 120:
            return 1
        elif ratio1 > 80 and ratio2 > 120:
            return 2
        elif ratio1 > 90 and ratio2 > 110:
            return 3
        elif ratio1 > 70 and ratio2 > 120:
            return 4
        elif ratio1 > 80 and ratio2 > 110:
            return 5
        else:
            return 6
    
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
    
    def read_all_coins(self) -> List[Dict]:
        """读取所有币种记录"""
        if not os.path.exists(self.coins_file):
            return []
        
        records = []
        try:
            with open(self.coins_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            print(f"❌ 读取币种失败: {e}")
            return []
        
        return records
    
    def write_snapshots(self, records: List[Dict], backup=True):
        """写入快照记录"""
        try:
            if backup and os.path.exists(self.snapshots_file):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"{self.snapshots_file}.backup_{timestamp}"
                shutil.copy2(self.snapshots_file, backup_file)
            
            with open(self.snapshots_file, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            print(f"✅ 已写入 {len(records)} 条快照记录")
        except Exception as e:
            print(f"❌ 写入快照失败: {e}")
            raise
    
    def write_coins(self, records: List[Dict], backup=True):
        """写入币种记录"""
        try:
            if backup and os.path.exists(self.coins_file):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"{self.coins_file}.backup_{timestamp}"
                shutil.copy2(self.coins_file, backup_file)
            
            with open(self.coins_file, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            print(f"✅ 已写入 {len(records)} 条币种记录")
        except Exception as e:
            print(f"❌ 写入币种失败: {e}")
            raise
    
    def get_snapshot_by_time(self, snapshot_time: str) -> Optional[Dict]:
        """根据时间获取快照"""
        all_snapshots = self.read_all_snapshots()
        for snapshot in all_snapshots:
            if snapshot.get('snapshot_time', '').startswith(snapshot_time):
                return snapshot
        return None
    
    def get_coins_by_time(self, snapshot_time: str) -> List[Dict]:
        """根据时间获取币种列表"""
        all_coins = self.read_all_coins()
        return [c for c in all_coins if c.get('snapshot_time') == snapshot_time]
    
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
    
    def upsert_coins(self, coins: List[Dict], snapshot_time: str):
        """更新或插入币种列表（删除旧的，插入新的）"""
        all_coins = self.read_all_coins()
        
        # 删除该时间点的旧币种数据
        all_coins = [c for c in all_coins if c.get('snapshot_time') != snapshot_time]
        
        # 添加新币种数据
        all_coins.extend(coins)
        
        # 按时间降序、序号升序排序
        all_coins.sort(key=lambda x: (
            x.get('snapshot_time', ''),
            x.get('index_order', 999)
        ), reverse=True)
        
        self.write_coins(all_coins, backup=True)
    
    def get_latest_snapshot_time(self) -> Optional[str]:
        """获取最新快照时间"""
        all_snapshots = self.read_all_snapshots()
        if not all_snapshots:
            return None
        
        sorted_snapshots = sorted(all_snapshots, key=lambda x: x.get('snapshot_time', ''), reverse=True)
        return sorted_snapshots[0].get('snapshot_time') if sorted_snapshots else None
    
    def get_latest_snapshot(self) -> Optional[Dict]:
        """获取最新快照记录"""
        all_snapshots = self.read_all_snapshots()
        if not all_snapshots:
            return None
        
        sorted_snapshots = sorted(all_snapshots, key=lambda x: x.get('snapshot_time', ''), reverse=True)
        return sorted_snapshots[0] if sorted_snapshots else None
    
    def upsert_coin(self, coin: Dict):
        """更新或插入单个币种（便捷方法）"""
        snapshot_time = coin.get('snapshot_time')
        if not snapshot_time:
            raise ValueError("币种数据缺少snapshot_time字段")
        
        # 读取所有币种
        all_coins = self.read_all_coins()
        
        # 查找是否存在同一时间点、同一币种的记录
        found = False
        for i, c in enumerate(all_coins):
            if (c.get('snapshot_time') == snapshot_time and 
                c.get('symbol') == coin.get('symbol')):
                all_coins[i] = coin
                found = True
                break
        
        if not found:
            all_coins.append(coin)
        
        # 排序
        all_coins.sort(key=lambda x: (
            x.get('snapshot_time', ''),
            x.get('index_order', 999)
        ), reverse=True)
        
        self.write_coins(all_coins, backup=True)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        snapshots = self.read_all_snapshots()
        coins = self.read_all_coins()
        
        if not snapshots:
            return {
                'total_snapshots': 0,
                'total_coins': 0,
                'latest_time': None,
                'unique_times': 0
            }
        
        times = set(s.get('snapshot_time') for s in snapshots)
        sorted_times = sorted(times, reverse=True)
        
        return {
            'total_snapshots': len(snapshots),
            'total_coins': len(coins),
            'latest_time': sorted_times[0] if sorted_times else None,
            'unique_times': len(times)
        }


if __name__ == '__main__':
    # 测试代码
    manager = QueryJSONLManager()
    stats = manager.get_statistics()
    print(f"📊 数据统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
