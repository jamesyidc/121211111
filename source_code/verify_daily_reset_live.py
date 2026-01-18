#!/usr/bin/env python3
"""
实时验证每日重置功能
"""
from datetime import datetime
import pytz
import sqlite3

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

print("="*80)
print("🔍 每日重置功能 - 实时验证")
print("="*80)

# 当前北京时间
now = datetime.now(BEIJING_TZ)
print(f"\n📅 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
print(f"   当前日期: {now.date()}")
print(f"   当前时刻: {now.hour:02d}:{now.minute:02d}:{now.second:02d}")

# 距离下一个00:10还有多久
current_minutes = now.hour * 60 + now.minute
reset_minutes = 0 * 60 + 10  # 00:10
if current_minutes < reset_minutes:
    minutes_to_reset = reset_minutes - current_minutes
    reset_today = True
else:
    minutes_to_reset = (24 * 60 - current_minutes) + reset_minutes
    reset_today = False

hours_to_reset = minutes_to_reset // 60
mins_to_reset = minutes_to_reset % 60

print(f"\n⏰ 下一次重置时间:")
if reset_today:
    print(f"   今天 {now.date()} 00:10:00")
else:
    tomorrow = now.date().replace(day=now.day+1) if now.day < 28 else now.date()
    print(f"   明天 {tomorrow} 00:10:00")
print(f"   倒计时: {hours_to_reset}小时 {mins_to_reset}分钟")

# 数据库检查
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()

# 最新记录
cursor.execute("""
    SELECT id, snapshot_time, snapshot_date, rush_up, rush_down 
    FROM crypto_snapshots 
    ORDER BY snapshot_time DESC 
    LIMIT 3
""")
records = cursor.fetchall()

print(f"\n📊 数据库最新记录:")
print("-"*80)
for r in records:
    print(f"ID {r[0]:3d} | {r[1]} | 日期: {r[2]} | 急涨={r[3]:2d} 急跌={r[4]:2d}")

# 今天的数据统计
today_str = now.date().strftime('%Y-%m-%d')
cursor.execute("""
    SELECT COUNT(*), MIN(rush_up), MAX(rush_up), MIN(rush_down), MAX(rush_down)
    FROM crypto_snapshots 
    WHERE snapshot_date = ?
""", (today_str,))
today_stats = cursor.fetchone()

if today_stats and today_stats[0] > 0:
    count, min_up, max_up, min_down, max_down = today_stats
    print(f"\n📈 今日 ({today_str}) 统计:")
    print(f"   记录数: {count} 条")
    print(f"   急涨范围: {min_up} ~ {max_up}")
    print(f"   急跌范围: {min_down} ~ {max_down}")
    
    # 检查是否有重置迹象
    if min_up < 5 and count > 10:
        print(f"   ✅ 数据正常 (从小值开始，已有{count}条记录)")
    elif count < 5:
        print(f"   ⏳ 数据较少，等待更多采集")
else:
    print(f"\n⏳ 今日 ({today_str}) 暂无数据")

conn.close()

print("\n"+"="*80)
print("🎯 监控建议:")
print("="*80)
print("1. 实时日志监控:")
print("   tail -f auto_collect.log | grep \"跨天\\|重置\"")
print()
print("2. 明天00:10后检查:")
print("   python3 test_daily_reset.py")
print()
print("3. 查看跨天第一条数据:")
print("   sqlite3 crypto_data.db \"SELECT * FROM crypto_snapshots WHERE snapshot_date='2025-12-07' ORDER BY snapshot_time LIMIT 1\"")
print()
print("4. 对比前后数据:")
print("   - 查看今天23:50的数据 (预计: 急涨≈5~10, 急跌≈20~30)")
print("   - 查看明天00:10的数据 (预计: 急涨≈0~3, 急跌≈0~5)")
print("   - 如果出现数值重置，说明功能正常 ✅")
print("="*80)
