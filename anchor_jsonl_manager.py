#!/usr/bin/env python3
"""
锚点系统 JSONL 数据管理器
- 管理所有锚点相关数据（13个表）
- 使用JSONL格式存储
- 所有时间使用北京时间
- 支持独立计算运行
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据目录
DATA_DIR = '/home/user/webapp/data/anchor_jsonl'

# 所有锚点系统的表
ANCHOR_TABLES = [
    'anchor_monitors',           # 锚点监控记录（主表）
    'anchor_positions',          # 锚点持仓
    'anchor_profit_records',     # 盈亏记录
    'anchor_alerts',             # 告警记录
    'anchor_real_monitors',      # 实盘监控
    'anchor_real_positions',     # 实盘持仓
    'anchor_real_profit_records',# 实盘盈亏记录
    'anchor_paper_monitors',     # 模拟监控
    'anchor_paper_positions',    # 模拟持仓
    'anchor_paper_profit_records', # 模拟盈亏记录
    'anchor_profit_records_backup', # 备份记录
    'extreme_corrections_log'    # 极值修正日志
]


class AnchorJSONLManager:
    """锚点系统JSONL数据管理器"""
    
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_file_path(self, table_name: str) -> str:
        """获取表的文件路径"""
        return os.path.join(self.data_dir, f"{table_name}.jsonl")
    
    def _convert_timestamp(self, timestamp_str: str) -> str:
        """转换时间戳为北京时间"""
        if not timestamp_str or timestamp_str == '-':
            return timestamp_str
        
        try:
            # 尝试解析时间字符串
            dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            # 假设原始时间是UTC，转换为北京时间
            utc_dt = pytz.utc.localize(dt)
            beijing_dt = utc_dt.astimezone(BEIJING_TZ)
            return beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return timestamp_str
    
    def read_table(self, table_name: str, limit: Optional[int] = None, 
                   order: str = 'ASC') -> List[Dict]:
        """
        读取表数据
        
        Args:
            table_name: 表名
            limit: 限制返回数量
            order: 排序方式 'ASC' 或 'DESC'
            
        Returns:
            数据记录列表
        """
        file_path = self._get_file_path(table_name)
        
        if not os.path.exists(file_path):
            return []
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        
        # 按时间排序（如果有timestamp字段）
        if records and 'timestamp' in records[0]:
            records.sort(key=lambda x: x.get('timestamp', ''), reverse=(order == 'DESC'))
        elif records and 'created_at' in records[0]:
            records.sort(key=lambda x: x.get('created_at', ''), reverse=(order == 'DESC'))
        
        # 限制数量
        if limit:
            records = records[:limit]
        
        return records
    
    def write_table(self, table_name: str, records: List[Dict]) -> None:
        """
        写入表数据（覆盖）
        
        Args:
            table_name: 表名
            records: 记录列表
        """
        file_path = self._get_file_path(table_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def append_record(self, table_name: str, record: Dict) -> None:
        """
        追加单条记录
        
        Args:
            table_name: 表名
            record: 记录数据
        """
        file_path = self._get_file_path(table_name)
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def append_records(self, table_name: str, records: List[Dict]) -> int:
        """
        追加多条记录
        
        Args:
            table_name: 表名
            records: 记录列表
            
        Returns:
            追加的记录数
        """
        if not records:
            return 0
        
        file_path = self._get_file_path(table_name)
        
        with open(file_path, 'a', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        return len(records)
    
    def get_table_stats(self, table_name: str) -> Dict:
        """获取表统计信息"""
        records = self.read_table(table_name)
        
        if not records:
            return {
                'table_name': table_name,
                'count': 0,
                'first_time': None,
                'last_time': None,
                'file_size': 0
            }
        
        file_path = self._get_file_path(table_name)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # 尝试获取时间范围
        first_time = None
        last_time = None
        
        if 'timestamp' in records[0]:
            times = sorted([r['timestamp'] for r in records if 'timestamp' in r])
            first_time = times[0] if times else None
            last_time = times[-1] if times else None
        elif 'created_at' in records[0]:
            times = sorted([r['created_at'] for r in records if 'created_at' in r])
            first_time = times[0] if times else None
            last_time = times[-1] if times else None
        
        return {
            'table_name': table_name,
            'count': len(records),
            'first_time': first_time,
            'last_time': last_time,
            'file_size': file_size
        }
    
    def get_all_tables_stats(self) -> List[Dict]:
        """获取所有表的统计信息"""
        stats_list = []
        
        for table_name in ANCHOR_TABLES:
            stats = self.get_table_stats(table_name)
            stats_list.append(stats)
        
        return stats_list
    
    def query_by_inst_id(self, table_name: str, inst_id: str, limit: int = 100) -> List[Dict]:
        """
        按币种查询
        
        Args:
            table_name: 表名
            inst_id: 币种ID（如 BTC-USDT-SWAP）
            limit: 限制数量
            
        Returns:
            匹配的记录列表
        """
        all_records = self.read_table(table_name)
        
        filtered = [r for r in all_records if r.get('inst_id') == inst_id]
        
        # 按时间降序排序
        if filtered and 'timestamp' in filtered[0]:
            filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        elif filtered and 'created_at' in filtered[0]:
            filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return filtered[:limit]
    
    def get_latest_monitors(self, limit: int = 50) -> List[Dict]:
        """获取最新的监控记录"""
        return self.read_table('anchor_monitors', limit=limit, order='DESC')
    
    def get_profit_records(self, record_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        获取盈亏记录
        
        Args:
            record_type: 记录类型（max_profit, max_loss等）
            limit: 限制数量
            
        Returns:
            盈亏记录列表
        """
        records = self.read_table('anchor_profit_records', order='DESC')
        
        if record_type:
            records = [r for r in records if r.get('record_type') == record_type]
        
        return records[:limit]
    
    def get_alerts(self, alert_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        获取告警记录
        
        Args:
            alert_type: 告警类型
            limit: 限制数量
            
        Returns:
            告警记录列表
        """
        records = self.read_table('anchor_alerts', order='DESC')
        
        if alert_type:
            records = [r for r in records if r.get('alert_type') == alert_type]
        
        return records[:limit]
    
    def backup_to_sqlite(self, db_path: str) -> int:
        """
        备份JSONL数据到SQLite（用于兼容性）
        
        Args:
            db_path: SQLite数据库路径
            
        Returns:
            备份的总记录数
        """
        import sqlite3
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        total_count = 0
        
        for table_name in ANCHOR_TABLES:
            records = self.read_table(table_name)
            
            if not records:
                continue
            
            # 创建表（简化版，只保存JSON）
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入数据
            for record in records:
                try:
                    cursor.execute(f'''
                        INSERT INTO {table_name} (data)
                        VALUES (?)
                    ''', (json.dumps(record, ensure_ascii=False),))
                    total_count += 1
                except Exception as e:
                    print(f"Error inserting into {table_name}: {e}")
        
        conn.commit()
        conn.close()
        
        return total_count


def main():
    """测试和演示"""
    manager = AnchorJSONLManager()
    
    print("锚点系统 JSONL 数据管理器测试\n")
    print("=" * 80)
    
    # 获取所有表的统计信息
    stats_list = manager.get_all_tables_stats()
    
    print(f"\n📊 表统计 (共 {len(ANCHOR_TABLES)} 个表):\n")
    print(f"{'表名':<30} {'记录数':>10} {'文件大小':>12} {'最后时间':<20}")
    print("-" * 80)
    
    total_records = 0
    total_size = 0
    
    for stats in stats_list:
        total_records += stats['count']
        total_size += stats['file_size']
        
        size_kb = stats['file_size'] / 1024 if stats['file_size'] > 0 else 0
        last_time = stats['last_time'] or 'N/A'
        
        print(f"{stats['table_name']:<30} {stats['count']:>10,} {size_kb:>10.1f} KB {last_time:<20}")
    
    print("-" * 80)
    print(f"{'总计':<30} {total_records:>10,} {total_size/1024:>10.1f} KB")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
