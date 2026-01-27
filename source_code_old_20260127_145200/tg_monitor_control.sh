#!/bin/bash
# TG信号监控系统控制脚本

SCRIPT_DIR="/home/user/webapp"
SCRIPT_NAME="tg_signal_monitor.py"
LOG_FILE="$SCRIPT_DIR/tg_signal_monitor.log"
PID_FILE="$SCRIPT_DIR/tg_monitor.pid"
VENV_PATH="$SCRIPT_DIR/venv"

cd "$SCRIPT_DIR" || exit 1

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "❌ TG监控系统已在运行 (PID: $PID)"
                exit 1
            fi
        fi
        
        echo "🚀 启动TG信号监控系统..."
        source "$VENV_PATH/bin/activate"
        nohup python3 -u "$SCRIPT_NAME" > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 2
        
        if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
            echo "✅ TG监控系统启动成功 (PID: $(cat "$PID_FILE"))"
            echo "📝 日志文件: $LOG_FILE"
        else
            echo "❌ TG监控系统启动失败，请检查日志"
            rm -f "$PID_FILE"
            exit 1
        fi
        ;;
        
    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "❌ PID文件不存在，系统可能未运行"
            pkill -f "$SCRIPT_NAME"
            exit 0
        fi
        
        PID=$(cat "$PID_FILE")
        echo "🛑 停止TG监控系统 (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 2
        
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️ 进程未响应，强制终止..."
            kill -9 "$PID" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        echo "✅ TG监控系统已停止"
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "✅ TG监控系统正在运行"
                echo "PID: $PID"
                ps -p "$PID" -o pid,etime,%mem,cmd --no-headers
                
                echo -e "\n📊 数据库状态:"
                if [ -f "$SCRIPT_DIR/tg_signals.db" ]; then
                    python3 << EOF
import sqlite3
conn = sqlite3.connect('$SCRIPT_DIR/tg_signals.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM signal_history")
signal_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM send_history WHERE status='success'")
send_count = cursor.fetchone()[0]
cursor.execute("SELECT sent_time FROM signal_history ORDER BY id DESC LIMIT 1")
latest = cursor.fetchone()
conn.close()
print(f"  信号记录: {signal_count}")
print(f"  成功发送: {send_count}")
if latest:
    print(f"  最新信号: {latest[0]}")
EOF
                else
                    echo "  数据库文件不存在"
                fi
            else
                echo "❌ TG监控系统未运行 (PID文件存在但进程不存在)"
                rm -f "$PID_FILE"
            fi
        else
            echo "❌ TG监控系统未运行"
        fi
        ;;
        
    logs)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "❌ 日志文件不存在"
        fi
        ;;
        
    *)
        echo "使用方法: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
