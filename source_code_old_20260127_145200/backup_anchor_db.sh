#!/bin/bash

################################################################################
# 锚点系统数据库备份脚本
# 功能：备份 anchor_system.db 数据库文件
# 作者：GenSpark AI Developer
# 日期：2025-12-27
################################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
DB_PATH="/home/user/webapp/anchor_system.db"
BACKUP_DIR="/home/user/webapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/anchor_system_${DATE}.db"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "================================================================================"
echo -e "${GREEN}🔧 锚点系统数据库备份${NC}"
echo "================================================================================"
echo ""
echo "数据库路径: $DB_PATH"
echo "备份目录: $BACKUP_DIR"
echo "备份文件: anchor_system_${DATE}.db"
echo ""

# 检查数据库文件是否存在
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}❌ 错误: 数据库文件不存在！${NC}"
    exit 1
fi

# 获取数据库大小
DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
echo "数据库大小: $DB_SIZE"
echo ""

# 执行备份
echo "开始备份..."
cp "$DB_PATH" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ 备份成功！${NC}"
    echo "备份文件: $BACKUP_FILE"
    echo "备份大小: $BACKUP_SIZE"
    
    # 显示数据库统计
    echo ""
    echo "================================================================================"
    echo "📊 数据库统计"
    echo "================================================================================"
    
    python3 << 'EOF'
import sqlite3
import sys

try:
    db_path = '/home/user/webapp/anchor_system.db'
    conn = sqlite3.connect(db_path, timeout=10.0)
    cursor = conn.cursor()
    
    # 监控记录数
    cursor.execute('SELECT COUNT(*) FROM anchor_monitors')
    monitor_count = cursor.fetchone()[0]
    print(f"监控记录数: {monitor_count}")
    
    # 告警记录数
    cursor.execute('SELECT COUNT(*) FROM anchor_alerts')
    alert_count = cursor.fetchone()[0]
    print(f"告警记录数: {alert_count}")
    
    # 极值记录数
    cursor.execute('SELECT COUNT(*) FROM anchor_profit_records')
    record_count = cursor.fetchone()[0]
    print(f"极值记录数: {record_count}")
    
    # 币种统计
    cursor.execute('SELECT DISTINCT inst_id FROM anchor_monitors')
    instruments = [row[0] for row in cursor.fetchall()]
    print(f"监控币种数: {len(instruments)}")
    
    if instruments:
        print(f"币种列表: {', '.join(instruments)}")
    
    # 最新记录时间
    cursor.execute('SELECT MAX(timestamp) FROM anchor_monitors')
    latest = cursor.fetchone()[0]
    if latest:
        print(f"最新记录: {latest}")
    
    conn.close()
    
except Exception as e:
    print(f"统计失败: {e}", file=sys.stderr)
    sys.exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "================================================================================"
        echo -e "${GREEN}✅ 备份完成！${NC}"
        echo "================================================================================"
        
        # 列出最近的备份文件
        echo ""
        echo "最近的备份文件 (最多显示5个):"
        ls -lht "$BACKUP_DIR"/*.db 2>/dev/null | head -5 | awk '{print "  " $9 " (" $5 ")"}'
        
        # 备份数量统计
        BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.db 2>/dev/null | wc -l)
        echo ""
        echo "总备份数: $BACKUP_COUNT"
        
        # 清理建议
        if [ $BACKUP_COUNT -gt 10 ]; then
            echo ""
            echo -e "${YELLOW}💡 提示: 备份文件较多，建议定期清理旧备份${NC}"
            echo "   清理命令: find $BACKUP_DIR -name '*.db' -mtime +30 -delete"
        fi
    fi
else
    echo -e "${RED}❌ 备份失败！${NC}"
    exit 1
fi

echo ""
echo "================================================================================"
