#!/bin/bash
# 恐慌清洗指标实时数据采集服务启动脚本

cd /home/user/webapp

echo "🚀 启动恐慌清洗指标实时采集服务..."
echo "📁 工作目录: $(pwd)"
echo "⏰ 采集间隔: 3分钟"
echo "🕐 时区: 北京时间"
echo ""

# 停止旧的采集进程（如果存在）
pkill -f "python3.*panic_wash_realtime.py" 2>/dev/null && echo "✅ 已停止旧的采集进程"

# 使用nohup在后台运行，自动开始采集
nohup python3 -u << 'PYEOF' > logs/realtime_collector.log 2>&1 &
from panic_wash_realtime import RealTimePanicWashCollector
from datetime import timedelta

collector = RealTimePanicWashCollector()

print("🚀 恐慌清洗指标实时采集服务启动")
print(f"⏰ 采集间隔: 180秒 (3分钟)")
print(f"🕐 时区: 北京时间 (Asia/Shanghai)")
print(f"📡 数据源: https://api.btc123.fans/")
print()

# 开始持续采集
collector.run_loop(interval=180)
PYEOF

# 获取进程ID
sleep 1
PID=$(pgrep -f "python3.*panic_wash_realtime.py" | head -1)

if [ -n "$PID" ]; then
    echo "✅ 采集服务已启动"
    echo "📝 进程ID: $PID"
    echo "📄 日志文件: logs/realtime_collector.log"
    echo ""
    echo "💡 查看日志: tail -f logs/realtime_collector.log"
    echo "🛑 停止服务: pkill -f 'python3.*panic_wash_realtime.py'"
else
    echo "❌ 服务启动失败"
    exit 1
fi
