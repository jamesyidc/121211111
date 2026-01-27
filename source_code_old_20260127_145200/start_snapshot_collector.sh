#!/bin/bash
# 启动支撑压力快照采集器

cd /home/user/webapp

# 检查是否已经在运行
if pgrep -f "support_resistance_snapshot_collector.py" > /dev/null; then
    echo "⚠️  快照采集器已在运行"
    ps aux | grep "support_resistance_snapshot_collector" | grep -v grep
else
    echo "🚀 启动快照采集器..."
    nohup python3 support_resistance_snapshot_collector.py > support_snapshot.log 2>&1 &
    sleep 2
    if pgrep -f "support_resistance_snapshot_collector.py" > /dev/null; then
        echo "✅ 快照采集器已启动"
        ps aux | grep "support_resistance_snapshot_collector" | grep -v grep
    else
        echo "❌ 启动失败"
        tail -20 support_snapshot.log
    fi
fi
