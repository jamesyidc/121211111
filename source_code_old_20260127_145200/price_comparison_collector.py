#!/usr/bin/env python3
"""
比价系统采集器
计算各币种与24h前、48h前、7天前的价格对比
"""

import os
import sqlite3
from datetime import datetime, timedelta

# 数据库配置
DB_PATH = os.path.join(os.path.dirname(__file__), 'crypto_data.db')

# 监控的币种列表
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP',
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_price_at_time(cursor, symbol, hours_ago):
    """获取指定时间前的价格"""
    try:
        # 计算目标时间
        target_time = datetime.now() - timedelta(hours=hours_ago)
        
        # 从 okex_kline_ohlc 表查询最接近的K线价格
        cursor.execute('''
            SELECT close, ABS(
                (julianday(datetime(timestamp/1000, 'unixepoch')) - julianday(?))
            ) as time_diff
            FROM okex_kline_ohlc
            WHERE symbol = ? AND timeframe = '5m'
            ORDER BY time_diff ASC
            LIMIT 1
        ''', (target_time.strftime('%Y-%m-%d %H:%M:%S'), symbol))
        
        result = cursor.fetchone()
        return float(result[0]) if result else None
        
    except Exception as e:
        log(f"❌ 获取 {symbol} {hours_ago}小时前价格失败: {e}")
        return None

def calculate_comparison(symbol):
    """计算价格对比数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. 获取当前价格
        cursor.execute('''
            SELECT close FROM okex_kline_ohlc
            WHERE symbol = ? AND timeframe = '5m'
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (symbol,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
            
        current_price = float(result[0])
        
        # 2. 获取历史价格
        price_24h = get_price_at_time(cursor, symbol, 24)
        price_48h = get_price_at_time(cursor, symbol, 48)
        price_7d = get_price_at_time(cursor, symbol, 24 * 7)
        
        # 3. 计算变化
        change_24h = (current_price - price_24h) if price_24h else None
        change_48h = (current_price - price_48h) if price_48h else None
        change_7d = (current_price - price_7d) if price_7d else None
        
        change_24h_percent = (change_24h / price_24h * 100) if price_24h and change_24h else None
        change_48h_percent = (change_48h / price_48h * 100) if price_48h and change_48h else None
        change_7d_percent = (change_7d / price_7d * 100) if price_7d and change_7d else None
        
        # 4. 保存到数据库
        cursor.execute('''
            INSERT INTO price_comparison (
                symbol, current_price,
                price_24h_ago, price_48h_ago, price_7d_ago,
                change_24h, change_48h, change_7d,
                change_24h_percent, change_48h_percent, change_7d_percent,
                record_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+8 hours'))
        ''', (
            symbol, current_price,
            price_24h, price_48h, price_7d,
            change_24h, change_48h, change_7d,
            change_24h_percent, change_48h_percent, change_7d_percent
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'change_24h_percent': change_24h_percent,
            'change_48h_percent': change_48h_percent,
            'change_7d_percent': change_7d_percent
        }
        
    except Exception as e:
        log(f"❌ {symbol} 计算比价失败: {e}")
        return None

def main():
    """主函数"""
    log("🚀 开始计算比价数据")
    
    success_count = 0
    failed_count = 0
    
    for i, symbol in enumerate(SYMBOLS, 1):
        log(f"📊 [{i}/{len(SYMBOLS)}] 正在处理 {symbol}...")
        
        result = calculate_comparison(symbol)
        
        if result:
            log(f"✅ {symbol} | 当前价: ${result['current_price']:.4f} | "
                f"24h: {result['change_24h_percent']:+.2f}% | "
                f"48h: {result['change_48h_percent']:+.2f}% | "
                f"7d: {result['change_7d_percent']:+.2f}%")
            success_count += 1
        else:
            failed_count += 1
    
    log(f"✅ 采集完成! 成功: {success_count}, 失败: {failed_count}")

if __name__ == '__main__':
    import time
    
    log("🔄 比价系统采集器启动 - 循环模式")
    log("📅 采集间隔: 每5分钟一次")
    
    while True:
        try:
            main()
            log("⏰ 等待5分钟后开始下一轮采集...")
            time.sleep(300)  # 5分钟
        except KeyboardInterrupt:
            log("⚠️  收到停止信号，正在退出...")
            break
        except Exception as e:
            log(f"❌ 采集出错: {e}")
            log("⏰ 等待1分钟后重试...")
            time.sleep(60)  # 出错后等待1分钟重试
