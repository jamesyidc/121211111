#!/bin/bash
# 启动所有数据采集器

cd /home/user/webapp

echo "🚀 启动所有数据采集器..."
echo ""

# 1. 支撑压力线采集器
if ! pgrep -f "support_resistance_collector.py" > /dev/null; then
    echo "启动支撑压力线采集器..."
    nohup python3 -u support_resistance_collector.py > support_resistance_new.out 2>&1 &
    sleep 2
fi

# 2. 支撑压力线快照采集器  
if ! pgrep -f "support_resistance_snapshot_collector.py" > /dev/null; then
    echo "启动快照采集器..."
    nohup python3 -u support_resistance_snapshot_collector.py > snapshot_new.out 2>&1 &
    sleep 2
fi

# 3. Google Drive检测器
if ! pgrep -f "gdrive_final_detector.py" > /dev/null; then
    echo "启动Google Drive检测器..."
    nohup python3 -u gdrive_final_detector.py > gdrive_detector_new.out 2>&1 &
    sleep 2
fi

# 4. 交易信号采集器
if ! pgrep -f "signal_collector.py" > /dev/null; then
    echo "启动交易信号采集器..."
    nohup python3 -u signal_collector.py > signal_new.out 2>&1 &
    sleep 2
fi

# 5. 恐慌清洗指数采集器
if ! pgrep -f "panic_wash_collector.py" > /dev/null; then
    echo "启动恐慌清洗指数采集器..."
    nohup python3 -u panic_wash_collector.py > panic_wash_new.out 2>&1 &
    sleep 2
fi

echo ""
echo "✅ 所有采集器启动完成！"
echo ""
echo "运行中的采集器:"
ps aux | grep -E "collector|detector" | grep python | grep -v grep | awk '{print "  -", $NF}'
