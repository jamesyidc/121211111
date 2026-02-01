#!/usr/bin/env python3
"""
历史数据查询和图表生成脚本
按照日期+时间查询历史数据，生成曲线图
"""
import sqlite3
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
from datetime import datetime
import pytz

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def calculate_priority_level(high_ratio_str, low_ratio_str):
    """
    根据最高占比和最低占比计算优先级等级
    
    等级1: 最高占比>90   最低占比>120
    等级2: 最高占比>80   最低占比>120
    等级3: 最高占比>90   最低占比>110
    等级4: 最高占比>70   最低占比>120
    等级5: 最高占比>80   最低占比>110
    等级6: 最高占比<80   最低占比<110
    """
    try:
        # 去除百分号并转换为数字
        high_ratio = float(high_ratio_str.replace('%', '')) if high_ratio_str else 0
        low_ratio = float(low_ratio_str.replace('%', '')) if low_ratio_str else 0
        
        # 按照优先级顺序判断
        if high_ratio > 90 and low_ratio > 120:
            return "等级1"
        elif high_ratio > 80 and low_ratio > 120:
            return "等级2"
        elif high_ratio > 90 and low_ratio > 110:
            return "等级3"
        elif high_ratio > 70 and low_ratio > 120:
            return "等级4"
        elif high_ratio > 80 and low_ratio > 110:
            return "等级5"
        else:  # high_ratio < 80 and low_ratio < 110
            return "等级6"
    except:
        return "未知"

def query_by_datetime(query_datetime_str):
    """
    按照日期+时间查询历史数据
    query_datetime_str: 格式如 "2025-12-06 13:30" 或 "2025-12-06_1330"
    """
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 支持多种格式
    if '_' in query_datetime_str:
        query_datetime_str = query_datetime_str.replace('_', ' ')
        # 如果是 HHMM 格式，添加冒号
        parts = query_datetime_str.split()
        if len(parts) == 2 and len(parts[1]) == 4:
            query_datetime_str = f"{parts[0]} {parts[1][:2]}:{parts[1][2:]}"
    
    print(f"\n{'='*80}")
    print(f"查询时间: {query_datetime_str}")
    print(f"{'='*80}")
    
    # 查询 crypto_snapshots 表中最接近的记录
    cursor.execute("""
        SELECT 
            snapshot_time,
            rush_up,
            rush_down,
            diff,
            count,
            ratio,
            status,
            filename
        FROM crypto_snapshots
        WHERE snapshot_time LIKE ?
        ORDER BY snapshot_time DESC
        LIMIT 1
    """, (f"{query_datetime_str}%",))
    
    snapshot = cursor.fetchone()
    
    if not snapshot:
        print(f"❌ 未找到 {query_datetime_str} 的数据")
        conn.close()
        return None
    
    snapshot_time, rush_up, rush_down, diff, count, ratio, status, filename = snapshot
    
    print(f"\n找到数据:")
    print(f"  时间: {snapshot_time}")
    print(f"  文件: {filename}")
    print(f"  急涨: {rush_up}")
    print(f"  急跌: {rush_down}")
    print(f"  差值: {diff}")
    print(f"  计次: {count}")
    print(f"  比值: {ratio}")
    print(f"  状态: {status}")
    
    # 查询该时间点的币种数据，计算优先级
    cursor.execute("""
        SELECT 
            symbol,
            change,
            change_24h,
            ratio1,
            ratio2,
            high_price,
            current_price
        FROM crypto_coin_data
        WHERE snapshot_time = ?
        ORDER BY index_order ASC
    """, (snapshot_time,))
    
    coins = cursor.fetchall()
    
    if coins:
        print(f"\n币种数据 (共 {len(coins)} 个):")
        print(f"{'序号':>4} {'币种':<8} {'涨幅':>8} {'24h涨幅':>10} {'最高占比':>10} {'最低占比':>10} {'优先级':>8}")
        print("-" * 80)
        
        for idx, coin in enumerate(coins[:20], 1):  # 只显示前20个
            symbol, change, change_24h, ratio1, ratio2, high_price, current_price = coin
            priority = calculate_priority_level(ratio1, ratio2)
            print(f"{idx:>4} {symbol:<8} {change:>7.2f}% {change_24h:>9.2f}% {ratio1:>10} {ratio2:>10} {priority:>8}")
        
        if len(coins) > 20:
            print(f"... 还有 {len(coins) - 20} 个币种")
    
    conn.close()
    
    return {
        'snapshot_time': snapshot_time,
        'rush_up': rush_up,
        'rush_down': rush_down,
        'diff': diff,
        'count': count,
        'ratio': ratio,
        'status': status,
        'filename': filename,
        'coins': coins
    }

