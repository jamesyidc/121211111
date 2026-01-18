#!/usr/bin/env python3
"""
SAR API适配器 - 从JSONL读取数据
将现有的SQLite API适配为JSONL数据源
所有时间使用北京时间
"""
from flask import jsonify
from sar_jsonl_manager import SARJSONLManager
import time

manager = SARJSONLManager()


def sar_slope_current_cycle_jsonl(symbol):
    """
    从JSONL获取当前完整周期的所有序列数据
    返回格式与原SQLite API兼容
    所有时间为北京时间
    """
    try:
        # 获取币种数据
        symbol = symbol.upper()
        
        # 获取最新记录（当前状态）
        latest = manager.get_latest_record(symbol)
        if not latest:
            return jsonify({'success': False, 'error': 'Symbol not found'})
        
        current_position = latest['position']
        current_sequence = latest['sequence']
        last_update = latest['beijing_time']  # 北京时间
        
        # 获取最近16天的数据（约4608条，16天 * 288条/天）
        max_records = 4608
        all_data = manager.read_symbol_data(symbol, limit=max_records, order='DESC')
        
        if not all_data:
            return jsonify({'success': False, 'error': 'No data found'})
        
        # 构建序列数据
        raw_sequences = []
        for record in all_data:
            raw_sequences.append({
                'sequence': record['sequence'],
                'price': round(record['close'], 2),
                'time': record['beijing_time'],  # 北京时间
                'open': round(record['open'], 2),
                'high': round(record['high'], 2),
                'low': round(record['low'], 2),
                'sar': record['sar'],
                'position': record['position']
            })
        
        # 计算变化率和历史平均值
        sequences_with_changes = []
        
        for i, seq_data in enumerate(raw_sequences):
            seq_num = seq_data['sequence']
            row_position = seq_data['position']
            
            result_data = {
                'sequence': seq_num,
                'price': seq_data['price'],
                'time': seq_data['time'],  # 北京时间
                'open': seq_data['open'],
                'high': seq_data['high'],
                'low': seq_data['low'],
                'sar': round(seq_data['sar'], 4),
                'position': row_position,
                'position_cn': '多头' if row_position == 'long' else '空头'
            }
            
            # 计算序列变化率
            if i < len(raw_sequences) - 1:
                next_data = raw_sequences[i + 1]
                next_position = next_data['position']
                
                # 只有当position相同时才计算变化率
                if row_position == next_position:
                    curr_sar = seq_data['sar']
                    next_sar = next_data['sar']
                    
                    if row_position == 'long':
                        seq_change_percent = ((curr_sar - next_sar) / curr_sar) * 100 if curr_sar != 0 else 0
                        sar_absolute_diff = curr_sar - next_sar
                    else:  # short
                        seq_change_percent = ((next_sar - curr_sar) / next_sar) * 100 if next_sar != 0 else 0
                        sar_absolute_diff = next_sar - curr_sar
                    
                    result_data['sequence_change_percent'] = round(seq_change_percent, 4)
                    result_data['sar_diff'] = round(sar_absolute_diff, 4)
                    
                    # 计算历史平均（简化版本，从当前位置往后查找相同position和sequence的历史数据）
                    historical_changes = []
                    for j in range(i + 1, min(i + 1 + 4320, len(raw_sequences))):  # 最多查找4320条（15天）
                        hist_rec = raw_sequences[j]
                        if hist_rec['position'] == row_position and hist_rec['sequence'] == seq_num:
                            # 计算这条历史记录的变化率
                            if j < len(raw_sequences) - 1:
                                hist_next = raw_sequences[j + 1]
                                if hist_next['position'] == row_position:
                                    curr_sar_hist = hist_rec['sar']
                                    next_sar_hist = hist_next['sar']
                                    
                                    if row_position == 'long':
                                        hist_change = ((curr_sar_hist - next_sar_hist) / curr_sar_hist) * 100 if curr_sar_hist != 0 else 0
                                    else:
                                        hist_change = ((next_sar_hist - curr_sar_hist) / next_sar_hist) * 100 if next_sar_hist != 0 else 0
                                    
                                    historical_changes.append(hist_change)
                    
                    # 计算不同周期的平均值
                    if historical_changes:
                        avg_1day = sum(historical_changes[:288]) / len(historical_changes[:288]) if len(historical_changes) >= 1 else 0
                        avg_3day = sum(historical_changes[:864]) / len(historical_changes[:864]) if len(historical_changes) >= 1 else avg_1day
                        avg_7day = sum(historical_changes[:2016]) / len(historical_changes[:2016]) if len(historical_changes) >= 1 else avg_1day
                        avg_15day = sum(historical_changes[:4320]) / len(historical_changes[:4320]) if len(historical_changes) >= 1 else avg_1day
                        
                        result_data['avg_1day'] = round(avg_1day, 6)
                        result_data['avg_3day'] = round(avg_3day, 6)
                        result_data['avg_7day'] = round(avg_7day, 6)
                        result_data['avg_15day'] = round(avg_15day, 6)
                        
                        # 计算变化百分比
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
                        
                        result_data['change_1day_percent'] = round(change_1day_percent, 2)
                        result_data['change_3day_percent'] = round(change_3day_percent, 2)
                        result_data['change_7day_percent'] = round(change_7day_percent, 2)
                        result_data['change_15day_percent'] = round(change_15day_percent, 2)
                        
                        # 判断偏向
                        if row_position == 'long':
                            bias = '偏多' if diff_1day < 0 else '偏空'
                        else:
                            bias = '偏空' if diff_1day < 0 else '偏多'
                        
                        result_data['bias'] = bias
            
            sequences_with_changes.append(result_data)
        
        # 计算最近2小时的偏向统计
        recent_2hours = sequences_with_changes[:24]  # 最新24条（2小时）
        
        bias_bullish_count = 0
        bias_bearish_count = 0
        bias_neutral_count = 0
        
        for seq in recent_2hours:
            if 'bias' in seq:
                if seq['bias'] == '偏多':
                    bias_bullish_count += 1
                elif seq['bias'] == '偏空':
                    bias_bearish_count += 1
                else:
                    bias_neutral_count += 1
            else:
                bias_neutral_count += 1
        
        total_bias_records = bias_bullish_count + bias_bearish_count + bias_neutral_count
        
        # 构建周期信息
        # 找到当前周期的起点（sequence == 1）
        cycle_start_index = -1
        for idx, seq in enumerate(sequences_with_changes):
            if seq['sequence'] == 1 and seq['position'] == current_position:
                cycle_start_index = idx
                break
        
        if cycle_start_index >= 0:
            cycle_sequences = sequences_with_changes[:cycle_start_index + 1]
            cycle_info = f"{current_position}01 → {current_position}{current_sequence:02d}"
        else:
            cycle_sequences = sequences_with_changes
            cycle_info = f"{current_position}01 → {current_position}{current_sequence:02d}"
        
        # 返回结果
        result = {
            'success': True,
            'symbol': symbol,
            'total_sequences': len(cycle_sequences),
            'current_status': {
                'position': current_position,
                'position_cn': '多头' if current_position == 'long' else '空头',
                'current_sequence': current_sequence,
                'cycle_info': cycle_info,
                'last_update': last_update  # 北京时间
            },
            'bias_statistics': {
                'total_records': total_bias_records,
                'bullish_count': bias_bullish_count,
                'bearish_count': bias_bearish_count,
                'neutral_count': bias_neutral_count,
                'bullish_ratio': round(bias_bullish_count / total_bias_records * 100, 1) if total_bias_records > 0 else 0,
                'bearish_ratio': round(bias_bearish_count / total_bias_records * 100, 1) if total_bias_records > 0 else 0
            },
            'sequences': cycle_sequences,
            '_data_source': 'JSONL',
            '_timezone': 'Asia/Shanghai (北京时间)'
        }
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


