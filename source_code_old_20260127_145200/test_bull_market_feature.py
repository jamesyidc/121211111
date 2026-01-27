#!/usr/bin/env python3
"""
测试锚点系统新增的低盈利/亏损统计和多头行情触发功能
"""

import sqlite3

db_path = '/home/user/webapp/anchor_system.db'
conn = sqlite3.connect(db_path, timeout=10.0)
cursor = conn.cursor()

print("=" * 80)
print("🧪 锚点系统新增功能测试")
print("=" * 80)
print()

# 获取当前持仓
cursor.execute("""
    SELECT inst_id, pos_side, profit_rate
    FROM anchor_profit_records
    WHERE pos_side = 'short'
    ORDER BY profit_rate DESC
""")

positions = cursor.fetchall()

if not positions:
    print("❌ 当前无持仓")
else:
    print(f"📍 当前持仓总数: {len(positions)}")
    print()
    
    # 统计各盈利级别
    profit70 = [p for p in positions if p[2] >= 70]
    profit60 = [p for p in positions if p[2] >= 60]
    profit50 = [p for p in positions if p[2] >= 50]
    profit40 = [p for p in positions if p[2] >= 40]
    profitBelow20 = [p for p in positions if p[2] <= 20]
    profitBelow10 = [p for p in positions if p[2] <= 10]
    lossCount = [p for p in positions if p[2] < 0]
    
    print("=" * 80)
    print("📈 新增统计项目")
    print("=" * 80)
    print(f"📉 空单盈利≤20%: {len(profitBelow20)} 个")
    print(f"📊 空单盈利≤10%: {len(profitBelow10)} 个")
    print(f"❌ 空单亏损: {len(lossCount)} 个")
    print()
    
    print("=" * 80)
    print("📊 完整盈利分级统计")
    print("=" * 80)
    print(f"🔥 空单盈利≥70%: {len(profit70)} 个")
    print(f"⚡ 空单盈利≥60%: {len(profit60)} 个")
    print(f"💫 空单盈利≥50%: {len(profit50)} 个")
    print(f"✨ 空单盈利≥40%: {len(profit40)} 个")
    print(f"📉 空单盈利≤20%: {len(profitBelow20)} 个")
    print(f"📊 空单盈利≤10%: {len(profitBelow10)} 个")
    print(f"❌ 空单亏损: {len(lossCount)} 个")
    print()
    
    # 判断触发状态
    print("=" * 80)
    print("🎯 三大触发规则测试")
    print("=" * 80)
    
    # 多头行情条件
    is_bull_market = (len(profitBelow20) >= 8 and len(profitBelow10) >= 6 and len(lossCount) >= 2)
    
    # 触底反弹条件
    is_bottom_rebound = (len(profit70) >= 1 and len(profit60) >= 2 and 
                         len(profit50) >= 5 and len(profit40) >= 8)
    
    # 多转空条件
    is_long_to_short = (len(profit70) == 0 and len(profit50) >= 1 and len(profit40) >= 3)
    
    print("1️⃣ 多头行情:")
    print(f"   条件: ≤20%: {len(profitBelow20)}>=8 {'✓' if len(profitBelow20)>=8 else '✗'}, "
          f"≤10%: {len(profitBelow10)}>=6 {'✓' if len(profitBelow10)>=6 else '✗'}, "
          f"亏损: {len(lossCount)}>=2 {'✓' if len(lossCount)>=2 else '✗'}")
    if is_bull_market:
        print("   状态: ✅ 已触发")
        print("   显示: 🚀 多头行情 (蓝色)")
        print("   提示: 操作提示：适合做多")
    else:
        print("   状态: ❌ 未触发")
    print()
    
    print("2️⃣ 触底反弹:")
    print(f"   条件: ≥70%: {len(profit70)}>=1 {'✓' if len(profit70)>=1 else '✗'}, "
          f"≥60%: {len(profit60)}>=2 {'✓' if len(profit60)>=2 else '✗'}, "
          f"≥50%: {len(profit50)}>=5 {'✓' if len(profit50)>=5 else '✗'}, "
          f"≥40%: {len(profit40)}>=8 {'✓' if len(profit40)>=8 else '✗'}")
    if is_bottom_rebound:
        print("   状态: ✅ 已触发")
        print("   显示: 📈 触底反弹 (绿色)")
        print("   提示: 操作提示：禁止空单")
    else:
        print("   状态: ❌ 未触发")
    print()
    
    print("3️⃣ 多转空:")
    print(f"   条件: ≥70%: {len(profit70)}=0 {'✓' if len(profit70)==0 else '✗'}, "
          f"≥50%: {len(profit50)}>=1 {'✓' if len(profit50)>=1 else '✗'}, "
          f"≥40%: {len(profit40)}>=3 {'✓' if len(profit40)>=3 else '✗'}")
    if is_long_to_short:
        print("   状态: ✅ 已触发")
        print("   显示: 🔄 多转空 (红色)")
        print("   提示: 操作提示：禁止多单")
    else:
        print("   状态: ❌ 未触发")
    print()
    
    # 优先级判断
    print("=" * 80)
    print("🎯 当前最终状态 (按优先级)")
    print("=" * 80)
    if is_bull_market:
        print("✅ 🚀 多头行情 (蓝色) - 适合做多")
    elif is_bottom_rebound:
        print("✅ 📈 触底反弹 (绿色) - 禁止空单")
    elif is_long_to_short:
        print("✅ 🔄 多转空 (红色) - 禁止做多")
    else:
        print("ℹ️ 状态栏隐藏 - 无特殊操作提示")
    print()
    
    # 显示低盈利/亏损持仓详情
    if profitBelow20:
        print("=" * 80)
        print("📉 盈利≤20%的持仓详情")
        print("=" * 80)
        for pos in profitBelow20[:10]:
            inst_id, pos_side, profit_rate = pos
            print(f"  • {inst_id}: {profit_rate:+.2f}%")
        if len(profitBelow20) > 10:
            print(f"  ... 还有 {len(profitBelow20)-10} 个")
        print()

conn.close()

print("=" * 80)
print("🌐 页面访问地址")
print("=" * 80)
print("https://5000-iawcy3xxhnan90u0qd9wq-cc2fbc16.sandbox.novita.ai/anchor-system-real")
print()
print("页面新增内容:")
print("✅ 3个新的统计卡片")
print("   - 📉 空单盈利≤20% (紫色)")
print("   - 📊 空单盈利≤10% (蓝色)")
print("   - ❌ 空单亏损 (红色)")
print()
print("✅ 新的触发规则")
print("   - 🚀 多头行情 (蓝色状态栏)")
print()
print("✅ 1小时内增量统计")
print("   - 所有7个指标都显示1小时内变化")
print()
print("=" * 80)
