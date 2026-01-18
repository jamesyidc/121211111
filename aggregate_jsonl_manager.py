"""
聚合数据JSONL管理器
用于存储和读取透明标签聚合数据
"""
import json
import os
from datetime import datetime

class AggregateJSONLManager:
    """管理聚合数据的JSONL文件"""
    
    def __init__(self, data_dir='/home/user/webapp/data/gdrive_jsonl'):
        self.data_dir = data_dir
        self.jsonl_file = os.path.join(data_dir, 'crypto_aggregate.jsonl')
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
    
    def save_aggregate(self, aggregate_data):
        """
        保存或更新聚合数据
        
        参数:
        - aggregate_data: 字典，必须包含snapshot_time字段
        """
        if 'snapshot_time' not in aggregate_data:
            raise ValueError("aggregate_data必须包含snapshot_time字段")
        
        snapshot_time = aggregate_data['snapshot_time']
        
        # 读取现有数据
        existing_data = {}
        if os.path.exists(self.jsonl_file):
            with open(self.jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        existing_data[record['snapshot_time']] = record
        
        # 更新或添加新数据
        existing_data[snapshot_time] = aggregate_data
        
        # 写回文件（按时间排序）
        sorted_times = sorted(existing_data.keys())
        with open(self.jsonl_file, 'w', encoding='utf-8') as f:
            for time in sorted_times:
                f.write(json.dumps(existing_data[time], ensure_ascii=False) + '\n')
    
    def get_latest_aggregate(self):
        """
        获取最新的聚合数据
        
        返回:
        - 聚合数据字典，如果没有数据则返回None
        """
        if not os.path.exists(self.jsonl_file):
            return None
        
        latest_record = None
        latest_time = None
        
        with open(self.jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    record_time = record.get('snapshot_time', '')
                    
                    if latest_time is None or record_time > latest_time:
                        latest_time = record_time
                        latest_record = record
        
        return latest_record
    
    def get_aggregate_by_time(self, snapshot_time):
        """
        根据时间获取聚合数据
        
        参数:
        - snapshot_time: 快照时间字符串
        
        返回:
        - 聚合数据字典，如果没有找到则返回None
        """
        if not os.path.exists(self.jsonl_file):
            return None
        
        with open(self.jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record.get('snapshot_time') == snapshot_time:
                        return record
        
        return None
    
    def load_all_aggregates(self):
        """
        加载所有聚合数据
        
        返回:
        - 聚合数据列表，按时间排序
        """
        if not os.path.exists(self.jsonl_file):
            return []
        
        aggregates = []
        with open(self.jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    aggregates.append(record)
        
        # 按时间排序
        aggregates.sort(key=lambda x: x.get('snapshot_time', ''))
        
        return aggregates

if __name__ == "__main__":
    # 测试代码
    manager = AggregateJSONLManager('/tmp/test_aggregate')
    
    # 测试保存
    test_data1 = {
        'snapshot_time': '2026-01-14 22:00:00',
        'rush_up_total': 14,
        'rush_down_total': 18,
        'diff_total': -4,
        'ratio': 0.29,
        'status': '震荡无序',
        'count_aggregate': 3,
        'price_lowest': 0,
        'price_newhigh': 1
    }
    
    test_data2 = {
        'snapshot_time': '2026-01-14 22:10:00',
        'rush_up_total': 20,
        'rush_down_total': 10,
        'diff_total': 10,
        'ratio': 2.0,
        'status': '温和上涨',
        'count_aggregate': 5,
        'price_lowest': 1,
        'price_newhigh': 2
    }
    
    print("=== 保存聚合数据 ===")
    manager.save_aggregate(test_data1)
    manager.save_aggregate(test_data2)
    print("✅ 保存成功")
    
    print("\n=== 获取最新聚合数据 ===")
    latest = manager.get_latest_aggregate()
    if latest:
        print(f"时间: {latest['snapshot_time']}")
        print(f"急涨: {latest['rush_up_total']}, 急跌: {latest['rush_down_total']}")
        print(f"状态: {latest['status']}")
    
    print("\n=== 根据时间获取聚合数据 ===")
    specific = manager.get_aggregate_by_time('2026-01-14 22:00:00')
    if specific:
        print(f"找到数据: {specific['status']}")
    
    print("\n=== 加载所有聚合数据 ===")
    all_data = manager.load_all_aggregates()
    print(f"总共 {len(all_data)} 条记录")
    for data in all_data:
        print(f"  {data['snapshot_time']}: {data['status']}")
