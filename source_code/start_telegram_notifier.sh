#!/bin/bash
# Telegram通知系统启动脚本

cd /home/user/webapp

# 检查是否已运行
if pgrep -f "telegram_notifier.py" > /dev/null; then
    echo "⚠️  Telegram通知系统已在运行中"
    echo "PID: $(pgrep -f telegram_notifier.py)"
    exit 1
fi

# 启动服务
echo "🚀 启动Telegram通知系统..."
nohup python3 telegram_notifier.py > telegram_notifier.log 2>&1 &

sleep 2

# 检查是否启动成功
if pgrep -f "telegram_notifier.py" > /dev/null; then
    echo "✅ Telegram通知系统启动成功"
    echo "PID: $(pgrep -f telegram_notifier.py)"
    echo "📋 查看日志: tail -f /home/user/webapp/telegram_notifier.log"
else
    echo "❌ 启动失败，请查看日志"
    tail -20 telegram_notifier.log
    exit 1
fi
