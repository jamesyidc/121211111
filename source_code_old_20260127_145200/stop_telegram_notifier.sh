#!/bin/bash
# Telegram通知系统停止脚本

cd /home/user/webapp

# 检查是否在运行
if ! pgrep -f "telegram_notifier.py" > /dev/null; then
    echo "⚠️  Telegram通知系统未运行"
    exit 0
fi

echo "🛑 停止Telegram通知系统..."
pkill -9 -f "telegram_notifier.py"

sleep 2

# 检查是否停止成功
if pgrep -f "telegram_notifier.py" > /dev/null; then
    echo "❌ 停止失败"
    exit 1
else
    echo "✅ Telegram通知系统已停止"
fi
