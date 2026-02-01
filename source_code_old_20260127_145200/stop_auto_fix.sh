#!/bin/bash
# 停止自动修复守护进程

SCRIPT_DIR="/home/user/webapp"
PID_FILE="$SCRIPT_DIR/auto_fix_daemon.pid"

echo "=========================================="
echo "🛑 停止自动修复守护进程"
echo "=========================================="

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  守护进程未运行（无PID文件）"
    
    # 尝试查找并停止进程
    RUNNING_PID=$(ps aux | grep "auto_fix_daemon.sh" | grep -v grep | awk '{print $2}')
    if [ -n "$RUNNING_PID" ]; then
        echo "发现运行中的进程 (PID: $RUNNING_PID)，尝试停止..."
        kill -15 $RUNNING_PID 2>/dev/null
        sleep 2
        if kill -0 $RUNNING_PID 2>/dev/null; then
            echo "进程未响应，强制终止..."
            kill -9 $RUNNING_PID 2>/dev/null
        fi
        echo "✅ 进程已停止"
    else
        echo "未发现运行中的进程"
    fi
    exit 0
fi

# 读取PID
PID=$(cat "$PID_FILE")
echo "PID文件: $PID_FILE"
echo "进程ID: $PID"

# 检查进程是否存在
if kill -0 "$PID" 2>/dev/null; then
    echo "停止进程..."
    
    # 尝试优雅停止
    kill -15 "$PID" 2>/dev/null
    
    # 等待最多5秒
    for i in {1..5}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "✅ 守护进程已停止"
            rm -f "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    # 如果还在运行，强制停止
    if kill -0 "$PID" 2>/dev/null; then
        echo "进程未响应，强制终止..."
        kill -9 "$PID" 2>/dev/null
        sleep 1
        echo "✅ 守护进程已强制停止"
    fi
else
    echo "⚠️  进程不存在（可能已停止）"
fi

# 清理PID文件
rm -f "$PID_FILE"
echo "PID文件已清理"

echo "=========================================="
