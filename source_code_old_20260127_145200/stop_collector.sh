#!/bin/bash
# 停止 Google Drive 自动采集器

SCRIPT_DIR="/home/user/webapp"
cd "$SCRIPT_DIR" || exit 1

if [ ! -f "logs/collector.pid" ]; then
    echo "✗ 采集器未运行（PID文件不存在）"
    exit 1
fi

PID=$(cat logs/collector.pid)

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "✗ 采集器未运行（进程不存在）"
    rm logs/collector.pid
    exit 1
fi

echo "🛑 停止采集器 (PID: $PID)..."
kill -TERM "$PID"

# 等待进程结束
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✓ 采集器已停止"
        rm logs/collector.pid
        exit 0
    fi
    sleep 1
done

# 强制结束
echo "⚠️  进程未响应，强制结束..."
kill -9 "$PID"
rm logs/collector.pid
echo "✓ 采集器已强制停止"
