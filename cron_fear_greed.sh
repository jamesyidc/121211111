#!/bin/bash

# 恐惧贪婪指数自动采集脚本
# 每天凌晨2点运行一次

cd /home/user/webapp

# 运行采集脚本
/usr/bin/python3 /home/user/webapp/fear_greed_collector.py >> /home/user/webapp/logs/fear_greed_collector.log 2>&1

echo "✅ 恐惧贪婪指数采集完成: $(date)"
