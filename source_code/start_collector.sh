#!/bin/bash
# 启动 Google Drive 自动采集器

SCRIPT_DIR="/home/user/webapp"
cd "$SCRIPT_DIR" || exit 1

# 创建日志目录
mkdir -p logs

# 检查是否已经在运行
if [ -f "logs/collector.pid" ]; then
    PID=$(cat logs/collector.pid)
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✗ 采集器已经在运行 (PID: $PID)"
        exit 1
    fi
fi

# 启动采集器
echo "🚀 启动 Google Drive 自动采集器..."
nohup python3 auto_gdrive_collector_v2.py > logs/collector.log 2>&1 &
PID=$!

# 保存PID
echo $PID > logs/collector.pid

echo "✓ 采集器已启动 (PID: $PID)"
echo "📝 日志文件: logs/collector.log"
echo ""
echo "查看日志: tail -f logs/collector.log"
echo "停止采集: ./stop_collector.sh"
echo "查看状态: python3 auto_gdrive_collector_v2.py --status"
