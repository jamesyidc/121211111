#!/usr/bin/env python3
"""
比价系统 price_baseline 表同步脚本
从 price_comparison 的历史数据重新计算并更新 baseline 表
"""

import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'crypto_data.db')

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def sync_baseline():
    """同步price_baseline表数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        log("=" * 80)
        log("🔄 开始同步 price_baseline 表")
        log("=" * 80)
        
        # 1. 获取所有监控的币种
        cursor.execute("SELECT DISTINCT symbol FROM price_comparison ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]
        
        log(f"📊 找到 {len(symbols)} 个币种")
        
        # 2. 为每个币种计算历史最高/最低价
        updated_count = 0
        
        for symbol in symbols:
            # 从price_comparison历史数据中获取最高和最低价
            cursor.execute('''
                SELECT 
                    MAX(current_price) as highest_price,
                    MIN(current_price) as lowest_price
                FROM price_comparison
                WHERE symbol = ?
            ''', (symbol,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                log(f"⚠️  {symbol}: 无历史数据，跳过")
                continue
            
            highest_price = result[0]
            lowest_price = result[1]
            
            # 获取当前最新价格
            cursor.execute('''
                SELECT current_price 
                FROM price_comparison 
                WHERE symbol = ? 
                ORDER BY record_time DESC 
                LIMIT 1
            ''', (symbol,))
            
            current_result = cursor.fetchone()
            last_price = current_result[0] if current_result else highest_price
            
            # 计算比率
            highest_ratio = (last_price / lowest_price * 100) if lowest_price else 100
            lowest_ratio = (last_price / highest_price * 100) if highest_price else 100
            
            # 获取或创建display_order
            cursor.execute("SELECT display_order FROM price_baseline WHERE symbol = ?", (symbol,))
            order_result = cursor.fetchone()
            display_order = order_result[0] if order_result else (len(symbols) - symbols.index(symbol))
            
            # 更新或插入数据
            cursor.execute('''
                INSERT OR REPLACE INTO price_baseline (
                    symbol, 
                    highest_price, 
                    highest_count, 
                    lowest_price, 
                    lowest_count,
                    last_price,
                    highest_ratio,
                    lowest_ratio,
                    last_update_time,
                    display_order
                ) VALUES (?, ?, 0, ?, 0, ?, ?, ?, datetime('now', '+8 hours'), ?)
            ''', (
                symbol,
                highest_price,
                lowest_price,
                last_price,
                highest_ratio,
                lowest_ratio,
                display_order
            ))
            
            log(f"✅ {symbol}: 最高${highest_price:.4f}, 最低${lowest_price:.4f}, "
                f"当前${last_price:.4f} (比率: 最高{highest_ratio:.2f}%, 最低{lowest_ratio:.2f}%)")
            
            updated_count += 1
        
        conn.commit()
        conn.close()
        
        log("=" * 80)
        log(f"✅ 同步完成! 更新了 {updated_count} 个币种")
        log("=" * 80)
        
        return True
        
    except Exception as e:
        log(f"❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    log("🚀 启动 price_baseline 同步脚本")
    success = sync_baseline()
    
    if success:
        log("🎉 同步成功!")
    else:
        log("❌ 同步失败，请检查错误信息")
