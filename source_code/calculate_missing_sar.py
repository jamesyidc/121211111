#!/usr/bin/env python3
"""
为12个新币种直接从已有OHLC数据计算SAR指标
补充48小时（576条）SAR数据
"""

import sqlite3
import pandas as pd
import pandas_ta as ta
from datetime import datetime

DB_PATH = 'crypto_data.db'

# 12个需要补充SAR的币种
COINS_TO_PROCESS = [
    'HBAR-USDT-SWAP', 'FIL-USDT-SWAP', 'CRO-USDT-SWAP', 'AAVE-USDT-SWAP',
    'UNI-USDT-SWAP', 'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP',
    'CRV-USDT-SWAP', 'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

def get_ohlc_data(symbol, timeframe='5m', limit=700):
    """从数据库获取OHLC数据"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM okex_kline_ohlc
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
    conn.close()
    
    # Reverse to chronological order (oldest first)
    df = df.iloc[::-1].reset_index(drop=True)
    
    return df

def calculate_sar_indicators(df):
    """计算SAR指标"""
    try:
        # Calculate Parabolic SAR
        sar_result = ta.psar(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            af0=0.02,
            af=0.02,
            max_af=0.2
        )
        
        if sar_result is None or sar_result.empty:
            print("  ⚠️  SAR计算返回空结果")
            return None
        
        # Find the correct column names (they can vary by pandas_ta version)
        long_cols = [col for col in sar_result.columns if 'long' in col.lower() or 'psarl' in col.lower()]
        short_cols = [col for col in sar_result.columns if 'short' in col.lower() or 'psars' in col.lower()]
        
        if not long_cols or not short_cols:
            print(f"  ⚠️  无法找到SAR列: {sar_result.columns.tolist()}")
            return None
        
        # Extract SAR values
        df['sar_long'] = sar_result[long_cols[0]]
        df['sar_short'] = sar_result[short_cols[0]]
        
        # Combine into single SAR column
        df['sar'] = df['sar_long'].fillna(df['sar_short'])
        
        # Determine position
        df['sar_position'] = df.apply(
            lambda row: 'bullish' if pd.notna(row['sar_long']) else 'bearish',
            axis=1
        )
        
        # Determine quadrant
        df['sar_quadrant'] = df['sar_position'].map({
            'bullish': 'Q1',
            'bearish': 'Q3'
        })
        
        # Calculate RSI for completeness
        try:
            df['rsi_14'] = ta.rsi(df['close'], length=14)
        except:
            df['rsi_14'] = None
        
        return df[['timestamp', 'sar', 'sar_position', 'sar_quadrant', 'rsi_14']]
        
    except Exception as e:
        print(f"  ❌ SAR计算错误: {e}")
        return None

def insert_sar_data(symbol, timeframe, sar_df):
    """将SAR数据插入kline_technical_markers表"""
    if sar_df is None or sar_df.empty:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for _, row in sar_df.iterrows():
        if pd.isna(row['sar']):
            skipped += 1
            continue
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO kline_technical_markers (
                    symbol, timeframe, timestamp,
                    sar, sar_position, sar_quadrant, rsi_14
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, timeframe, int(row['timestamp']),
                float(row['sar']),
                row['sar_position'],
                row['sar_quadrant'],
                float(row['rsi_14']) if pd.notna(row['rsi_14']) else None
            ))
            
            if cursor.rowcount > 0:
                inserted += 1
        
        except Exception as e:
            skipped += 1
            continue
    
    conn.commit()
    conn.close()
    
    return inserted

def process_symbol(symbol, timeframe='5m'):
    """处理单个币种"""
    print(f"\n{'='*70}")
    print(f"📊 处理 {symbol} ({timeframe})")
    print(f"{'='*70}")
    
    # Get OHLC data
    print(f"  获取OHLC数据...", end=' ', flush=True)
    ohlc_df = get_ohlc_data(symbol, timeframe, limit=700)
    
    if ohlc_df.empty:
        print("❌ 无OHLC数据")
        return 0
    
    print(f"✅ {len(ohlc_df)} 条")
    
    # Calculate SAR
    print(f"  计算SAR指标...", end=' ', flush=True)
    sar_df = calculate_sar_indicators(ohlc_df.copy())
    
    if sar_df is None:
        print("❌ 失败")
        return 0
    
    valid_sar = sar_df['sar'].notna().sum()
    print(f"✅ {valid_sar} 条有效")
    
    # Insert into database
    print(f"  插入数据库...", end=' ', flush=True)
    inserted = insert_sar_data(symbol, timeframe, sar_df)
    print(f"✅ {inserted} 条")
    
    # Check final count
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM kline_technical_markers
        WHERE symbol = ? AND timeframe = ? AND sar IS NOT NULL
    """, (symbol, timeframe))
    final_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"  ✅ 最终记录数: {final_count}")
    
    return inserted

def main():
    print("\n" + "="*80)
    print("🚀 为12个新币种计算SAR指标")
    print("="*80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 币种数量: {len(COINS_TO_PROCESS)}")
    print(f"🎯 目标: 从已有OHLC数据计算SAR，达到576条记录")
    
    total_inserted = 0
    success_count = 0
    
    for symbol in COINS_TO_PROCESS:
        try:
            inserted = process_symbol(symbol, timeframe='5m')
            if inserted > 0:
                success_count += 1
            total_inserted += inserted
        except Exception as e:
            print(f"\n❌ {symbol} 处理失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "="*80)
    print("📊 SAR计算完成统计")
    print("="*80)
    print(f"✅ 成功币种: {success_count}/{len(COINS_TO_PROCESS)}")
    print(f"📈 插入/更新记录: {total_inserted} 条")
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Final verification
    print("\n" + "="*80)
    print("🔍 最终数据验证")
    print("="*80)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for symbol in COINS_TO_PROCESS:
        cursor.execute("""
            SELECT COUNT(*) FROM kline_technical_markers
            WHERE symbol = ? AND timeframe = '5m' AND sar IS NOT NULL
        """, (symbol,))
        count = cursor.fetchone()[0]
        status = "✅" if count >= 576 else "⚠️ "
        print(f"  {status} {symbol:20s}: {count:4d} 条SAR记录")
    
    conn.close()
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
