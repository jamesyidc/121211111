#!/usr/bin/env python3
"""
支撑压力线系统 JSONL 数据管理器
功能：管理和操作 JSONL 格式的支撑压力线数据
时区：统一使用北京时间 (UTC+8)
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 数据目录
DATA_DIR = '/home/user/webapp/data/support_resistance_jsonl'


class SupportResistanceJSONLManager:
    """支撑压力线 JSONL 数据管理器"""
    
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
    def _get_file_path(self, table_name: str) -> str:
        """获取表对应的 JSONL 文件路径"""
        return os.path.join(self.data_dir, f"{table_name}.jsonl")
    
    def read_records(self, table_name: str, limit: Optional[int] = None, 
                    reverse: bool = True, filter_func: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        读取 JSONL 记录
        
        参数:
            table_name: 表名
            limit: 限制返回记录数
            reverse: 是否倒序（最新在前）
            filter_func: 过滤函数
        
        返回:
            记录列表
        """
        try:
            file_path = self._get_file_path(table_name)
            if not os.path.exists(file_path):
                return []
            
            # 如果需要倒序读取且有limit，使用tail优化
            if reverse and limit and limit <= 10000:
                return self._read_last_n_lines(file_path, limit, filter_func)
            
            # 否则使用常规方法
            records = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                        
                        # 应用过滤器
                        if filter_func and not filter_func(record):
                            continue
                        
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
            
            # 倒序
            if reverse:
                records = list(reversed(records))
            
            # 限制数量
            if limit:
                records = records[:limit]
            
            return records
            
        except Exception as e:
            print(f"读取 JSONL 失败 [{table_name}]: {e}")
            return []
    
    def _read_last_n_lines(self, file_path: str, n: int, filter_func: Optional[callable] = None) -> List[Dict[str, Any]]:
        """高效读取文件最后N行（倒序）"""
        try:
            import subprocess
            # 使用tail命令快速读取最后N行
            result = subprocess.run(
                ['tail', '-n', str(n * 2), file_path],  # 读2倍以防过滤后不够
                capture_output=True, text=True, check=True
            )
            
            records = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if filter_func and not filter_func(record):
                        continue
                    records.append(record)
                except json.JSONDecodeError:
                    continue
            
            # 已经是倒序（最新在后），需要反转
            return list(reversed(records))[:n]
            
        except Exception as e:
            print(f"快速读取失败，使用常规方法: {e}")
            # 降级到常规方法
            records = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if filter_func and not filter_func(record):
                            continue
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
            return list(reversed(records))[:n]
    
    def append_record(self, table_name: str, record: Dict[str, Any]) -> bool:
        """
        追加一条记录到 JSONL 文件
        
        参数:
            table_name: 表名
            record: 记录数据
        
        返回:
            是否成功
        """
        try:
            file_path = self._get_file_path(table_name)
            
            # 添加北京时间戳
            beijing_now = datetime.now(BEIJING_TZ)
            if 'record_time' not in record:
                record['record_time_beijing'] = beijing_now.strftime('%Y-%m-%d %H:%M:%S')
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
            
        except Exception as e:
            print(f"追加记录失败 [{table_name}]: {e}")
            return False
    
    def count_records(self, table_name: str) -> int:
        """统计记录数"""
        try:
            file_path = self._get_file_path(table_name)
            if not os.path.exists(file_path):
                return 0
            
            count = 0
            with open(file_path, 'r', encoding='utf-8') as f:
                for _ in f:
                    count += 1
            
            return count
            
        except Exception as e:
            print(f"统计记录失败 [{table_name}]: {e}")
            return 0
    
    def get_latest_record(self, table_name: str, filter_func: Optional[callable] = None) -> Optional[Dict[str, Any]]:
        """获取最新的一条记录"""
        records = self.read_records(table_name, limit=1, reverse=True, filter_func=filter_func)
        return records[0] if records else None
    
    def get_support_resistance_levels(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取支撑压力线数据
        
        参数:
            symbol: 币种（可选，如 'BTCUSDT'）
            limit: 返回记录数
        
        返回:
            记录列表
        """
        filter_func = None
        if symbol:
            filter_func = lambda r: r.get('symbol') == symbol
        
        return self.read_records('support_resistance_levels', limit=limit, filter_func=filter_func)
    
    def get_latest_levels_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取某个币种的最新支撑压力线数据"""
        filter_func = lambda r: r.get('symbol') == symbol
        return self.get_latest_record('support_resistance_levels', filter_func=filter_func)
    
    def get_all_latest_levels(self) -> List[Dict[str, Any]]:
        """获取所有币种的最新支撑压力线数据"""
        # 只读取最近的100条记录（27个币种，100条足够覆盖所有币种的最新数据）
        # 使用tail命令优化，避免扫描整个544MB文件
        recent_records = self.read_records('support_resistance_levels', limit=100, reverse=True)
        
        # 按币种分组，取每个币种的最新记录
        symbol_latest = {}
        for record in recent_records:
            symbol = record.get('symbol')
            if symbol and symbol not in symbol_latest:
                symbol_latest[symbol] = record
        
        return list(symbol_latest.values())
    
    def get_snapshots(self, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """
        获取快照数据
        
        参数:
            limit: 返回记录数，None表示返回所有数据
        """
        return self.read_records('support_resistance_snapshots', limit=limit)
    
    def get_daily_baseline_prices(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取每日基准价格"""
        filter_func = None
        if symbol:
            filter_func = lambda r: r.get('symbol') == symbol
        
        return self.read_records('daily_baseline_prices', limit=limit, filter_func=filter_func)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        tables = [
            'support_resistance_levels',
            'support_resistance_snapshots',
            'daily_baseline_prices',
            'okex_kline_ohlc'
        ]
        
        stats = {}
        total_records = 0
        
        for table in tables:
            count = self.count_records(table)
            stats[table] = count
            total_records += count
            
            # 获取最新记录时间
            latest = self.get_latest_record(table)
            if latest:
                # 尝试找到时间字段
                time_fields = ['record_time_beijing', 'created_at_beijing', 'snapshot_time_beijing', 
                              'baseline_time_beijing', 'timestamp_beijing']
                latest_time = None
                
                for field in time_fields:
                    if field in latest:
                        latest_time = latest[field]
                        break
                
                if not latest_time:
                    # 如果没有北京时间字段，尝试原始时间字段
                    for field in ['record_time', 'created_at', 'snapshot_time', 'baseline_time', 'timestamp']:
                        if field in latest:
                            latest_time = latest[field]
                            break
                
                stats[f'{table}_latest_time'] = latest_time
        
        stats['total_records'] = total_records
        stats['timezone'] = 'Asia/Shanghai (Beijing Time, UTC+8)'
        
        return stats


def test_manager():
    """测试管理器"""
    print("="*60)
    print("🧪 测试支撑压力线 JSONL 数据管理器")
    print("="*60)
    print()
    
    manager = SupportResistanceJSONLManager()
    
    # 1. 统计信息
    print("📊 统计信息:")
    stats = manager.get_statistics()
    
    print(f"  总记录数: {stats['total_records']:,}")
    print(f"  时区: {stats['timezone']}")
    print()
    
    tables = ['support_resistance_levels', 'support_resistance_snapshots', 
              'daily_baseline_prices', 'okex_kline_ohlc']
    
    for table in tables:
        count = stats.get(table, 0)
        latest_time = stats.get(f'{table}_latest_time', 'N/A')
        print(f"  • {table:40s} {count:>10,} 条")
        print(f"    最新时间: {latest_time}")
    
    print()
    
    # 2. 获取所有币种的最新数据
    print("📈 所有币种最新支撑压力线数据:")
    latest_levels = manager.get_all_latest_levels()
    
    print(f"  币种数: {len(latest_levels)}")
    print()
    
    # 按币种排序
    latest_levels.sort(key=lambda x: x.get('symbol', ''))
    
    for level in latest_levels[:10]:  # 只显示前10个
        symbol = level.get('symbol', 'N/A')
        current_price = level.get('current_price', 0)
        support_1 = level.get('support_line_1', 0)
        resistance_1 = level.get('resistance_line_1', 0)
        record_time = level.get('record_time_beijing') or level.get('record_time', 'N/A')
        
        print(f"  {symbol:15s} 价格: {current_price:>10.4f}")
        print(f"                  支撑1: {support_1:>10.4f} | 压力1: {resistance_1:>10.4f}")
        print(f"                  时间: {record_time}")
        print()
    
    if len(latest_levels) > 10:
        print(f"  ... 还有 {len(latest_levels) - 10} 个币种")
        print()
    
    # 3. 测试单个币种查询
    print("🔍 测试查询 BTCUSDT 最新数据:")
    btc_latest = manager.get_latest_levels_by_symbol('BTCUSDT')
    
    if btc_latest:
        print(f"  币种: {btc_latest.get('symbol')}")
        print(f"  当前价格: {btc_latest.get('current_price')}")
        print(f"  支撑线1: {btc_latest.get('support_line_1')}")
        print(f"  支撑线2: {btc_latest.get('support_line_2')}")
        print(f"  压力线1: {btc_latest.get('resistance_line_1')}")
        print(f"  压力线2: {btc_latest.get('resistance_line_2')}")
        print(f"  记录时间: {btc_latest.get('record_time_beijing') or btc_latest.get('record_time')}")
    else:
        print("  未找到数据")
    
    print()
    
    # 4. 测试快照查询
    print("📸 最新快照数据 (前3条):")
    snapshots = manager.get_snapshots(limit=3)
    
    for idx, snapshot in enumerate(snapshots, 1):
        snapshot_time = snapshot.get('snapshot_time_beijing') or snapshot.get('snapshot_time', 'N/A')
        total_coins = snapshot.get('total_coins', 0)
        scenario_1 = snapshot.get('scenario_1_count', 0)
        scenario_2 = snapshot.get('scenario_2_count', 0)
        
        print(f"  {idx}. 时间: {snapshot_time}")
        print(f"     总币种: {total_coins} | 场景1: {scenario_1} | 场景2: {scenario_2}")
    
    print()
    print("="*60)
    print("✅ 测试完成！")
    print("="*60)


if __name__ == '__main__':
    test_manager()
