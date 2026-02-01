#!/usr/bin/env python3
"""
添加今天早上的测试数据，用于展示图表功能
添加从 08:00 到 10:20 的数据，模拟真实市场波动
"""
import sqlite3
import random
from datetime import datetime

def add_morning_history():
    """添加早上的历史数据"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 定义早上的数据点（从 08:00 到 10:20，每10分钟一个点）
    # 设计一个有波动的市场走势
    morning_data = [
        # 时间, 急涨, 急跌, 状态
        ('2025-12-03 08:00:00', 4, 8, '震荡偏空'),  # 早盘偏空
        ('2025-12-03 08:10:00', 5, 7, '震荡偏空'),
        ('2025-12-03 08:20:00', 6, 6, '震荡无序'),  # 开始平衡
        ('2025-12-03 08:30:00', 8, 5, '震荡偏多'),  # 转多
        ('2025-12-03 08:40:00', 10, 4, '多头趋势'),  # 强势上涨
        ('2025-12-03 08:50:00', 9, 3, '多头趋势'),
        ('2025-12-03 09:00:00', 8, 4, '震荡偏多'),  # 回调
        ('2025-12-03 09:10:00', 6, 6, '震荡无序'),  # 震荡
        ('2025-12-03 09:20:00', 5, 7, '震荡偏空'),  # 下跌
        ('2025-12-03 09:30:00', 4, 9, '空头趋势'),  # 加速下跌
        ('2025-12-03 09:40:00', 3, 8, '空头趋势'),
        ('2025-12-03 09:50:00', 5, 7, '震荡偏空'),  # 跌幅收窄
        ('2025-12-03 10:00:00', 6, 6, '震荡无序'),  # 企稳
        ('2025-12-03 10:10:00', 7, 5, '震荡偏多'),  # 反弹
        ('2025-12-03 10:20:00', 7, 5, '震荡偏多'),  # 稳定
    ]
    
    added_count = 0
    
    for record_time, rush_up, rush_down, status in morning_data:
        # 检查是否已存在
        cursor.execute('SELECT id FROM stats_history WHERE record_time = ?', (record_time,))
        if cursor.fetchone():
            print(f"⏭️  跳过已存在: {record_time}")
            continue
        
        # 插入统计数据
        try:
            cursor.execute('''
                INSERT INTO stats_history 
                (record_time, rush_up, rush_down, status, percentage, ratio, green_count, filename)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record_time,
                rush_up,
                rush_down,
                status,
                f"{(rush_up - rush_down) * 3}%",  # 简单计算百分比
                f"{rush_up}/{rush_down}",
                random.randint(15, 25),
                f"demo_{record_time.replace(':', '').replace(' ', '_')}.txt"
            ))
            
            print(f"✅ 添加: {record_time} - 急涨={rush_up}, 急跌={rush_down}, 状态={status}")
            added_count += 1
            
        except Exception as e:
            print(f"❌ 添加失败 {record_time}: {e}")
    
    conn.commit()
    
    # 统计总数据
    cursor.execute('SELECT COUNT(*) FROM stats_history')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM stats_history')
    time_range = cursor.fetchone()
    
    print(f"\n" + "=" * 70)
    print(f"📊 完成！")
    print(f"=" * 70)
    print(f"本次添加: {added_count} 条记录")
    print(f"数据库总记录: {total} 条")
    print(f"时间范围: {time_range[0]} ~ {time_range[1]}")
    print(f"=" * 70)
    
    conn.close()

if __name__ == '__main__':
    add_morning_history()
