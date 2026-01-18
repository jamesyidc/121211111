#!/usr/bin/env python3
"""
导入48小时历史SAR数据脚本
为每个币种导入最近48小时（576条）的5分钟SAR数据
"""

import sqlite3
import sys
from datetime import datetime, timedelta
import pytz

DB_PATH = 'crypto_data.db'
TIMEFRAME = '5m'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 27个监控币种
MONITORED_SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP',
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

def get_historical_sar_data(symbol: str, limit: int = 576):
    """获取历史SAR数据（最近576条 = 48小时）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, sar, sar_position, sar_quadrant
        FROM kline_technical_markers
        WHERE symbol = ? AND timeframe = ? AND sar IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT ?
    """, (symbol, TIMEFRAME, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Reverse to chronological order (oldest first)
    return list(reversed(rows))

def get_price_data(symbol: str, timestamp: int):
    """获取价格数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT open, close FROM okex_kline_ohlc
        WHERE symbol = ? AND timeframe = ? AND timestamp = ?
        LIMIT 1
    """, (symbol, TIMEFRAME, timestamp))
    
    row = cursor.fetchone()
    conn.close()
    
    return (row[0], row[1]) if row else (None, None)

def calculate_position_duration(data_list, current_index):
    """计算持续周期"""
    if current_index == 0:
        return 1
    
    current_position = data_list[current_index][2]  # sar_position
    duration = 1
    
    # 向前查找相同position
    for i in range(current_index - 1, -1, -1):
        if data_list[i][2] == current_position:
            duration += 1
        else:
            break
    
    return duration

def import_historical_data(symbol: str):
    """导入单个币种的历史数据"""
    print(f"\n{'='*60}")
    print(f"导入 {symbol} 的历史数据...")
    print(f"{'='*60}")
    
    # 获取历史SAR数据
    sar_data_list = get_historical_sar_data(symbol, 576)
    
    if not sar_data_list:
        print(f"❌ {symbol}: 没有可用的SAR历史数据")
        return 0
    
    print(f"📊 找到 {len(sar_data_list)} 条SAR记录")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    imported_count = 0
    skipped_count = 0
    
    for idx, (timestamp, sar, sar_position, sar_quadrant) in enumerate(sar_data_list):
        # 获取价格数据
        price_open, price_close = get_price_data(symbol, timestamp)
        
        if price_close is None:
            skipped_count += 1
            continue
        
        # 计算持续周期
        duration = calculate_position_duration(sar_data_list, idx)
        
        # 转换时间
        dt_utc = datetime.utcfromtimestamp(timestamp / 1000)
        dt_beijing = dt_utc.replace(tzinfo=pytz.UTC).astimezone(BEIJING_TZ)
        
        # 检查是否已存在
        cursor.execute("""
            SELECT id FROM sar_slope_data
            WHERE symbol = ? AND timestamp = ?
        """, (symbol, timestamp))
        
        if cursor.fetchone():
            skipped_count += 1
            continue
        
        # 插入数据
        try:
            cursor.execute("""
                INSERT INTO sar_slope_data (
                    symbol, timestamp, datetime_utc, datetime_beijing,
                    sar_value, sar_position, sar_quadrant, position_duration,
                    slope_value, slope_direction, price_open, price_close
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, timestamp,
                dt_utc.strftime('%Y-%m-%d %H:%M:%S'),
                dt_beijing.strftime('%Y-%m-%d %H:%M:%S'),
                sar, sar_position, sar_quadrant, duration,
                None, 'stable',  # slope暂时设为None和stable
                price_open, price_close
            ))
            imported_count += 1
            
            if imported_count % 100 == 0:
                print(f"  已导入 {imported_count} 条...")
                
        except Exception as e:
            print(f"  ⚠️  插入失败 (timestamp={timestamp}): {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ {symbol} 导入完成:")
    print(f"   导入: {imported_count} 条")
    print(f"   跳过: {skipped_count} 条")
    
    return imported_count

def main():
    print("\n" + "="*70)
    print("🚀 开始导入48小时历史SAR数据")
    print("="*70)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 目标: 每个币种最多576条记录 (48小时)")
    print(f"💰 币种数量: {len(MONITORED_SYMBOLS)}")
    
    total_imported = 0
    success_count = 0
    
    for symbol in MONITORED_SYMBOLS:
        try:
            count = import_historical_data(symbol)
            if count > 0:
                success_count += 1
                total_imported += count
        except Exception as e:
            print(f"\n❌ {symbol} 导入失败: {e}")
            continue
    
    print("\n" + "="*70)
    print("📊 导入完成统计")
    print("="*70)
    print(f"✅ 成功币种: {success_count}/{len(MONITORED_SYMBOLS)}")
    print(f"📈 总导入记录: {total_imported} 条")
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
