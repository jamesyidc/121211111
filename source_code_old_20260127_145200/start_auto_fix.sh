#!/bin/bash
# 启动自动修复守护进程

SCRIPT_DIR="/home/user/webapp"
DAEMON_SCRIPT="$SCRIPT_DIR/auto_fix_daemon.sh"
PID_FILE="$SCRIPT_DIR/auto_fix_daemon.pid"
LOG_FILE="$SCRIPT_DIR/auto_fix_daemon.log"

echo "=========================================="
echo "🚀 启动自动修复守护进程"
echo "=========================================="

# 检查脚本是否存在
if [ ! -f "$DAEMON_SCRIPT" ]; then
    echo "❌ 守护进程脚本不存在: $DAEMON_SCRIPT"
    exit 1
fi

# 赋予执行权限
chmod +x "$DAEMON_SCRIPT"

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️  守护进程已在运行 (PID: $OLD_PID)"
        echo ""
        echo "如需重启，请先运行: bash /home/user/webapp/stop_auto_fix.sh"
        exit 0
    else
        echo "清理旧PID文件..."
        rm -f "$PID_FILE"
    fi
fi

# 启动守护进程
echo "启动守护进程..."
nohup bash "$DAEMON_SCRIPT" >> "$LOG_FILE" 2>&1 &
DAEMON_PID=$!

sleep 2

# 验证启动状态
if kill -0 "$DAEMON_PID" 2>/dev/null; then
    echo "✅ 守护进程启动成功!"
    echo ""
    echo "📊 进程信息:"
    echo "  - PID: $DAEMON_PID"
    echo "  - 日志文件: $LOG_FILE"
    echo "  - 执行间隔: 每小时"
    echo ""
    echo "📝 管理命令:"
    echo "  - 查看日志: tail -f $LOG_FILE"
    echo "  - 查看状态: ps aux | grep auto_fix_daemon"
    echo "  - 停止服务: bash /home/user/webapp/stop_auto_fix.sh"
    echo ""
    echo "🔄 首次修复任务已开始执行，请查看日志..."
else
    echo "❌ 守护进程启动失败"
    exit 1
fi

echo "=========================================="
