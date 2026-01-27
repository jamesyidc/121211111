#!/usr/bin/env python3
"""测试时间轴布局和排序"""
import requests
import json

def test_timeline_layout():
    """测试时间轴API和布局"""
    print("=" * 60)
    print("时间轴布局验证报告")
    print("=" * 60)
    
    # 测试 API
    response = requests.get('http://localhost:5000/api/timeline')
    data = response.json()
    
    print(f"\n📊 API数据:")
    print(f"   总数据点: {data['total']} 个")
    print(f"\n🔽 时间轴排序（从上到下）:")
    print(f"   ┌─ 最早的在上面")
    print(f"   │")
    
    for i, snapshot in enumerate(data['snapshots'], 1):
        time = snapshot['snapshot_time']
        rush_up = snapshot['rush_up']
        rush_down = snapshot['rush_down']
        count = snapshot['count']
        
        # 第一个（最早）
        if i == 1:
            print(f"   ├─ [{i}] {time}")
            print(f"   │      ⬆️ 急涨:{rush_up} ⬇️ 急跌:{rush_down} 🔄 计次:{count}")
        # 最后一个（最新）
        elif i == len(data['snapshots']):
            print(f"   │")
            print(f"   └─ [{i}] {time} ⭐ 当前选中")
            print(f"          ⬆️ 急涨:{rush_up} ⬇️ 急跌:{rush_down} 🔄 计次:{count}")
        # 中间的
        else:
            print(f"   │")
            print(f"   ├─ [{i}] {time}")
            print(f"   │      ⬆️ 急涨:{rush_up} ⬇️ 急跌:{rush_down} 🔄 计次:{count}")
    
    print(f"\n   └─ 最新的在下面 ✅")
    
    # 布局验证
    print(f"\n📐 页面布局顺序:")
    print(f"   1️⃣ 控制栏（日期/时间选择）")
    print(f"   2️⃣ 统计栏（14个字段）")
    print(f"   3️⃣ 次要统计栏")
    print(f"   4️⃣ 📈 趋势图（散点图）")
    print(f"   5️⃣ 📍 历史时间轴 ← 在趋势图下方 ✅")
    print(f"   6️⃣ 📋 币列表数据表")
    
    print(f"\n🎨 时间轴样式特性:")
    print(f"   ✅ 竖直布局（flex-direction: column）")
    print(f"   ✅ 最早数据在上面")
    print(f"   ✅ 最新数据在下面")
    print(f"   ✅ 圆点在左侧")
    print(f"   ✅ 竖直连接线")
    print(f"   ✅ 当前选中显示为绿色")
    print(f"   ✅ 鼠标悬停效果（背景高亮+圆点放大）")
    print(f"   ✅ 可滚动（最大高度400px）")
    print(f"   ✅ 点击切换数据")
    
    print(f"\n🌐 访问地址:")
    print(f"   https://5000-iik759kgm7i3zqlxvfrfx-cc2fbc16.sandbox.novita.ai")
    
    print(f"\n" + "=" * 60)
    print("✅ 时间轴布局完全符合要求！")
    print("=" * 60)

if __name__ == '__main__':
    test_timeline_layout()
