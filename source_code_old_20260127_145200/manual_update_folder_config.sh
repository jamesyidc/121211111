#!/bin/bash

# 手动更新 daily_folder_config.json 脚本
# 用法: ./manual_update_folder_config.sh [首页数据_folder_id] [2025-12-21_folder_id]

echo "================================================================================"
echo "📝 手动更新 Google Drive 文件夹配置"
echo "================================================================================"
echo ""

# Get current date
CURRENT_DATE=$(TZ='Asia/Shanghai' date '+%Y-%m-%d')
CURRENT_TIME=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')

echo "📅 当前日期: $CURRENT_DATE"
echo "⏰ 当前时间: $CURRENT_TIME"
echo ""

# Check arguments
if [ $# -eq 0 ]; then
    echo "⚠️  使用方式:"
    echo "   方式1 (推荐): 提供两个 folder ID"
    echo "     $0 <parent_folder_id> <daily_folder_id>"
    echo ""
    echo "   方式2: 只提供 daily folder ID (保留当前的 parent_folder_id)"
    echo "     $0 <daily_folder_id>"
    echo ""
    echo "📋 当前配置:"
    cat daily_folder_config.json
    echo ""
    exit 1
fi

# Check current config
if [ ! -f "daily_folder_config.json" ]; then
    echo "❌ 配置文件不存在: daily_folder_config.json"
    exit 1
fi

echo "📄 当前配置:"
cat daily_folder_config.json | python3 -m json.tool
echo ""

# Backup current config
BACKUP_FILE="daily_folder_config_backup_$(date '+%Y%m%d_%H%M%S').json"
cp daily_folder_config.json "$BACKUP_FILE"
echo "💾 已备份当前配置到: $BACKUP_FILE"
echo ""

# Parse arguments
if [ $# -eq 2 ]; then
    PARENT_FOLDER_ID="$1"
    DAILY_FOLDER_ID="$2"
    echo "📁 使用新的 parent_folder_id: $PARENT_FOLDER_ID"
    echo "📁 使用新的 daily_folder_id: $DAILY_FOLDER_ID"
elif [ $# -eq 1 ]; then
    PARENT_FOLDER_ID=$(cat daily_folder_config.json | python3 -c "import sys, json; print(json.load(sys.stdin)['parent_folder_id'])")
    DAILY_FOLDER_ID="$1"
    echo "📁 保留当前 parent_folder_id: $PARENT_FOLDER_ID"
    echo "📁 更新 daily_folder_id: $DAILY_FOLDER_ID"
fi

echo ""
echo "🔧 正在更新配置..."

# Create new config
cat > daily_folder_config.json << EOF
{
    "current_date": "$CURRENT_DATE",
    "folder_id": "$DAILY_FOLDER_ID",
    "parent_folder_id": "$PARENT_FOLDER_ID",
    "updated_at": "$CURRENT_TIME",
    "auto_updated": false,
    "file_count": 0
}
EOF

echo "✅ 配置已更新"
echo ""

echo "📄 新配置:"
cat daily_folder_config.json | python3 -m json.tool
echo ""

# Restart services
echo "🔄 重启相关服务..."
pm2 restart gdrive-monitor 2>/dev/null
pm2 restart gdrive-auto-trigger 2>/dev/null
pm2 restart support-resistance-collector 2>/dev/null
pm2 restart support-resistance-snapshot-collector 2>/dev/null

echo ""
echo "================================================================================"
echo "✅ 配置更新完成！"
echo "================================================================================"
echo ""
echo "📊 验证步骤:"
echo "   1. 查看配置: cat daily_folder_config.json | python3 -m json.tool"
echo "   2. 查看日志: pm2 logs gdrive-monitor --lines 20 --nostream"
echo "   3. 手动触发: python3 gdrive_final_detector.py"
echo ""
echo "💡 提示: 如果数据仍然不对，请检查 folder_id 是否正确"
echo ""
