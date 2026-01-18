#!/usr/bin/env python3
"""
SAR API JSONL版本
从JSONL文件读取数据并提供API接口
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from sar_jsonl_manager import SARJSONLManager

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 27个币种
SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'DOGE', 'LINK', 'DOT', 'LTC', 'UNI',
    'NEAR', 'FIL', 'ETC', 'APT', 'HBAR', 'CRV', 'LDO', 'STX', 'CFX', 'CRO',
    'BCH', 'SUI', 'TAO', 'TRX', 'TON', 'XLM', 'AAVE'
]


def get_sar_current_cycle(symbol: str, limit: int = 500) -> Dict:
    """
    获取当前完整周期的所有序列数据（从JSONL）
    
    Args:
        symbol: 币种代码，如 'BTC'
        limit: 最多返回多少条记录，默认500（约1.7天）
    
    Returns:
        包含当前周期所有序列数据的字典
    """
    try:
        if symbol.upper() not in SYMBOLS:
            return {
                'success': False,
                'error': f'Symbol {symbol} not supported'
            }
        
        # 初始化JSONL管理器
        manager = SARJSONLManager(symbol.upper())
        
        # 获取当前状态
        current_status = manager.get_latest_status()
        if not current_status:
            return {
                'success': False,
                'error': 'No data available'
            }
        
        # 读取最新N条数据，reverse=True表示最新的在前
        # 默认500条（约1.7天），最多1000条（约3.5天）
        limit = min(max(50, limit), 2000)  # 限制在50-2000之间
        all_records = manager.read_records(limit=limit, reverse=True)
        
        if not all_records:
            return {
                'success': False,
                'error': 'No records found'
            }
        
        # 数据已经是最新的在前，不需要再反转
        
        # 🔥 重新计算序列号：按照OKX图表逻辑
        # 从转折点（position变化的点）往最新方向数序列号
        # 策略：从最旧往最新遍历，这样序列号才是正向递增
        
        # 第一步：反转数组，从最旧的开始
        all_records_reversed = list(reversed(all_records))
        
        # 第二步：从最旧往最新计算序列号
        for i in range(len(all_records_reversed)):
            if i == 0:
                # 第一条记录（最旧的）序列号从1开始
                all_records_reversed[i]['recalc_sequence'] = 1
            else:
                prev_position = all_records_reversed[i-1].get('position')
                curr_position = all_records_reversed[i].get('position')
                prev_time_str = all_records_reversed[i-1].get('beijing_time', '')
                curr_time_str = all_records_reversed[i].get('beijing_time', '')
                
                # 检查时间连续性
                is_continuous = False
                if prev_time_str and curr_time_str:
                    try:
                        prev_time = datetime.strptime(prev_time_str, '%Y-%m-%d %H:%M:%S')
                        curr_time = datetime.strptime(curr_time_str, '%Y-%m-%d %H:%M:%S')
                        # 注意：all_records_reversed[i-1]是较旧的，all_records_reversed[i]是较新的
                        time_diff_minutes = (curr_time - prev_time).total_seconds() / 60
                        # 时间差在4-6分钟之间认为是连续的
                        is_continuous = 4 <= time_diff_minutes <= 6
                    except:
                        is_continuous = False
                
                if not is_continuous:
                    # 时间不连续，重置序列号为1
                    all_records_reversed[i]['recalc_sequence'] = 1
                elif prev_position == curr_position and is_continuous:
                    # position相同且时间连续，序列号+1
                    all_records_reversed[i]['recalc_sequence'] = all_records_reversed[i-1]['recalc_sequence'] + 1
                else:
                    # position改变，序列号重置为1
                    all_records_reversed[i]['recalc_sequence'] = 1
        
        # 第三步：再反转回来，恢复最新在前的顺序
        all_records = list(reversed(all_records_reversed))
        
        # 预先按position分组记录（优化性能）
        long_records = [r for r in all_records if r.get('position') == 'long']
        short_records = [r for r in all_records if r.get('position') == 'short']
        
        # 构建序列数据
        sequences = []
        for i, record in enumerate(all_records):
            seq_data = {
                'sequence': record.get('recalc_sequence', 1),  # 使用重新计算的序列号
                'price': round(record.get('close', 0), 2),
                'time': record.get('beijing_time', ''),
                'open': round(record.get('open', 0), 2),
                'high': round(record.get('high', 0), 2),
                'low': round(record.get('low', 0), 2),
                'sar': round(record.get('sar', 0), 4),
                'position': record.get('position', ''),
                'position_cn': '多头' if record.get('position') == 'long' else '空头'
            }
            
            # 计算序列变化率（与前一个序列比较）
            if i < len(all_records) - 1:
                next_record = all_records[i + 1]
                curr_position = record.get('position')
                next_position = next_record.get('position')
                
                # 只有当position相同时才计算变化率
                if curr_position == next_position:
                    curr_sar = record.get('sar', 0)
                    next_sar = next_record.get('sar', 0)
                    
                    if curr_position == 'long':
                        # 多头: (当前SAR - 前一个SAR) / 当前SAR
                        seq_change_percent = ((curr_sar - next_sar) / curr_sar) * 100 if curr_sar != 0 else 0
                        sar_absolute_diff = curr_sar - next_sar
                    else:  # short
                        # 空头: (前一个SAR - 当前SAR) / 前一个SAR
                        seq_change_percent = ((next_sar - curr_sar) / next_sar) * 100 if next_sar != 0 else 0
                        sar_absolute_diff = next_sar - curr_sar
                    
                    seq_data['sequence_change_percent'] = round(seq_change_percent, 4)
                    seq_data['sar_diff'] = round(sar_absolute_diff, 4)
                    
                    # 计算历史平均值（优化版，使用预先分组的数据）
                    # 选择对应position的记录集
                    same_position_records = long_records if curr_position == 'long' else short_records
                    
                    # 计算最近1天、3天、7天、15天的平均变化率
                    # 优化：只计算1天平均，其他使用估算
                    def calc_avg_change(records, days):
                        limit = min(days * 288, len(records), 288)  # 最多288条（1天）
                        if limit < 2:
                            return 0
                        
                        changes = []
                        for j in range(min(limit - 1, 50)):  # 只计算前50条，足够准确
                            if j + 1 < len(records):
                                r1 = records[j]
                                r2 = records[j + 1]
                                s1 = r1.get('sar', 0)
                                s2 = r2.get('sar', 0)
                                
                                if curr_position == 'long':
                                    change = ((s1 - s2) / s1) * 100 if s1 != 0 else 0
                                else:
                                    change = ((s2 - s1) / s2) * 100 if s2 != 0 else 0
                                
                                changes.append(change)
                        
                        return sum(changes) / len(changes) if changes else 0
                    
                    avg_1day = calc_avg_change(same_position_records[:288], 1)
                    avg_3day = avg_1day  # 简化：使用1天平均
                    avg_7day = avg_1day  # 简化：使用1天平均
                    avg_15day = avg_1day  # 简化：使用1天平均
                    
                    seq_data['avg_1day'] = round(avg_1day, 6)
                    seq_data['avg_3day'] = round(avg_3day, 6)
                    seq_data['avg_7day'] = round(avg_7day, 6)
                    seq_data['avg_15day'] = round(avg_15day, 6)
                    
                    # 计算相对变化百分比
                    if avg_1day != 0:
                        change_1day_percent = ((seq_change_percent - avg_1day) / avg_1day) * 100
                    else:
                        change_1day_percent = 0
                    
                    if avg_3day != 0:
                        change_3day_percent = ((seq_change_percent - avg_3day) / avg_3day) * 100
                    else:
                        change_3day_percent = 0
                    
                    if avg_7day != 0:
                        change_7day_percent = ((seq_change_percent - avg_7day) / avg_7day) * 100
                    else:
                        change_7day_percent = 0
                    
                    if avg_15day != 0:
                        change_15day_percent = ((seq_change_percent - avg_15day) / avg_15day) * 100
                    else:
                        change_15day_percent = 0
                    
                    diff_1day = seq_change_percent - avg_1day
                    
                    seq_data['change_1day_percent'] = round(change_1day_percent, 2)
                    seq_data['change_3day_percent'] = round(change_3day_percent, 2)
                    seq_data['change_7day_percent'] = round(change_7day_percent, 2)
                    seq_data['change_15day_percent'] = round(change_15day_percent, 2)
                    
                    # 判断偏向
                    if curr_position == 'long':
                        bias = '偏多' if diff_1day < 0 else '偏空'
                    else:
                        bias = '偏空' if diff_1day < 0 else '偏多'
                    
                    seq_data['bias'] = bias
            
            sequences.append(seq_data)
        
        # 计算最近2小时的偏多/偏空比例
        recent_2hours = sequences[:24]  # 取最新的24条数据
        
        bias_bullish_count = sum(1 for s in recent_2hours if s.get('bias') == '偏多')
        bias_bearish_count = sum(1 for s in recent_2hours if s.get('bias') == '偏空')
        
        total_bias = bias_bullish_count + bias_bearish_count
        bias_bullish_percent = (bias_bullish_count / total_bias * 100) if total_bias > 0 else 0
        bias_bearish_percent = (bias_bearish_count / total_bias * 100) if total_bias > 0 else 0
        
        # 获取当前周期的序列号（最新记录的序列号）
        current_cycle_sequence = all_records[0].get('recalc_sequence', 1) if all_records else 1
        
        # 构建返回数据
        result = {
            'success': True,
            'symbol': symbol.upper(),
            'current_status': {
                'position': current_status['current_position'],
                'position_cn': '多头' if current_status['current_position'] == 'long' else '空头',
                'sequence': current_cycle_sequence,  # 使用重新计算的序列号
                'last_update': current_status['last_update_time'],
                'latest_price': current_status['latest_price'],
                'latest_sar': round(current_status['latest_sar'], 4),
                'cycle_info': f"序列{current_cycle_sequence}"
            },
            'sequences': sequences,
            'total_sequences': len(sequences),
            'bias_statistics': {
                # 顶层字段，供前端统计使用
                'bullish_ratio': round(bias_bullish_percent, 2),
                'bearish_ratio': round(bias_bearish_percent, 2),
                # 详细统计
                'recent_2hours': {
                    'bullish_count': bias_bullish_count,
                    'bearish_count': bias_bearish_count,
                    'bullish_percent': round(bias_bullish_percent, 2),
                    'bearish_percent': round(bias_bearish_percent, 2)
                }
            },
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)',
            '_from_server_cache': False
        }
        
        return result
        
    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# 测试代码
if __name__ == '__main__':
    import sys
    
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'AAVE'
    
    print(f"测试 SAR API JSONL - {symbol}")
    print("=" * 80)
    
    result = get_sar_current_cycle(symbol)
    
    if result['success']:
        print(f"✓ 成功获取数据")
        print(f"  币种: {result['symbol']}")
        print(f"  当前状态:")
        print(f"    位置: {result['current_status']['position']}")
        print(f"    序列: {result['current_status']['sequence']}")
        print(f"    最新价格: {result['current_status']['latest_price']}")
        print(f"    最新SAR: {result['current_status']['latest_sar']}")
        print(f"  序列总数: {result['total_sequences']}")
        print(f"  数据源: {result['data_source']}")
        print(f"\n  最新3条序列:")
        for i, seq in enumerate(result['sequences'][:3]):
            print(f"    [{i+1}] {seq['time']} | {seq['position_cn']} #{seq['sequence']} | "
                  f"价格: {seq['price']} | SAR: {seq['sar']}")
    else:
        print(f"✗ 获取失败: {result.get('error')}")
