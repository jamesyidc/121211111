#!/usr/bin/env python3
"""
添加几条测试数据来展示高亮功能
"""
import sqlite3

def add_test_data():
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 测试数据：展示不同的高亮情况
    test_data = [
        # 时间, 急涨, 急跌, 状态, 说明
        ('2025-12-03 08:00:00', 15, 3, '强势多头', '急涨>10，应该高亮（仅一次）'),
        ('2025-12-03 08:10:00', 18, 2, '极强多头', '急涨>10，但已标注过，不重复'),
        ('2025-12-03 08:30:00', 25, 4, '暴涨', '差值=21，应该高亮（大差值）'),
        ('2025-12-03 09:00:00', 3, 26, '暴跌', '差值=-23，应该高亮（大差值）'),
        ('2025-12-03 09:30:00', 60, 5, '极端上涨', '差值=55，应该高亮（极端差值）'),
        ('2025-12-03 10:00:00', 2, 55, '极端下跌', '差值=-53，应该高亮（极端差值）'),
    ]
    
    added_count = 0
    
    for record_time, rush_up, rush_down, status, note in test_data:
        # 检查是否已存在
        cursor.execute('SELECT id FROM stats_history WHERE record_time = ?', (record_time,))
        if cursor.fetchone():
            print(f"⏭️  跳过已存在: {record_time}")
            continue
        
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
                f"{(rush_up - rush_down) * 3}%",
                f"{rush_up}/{rush_down}",
                15,  # 默认绿色计数
                f"test_highlight_{record_time.replace(':', '').replace(' ', '_')}.txt"
            ))
            
            diff = rush_up - rush_down
            print(f"✅ 添加: {record_time} - 急涨={rush_up:2d}, 急跌={rush_down:2d}, 差值={diff:+3d} - {note}")
            added_count += 1
            
        except Exception as e:
            print(f"❌ 添加失败 {record_time}: {e}")
    
    conn.commit()
    
    # 统计
    cursor.execute('SELECT COUNT(*) FROM stats_history')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM stats_history')
    time_range = cursor.fetchone()
    
    print(f"\n" + "=" * 80)
    print(f"📊 完成！")
    print(f"=" * 80)
    print(f"本次添加: {added_count} 条测试数据")
    print(f"数据库总记录: {total} 条")
    print(f"时间范围: {time_range[0]} ~ {time_range[1]}")
    print(f"\n高亮测试数据包含:")
    print(f"  - 🟡 急涨>10 的情况（仅标注一次）")
    print(f"  - 🟠 差值>20 或 <-20 的情况")
    print(f"  - 🔴 差值>50 或 <-50 的极端情况")
    print(f"=" * 80)
    
    conn.close()

if __name__ == '__main__':
    add_test_data()
