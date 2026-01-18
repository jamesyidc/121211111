#!/bin/bash
# TG信号监控系统控制脚本

SCRIPT_DIR="/home/user/webapp"
SCRIPT_NAME="tg_signal_monitor.py"
LOG_FILE="${SCRIPT_DIR}/tg_signal_monitor.log"
VENV_PATH="${SCRIPT_DIR}/venv"

cd "$SCRIPT_DIR"

case "$1" in
    start)
        if pgrep -f "$SCRIPT_NAME" > /dev/null; then
            echo "❌ TG信号监控系统已在运行"
            exit 1
        fi
        echo "🚀 启动TG信号监控系统..."
        source "${VENV_PATH}/bin/activate"
        nohup python3 -u "$SCRIPT_NAME" > "$LOG_FILE" 2>&1 &
        sleep 2
        if pgrep -f "$SCRIPT_NAME" > /dev/null; then
            echo "✅ TG信号监控系统已启动"
            echo "📝 日志文件: $LOG_FILE"
        else
            echo "❌ TG信号监控系统启动失败，请查看日志"
        fi
        ;;
    stop)
        echo "🛑 停止TG信号监控系统..."
        pkill -f "$SCRIPT_NAME"
        sleep 2
        if ! pgrep -f "$SCRIPT_NAME" > /dev/null; then
            echo "✅ TG信号监控系统已停止"
        else
            echo "❌ 停止失败，强制结束..."
            pkill -9 -f "$SCRIPT_NAME"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if pgrep -f "$SCRIPT_NAME" > /dev/null; then
            PID=$(pgrep -f "$SCRIPT_NAME" | head -1)
            UPTIME=$(ps -p $PID -o etime= | tr -d ' ')
            MEM=$(ps -p $PID -o rss= | awk '{printf "%.0f", $1/1024}')
            echo "✅ TG信号监控系统运行中"
            echo "   PID: $PID"
            echo "   运行时间: $UPTIME"
            echo "   内存使用: ${MEM} MB"
            echo ""
            echo "📊 数据库统计:"
            python3 << 'PYEOF'
import sqlite3
try:
    conn = sqlite3.connect('tg_signals.db', timeout=5)
    c = conn.cursor()
    # 检查发送历史
    c.execute("SELECT COUNT(*) FROM signal_history WHERE sent_time >= datetime('now', '-1 hour')")
    count_1h = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM signal_history WHERE sent_time >= datetime('now', '-1 day')")
    count_1d = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM signal_history")
    count_total = c.fetchone()[0]
    
    # 获取最近发送的5条记录
    c.execute("""SELECT signal_type, symbol, signal_name, sent_time 
                 FROM signal_history 
                 ORDER BY created_at DESC LIMIT 5""")
    recent = c.fetchall()
    
    print(f"   最近1小时发送: {count_1h} 条")
    print(f"   最近24小时发送: {count_1d} 条")
    print(f"   总计发送: {count_total} 条")
    
    if recent:
        print("\n📝 最近5条发送记录:")
        for r in recent:
            print(f"   - {r[2]} ({r[1]}) at {r[3]}")
    
    conn.close()
except Exception as e:
    print(f"   ⚠️ 无法读取数据库: {e}")
PYEOF
        else
            echo "❌ TG信号监控系统未运行"
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
        echo "用法: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
