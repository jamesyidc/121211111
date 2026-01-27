#!/usr/bin/env python3
"""
技术指标自动同步脚本
功能：为所有K线数据计算并更新技术指标（RSI、SAR、布林带等）
直接从 okex_kline_ohlc 表读取OHLC数据，计算技术指标并存储到 kline_technical_markers 表
不依赖 okex_indicators_history 表
"""

import sqlite3
import pandas as pd
import numpy as np
import talib
from datetime import datetime
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 监控的币种列表（全部27个币种）
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP', 
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

TIMEFRAMES = ['5m', '1H']

# 窄幅震荡阈值
NARROW_RANGE_CHANGE_THRESHOLD = 0.25  # 涨跌幅 <= 0.25%
NARROW_RANGE_RANGE_THRESHOLD = 0.50   # 振幅 <= 0.50%

def get_ohlc_data(symbol, timeframe):
    """从 okex_kline_ohlc 表获取OHLC数据"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, open, high, low, close, volume
        FROM okex_kline_ohlc
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    ''', (symbol, timeframe))
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows

def calculate_technical_indicators(ohlc_data):
    """
    使用 TA-Lib 计算技术指标
    返回：包含所有技术指标的 DataFrame
    """
    if len(ohlc_data) < 30:
        return None
    
    # 转换为 DataFrame
    df = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # 转换数据类型
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # 转换为 numpy 数组（TA-Lib 要求）
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    # 1. RSI (14周期)
    df['rsi_14'] = talib.RSI(closes, timeperiod=14)
    
    # 2. Parabolic SAR
    df['sar'] = talib.SAR(highs, lows, acceleration=0.02, maximum=0.2)
    
    # 3. 布林带 (20周期, 2倍标准差)
    bb_upper, bb_middle, bb_lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)
    df['bb_upper'] = bb_upper
    df['bb_middle'] = bb_middle
    df['bb_lower'] = bb_lower
    
    # 4. SAR 多空判断（根据价格与SAR的关系）
    df['sar_position'] = df.apply(
        lambda row: 'bullish' if pd.notna(row['sar']) and row['close'] > row['sar'] else 'bearish' if pd.notna(row['sar']) else None,
        axis=1
    )
    
    # 5. SAR 象限（相对布林带）
    def calculate_quadrant(row):
        if pd.isna(row['sar']) or pd.isna(row['bb_upper']):
            return None
        if row['sar'] > row['bb_upper']:
            return 1
        elif row['sar'] > row['bb_middle']:
            return 2
        elif row['sar'] > row['bb_lower']:
            return 3
        else:
            return 4
    
    df['sar_quadrant'] = df.apply(calculate_quadrant, axis=1)
    
    # 6. SAR 连续计数标签
    df['consecutive_count'] = 0
    df['sar_count_label'] = None
    
    for i in range(len(df)):
        if pd.isna(df.loc[i, 'sar_position']):
            continue
        
        current_position = df.loc[i, 'sar_position']
        count = 1
        
        # 向前计数连续相同位置
        for j in range(i - 1, -1, -1):
            if pd.isna(df.loc[j, 'sar_position']):
                break
            if df.loc[j, 'sar_position'] == current_position:
                count += 1
            else:
                break
        
        df.loc[i, 'consecutive_count'] = count
        label = '多头' if current_position == 'bullish' else '空头'
        df.loc[i, 'sar_count_label'] = f"{label}{count:02d}"
    
    # 7. 窄幅震荡判断
    df['change_percent'] = ((df['close'] - df['open']) / df['open'] * 100).abs()
    df['range_percent'] = ((df['high'] - df['low']) / df['low'] * 100)
    df['is_narrow_range'] = (
        (df['change_percent'] <= NARROW_RANGE_CHANGE_THRESHOLD) & 
        (df['range_percent'] <= NARROW_RANGE_RANGE_THRESHOLD)
    )
    
    # 8. 计算连续窄幅震荡区域
    df['narrow_consecutive'] = 0
    current_count = 0
    
    for i in range(len(df)):
        if df.loc[i, 'is_narrow_range']:
            current_count += 1
            df.loc[i, 'narrow_consecutive'] = current_count
        else:
            current_count = 0
    
    # 9. 7天和48小时高低点
    df['is_7d_high'] = False
    df['is_7d_low'] = False
    df['is_48h_high'] = False
    df['is_48h_low'] = False
    
    # 计算时间窗口（假设5m=288根/天，1H=24根/天）
    if len(df) > 0:
        # 7天高低点：只标记最近7天的全局极值
        window_7d = 2016 if 'm' in str(df['timestamp'].iloc[0]) else 168  # 7*24*12 或 7*24
        if len(df) >= window_7d:
            recent_7d = df.tail(window_7d)
            # 找到7天内的最高点和最低点（如果有多个相同极值，标记最近的一个）
            max_high_idx = recent_7d['high'].idxmax()
            min_low_idx = recent_7d['low'].idxmin()
            df.loc[max_high_idx, 'is_7d_high'] = True
            df.loc[min_low_idx, 'is_7d_low'] = True
        else:
            # 数据不足7天，标记所有数据中的极值
            if len(df) > 0:
                max_high_idx = df['high'].idxmax()
                min_low_idx = df['low'].idxmin()
                df.loc[max_high_idx, 'is_7d_high'] = True
                df.loc[min_low_idx, 'is_7d_low'] = True
        
        # 48小时高低点：只标记最近48小时的全局极值
        window_48h = 576 if 'm' in str(df['timestamp'].iloc[0]) else 48  # 48*12 或 48
        if len(df) >= window_48h:
            recent_48h = df.tail(window_48h)
            # 找到48小时内的最高点和最低点（如果有多个相同极值，标记最近的一个）
            max_high_idx = recent_48h['high'].idxmax()
            min_low_idx = recent_48h['low'].idxmin()
            df.loc[max_high_idx, 'is_48h_high'] = True
            df.loc[min_low_idx, 'is_48h_low'] = True
        else:
            # 数据不足48小时，标记所有数据中的极值
            if len(df) > 0:
                max_high_idx = df['high'].idxmax()
                min_low_idx = df['low'].idxmin()
                df.loc[max_high_idx, 'is_48h_high'] = True
                df.loc[min_low_idx, 'is_48h_low'] = True
    
    # 10. 买点4检测（7天低点后2根不创新低）
    df['is_buy_point_4'] = False
    
    for i in range(2, len(df)):
        if df.loc[i-2, 'is_7d_low']:
            # 检查后两根是否不创新低
            if (df.loc[i-1, 'low'] >= df.loc[i-2, 'low'] and 
                df.loc[i, 'low'] >= df.loc[i-2, 'low']):
                df.loc[i, 'is_buy_point_4'] = True
    
    return df

def save_indicators_to_db(symbol, timeframe, df):
    """将技术指标数据保存到 kline_technical_markers 表"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    insert_count = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO kline_technical_markers
                (symbol, timeframe, timestamp, 
                 is_narrow_range, change_percent, range_percent, consecutive_count,
                 is_7d_high, is_7d_low, is_48h_high, is_48h_low,
                 rsi_14, sar, sar_position, sar_quadrant, sar_count_label,
                 bb_upper, bb_middle, bb_lower, is_buy_point_4)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, timeframe, int(row['timestamp']),
                1 if row['is_narrow_range'] else 0,
                float(row['change_percent']) if pd.notna(row['change_percent']) else None,
                float(row['range_percent']) if pd.notna(row['range_percent']) else None,
                int(row['narrow_consecutive']),
                1 if row['is_7d_high'] else 0,
                1 if row['is_7d_low'] else 0,
                1 if row['is_48h_high'] else 0,
                1 if row['is_48h_low'] else 0,
                float(row['rsi_14']) if pd.notna(row['rsi_14']) else None,
                float(row['sar']) if pd.notna(row['sar']) else None,
                row['sar_position'] if pd.notna(row['sar_position']) else None,
                int(row['sar_quadrant']) if pd.notna(row['sar_quadrant']) else None,
                row['sar_count_label'] if pd.notna(row['sar_count_label']) else None,
                float(row['bb_upper']) if pd.notna(row['bb_upper']) else None,
                float(row['bb_middle']) if pd.notna(row['bb_middle']) else None,
                float(row['bb_lower']) if pd.notna(row['bb_lower']) else None,
                1 if row['is_buy_point_4'] else 0
            ))
            insert_count += 1
        except Exception as e:
            print(f"  ⚠️  保存失败 timestamp={row['timestamp']}: {e}")
    
    conn.commit()
    conn.close()
    
    return insert_count

