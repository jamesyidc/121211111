#!/usr/bin/env python3
"""
SAR斜率计算脚本
计算所有币种的SAR斜率，并存储到数据库
"""

import sqlite3
import numpy as np
from datetime import datetime

# SAR斜率分类阈值（百分比）
SLOPE_THRESHOLDS = {
    'steep_up': 0.5,      # 陡峭上升 (>0.5%)
    'moderate_up': 0.1,   # 温和上升 (0.1%~0.5%)
    'flat': 0.1,          # 平稳 (-0.1%~0.1%)
    'moderate_down': -0.5, # 温和下降 (-0.5%~-0.1%)
    'steep_down': -0.5    # 陡峭下降 (<-0.5%)
}

def calculate_sar_slope(sar_values, periods=5, method='linear'):
    """
    计算SAR斜率
    
    参数:
    - sar_values: SAR值列表
    - periods: 计算周期（默认5个K线）
    - method: 计算方法 ('linear', 'simple', 'weighted')
    
    返回:
    - slope: 绝对斜率值
    - slope_percent: 相对斜率（百分比）
    - slope_category: 斜率分类
    """
    if len(sar_values) < periods:
        return None, None, None
    
    recent_sar = sar_values[-periods:]
    
    if method == 'simple':
        # 方法1：简单差分
        current_sar = recent_sar[-1]
        past_sar = recent_sar[0]
        
        slope = (current_sar - past_sar) / (periods - 1)
        slope_percent = ((current_sar - past_sar) / past_sar) * 100 if past_sar != 0 else 0
        
    elif method == 'weighted':
        # 方法2：加权线性回归
        weights = np.arange(1, periods + 1)
        x = np.arange(len(recent_sar))
        y = np.array(recent_sar)
        
        slope, intercept = np.polyfit(x, y, 1, w=weights)
        
        current_sar = recent_sar[-1]
        slope_percent = (slope / current_sar) * 100 if current_sar != 0 else 0
        
    else:  # method == 'linear' (默认)
        # 方法3：线性回归
        x = np.arange(len(recent_sar))
        y = np.array(recent_sar)
        
        slope, intercept = np.polyfit(x, y, 1)
        
        current_sar = recent_sar[-1]
        slope_percent = (slope / current_sar) * 100 if current_sar != 0 else 0
    
    # 分类斜率
    slope_category = classify_slope(slope_percent)
    
    return slope, slope_percent, slope_category

def classify_slope(slope_percent):
    """
    根据斜率百分比进行分类
    
    返回:
    - steep_up: 陡峭上升
    - moderate_up: 温和上升
    - flat: 平稳
    - moderate_down: 温和下降
    - steep_down: 陡峭下降
    """
    if slope_percent > SLOPE_THRESHOLDS['steep_up']:
        return 'steep_up'
    elif slope_percent > SLOPE_THRESHOLDS['moderate_up']:
        return 'moderate_up'
    elif slope_percent < SLOPE_THRESHOLDS['steep_down']:
        return 'steep_down'
    elif slope_percent < SLOPE_THRESHOLDS['moderate_down']:
        return 'moderate_down'
    else:
        return 'flat'

def get_slope_label(slope_category, sar_position='bullish'):
    """
    获取斜率的中文标签
    
    参数:
    - slope_category: 斜率分类
    - sar_position: SAR方向 ('bullish' 或 'bearish')
    """
    if sar_position == 'bullish':
        labels = {
            'steep_up': '强势多头📈',
            'moderate_up': '温和多头↗',
            'flat': '平稳多头→',
            'moderate_down': '减弱多头↘',
            'steep_down': '转向空头📉'
        }
    else:  # bearish
        labels = {
            'steep_down': '强势空头📉',
            'moderate_down': '温和空头↘',
            'flat': '平稳空头→',
            'moderate_up': '减弱空头↗',
            'steep_up': '转向多头📈'
        }
    
    return labels.get(slope_category, '未知')

