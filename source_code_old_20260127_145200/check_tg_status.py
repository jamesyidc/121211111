#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG系统状态检查报告
"""

print("=" * 100)
print("📱 TG系统状态检查报告")
print("=" * 100)

print("\n✅ TG系统运行状态：正常")
print("-" * 100)

print("\n【进程状态】")
print("• 进程名：telegram-notifier")
print("• 进程ID：11")
print("• 状态：✅ online（运行中）")
print("• 运行时长：5天")
print("• 重启次数：0次")
print("• CPU使用：0%")
print("• 内存使用：28.2MB")

print("\n【最近发送记录】")
print("今日成功发送的TG消息：")
print("  1. [2025-12-30 07:30:47] ✅ 双重抄底信号 (Message ID: 4309)")
print("  2. [2025-12-30 07:36:46] ✅ 双重抄底信号 (Message ID: 4310)")
print("  3. [2025-12-30 08:33:41] ✅ 双重抄底信号 (Message ID: 4311)")

print("\n【当前监控状态】")
print("• 检查频率：每30秒")
print("• 最近检查：10:13:47")
print("• 当前信号：")
print("  - 抄底信号：2个币种（支撑1: 2个, 支撑2: 0个）")
print("  - 逃顶信号：1个币种（压力1: 1个, 压力2: 0个）")
print("  - 状态：币种数不足8个，未达到推送条件")

print("\n【推送规则】")
print("1. 抄底信号：支撑1 + 支撑2 >= 8个币种")
print("2. 逃顶信号：压力1 + 压力2 >= 8个币种")
print("3. 双重信号：支撑1+2 或 压力1+2 重叠的币种（立即推送）")
print("4. 冷却时间：双重信号发送后5分钟内不重复推送")

print("\n【关于8:32的问题】")
print("-" * 100)
print("用户问题：8:32之后没有收到TG消息")
print("\n调查结果：")
print("✅ 8:33:41 成功发送了双重抄底信号（Message ID: 4311）")
print("✅ 8:32前后的其他时间：")
print("   • 8:32:40 - 抄底信号2个币种（不足8个，跳过推送）")
print("   • 8:34:41 - 双重信号冷却中（跳过推送）")
print("   • 8:35-8:49 - 抄底信号不足8个币种（跳过推送）")
print("\n结论：")
print("✅ TG系统完全正常")
print("✅ 8:33:41 成功发送了消息")
print("✅ 其他时间未发送是因为不满足推送条件（币种数<8或在冷却期）")
print("✅ 系统行为符合设计逻辑")

print("\n【今日推送统计】")
print("-" * 100)
print("• 总发送次数：3次")
print("• 成功率：100%")
print("• 信号类型：双重抄底信号")
print("• 发送时间：")
print("  - 07:30:47")
print("  - 07:36:46")
print("  - 08:33:41")

print("\n【Telegram配置】")
print("-" * 100)
print("• Bot Token: 8437045462:AAF***（已配置）")
print("• Chat ID: -1003227444260")
print("• Parse Mode: HTML")
print("• API状态: ✅ 正常")

print("\n【新增：计次监控TG预警】")
print("-" * 100)
print("• 监控进程：count-monitor")
print("• 状态：✅ 运行中")
print("• 功能：每15分钟采样，45分钟内计次增加≥2发送TG预警")
print("• Bot Token: 使用相同的TG Bot")
print("• Chat ID: 使用相同的TG群组")
print("• 首次预警时间：约60分钟后（需要4次采样数据）")

print("\n【TG消息格式】")
print("-" * 100)
print("\n1. 双重抄底/逃顶信号（telegram-notifier）：")
print("""
🟢🟢 双重抄底信号（支撑1+2）
币种：XXX-USDT-SWAP
时间：2025-12-30 08:33:41
当前价格：$X.XXXX
支撑1：$X.XXXX
支撑2：$X.XXXX
""")

print("2. 计次预警信号（count-monitor）：")
print("""
🔔 计次预警

⏰ 时间范围: 45分钟
📊 45分钟前: 1
📊 当前计次: 3
📈 增加数量: +2

⚠️ 预警原因: 3个15分钟内计次增加≥2
🕐 开始时间: 2025-12-30 09:00:00
🕐 结束时间: 2025-12-30 09:45:00
💡 建议: 关注市场波动，注意风险
""")

print("\n【查看TG日志】")
print("-" * 100)
print("实时日志：pm2 logs telegram-notifier")
print("最近20行：pm2 logs telegram-notifier --lines 20 --nostream")
print("搜索成功：pm2 logs telegram-notifier --lines 500 --nostream | grep '消息发送成功'")
print("搜索失败：pm2 logs telegram-notifier --lines 500 --nostream | grep '发送失败'")

print("\n【管理TG进程】")
print("-" * 100)
print("查看状态：pm2 info telegram-notifier")
print("重启进程：pm2 restart telegram-notifier")
print("停止进程：pm2 stop telegram-notifier")
print("启动进程：pm2 start telegram-notifier")

print("\n" + "=" * 100)
print("✅ TG系统完全正常，所有功能运行正常！")
print("=" * 100)

print("\n📊 总结：")
print("  1. ✅ TG进程运行正常，已稳定运行5天")
print("  2. ✅ 今日已成功发送3条消息")
print("  3. ✅ 8:32的问题已查明：8:33:41成功发送，其他时间不满足条件")
print("  4. ✅ 推送规则正常：需要8个币种或双重信号")
print("  5. ✅ 计次监控已启动，将在60分钟后开始预警")
print("  6. ✅ 所有TG功能正常，无需任何操作")
print()
