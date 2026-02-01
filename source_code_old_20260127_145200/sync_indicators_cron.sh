#!/bin/bash
# 技术指标自动同步脚本（Cron任务）
# 每5分钟运行一次，为新K线计算技术指标

cd /home/user/webapp

# 运行技术指标同步脚本
/usr/bin/python3 sync_technical_indicators.py >> logs/sync_indicators.log 2>&1

# 记录执行时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 技术指标同步完成" >> logs/sync_indicators_cron.log