def calculate_and_store_sar_slopes(db_path='crypto_data.db', periods=5, method='linear'):
    """
    计算所有币种的SAR斜率并存储到数据库
    
    参数:
    - db_path: 数据库路径
    - periods: 计算周期
    - method: 计算方法
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查是否需要添加新字段
    cursor.execute("PRAGMA table_info(kline_technical_markers)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'sar_slope' not in columns:
        print("添加 sar_slope 字段到数据库...")
        cursor.execute("""
            ALTER TABLE kline_technical_markers 
            ADD COLUMN sar_slope REAL
        """)
        conn.commit()
    
    if 'sar_slope_percent' not in columns:
        print("添加 sar_slope_percent 字段到数据库...")
        cursor.execute("""
            ALTER TABLE kline_technical_markers 
            ADD COLUMN sar_slope_percent REAL
        """)
        conn.commit()
    
    if 'sar_slope_category' not in columns:
        print("添加 sar_slope_category 字段到数据库...")
        cursor.execute("""
            ALTER TABLE kline_technical_markers 
            ADD COLUMN sar_slope_category TEXT
        """)
        conn.commit()
    
    if 'sar_slope_label' not in columns:
        print("添加 sar_slope_label 字段到数据库...")
        cursor.execute("""
            ALTER TABLE kline_technical_markers 
            ADD COLUMN sar_slope_label TEXT
        """)
        conn.commit()
    
    # 获取所有symbol和timeframe组合
    cursor.execute("""
        SELECT DISTINCT symbol, timeframe 
        FROM kline_technical_markers 
        WHERE sar IS NOT NULL
        ORDER BY symbol, timeframe
    """)
    symbol_timeframes = cursor.fetchall()
    
    total_updated = 0
    
    for symbol, timeframe in symbol_timeframes:
        print(f"\n处理 {symbol} ({timeframe})...")
        
        # 获取该币种的所有SAR数据（按时间升序）
        cursor.execute("""
            SELECT id, timestamp, sar, sar_position
            FROM kline_technical_markers
            WHERE symbol = ? AND timeframe = ? AND sar IS NOT NULL
            ORDER BY timestamp ASC
        """, (symbol, timeframe))
        
        rows = cursor.fetchall()
        
        if len(rows) < periods:
            print(f"  ⚠️  数据不足（需要至少{periods}条，实际{len(rows)}条）")
            continue
        
        # 提取SAR值
        sar_values = [row[2] for row in rows]
        
        # 计算每个点的斜率（需要至少periods个历史点）
        updated_count = 0
        for i in range(periods - 1, len(rows)):
            row_id = rows[i][0]
            sar_position = rows[i][3]
            
            # 获取最近periods个SAR值
            sar_window = sar_values[i - periods + 1:i + 1]
            
            # 计算斜率
            slope, slope_percent, slope_category = calculate_sar_slope(
                sar_window, periods=periods, method=method
            )
            
            if slope is not None:
                # 获取标签
                slope_label = get_slope_label(slope_category, sar_position)
                
                # 更新数据库
                cursor.execute("""
                    UPDATE kline_technical_markers
                    SET sar_slope = ?,
                        sar_slope_percent = ?,
                        sar_slope_category = ?,
                        sar_slope_label = ?
                    WHERE id = ?
                """, (slope, slope_percent, slope_category, slope_label, row_id))
                
                updated_count += 1
        
        conn.commit()
        total_updated += updated_count
        print(f"  ✅ 更新了 {updated_count} 条记录")
    
    conn.close()
    
    print(f"\n🎉 完成！共更新 {total_updated} 条SAR斜率记录")
    print(f"📊 计算方法: {method}")
    print(f"📏 计算周期: {periods} 个K线")
    
    return total_updated

def show_sar_slope_examples(db_path='crypto_data.db', symbol='BTC-USDT-SWAP', timeframe='5m', limit=10):
    """
    显示SAR斜率计算示例
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, sar, sar_position, 
               sar_slope, sar_slope_percent, 
               sar_slope_category, sar_slope_label
        FROM kline_technical_markers
        WHERE symbol = ? AND timeframe = ? 
          AND sar_slope IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT ?
    """, (symbol, timeframe, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"❌ 没有找到 {symbol} ({timeframe}) 的SAR斜率数据")
        return
    
    print(f"\n{'='*100}")
    print(f"{symbol} ({timeframe}) SAR斜率示例（最新{limit}条）")
    print(f"{'='*100}")
    print(f"{'时间':<20} {'SAR':<12} {'方向':<10} {'斜率':<12} {'斜率%':<10} {'分类':<15} {'标签':<15}")
    print(f"{'-'*100}")
    
    for row in rows:
        ts = datetime.fromtimestamp(row[0]/1000).strftime('%Y-%m-%d %H:%M:%S')
        sar = row[1]
        position = '多头' if row[2] == 'bullish' else '空头'
        slope = row[3]
        slope_pct = row[4]
        category = row[5]
        label = row[6]
        
        print(f"{ts:<20} {sar:<12.6f} {position:<10} {slope:<12.6f} {slope_pct:<10.4f} {category:<15} {label:<15}")
    
    print(f"{'='*100}\n")

if __name__ == '__main__':
    print("=" * 80)
    print("SAR斜率计算脚本")
    print("=" * 80)
    
    # 选择计算方法
    print("\n可选计算方法:")
    print("1. linear   - 线性回归（推荐，最精确）")
    print("2. simple   - 简单差分（最快速）")
    print("3. weighted - 加权回归（更重视最近数据）")
    
    method = 'linear'  # 默认使用线性回归
    periods = 5        # 默认使用5个K线周期
    
    print(f"\n使用方法: {method}")
    print(f"计算周期: {periods} 个K线")
    
    # 计算并存储SAR斜率
    total_updated = calculate_and_store_sar_slopes(
        db_path='crypto_data.db',
        periods=periods,
        method=method
    )
    
    if total_updated > 0:
        # 显示示例
        print("\n" + "=" * 80)
        print("计算结果示例")
        print("=" * 80)
        
        # BTC示例
        show_sar_slope_examples(symbol='BTC-USDT-SWAP', timeframe='5m', limit=10)
        
        # ETH示例
        show_sar_slope_examples(symbol='ETH-USDT-SWAP', timeframe='5m', limit=10)