def query_time_range(start_time, end_time=None):
    """
    查询时间范围内的数据，用于生成图表
    start_time: 开始时间，格式如 "2025-12-06 10:00"
    end_time: 结束时间，如果为None则查询到最新数据
    """
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    if end_time:
        cursor.execute("""
            SELECT 
                snapshot_time,
                rush_up,
                rush_down,
                diff,
                count
            FROM crypto_snapshots
            WHERE snapshot_time >= ? AND snapshot_time <= ?
            ORDER BY snapshot_time ASC
        """, (start_time, end_time))
    else:
        cursor.execute("""
            SELECT 
                snapshot_time,
                rush_up,
                rush_down,
                diff,
                count
            FROM crypto_snapshots
            WHERE snapshot_time >= ?
            ORDER BY snapshot_time ASC
        """, (start_time,))
    
    data = cursor.fetchall()
    conn.close()
    
    return data

def create_chart(data, output_file='chart.png'):
    """
    生成包含4个指标的曲线图：急涨、急跌、差值、计次
    """
    if not data:
        print("❌ 没有数据可以绘制图表")
        return None
    
    times = []
    rush_ups = []
    rush_downs = []
    diffs = []
    counts = []
    
    for row in data:
        snapshot_time, rush_up, rush_down, diff, count = row
        times.append(snapshot_time)
        rush_ups.append(rush_up)
        rush_downs.append(rush_down)
        diffs.append(diff)
        counts.append(count)
    
    # 创建图表
    fig, ax1 = plt.subplots(figsize=(14, 8))
    
    # 第一个y轴：急涨、急跌、差值
    ax1.set_xlabel('时间', fontsize=12)
    ax1.set_ylabel('数量', fontsize=12, color='black')
    
    line1 = ax1.plot(times, rush_ups, 'r-o', label='急涨', linewidth=2, markersize=4)
    line2 = ax1.plot(times, rush_downs, 'g-s', label='急跌', linewidth=2, markersize=4)
    line3 = ax1.plot(times, diffs, 'b-^', label='差值(急涨-急跌)', linewidth=2, markersize=4)
    
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(True, alpha=0.3)
    
    # 第二个y轴：计次
    ax2 = ax1.twinx()
    ax2.set_ylabel('计次', fontsize=12, color='purple')
    line4 = ax2.plot(times, counts, 'purple', linestyle='--', marker='D', 
                     label='计次', linewidth=2, markersize=4)
    ax2.tick_params(axis='y', labelcolor='purple')
    
    # 合并图例
    lines = line1 + line2 + line3 + line4
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=10)
    
    # 设置标题
    start_time = times[0] if times else ''
    end_time = times[-1] if times else ''
    plt.title(f'加密货币市场数据曲线图\n时间范围: {start_time} - {end_time}', 
              fontsize=14, fontweight='bold', pad=20)
    
    # 旋转x轴标签
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存至: {output_file}")
    
    plt.close()
    
    return output_file

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  查询单个时间点: python3 query_history.py '2025-12-06 13:30'")
        print("  查询单个时间点: python3 query_history.py '2025-12-06_1330'")
        print("  生成图表: python3 query_history.py chart '2025-12-06 10:00'")
        print("  生成图表: python3 query_history.py chart '2025-12-06 10:00' '2025-12-06 14:00'")
        return
    
    if sys.argv[1] == 'chart':
        # 生成图表
        if len(sys.argv) < 3:
            print("❌ 请提供开始时间")
            return
        
        start_time = sys.argv[2]
        end_time = sys.argv[3] if len(sys.argv) > 3 else None
        
        print(f"\n查询时间范围: {start_time} - {end_time or '最新'}")
        data = query_time_range(start_time, end_time)
        
        if data:
            print(f"找到 {len(data)} 条数据")
            output_file = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            create_chart(data, output_file)
        else:
            print("❌ 未找到数据")
    else:
        # 查询单个时间点
        query_datetime = sys.argv[1]
        result = query_by_datetime(query_datetime)

if __name__ == '__main__':
    main()
