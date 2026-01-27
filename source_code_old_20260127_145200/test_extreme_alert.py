#!/usr/bin/env python3
"""
测试极值突破预警功能
"""
import sys
sys.path.append('/home/user/webapp')

from anchor_system import format_extreme_alert, send_telegram_message

# 模拟一个超过历史最高收益的持仓
max_profit_position = {
    'instId': 'CRV-USDT-SWAP',
    'posSide': 'short',
    'pos': '24.0',
    'avgPx': '0.3980504128863671',
    'markPx': '0.3650',  # 价格大幅下跌
    'upl': '0.80',
    'margin': '0.95',
    'lever': '10'
}

# 当前收益率: 40%（超过之前的36.57%）
current_profit_rate = 40.0
previous_profit_rate = 36.57

print("=" * 60)
print("测试1: 历史最高收益突破预警")
print("=" * 60)
print(f"币种: {max_profit_position['instId']}")
print(f"之前最高收益: {previous_profit_rate:.2f}%")
print(f"当前收益率: {current_profit_rate:.2f}%")
print(f"突破幅度: {current_profit_rate - previous_profit_rate:.2f}%")
print("=" * 60)

# 生成并发送预警消息
message = format_extreme_alert(max_profit_position, current_profit_rate, previous_profit_rate, 'max_profit')
print("\n预警消息:")
print("-" * 60)
print(message)
print("-" * 60)

print("\n正在发送Telegram消息...")
success = send_telegram_message(message)

if success:
    print("✅ 最高收益突破预警已发送到Telegram")
else:
    print("❌ Telegram消息发送失败")

print("\n" + "=" * 60)
print("测试2: 历史最大亏损突破预警")
print("=" * 60)

# 模拟一个超过历史最大亏损的持仓
max_loss_position = {
    'instId': 'LDO-USDT-SWAP',
    'posSide': 'short',
    'pos': '21.0',
    'avgPx': '0.5689831389837741',
    'markPx': '0.6500',  # 价格大幅上涨
    'upl': '-0.35',
    'margin': '1.20',
    'lever': '10'
}

# 当前收益率: -18%（低于之前的-15.5%）
current_loss_rate = -18.0
previous_loss_rate = -15.5

print(f"币种: {max_loss_position['instId']}")
print(f"之前最大亏损: {previous_loss_rate:.2f}%")
print(f"当前收益率: {current_loss_rate:.2f}%")
print(f"突破幅度: {abs(current_loss_rate - previous_loss_rate):.2f}%")
print("=" * 60)

# 生成并发送预警消息
message = format_extreme_alert(max_loss_position, current_loss_rate, previous_loss_rate, 'max_loss')
print("\n预警消息:")
print("-" * 60)
print(message)
print("-" * 60)

print("\n正在发送Telegram消息...")
success = send_telegram_message(message)

if success:
    print("✅ 最大亏损突破预警已发送到Telegram")
else:
    print("❌ Telegram消息发送失败")

print("\n✅ 极值突破预警测试完成")
