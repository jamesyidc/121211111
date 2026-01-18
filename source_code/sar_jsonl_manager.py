#!/usr/bin/env python3
"""
SAR JSONL数据管理器
负责读写SAR K线数据的JSONL文件
每个币种一个独立的JSONL文件
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import subprocess


class SARJSONLManager:
    """SAR JSONL文件管理器"""
    
    def __init__(self, symbol: str):
        """
        初始化管理器
        
        Args:
            symbol: 币种符号，如 'AAVE', 'BTC' 等
        """
        self.symbol = symbol.upper()
        self.base_dir = '/home/user/webapp/data/sar_jsonl'
        self.jsonl_path = os.path.join(self.base_dir, f'{self.symbol}.jsonl')
        
        # 确保目录存在
        os.makedirs(self.base_dir, exist_ok=True)
        
        # 确保文件存在
        if not os.path.exists(self.jsonl_path):
            # 创建空文件
            open(self.jsonl_path, 'a').close()
    
    def append_record(self, data: Dict) -> bool:
        """
        追加一条记录到JSONL文件
        
        Args:
            data: 包含SAR数据的字典，必须包含以下字段：
                - symbol: 币种符号
                - timestamp: 时间戳(毫秒)
                - beijing_time: 北京时间字符串
                - open, high, low, close: OHLC数据
                - sar: SAR值
                - position: 'long' 或 'short'
                - sequence: 序列号
                - duration_minutes: 持续时间(分钟)
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 确保symbol匹配
            data['symbol'] = self.symbol
            
            # 写入文件
            with open(self.jsonl_path, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
            
            return True
        except Exception as e:
            print(f"❌ 写入JSONL失败: {e}")
            return False
    
    def read_records(self, limit: Optional[int] = None, reverse: bool = False) -> List[Dict]:
        """
        读取JSONL记录
        
        Args:
            limit: 限制返回的记录数，None表示返回所有
            reverse: 是否反向读取(从最新到最旧)，默认False(从最旧到最新)
        
        Returns:
            记录列表
        """
        try:
            if not os.path.exists(self.jsonl_path):
                return []
            
            records = []
            
            if reverse and limit:
                # 使用tail命令高效读取最后N行
                result = subprocess.run(
                    ['tail', '-n', str(limit), self.jsonl_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                lines = result.stdout.strip().split('\n')
                # tail返回的已经是最新的N条，按时间正序（最旧→最新）
                # reverse=True表示要返回最新的在前，所以需要反转
                lines.reverse()
            elif reverse:
                # 读取所有行并反转
                with open(self.jsonl_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                lines.reverse()
                if limit:
                    lines = lines[:limit]
            else:
                # 正序读取
                with open(self.jsonl_path, 'r', encoding='utf-8') as f:
                    if limit:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= limit:
                                break
                            lines.append(line)
                    else:
                        lines = f.readlines()
            
            # 解析JSON
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            return records
        
        except Exception as e:
            print(f"❌ 读取JSONL失败: {e}")
            return []
    
    def get_latest_record(self) -> Optional[Dict]:
        """
        获取最新的一条记录
        
        Returns:
            最新记录，如果文件为空则返回None
        """
        try:
            if not os.path.exists(self.jsonl_path):
                return None
            
            # 使用tail命令获取最后一行
            result = subprocess.run(
                ['tail', '-1', self.jsonl_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            line = result.stdout.strip()
            if line:
                return json.loads(line)
            return None
        
        except Exception as e:
            print(f"❌ 获取最新记录失败: {e}")
            return None
    
    def get_latest_status(self) -> Dict:
        """
        获取最新状态信息
        
        Returns:
            包含以下字段的字典：
            - current_position: 当前仓位 ('long' 或 'short')
            - current_sequence: 当前序列号
            - last_update_time: 最后更新时间
            - latest_price: 最新价格
            - latest_sar: 最新SAR值
        """
        latest = self.get_latest_record()
        
        if not latest:
            return {
                'current_position': None,
                'current_sequence': 0,
                'last_update_time': None,
                'latest_price': None,
                'latest_sar': None
            }
        
        return {
            'current_position': latest.get('position'),
            'current_sequence': latest.get('sequence', 0),
            'last_update_time': latest.get('beijing_time'),
            'latest_price': latest.get('close'),
            'latest_sar': latest.get('sar')
        }
    
    def get_records_count(self) -> int:
        """
        获取记录总数
        
        Returns:
            记录数量
        """
        try:
            if not os.path.exists(self.jsonl_path):
                return 0
            
            result = subprocess.run(
                ['wc', '-l', self.jsonl_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            count = int(result.stdout.split()[0])
            return count
        
        except Exception as e:
            print(f"❌ 统计记录数失败: {e}")
            return 0
    
    def get_file_size_mb(self) -> float:
        """
        获取文件大小(MB)
        
        Returns:
            文件大小
        """
        try:
            if not os.path.exists(self.jsonl_path):
                return 0.0
            
            size_bytes = os.path.getsize(self.jsonl_path)
            return size_bytes / (1024 * 1024)
        
        except Exception as e:
            print(f"❌ 获取文件大小失败: {e}")
            return 0.0
    
    def get_time_range(self) -> Dict:
        """
        获取数据的时间范围
        
        Returns:
            包含start_time和end_time的字典
        """
        try:
            if not os.path.exists(self.jsonl_path):
                return {'start_time': None, 'end_time': None}
            
            # 获取第一条记录
            with open(self.jsonl_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            
            if not first_line:
                return {'start_time': None, 'end_time': None}
            
            first_record = json.loads(first_line)
            
            # 获取最后一条记录
            result = subprocess.run(
                ['tail', '-1', self.jsonl_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            last_line = result.stdout.strip()
            if not last_line:
                return {'start_time': None, 'end_time': None}
            
            last_record = json.loads(last_line)
            
            return {
                'start_time': first_record.get('beijing_time'),
                'end_time': last_record.get('beijing_time')
            }
        
        except Exception as e:
            print(f"❌ 获取时间范围失败: {e}")
            return {'start_time': None, 'end_time': None}
    
    def get_statistics(self) -> Dict:
        """
        获取文件统计信息
        
        Returns:
            包含各种统计数据的字典
        """
        time_range = self.get_time_range()
        
        return {
            'symbol': self.symbol,
            'file_path': self.jsonl_path,
            'file_exists': os.path.exists(self.jsonl_path),
            'total_records': self.get_records_count(),
            'file_size_mb': round(self.get_file_size_mb(), 2),
            'start_time': time_range['start_time'],
            'end_time': time_range['end_time']
        }
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """
        清理超过指定天数的旧数据
        
        Args:
            days: 保留数据的天数，默认30天
        
        Returns:
            删除的记录数
        """
        try:
            if not os.path.exists(self.jsonl_path):
                return 0
            
            from datetime import datetime, timedelta
            
            # 计算截止时间
            cutoff_time = datetime.now() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_time.timestamp() * 1000)
            
            # 读取所有记录
            all_records = self.read_records()
            
            # 过滤掉旧记录
            new_records = [r for r in all_records if r.get('timestamp', 0) >= cutoff_timestamp]
            
            deleted_count = len(all_records) - len(new_records)
            
            if deleted_count > 0:
                # 重写文件
                with open(self.jsonl_path, 'w', encoding='utf-8') as f:
                    for record in new_records:
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ 清理旧数据失败: {e}")
            return 0


# 测试代码
if __name__ == '__main__':
    import sys
    
    # 测试AAVE币种
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'AAVE'
    
    print(f"=" * 80)
    print(f"测试 SAR JSONL Manager - {symbol}")
    print(f"=" * 80)
    print()
    
    manager = SARJSONLManager(symbol)
    
    # 获取统计信息
    stats = manager.get_statistics()
    print("📊 文件统计:")
    print(f"  文件路径: {stats['file_path']}")
    print(f"  文件存在: {stats['file_exists']}")
    print(f"  记录总数: {stats['total_records']:,}")
    print(f"  文件大小: {stats['file_size_mb']} MB")
    print(f"  时间范围: {stats['start_time']} ~ {stats['end_time']}")
    print()
    
    # 获取最新状态
    status = manager.get_latest_status()
    print("📈 最新状态:")
    print(f"  当前仓位: {status['current_position']}")
    print(f"  当前序列: {status['current_sequence']}")
    print(f"  最新价格: ${status['latest_price']}")
    print(f"  最新SAR: {status['latest_sar']}")
    print(f"  更新时间: {status['last_update_time']}")
    print()
    
    # 读取最新3条记录
    print("📋 最新3条记录:")
    latest_records = manager.read_records(limit=3, reverse=True)
    for i, record in enumerate(latest_records, 1):
        print(f"  {i}. {record['beijing_time']}: {record['position'].upper()} #{record['sequence']}, "
              f"Close: ${record['close']}, SAR: {record['sar']:.4f}")
    print()
    
    print("=" * 80)
    print("✅ 测试完成")
