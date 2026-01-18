#!/usr/bin/env python3
"""
历史极值 JSONL 管理器
功能：
1. 管理历史极值记录（JSONL格式）
2. 添加、更新、删除极值记录
3. 查询极值记录
4. 支持实盘和模拟盘分离
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class ExtremeJSONLManager:
    """历史极值JSONL管理器"""
    
    def __init__(self, trade_mode: str = 'real'):
        """
        初始化管理器
        
        Args:
            trade_mode: 交易模式，'real'(实盘) 或 'paper'(模拟盘)
        """
        self.trade_mode = trade_mode
        self.data_dir = 'data/extreme_jsonl'
        self.file_path = os.path.join(self.data_dir, f'extreme_{trade_mode}.jsonl')
        
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 确保文件存在
        if not os.path.exists(self.file_path):
            open(self.file_path, 'w').close()
    
    def add_record(self, record: Dict) -> bool:
        """
        添加一条极值记录
        
        Args:
            record: 记录字典，包含inst_id, pos_side, record_type, profit_rate等字段
        
        Returns:
            是否成功
        """
        try:
            # 补充必要字段
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            if 'created_at' not in record:
                record['created_at'] = now
            if 'updated_at' not in record:
                record['updated_at'] = now
            
            # 追加到文件
            with open(self.file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
        except Exception as e:
            print(f"添加记录失败: {e}")
            return False
    
    def get_all_records(self) -> List[Dict]:
        """
        获取所有极值记录
        
        Returns:
            记录列表
        """
        records = []
        try:
            if not os.path.exists(self.file_path):
                return records
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"读取记录失败: {e}")
        
        return records
    
    def get_latest_records(self, limit: int = 50) -> List[Dict]:
        """
        获取最新的N条记录
        
        Args:
            limit: 返回记录数量
        
        Returns:
            记录列表（按created_at降序）
        """
        records = self.get_all_records()
        
        # 按created_at降序排序
        records.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return records[:limit]
    
    def get_records_by_symbol(self, inst_id: str) -> List[Dict]:
        """
        获取指定币种的所有极值记录
        
        Args:
            inst_id: 合约ID，如 'BTC-USDT-SWAP'
        
        Returns:
            记录列表
        """
        all_records = self.get_all_records()
        return [r for r in all_records if r.get('inst_id') == inst_id]
    
    def get_extreme_for_position(self, inst_id: str, pos_side: str, record_type: str) -> Optional[Dict]:
        """
        获取指定币种、方向、类型的极值记录
        
        Args:
            inst_id: 合约ID
            pos_side: 持仓方向 'long' 或 'short'
            record_type: 记录类型，如 'highest_profit', 'most_loss'
        
        Returns:
            极值记录，如果不存在返回None
        """
        records = self.get_records_by_symbol(inst_id)
        
        for record in reversed(records):  # 从最新往旧找
            if (record.get('pos_side') == pos_side and 
                record.get('record_type') == record_type):
                return record
        
        return None
    
    def update_extreme(self, inst_id: str, pos_side: str, record_type: str, 
                      new_record: Dict) -> bool:
        """
        更新极值记录（如果新值超过旧值）
        
        Args:
            inst_id: 合约ID
            pos_side: 持仓方向
            record_type: 记录类型
            new_record: 新记录
        
        Returns:
            是否更新
        """
        old_record = self.get_extreme_for_position(inst_id, pos_side, record_type)
        
        new_profit_rate = new_record.get('profit_rate', 0)
        
        # 判断是否需要更新
        should_update = False
        if old_record is None:
            should_update = True
        else:
            old_profit_rate = old_record.get('profit_rate', 0)
            
            if record_type in ['highest_profit', 'max_profit']:
                # 最高盈利：新值更大则更新
                should_update = new_profit_rate > old_profit_rate
            elif record_type in ['most_loss', 'max_loss']:
                # 最大亏损：新值更小（更负）则更新
                should_update = new_profit_rate < old_profit_rate
        
        if should_update:
            # 添加新记录
            return self.add_record(new_record)
        
        return False
    
    def delete_records_by_symbol(self, inst_id: str, pos_side: Optional[str] = None) -> int:
        """
        删除指定币种的极值记录
        
        Args:
            inst_id: 合约ID
            pos_side: 持仓方向（可选），如果不指定则删除所有方向
        
        Returns:
            删除的记录数
        """
        all_records = self.get_all_records()
        filtered_records = []
        deleted_count = 0
        
        for record in all_records:
            if record.get('inst_id') == inst_id:
                if pos_side is None or record.get('pos_side') == pos_side:
                    deleted_count += 1
                    continue
            filtered_records.append(record)
        
        # 重写文件
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                for record in filtered_records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            return deleted_count
        except Exception as e:
            print(f"删除记录失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        records = self.get_all_records()
        
        # 按币种统计
        symbols = {}
        for record in records:
            inst_id = record.get('inst_id', '')
            if inst_id not in symbols:
                symbols[inst_id] = {'long': 0, 'short': 0}
            
            pos_side = record.get('pos_side', '')
            if pos_side in ['long', 'short']:
                symbols[inst_id][pos_side] += 1
        
        return {
            'total_records': len(records),
            'total_symbols': len(symbols),
            'symbols': symbols,
            'trade_mode': self.trade_mode,
            'file_path': self.file_path,
            'file_size_mb': round(os.path.getsize(self.file_path) / 1024 / 1024, 2) if os.path.exists(self.file_path) else 0
        }


# 测试代码
if __name__ == '__main__':
    # 测试实盘管理器
    manager = ExtremeJSONLManager('real')
    
    print("测试历史极值JSONL管理器")
    print("=" * 80)
    
    # 测试添加记录
    test_record = {
        'inst_id': 'BTC-USDT-SWAP',
        'pos_side': 'long',
        'record_type': 'highest_profit',
        'profit_rate': 0.1234,
        'pos_size': 10,
        'avg_price': 92000,
        'mark_price': 93234,
        'upl': 12340,
        'margin': 10000,
        'leverage': 10
    }
    
    print(f"\n添加测试记录...")
    result = manager.add_record(test_record)
    print(f"结果: {'成功' if result else '失败'}")
    
    # 获取统计信息
    print(f"\n统计信息:")
    stats = manager.get_statistics()
    for key, value in stats.items():
        if key != 'symbols':
            print(f"  {key}: {value}")
    
    # 获取最新记录
    print(f"\n最新5条记录:")
    latest = manager.get_latest_records(5)
    for i, record in enumerate(latest, 1):
        print(f"  [{i}] {record.get('inst_id')} {record.get('pos_side')} "
              f"收益率: {record.get('profit_rate', 0):.2%}")

