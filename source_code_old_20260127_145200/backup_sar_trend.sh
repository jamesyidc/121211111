#!/bin/bash
# SAR偏向趋势数据库备份脚本

BACKUP_DIR="/tmp/sar_trend_backups"
WEBAPP_DIR="/home/user/webapp"
DB_FILE="sar_slope_data.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BEIJING_TIME=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')

# 创建备份目录
mkdir -p $BACKUP_DIR

echo "=========================================="
echo "SAR偏向趋势数据库备份"
echo "时间: $BEIJING_TIME (北京时间)"
echo "=========================================="

# 检查数据库文件
if [ ! -f "$WEBAPP_DIR/$DB_FILE" ]; then
    echo "❌ 数据库文件不存在: $WEBAPP_DIR/$DB_FILE"
    exit 1
fi

echo -e "\n步骤1: 检查数据库状态..."
cd $WEBAPP_DIR

# 获取数据库信息
DB_SIZE=$(du -h $DB_FILE | cut -f1)
echo "  数据库大小: $DB_SIZE"

# 获取记录数
RECORD_COUNT=$(python3 << 'EOF'
import sqlite3
try:
    conn = sqlite3.connect('sar_slope_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM sar_bias_trend')
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except Exception as e:
    print(f"Error: {e}")
    exit(1)
EOF
)

if [ $? -ne 0 ]; then
    echo "❌ 无法读取数据库"
    exit 1
fi

echo "  趋势记录数: $RECORD_COUNT"

# 获取时间范围
TIME_RANGE=$(python3 << 'EOF'
import sqlite3
try:
    conn = sqlite3.connect('sar_slope_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM sar_bias_trend')
    min_time, max_time = cursor.fetchone()
    conn.close()
    print(f"{min_time} ~ {max_time}")
except Exception as e:
    print(f"Error: {e}")
EOF
)

echo "  时间范围: $TIME_RANGE"

echo -e "\n步骤2: 创建备份..."

# 备份数据库文件
BACKUP_FILE="$BACKUP_DIR/sar_slope_data_$TIMESTAMP.db"
cp $DB_FILE $BACKUP_FILE

if [ $? -ne 0 ]; then
    echo "❌ 备份失败"
    exit 1
fi

echo "  ✅ 数据库已备份: $BACKUP_FILE"

echo -e "\n步骤3: 压缩备份..."

# 压缩
cd $BACKUP_DIR
tar -czf "sar_slope_data_$TIMESTAMP.tar.gz" "sar_slope_data_$TIMESTAMP.db"

if [ $? -ne 0 ]; then
    echo "❌ 压缩失败"
    exit 1
fi

# 删除未压缩的备份
rm "sar_slope_data_$TIMESTAMP.db"

COMPRESSED_SIZE=$(du -h "sar_slope_data_$TIMESTAMP.tar.gz" | cut -f1)
echo "  ✅ 压缩完成: sar_slope_data_$TIMESTAMP.tar.gz"
echo "  压缩后大小: $COMPRESSED_SIZE"

echo -e "\n步骤4: 导出JSON备份（仅趋势数据）..."

# 导出趋势表为JSON
cd $WEBAPP_DIR
python3 << EOF
import sqlite3
import json
from datetime import datetime

try:
    conn = sqlite3.connect('sar_slope_data.db')
    cursor = conn.cursor()
    
    # 导出sar_bias_trend表
    cursor.execute('SELECT * FROM sar_bias_trend ORDER BY timestamp')
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    
    data = {
        'table': 'sar_bias_trend',
        'backup_time': '$BEIJING_TIME',
        'record_count': len(rows),
        'columns': columns,
        'data': []
    }
    
    for row in rows:
        record = {}
        for i, col in enumerate(columns):
            record[col] = row[i]
        data['data'].append(record)
    
    output_file = '$BACKUP_DIR/sar_bias_trend_$TIMESTAMP.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    conn.close()
    print(f"  ✅ JSON导出成功: {len(rows)}条记录")
    
except Exception as e:
    print(f"  ❌ JSON导出失败: {e}")
EOF

echo -e "\n步骤5: 清理旧备份..."

# 保留最近7天的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.json" -mtime +7 -delete

BACKUP_COUNT=$(ls -1 $BACKUP_DIR/*.tar.gz 2>/dev/null | wc -l)
echo "  当前备份数: $BACKUP_COUNT 个"

echo -e "\n步骤6: 创建备份清单..."

# 生成备份清单
cat > "$BACKUP_DIR/BACKUP_INFO_$TIMESTAMP.txt" << EOFINFO
SAR偏向趋势数据库备份信息
========================================
备份时间: $BEIJING_TIME (北京时间)
备份位置: $BACKUP_DIR

数据库信息:
  文件: $DB_FILE
  大小: $DB_SIZE
  记录数: $RECORD_COUNT
  时间范围: $TIME_RANGE

备份文件:
  1. 完整数据库: sar_slope_data_$TIMESTAMP.tar.gz ($COMPRESSED_SIZE)
  2. 趋势数据JSON: sar_bias_trend_$TIMESTAMP.json

恢复命令:
  # 解压并恢复完整数据库
  cd /home/user/webapp
  pm2 stop sar-bias-trend-collector flask-app
  tar -xzf $BACKUP_DIR/sar_slope_data_$TIMESTAMP.tar.gz
  cp sar_slope_data_$TIMESTAMP.db sar_slope_data.db
  pm2 restart sar-bias-trend-collector flask-app

验证命令:
  python3 -c "import sqlite3; conn=sqlite3.connect('sar_slope_data.db'); print('记录数:', conn.execute('SELECT COUNT(*) FROM sar_bias_trend').fetchone()[0]); conn.close()"

========================================
EOFINFO

echo "  ✅ 备份清单已创建"

echo -e "\n=========================================="
echo "✅ 备份完成！"
echo "=========================================="
echo "备份位置: $BACKUP_DIR"
echo "完整数据库: sar_slope_data_$TIMESTAMP.tar.gz ($COMPRESSED_SIZE)"
echo "趋势数据: sar_bias_trend_$TIMESTAMP.json"
echo "备份信息: BACKUP_INFO_$TIMESTAMP.txt"
echo "=========================================="
