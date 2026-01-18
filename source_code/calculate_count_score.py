#!/usr/bin/env python3
"""
计次得分计算和更新脚本
根据时间段和count值计算星级得分
"""
import sqlite3
from datetime import datetime
import pytz

def calculate_count_score(snapshot_time, count):
    """
    根据时间和count值计算计次得分
    
    返回: (display_str, score_type)
    - display_str: 如 "★★★" 或 "☆☆☆"
    - score_type: "实心3星" 或 "空心3星"
    
    规则（2026-01-18 用户提供的正确版本）：
    
    截止6点前:
      实心星：
        - count <= 1:              ★★★ (实心3星)
        - 1 < count <= 2:          ★★ (实心2星)
        - 2 < count <= 3:          ★ (实心1星)
      空心星：
        - 3 < count <= 4:          ☆ (空心1星)
        - 4 < count <= 5:          ☆☆ (空心2星)
        - count > 5:               ☆☆☆ (空心3星)
    
    截止12点前:
      实心星：
        - count <= 2:              ★★★ (实心3星)
        - 2 < count <= 3:          ★★ (实心2星)
        - 3 < count <= 4:          ★ (实心1星)
      空心星：
        - 4 < count <= 5:          (中性区)
        - 5 < count <= 6:          ☆ (空心1星)
        - 6 < count <= 7:          ☆☆ (空心2星)
        - count > 7:               ☆☆☆ (空心3星)
    
    截止18点前:
      实心星：
        - count <= 3:              ★★★ (实心3星)
        - 3 < count <= 4:          ★★ (实心2星)
        - 4 < count <= 5:          ★ (实心1星)
      空心星：
        - 5 < count <= 7:          (中性区)
        - 7 < count <= 8:          ☆ (空心1星)
        - 8 < count <= 9:          ☆☆ (空心2星)
        - count > 9:               ☆☆☆ (空心3星)
    
    截止24点前:
      实心星：
        - count <= 4:              ★★★ (实心3星)
        - 4 < count <= 5:          ★★ (实心2星)
        - 5 < count <= 6:          ★ (实心1星)
      空心星：
        - 6 < count <= 9:          (中性区)
        - 9 < count <= 10:         ☆ (空心1星)
        - 10 < count <= 12:        ☆☆ (空心2星，推断)
        - count > 12:              ☆☆☆ (空心3星，推断)
    """
    try:
        # 解析时间，提取小时
        dt = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S')
        hour = dt.hour
        
        # 判断时间段
        if hour < 6:  # 0-6点前（截止6点前）
            if count <= 1:
                return "★★★", "实心3星"
            elif 1 < count <= 2:
                return "★★", "实心2星"
            elif 2 < count <= 3:
                return "★", "实心1星"
            elif 3 < count <= 4:
                return "☆", "空心1星"
            elif 4 < count <= 5:
                return "☆☆", "空心2星"
            else:  # count > 5
                return "☆☆☆", "空心3星"
                
        elif hour < 12:  # 6-12点前（截止12点前）
            if count <= 2:
                return "★★★", "实心3星"
            elif 2 < count <= 3:
                return "★★", "实心2星"
            elif 3 < count <= 4:
                return "★", "实心1星"
            elif 4 < count <= 5:
                return "", "中性"  # 中间区
            elif 5 < count <= 6:
                return "☆", "空心1星"
            elif 6 < count <= 7:
                return "☆☆", "空心2星"
            else:  # count > 7
                return "☆☆☆", "空心3星"
                
        elif hour < 18:  # 12-18点前（截止18点前）
            if count <= 3:
                return "★★★", "实心3星"
            elif 3 < count <= 4:
                return "★★", "实心2星"
            elif 4 < count <= 5:
                return "★", "实心1星"
            elif 5 < count <= 7:
                return "", "中性"  # 中间区
            elif 7 < count <= 8:
                return "☆", "空心1星"
            elif 8 < count <= 9:
                return "☆☆", "空心2星"
            else:  # count > 9
                return "☆☆☆", "空心3星"
                
        else:  # 18-24点（24点前）
            if count <= 4:
                return "★★★", "实心3星"
            elif 4 < count <= 5:
                return "★★", "实心2星"
            elif 5 < count <= 6:
                return "★", "实心1星"
            elif 6 < count <= 9:
                return "", "中性"  # 中间区
            elif 9 < count <= 10:
                return "☆", "空心1星"
            elif 10 < count <= 12:
                return "☆☆", "空心2星"
            else:  # count > 12
                return "☆☆☆", "空心3星"
                
    except Exception as e:
        print(f"计算得分出错: {e}")
        return "", "中性"

