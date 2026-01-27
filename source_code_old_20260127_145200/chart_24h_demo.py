#!/usr/bin/env python3
"""
24小时完整趋势图可视化演示
"""
import requests

def create_visual_demo():
    """创建24小时趋势图的可视化演示"""
    
    print("\n" + "=" * 90)
    print(" " * 25 + "📊 24小时完整趋势图演示")
    print("=" * 90)
    
    # 获取实际数据
    response = requests.get('http://localhost:5000/api/chart')
    data = response.json()
    
    times = data['times']
    rush_up = data['rush_up']
    
    print("\n横轴时间标签（每小时一个刻度）:")
    print("─" * 90)
    
    # 显示时间轴（每5个点显示一次，节省空间）
    display_times = []
    for i, t in enumerate(times):
        if i % 5 == 0 or i == len(times) - 1:
            display_times.append(t)
        else:
            display_times.append("")
    
    # 打印时间标签
    for i in range(0, len(display_times), 5):
        chunk = display_times[i:i+5]
        time_str = "  ".join(f"{t:12s}" for t in chunk)
        print(time_str)
    
    print("─" * 90)
    print("\n纵轴数据展示（急涨趋势线示例）:")
    print("─" * 90)
    
    # 找出最大值用于缩放
    max_val = max((v for v in rush_up if v is not None), default=1)
    
    # 显示数据点（简化的ASCII图）
    for level in range(max_val, -1, -2):
        line = []
        for val in rush_up:
            if val is None:
                line.append("    ")  # 无数据
            elif val >= level:
                line.append(" ●  ")  # 有数据点
            else:
                line.append("    ")
        
        level_str = f"{level:2d} |" + "".join(line)
        print(level_str)
    
    print("   +" + "─" * 88)
    print("    " + "  ".join(["    "] * 6))
    
    print("\n图例:")
    print("  ● = 数据点    空白 = 无数据    ─ = 连线")
    
    print("\n" + "=" * 90)
    print("\n实际显示效果:")
    print("  🔴 急涨 (红色线)   🟢 急跌 (绿色线)")
    print("  🟡 差值 (黄色线)   🔵 计次 (蓝色线，右侧Y轴)")
    
    print("\n特点:")
    print("  ✅ 横轴始终显示完整24小时范围")
    print("  ✅ 数据点用圆点清晰标记")
    print("  ✅ 有数据时段显示平滑连线")
    print("  ✅ 无数据时段不连线（断续线段）")
    print("  ✅ 鼠标悬停显示详细数值")
    
    print("\n🌐 在线访问: https://5000-iik759kgm7i3zqlxvfrfx-cc2fbc16.sandbox.novita.ai")
    print("=" * 90 + "\n")

if __name__ == '__main__':
    create_visual_demo()
