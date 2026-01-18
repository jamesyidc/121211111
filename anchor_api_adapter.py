#!/usr/bin/env python3
"""
锚点系统 API 适配器
功能：为 Flask 应用提供从 JSONL 读取数据的接口（替代 SQLite）
时区：统一使用北京时间
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


class AnchorAPIAdapter:
    """锚点系统 JSONL API 适配器"""
    
    def __init__(self, data_dir: str = '/home/user/webapp/data/anchor_jsonl'):
        self.data_dir = data_dir
        
    def _get_file_path(self, table_name: str) -> str:
        """获取表对应的 JSONL 文件路径"""
        return os.path.join(self.data_dir, f"{table_name}.jsonl")
    
    def _read_jsonl(self, table_name: str, limit: Optional[int] = None,
                   reverse: bool = True, filter_func: Optional[callable] = None) -> List[Dict[str, Any]]:
        """读取 JSONL 数据"""
        try:
            file_path = self._get_file_path(table_name)
            if not os.path.exists(file_path):
                return []
            
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
            
            # 倒序（最新在前）
            if reverse:
                records = list(reversed(records))
            
            # 限制数量
            if limit:
                records = records[:limit]
            
            return records
            
        except Exception as e:
            print(f"读取 JSONL 失败 [{table_name}]: {e}")
            return []
    
    def get_monitors(self, limit: int = 100, inst_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取持仓监控记录（替代 /api/anchor-system/monitors）
        
        参数:
            limit: 返回记录数量
            inst_id: 可选，筛选特定币种
        
        返回:
            {
                'success': bool,
                'data': List[Dict],
                'total': int,
                'data_source': 'JSONL',
                'timezone': 'Asia/Shanghai (Beijing)'
            }
        """
        try:
            # 过滤器（如果需要筛选币种）
            filter_func = None
            if inst_id:
                filter_func = lambda r: r.get('inst_id') == inst_id
            
            records = self._read_jsonl('anchor_monitors', limit=limit, filter_func=filter_func)
            
            # 格式化数据（确保字段名与前端一致）
            monitors = []
            for record in records:
                monitors.append({
                    'id': record.get('id'),
                    'timestamp': record.get('timestamp'),
                    'beijing_time': record.get('timestamp_beijing') or record.get('beijing_time'),
                    'inst_id': record.get('inst_id'),
                    'pos_side': record.get('pos_side'),
                    'pos_size': record.get('pos_size'),
                    'avg_price': record.get('avg_price'),
                    'mark_price': record.get('mark_price'),
                    'upl': record.get('upl'),
                    'upl_ratio': record.get('upl_ratio'),
                    'margin': record.get('margin'),
                    'leverage': record.get('leverage'),
                    'profit_rate': record.get('profit_rate'),
                    'alert_type': record.get('alert_type'),
                    'alert_sent': record.get('alert_sent', 0)
                })
            
            return {
                'success': True,
                'data': monitors,
                'total': len(monitors),
                'data_source': 'JSONL',
                'timezone': 'Asia/Shanghai (Beijing)'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'total': 0
            }
    
    def get_alerts(self, limit: int = 50, inst_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取告警历史（替代 /api/anchor-system/alerts）
        
        参数:
            limit: 返回记录数量
            inst_id: 可选，筛选特定币种
        
        返回:
            {
                'success': bool,
                'data': List[Dict],
                'total': int,
                'data_source': 'JSONL',
                'timezone': 'Asia/Shanghai (Beijing)'
            }
        """
        try:
            # 过滤器
            filter_func = None
            if inst_id:
                filter_func = lambda r: r.get('inst_id') == inst_id
            
            records = self._read_jsonl('anchor_alerts', limit=limit, filter_func=filter_func)
            
            # 格式化数据
            alerts = []
            for record in records:
                alerts.append({
                    'id': record.get('id'),
                    'timestamp': record.get('timestamp'),
                    'beijing_time': record.get('timestamp_beijing') or record.get('beijing_time'),
                    'inst_id': record.get('inst_id'),
                    'pos_side': record.get('pos_side'),
                    'profit_rate': record.get('profit_rate'),
                    'alert_type': record.get('alert_type'),
                    'message': record.get('message'),
                    'sent_status': record.get('sent_status', 0)
                })
            
            return {
                'success': True,
                'data': alerts,
                'total': len(alerts),
                'data_source': 'JSONL',
                'timezone': 'Asia/Shanghai (Beijing)'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'total': 0
            }
    
    def get_profit_records(self, limit: int = 50) -> Dict[str, Any]:
        """
        获取盈利记录（替代相关 API）
        
        返回:
            {
                'success': bool,
                'data': List[Dict],
                'total': int,
                'data_source': 'JSONL',
                'timezone': 'Asia/Shanghai (Beijing)'
            }
        """
        try:
            # 优先读取实盘记录
            records = self._read_jsonl('anchor_real_profit_records', limit=limit)
            
            if not records:
                # 如果没有实盘记录，尝试读取其他记录
                records = self._read_jsonl('anchor_profit_records', limit=limit)
            
            # 格式化数据
            profit_records = []
            for record in records:
                profit_records.append({
                    'id': record.get('id'),
                    'timestamp': record.get('timestamp'),
                    'beijing_time': record.get('timestamp_beijing') or record.get('beijing_time'),
                    'inst_id': record.get('inst_id'),
                    'pos_side': record.get('pos_side'),
                    'entry_price': record.get('entry_price'),
                    'exit_price': record.get('exit_price'),
                    'quantity': record.get('quantity'),
                    'profit': record.get('profit'),
                    'profit_rate': record.get('profit_rate'),
                    'leverage': record.get('leverage'),
                    'hold_duration': record.get('hold_duration')
                })
            
            return {
                'success': True,
                'data': profit_records,
                'total': len(profit_records),
                'data_source': 'JSONL',
                'timezone': 'Asia/Shanghai (Beijing)'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'total': 0
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回:
            {
                'success': bool,
                'statistics': Dict,
                'data_source': 'JSONL',
                'timezone': 'Asia/Shanghai (Beijing)'
            }
        """
        try:
            monitors = self._read_jsonl('anchor_monitors', limit=None)
            alerts = self._read_jsonl('anchor_alerts', limit=None)
            profit_records = self._read_jsonl('anchor_real_profit_records', limit=None)
            
            # 计算统计信息
            total_monitors = len(monitors)
            total_alerts = len(alerts)
            total_profit_records = len(profit_records)
            
            # 计算当前持仓数量（去重）
            unique_positions = set()
            if monitors:
                for monitor in monitors[:100]:  # 取最近100条
                    key = f"{monitor.get('inst_id')}_{monitor.get('pos_side')}"
                    unique_positions.add(key)
            
            # 最新记录时间
            latest_time = None
            if monitors:
                latest_time = monitors[0].get('timestamp_beijing') or monitors[0].get('beijing_time')
            
            return {
                'success': True,
                'statistics': {
                    'total_monitors': total_monitors,
                    'total_alerts': total_alerts,
                    'total_profit_records': total_profit_records,
                    'current_positions': len(unique_positions),
                    'latest_monitor_time': latest_time
                },
                'data_source': 'JSONL',
                'timezone': 'Asia/Shanghai (Beijing)'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'statistics': {}
            }


# 测试函数
def test_adapter():
    """测试适配器"""
    print("="*60)
    print("🧪 测试锚点系统 JSONL API 适配器")
    print("="*60)
    
    adapter = AnchorAPIAdapter()
    
    # 测试获取监控记录
    print("\n📊 测试获取监控记录 (limit=5):")
    result = adapter.get_monitors(limit=5)
    
    if result['success']:
        print(f"  ✅ 数据源: {result['data_source']}")
        print(f"  ✅ 时区: {result['timezone']}")
        print(f"  ✅ 总记录数: {result['total']}")
        
        print(f"\n  最新5条监控:")
        for idx, monitor in enumerate(result['data'], 1):
            print(f"  {idx}. {monitor['beijing_time']} | {monitor['inst_id']} {monitor['pos_side']}")
            print(f"     价格: {monitor['mark_price']:.4f} | 收益率: {monitor['profit_rate']:.2f}%")
    else:
        print(f"  ❌ 失败: {result['error']}")
    
    # 测试获取告警
    print("\n⚠️  测试获取告警 (limit=3):")
    result = adapter.get_alerts(limit=3)
    
    if result['success']:
        print(f"  ✅ 总告警数: {result['total']}")
        
        print(f"\n  最新3条告警:")
        for idx, alert in enumerate(result['data'], 1):
            print(f"  {idx}. {alert['beijing_time']} | {alert['inst_id']}")
            print(f"     告警类型: {alert['alert_type']} | 收益率: {alert['profit_rate']:.2f}%")
    else:
        print(f"  ❌ 失败: {result['error']}")
    
    # 测试统计信息
    print("\n📈 测试统计信息:")
    result = adapter.get_statistics()
    
    if result['success']:
        stats = result['statistics']
        print(f"  ✅ 数据源: {result['data_source']}")
        print(f"  ✅ 监控记录总数: {stats['total_monitors']:,}")
        print(f"  ✅ 告警记录总数: {stats['total_alerts']:,}")
        print(f"  ✅ 盈利记录总数: {stats['total_profit_records']:,}")
        print(f"  ✅ 当前持仓数: {stats['current_positions']}")
        print(f"  ✅ 最新监控时间: {stats['latest_monitor_time']} (北京时间)")
    else:
        print(f"  ❌ 失败: {result['error']}")
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)


if __name__ == '__main__':
    test_adapter()
