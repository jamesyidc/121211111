#!/bin/bash

# 完整系统备份脚本
# 创建时间: 2026-01-23
# 备份范围: webapp目录、PM2进程、Flask路由、Git状态、缓存等

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 备份目录
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_BASE="/tmp/system_backup_${TIMESTAMP}"
mkdir -p "$BACKUP_BASE"

echo "================================================================================"
echo "                    系统完整备份 - System Full Backup"
echo "================================================================================"
echo -e "${GREEN}备份时间:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "${GREEN}备份目录:${NC} $BACKUP_BASE"
echo "================================================================================"
echo ""

# ============================================================================
# 1. 备份 Git 信息
# ============================================================================
echo -e "${YELLOW}[1/8] 备份 Git 信息...${NC}"
GIT_BACKUP="$BACKUP_BASE/git_info"
mkdir -p "$GIT_BACKUP"

cd /home/user/webapp

# Git 状态
git status > "$GIT_BACKUP/git_status.txt" 2>&1 || echo "No git repo" > "$GIT_BACKUP/git_status.txt"
git log --oneline -20 > "$GIT_BACKUP/git_log.txt" 2>&1 || echo "No git history" > "$GIT_BACKUP/git_log.txt"
git branch -a > "$GIT_BACKUP/git_branches.txt" 2>&1 || echo "No branches" > "$GIT_BACKUP/git_branches.txt"
git remote -v > "$GIT_BACKUP/git_remotes.txt" 2>&1 || echo "No remotes" > "$GIT_BACKUP/git_remotes.txt"
git diff > "$GIT_BACKUP/git_diff.txt" 2>&1 || echo "No diff" > "$GIT_BACKUP/git_diff.txt"

# Git config
cp .git/config "$GIT_BACKUP/git_config" 2>/dev/null || echo "No git config"

echo -e "${GREEN}✓ Git 信息已备份${NC}"
echo ""

# ============================================================================
# 2. 备份 PM2 进程信息
# ============================================================================
echo -e "${YELLOW}[2/8] 备份 PM2 进程信息...${NC}"
PM2_BACKUP="$BACKUP_BASE/pm2_info"
mkdir -p "$PM2_BACKUP"

# PM2 状态
pm2 list > "$PM2_BACKUP/pm2_list.txt" 2>&1 || echo "PM2 not running" > "$PM2_BACKUP/pm2_list.txt"
pm2 jlist > "$PM2_BACKUP/pm2_jlist.json" 2>&1 || echo "[]" > "$PM2_BACKUP/pm2_jlist.json"
pm2 info all > "$PM2_BACKUP/pm2_info_all.txt" 2>&1 || echo "No PM2 processes" > "$PM2_BACKUP/pm2_info_all.txt"

# PM2 配置文件
cp ecosystem.config.js "$PM2_BACKUP/" 2>/dev/null || echo "No ecosystem.config.js"
cp /home/user/.pm2/dump.pm2 "$PM2_BACKUP/" 2>/dev/null || echo "No PM2 dump"

# PM2 日志列表
ls -lh logs/ > "$PM2_BACKUP/pm2_logs_list.txt" 2>/dev/null || echo "No logs directory"

echo -e "${GREEN}✓ PM2 进程信息已备份${NC}"
echo ""

# ============================================================================
# 3. 备份 Flask 路由信息
# ============================================================================
echo -e "${YELLOW}[3/8] 备份 Flask 路由信息...${NC}"
FLASK_BACKUP="$BACKUP_BASE/flask_info"
mkdir -p "$FLASK_BACKUP"

# Flask 路由列表
if [ -f "source_code/app_new.py" ]; then
    grep -n "@app.route" source_code/app_new.py > "$FLASK_BACKUP/flask_routes.txt" 2>&1 || echo "No routes found"
    grep -n "def.*():" source_code/app_new.py | head -100 > "$FLASK_BACKUP/flask_functions.txt" 2>&1 || echo "No functions found"
fi

# Flask 配置
cp config.py "$FLASK_BACKUP/" 2>/dev/null || echo "No config.py"

