#!/usr/bin/env python3
"""
回填历史K线的指标数据
"""
import sqlite3
import talib
import numpy as np
from datetime import datetime

def calculate_indicators_for_kline(closes, highs, lows, volumes, period=14):
    """计算技术指标"""
    if len(closes) < period + 20:
        return None
    
    try:
        # 转换为numpy数组
        closes_np = np.array(closes, dtype=float)
        highs_np = np.array(highs, dtype=float)
        lows_np = np.array(lows, dtype=float)
        
        # RSI
        rsi = talib.RSI(closes_np, timeperiod=period)
        
        # SAR
        sar = talib.SAR(highs_np, lows_np, acceleration=0.02, maximum=0.2)
        
        # 布林带
        bb_upper, bb_middle, bb_lower = talib.BBANDS(closes_np, timeperiod=20, nbdevup=2, nbdevdn=2)
        
        # 最后一个值
        current_price = closes[-1]
        current_rsi = rsi[-1]
        current_sar = sar[-1]
        current_bb_upper = bb_upper[-1]
        current_bb_middle = bb_middle[-1]
        current_bb_lower = bb_lower[-1]
        
        # SAR位置
        sar_position = 'bullish' if current_sar < current_price else 'bearish'
        
        # SAR计数（简化版）
        sar_count = 0
        for i in range(len(sar)-1, max(0, len(sar)-20), -1):
            if not np.isnan(sar[i]):
                current_pos = 'bullish' if sar[i] < closes[i] else 'bearish'
                if current_pos == sar_position:
                    sar_count += 1
                else:
                    break
        
        sar_label = f"{'多头' if sar_position == 'bullish' else '空头'}{min(sar_count, 20):02d}"
        
        return {
            'current_price': current_price,
            'rsi_14': current_rsi if not np.isnan(current_rsi) else None,
            'sar': current_sar if not np.isnan(current_sar) else None,
            'sar_position': sar_position,
            'sar_count_label': sar_label,
            'bb_upper': current_bb_upper if not np.isnan(current_bb_upper) else None,
            'bb_middle': current_bb_middle if not np.isnan(current_bb_middle) else None,
            'bb_lower': current_bb_lower if not np.isnan(current_bb_lower) else None,
        }
    except Exception as e:
        print(f"计算指标失败: {e}")
        return None

def backfill_symbol(symbol, timeframe='5m'):
    """回填单个币种的指标"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 选择K线表
    table = 'okex_kline_5m' if timeframe == '5m' else 'okex_kline_1h'
    
    # 获取所有K线数据
    cursor.execute(f"""
        SELECT timestamp, open, high, low, close, volume
        FROM {table}
        WHERE symbol = ?
        ORDER BY timestamp ASC
    """, (symbol,))
    
    klines = cursor.fetchall()
    
    if len(klines) < 40:
        print(f"⚠️  {symbol} K线数据不足({len(klines)}条)，跳过")
        conn.close()
        return 0
    
    saved_count = 0
    
    # 对每根K线计算指标（需要至少前40根K线的数据）
    for i in range(40, len(klines)):
        # 取前i+1根K线计算指标
        hist_klines = klines[:i+1]
        
        closes = [k[4] for k in hist_klines]
        highs = [k[2] for k in hist_klines]
        lows = [k[3] for k in hist_klines]
        volumes = [k[5] for k in hist_klines]
        
        indicators = calculate_indicators_for_kline(closes, highs, lows, volumes)
        
        if indicators:
            timestamp = klines[i][0]
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 插入到历史指标表
            cursor.execute("""
                INSERT OR REPLACE INTO okex_indicators_history
                (symbol, timeframe, timestamp, current_price, rsi_14, sar, sar_position, 
                 sar_count_label, bb_upper, bb_middle, bb_lower, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, timeframe, timestamp,
                indicators['current_price'], indicators['rsi_14'],
                indicators['sar'], indicators['sar_position'], indicators['sar_count_label'],
                indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'],
                created_at
            ))
            
            saved_count += 1
    
    conn.commit()
    conn.close()
    
    return saved_count

def main():
    """主函数"""
    symbols = [
        'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'FIL-USDT-SWAP', 'SOL-USDT-SWAP',
        # 可以添加更多币种
    ]
    
    print("="*80)
    print("开始回填历史指标数据...")
    print("="*80)
    
    total_saved = 0
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] 处理 {symbol}...")
        saved = backfill_symbol(symbol, '5m')
        total_saved += saved
        print(f"  ✅ 已保存 {saved} 条指标记录")
    
    print("\n" + "="*80)
    print(f"回填完成！总共保存 {total_saved} 条指标记录")
    print("="*80)

if __name__ == '__main__':
    main()
