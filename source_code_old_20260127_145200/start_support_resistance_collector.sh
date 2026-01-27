#!/bin/bash
# 支撑压力线采集器启动脚本

cd /home/user/webapp

# 检查是否已经在运行
if pgrep -f "support_resistance_collector.py" > /dev/null; then
    echo "⚠️  支撑压力线采集器已在运行"
    ps aux | grep support_resistance_collector.py | grep -v grep
    exit 1
fi

# 启动采集器
echo "🚀 启动支撑压力线采集器..."
nohup python3 support_resistance_collector.py > /dev/null 2>&1 &

sleep 2

# 检查是否启动成功
if pgrep -f "support_resistance_collector.py" > /dev/null; then
    PID=$(pgrep -f "support_resistance_collector.py")
    echo "✅ 支撑压力线采集器启动成功！PID: $PID"
    echo "📊 监控27个币种的支撑压力线"
    echo "⏰ 每5分钟采集一次"
    echo ""
    echo "查看日志: tail -f support_resistance.log"
    echo "停止采集: pkill -f support_resistance_collector.py"
else
    echo "❌ 启动失败"
    exit 1
fi
