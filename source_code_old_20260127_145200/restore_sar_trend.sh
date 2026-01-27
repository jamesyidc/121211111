#!/bin/bash
# SAR偏向趋势数据库恢复脚本

BACKUP_DIR="/tmp/sar_trend_backups"
WEBAPP_DIR="/home/user/webapp"
DB_FILE="sar_slope_data.db"
BEIJING_TIME=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')

echo "=========================================="
echo "SAR偏向趋势数据库恢复"
echo "时间: $BEIJING_TIME (北京时间)"
echo "=========================================="

# 检查备份目录
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ 备份目录不存在: $BACKUP_DIR"
    exit 1
fi

# 列出可用备份
echo -e "\n可用的备份文件:"
echo "----------------------------------------"
ls -lht $BACKUP_DIR/*.tar.gz 2>/dev/null | head -10 | awk '{print $9, "(" $5 ")", $6, $7, $8}'

if [ $? -ne 0 ] || [ $(ls -1 $BACKUP_DIR/*.tar.gz 2>/dev/null | wc -l) -eq 0 ]; then
    echo "❌ 没有可用的备份文件"
    exit 1
fi

echo "----------------------------------------"

# 选择备份文件
echo -e "\n请输入要恢复的备份文件名（不含路径）:"
echo "例如: sar_slope_data_20251226_222500.tar.gz"
read -p "> " BACKUP_FILE

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ 未指定备份文件"
    exit 1
fi

FULL_BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

if [ ! -f "$FULL_BACKUP_PATH" ]; then
    echo "❌ 备份文件不存在: $FULL_BACKUP_PATH"
    exit 1
fi

echo -e "\n选择的备份: $BACKUP_FILE"
echo "大小: $(du -h $FULL_BACKUP_PATH | cut -f1)"

# 确认恢复
echo -e "\n⚠️  警告: 此操作将覆盖当前数据库！"
read -p "是否继续恢复? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

echo -e "\n步骤1: 停止相关服务..."
pm2 stop sar-bias-trend-collector 2>/dev/null
pm2 stop flask-app 2>/dev/null
sleep 2
echo "  ✅ 服务已停止"

echo -e "\n步骤2: 备份当前数据库..."
cd $WEBAPP_DIR

if [ -f "$DB_FILE" ]; then
    CURRENT_BACKUP="sar_slope_data_before_restore_$(date +%Y%m%d_%H%M%S).db"
    cp $DB_FILE $CURRENT_BACKUP
    echo "  ✅ 当前数据库已备份: $CURRENT_BACKUP"
else
    echo "  ⚠️  当前数据库不存在，跳过备份"
fi

echo -e "\n步骤3: 解压备份文件..."
cd $BACKUP_DIR

# 提取不含.tar.gz的文件名
BASE_NAME=$(basename $BACKUP_FILE .tar.gz)

tar -xzf $BACKUP_FILE

if [ $? -ne 0 ]; then
    echo "❌ 解压失败"
    exit 1
fi

echo "  ✅ 解压完成: $BASE_NAME.db"

echo -e "\n步骤4: 恢复数据库..."
cd $WEBAPP_DIR

cp "$BACKUP_DIR/$BASE_NAME.db" $DB_FILE

if [ $? -ne 0 ]; then
    echo "❌ 恢复失败"
    exit 1
fi

echo "  ✅ 数据库文件已恢复"

# 清理解压的文件
rm "$BACKUP_DIR/$BASE_NAME.db"

echo -e "\n步骤5: 验证数据库完整性..."

python3 << 'EOF'
import sqlite3
import sys

try:
    conn = sqlite3.connect('sar_slope_data.db')
    cursor = conn.cursor()
    
    # 完整性检查
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]
    
    if result != 'ok':
        print(f"❌ 数据库完整性检查失败: {result}")
        sys.exit(1)
    
    print("  ✅ 数据库完整性检查通过")
    
    # 检查sar_bias_trend表
    cursor.execute("SELECT COUNT(*) FROM sar_bias_trend")
    count = cursor.fetchone()[0]
    print(f"  ✅ sar_bias_trend表: {count}条记录")
    
    # 获取时间范围
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM sar_bias_trend")
    min_time, max_time = cursor.fetchone()
    print(f"  ✅ 时间范围: {min_time} ~ {max_time}")
    
    # 最新数据
    cursor.execute("""
        SELECT timestamp, bullish_count, bearish_count 
        FROM sar_bias_trend 
        ORDER BY timestamp DESC 
        LIMIT 3
    """)
    print(f"\n  最新3条数据:")
    for row in cursor.fetchall():
        print(f"    {row[0]}  偏多:{row[1]:2d}  偏空:{row[2]:2d}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ 验证失败: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "\n❌ 数据库验证失败，请检查备份文件"
    exit 1
fi

echo -e "\n步骤6: 重启服务..."
pm2 restart sar-bias-trend-collector 2>/dev/null
pm2 restart flask-app 2>/dev/null
sleep 2

# 检查服务状态
echo -e "\n服务状态:"
pm2 status | grep -E "sar-bias-trend-collector|flask-app"

echo -e "\n=========================================="
echo "✅ 恢复完成！"
echo "=========================================="
echo "数据库: $DB_FILE"
echo "备份源: $BACKUP_FILE"
echo "恢复时间: $BEIJING_TIME (北京时间)"
echo "=========================================="

echo -e "\n访问页面验证:"
echo "https://5000-iawcy3xxhnan90u0qd9wq-cc2fbc16.sandbox.novita.ai/sar-bias-trend"

echo -e "\n如需查看API数据:"
echo "curl http://localhost:5000/api/sar-slope/bias-trend?page=1"
