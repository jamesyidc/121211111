#!/usr/bin/env python3
"""
1小时爆仓金额数据管理器
存储格式: JSONL (每行一条JSON记录)
数据源: /api/panic/latest 的 hour_1_amount 字段
"""

import json
import os
from datetime import datetime
import pytz

# 北京时间
TZ = pytz.timezone('Asia/Shanghai')

class Liquidation1HManager:
    """1小时爆仓金额数据管理器"""
    
    def __init__(self, data_file=None):
        """初始化管理器
        
        Args:
            data_file: JSONL数据文件路径，默认为 data/liquidation_1h/liquidation_1h.jsonl
        """
        if data_file is None:
            data_file = '/home/user/webapp/data/liquidation_1h/liquidation_1h.jsonl'
        
        self.data_file = data_file
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        # 如果文件不存在，创建空文件
        if not os.path.exists(self.data_file):
            open(self.data_file, 'w').close()
            print(f"✅ 创建数据文件: {self.data_file}")
    
    def add_record(self, hour_1_amount, panic_index=None, hour_24_amount=None, total_position=None):
        """添加一条记录
        
        Args:
            hour_1_amount: 1小时爆仓金额（万美元）
            panic_index: 恐慌指数（可选）
            hour_24_amount: 24小时爆仓金额（可选）
            total_position: 全网持仓（可选）
        
        Returns:
            bool: 是否添加成功
        """
        try:
            now = datetime.now(TZ)
            
            record = {
                'timestamp': int(now.timestamp()),
                'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
                'hour_1_amount': round(float(hour_1_amount), 2),  # 1小时爆仓金额（万美元）
            }
            
            # 添加可选字段
            if panic_index is not None:
                record['panic_index'] = round(float(panic_index), 4)
            if hour_24_amount is not None:
                record['hour_24_amount'] = round(float(hour_24_amount), 2)
            if total_position is not None:
                record['total_position'] = round(float(total_position), 2)
            
            # 写入文件
            with open(self.data_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            print(f"✅ 记录已保存: {record['datetime']}, 1小时爆仓: {record['hour_1_amount']}万美元")
            return True
            
        except Exception as e:
            print(f"❌ 添加记录失败: {e}")
            return False
    
    def get_latest(self, limit=1):
        """获取最新的N条记录
        
        Args:
            limit: 返回记录数量
        
        Returns:
            list: 记录列表，按时间倒序
        """
        try:
            if not os.path.exists(self.data_file):
                return []
            
            records = []
            with open(self.data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError:
                            continue
            
            # 按时间倒序排序
            records.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            return records[:limit]
            
        except Exception as e:
            print(f"❌ 读取记录失败: {e}")
            return []
    
    def get_range(self, start_time=None, end_time=None, limit=None):
        """获取指定时间范围的记录
        
        Args:
            start_time: 开始时间（时间戳或datetime字符串）
            end_time: 结束时间（时间戳或datetime字符串）
            limit: 最大返回数量
        
        Returns:
            list: 记录列表，按时间正序
        """
        try:
            if not os.path.exists(self.data_file):
                return []
            
            # 转换时间为时间戳
            if isinstance(start_time, str):
                start_time = int(datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=TZ).timestamp())
            if isinstance(end_time, str):
                end_time = int(datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=TZ).timestamp())
            
            records = []
            with open(self.data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            timestamp = record.get('timestamp', 0)
                            
                            # 时间范围过滤
                            if start_time and timestamp < start_time:
                                continue
                            if end_time and timestamp > end_time:
                                continue
                            
                            records.append(record)
                        except json.JSONDecodeError:
                            continue
            
            # 按时间正序排序
            records.sort(key=lambda x: x.get('timestamp', 0))
            
            # 限制返回数量
            if limit and len(records) > limit:
                records = records[-limit:]  # 返回最新的N条
            
            return records
            
        except Exception as e:
            print(f"❌ 读取范围记录失败: {e}")
            return []
    
    def get_count(self):
        """获取总记录数"""
        try:
            if not os.path.exists(self.data_file):
                return 0
            
            count = 0
            with open(self.data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        count += 1
            return count
            
        except Exception as e:
            print(f"❌ 统计记录数失败: {e}")
            return 0


if __name__ == '__main__':
    # 测试代码
    manager = Liquidation1HManager()
    
    # 测试添加记录
    print("\n=== 测试添加记录 ===")
    manager.add_record(
        hour_1_amount=397.14,
        panic_index=0.0761,
        hour_24_amount=13583.0,
        total_position=104.72
    )
    
    # 测试获取最新记录
    print("\n=== 测试获取最新记录 ===")
    latest = manager.get_latest(limit=5)
    for record in latest:
        print(f"  {record['datetime']}: {record['hour_1_amount']}万美元")
    
    # 测试统计
    print(f"\n=== 总记录数: {manager.get_count()} ===")
