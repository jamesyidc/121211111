#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比价系统JSONL数据管理器
从JSONL文件读取比价系统数据，替代数据库查询
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

class PriceComparisonJSONLManager:
    def __init__(self, jsonl_dir='/home/user/webapp/data/price_comparison_jsonl'):
        self.jsonl_dir = Path(jsonl_dir)
        self.latest_baseline_file = self.jsonl_dir / 'latest_price_baseline.jsonl'
        self.breakthrough_events_file = self.jsonl_dir / 'price_breakthrough_events.jsonl'
        self.stats_file = self.jsonl_dir / 'price_comparison_stats.jsonl'
    
    def get_all_coins(self) -> List[Dict]:
        """获取所有币种的最新数据"""
        try:
            data = []
            with open(self.latest_baseline_file, 'r') as f:
                for line in f:
                    if line.strip():
                        coin_data = json.loads(line)
                        # 提取币种名称
                        symbol = coin_data.get('symbol', '')
                        coin_name = symbol.split('-')[0] if symbol else ''
                        
                        # 获取价格数据
                        highest_price = coin_data.get('highest_price', 0)
                        lowest_price = coin_data.get('lowest_price', 0)
                        last_price = coin_data.get('last_price', 0)
                        
                        # 计算跌幅（从最高点到当前价格）
                        decline = 0
                        if highest_price > 0 and last_price > 0:
                            decline = ((last_price - highest_price) / highest_price) * 100
                        
                        # 计算涨幅（从最低点到当前价格）
                        rise_from_low = 0
                        if lowest_price > 0 and last_price > 0:
                            rise_from_low = ((last_price - lowest_price) / lowest_price) * 100
                        
                        data.append({
                            'coin_name': coin_name,
                            'symbol': symbol,
                            # 使用前端期望的字段名
                            'high_price': highest_price,
                            'low_price': lowest_price,
                            'current_price': last_price,
                            'decline': round(decline, 2),  # 跌幅（负数表示下跌）
                            'rise_from_low': round(rise_from_low, 2),  # 从最低点涨幅
                            # 保留原始字段名（兼容性）
                            'highest_price': highest_price,
                            'highest_count': coin_data.get('highest_count'),
                            'lowest_price': lowest_price,
                            'lowest_count': coin_data.get('lowest_count'),
                            'last_price': last_price,
                            'highest_ratio': coin_data.get('highest_ratio'),
                            'lowest_ratio': coin_data.get('lowest_ratio'),
                            'snapshot_time': coin_data.get('last_update_time'),
                            'last_update_time': coin_data.get('last_update_time')
                        })
            return data
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"读取币种数据失败: {e}")
            return []
    
    def get_breakthrough_events(self, limit: int = 50, days: int = 7, 
                               coin_filter: Optional[str] = None,
                               type_filter: Optional[str] = None) -> List[Dict]:
        """获取突破事件日志"""
        try:
            events = []
            
            # 计算时间过滤
            if days > 0:
                cutoff_time = datetime.now() - timedelta(days=days)
                cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                cutoff_str = None
            
            # 读取所有事件（倒序，最新的在前）
            with open(self.breakthrough_events_file, 'r') as f:
                lines = f.readlines()
            
            # 倒序处理
            for line in reversed(lines):
                if not line.strip():
                    continue
                
                event = json.loads(line)
                
                # 时间过滤
                if cutoff_str and event.get('event_time', '') < cutoff_str:
                    continue
                
                # 币种过滤
                if coin_filter and event.get('symbol') != coin_filter:
                    continue
                
                # 类型过滤
                if type_filter and event.get('event_type') != type_filter:
                    continue
                
                # 提取币种名称
                symbol = event.get('symbol', '')
                coin_name = symbol.split('-')[0] if symbol else ''
                
                # 计算变化
                price = event.get('price', 0)
                previous_price = event.get('previous_extreme_price', 0)
                change = price - previous_price if previous_price else 0
                
                events.append({
                    'coin_name': coin_name,
                    'symbol': symbol,
                    'event_type': event.get('event_type'),
                    'event_label': '创新高' if event.get('event_type') == 'new_high' else '创新低',
                    'price': price,
                    'previous_extreme_price': previous_price,
                    'change': change,
                    'event_time': event.get('event_time')
                })
                
                # 限制数量
                if len(events) >= limit:
                    break
            
            return events
            
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"读取突破事件失败: {e}")
            return []
    
    def get_breakthrough_stats(self) -> Dict:
        """获取突破事件统计"""
        try:
            # 从缓存文件读取
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            stats = json.loads(line)
                            # 检查是否是今天的数据
                            stat_date = stats.get('stat_date')
                            today = datetime.now().strftime('%Y-%m-%d')
                            if stat_date == today:
                                return {
                                    'today': {
                                        'new_high': stats.get('today_new_high', 0),
                                        'new_low': stats.get('today_new_low', 0)
                                    },
                                    'three_days': {
                                        'new_high': stats.get('three_days_new_high', 0),
                                        'new_low': stats.get('three_days_new_low', 0)
                                    },
                                    'seven_days': {
                                        'new_high': stats.get('seven_days_new_high', 0),
                                        'new_low': stats.get('seven_days_new_low', 0)
                                    }
                                }
            
            # 如果没有缓存或过期，实时计算
            return self._calculate_breakthrough_stats()
            
        except Exception as e:
            print(f"读取突破统计失败: {e}")
            return self._calculate_breakthrough_stats()
    
    def _calculate_breakthrough_stats(self) -> Dict:
        """实时计算突破事件统计"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        three_days_ago = now - timedelta(days=3)
        seven_days_ago = now - timedelta(days=7)
        
        today_start_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
        three_days_ago_str = three_days_ago.strftime('%Y-%m-%d %H:%M:%S')
        seven_days_ago_str = seven_days_ago.strftime('%Y-%m-%d %H:%M:%S')
        
        stats = {
            'today': {'new_high': 0, 'new_low': 0},
            'three_days': {'new_high': 0, 'new_low': 0},
            'seven_days': {'new_high': 0, 'new_low': 0}
        }
        
        try:
            with open(self.breakthrough_events_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    event = json.loads(line)
                    event_time = event.get('event_time', '')
                    event_type = event.get('event_type', '')
                    
                    # 7天统计
                    if event_time >= seven_days_ago_str:
                        if event_type == 'new_high':
                            stats['seven_days']['new_high'] += 1
                        elif event_type == 'new_low':
                            stats['seven_days']['new_low'] += 1
                    
                    # 3天统计
                    if event_time >= three_days_ago_str:
                        if event_type == 'new_high':
                            stats['three_days']['new_high'] += 1
                        elif event_type == 'new_low':
                            stats['three_days']['new_low'] += 1
                    
                    # 今天统计
                    if event_time >= today_start_str:
                        if event_type == 'new_high':
                            stats['today']['new_high'] += 1
                        elif event_type == 'new_low':
                            stats['today']['new_low'] += 1
            
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"计算统计失败: {e}")
        
        return stats
