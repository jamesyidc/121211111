#!/bin/bash

# OKEx K线指标采集器控制脚本
# 描述: 控制决策-K线指标系统的启动、停止、状态查看

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

COLLECTOR_SCRIPT="okex_websocket_realtime_collector_fixed.py"
PID_FILE="okex_indicators.pid"
LOG_FILE="okex_indicators.log"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  OKEx K线指标采集器已经在运行 (PID: $PID)"
            return 1
        fi
    fi
    
    echo "🚀 启动 OKEx K线指标采集器..."
    # 激活虚拟环境并启动
    nohup bash -c "source venv/bin/activate && python3 $COLLECTOR_SCRIPT" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    sleep 2
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ OKEx K线指标采集器已启动 (PID: $PID)"
        echo "   日志文件: $LOG_FILE"
        echo "   采集周期: 实时WebSocket"
        echo "   币种数量: 27个"
        return 0
    else
        echo "❌ OKEx K线指标采集器启动失败，请检查日志"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️  OKEx K线指标采集器未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 停止 OKEx K线指标采集器 (PID: $PID)..."
        kill "$PID"
        sleep 2
        
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  正常停止失败，强制终止..."
            kill -9 "$PID"
        fi
        
        rm -f "$PID_FILE"
        echo "✅ OKEx K线指标采集器已停止"
        return 0
    else
        echo "⚠️  进程不存在，清理PID文件"
        rm -f "$PID_FILE"
        return 1
    fi
}

restart() {
    echo "🔄 重启 OKEx K线指标采集器..."
    stop
    sleep 1
    start
}

status() {
    echo "=== OKEx K线指标采集器状态 ==="
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 运行状态: 运行中"
            echo "   PID: $PID"
            ps -p "$PID" -o pid,etime,rss,cmd | tail -1 | awk '{printf "   运行时长: %s\n   内存占用: %d MB\n", $2, $3/1024}'
            echo "   日志文件: $LOG_FILE"
        else
            echo "❌ 运行状态: 未运行 (PID文件存在但进程不存在)"
        fi
    else
        echo "❌ 运行状态: 未运行"
    fi
    
    # 检查数据库最新数据
    echo -e "\n=== 数据库状态 ==="
    python3 << 'PYEOF'
import sqlite3
from datetime import datetime

try:
    conn = sqlite3.connect('crypto_data.db', timeout=10.0)
    cursor = conn.cursor()
    
    # 检查okex_technical_indicators表
    try:
        cursor.execute("SELECT COUNT(*) FROM okex_technical_indicators")
        total = cursor.fetchone()[0]
        print(f"   总记录数: {total}")
        
        cursor.execute("""
            SELECT symbol, record_time 
            FROM okex_technical_indicators 
            ORDER BY record_time DESC 
            LIMIT 3
        """)
        rows = cursor.fetchall()
        if rows:
            print(f"   最新数据:")
            for row in rows:
                print(f"     {row[0]}: {row[1]}")
        else:
            print("   ⚠️  暂无数据")
    except Exception as e:
        print(f"   ❌ 查询失败: {e}")
    
    conn.close()
except Exception as e:
    print(f"   ❌ 数据库连接失败: {e}")
PYEOF
}

logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "=== 最新日志 (最后50行) ==="
        tail -50 "$LOG_FILE"
    else
        echo "⚠️  日志文件不存在"
    fi
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
        echo "用法: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "  start   - 启动 OKEx K线指标采集器"
        echo "  stop    - 停止 OKEx K线指标采集器"
        echo "  restart - 重启 OKEx K线指标采集器"
        echo "  status  - 查看运行状态和最新数据"
        echo "  logs    - 查看最新日志"
        exit 1
        ;;
esac

exit 0