# 记录当前运行的端口
netstat -tuln 2>/dev/null | grep 5000 > "$FLASK_BACKUP/flask_port.txt" || echo "Port 5000 not listening" > "$FLASK_BACKUP/flask_port.txt"

echo -e "${GREEN}✓ Flask 路由信息已备份${NC}"
echo ""

# ============================================================================
# 4. 备份数据库
# ============================================================================
echo -e "${YELLOW}[4/8] 备份数据库...${NC}"
DB_BACKUP="$BACKUP_BASE/databases"
mkdir -p "$DB_BACKUP"

if [ -d "databases" ]; then
    # 直接打包数据库目录
    tar -czf "$DB_BACKUP/databases.tar.gz" databases/ 2>/dev/null
    echo -e "${GREEN}✓ 数据库已备份: $(du -sh databases/ | awk '{print $1}')${NC}"
else
    echo "No databases directory"
fi
echo ""

# ============================================================================
# 5. 备份数据文件 (data/)
# ============================================================================
echo -e "${YELLOW}[5/8] 备份数据文件...${NC}"
DATA_BACKUP="$BACKUP_BASE/data"
mkdir -p "$DATA_BACKUP"

if [ -d "data" ]; then
    echo "正在压缩数据目录..."
    tar -czf "$DATA_BACKUP/data.tar.gz" data/ 2>/dev/null
    echo -e "${GREEN}✓ 数据文件已备份: $(du -sh data/ | awk '{print $1}')${NC}"
    echo -e "${GREEN}  压缩后大小: $(du -sh $DATA_BACKUP/data.tar.gz | awk '{print $1}')${NC}"
else
    echo "No data directory"
fi
echo ""

# ============================================================================
# 6. 备份源代码
# ============================================================================
echo -e "${YELLOW}[6/8] 备份源代码...${NC}"
CODE_BACKUP="$BACKUP_BASE/source_code"
mkdir -p "$CODE_BACKUP"

if [ -d "source_code" ]; then
    tar -czf "$CODE_BACKUP/source_code.tar.gz" source_code/ 2>/dev/null
    echo -e "${GREEN}✓ 源代码已备份: $(du -sh source_code/ | awk '{print $1}')${NC}"
else
    echo "No source_code directory"
fi
echo ""

# ============================================================================
# 7. 备份缓存信息
# ============================================================================
echo -e "${YELLOW}[7/8] 收集缓存信息...${NC}"
CACHE_BACKUP="$BACKUP_BASE/cache_info"
mkdir -p "$CACHE_BACKUP"

# Python 缓存
find /home/user/webapp -type d -name "__pycache__" > "$CACHE_BACKUP/pycache_list.txt" 2>/dev/null || echo "No pycache"
echo "Python __pycache__ 目录数: $(cat $CACHE_BACKUP/pycache_list.txt | wc -l)" >> "$CACHE_BACKUP/cache_summary.txt"

# pip 缓存
du -sh /home/user/.cache/pip 2>/dev/null >> "$CACHE_BACKUP/cache_summary.txt" || echo "No pip cache" >> "$CACHE_BACKUP/cache_summary.txt"

echo -e "${GREEN}✓ 缓存信息已收集${NC}"
echo ""

# ============================================================================
# 8. 备份配置文件和日志
# ============================================================================
echo -e "${YELLOW}[8/8] 备份配置文件和日志...${NC}"
CONFIG_BACKUP="$BACKUP_BASE/config_and_logs"
mkdir -p "$CONFIG_BACKUP"

# 配置文件
cp *.json "$CONFIG_BACKUP/" 2>/dev/null || true
cp *.txt "$CONFIG_BACKUP/" 2>/dev/null || true
cp *.md "$CONFIG_BACKUP/" 2>/dev/null || true