def update_all_scores():
    """更新数据库中所有记录的计次得分"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 获取所有记录
    cursor.execute("""
        SELECT id, snapshot_time, count 
        FROM crypto_snapshots 
        WHERE count IS NOT NULL
        ORDER BY snapshot_time DESC
    """)
    
    records = cursor.fetchall()
    print(f"找到 {len(records)} 条记录需要更新")
    
    updated_count = 0
    error_count = 0
    
    for record_id, snapshot_time, count in records:
        try:
            # 计算得分
            display, score_type = calculate_count_score(snapshot_time, count)
            
            # 更新数据库
            cursor.execute("""
                UPDATE crypto_snapshots 
                SET count_score_display = ?, count_score_type = ?
                WHERE id = ?
            """, (display, score_type, record_id))
            
            updated_count += 1
            
            # 每100条显示一次进度
            if updated_count % 100 == 0:
                print(f"已更新 {updated_count} 条记录...")
                
        except Exception as e:
            error_count += 1
            print(f"更新记录 {record_id} 失败: {e}")
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print(f"\n更新完成!")
    print(f"成功更新: {updated_count} 条")
    print(f"失败: {error_count} 条")
    
    return updated_count, error_count

def verify_scores():
    """验证计次得分计算结果"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 获取不同时间段的样本
    test_times = [
        ('截止6点前', '2025-12-10 03:00:00'),
        ('截止12点前', '2025-12-10 09:00:00'),
        ('截止18点前', '2025-12-10 15:00:00'),
        ('24点前', '2025-12-10 21:00:00'),
    ]
    
    print("\n=== 验证计次得分计算 ===")
    for period_name, time_example in test_times:
        cursor.execute("""
            SELECT snapshot_time, count, count_score_display, count_score_type 
            FROM crypto_snapshots 
            WHERE snapshot_time >= ? AND snapshot_time < datetime(?, '+6 hours')
            ORDER BY snapshot_time DESC 
            LIMIT 5
        """, (time_example.split()[0] + ' ' + time_example.split()[1][:2] + ':00:00',
              time_example.split()[0] + ' ' + time_example.split()[1][:2] + ':00:00'))
        
        results = cursor.fetchall()
        if results:
            print(f"\n{period_name} 示例:")
            for row in results:
                print(f"  时间: {row[0]}, count: {row[1]}, 得分: '{row[2]}', 类型: {row[3]}")
    
    # 统计各类得分的数量
    cursor.execute("""
        SELECT count_score_type, count_score_display, COUNT(*) as cnt
        FROM crypto_snapshots
        WHERE count_score_display IS NOT NULL AND count_score_display != ''
        GROUP BY count_score_type, count_score_display
        ORDER BY count_score_type, count_score_display
    """)
    
    print("\n=== 得分分布统计 ===")
    for row in cursor.fetchall():
        print(f"{row[0]:6} {row[1]:6} : {row[2]:5} 条")
    
    conn.close()

if __name__ == '__main__':
    print("开始更新计次得分...")
    updated, errors = update_all_scores()
    
    if updated > 0:
        verify_scores()
    
    print("\n✓ 完成!")
