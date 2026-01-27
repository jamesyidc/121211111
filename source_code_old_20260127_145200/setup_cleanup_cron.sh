#!/bin/bash
# 设置每日00:10执行父文件夹ID清理任务

SCRIPT_PATH="/home/user/webapp/cleanup_unused_folder_id.py"
LOG_PATH="/home/user/webapp/cleanup_cron.log"

# 创建cron任务
CRON_JOB="10 0 * * * cd /home/user/webapp && /usr/bin/python3 $SCRIPT_PATH >> $LOG_PATH 2>&1"

echo "🔧 设置每日清理任务..."
echo ""
echo "任务详情:"
echo "  执行时间: 每天 00:10 (北京时间)"
echo "  脚本路径: $SCRIPT_PATH"
echo "  日志路径: $LOG_PATH"
echo ""

# 检查是否已存在相同的cron任务
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "⚠️  检测到已存在的清理任务，将先移除..."
    crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" | crontab -
fi

# 添加新的cron任务
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron任务添加成功！"
echo ""
echo "当前cron任务列表:"
crontab -l
echo ""
echo "📝 任务说明:"
echo "  - 如果今天是单数日期(1,3,5,7,9,11...)，删除双数父文件夹ID"
echo "  - 如果今天是双数日期(2,4,6,8,10,12...)，删除单数父文件夹ID"
echo "  - 只保留当天应该使用的父文件夹ID"
echo ""
echo "🧪 测试命令:"
echo "  python3 $SCRIPT_PATH"
echo ""
