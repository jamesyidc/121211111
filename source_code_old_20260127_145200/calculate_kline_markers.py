#!/usr/bin/env python3
"""
计算并存储K线技术指标标记
包括：窄幅震荡、7天高低点、48小时高低点
"""
import sqlite3
from datetime import datetime

def calculate_narrow_range_markers(symbol, timeframe):
    """计算窄幅震荡标记"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 获取OHLC数据
    cursor.execute('''
        SELECT timestamp, open, high, low, close
        FROM okex_kline_ohlc
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    ''', (symbol, timeframe))
    
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  ⚠️  {symbol} {timeframe} 无数据")
        conn.close()
        return
    
    print(f"  📊 处理 {symbol} {timeframe}: {len(rows)} 条数据")
    
    max_change_percent = 0.25  # 涨跌幅阈值 0.25%
    max_range_percent = 0.50   # 震荡幅度阈值 0.50%
    
    narrow_range_records = []
    consecutive_groups = []
    
    # 第一遍：检测窄幅震荡
    for i, (timestamp, open_price, high, low, close) in enumerate(rows):
        if open_price == 0:
            continue
        
        # 计算涨跌幅和震荡幅度
        change_percent = abs((close - open_price) / open_price * 100)
        range_percent = (high - low) / open_price * 100
        
        is_narrow = (change_percent <= max_change_percent and range_percent <= max_range_percent)
        
        narrow_range_records.append({
            'timestamp': timestamp,
            'is_narrow': is_narrow,
            'change_percent': change_percent,
            'range_percent': range_percent
        })
    
    # 第二遍：计算连续根数
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
    
    # 处理最后一组
    if consecutive_count >= 2:
        consecutive_groups.append({
            'timestamps': current_group,
            'count': consecutive_count
        })
    
    # 第三遍：写入数据库
    insert_count = 0
    for record in narrow_range_records:
        # 查找该时间戳属于哪个连续组
        consecutive_count = 0
        for group in consecutive_groups:
            if record['timestamp'] in group['timestamps']:
                consecutive_count = group['count']
                break
        
        cursor.execute('''
            INSERT OR REPLACE INTO kline_technical_markers 
            (symbol, timeframe, timestamp, is_narrow_range, change_percent, range_percent, consecutive_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol, timeframe, record['timestamp'], 
            1 if record['is_narrow'] else 0,
            record['change_percent'],
            record['range_percent'],
            consecutive_count
        ))
        insert_count += 1
    
    conn.commit()
    
    narrow_count = sum(1 for r in narrow_range_records if r['is_narrow'])
    print(f"  ✅ 窄幅震荡: {narrow_count}/{len(rows)} 条，{len(consecutive_groups)} 个连续区域")
    
    conn.close()
    return narrow_count, len(consecutive_groups)


def calculate_high_low_markers(symbol, timeframe):
    """计算7天和48小时高低点标记"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 获取OHLC数据
    cursor.execute('''
        SELECT timestamp, open, high, low, close
        FROM okex_kline_ohlc
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    ''', (symbol, timeframe))
    
    rows = cursor.fetchall()
    
    if not rows:
        conn.close()
        return
    
    # 使用最后一条数据的时间戳作为基准
    latest_timestamp = rows[-1][0]
    seven_days_ms = 7 * 24 * 60 * 60 * 1000
    forty_eight_hours_ms = 48 * 60 * 60 * 1000
    
    # 找到7天和48小时的起始索引
    seven_day_start_idx = 0
    forty_eight_hour_start_idx = 0
    
    for i, (timestamp, _, _, _, _) in enumerate(rows):
        age = latest_timestamp - timestamp
        if age <= seven_days_ms and seven_day_start_idx == 0:
            seven_day_start_idx = i
        if age <= forty_eight_hours_ms and forty_eight_hour_start_idx == 0:
            forty_eight_hour_start_idx = i
    
    # 7天最高点和最低点
    seven_day_data = rows[seven_day_start_idx:]
    seven_day_high_idx = seven_day_start_idx
    seven_day_low_idx = seven_day_start_idx
    seven_day_high = seven_day_data[0][2]  # high
    seven_day_low = seven_day_data[0][3]   # low
    
    for i, (timestamp, _, high, low, _) in enumerate(seven_day_data):
        idx = seven_day_start_idx + i
        if high > seven_day_high:
            seven_day_high = high
            seven_day_high_idx = idx
        if low < seven_day_low:
            seven_day_low = low
            seven_day_low_idx = idx
    
    # 48小时最高点和最低点
    forty_eight_hour_data = rows[forty_eight_hour_start_idx:]
    h48_high_idx = forty_eight_hour_start_idx
    h48_low_idx = forty_eight_hour_start_idx
    h48_high = forty_eight_hour_data[0][2]
    h48_low = forty_eight_hour_data[0][3]
    
    for i, (timestamp, _, high, low, _) in enumerate(forty_eight_hour_data):
        idx = forty_eight_hour_start_idx + i
        if high > h48_high:
            h48_high = high
            h48_high_idx = idx
        if low < h48_low:
            h48_low = low
            h48_low_idx = idx
    
    # 标记高低点
    mark_timestamps = {
        rows[seven_day_high_idx][0]: {'is_7d_high': 1},
        rows[seven_day_low_idx][0]: {'is_7d_low': 1},
        rows[h48_high_idx][0]: {'is_48h_high': 1},
        rows[h48_low_idx][0]: {'is_48h_low': 1}
    }
    
    for timestamp, marks in mark_timestamps.items():
        cursor.execute('''
            INSERT OR IGNORE INTO kline_technical_markers 
            (symbol, timeframe, timestamp, is_7d_high, is_7d_low, is_48h_high, is_48h_low)
            VALUES (?, ?, ?, 0, 0, 0, 0)
        ''', (symbol, timeframe, timestamp))
        
        for mark_type, value in marks.items():
            cursor.execute(f'''
                UPDATE kline_technical_markers
                SET {mark_type} = ?
                WHERE symbol = ? AND timeframe = ? AND timestamp = ?
            ''', (value, symbol, timeframe, timestamp))
    
    conn.commit()
    
    print(f"  ✅ 高低点: 7天({seven_day_high:.4f}/{seven_day_low:.4f}), 48小时({h48_high:.4f}/{h48_low:.4f})")
    
    conn.close()


def main():
    print("=" * 80)
    print("K线技术指标计算")
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
            
            # 计算窄幅震荡
            try:
                calculate_narrow_range_markers(symbol_full, timeframe)
            except Exception as e:
                print(f"  ❌ 窄幅震荡计算失败: {e}")
            
            # 计算高低点
            try:
                calculate_high_low_markers(symbol_full, timeframe)
            except Exception as e:
                print(f"  ❌ 高低点计算失败: {e}")
    
    print(f"\n{'='*80}")
    print("✅ 所有指标计算完成！")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
