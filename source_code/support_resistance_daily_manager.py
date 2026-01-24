#!/usr/bin/env python3
"""
支撑阻力系统 - 按日期存储管理器
每天一个JSONL文件，包含当天的所有 levels 和 snapshots 数据

文件命名: support_resistance_YYYYMMDD.jsonl
数据结构:
{
    "type": "level" | "snapshot",
    "timestamp": "2026-01-24T19:30:35+08:00",
    "date": "20260124",
    "time": "19:30:35",
    "data": { ... }  # 实际数据内容
}
"""

import os
import json
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

class SupportResistanceDailyManager:
    """支撑阻力系统按日期管理器"""
    
    def __init__(self, data_dir: str = None):
        """初始化管理器"""
        if data_dir is None:
            data_dir = '/home/user/webapp/data/support_resistance_daily'
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
    
    def get_current_date(self) -> str:
        """获取当前日期（北京时间，格式：YYYYMMDD）"""
        now = datetime.now(self.beijing_tz)
        return now.strftime('%Y%m%d')
    
    def get_current_datetime_str(self) -> tuple:
        """获取当前日期时间字符串（北京时间）"""
        now = datetime.now(self.beijing_tz)
        date_str = now.strftime('%Y%m%d')
        time_str = now.strftime('%H:%M:%S')
        timestamp = now.isoformat()
        return date_str, time_str, timestamp
    
    def get_file_path(self, date_str: str) -> Path:
        """获取指定日期的文件路径"""
        filename = f"support_resistance_{date_str}.jsonl"
        return self.data_dir / filename
    
    def write_level_record(self, level_data: Dict) -> bool:
        """
        写入支撑阻力位数据记录
        
        Args:
            level_data: 支撑阻力位数据字典，包含:
                - symbol: 币种符号
                - current_price: 当前价格
                - support_line_1/2: 支撑位
                - resistance_line_1/2: 阻力位
                - 其他计算字段
        
        Returns:
            bool: 写入成功返回True
        """
        try:
            date_str, time_str, timestamp = self.get_current_datetime_str()
            file_path = self.get_file_path(date_str)
            
            # 构建记录
            record = {
                "type": "level",
                "timestamp": timestamp,
                "date": date_str,
                "time": time_str,
                "data": level_data
            }
            
            # 追加写入JSONL
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
            
        except Exception as e:
            print(f"❌ 写入level记录失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def write_snapshot_record(self, snapshot_data: Dict) -> bool:
        """
        写入快照数据记录
        
        Args:
            snapshot_data: 快照数据字典，包含:
                - scenario_1_count/2/3/4: 4种场景的币种数量
                - scenario_1_coins/2/3/4: 4种场景的币种列表（JSON字符串或列表）
                - total_coins: 总币种数
        
        Returns:
            bool: 写入成功返回True
        """
        try:
            date_str, time_str, timestamp = self.get_current_datetime_str()
            file_path = self.get_file_path(date_str)
            
            # 构建记录
            record = {
                "type": "snapshot",
                "timestamp": timestamp,
                "date": date_str,
                "time": time_str,
                "data": snapshot_data
            }
            
            # 追加写入JSONL
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
            
        except Exception as e:
            print(f"❌ 写入snapshot记录失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def read_date_records(self, date_str: str, record_type: str = None) -> List[Dict]:
        """
        读取指定日期的记录
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            record_type: 记录类型过滤（'level'/'snapshot'/None表示全部）
        
        Returns:
            List[Dict]: 记录列表
        """
        try:
            file_path = self.get_file_path(date_str)
            
            if not file_path.exists():
                return []
            
            records = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                        
                        # 类型过滤
                        if record_type and record.get('type') != record_type:
                            continue
                        
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
            
            return records
            
        except Exception as e:
            print(f"❌ 读取日期记录失败 ({date_str}): {e}")
            return []
    
    def get_latest_levels(self, date_str: str = None, limit: int = 27, symbol: str = None) -> List[Dict]:
        """
        获取最新的支撑阻力位数据（优化版：反向读取文件）
        
        Args:
            date_str: 日期字符串（默认今天）
            limit: 返回记录数量
            symbol: 可选，只获取指定币种
        
        Returns:
            List[Dict]: level记录列表（最新的N条）
        """
        if date_str is None:
            date_str = self.get_current_date()
        
        file_path = self.get_file_path(date_str)
        
        if not os.path.exists(file_path):
            return []
        
        try:
            # 反向读取文件，避免加载整个大文件
            records = []
            buffer_size = 8192  # 8KB buffer
            
            with open(file_path, 'rb') as f:
                # 移动到文件末尾
                f.seek(0, 2)
                file_size = f.tell()
                
                # 从末尾开始读取
                position = file_size
                lines = []
                
                while position > 0 and len(records) < limit * 10:  # 读取足够的行
                    # 读取一个buffer
                    chunk_size = min(buffer_size, position)
                    position -= chunk_size
                    f.seek(position)
                    chunk = f.read(chunk_size).decode('utf-8', errors='ignore')
                    
                    # 分割成行
                    chunk_lines = chunk.split('\n')
                    lines = chunk_lines + lines
                
                # 解析最后的N行（倒序）
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    
                    try:
                        record = json.loads(line)
                        
                        # 只要level类型的记录
                        if record.get('type') != 'level':
                            continue
                        
                        # 如果指定了symbol，只返回该币种
                        if symbol:
                            data = record.get('data', {})
                            if data.get('symbol') != symbol:
                                continue
                        
                        records.append(record)
                        
                        # 达到limit就停止
                        if len(records) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            # 返回最新的记录（已经是倒序，需要再反转）
            return list(reversed(records))
            
        except Exception as e:
            print(f"❌ 反向读取文件失败 ({date_str}): {e}")
            # 回退到原始方法
            records = self.read_date_records(date_str, record_type='level')
            if symbol:
                records = [r for r in records if r.get('data', {}).get('symbol') == symbol]
            return records[-limit:] if len(records) > limit else records
    
    def get_latest_snapshot(self, date_str: str = None) -> Optional[Dict]:
        """
        获取最新的快照数据（优化版：反向读取文件）
        
        Args:
            date_str: 日期字符串（默认今天）
        
        Returns:
            Dict: snapshot记录，如果没有返回None
        """
        if date_str is None:
            date_str = self.get_current_date()
        
        file_path = self.get_file_path(date_str)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            # 反向读取文件，找到第一个snapshot
            buffer_size = 8192  # 8KB buffer
            
            with open(file_path, 'rb') as f:
                # 移动到文件末尾
                f.seek(0, 2)
                file_size = f.tell()
                
                # 从末尾开始读取
                position = file_size
                lines = []
                
                while position > 0:
                    # 读取一个buffer
                    chunk_size = min(buffer_size, position)
                    position -= chunk_size
                    f.seek(position)
                    chunk = f.read(chunk_size).decode('utf-8', errors='ignore')
                    
                    # 分割成行
                    chunk_lines = chunk.split('\n')
                    lines = chunk_lines + lines
                    
                    # 从最新的行开始检查
                    for line in reversed(lines):
                        if not line.strip():
                            continue
                        
                        try:
                            record = json.loads(line)
                            
                            # 找到snapshot就返回
                            if record.get('type') == 'snapshot':
                                return record
                                
                        except json.JSONDecodeError:
                            continue
                    
                    # 如果已经检查了足够多的行还没找到，停止
                    if len(lines) > 1000:
                        break
            
            return None
            
        except Exception as e:
            print(f"❌ 反向读取快照失败 ({date_str}): {e}")
            # 回退到原始方法
            records = self.read_date_records(date_str, record_type='snapshot')
            return records[-1] if records else None
    
    def get_symbol_latest(self, symbol: str, date_str: str = None) -> Optional[Dict]:
        """
        获取指定币种的最新支撑阻力位数据
        
        Args:
            symbol: 币种符号
            date_str: 日期字符串（默认今天）
        
        Returns:
            Dict: level记录，如果没有返回None
        """
        if date_str is None:
            date_str = self.get_current_date()
        
        records = self.read_date_records(date_str, record_type='level')
        
        # 反向查找最新的该币种记录
        for record in reversed(records):
            if record.get('data', {}).get('symbol') == symbol:
                return record
        
        return None
    
    def get_date_range_records(self, start_date: str, end_date: str, 
                               record_type: str = None) -> List[Dict]:
        """
        获取日期范围内的记录
        
        Args:
            start_date: 起始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            record_type: 记录类型过滤
        
        Returns:
            List[Dict]: 记录列表
        """
        records = []
        
        # 生成日期范围
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        
        current = start
        while current <= end:
            date_str = current.strftime('%Y%m%d')
            date_records = self.read_date_records(date_str, record_type)
            records.extend(date_records)
            current += timedelta(days=1)
        
        return records
    
    def get_available_dates(self) -> List[str]:
        """获取所有可用的日期列表"""
        dates = []
        
        for file_path in sorted(self.data_dir.glob('support_resistance_*.jsonl')):
            # 从文件名提取日期
            filename = file_path.stem  # support_resistance_20260124
            date_str = filename.split('_')[-1]  # 20260124
            
            if len(date_str) == 8 and date_str.isdigit():
                dates.append(date_str)
        
        return sorted(dates)
    
    def get_date_statistics(self, date_str: str) -> Dict:
        """
        获取指定日期的统计信息
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
        
        Returns:
            Dict: 统计信息
        """
        file_path = self.get_file_path(date_str)
        
        if not file_path.exists():
            return {
                "date": date_str,
                "exists": False,
                "file_size": 0,
                "total_records": 0,
                "level_count": 0,
                "snapshot_count": 0
            }
        
        level_count = 0
        snapshot_count = 0
        total_records = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                total_records += 1
                
                try:
                    record = json.loads(line)
                    record_type = record.get('type')
                    
                    if record_type == 'level':
                        level_count += 1
                    elif record_type == 'snapshot':
                        snapshot_count += 1
                except:
                    continue
        
        file_size = file_path.stat().st_size
        
        return {
            "date": date_str,
            "exists": True,
            "file_path": str(file_path),
            "file_size": file_size,
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "total_records": total_records,
            "level_count": level_count,
            "snapshot_count": snapshot_count
        }
    
    def cleanup_old_data(self, keep_days: int = 30) -> Dict:
        """
        清理旧数据（保留最近N天）
        
        Args:
            keep_days: 保留天数
        
        Returns:
            Dict: 清理统计
        """
        try:
            cutoff_date = datetime.now(self.beijing_tz) - timedelta(days=keep_days)
            cutoff_str = cutoff_date.strftime('%Y%m%d')
            
            deleted_files = []
            deleted_size = 0
            
            for file_path in self.data_dir.glob('support_resistance_*.jsonl'):
                filename = file_path.stem
                date_str = filename.split('_')[-1]
                
                if len(date_str) == 8 and date_str.isdigit() and date_str < cutoff_str:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_files.append(date_str)
                    deleted_size += file_size
            
            return {
                "success": True,
                "deleted_files": len(deleted_files),
                "deleted_dates": sorted(deleted_files),
                "deleted_size_mb": round(deleted_size / 1024 / 1024, 2)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


if __name__ == '__main__':
    # 测试代码
    manager = SupportResistanceDailyManager()
    
    print("=== 测试支撑阻力按日期管理器 ===\n")
    
    # 测试1: 写入level记录
    print("1. 测试写入level记录...")
    test_level = {
        "symbol": "BTCUSDT",
        "current_price": 89500.0,
        "support_line_1": 88000.0,
        "support_line_2": 87500.0,
        "resistance_line_1": 91000.0,
        "resistance_line_2": 90500.0,
        "distance_to_support_1": 1.70,
        "distance_to_resistance_1": 1.68
    }
    
    success = manager.write_level_record(test_level)
    print(f"   写入结果: {'✅ 成功' if success else '❌ 失败'}\n")
    
    # 测试2: 写入snapshot记录
    print("2. 测试写入snapshot记录...")
    test_snapshot = {
        "scenario_1_count": 2,
        "scenario_2_count": 3,
        "scenario_3_count": 5,
        "scenario_4_count": 4,
        "total_coins": 27
    }
    
    success = manager.write_snapshot_record(test_snapshot)
    print(f"   写入结果: {'✅ 成功' if success else '❌ 失败'}\n")
    
    # 测试3: 读取今天的数据
    print("3. 测试读取今天的数据...")
    today = manager.get_current_date()
    stats = manager.get_date_statistics(today)
    print(f"   日期: {stats['date']}")
    print(f"   文件大小: {stats['file_size_mb']} MB")
    print(f"   总记录数: {stats['total_records']}")
    print(f"   Level记录: {stats['level_count']}")
    print(f"   Snapshot记录: {stats['snapshot_count']}\n")
    
    # 测试4: 获取最新level
    print("4. 测试获取最新level...")
    latest_levels = manager.get_latest_levels(limit=3)
    print(f"   获取到 {len(latest_levels)} 条记录")
    if latest_levels:
        print(f"   最新一条: {latest_levels[-1]['data']['symbol']} @ {latest_levels[-1]['time']}\n")
    
    # 测试5: 获取可用日期列表
    print("5. 获取可用日期列表...")
    dates = manager.get_available_dates()
    print(f"   共有 {len(dates)} 个日期的数据")
    if dates:
        print(f"   最早: {dates[0]}, 最新: {dates[-1]}\n")
    
    print("✅ 测试完成！")
