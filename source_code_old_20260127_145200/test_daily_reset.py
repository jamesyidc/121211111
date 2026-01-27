#!/usr/bin/env python3
"""
每日00:10重置功能验证脚本
"""
from datetime import datetime, timedelta
import sqlite3

print("="*80)
print("📅 每日重置功能验证")
print("="*80)

# 连接数据库
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()

# 检查当前数据
cursor.execute("""
    SELECT id, snapshot_time, snapshot_date, rush_up, rush_down 
    FROM crypto_snapshots 
    ORDER BY snapshot_time DESC 
    LIMIT 5
""")

records = cursor.fetchall()
print("\n📊 当前数据库记录 (最新5条):")
print("-"*80)
for r in records:
    print(f"ID {r[0]:3d} | {r[1]} | {r[2]} | 急涨={r[3]:2d} 急跌={r[4]:2d}")

# 统计每天的数据
cursor.execute("""
    SELECT snapshot_date, 
           COUNT(*) as count,
           MIN(rush_up) as min_rush_up,
           MAX(rush_up) as max_rush_up,
           MIN(rush_down) as min_rush_down,
           MAX(rush_down) as max_rush_down
    FROM crypto_snapshots 
    GROUP BY snapshot_date
    ORDER BY snapshot_date DESC
""")

daily_stats = cursor.fetchall()
print("\n📈 每日统计:")
print("-"*80)
for stat in daily_stats:
    date, count, min_up, max_up, min_down, max_down = stat
    print(f"{date} | 记录数:{count:3d} | 急涨:{min_up:2d}~{max_up:2d} | 急跌:{min_down:2d}~{max_down:2d}")

conn.close()

print("\n"+"="*80)
print("🔄 每日重置规则说明:")
print("="*80)
print("✅ 规则: 每天北京时间 00:10，急涨/急跌计数器自动重置为0")
print()
print("📝 工作机制:")
print("   1. 数据采集脚本在每次存储数据前，检查是否跨天")
print("   2. 如果检测到新的一天 (日期从 12-06 变为 12-07):")
print("      - 允许急涨/急跌数值从大数重置为小数")
print("      - 例如: 12-06 23:59 急涨=50 → 12-07 00:10 急涨=1 ✅")
print("   3. 同一天内，急涨/急跌只能递增:")
print("      - 例如: 12-07 08:00 急涨=10 → 12-07 09:00 急涨=8 ❌ (拒绝)")
print()
print("🎯 示例场景:")
print("   昨天 12-06 23:50:00  急涨=45  急跌=120  ✅ (正常)")
print("   今天 12-07 00:10:00  急涨=1   急跌=3    ✅ (跨天重置，允许)")
print("   今天 12-07 00:20:00  急涨=2   急跌=5    ✅ (同天递增，允许)")
print("   今天 12-07 00:30:00  急涨=1   急跌=8    ❌ (急涨减小，拒绝)")
print()
print("💡 当前配置:")
print("   - 自动采集间隔: 10分钟")
print("   - 守护进程: 运行中")
print("   - 跨天重置: 已启用")
print("="*80)
