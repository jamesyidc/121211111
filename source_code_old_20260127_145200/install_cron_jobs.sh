#!/bin/bash
"""
安装定时任务脚本
- 磁盘监控：每小时执行一次
- 数据库维护：每6小时执行一次
- 日志清理：每天凌晨2点执行一次
"""

WEBAPP_DIR="/home/user/webapp"

echo "🔧 正在安装定时维护任务..."
echo ""

# 创建临时crontab文件
TEMP_CRON=$(mktemp)

# 获取当前用户的crontab（如果有的话）
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# 添加注释说明
echo "" >> "$TEMP_CRON"
echo "# ========================================" >> "$TEMP_CRON"
echo "# Crypto Data Webapp Auto Maintenance" >> "$TEMP_CRON"
echo "# 自动添加于: $(date '+%Y-%m-%d %H:%M:%S')" >> "$TEMP_CRON"
echo "# ========================================" >> "$TEMP_CRON"

# 1. 磁盘监控 - 每小时执行一次
echo "" >> "$TEMP_CRON"
echo "# 磁盘空间监控 (每小时执行)" >> "$TEMP_CRON"
echo "0 * * * * cd $WEBAPP_DIR && /usr/bin/python3 disk_monitor.py >> logs/disk_monitor_cron.log 2>&1" >> "$TEMP_CRON"

# 2. 数据库维护 - 每6小时执行一次 (0:00, 6:00, 12:00, 18:00)
echo "" >> "$TEMP_CRON"
echo "# 数据库自动维护 (每6小时执行)" >> "$TEMP_CRON"
echo "0 */6 * * * cd $WEBAPP_DIR && /usr/bin/python3 db_maintenance.py >> logs/db_maintenance_cron.log 2>&1" >> "$TEMP_CRON"

# 3. 日志清理 - 每天凌晨2点执行
echo "" >> "$TEMP_CRON"
echo "# 日志文件清理 (每天凌晨2点)" >> "$TEMP_CRON"
echo "0 2 * * * cd $WEBAPP_DIR && /bin/bash cleanup_logs.sh >> logs/cleanup_cron.log 2>&1" >> "$TEMP_CRON"

# 4. WAL紧急清理 - 每天凌晨3点执行（额外保险）
echo "" >> "$TEMP_CRON"
echo "# SQLite WAL紧急清理 (每天凌晨3点)" >> "$TEMP_CRON"
echo "0 3 * * * cd $WEBAPP_DIR && /usr/bin/python3 -c \"import sqlite3; conn=sqlite3.connect('crypto_data.db'); conn.execute('PRAGMA wal_checkpoint(TRUNCATE)'); conn.close()\" >> logs/wal_emergency_cron.log 2>&1" >> "$TEMP_CRON"

echo "" >> "$TEMP_CRON"

# 安装新的crontab
crontab "$TEMP_CRON"

# 清理临时文件
rm "$TEMP_CRON"

echo "✅ 定时任务安装成功！"
echo ""
echo "📋 已安装的定时任务："
echo "  1️⃣  磁盘监控：每小时执行一次"
echo "  2️⃣  数据库维护：每6小时执行一次 (0:00, 6:00, 12:00, 18:00)"
echo "  3️⃣  日志清理：每天凌晨2:00执行"
echo "  4️⃣  WAL紧急清理：每天凌晨3:00执行"
echo ""
echo "🔍 查看当前crontab配置："
echo "----------------------------------------"
crontab -l | grep -A 20 "Crypto Data Webapp"
echo "----------------------------------------"
echo ""
echo "💡 提示："
echo "  - 查看定时任务：crontab -l"
echo "  - 编辑定时任务：crontab -e"
echo "  - 删除所有定时任务：crontab -r"
echo "  - 查看执行日志：tail -f logs/*_cron.log"
