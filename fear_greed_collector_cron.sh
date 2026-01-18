#!/bin/bash
# 恐慌贪婪指数定时采集脚本
# 每天早上10点执行

cd /home/user/webapp
/usr/bin/python3 fear_greed_collector.py >> logs/fear_greed_cron.log 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 定时采集完成" >> logs/fear_greed_cron.log
