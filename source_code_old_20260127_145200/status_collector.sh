#!/bin/bash
# 查看 Google Drive 自动采集器状态

SCRIPT_DIR="/home/user/webapp"
cd "$SCRIPT_DIR" || exit 1

echo "======================================================"
echo "🔍 Google Drive 自动采集器状态"
echo "======================================================"

# 检查进程状态
if [ -f "logs/collector.pid" ]; then
    PID=$(cat logs/collector.pid)
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✓ 采集器正在运行 (PID: $PID)"
        
        # 显示进程信息
        echo ""
        echo "进程信息:"
        ps -p "$PID" -o pid,ppid,cmd,%cpu,%mem,etime
    else
        echo "✗ 采集器未运行（进程不存在）"
        rm logs/collector.pid 2>/dev/null
    fi
else
    echo "✗ 采集器未运行（PID文件不存在）"
fi

echo ""
echo "======================================================"
echo "📊 数据库统计"
echo "======================================================"

# 显示数据库统计
python3 auto_gdrive_collector_v2.py --status

echo ""
echo "======================================================"
echo "📝 最新日志（最后20行）"
echo "======================================================"

if [ -f "logs/collector.log" ]; then
    tail -20 logs/collector.log
else
    echo "日志文件不存在"
fi

echo ""
echo "======================================================"
echo "💡 常用命令"
echo "======================================================"
echo "启动采集器: ./start_collector.sh"
echo "停止采集器: ./stop_collector.sh"
echo "查看实时日志: tail -f logs/collector.log"
echo "手动执行一次: python3 auto_gdrive_collector_v2.py --once"
echo "======================================================"
