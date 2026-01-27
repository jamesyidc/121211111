#!/bin/bash
# 日志清理脚本 - 保留最近7天的日志

LOG_DIR="/home/user/webapp/logs"
RETENTION_DAYS=7

echo "========================================="
echo "🧹 开始清理旧日志文件"
echo "========================================="
echo "日志目录: $LOG_DIR"
echo "保留天数: $RETENTION_DAYS 天"
echo ""

# 清理超过7天的日志文件
find "$LOG_DIR" -name "*.log" -type f -mtime +$RETENTION_DAYS -exec rm -f {} \;

# 截断过大的日志文件（超过100MB）
find "$LOG_DIR" -name "*.log" -type f -size +100M -exec sh -c 'echo "Truncated at $(date)" > "$1"' _ {} \;

echo ""
echo "✅ 日志清理完成"
echo ""
echo "📊 当前日志目录大小:"
du -sh "$LOG_DIR"
echo ""
echo "💾 磁盘使用情况:"
df -h /
