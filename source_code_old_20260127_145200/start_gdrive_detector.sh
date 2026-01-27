#!/bin/bash
# Google Drive TXT文件更新检测器 - 启动脚本

cd /home/user/webapp

echo "======================================================================"
echo "启动 Google Drive TXT 更新检测器"
echo "======================================================================"

# 停止旧的监控进程
pkill -f gdrive_txt_detector.py 2>/dev/null
pkill -f gdrive_monitor 2>/dev/null
sleep 2

# 启动检测器
nohup python3 gdrive_txt_detector.py > gdrive_detector_startup.log 2>&1 &
PID=$!

echo "✓ 检测器已启动 (PID: $PID)"
echo ""
echo "日志文件: /home/user/webapp/gdrive_txt_detector.log"
echo "查看日志: tail -f /home/user/webapp/gdrive_txt_detector.log"
echo ""
echo "======================================================================"
