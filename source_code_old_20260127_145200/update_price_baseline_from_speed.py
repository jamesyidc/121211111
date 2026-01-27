#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从price_speed数据更新price_baseline表并保存到JSONL
实时监控价格变化，更新最高价/最低价基准，并记录突破事件
"""

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path

# 数据库路径
DB_PATH = '/home/user/webapp/databases/crypto_data.db'
PRICE_SPEED_FILE = '/home/user/webapp/data/price_speed_jsonl/latest_price_speed.jsonl'
JSONL_DIR = '/home/user/webapp/data/price_comparison_jsonl'

def save_to_jsonl(data, filename):
    """保存数据到JSONL文件"""
    try:
        Path(JSONL_DIR).mkdir(parents=True, exist_ok=True)
        filepath = Path(JSONL_DIR) / filename
        
        with open(filepath, 'a') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        return True
    except Exception as e:
        log(f"❌ 保存JSONL失败: {e}")
        return False

def update_latest_snapshot():
    """更新最新数据快照"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, highest_price, highest_count, lowest_price, lowest_count,
                   last_price, highest_ratio, lowest_ratio, last_update_time
            FROM price_baseline
            ORDER BY display_order
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # 覆盖写入最新快照
        filepath = Path(JSONL_DIR) / 'latest_price_baseline.jsonl'
        with open(filepath, 'w') as f:
            for row in rows:
                data = dict(row)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        return True
    except Exception as e:
        log(f"❌ 更新快照失败: {e}")
        return False

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def load_latest_prices():
    """从JSONL文件加载最新价格"""
    prices = {}
    try:
        with open(PRICE_SPEED_FILE, 'r') as f:
            for line in f:
                data = json.loads(line.strip())
                symbol = data['symbol']
                # 转换为-USDT-SWAP格式
                full_symbol = f"{symbol}-USDT-SWAP"
                prices[full_symbol] = {
                    'price': float(data['current_price']),
                    'timestamp': data['timestamp']
                }
        return prices
    except Exception as e:
        log(f"❌ 加载价格数据失败: {e}")
        return {}

def update_price_baseline(symbol, current_price, timestamp):
    """更新价格基准并记录突破事件"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.execute('PRAGMA journal_mode=WAL')  # 使用WAL模式减少锁定
        cursor = conn.cursor()
        
        # 获取当前的最高价/最低价
        cursor.execute('''
            SELECT highest_price, highest_count, lowest_price, lowest_count
            FROM price_baseline
            WHERE symbol = ?
        ''', (symbol,))
        
        row = cursor.fetchone()
        if not row:
            log(f"⚠️  {symbol} 不在监控列表中")
            conn.close()
            return
        
        highest_price, highest_count, lowest_price, lowest_count = row
        
        # 计算新的比例
        price_range = highest_price - lowest_price
        if price_range > 0:
            highest_ratio = ((highest_price - current_price) / price_range) * 100
            highest_ratio = max(0, min(100, 100 - highest_ratio))  # 转换为接近最高价的百分比
            
            lowest_ratio = ((current_price - lowest_price) / price_range) * 100
            lowest_ratio = max(0, min(100, lowest_ratio))
        else:
            highest_ratio = 100.0
            lowest_ratio = 100.0
        
        # 判断是否突破
        breakthrough = None
        
        if current_price > highest_price:
            # 创新高
            old_highest = highest_price
            highest_price = current_price
            highest_count = 0
            breakthrough = {
                'type': 'new_high',
                'old_price': old_highest,
                'new_price': current_price
            }
            log(f"🚀 {symbol} 创新高！ ${old_highest:.6f} -> ${current_price:.6f}")
        elif current_price < lowest_price:
            # 创新低
            old_lowest = lowest_price
            lowest_price = current_price
            lowest_count = 0
            breakthrough = {
                'type': 'new_low',
                'old_price': old_lowest,
                'new_price': current_price
            }
            log(f"📉 {symbol} 创新低！ ${old_lowest:.6f} -> ${current_price:.6f}")
        else:
            # 在区间内，计次+1
            highest_count += 1
            lowest_count += 1
        
        # 更新price_baseline
        cursor.execute('''
            UPDATE price_baseline
            SET highest_price = ?,
                highest_count = ?,
                lowest_price = ?,
                lowest_count = ?,
                last_price = ?,
                highest_ratio = ?,
                lowest_ratio = ?,
                last_update_time = ?
            WHERE symbol = ?
        ''', (
            highest_price, highest_count,
            lowest_price, lowest_count,
            current_price,
            highest_ratio,
            lowest_ratio,
            timestamp,
            symbol
        ))
        
        # 如果有突破事件，记录到price_breakthrough_events
        if breakthrough:
            cursor.execute('''
                INSERT INTO price_breakthrough_events
                (symbol, event_type, price, previous_extreme_price, event_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                symbol,
                breakthrough['type'],
                breakthrough['new_price'],
                breakthrough['old_price'],
                timestamp
            ))
            
            # 保存突破事件到JSONL
            event_data = {
                'symbol': symbol,
                'event_type': breakthrough['type'],
                'price': breakthrough['new_price'],
                'previous_extreme_price': breakthrough['old_price'],
                'event_time': timestamp
            }
            save_to_jsonl(event_data, 'price_breakthrough_events.jsonl')
            
            # 清除旧的统计缓存，强制重新计算
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('DELETE FROM price_comparison_stats WHERE stat_date = ?', (today,))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        log(f"❌ {symbol} 更新失败: {e}")
        return False

def main():
    """主函数"""
    log("🔄 开始更新price_baseline...")
    
    # 加载最新价格
    prices = load_latest_prices()
    if not prices:
        log("⚠️  没有价格数据")
        return
    
    log(f"📊 加载了 {len(prices)} 个币种的价格")
    
    # 更新每个币种
    success_count = 0
    for symbol, data in prices.items():
        if update_price_baseline(symbol, data['price'], data['timestamp']):
            success_count += 1
    
    log(f"✅ 更新完成! 成功: {success_count}/{len(prices)}")
    
    # 更新最新快照
    if success_count > 0:
        if update_latest_snapshot():
            log("✅ 最新快照已更新")

if __name__ == '__main__':
    import sys
    
    # 如果有参数 --once，只运行一次
    run_once = '--once' in sys.argv
    
    if run_once:
        log("🚀 Price Baseline 更新器 - 单次运行模式")
        main()
        log("✅ 单次运行完成")
    else:
        log("🚀 Price Baseline 更新器启动")
        log("📅 更新间隔: 每30秒一次")
        
        while True:
            try:
                main()
                log("⏰ 等待30秒后开始下一轮更新...")
                time.sleep(30)
            except KeyboardInterrupt:
                log("⚠️  收到停止信号，正在退出...")
                break
            except Exception as e:
                log(f"❌ 更新出错: {e}")
                log("⏰ 等待10秒后重试...")
                time.sleep(10)
