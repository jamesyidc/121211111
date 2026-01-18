#!/bin/bash
# 自动采集守护进程控制脚本

DAEMON_SCRIPT="/home/user/webapp/auto_collect_daemon.py"
PID_FILE="/home/user/webapp/auto_collect.pid"
LOG_FILE="/home/user/webapp/auto_collect.log"

# 启动守护进程
start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "❌ 守护进程已在运行 (PID: $PID)"
            return 1
        else
            echo "⚠️  PID文件存在但进程已停止，清理旧PID文件..."
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "🚀 启动自动采集守护进程..."
    nohup python3 "$DAEMON_SCRIPT" >> "$LOG_FILE" 2>&1 &
    sleep 2
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "✅ 守护进程已启动 (PID: $PID)"
        echo "📝 日志文件: $LOG_FILE"
        echo "🔄 采集间隔: 10分钟"
        return 0
    else
        echo "❌ 启动失败，请检查日志: $LOG_FILE"
        return 1
    fi
}

# 停止守护进程
stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "❌ 守护进程未运行 (PID文件不存在)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "❌ 守护进程未运行 (PID: $PID 不存在)"
        rm -f "$PID_FILE"
        return 1
    fi
    
    echo "🛑 停止守护进程 (PID: $PID)..."
    kill -TERM $PID
    
    # 等待进程结束
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            echo "✅ 守护进程已停止"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # 强制结束
    echo "⚠️  进程未响应，强制结束..."
    kill -9 $PID
    rm -f "$PID_FILE"
    echo "✅ 守护进程已强制停止"
    return 0
}

# 查看状态
status() {
    if [ ! -f "$PID_FILE" ]; then
        echo "❌ 守护进程未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ 守护进程正在运行"
        echo "   PID: $PID"
        echo "   运行时间: $(ps -p $PID -o etime= | tr -d ' ')"
        echo "   日志文件: $LOG_FILE"
        echo ""
        echo "📊 最近10条日志:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        tail -n 10 "$LOG_FILE"
        return 0
    else
        echo "❌ 守护进程未运行 (PID: $PID 不存在)"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 重启守护进程
restart() {
    echo "🔄 重启守护进程..."
    stop
    sleep 2
    start
}

# 查看日志
logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "❌ 日志文件不存在: $LOG_FILE"
        return 1
    fi
    
    if [ "$1" == "-f" ]; then
        echo "📝 实时日志 (Ctrl+C 退出):"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        tail -f "$LOG_FILE"
    else
        echo "📝 最近50条日志:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        tail -n 50 "$LOG_FILE"
    fi
}

# 主逻辑
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs [-f]}"
        echo ""
        echo "命令说明:"
        echo "  start    - 启动自动采集守护进程"
        echo "  stop     - 停止自动采集守护进程"
        echo "  restart  - 重启自动采集守护进程"
        echo "  status   - 查看守护进程状态"
        echo "  logs     - 查看最近50条日志"
        echo "  logs -f  - 实时查看日志"
        exit 1
        ;;
esac

exit $?