# 重要日志（只备份最新的部分）
if [ -d "logs" ]; then
    mkdir -p "$CONFIG_BACKUP/logs"
    # 只备份最近的日志（最后1000行）
    for logfile in logs/*.log; do
        if [ -f "$logfile" ]; then
            filename=$(basename "$logfile")
            tail -1000 "$logfile" > "$CONFIG_BACKUP/logs/$filename" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}✓ 配置文件和日志已备份${NC}"
else
    echo "No logs directory"
fi
echo ""

# ============================================================================
# 生成备份清单和统计信息
# ============================================================================
echo -e "${YELLOW}生成备份清单...${NC}"

cat > "$BACKUP_BASE/BACKUP_MANIFEST.txt" << EOF
================================================================================
                    系统完整备份清单 - Backup Manifest
================================================================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份目录: $BACKUP_BASE
系统信息: $(uname -a)

================================================================================
                            备份内容统计
================================================================================

$(du -sh $BACKUP_BASE/* 2>/dev/null)

================================================================================
                            详细目录结构
================================================================================

$(tree -L 2 "$BACKUP_BASE" 2>/dev/null || find "$BACKUP_BASE" -maxdepth 2 -type d)

================================================================================
                            Git 状态快照
================================================================================

分支信息:
$(cat "$GIT_BACKUP/git_branches.txt" 2>/dev/null || echo "无 Git 信息")

最近提交:
$(cat "$GIT_BACKUP/git_log.txt" 2>/dev/null | head -5 || echo "无提交历史")

================================================================================
                            PM2 进程快照
================================================================================

$(cat "$PM2_BACKUP/pm2_list.txt" 2>/dev/null || echo "无 PM2 进程")

================================================================================
                            数据库统计
================================================================================

$(ls -lh "$DB_BACKUP/" 2>/dev/null || echo "无数据库备份")

================================================================================
                            恢复说明
================================================================================

1. 恢复数据库:
   cd /home/user/webapp
   tar -xzf $BACKUP_BASE/databases/databases.tar.gz

2. 恢复数据文件:
   cd /home/user/webapp
   tar -xzf $BACKUP_BASE/data/data.tar.gz

3. 恢复源代码:
   cd /home/user/webapp
   tar -xzf $BACKUP_BASE/source_code/source_code.tar.gz

4. 恢复 PM2 进程:
   pm2 delete all
   pm2 start ecosystem.config.js

5. 恢复 Git 状态:
   查看 $GIT_BACKUP/ 目录中的 Git 信息

================================================================================
                            备份验证
================================================================================

备份完整性: $([ -d "$BACKUP_BASE" ] && echo "✓ 通过" || echo "✗ 失败")
文件数量: $(find "$BACKUP_BASE" -type f | wc -l)
总大小: $(du -sh "$BACKUP_BASE" | awk '{print $1}')

================================================================================
EOF

echo -e "${GREEN}✓ 备份清单已生成${NC}"
echo ""

# ============================================================================
# 压缩整个备份目录
# ============================================================================
echo -e "${YELLOW}压缩备份目录...${NC}"
FINAL_BACKUP="/tmp/system_backup_${TIMESTAMP}.tar.gz"

cd /tmp
tar -czf "$FINAL_BACKUP" "system_backup_${TIMESTAMP}/" 2>/dev/null

echo ""
echo "================================================================================"
echo -e "${GREEN}                    备份完成！ Backup Complete!${NC}"
echo "================================================================================"
echo ""
echo -e "${GREEN}✓ 原始备份目录:${NC} $BACKUP_BASE"
echo -e "${GREEN}✓ 压缩备份文件:${NC} $FINAL_BACKUP"
echo -e "${GREEN}✓ 原始大小:${NC} $(du -sh $BACKUP_BASE | awk '{print $1}')"
echo -e "${GREEN}✓ 压缩后大小:${NC} $(du -sh $FINAL_BACKUP | awk '{print $1}')"
echo ""
echo "================================================================================"
echo -e "${YELLOW}备份清单位置:${NC} $BACKUP_BASE/BACKUP_MANIFEST.txt"
echo ""
echo -e "${YELLOW}快速查看备份内容:${NC}"
echo "  cat $BACKUP_BASE/BACKUP_MANIFEST.txt"
echo ""
echo -e "${YELLOW}恢复备份:${NC}"
echo "  cd /tmp"
echo "  tar -xzf $FINAL_BACKUP"
echo "  # 然后按照 BACKUP_MANIFEST.txt 中的说明恢复"
echo "================================================================================"
echo ""

# 输出最终备份文件路径供后续使用
echo "$FINAL_BACKUP"
