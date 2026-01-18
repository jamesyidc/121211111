#!/usr/bin/env python3
"""
添加做多做空信号测试数据
用于展示历史趋势图效果
"""
import sqlite3
from datetime import datetime, timedelta
import random

def add_test_data():
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 生成过去10小时的数据，每10分钟一条
    base_time = datetime.now()
    
    test_data = []
    for i in range(60):  # 60条数据
        # 从当前时间往前推
        record_time = (base_time - timedelta(minutes=10 * (60 - i)))
        record_time_str = record_time.strftime('%Y-%m-%d %H:%M:00')
        
        # 模拟市场变化
        if i < 20:
            # 前期：做空信号较多（空头市场）
            total = random.randint(80, 120)
            long_pct = random.uniform(0.1, 0.3)
        elif i < 40:
            # 中期：平衡市场
            total = random.randint(60, 100)
            long_pct = random.uniform(0.3, 0.6)
        else:
            # 后期：做多信号增加（多头市场）
            total = random.randint(70, 110)
            long_pct = random.uniform(0.5, 0.8)
        
        long_count = int(total * long_pct)
        short_count = total - long_count
        
        # 细分统计
        chaodi = int(long_count * random.uniform(0.2, 0.4))
        dibu = long_count - chaodi
        dingbu = short_count
        
        test_data.append((
            record_time_str, total, long_count, short_count,
            chaodi, dibu, dingbu
        ))
    
    # 插入数据
    added = 0
    for data in test_data:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO signal_stats_history 
                (record_time, total_count, long_count, short_count,
                 chaodi_count, dibu_count, dingbu_count, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (*data, 'test_data'))
            
            if cursor.rowcount > 0:
                added += 1
        except Exception as e:
            print(f"插入失败: {data[0]}, {e}")
    
    conn.commit()
    
    # 统计
    cursor.execute('SELECT COUNT(*) FROM signal_stats_history')
    total_records = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM signal_stats_history')
    time_range = cursor.fetchone()
    
    conn.close()
    
    print(f"✅ 添加测试数据完成")
    print(f"   本次添加: {added} 条")
    print(f"   数据库总计: {total_records} 条")
    print(f"   时间范围: {time_range[0]} ~ {time_range[1]}")

if __name__ == '__main__':
    add_test_data()
