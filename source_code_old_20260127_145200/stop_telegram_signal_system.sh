#!/bin/bash
# 停止Telegram信号推送系统

cd /home/user/webapp

if [ ! -f telegram_signal_system.pid ]; then
    echo "⚠️  Telegram信号系统未运行"
    exit 1
fi

PID=$(cat telegram_signal_system.pid)

if ps -p $PID > /dev/null 2>&1; then
    kill $PID
    echo "✅ Telegram信号系统已停止 (PID: $PID)"
    rm telegram_signal_system.pid
else
    echo "⚠️  进程不存在 (PID: $PID)"
    rm telegram_signal_system.pid
fi
