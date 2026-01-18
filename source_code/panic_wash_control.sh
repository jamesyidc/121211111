#!/bin/bash
# 恐慌清洗指数采集器控制脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/panic_wash_collector.pid"
LOG_FILE="$SCRIPT_DIR/panic_wash_collector.log"

case "$1" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "❌ 恐慌清洗指数采集器已在运行中 (PID: $(cat $PID_FILE))"
            exit 1
        fi
        
        echo "🚀 启动恐慌清洗指数采集器..."
        cd "$SCRIPT_DIR"
        nohup python3 panic_wash_collector.py > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 2
        
        if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "✅ 恐慌清洗指数采集器已启动 (PID: $(cat $PID_FILE))"
            echo "📊 采集间隔: 3分钟"
            echo "📝 日志文件: $LOG_FILE"
        else
            echo "❌ 启动失败，请查看日志: $LOG_FILE"
            rm -f "$PID_FILE"
            exit 1
        fi
        ;;
        
    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "❌ 恐慌清洗指数采集器未运行"
            exit 1
        fi
        
        PID=$(cat "$PID_FILE")
        echo "⛔ 停止恐慌清洗指数采集器 (PID: $PID)..."
        kill -15 $PID 2>/dev/null
        sleep 2
        
        if kill -0 $PID 2>/dev/null; then
            echo "⚠️ 进程未响应，强制停止..."
            kill -9 $PID 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        echo "✅ 恐慌清洗指数采集器已停止"
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            PID=$(cat "$PID_FILE")
            echo "✅ 恐慌清洗指数采集器运行中"
            echo "   PID: $PID"
            echo "   运行时间: $(ps -o etime= -p $PID 2>/dev/null | xargs)"
            echo "   日志文件: $LOG_FILE"
            echo ""
            echo "📊 最近3条采集记录:"
            cd "$SCRIPT_DIR"
            python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()
cursor.execute("""
    SELECT record_time, panic_index, hour_24_people, total_position
    FROM panic_wash_index
    ORDER BY record_time DESC
    LIMIT 3
""")
for row in cursor.fetchall():
    people_wan = row[2] / 10000
    position_yi = row[3] / 100000000
    print(f"   {row[0]} | 恐慌指数:{row[1]}% ({people_wan:.2f}万人/{position_yi:.2f}亿)")
conn.close()
EOF
        else
            echo "❌ 恐慌清洗指数采集器未运行"
            [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
        fi
        ;;
        
    logs)
        if [ ! -f "$LOG_FILE" ]; then
            echo "❌ 日志文件不存在"
            exit 1
        fi
        tail -f "$LOG_FILE"
        ;;
        
    *)
        echo "使用方法: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动恐慌清洗指数采集器"
        echo "  stop    - 停止恐慌清洗指数采集器"
        echo "  restart - 重启恐慌清洗指数采集器"
        echo "  status  - 查看运行状态"
        echo "  logs    - 查看实时日志"
        exit 1
        ;;
esac

exit 0
