#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAR斜率JSONL管理器
从SAR JSONL数据计算斜率并提供查询接口
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

class SARSlopeJSONLManager:
    def __init__(self, sar_jsonl_dir='/home/user/webapp/data/sar_jsonl'):
        self.sar_jsonl_dir = Path(sar_jsonl_dir)
        
    def calculate_sar_slope(self, symbol: str, window: int = 10) -> Optional[Dict]:
        """
        计算指定币种的SAR斜率
        
        参数:
            symbol: 币种符号 (如 BTC, ETH)
            window: 计算窗口大小（使用最近N个数据点）
        
        返回:
            包含斜率信息的字典
        """
        try:
            filepath = self.sar_jsonl_dir / f"{symbol}.jsonl"
            if not filepath.exists():
                return None
            
            # 读取最近的数据
            data_points = []
            with open(filepath, 'r') as f:
                lines = f.readlines()
                # 取最后window个点
                for line in lines[-window:]:
                    if line.strip():
                        data_points.append(json.loads(line))
            
            if len(data_points) < 2:
                return None
            
            # 计算斜率 (使用线性回归)
            latest = data_points[-1]
            position = latest.get('position', 'long')
            
            # 计算SAR值的变化趋势
            sar_values = [d.get('sar', 0) for d in data_points]
            prices = [d.get('close', 0) for d in data_points]
            
            # 简单斜率：(最后值 - 第一值) / 点数
            if len(sar_values) > 1:
                sar_slope = (sar_values[-1] - sar_values[0]) / len(sar_values)
                price_slope = (prices[-1] - prices[0]) / len(prices)
            else:
                sar_slope = 0
                price_slope = 0
            
            # 计算方向一致性（价格和SAR同向的比例）
            direction_match = 0
            for i in range(1, len(data_points)):
                sar_diff = sar_values[i] - sar_values[i-1]
                price_diff = prices[i] - prices[i-1]
                if (sar_diff > 0 and price_diff > 0) or (sar_diff < 0 and price_diff < 0):
                    direction_match += 1
            
            direction_ratio = direction_match / (len(data_points) - 1) if len(data_points) > 1 else 0
            
            # 计算偏多比/偏空比
            # 偏多比：SAR向上趋势的比例
            slope_value = direction_ratio if position == 'long' else -direction_ratio
            
            return {
                'symbol': symbol,
                'datetime': latest.get('beijing_time'),
                'sar_value': latest.get('sar'),
                'sar_position': position,
                'sar_quadrant': self._get_quadrant(latest.get('close', 0), latest.get('sar', 0), position),
                'position_duration': latest.get('duration_minutes', 0),
                'slope_value': round(slope_value, 4),
                'slope_direction': 'up' if sar_slope > 0 else 'down',
                'price': latest.get('close'),
                'timestamp': latest.get('timestamp')
            }
            
        except Exception as e:
            print(f"计算 {symbol} SAR斜率失败: {e}")
            return None
    
    def _get_quadrant(self, price: float, sar: float, position: str) -> str:
        """确定SAR象限"""
        if position == 'long':
            if price > sar:
                return 'Q1'  # 多头强势
            else:
                return 'Q2'  # 多头弱势
        else:  # bearish
            if price < sar:
                return 'Q3'  # 空头强势
            else:
                return 'Q4'  # 空头弱势
    
    def get_all_sar_slopes(self, position_filter: Optional[str] = None) -> List[Dict]:
        """
        获取所有币种的SAR斜率
        
        参数:
            position_filter: 仓位过滤 ('bullish'/'bearish')
        
        返回:
            斜率数据列表
        """
        results = []
        
        # 遍历所有JSONL文件
        for filepath in self.sar_jsonl_dir.glob("*.jsonl"):
            if filepath.name.endswith('.backup'):
                continue
            
            symbol = filepath.stem  # 获取文件名（不含扩展名）
            slope_data = self.calculate_sar_slope(symbol)
            
            if slope_data:
                # 转换position格式
                sar_position = slope_data['sar_position']
                if sar_position == 'long':
                    slope_data['sar_position'] = 'bullish'
                elif sar_position == 'short':
                    slope_data['sar_position'] = 'bearish'
                
                # 应用过滤
                if position_filter and slope_data['sar_position'] != position_filter:
                    continue
                
                results.append(slope_data)
        
        # 按symbol排序
        results.sort(key=lambda x: x['symbol'])
        
        return results
    
    def get_position_stats(self, data: List[Dict]) -> Dict:
        """
        计算仓位统计
        
        参数:
            data: SAR斜率数据列表
        
        返回:
            统计信息字典
        """
        total = len(data)
        bullish = sum(1 for d in data if d['sar_position'] == 'bullish')
        bearish = total - bullish
        
        # 计算平均持续时间
        avg_duration = sum(d.get('position_duration', 0) for d in data) / total if total > 0 else 0
        
        return {
            'total_symbols': total,
            'bullish_count': bullish,
            'bearish_count': bearish,
            'avg_duration': round(avg_duration, 1)
        }
    
    def export_to_jsonl(self, output_file: str = '/home/user/webapp/data/sar_slope_jsonl/latest_sar_slope.jsonl'):
        """
        导出所有SAR斜率数据到JSONL文件
        
        参数:
            output_file: 输出文件路径
        """
        try:
            # 确保目录存在
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            # 获取所有数据
            all_data = self.get_all_sar_slopes()
            
            # 写入JSONL
            with open(output_file, 'w') as f:
                for item in all_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            print(f"✅ SAR斜率数据已导出: {len(all_data)} 个币种 -> {output_file}")
            return len(all_data)
            
        except Exception as e:
            print(f"❌ 导出SAR斜率数据失败: {e}")
            return 0
