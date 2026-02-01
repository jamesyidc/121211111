#!/usr/bin/env python3
"""
计算并存储K线技术指标标记 V2
包括：
- 窄幅震荡、7天高低点、48小时高低点
- SAR、布林带、RSI
- SAR多空判断、SAR象限、多空支持时间
- 买点4检测
"""
import sqlite3
from datetime import datetime

def get_indicator_data(symbol, timeframe):
    """从 okex_indicators_history 获取技术指标数据"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, current_price, rsi_14, sar, sar_position, sar_count_label,
               bb_upper, bb_middle, bb_lower
        FROM okex_indicators_history
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    ''', (symbol, timeframe))
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows

def calculate_sar_position(close, sar):
    """
    判断SAR多空
    多头：K线在SAR上方 (close > sar)
    空头：K线在SAR下方 (close <= sar)
    """
    if close > sar:
        return 'bullish'  # 多头
    else:
        return 'bearish'  # 空头

def calculate_sar_quadrant(sar, bb_upper, bb_middle, bb_lower):
    """
    计算SAR在布林带的象限
    第1象限: sar > bb_upper
    第2象限: bb_middle < sar <= bb_upper
    第3象限: bb_lower < sar <= bb_middle
    第4象限: sar <= bb_lower
    """
    if sar > bb_upper:
        return 1
    elif sar > bb_middle:
        return 2
    elif sar > bb_lower:
        return 3
    else:
        return 4

def calculate_sar_count_labels(positions):
    """
    计算多空支持时间标签
    多转空：当SAR从K线下方转到上方，开始计数：空头01、空头02...
    空转多：当SAR从K线上方转到下方，开始计数：多头01、多头02...
    """
    labels = []
    current_position = None
    count = 0
    
    for position in positions:
        if current_position is None:
            current_position = position
            count = 1
        elif current_position == position:
            count += 1
        else:
            # 发生转换
            current_position = position
            count = 1
        
        if position == 'bullish':
            labels.append(f'多头{count:02d}')
        else:
            labels.append(f'空头{count:02d}')
    
    return labels

def detect_buy_point_4(rows, ohlc_data, seven_day_low_idx):
    """
    检测买点4
    条件：
    1. 7day低点后2根不创新低
    2. 前后5分钟内（对于5m周期，前后1根K线），出现过：
       - 情况1 >= 8
       - 情况2 >= 8
    
    注意：这里的"情况1"和"情况2"需要您明确定义
    暂时返回空列表，待您补充逻辑
    """
    buy_point_4_indices = []
    
    if not ohlc_data or seven_day_low_idx is None:
        return buy_point_4_indices
    
    # 找到7天低点后2根的位置
    check_idx = seven_day_low_idx + 2
    
    if check_idx >= len(ohlc_data):
        return buy_point_4_indices
    
    # 检查是否不创新低
    seven_day_low_price = ohlc_data[seven_day_low_idx][3]  # low
    
    # 检查后2根K线的低点
    for i in range(seven_day_low_idx + 1, min(check_idx + 1, len(ohlc_data))):
        current_low = ohlc_data[i][3]
        if current_low < seven_day_low_price:
            # 创新低了，不符合条件
            return buy_point_4_indices
    
    # TODO: 这里需要添加"情况1 >= 8"和"情况2 >= 8"的检测逻辑
    # 由于您没有提供"情况1"和"情况2"的具体定义，这里暂时标记为True
    condition_1_met = True  # 请替换为实际逻辑
    condition_2_met = True  # 请替换为实际逻辑
    
    if condition_1_met and condition_2_met:
        buy_point_4_indices.append(check_idx)
    
    return buy_point_4_indices

def calculate_all_markers(symbol, timeframe):
    """计算所有技术标记"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 获取OHLC数据
    cursor.execute('''
        SELECT timestamp, open, high, low, close
        FROM okex_kline_ohlc
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    ''', (symbol, timeframe))
    
    ohlc_rows = cursor.fetchall()
    
    if not ohlc_rows:
        print(f"  ⚠️  {symbol} {timeframe} 无OHLC数据")
        conn.close()
        return
    
    # 获取技术指标数据
    indicator_rows = get_indicator_data(symbol, timeframe)
    
    if not indicator_rows:
        print(f"  ⚠️  {symbol} {timeframe} 无技术指标数据")
        conn.close()
        return
    
    print(f"  📊 处理 {symbol} {timeframe}: OHLC={len(ohlc_rows)}, 指标={len(indicator_rows)}")
    
    # 创建时间戳到指标的映射
    indicator_map = {}
    for row in indicator_rows:
        timestamp = row[0]
        indicator_map[timestamp] = {
            'current_price': row[1],
            'rsi_14': row[2],
            'sar': row[3],
            'sar_position_db': row[4],  # 数据库中的position
            'sar_count_label_db': row[5],  # 数据库中的count label
            'bb_upper': row[6],
            'bb_middle': row[7],
            'bb_lower': row[8]
        }
    
    # 计算窄幅震荡
    max_change_percent = 0.25
    max_range_percent = 0.50
    narrow_range_records = []
    consecutive_groups = []
    
    for i, (timestamp, open_price, high, low, close) in enumerate(ohlc_rows):
        if open_price == 0:
            continue
        
        change_percent = abs((close - open_price) / open_price * 100)
        range_percent = (high - low) / open_price * 100
        is_narrow = (change_percent <= max_change_percent and range_percent <= max_range_percent)
        
        narrow_range_records.append({
            'timestamp': timestamp,
            'is_narrow': is_narrow,
            'change_percent': change_percent,
            'range_percent': range_percent
        })
    
    # 计算连续窄幅震荡组
    consecutive_count = 0
    current_group = []
    
    for record in narrow_range_records:
        if record['is_narrow']:
            consecutive_count += 1
            current_group.append(record['timestamp'])
        else:
            if consecutive_count >= 2:
                consecutive_groups.append({
                    'timestamps': current_group,
                    'count': consecutive_count
                })
            consecutive_count = 0
            current_group = []
    
    if consecutive_count >= 2:
        consecutive_groups.append({
            'timestamps': current_group,
            'count': consecutive_count
        })
    
    # 计算7天和48小时高低点
    latest_timestamp = ohlc_rows[-1][0]
    seven_days_ms = 7 * 24 * 60 * 60 * 1000
    forty_eight_hours_ms = 48 * 60 * 60 * 1000
    
    seven_day_start_idx = 0
    forty_eight_hour_start_idx = 0
    
    for i, (timestamp, _, _, _, _) in enumerate(ohlc_rows):
        age = latest_timestamp - timestamp
        if age <= seven_days_ms and seven_day_start_idx == 0:
            seven_day_start_idx = i
        if age <= forty_eight_hours_ms and forty_eight_hour_start_idx == 0:
            forty_eight_hour_start_idx = i
    
    # 7天最高低点
    seven_day_high_idx = seven_day_start_idx
    seven_day_low_idx = seven_day_start_idx
    seven_day_high = ohlc_rows[seven_day_start_idx][2]
    seven_day_low = ohlc_rows[seven_day_start_idx][3]
    
    for i in range(seven_day_start_idx, len(ohlc_rows)):
        high = ohlc_rows[i][2]
        low = ohlc_rows[i][3]
        if high > seven_day_high:
            seven_day_high = high
            seven_day_high_idx = i
        if low < seven_day_low:
            seven_day_low = low
            seven_day_low_idx = i
    
    # 48小时最高低点
    h48_high_idx = forty_eight_hour_start_idx
    h48_low_idx = forty_eight_hour_start_idx
    h48_high = ohlc_rows[forty_eight_hour_start_idx][2]
    h48_low = ohlc_rows[forty_eight_hour_start_idx][3]
    
    for i in range(forty_eight_hour_start_idx, len(ohlc_rows)):
        high = ohlc_rows[i][2]
        low = ohlc_rows[i][3]
        if high > h48_high:
            h48_high = high
            h48_high_idx = i
        if low < h48_low:
            h48_low = low
            h48_low_idx = i
    
    # 重新计算SAR position和count labels
    sar_positions = []
    for timestamp, _, _, _, close in ohlc_rows:
        if timestamp in indicator_map:
            sar = indicator_map[timestamp]['sar']
            if sar is not None:
                position = calculate_sar_position(close, sar)
                sar_positions.append(position)
            else:
                sar_positions.append(None)
        else:
            sar_positions.append(None)
    
    # 计算SAR count labels
    sar_count_labels = calculate_sar_count_labels([p for p in sar_positions if p is not None])
    
    # 检测买点4
    buy_point_4_indices = detect_buy_point_4(indicator_rows, ohlc_rows, seven_day_low_idx)
    
    # 写入数据库
    insert_count = 0
    narrow_count = 0
    
    for i, (timestamp, open_price, high, low, close) in enumerate(ohlc_rows):
        # 获取技术指标
        indicators = indicator_map.get(timestamp, {})
        rsi_14 = indicators.get('rsi_14')
        sar = indicators.get('sar')
        bb_upper = indicators.get('bb_upper')
        bb_middle = indicators.get('bb_middle')
        bb_lower = indicators.get('bb_lower')
        
        # SAR position 和 quadrant
        sar_position = None
        sar_quadrant = None
        if sar is not None and bb_upper is not None:
            sar_position = calculate_sar_position(close, sar)
            sar_quadrant = calculate_sar_quadrant(sar, bb_upper, bb_middle, bb_lower)
        
        # SAR count label
        sar_count_label = None
        if i < len(sar_count_labels):
            sar_count_label = sar_count_labels[i]
        
        # 窄幅震荡
        narrow_record = next((r for r in narrow_range_records if r['timestamp'] == timestamp), None)
        is_narrow = 0
        change_percent = 0
        range_percent = 0
        consecutive_count = 0
        
        if narrow_record:
            is_narrow = 1 if narrow_record['is_narrow'] else 0
            change_percent = narrow_record['change_percent']
            range_percent = narrow_record['range_percent']
            
            # 查找连续组
            for group in consecutive_groups:
                if timestamp in group['timestamps']:
                    consecutive_count = group['count']
                    break
            
            if is_narrow:
                narrow_count += 1
        
        # 高低点标记
        is_7d_high = 1 if i == seven_day_high_idx else 0
        is_7d_low = 1 if i == seven_day_low_idx else 0
        is_48h_high = 1 if i == h48_high_idx else 0
        is_48h_low = 1 if i == h48_low_idx else 0
        
        # 买点4
        is_buy_point_4 = 1 if i in buy_point_4_indices else 0
        
        # 插入或更新
        cursor.execute('''
            INSERT OR REPLACE INTO kline_technical_markers 
            (symbol, timeframe, timestamp, 
             is_narrow_range, change_percent, range_percent, consecutive_count,
             is_7d_high, is_7d_low, is_48h_high, is_48h_low,
             rsi_14, sar, sar_position, sar_quadrant, sar_count_label,
             bb_upper, bb_middle, bb_lower, is_buy_point_4)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol, timeframe, timestamp,
            is_narrow, change_percent, range_percent, consecutive_count,
            is_7d_high, is_7d_low, is_48h_high, is_48h_low,
            rsi_14, sar, sar_position, sar_quadrant, sar_count_label,
            bb_upper, bb_middle, bb_lower, is_buy_point_4
        ))
        insert_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"  ✅ 窄幅震荡: {narrow_count}/{len(ohlc_rows)}, {len(consecutive_groups)}个区域")
    print(f"  ✅ 高低点: 7天高={seven_day_high:.4f}(idx={seven_day_high_idx}), 低={seven_day_low:.4f}(idx={seven_day_low_idx})")
    print(f"  ✅ 买点4: {len(buy_point_4_indices)}个")
    print(f"  ✅ 插入/更新: {insert_count}条记录")

def main():
    print("=" * 80)
    print("K线技术指标计算 V2")
    print("=" * 80)
    
    symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'SHIB', 'TON', 'DOT', 'LINK', 'ETC', 'XLM']
    timeframes = ['5m', '1H']
    
    total_symbols = len(symbols)
    
    for idx, symbol in enumerate(symbols, 1):
        symbol_full = f"{symbol}-USDT-SWAP"
        print(f"\n{'='*80}")
        print(f"进度: {idx}/{total_symbols} - {symbol}")
        print(f"{'='*80}")
        
        for timeframe in timeframes:
            print(f"\n⏰ {timeframe} 周期:")
            
            try:
                calculate_all_markers(symbol_full, timeframe)
            except Exception as e:
                print(f"  ❌ 计算失败: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("✅ 所有指标计算完成！")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
