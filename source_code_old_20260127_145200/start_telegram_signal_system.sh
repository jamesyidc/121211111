#!/bin/bash
# 启动Telegram信号推送系统

cd /home/user/webapp

# 检查是否已经在运行
if [ -f telegram_signal_system.pid ]; then
    PID=$(cat telegram_signal_system.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Telegram信号系统已在运行 (PID: $PID)"
        exit 1
    fi
fi

# 启动服务
nohup python3 telegram_signal_system.py > telegram_signal_system_output.log 2>&1 &
PID=$!

# 保存PID
echo $PID > telegram_signal_system.pid

echo "✅ Telegram信号推送系统已启动 (PID: $PID)"
echo "📝 日志文件: telegram_signal_system.log"
echo "📊 输出文件: telegram_signal_system_output.log"
echo ""
echo "查看日志: tail -f telegram_signal_system.log"
echo "停止服务: ./stop_telegram_signal_system.sh"
