#!/bin/bash
# 设置每日自动更新文件夹ID的cron任务

CRON_CMD="15 0 * * * cd /home/user/webapp && /usr/bin/python3 /home/user/webapp/auto_update_daily_folder.py >> /home/user/webapp/auto_folder_update.log 2>&1"

# 检查cron任务是否已存在
if crontab -l 2>/dev/null | grep -q "auto_update_daily_folder.py"; then
    echo "✅ Cron任务已存在"
    crontab -l
else
    # 添加新的cron任务
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Cron任务已添加"
    echo "   每天 00:15 自动更新文件夹ID"
    echo ""
    echo "当前cron任务列表："
    crontab -l
fi
