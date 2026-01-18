#!/usr/bin/env python3
"""
测试最大亏损记录功能
"""
import sys
sys.path.append('/home/user/webapp')

from anchor_system import update_profit_record

# 模拟一个亏损持仓
loss_position = {
    'instId': 'LDO-USDT-SWAP',
    'posSide': 'short',
    'pos': '21.0',
    'avgPx': '0.5689831389837741',
    'markPx': '0.6200',  # 价格上涨，做空亏损
    'upl': '-60.0',
    'margin': '6.0',
    'lever': '10'
}

# 计算亏损率：-60 / 6 * 100 = -1000% (极端情况)
profit_rate = -15.5  # 模拟-15.5%的亏损

print("=" * 60)
print("测试最大亏损记录功能")
print("=" * 60)
print(f"币种: {loss_position['instId']}")
print(f"方向: {loss_position['posSide']}")
print(f"收益率: {profit_rate:+.2f}%")
print("=" * 60)

# 更新记录
update_profit_record(loss_position, profit_rate)

print("\n✅ 测试完成")
