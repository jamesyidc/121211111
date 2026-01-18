import sqlite3
import subprocess
from datetime import datetime, timedelta
import pytz

print("=" * 80)
print("完整服务状态检查 - 修正版")
print("=" * 80)

# 获取当前时间
beijing_tz = pytz.timezone('Asia/Shanghai')
beijing_now = datetime.now(beijing_tz)
utc_now = datetime.utcnow()

print(f"\n当前时间:")
print(f"  UTC:    {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  北京:   {beijing_now.strftime('%Y-%m-%d %H:%M:%S')}")

# 检查进程状态
print("\n" + "=" * 80)
print("1. 进程运行状态")
print("=" * 80)

services = {
    'Flask API': 'app_new.py',
    'Google Drive监控': 'gdrive_final_detector.py',
    '支撑/阻力快照': 'support_resistance_snapshot_collector.py',
    'K线实时采集': 'okex_websocket_realtime_collector_fixed.py',
    '交易信号采集': 'signal_collector.py',
    'Panic Wash采集': 'panic_wash_collector.py'
}

running_count = 0
for name, script in services.items():
    result = subprocess.run(
        f"ps aux | grep '{script}' | grep -v grep",
        shell=True,
        capture_output=True,
        text=True
    )
    if result.stdout.strip():
        pid = result.stdout.split()[1]
        print(f"✓ {name:20s} - 运行中 (PID: {pid})")
        running_count += 1
    else:
        print(f"✗ {name:20s} - 未运行 ⚠️")

print(f"\n总计: {running_count}/{len(services)} 个服务运行中")

# 检查数据库数据时效性
print("\n" + "=" * 80)
print("2. 数据库数据更新状态")
print("=" * 80)

db_path = '/home/user/webapp/crypto_data.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# K线指标数据 (修正：使用record_time列)
try:
    cursor.execute("""
        SELECT record_time, symbol, timeframe, current_price, rsi_14, COUNT(*) OVER()
        FROM okex_technical_indicators 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        record_time = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        delay = (beijing_now.replace(tzinfo=None) - record_time).total_seconds() / 60
        print(f"\nK线指标数据:")
        print(f"  最后更新: {result[0]} (北京时间)")
        print(f"  币种示例: {result[1]} ({result[2]})")
        print(f"  价格: ${result[3]:.4f}, RSI: {result[4]:.2f}")
        print(f"  数据延迟: {delay:.1f} 分钟")
        print(f"  记录总数: {result[5]}")
        if delay <= 10:
            print(f"  状态: ✓ 正常运行")
        else:
            print(f"  状态: ⚠️ 数据过期 (>{delay:.0f}分钟)")
except Exception as e:
    print(f"\nK线指标数据: ✗ 检查失败 - {e}")

# 支撑/阻力快照数据
try:
    cursor.execute("""
        SELECT snapshot_time, created_at
        FROM support_resistance_snapshots 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        snapshot_utc = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        snapshot_beijing = snapshot_utc + timedelta(hours=8)
        created = datetime.strptime(result[1], '%Y-%m-%d %H:%M:%S')
        delay = (utc_now - created).total_seconds() / 60
        print(f"\n支撑/阻力快照:")
        print(f"  快照时间: {snapshot_beijing.strftime('%Y-%m-%d %H:%M:%S')} 北京时间")
        print(f"  创建时间: {result[1]} UTC")
        print(f"  数据延迟: {delay:.1f} 分钟")
        if delay <= 5:
            print(f"  状态: ✓ 正常运行")
        else:
            print(f"  状态: ⚠️ 数据过期 (>{delay:.0f}分钟)")
except Exception as e:
    print(f"\n支撑/阻力快照: ✗ 检查失败 - {e}")

# 交易信号数据
try:
    cursor.execute("""
        SELECT record_time, long_signals, short_signals, total_signals
        FROM trading_signals 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        record_time = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        delay = (beijing_now.replace(tzinfo=None) - record_time).total_seconds() / 60
        print(f"\n交易信号数据:")
        print(f"  记录时间: {result[0]} (北京时间)")
        print(f"  多头信号: {result[1]}, 空头信号: {result[2]}, 总计: {result[3]}")
        print(f"  数据延迟: {delay:.1f} 分钟")
        if delay <= 5:
            print(f"  状态: ✓ 正常运行")
        else:
            print(f"  状态: ⚠️ 数据过期 (>{delay:.0f}分钟)")
except Exception as e:
    print(f"\n交易信号数据: ✗ 检查失败 - {e}")

# Panic Wash指数数据
try:
    cursor.execute("""
        SELECT record_time, panic_index, hour_24_people, total_position
        FROM panic_wash_index 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        record_time = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        delay = (beijing_now.replace(tzinfo=None) - record_time).total_seconds() / 60
        print(f"\nPanic Wash指数:")
        print(f"  记录时间: {result[0]} (北京时间)")
        print(f"  恐慌指数: {result[1]:.2f}")
        print(f"  24h爆仓人数: {result[2]}")
        print(f"  全网持仓: ${result[3]/1e9:.3f}B")
        print(f"  数据延迟: {delay:.1f} 分钟")
        if delay <= 5:
            print(f"  状态: ✓ 正常运行")
        else:
            print(f"  状态: ⚠️ 数据过期 (>{delay:.0f}分钟)")
except Exception as e:
    print(f"\nPanic Wash指数: ✗ 检查失败 - {e}")

# Google Drive数据 (修正：使用rush_up和rush_down列)
try:
    cursor.execute("""
        SELECT snapshot_time, rush_up, rush_down, status
        FROM crypto_snapshots 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        snapshot_time = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        delay = (beijing_now.replace(tzinfo=None) - snapshot_time).total_seconds() / 60
        print(f"\nGoogle Drive数据:")
        print(f"  快照时间: {result[0]} (北京时间)")
        print(f"  急涨: {result[1]}, 急跌: {result[2]}")
        print(f"  市场状态: {result[3]}")
        print(f"  数据延迟: {delay:.1f} 分钟")
        if delay <= 15:
            print(f"  状态: ✓ 正常运行")
        else:
            print(f"  状态: ⚠️ 数据过期 (>{delay:.0f}分钟)")
except Exception as e:
    print(f"\nGoogle Drive数据: ✗ 检查失败 - {e}")

conn.close()

print("\n" + "=" * 80)
print("检查完成")
print("=" * 80)
