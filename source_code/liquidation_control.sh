#!/bin/bash
# 30日爆仓数据采集器控制脚本

SCRIPT_DIR="/home/user/webapp"
COLLECTOR_SCRIPT="$SCRIPT_DIR/liquidation_history_collector.py"
PID_FILE="$SCRIPT_DIR/liquidation_collector.pid"
LOG_FILE="$SCRIPT_DIR/liquidation_collector.log"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "❌ 30日爆仓采集器已在运行 (PID: $PID)"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "🚀 启动30日爆仓数据采集器..."
    cd "$SCRIPT_DIR"
    nohup python3 "$COLLECTOR_SCRIPT" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    
    if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        echo "✅ 30日爆仓采集器启动成功 (PID: $(cat $PID_FILE))"
        echo "📝 日志文件: $LOG_FILE"
        echo "⏰ 采集间隔: 1小时"
    else
        echo "❌ 启动失败，请检查日志: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️  30日爆仓采集器未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 停止30日爆仓采集器 (PID: $PID)..."
        kill "$PID"
        sleep 2
        
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  进程未响应，强制终止..."
            kill -9 "$PID"
        fi
        
        rm -f "$PID_FILE"
        echo "✅ 30日爆仓采集器已停止"
    else
        echo "⚠️  进程不存在，清理PID文件"
        rm -f "$PID_FILE"
    fi
}

status() {
    if [ ! -f "$PID_FILE" ]; then
        echo "❌ 30日爆仓采集器未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        # 计算运行时间
        START_TIME=$(ps -p "$PID" -o lstart=)
        CURRENT_TIME=$(date)
        
        echo "✅ 30日爆仓采集器正在运行"
        echo "   PID: $PID"
        echo "   启动时间: $START_TIME"
        echo "   日志文件: $LOG_FILE"
        echo ""
        echo "📊 最近3条采集记录:"
        if [ -f "$LOG_FILE" ]; then
            tail -20 "$LOG_FILE" | grep "成功保存/更新" | tail -3
        fi
    else
        echo "❌ 30日爆仓采集器未运行 (PID文件存在但进程不存在)"
        rm -f "$PID_FILE"
        return 1
    fi
}

restart() {
    echo "🔄 重启30日爆仓采集器..."
    stop
    sleep 2
    start
}

logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "⚠️  日志文件不存在: $LOG_FILE"
        return 1
    fi
    
    echo "📝 显示最近30行日志:"
    echo "----------------------------------------"
    tail -30 "$LOG_FILE"
}

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
        logs
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "  start   - 启动30日爆仓采集器"
        echo "  stop    - 停止30日爆仓采集器"
        echo "  restart - 重启30日爆仓采集器"
        echo "  status  - 查看运行状态"
        echo "  logs    - 查看日志"
        exit 1
        ;;
esac

exit 0