def sync_symbol_indicators(symbol, timeframe):
    """同步单个币种的技术指标"""
    print(f"\n📊 处理 {symbol} {timeframe}")
    
    # 1. 获取OHLC数据
    ohlc_data = get_ohlc_data(symbol, timeframe)
    
    if not ohlc_data:
        print(f"  ⚠️  没有OHLC数据")
        return
    
    print(f"  ✅ 读取 {len(ohlc_data)} 根K线")
    
    # 2. 计算技术指标
    df = calculate_technical_indicators(ohlc_data)
    
    if df is None:
        print(f"  ⚠️  数据不足，无法计算指标")
        return
    
    # 统计指标覆盖率
    has_rsi = df['rsi_14'].notna().sum()
    has_sar = df['sar'].notna().sum()
    has_bb = df['bb_upper'].notna().sum()
    
    print(f"  📈 指标统计: RSI={has_rsi}/{len(df)}, SAR={has_sar}/{len(df)}, BB={has_bb}/{len(df)}")
    
    # 3. 保存到数据库
    insert_count = save_indicators_to_db(symbol, timeframe, df)
    
    print(f"  ✅ 插入/更新: {insert_count} 条记录")

def main():
    """主函数"""
    print("=" * 80)
    print("🚀 技术指标自动同步系统")
    print("=" * 80)
    print(f"⏰ 开始时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"📊 币种数量: {len(SYMBOLS)}")
    print(f"⏱️  时间周期: {', '.join(TIMEFRAMES)}")
    print(f"📈 技术指标: RSI(14), SAR, 布林带(20,2), 窄幅震荡, 高低点, 买点4")
    print(f"🔧 计算引擎: TA-Lib (高性能C库)")
    print("=" * 80)
    
    success_count = 0
    failed_count = 0
    
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                sync_symbol_indicators(symbol, timeframe)
                success_count += 1
            except Exception as e:
                print(f"\n❌ {symbol} {timeframe} 失败: {e}")
                import traceback
                traceback.print_exc()
                failed_count += 1
    
    print("\n" + "=" * 80)
    print(f"✅ 同步完成")
    print(f"   成功: {success_count}/{success_count + failed_count}")
    print(f"   失败: {failed_count}")
    print(f"⏰ 完成时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print("=" * 80)

if __name__ == '__main__':
    main()
