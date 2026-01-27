#!/usr/bin/env python3
"""
同步支撑压力线快照数据
从 support_resistance_levels 表生成 support_resistance_snapshots 表的数据
每1分钟执行一次

快照场景定义（基于alert字段，与前端统计卡片完全一致）:
- 场景1 (scenario_1): 接近支撑线2 (48h低位) = alert_48h_low
- 场景2 (scenario_2): 接近支撑线1 (7天低位) = alert_7d_low
- 场景3 (scenario_3): 接近压力线2 (48h高位) = alert_48h_high
- 场景4 (scenario_4): 接近压力线1 (7天高位) = alert_7d_high
"""

import os
import sys
import time
import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), 'crypto_data.db')

def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def generate_snapshot():
    """生成快照数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取每个币种的最新数据时间
        # 因为采集器是逐个币种写入的，我们需要取每个币种最新的record_time
        cursor.execute('''
            SELECT symbol, MAX(record_time) as latest_time
            FROM support_resistance_levels
            WHERE record_time >= datetime('now', '-5 minutes')
            GROUP BY symbol
        ''')
        symbol_times = cursor.fetchall()
        
        if not symbol_times or len(symbol_times) < 10:
            log("❌ 没有找到足够的最新support_resistance_levels数据")
            conn.close()
            return False
        
        # 使用中位数时间作为快照基准（避免过早或过晚）
        times = sorted([row['latest_time'] for row in symbol_times])
        median_index = len(times) // 2
        latest_time = times[median_index]
        
        log(f"📊 正在生成快照，基于中位数时间: {latest_time} (共{len(symbol_times)}个币种)")
        
        # 获取每个币种的最新数据（包含alert字段）
        cursor.execute('''
            SELECT symbol, current_price, 
                   support_line_1, support_line_2,
                   resistance_line_1, resistance_line_2,
                   distance_to_support_1, distance_to_support_2,
                   distance_to_resistance_1, distance_to_resistance_2,
                   alert_7d_low, alert_48h_low,
                   alert_7d_high, alert_48h_high,
                   position_7d, position_48h,
                   record_time
            FROM support_resistance_levels
            WHERE (symbol, record_time) IN (
                SELECT symbol, MAX(record_time)
                FROM support_resistance_levels
                WHERE record_time >= datetime('now', '-5 minutes')
                GROUP BY symbol
            )
        ''')
        
        rows = cursor.fetchall()
        
        # 按alert字段分类（与前端统计卡片逻辑完全一致）
        scenario_1_coins = []  # 接近支撑线2（48h低位）= alert_48h_low
        scenario_2_coins = []  # 接近支撑线1（7天低位）= alert_7d_low
        scenario_3_coins = []  # 接近压力线2（48h高位）= alert_48h_high
        scenario_4_coins = []  # 接近压力线1（7天高位）= alert_7d_high
        
        total_coins = len(rows)
        
        for row in rows:
            symbol = row['symbol']
            current_price = row['current_price']
            
            # 使用数据库中的alert字段（与前端完全一致）
            # 场景1：接近48h低位（支撑线2）
            if row['alert_48h_low']:
                coin_data = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'support_line': row['support_line_2'],
                    'distance': row['distance_to_support_2'],
                    'position': row['position_48h']
                }
                scenario_1_coins.append(coin_data)
            
            # 场景2：接近7天低位（支撑线1）
            if row['alert_7d_low']:
                coin_data = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'support_line': row['support_line_1'],
                    'distance': row['distance_to_support_1'],
                    'position': row['position_7d']
                }
                scenario_2_coins.append(coin_data)
            
            # 场景3：接近48h高位（压力线2）
            if row['alert_48h_high']:
                coin_data = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'resistance_line': row['resistance_line_2'],
                    'distance': row['distance_to_resistance_2'],
                    'position': row['position_48h']
                }
                scenario_3_coins.append(coin_data)
            
            # 场景4：接近7天高位（压力线1）
            if row['alert_7d_high']:
                coin_data = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'resistance_line': row['resistance_line_1'],
                    'distance': row['distance_to_resistance_1'],
                    'position': row['position_7d']
                }
                scenario_4_coins.append(coin_data)
        
        # 插入快照数据
        snapshot_date = latest_time.split()[0]
        
        cursor.execute('''
            INSERT INTO support_resistance_snapshots (
                snapshot_time, snapshot_date,
                scenario_1_count, scenario_2_count, scenario_3_count, scenario_4_count,
                scenario_1_coins, scenario_2_coins, scenario_3_coins, scenario_4_coins,
                total_coins, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ''', (
            latest_time, snapshot_date,
            len(scenario_1_coins), len(scenario_2_coins), len(scenario_3_coins), len(scenario_4_coins),
            json.dumps(scenario_1_coins, ensure_ascii=False),
            json.dumps(scenario_2_coins, ensure_ascii=False),
            json.dumps(scenario_3_coins, ensure_ascii=False),
            json.dumps(scenario_4_coins, ensure_ascii=False),
            total_coins
        ))
        
        conn.commit()
        conn.close()
        
        log(f"✅ 快照生成成功 | 48h低位: {len(scenario_1_coins)}, 7天低位: {len(scenario_2_coins)}, 48h高位: {len(scenario_3_coins)}, 7天高位: {len(scenario_4_coins)}")
        return True
        
    except Exception as e:
        log(f"❌ 生成快照失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    log("🚀 支撑压力线快照同步器启动")
    log("=" * 60)
    
    while True:
        try:
            generate_snapshot()
            log("⏳ 等待60秒后进行下一次同步...")
            log("=" * 60)
            time.sleep(60)  # 1分钟
            
        except KeyboardInterrupt:
            log("⚠️  收到退出信号，停止同步器...")
            break
        except Exception as e:
            log(f"❌ 发生异常: {e}")
            import traceback
            traceback.print_exc()
            log("⏳ 60秒后重试...")
            time.sleep(60)

if __name__ == '__main__':
    main()
