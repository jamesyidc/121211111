#!/bin/bash
# 完整备份脚本 - 备份所有项目数据到 /tmp 目录

# 配置
BACKUP_BASE="/tmp/webapp_backup"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="$BACKUP_BASE/backup_$TIMESTAMP"
SOURCE_DIR="/home/user/webapp"
LOG_FILE="$BACKUP_DIR/backup.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

# 获取文件/目录大小
get_size() {
    if [ -e "$1" ]; then
        du -sh "$1" 2>/dev/null | awk '{print $1}'
    else
        echo "0"
    fi
}

# 创建备份目录
mkdir -p "$BACKUP_DIR"
cd "$SOURCE_DIR" || exit 1

log "=========================================="
log "🚀 开始完整备份"
log "=========================================="
log "备份目录: $BACKUP_DIR"
log "源目录: $SOURCE_DIR"
log "时间戳: $TIMESTAMP"
log ""

# ============================================================
# 1. 备份数据库
# ============================================================
log "📦 1. 备份数据库..."
DB_DIR="$BACKUP_DIR/databases"
mkdir -p "$DB_DIR"

# 备份所有 .db 和 .sqlite 文件
DB_COUNT=0
if ls *.db >/dev/null 2>&1 || ls *.sqlite >/dev/null 2>&1; then
    for db in *.db *.sqlite; do
        if [ -f "$db" ] 2>/dev/null; then
            cp "$db" "$DB_DIR/" 2>/dev/null && \
                SIZE=$(get_size "$db") && \
                log "  ✅ $db (大小: $SIZE)" && \
                DB_COUNT=$((DB_COUNT + 1))
        fi
    done
else
    log_warn "  未找到数据库文件"
fi

