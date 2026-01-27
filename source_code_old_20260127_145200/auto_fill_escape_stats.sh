#!/bin/bash
# 自动补全逃顶信号统计数据的定时任务

cd /home/user/webapp

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始补全逃顶信号数据..."
    python3 fill_escape_signal_stats.py >> /home/user/webapp/fill_escape_signal_stats.log 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 补全完成，等待60秒..."
    sleep 60
done
