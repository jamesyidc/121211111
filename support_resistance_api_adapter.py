#!/usr/bin/env python3
"""
支撑压力线系统 API 适配器
功能：为 Flask 应用提供从 JSONL 读取数据的接口
时区：统一使用北京时间 (UTC+8)
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')

from support_resistance_jsonl_manager import SupportResistanceJSONLManager

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


class SupportResistanceAPIAdapter:
    """支撑压力线 API 适配器"""
    
    def __init__(self):
        self.manager = SupportResistanceJSONLManager()
    
    def get_all_symbols_latest(self) -> Dict[str, Any]:
        """
        获取所有币种的最新支撑压力线数据
        
        返回格式：
        {
            'success': True,
            'data': [...],
            'count': 27,
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)'
        }
        """
        try:
            latest_levels = self.manager.get_all_latest_levels()
            
            # 格式化数据
            formatted_data = []
            for level in latest_levels:
                formatted_data.append({
                    'symbol': level.get('symbol'),
                    'current_price': level.get('current_price'),
                    'support_line_1': level.get('support_line_1'),
                    'support_line_2': level.get('support_line_2'),
                    'resistance_line_1': level.get('resistance_line_1'),
                    'resistance_line_2': level.get('resistance_line_2'),
                    'distance_to_support_1': level.get('distance_to_support_1'),
                    'distance_to_support_2': level.get('distance_to_support_2'),
                    'distance_to_resistance_1': level.get('distance_to_resistance_1'),
                    'distance_to_resistance_2': level.get('distance_to_resistance_2'),
                    'position_7d': level.get('position_7d'),
                    'position_48h': level.get('position_48h'),
                    'price_change_24h': level.get('price_change_24h'),
                    'change_percent_24h': level.get('change_percent_24h'),
                    'baseline_price_24h': level.get('baseline_price_24h'),
                    'record_time': level.get('record_time_beijing') or level.get('record_time'),
                    'alert_7d_low': level.get('alert_7d_low', 0),
                    'alert_7d_high': level.get('alert_7d_high', 0),
                    'alert_48h_low': level.get('alert_48h_low', 0),
                    'alert_48h_high': level.get('alert_48h_high', 0)
                })
            
            # 按币种排序
            formatted_data.sort(key=lambda x: x['symbol'])
            
            return {
                'success': True,
                'data': formatted_data,
                'count': len(formatted_data),
                'data_source': 'JSONL',
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
    
    def get_symbol_detail(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """
        获取单个币种的详细历史数据
        
        参数:
            symbol: 币种（如 'BTCUSDT'）
            limit: 返回记录数
        
        返回格式：
        {
            'success': True,
            'symbol': 'BTCUSDT',
            'data': [...],
            'count': 100,
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)'
        }
        """
        try:
            records = self.manager.get_support_resistance_levels(symbol=symbol, limit=limit)
            
            # 格式化数据
            formatted_data = []
            for record in records:
                formatted_data.append({
                    'symbol': record.get('symbol'),
                    'current_price': record.get('current_price'),
                    'support_line_1': record.get('support_line_1'),
                    'support_line_2': record.get('support_line_2'),
                    'resistance_line_1': record.get('resistance_line_1'),
                    'resistance_line_2': record.get('resistance_line_2'),
                    'distance_to_support_1': record.get('distance_to_support_1'),
                    'distance_to_support_2': record.get('distance_to_support_2'),
                    'distance_to_resistance_1': record.get('distance_to_resistance_1'),
                    'distance_to_resistance_2': record.get('distance_to_resistance_2'),
                    'position_7d': record.get('position_7d'),
                    'position_48h': record.get('position_48h'),
                    'price_change_24h': record.get('price_change_24h'),
                    'change_percent_24h': record.get('change_percent_24h'),
                    'record_time': record.get('record_time_beijing') or record.get('record_time')
                })
            
            return {
                'success': True,
                'symbol': symbol,
                'data': formatted_data,
                'count': len(formatted_data),
                'data_source': 'JSONL',
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
    
    def get_snapshots(self, limit: Optional[int] = 100) -> Dict[str, Any]:
        """
        获取快照数据
        
        参数:
            limit: 返回记录数，None表示返回所有数据
        
        返回格式：
        {
            'success': True,
            'data': [...],
            'count': 100,
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)'
        }
        """
        try:
            snapshots = self.manager.get_snapshots(limit=limit)
            
            # 格式化数据
            formatted_data = []
            for snapshot in snapshots:
                formatted_data.append({
                    'snapshot_time': snapshot.get('snapshot_time_beijing') or snapshot.get('snapshot_time'),
                    'snapshot_date': snapshot.get('snapshot_date_beijing') or snapshot.get('snapshot_date'),
                    'scenario_1_count': snapshot.get('scenario_1_count', 0),
                    'scenario_2_count': snapshot.get('scenario_2_count', 0),
                    'scenario_3_count': snapshot.get('scenario_3_count', 0),
                    'scenario_4_count': snapshot.get('scenario_4_count', 0),
                    'scenario_1_coins': snapshot.get('scenario_1_coins', '[]'),
                    'scenario_2_coins': snapshot.get('scenario_2_coins', '[]'),
                    'scenario_3_coins': snapshot.get('scenario_3_coins', '[]'),
                    'scenario_4_coins': snapshot.get('scenario_4_coins', '[]'),
                    'total_coins': snapshot.get('total_coins', 0)
                })
            
            return {
                'success': True,
                'data': formatted_data,
                'count': len(formatted_data),
                'data_source': 'JSONL',
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
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)'
        }
        """
        try:
            stats = self.manager.get_statistics()
            
            return {
                'success': True,
                'statistics': stats,
                'data_source': 'JSONL',
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