# 导出数据库为SQL格式
if [ "$DB_COUNT" -gt 0 ]; then
    log "  📤 导出数据库为SQL格式..."
    for db in "$DB_DIR"/*.db; do
        if [ -f "$db" ]; then
            DB_NAME=$(basename "$db")
            sqlite3 "$db" .dump > "$DB_DIR/${DB_NAME}.sql" 2>/dev/null && \
                log "  ✅ ${DB_NAME}.sql 导出成功" || \
                log_warn "  跳过 ${DB_NAME} SQL导出"
        fi
    done
fi

log "  📊 数据库备份完成: $DB_COUNT 个数据库文件"
log ""

# ============================================================
# 2. 备份源码
# ============================================================
log "📝 2. 备份源码..."
CODE_DIR="$BACKUP_DIR/source_code"
mkdir -p "$CODE_DIR"

# 备份所有源码文件（排除缓存和临时文件）
log "  复制源码文件..."
rsync -av \
    --exclude='node_modules/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.git/' \
    --exclude='*.log' \
    --exclude='*.log.*' \
    --exclude='.pytest_cache/' \
    --exclude='.coverage' \
    --exclude='dist/' \
    --exclude='build/' \
    "$SOURCE_DIR/" "$CODE_DIR/" >> "$LOG_FILE" 2>&1

CODE_SIZE=$(get_size "$CODE_DIR")
CODE_FILES=$(find "$CODE_DIR" -type f | wc -l)
log "  ✅ 源码备份完成"
log "  📊 文件数量: $CODE_FILES 个"
log "  💾 总大小: $CODE_SIZE"
log ""

# ============================================================
# 3. 备份依赖
# ============================================================
log "📚 3. 备份项目依赖..."
DEP_DIR="$BACKUP_DIR/dependencies"
mkdir -p "$DEP_DIR"

# Python 依赖
if [ -f "requirements.txt" ]; then
    log "  🐍 备份Python依赖..."
    cp requirements.txt "$DEP_DIR/"
    pip freeze > "$DEP_DIR/requirements_frozen.txt" 2>/dev/null
    log "  ✅ requirements.txt"
    log "  ✅ requirements_frozen.txt (当前环境)"
fi

# Node.js 依赖
if [ -f "package.json" ]; then
    log "  📦 备份Node.js依赖..."
    cp package.json "$DEP_DIR/"
    [ -f "package-lock.json" ] && cp package-lock.json "$DEP_DIR/"
    [ -f "yarn.lock" ] && cp yarn.lock "$DEP_DIR/"
    log "  ✅ package.json"
    [ -f "package-lock.json" ] && log "  ✅ package-lock.json"
    [ -f "yarn.lock" ] && log "  ✅ yarn.lock"
    
    # 备份 node_modules（可选，体积较大）
    if [ -d "node_modules" ]; then
        log "  📦 压缩 node_modules..."
        tar -czf "$DEP_DIR/node_modules.tar.gz" node_modules/ 2>/dev/null && \
            log "  ✅ node_modules.tar.gz ($(get_size "$DEP_DIR/node_modules.tar.gz"))" || \
            log_warn "  node_modules 备份失败（可能体积过大）"
    fi
fi

# Python 虚拟环境信息
if [ -d "venv" ] || [ -d ".venv" ]; then
    log "  🐍 记录虚拟环境信息..."
    python3 --version > "$DEP_DIR/python_version.txt" 2>&1
    log "  ✅ Python版本信息已保存"
fi

log "  📊 依赖备份完成"
log ""

# ============================================================
# 4. 备份完整缓存
# ============================================================
log "💾 4. 备份完整缓存..."
CACHE_DIR="$BACKUP_DIR/cache"
mkdir -p "$CACHE_DIR"

# 备份数据库缓存
if [ -f "crypto_data.db" ]; then
    log "  📊 备份数据库缓存内容..."
    sqlite3 crypto_data.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" > "$CACHE_DIR/db_table_count.txt" 2>/dev/null
    sqlite3 crypto_data.db ".tables" > "$CACHE_DIR/db_tables.txt" 2>/dev/null
    log "  ✅ 数据库表信息已保存"
fi

# 备份 home_cache 表
if [ -f "crypto_data.db" ]; then
    sqlite3 crypto_data.db "SELECT * FROM home_cache ORDER BY id DESC LIMIT 1;" > "$CACHE_DIR/home_cache_latest.txt" 2>/dev/null || true
    log "  ✅ 最新缓存数据已保存"
fi

# 备份所有缓存文件
CACHE_FILES=("*.cache" "*.tmp" "*_cache.txt" "*_latest.txt")
CACHE_COUNT=0
for pattern in "${CACHE_FILES[@]}"; do
    for file in $pattern; do
        if [ -f "$file" ] 2>/dev/null; then
            cp "$file" "$CACHE_DIR/" 2>/dev/null && \
                log "  ✅ $file" && \
                CACHE_COUNT=$((CACHE_COUNT + 1))
        fi
    done
done

log "  📊 缓存备份完成: $CACHE_COUNT 个缓存文件"
log ""

# ============================================================
# 5. 备份 Git 完整仓库
# ============================================================
log "📂 5. 备份Git完整仓库..."
GIT_DIR="$BACKUP_DIR/git_repository"
mkdir -p "$GIT_DIR"

if [ -d ".git" ]; then
    log "  🔄 备份 .git 目录..."
    cp -r .git "$GIT_DIR/"
    
    # 备份 Git 配置
    git config --list > "$GIT_DIR/git_config.txt" 2>/dev/null
    git remote -v > "$GIT_DIR/git_remotes.txt" 2>/dev/null
    git branch -a > "$GIT_DIR/git_branches.txt" 2>/dev/null
    git log --oneline -20 > "$GIT_DIR/git_recent_commits.txt" 2>/dev/null
    git status > "$GIT_DIR/git_status.txt" 2>/dev/null
    
    GIT_SIZE=$(get_size "$GIT_DIR")
    log "  ✅ Git仓库备份完成"
    log "  💾 大小: $GIT_SIZE"
    log "  📊 最近20次提交已记录"
else
    log_warn "  未找到 .git 目录"
fi
log ""

# ============================================================
# 6. 备份 PM2 配置
# ============================================================
log "⚙️  6. 备份PM2配置..."
PM2_DIR="$BACKUP_DIR/pm2_config"
mkdir -p "$PM2_DIR"

if command -v pm2 >/dev/null 2>&1; then
    log "  📋 导出PM2配置..."
    
    # PM2 列表
    pm2 jlist > "$PM2_DIR/pm2_list.json" 2>/dev/null && \
        log "  ✅ pm2_list.json"
    
    # PM2 状态
    pm2 status > "$PM2_DIR/pm2_status.txt" 2>/dev/null && \
        log "  ✅ pm2_status.txt"
    
    # PM2 环境变量
    pm2 env 0 > "$PM2_DIR/pm2_env.txt" 2>/dev/null || true
    
    # 备份 PM2 配置文件
    if [ -f "ecosystem.config.js" ]; then
        cp ecosystem.config.js "$PM2_DIR/"
        log "  ✅ ecosystem.config.js"
    fi
    
    if [ -f "pm2.config.js" ]; then
        cp pm2.config.js "$PM2_DIR/"
        log "  ✅ pm2.config.js"
    fi
    
    # 导出 PM2 启动脚本
    pm2 startup > "$PM2_DIR/pm2_startup_command.txt" 2>/dev/null || true
    
    log "  📊 PM2配置备份完成"
else
    log_warn "  PM2未安装"
fi
log ""

# ============================================================
# 7. 备份完整日志
# ============================================================
log "📄 7. 备份完整日志..."
LOGS_DIR="$BACKUP_DIR/logs"
mkdir -p "$LOGS_DIR"

# 备份所有日志文件
LOG_COUNT=0
shopt -s nullglob
for logfile in *.log *.log.*; do
    if [ -f "$logfile" ]; then
        cp "$logfile" "$LOGS_DIR/" && \
            SIZE=$(get_size "$logfile") && \
            log "  ✅ $logfile ($SIZE)" && \
            LOG_COUNT=$((LOG_COUNT + 1))
    fi
done
shopt -u nullglob

if [ "$LOG_COUNT" -eq 0 ]; then
    log_warn "  未找到日志文件"
fi

# 备份 PM2 日志
if [ -d "$HOME/.pm2/logs" ]; then
    log "  📋 备份PM2日志..."
    mkdir -p "$LOGS_DIR/pm2"
    cp -r "$HOME/.pm2/logs/"* "$LOGS_DIR/pm2/" 2>/dev/null || true
    PM2_LOG_COUNT=$(find "$LOGS_DIR/pm2" -type f | wc -l)
    log "  ✅ PM2日志: $PM2_LOG_COUNT 个文件"
fi

LOGS_SIZE=$(get_size "$LOGS_DIR")
log "  📊 日志备份完成"
log "  📄 项目日志: $LOG_COUNT 个文件"
log "  💾 总大小: $LOGS_SIZE"
log ""

# ============================================================
# 8. 系统配置转存
# ============================================================
log "⚙️  8. 系统配置转存..."
SYS_DIR="$BACKUP_DIR/system_config"
mkdir -p "$SYS_DIR"

# 系统信息
log "  💻 收集系统信息..."
uname -a > "$SYS_DIR/system_info.txt" 2>/dev/null
cat /etc/os-release > "$SYS_DIR/os_release.txt" 2>/dev/null || true
df -h > "$SYS_DIR/disk_usage.txt" 2>/dev/null
free -m > "$SYS_DIR/memory_usage.txt" 2>/dev/null
ps aux > "$SYS_DIR/running_processes.txt" 2>/dev/null
lsof -i -P -n > "$SYS_DIR/network_connections.txt" 2>/dev/null || true
env > "$SYS_DIR/environment_variables.txt" 2>/dev/null

log "  ✅ system_info.txt"
log "  ✅ os_release.txt"
log "  ✅ disk_usage.txt"
log "  ✅ memory_usage.txt"
log "  ✅ running_processes.txt"
log "  ✅ network_connections.txt"
log "  ✅ environment_variables.txt"

# Python 环境
if command -v python3 >/dev/null 2>&1; then
    log "  🐍 Python环境信息..."
    python3 --version > "$SYS_DIR/python_version.txt" 2>&1
    pip list > "$SYS_DIR/pip_packages.txt" 2>/dev/null || true
    log "  ✅ Python版本和包列表"
fi

# Node.js 环境
if command -v node >/dev/null 2>&1; then
    log "  📦 Node.js环境信息..."
    node --version > "$SYS_DIR/node_version.txt" 2>&1
    npm --version > "$SYS_DIR/npm_version.txt" 2>&1
    npm list -g --depth=0 > "$SYS_DIR/npm_global_packages.txt" 2>/dev/null || true
    log "  ✅ Node.js和npm版本"
fi

log "  📊 系统配置转存完成"
log ""

# ============================================================
# 9. 备份应用配置文件
# ============================================================
log "📋 9. 备份应用配置文件..."
CONFIG_DIR="$BACKUP_DIR/app_config"
mkdir -p "$CONFIG_DIR"

# 常见配置文件
CONFIG_FILES=(
    ".env"
    ".env.local"
    ".env.production"
    "config.json"
    "config.js"
    "config.py"
    "settings.py"
    "settings.json"
    ".gitignore"
    ".npmrc"
    ".pylintrc"
    "tsconfig.json"
    "webpack.config.js"
    "babel.config.js"
    "supervisord.conf"
    "nginx.conf"
)

CONFIG_COUNT=0
for config in "${CONFIG_FILES[@]}"; do
    if [ -f "$config" ]; then
        cp "$config" "$CONFIG_DIR/"
        log "  ✅ $config"
        CONFIG_COUNT=$((CONFIG_COUNT + 1))
    fi
done

# 备份所有 shell 脚本
shopt -s nullglob
SCRIPT_FILES=(*.sh)
shopt -u nullglob

if [ ${#SCRIPT_FILES[@]} -gt 0 ]; then
    log "  📜 备份Shell脚本..."
    mkdir -p "$CONFIG_DIR/scripts"
    for script in "${SCRIPT_FILES[@]}"; do
        if [ -f "$script" ]; then
            cp "$script" "$CONFIG_DIR/scripts/" && \
                log "  ✅ $script" && \
                CONFIG_COUNT=$((CONFIG_COUNT + 1))
        fi
    done
fi

log "  📊 配置文件备份完成: $CONFIG_COUNT 个文件"
log ""

# ============================================================
# 10. 创建备份清单
# ============================================================
log "📋 10. 创建备份清单..."
MANIFEST="$BACKUP_DIR/BACKUP_MANIFEST.txt"

cat > "$MANIFEST" << EOF
========================================
完整备份清单
========================================
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份目录: $BACKUP_DIR
源目录: $SOURCE_DIR
主机名: $(hostname)
用户: $(whoami)

========================================
1. 数据库 (databases/)
========================================
EOF

if [ -d "$DB_DIR" ]; then
    echo "数据库文件数量: $(find "$DB_DIR" -name "*.db" -o -name "*.sqlite" | wc -l)" >> "$MANIFEST"
    echo "SQL导出文件数量: $(find "$DB_DIR" -name "*.sql" | wc -l)" >> "$MANIFEST"
    echo "总大小: $(get_size "$DB_DIR")" >> "$MANIFEST"
    echo "" >> "$MANIFEST"
    echo "文件列表:" >> "$MANIFEST"
    ls -lh "$DB_DIR" >> "$MANIFEST" 2>/dev/null
fi

cat >> "$MANIFEST" << EOF

========================================
2. 源码 (source_code/)
========================================
文件数量: $CODE_FILES
总大小: $CODE_SIZE

========================================
3. 依赖 (dependencies/)
========================================
EOF

if [ -d "$DEP_DIR" ]; then
    ls -lh "$DEP_DIR" >> "$MANIFEST" 2>/dev/null
fi

cat >> "$MANIFEST" << EOF

========================================
4. 缓存 (cache/)
========================================
缓存文件数量: $CACHE_COUNT
总大小: $(get_size "$CACHE_DIR")

========================================
5. Git仓库 (git_repository/)
========================================
EOF

if [ -d "$GIT_DIR" ]; then
    echo "仓库大小: $(get_size "$GIT_DIR")" >> "$MANIFEST"
    echo "" >> "$MANIFEST"
    [ -f "$GIT_DIR/git_remotes.txt" ] && cat "$GIT_DIR/git_remotes.txt" >> "$MANIFEST"
    echo "" >> "$MANIFEST"
    [ -f "$GIT_DIR/git_branches.txt" ] && cat "$GIT_DIR/git_branches.txt" >> "$MANIFEST"
fi

cat >> "$MANIFEST" << EOF

========================================
6. PM2配置 (pm2_config/)
========================================
EOF

if [ -d "$PM2_DIR" ]; then
    ls -lh "$PM2_DIR" >> "$MANIFEST" 2>/dev/null
fi

cat >> "$MANIFEST" << EOF

========================================
7. 日志 (logs/)
========================================
日志文件数量: $LOG_COUNT
总大小: $LOGS_SIZE

========================================
8. 系统配置 (system_config/)
========================================
EOF

if [ -d "$SYS_DIR" ]; then
    ls -lh "$SYS_DIR" >> "$MANIFEST" 2>/dev/null
fi

cat >> "$MANIFEST" << EOF

========================================
9. 应用配置 (app_config/)
========================================
配置文件数量: $CONFIG_COUNT

========================================
备份目录结构
========================================
EOF

tree -L 2 "$BACKUP_DIR" >> "$MANIFEST" 2>/dev/null || \
    find "$BACKUP_DIR" -maxdepth 2 -type d >> "$MANIFEST" 2>/dev/null

cat >> "$MANIFEST" << EOF

========================================
总计
========================================
备份总大小: $(get_size "$BACKUP_DIR")
备份文件数量: $(find "$BACKUP_DIR" -type f | wc -l)
备份目录数量: $(find "$BACKUP_DIR" -type d | wc -l)

========================================
恢复说明
========================================
1. 数据库恢复:
   cp databases/*.db /home/user/webapp/
   或使用SQL文件: sqlite3 db_name.db < db_name.sql

2. 源码恢复:
   cp -r source_code/* /home/user/webapp/

3. 依赖恢复:
   pip install -r dependencies/requirements.txt
   npm install (从 package.json)

4. Git仓库恢复:
   cp -r git_repository/.git /home/user/webapp/

5. PM2恢复:
   pm2 resurrect (如果有保存)
   或使用 ecosystem.config.js 重新配置

6. 日志恢复 (可选):
   cp logs/* /home/user/webapp/

========================================
备份完成时间: $(date '+%Y-%m-%d %H:%M:%S')
========================================
EOF

log "  ✅ 备份清单已创建: BACKUP_MANIFEST.txt"
log ""

# ============================================================
# 11. 压缩备份（可选）
# ============================================================
log "🗜️  11. 压缩备份..."
ARCHIVE_NAME="webapp_backup_$TIMESTAMP.tar.gz"
ARCHIVE_PATH="$BACKUP_BASE/$ARCHIVE_NAME"

cd "$BACKUP_BASE"
tar -czf "$ARCHIVE_NAME" "backup_$TIMESTAMP/" 2>/dev/null && \
    log "  ✅ 备份已压缩: $ARCHIVE_NAME" || \
    log_warn "  压缩失败，保留未压缩版本"

if [ -f "$ARCHIVE_PATH" ]; then
    ARCHIVE_SIZE=$(get_size "$ARCHIVE_PATH")
    log "  💾 压缩包大小: $ARCHIVE_SIZE"
    log "  📍 压缩包路径: $ARCHIVE_PATH"
fi
log ""

# ============================================================
# 12. 创建快速恢复脚本
# ============================================================
log "🔄 12. 创建快速恢复脚本..."
RESTORE_SCRIPT="$BACKUP_DIR/RESTORE.sh"

cat > "$RESTORE_SCRIPT" << 'RESTORE_EOF'
#!/bin/bash
# 快速恢复脚本

echo "=========================================="
echo "🔄 开始恢复备份"
echo "=========================================="

BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/home/user/webapp"

read -p "确认恢复到 $TARGET_DIR? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 恢复已取消"
    exit 1
fi

# 1. 恢复数据库
if [ -d "$BACKUP_DIR/databases" ]; then
    echo "📦 恢复数据库..."
    cp -v "$BACKUP_DIR/databases"/*.db "$TARGET_DIR/" 2>/dev/null || true
fi

# 2. 恢复源码
if [ -d "$BACKUP_DIR/source_code" ]; then
    echo "📝 恢复源码..."
    rsync -av "$BACKUP_DIR/source_code/" "$TARGET_DIR/"
fi

# 3. 恢复Git仓库
if [ -d "$BACKUP_DIR/git_repository/.git" ]; then
    echo "📂 恢复Git仓库..."
    cp -r "$BACKUP_DIR/git_repository/.git" "$TARGET_DIR/"
fi

# 4. 恢复配置文件
if [ -d "$BACKUP_DIR/app_config" ]; then
    echo "⚙️  恢复配置文件..."
    cp -v "$BACKUP_DIR/app_config"/* "$TARGET_DIR/" 2>/dev/null || true
    [ -d "$BACKUP_DIR/app_config/scripts" ] && \
        cp -v "$BACKUP_DIR/app_config/scripts"/* "$TARGET_DIR/" 2>/dev/null || true
fi

# 5. 恢复依赖（提示用户手动安装）
echo ""
echo "=========================================="
echo "⚠️  请手动安装依赖:"
echo "=========================================="
if [ -f "$BACKUP_DIR/dependencies/requirements.txt" ]; then
    echo "Python: pip install -r $BACKUP_DIR/dependencies/requirements.txt"
fi
if [ -f "$BACKUP_DIR/dependencies/package.json" ]; then
    echo "Node.js: cd $TARGET_DIR && npm install"
fi

echo ""
echo "=========================================="
echo "✅ 恢复完成!"
echo "=========================================="
echo "请检查服务状态并手动重启必要的服务"
RESTORE_EOF

chmod +x "$RESTORE_SCRIPT"
log "  ✅ 恢复脚本已创建: RESTORE.sh"
log ""

# ============================================================
# 完成
# ============================================================
TOTAL_SIZE=$(get_size "$BACKUP_DIR")
TOTAL_FILES=$(find "$BACKUP_DIR" -type f | wc -l)

log "=========================================="
log "✅ 完整备份完成!"
log "=========================================="
log "📍 备份位置: $BACKUP_DIR"
log "💾 备份大小: $TOTAL_SIZE"
log "📄 文件数量: $TOTAL_FILES"
log ""

if [ -f "$ARCHIVE_PATH" ]; then
    log "📦 压缩包: $ARCHIVE_PATH"
    log "💾 压缩包大小: $ARCHIVE_SIZE"
    log ""
fi

log "📋 备份内容:"
log "  1. ✅ 数据库 ($DB_COUNT 个)"
log "  2. ✅ 源码 ($CODE_FILES 个文件)"
log "  3. ✅ 依赖配置"
log "  4. ✅ 缓存数据 ($CACHE_COUNT 个)"
log "  5. ✅ Git完整仓库"
log "  6. ✅ PM2配置"
log "  7. ✅ 完整日志 ($LOG_COUNT 个)"
log "  8. ✅ 系统配置"
log "  9. ✅ 应用配置 ($CONFIG_COUNT 个)"
log " 10. ✅ 备份清单"
log " 11. ✅ 恢复脚本"
log ""

log "📖 查看备份清单:"
log "  cat $MANIFEST"
log ""

log "🔄 恢复备份:"
log "  bash $RESTORE_SCRIPT"
log ""

log "=========================================="
log "备份日志已保存: $LOG_FILE"
log "=========================================="

# 显示 /tmp 目录使用情况
TMP_USAGE=$(df -h /tmp | tail -1 | awk '{print $5}')
log ""
log_info "/tmp 目录使用率: $TMP_USAGE"

# 列出所有备份
log ""
log "📦 /tmp 中的所有备份:"
ls -lth "$BACKUP_BASE" | head -20

exit 0
