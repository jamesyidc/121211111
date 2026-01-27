#!/bin/bash
# 完整备份脚本 - 加密货币监控系统
# 使用方法: ./create_backup.sh

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/webapp_backup_${TIMESTAMP}"
WEBAPP_DIR="/home/user/webapp"

echo "=================================================================================="
echo "           加密货币监控系统 - 完整备份脚本"
echo "=================================================================================="
echo
echo "⏰ 开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📂 备份目录: $BACKUP_DIR"
echo

# 创建备份目录结构
mkdir -p "$BACKUP_DIR"/{databases,source_code,dependencies,git,pm2_config,logs,system_logs}

# 1. 备份数据库
echo "📦 [1/8] 备份数据库..."
cd "$WEBAPP_DIR" && cp *.db "$BACKUP_DIR/databases/" 2>/dev/null && echo "✅ 完成"

# 2. 备份源码
echo "📦 [2/8] 备份源码..."
tar -czf "$BACKUP_DIR/source_code/webapp_source.tar.gz" \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='*.db' \
  --exclude='*.log' \
  --exclude='venv' \
  --exclude='.venv' \
  -C "$WEBAPP_DIR" . && echo "✅ 完成"

# 3. 备份Python依赖
echo "📦 [3/8] 备份Python依赖..."
pip3 freeze > "$BACKUP_DIR/dependencies/requirements.txt" 2>&1 && echo "✅ 完成"

# 4. 备份Git仓库
echo "📦 [4/8] 备份Git仓库..."
cd "$WEBAPP_DIR" && tar -czf "$BACKUP_DIR/git/git_repo.tar.gz" .git && echo "✅ 完成"

# 5. 备份Git信息
git log --oneline -10 > "$BACKUP_DIR/git/recent_commits.txt"
git branch -a > "$BACKUP_DIR/git/branches.txt"

# 6. 备份PM2配置
echo "📦 [5/8] 备份PM2配置..."
if command -v pm2 &> /dev/null; then
    pm2 save 2>&1 | grep -v "WARN" || true
    cp -r ~/.pm2 "$BACKUP_DIR/pm2_config/" 2>/dev/null || true
fi
echo "✅ 完成"

# 7. 备份应用日志
echo "📦 [6/8] 备份应用日志..."
cd "$WEBAPP_DIR" && find . -maxdepth 1 -name "*.log" -type f -exec cp {} "$BACKUP_DIR/logs/" \; 2>/dev/null
echo "✅ 完成"

# 8. 备份系统日志
echo "📦 [7/8] 备份系统日志..."
[ -f "/tmp/flask.log" ] && cp /tmp/flask.log "$BACKUP_DIR/system_logs/"
echo "✅ 完成"

# 创建清单
echo "📦 [8/8] 创建备份清单..."
cat > "$BACKUP_DIR/BACKUP_MANIFEST.txt" << EOF
================================================================================
                    加密货币监控系统 - 完整备份清单
================================================================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份目录: $BACKUP_DIR

内容: 数据库、源码、Git仓库、依赖、PM2配置、日志
================================================================================
EOF
echo "✅ 完成"

# 创建最终压缩包
echo
echo "🗜️  创建最终压缩包..."
cd /tmp
FINAL_BACKUP="webapp_complete_backup_${TIMESTAMP}.tar.gz"
tar -czf "$FINAL_BACKUP" "webapp_backup_${TIMESTAMP}/" 2>&1 | grep -v "socket ignored" || true

echo
echo "=================================================================================="
echo "                          ✅ 备份完成！"
echo "=================================================================================="
echo
echo "📦 备份文件: /tmp/$FINAL_BACKUP"
echo "📊 文件大小: $(ls -lh /tmp/$FINAL_BACKUP | awk '{print $5}')"
echo "⏰ 完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo
echo "📤 转存到AI Drive:"
echo "   cp /tmp/$FINAL_BACKUP /mnt/aidrive/"
echo
echo "=================================================================================="