# 测试函数（不使用Flask context）
def test_api():
    """测试API适配器（不依赖Flask）"""
    print("测试 AAVE 数据（北京时间）\n")
    
    try:
        symbol = 'AAVE'
        latest = manager.get_latest_record(symbol)
        
        if latest:
            print(f"✅ 币种: {symbol}")
            print(f"✅ 数据源: JSONL")
            print(f"✅ 时区: Asia/Shanghai (北京时间)")
            print(f"✅ 当前状态: {'多头' if latest['position'] == 'long' else '空头'}")
            print(f"✅ 当前序列: {latest['sequence']}")
            print(f"✅ 最后更新: {latest['beijing_time']} (北京时间)")
            
            # 获取最新几条数据
            recent_data = manager.read_symbol_data(symbol, limit=5, order='DESC')
            print(f"\n最新5条数据:")
            for i, record in enumerate(recent_data, 1):
                print(f"  {i}. {record['beijing_time']} (北京时间) | 序列#{record['sequence']:02d} | "
                      f"价格={record['close']:.2f} | SAR={record['sar']:.4f} | "
                      f"{'多头' if record['position'] == 'long' else '空头'}")
        else:
            print(f"❌ 未找到 {symbol} 数据")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ 错误: {e}")


if __name__ == '__main__':
    test_api()
