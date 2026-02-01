#!/usr/bin/env python3
"""
支撑压力线系统 API 适配器
功能：为 Flask 应用提供从 JSONL 读取数据的接口（按日期存储）
时区：统一使用北京时间 (UTC+8)
更新：2026-01-24 - 使用按日期存储的新管理器
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')

from support_resistance_daily_manager import SupportResistanceDailyManager

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


class SupportResistanceAPIAdapter:
    """支撑压力线 API 适配器（使用按日期存储）"""
    
    def __init__(self):
        self.manager = SupportResistanceDailyManager()
    
    def get_all_symbols_latest(self) -> Dict[str, Any]:
        """
        获取所有币种的最新支撑压力线数据
        
        返回格式：
        {
            'success': True,
            'data': [...],
            'count': 27,
            'data_source': 'JSONL (按日期存储)',
            'timezone': 'Beijing Time (UTC+8)'
        }
        """
        try:
            # 使用新管理器获取今日最新数据
            latest_levels = self.manager.get_latest_levels()
            
            # 格式化数据
            formatted_data = []
            for level in latest_levels:
                # 提取data字段（新格式）
                data = level.get('data', level)  # 兼容新旧格式
                
                formatted_data.append({
                    'symbol': data.get('symbol'),
                    'current_price': data.get('current_price'),
                    'support_line_1': data.get('support_line_1'),
                    'support_line_2': data.get('support_line_2'),
                    'resistance_line_1': data.get('resistance_line_1'),
                    'resistance_line_2': data.get('resistance_line_2'),
                    'distance_to_support_1': data.get('distance_to_support_1'),
                    'distance_to_support_2': data.get('distance_to_support_2'),
                    'distance_to_resistance_1': data.get('distance_to_resistance_1'),
                    'distance_to_resistance_2': data.get('distance_to_resistance_2'),
                    'position_7d': data.get('position_7d'),
                    'position_48h': data.get('position_48h'),
                    'price_change_24h': data.get('price_change_24h'),
                    'change_percent_24h': data.get('change_percent_24h'),
                    'baseline_price_24h': data.get('baseline_price_24h'),
                    'record_time': data.get('record_time_beijing') or data.get('record_time'),
                    'alert_7d_low': data.get('alert_7d_low', 0),
                    'alert_7d_high': data.get('alert_7d_high', 0),
                    'alert_48h_low': data.get('alert_48h_low', 0),
                    'alert_48h_high': data.get('alert_48h_high', 0)
                })
            
            # 按币种排序
            formatted_data.sort(key=lambda x: x['symbol'])
            
            return {
                'success': True,
                'data': formatted_data,
                'count': len(formatted_data),
                'data_source': 'JSONL (按日期存储)',
                'timezone': 'Beijing Time (UTC+8)',
                'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0
            }
    
    def get_symbol_detail(self, symbol: str, limit: int = 100, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取单个币种的详细历史数据
        
        参数:
            symbol: 币种（如 'BTCUSDT'）
            limit: 返回记录数
            date: 日期（YYYY-MM-DD格式），None表示今天
        
        返回格式：
        {
            'success': True,
            'symbol': 'BTCUSDT',
            'data': [...],
            'count': 100,
            'data_source': 'JSONL (按日期存储)',
            'timezone': 'Beijing Time (UTC+8)'
        }
        """
        try:
            # 如果指定日期，读取特定日期的数据；否则读取今天的数据
            if date:
                date_str = date.replace('-', '')  # YYYY-MM-DD -> YYYYMMDD
                records = self.manager.get_levels_by_date(date_str, symbol=symbol, limit=limit)
            else:
                # 获取今天的数据（最新）
                all_records = self.manager.get_latest_levels(symbol=symbol)
                records = all_records[-limit:] if len(all_records) > limit else all_records
            
            # 格式化数据
            formatted_data = []
            for record in records:
                # 提取data字段（新格式）
                data = record.get('data', record)  # 兼容新旧格式
                
                formatted_data.append({
                    'symbol': data.get('symbol'),
                    'current_price': data.get('current_price'),
                    'support_line_1': data.get('support_line_1'),
                    'support_line_2': data.get('support_line_2'),
                    'resistance_line_1': data.get('resistance_line_1'),
                    'resistance_line_2': data.get('resistance_line_2'),
                    'distance_to_support_1': data.get('distance_to_support_1'),
                    'distance_to_support_2': data.get('distance_to_support_2'),
                    'distance_to_resistance_1': data.get('distance_to_resistance_1'),
                    'distance_to_resistance_2': data.get('distance_to_resistance_2'),
                    'position_7d': data.get('position_7d'),
                    'position_48h': data.get('position_48h'),
                    'price_change_24h': data.get('price_change_24h'),
                    'change_percent_24h': data.get('change_percent_24h'),
                    'record_time': data.get('record_time_beijing') or data.get('record_time')
                })
            
            return {
                'success': True,
                'symbol': symbol,
                'data': formatted_data,
                'count': len(formatted_data),
                'data_source': 'JSONL (按日期存储)',
                'timezone': 'Beijing Time (UTC+8)',
                'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol,
                'data': [],
                'count': 0
            }
    
    def get_snapshots(self, limit: Optional[int] = 100, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取快照数据
        
        参数:
            limit: 返回记录数，None表示返回所有数据
            date: 日期（YYYY-MM-DD格式），None表示今天
        
        返回格式：
        {
            'success': True,
            'data': [...],
            'count': 100,
            'data_source': 'JSONL (按日期存储)',
            'timezone': 'Beijing Time (UTC+8)'
        }
        """
        try:
            # 如果指定日期，读取特定日期的数据
            if date:
                date_str = date.replace('-', '')  # YYYY-MM-DD -> YYYYMMDD
                all_records = self.manager.read_date_records(date_str, record_type='snapshot')
                snapshots = all_records[-limit:] if (limit and len(all_records) > limit) else all_records
            elif limit is None:
                # limit=None表示获取所有历史数据（跨所有日期）
                # 从按日期分片的文件读取所有快照
                print("📖 从按日期文件读取所有历史快照...")
                all_snapshots = []
                available_dates = self.manager.get_available_dates()
                
                for date_str in available_dates:
                    date_snapshots = self.manager.read_date_records(date_str, record_type='snapshot')
                    all_snapshots.extend(date_snapshots)
                
                snapshots = all_snapshots
                print(f"✅ 成功读取 {len(snapshots)} 条快照 (覆盖 {len(available_dates)} 天)")

            else:
                # 获取今天最新的快照（指定limit）
                snapshots = self.manager.get_latest_snapshot()
                if snapshots:
                    snapshots = [snapshots]  # 转换为列表
                else:
                    snapshots = []
            
            # 格式化数据
            formatted_data = []
            for snapshot in snapshots:
                # 提取data字段（新格式）
                data = snapshot.get('data', snapshot)  # 兼容新旧格式
                
                formatted_data.append({
                    'snapshot_time': data.get('snapshot_time_beijing') or data.get('snapshot_time'),
                    'snapshot_date': data.get('snapshot_date_beijing') or data.get('snapshot_date'),
                    'scenario_1_count': data.get('scenario_1_count', 0),
                    'scenario_2_count': data.get('scenario_2_count', 0),
                    'scenario_3_count': data.get('scenario_3_count', 0),
                    'scenario_4_count': data.get('scenario_4_count', 0),
                    'scenario_1_coins': data.get('scenario_1_coins', '[]'),
                    'scenario_2_coins': data.get('scenario_2_coins', '[]'),
                    'scenario_3_coins': data.get('scenario_3_coins', '[]'),
                    'scenario_4_coins': data.get('scenario_4_coins', '[]'),
                    'total_coins': data.get('total_coins', 0)
                })
            
            return {
                'success': True,
                'data': formatted_data,
                'count': len(formatted_data),
                'data_source': 'JSONL (按日期存储)',
                'timezone': 'Beijing Time (UTC+8)',
                'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回格式：
        {
            'success': True,
            'statistics': {...},
            'data_source': 'JSONL (按日期存储)',
            'timezone': 'Beijing Time (UTC+8)'
        }
        """
        try:
            # 使用新管理器的统计方法
            available_dates = self.manager.get_available_dates()
            
            # 统计今日数据
            today_levels = self.manager.get_latest_levels()
            today_snapshots = self.manager.get_latest_snapshot()
            
            stats = {
                'total_dates': len(available_dates),
                'earliest_date': available_dates[0] if available_dates else None,
                'latest_date': available_dates[-1] if available_dates else None,
                'today_levels_count': len(today_levels),
                'today_has_snapshot': today_snapshots is not None,
                'available_dates': available_dates
            }
            
            return {
                'success': True,
                'statistics': stats,
                'data_source': 'JSONL (按日期存储)',
                'timezone': 'Beijing Time (UTC+8)',
                'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'statistics': {}
            }


def test_adapter():
    """测试适配器"""
    print("="*60)
    print("🧪 测试支撑压力线 API 适配器")
    print("="*60)
    print()
    
    adapter = SupportResistanceAPIAdapter()
    
    # 1. 测试获取所有币种最新数据
    print("📊 测试获取所有币种最新数据:")
    result = adapter.get_all_symbols_latest()
    
    if result['success']:
        print(f"  ✅ 数据源: {result['data_source']}")
        print(f"  ✅ 时区: {result['timezone']}")
        print(f"  ✅ 币种数: {result['count']}")
        print(f"  ✅ 时间戳: {result['timestamp']}")
        
        if result['data']:
            print(f"\n  前3个币种:")
            for idx, data in enumerate(result['data'][:3], 1):
                print(f"  {idx}. {data['symbol']:15s} 价格: ${data['current_price']:.4f}")
                print(f"     支撑1: ${data['support_line_1']:.4f} | 压力1: ${data['resistance_line_1']:.4f}")
                print(f"     时间: {data['record_time']}")
    else:
        print(f"  ❌ 失败: {result['error']}")
    
    print()
    
    # 2. 测试获取单个币种详细数据
    print("🔍 测试获取 BTCUSDT 详细数据 (最新5条):")
    result = adapter.get_symbol_detail('BTCUSDT', limit=5)
    
    if result['success']:
        print(f"  ✅ 币种: {result['symbol']}")
        print(f"  ✅ 记录数: {result['count']}")
        
        if result['data']:
            print(f"\n  最新5条:")
            for idx, data in enumerate(result['data'], 1):
                print(f"  {idx}. {data['record_time']} | 价格: ${data['current_price']:.4f}")
    else:
        print(f"  ❌ 失败: {result['error']}")
    
    print()
    
    # 3. 测试获取快照数据
    print("📸 测试获取快照数据 (最新3条):")
    result = adapter.get_snapshots(limit=3)
    
    if result['success']:
        print(f"  ✅ 记录数: {result['count']}")
        
        if result['data']:
            print(f"\n  最新3条:")
            for idx, data in enumerate(result['data'], 1):
                print(f"  {idx}. {data['snapshot_time']}")
                print(f"     总币种: {data['total_coins']} | 场景1: {data['scenario_1_count']} | 场景2: {data['scenario_2_count']}")
    else:
        print(f"  ❌ 失败: {result['error']}")
    
    print()
    
    # 4. 测试统计信息
    print("📈 测试统计信息:")
    result = adapter.get_statistics()
    
    if result['success']:
        stats = result['statistics']
        print(f"  ✅ 数据源: {result['data_source']}")
        print(f"  ✅ 总记录数: {stats['total_records']:,}")
        print(f"  ✅ 支撑压力线记录: {stats['support_resistance_levels']:,}")
        print(f"  ✅ 快照记录: {stats['support_resistance_snapshots']:,}")
        print(f"  ✅ 基准价格记录: {stats['daily_baseline_prices']:,}")
    else:
        print(f"  ❌ 失败: {result['error']}")
    
    print()
    print("="*60)
    print("✅ 测试完成！")
    print("="*60)


if __name__ == '__main__':
    test_adapter()
