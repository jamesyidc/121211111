#!/bin/bash
# 自动backfill指标数据脚本
# 每5分钟运行一次，确保指标数据与K线数据同步

cd /home/user/webapp
python3 backfill_indicators.py >> /home/user/webapp/logs/auto_backfill.log 2>&1
echo "$(date): Backfill completed" >> /home/user/webapp/logs/auto_backfill.log
