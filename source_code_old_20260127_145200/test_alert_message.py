#!/usr/bin/env python3
import requests
from datetime import datetime, timezone, timedelta

# Telegram配置
bot_token = "8437045462:AAFePnwdC21cqeWhZISMQHGGgjmroVqE2H0"
chat_id = "-1003227444260"

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 模拟持仓数据
position_profit = {
    'instId': 'CRV-USDT-SWAP',
    'posSide': 'short',
    'pos': 24.0,
    'avgPx': 0.3981,
    'markPx': 0.3750,  # 模拟价格下跌到触发40%
    'upl': 0.55,
    'margin': 0.95,
    'lever': 10.0
}

position_loss = {
    'instId': 'LDO-USDT-SWAP',
    'posSide': 'short',
    'pos': 84.0,
    'avgPx': 0.5683,
    'markPx': 0.6251,  # 模拟价格上涨到触发-10%
    'upl': -0.48,
    'margin': 4.78,
    'lever': 10.0
}

def format_alert_message(position, profit_rate, alert_type, cycle_count):
    """格式化告警消息"""
    inst_id = position.get('instId')
    pos_side = position.get('posSide')
    pos_size = float(position.get('pos', 0))
    avg_price = float(position.get('avgPx', 0))
    mark_price = float(position.get('markPx', 0))
    upl = float(position.get('upl', 0))
    margin = float(position.get('margin', 0))
    lever = float(position.get('lever', 0))
    
    beijing_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    direction = "做空" if pos_side == "short" else "做多"
    
    if alert_type == "profit_target":
        alert_emoji = "📈"
        alert_title = "【锚点系统触发 - 开仓多头预警】"
        signal_type = "做空盈利40%，建议开仓做多"
    else:
        alert_emoji = "📉"
        alert_title = "【锚点系统触发 - 开仓空头预警】"
        signal_type = "做空亏损-10%，建议开仓做空"
    
    score = abs(profit_rate)
    
    message = f"""
{alert_emoji} <b>锚点系统触发</b> {alert_emoji}

{alert_title}

🎯 <b>交易信号</b>
{signal_type}

📊 <b>当前持仓数据</b>
币种: {inst_id}
持仓方向: {direction}
持仓量: {abs(pos_size):.4f}
杠杆: {lever}x
开仓均价: ${avg_price:.4f}
当前标记: ${mark_price:.4f}

💰 <b>收益情况</b>
未实现盈亏: ${upl:.2f} USDT
保证金: ${margin:.2f} USDT
<b>收益率: {profit_rate:+.2f}%</b>

📈 <b>计次数据</b>
检测次数: {cycle_count}
触发得分: {score:.2f}分

⏰ <b>触发时间</b>
{beijing_time} (北京时间)

{'=' * 35}
💡 建议: 请根据自身风险承受能力谨慎决策
"""
    
    return message.strip()

def send_telegram_message(message):
    """发送Telegram消息"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Telegram消息发送成功")
                return True
            else:
                print(f"❌ 发送失败: {result}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

# 测试1: 盈利目标告警（开仓多头预警）
print("=" * 70)
print("测试1: 盈利目标40% - 开仓多头预警")
print("=" * 70)

profit_rate = 42.11
message1 = format_alert_message(position_profit, profit_rate, "profit_target", 8)
print("\n预览消息:")
print(message1)
print("\n发送中...")
send_telegram_message(message1)

print("\n" + "=" * 70)
input("按Enter继续测试止损警告...")

# 测试2: 止损警告（开仓空头预警）
print("\n" + "=" * 70)
print("测试2: 止损警告-10% - 开仓空头预警")
print("=" * 70)

loss_rate = -10.04
message2 = format_alert_message(position_loss, loss_rate, "loss_limit", 15)
print("\n预览消息:")
print(message2)
print("\n发送中...")
send_telegram_message(message2)

print("\n" + "=" * 70)
print("✅ 测试完成！请检查Telegram群组消息")
print("=" * 70)
