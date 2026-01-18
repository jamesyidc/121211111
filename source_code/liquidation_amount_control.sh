#!/bin/bash
# 爆仓金额采集器控制脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTOR_SCRIPT="$SCRIPT_DIR/liquidation_amount_collector.py"
PID_FILE="$SCRIPT_DIR/liquidation_amount_collector.pid"
LOG_FILE="$SCRIPT_DIR/liquidation_amount_collector.log"

cd "$SCRIPT_DIR"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  爆仓金额采集器已在运行 (PID: $PID)"
            return 1
        else
            echo "🔧 清理旧的PID文件..."
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "🚀 启动爆仓金额采集器..."
    nohup python3 "$COLLECTOR_SCRIPT" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    sleep 2
    
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ 爆仓金额采集器已启动 (PID: $PID)"
        echo "📋 日志文件: $LOG_FILE"
        echo "💡 使用 'tail -f $LOG_FILE' 查看实时日志"
    else
        echo "❌ 启动失败，请检查日志: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️  爆仓金额采集器未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 停止爆仓金额采集器 (PID: $PID)..."
        kill -TERM "$PID"
        sleep 2
        
        # 如果进程还在运行，强制终止
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  进程未响应，强制终止..."
            kill -9 "$PID"
            sleep 1
        fi
        
        rm -f "$PID_FILE"
        echo "✅ 爆仓金额采集器已停止"
    else
        echo "⚠️  进程不存在 (PID: $PID)，清理PID文件"
        rm -f "$PID_FILE"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 爆仓金额采集器正在运行"
            echo "   PID: $PID"
            echo "   日志: $LOG_FILE"
            
            # 显示最后几行日志
            if [ -f "$LOG_FILE" ]; then
                echo ""
                echo "📋 最近日志:"
                tail -5 "$LOG_FILE"
            fi
        else
            echo "❌ 爆仓金额采集器未运行 (PID文件存在但进程不存在)"
        fi
    else
        echo "❌ 爆仓金额采集器未运行"
    fi
}

restart() {
    echo "🔄 重启爆仓金额采集器..."
    stop
    sleep 2
    start
}

logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "❌ 日志文件不存在: $LOG_FILE"
    fi
}

test_once() {
    echo "🧪 测试运行爆仓金额采集器（单次）..."
    python3 "$COLLECTOR_SCRIPT" --once
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
    test)
        test_once
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动爆仓金额采集器"
        echo "  stop    - 停止爆仓金额采集器"
        echo "  restart - 重启爆仓金额采集器"
        echo "  status  - 查看采集器状态"
        echo "  logs    - 实时查看日志"
        echo "  test    - 测试运行（单次采集）"
        exit 1
        ;;
esac

exit 0
