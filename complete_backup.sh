#!/bin/bash
# 加密货币分析系统完整备份脚本
# 版本: 2.0
# 日期: 2026-01-10

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_BASE="/home/user/webapp/backups"
BACKUP_DIR="${BACKUP_BASE}/complete_backup_${TIMESTAMP}"
WEBAPP_DIR="/home/user/webapp"

echo "=========================================="
echo "加密货币分析系统完整备份"
echo "备份时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 创建备份目录
mkdir -p "${BACKUP_DIR}"
cd "${BACKUP_DIR}"

# 创建子目录结构
mkdir -p databases source_code configs logs docs git pm2 dependencies pages

echo "[1/15] 备份数据库文件..."
cp -v "${WEBAPP_DIR}/databases/"*.db databases/ 2>/dev/null || echo "  注意: 部分数据库文件不存在"
echo "  完成: $(du -sh databases/ | cut -f1)"
echo ""

echo "[2/15] 备份源代码..."
cp -r "${WEBAPP_DIR}/source_code/"* source_code/ 2>/dev/null || echo "  注意: 部分源代码不存在"
echo "  完成: $(du -sh source_code/ | cut -f1)"
echo ""

echo "[3/15] 备份根目录Python脚本..."
cp "${WEBAPP_DIR}/"*.py . 2>/dev/null || echo "  注意: 部分脚本不存在"
echo ""

echo "[4/15] 备份配置文件..."
cp "${WEBAPP_DIR}/"*.json configs/ 2>/dev/null || echo "  注意: 部分配置不存在"
cp "${WEBAPP_DIR}/"*.conf configs/ 2>/dev/null || echo "  注意: 部分配置不存在"
echo "  完成: $(du -sh configs/ | cut -f1)"
echo ""

echo "[5/15] 备份日志文件..."
cp "${WEBAPP_DIR}/"*.log logs/ 2>/dev/null || echo "  注意: 部分日志不存在"
cp "${WEBAPP_DIR}/source_code/"*.log logs/ 2>/dev/null || echo "  注意: 部分日志不存在"
echo "  完成: $(du -sh logs/ | cut -f1)"
echo ""

echo "[6/15] 备份文档..."
cp "${WEBAPP_DIR}/"*.md docs/ 2>/dev/null || echo "  注意: 部分文档不存在"
cp "${WEBAPP_DIR}/"*.txt docs/ 2>/dev/null || echo "  注意: 部分文档不存在"
echo "  完成: $(du -sh docs/ | cut -f1)"
echo ""

echo "[7/15] 备份Git仓库..."
if [ -d "${WEBAPP_DIR}/.git" ]; then
    cp -r "${WEBAPP_DIR}/.git" git/
    cd git
    git log --oneline -20 > git_history.txt
    git branch -a > git_branches.txt
    git remote -v > git_remotes.txt
    git status > git_status.txt
    cd ..
    echo "  完成: $(du -sh git/ | cut -f1)"
else
    echo "  警告: Git仓库不存在"
fi
echo ""

echo "[8/15] 备份PM2配置..."
if command -v pm2 &> /dev/null; then
    pm2 list > pm2/pm2_list.txt
    pm2 dump
    cp ~/.pm2/dump.pm2 pm2/ 2>/dev/null || echo "  注意: PM2 dump不存在"
    pm2 ecosystem > pm2/ecosystem.config.js 2>/dev/null || echo "  注意: 无ecosystem文件"
    echo "  完成"
else
    echo "  警告: PM2未安装"
fi
echo ""

echo "[9/15] 备份Python依赖..."
if command -v pip3 &> /dev/null; then
    pip3 list > dependencies/pip_list.txt
    pip3 freeze > dependencies/requirements.txt
    echo "  完成"
else
    echo "  警告: pip3未安装"
fi
echo ""

echo "[10/15] 备份Node.js依赖..."
if [ -f "${WEBAPP_DIR}/package.json" ]; then
    cp "${WEBAPP_DIR}/package.json" dependencies/
    cp "${WEBAPP_DIR}/package-lock.json" dependencies/ 2>/dev/null || echo "  注意: package-lock.json不存在"
fi
if command -v npm &> /dev/null; then
    npm list -g --depth=0 > dependencies/npm_global.txt 2>/dev/null || echo "  注意: npm list失败"
fi
echo ""

echo "[11/15] 生成系统信息..."
cat > SYSTEM_INFO.txt << EOF
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
系统信息: $(uname -a)
Python版本: $(python3 --version)
Node.js版本: $(node --version 2>/dev/null || echo "未安装")
PM2版本: $(pm2 --version 2>/dev/null || echo "未安装")
工作目录: ${WEBAPP_DIR}
备份目录: ${BACKUP_DIR}
EOF
echo "  完成"
echo ""

echo "[12/15] 生成文件清单..."
find . -type f > FILE_LIST.txt
echo "  完成"
echo ""

echo "[13/15] 生成数据库结构信息..."
python3 << 'PYEOF'
import sqlite3
import os
import json

db_dir = "./databases"
db_info = {}

if os.path.exists(db_dir):
    for db_file in os.listdir(db_dir):
        if db_file.endswith('.db'):
            db_path = os.path.join(db_dir, db_file)
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                table_info = {}
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]
                    table_info[table] = {
                        "row_count": count,
                        "columns": columns
                    }
                
                db_info[db_file] = {
                    "tables": len(tables),
                    "table_list": tables,
                    "table_details": table_info
                }
                conn.close()
            except Exception as e:
                db_info[db_file] = {"error": str(e)}

with open("DATABASE_STRUCTURE.json", "w", encoding="utf-8") as f:
    json.dump(db_info, f, indent=2, ensure_ascii=False)

print(f"已分析 {len(db_info)} 个数据库")
PYEOF
echo "  完成"
echo ""

echo "[14/15] 计算备份大小..."
BACKUP_SIZE=$(du -sh . | cut -f1)
echo "BACKUP_SIZE=${BACKUP_SIZE}" > BACKUP_SIZE.txt
echo "  备份总大小: ${BACKUP_SIZE}"
echo ""

echo "[15/15] 生成备份校验信息..."
find . -type f -exec md5sum {} \; > CHECKSUMS.md5 2>/dev/null || echo "  注意: 部分文件校验失败"
echo "  完成"
echo ""

# 创建备份清单摘要
cat > BACKUP_MANIFEST.txt << EOF
========================================
加密货币分析系统备份清单
========================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份目录: ${BACKUP_DIR}
总大小: ${BACKUP_SIZE}

目录结构:
$(tree -L 2 -d . 2>/dev/null || find . -maxdepth 2 -type d)

数据库文件:
$(ls -lh databases/*.db 2>/dev/null | awk '{print $9, $5}' || echo "无数据库文件")

重要文件数量:
- Python源文件: $(find source_code -name "*.py" | wc -l)
- HTML模板: $(find source_code/templates -name "*.html" 2>/dev/null | wc -l)
- 配置文件: $(ls configs/ 2>/dev/null | wc -l)
- 日志文件: $(ls logs/ 2>/dev/null | wc -l)
- 文档文件: $(ls docs/ 2>/dev/null | wc -l)

Git信息:
$(cat git/git_history.txt 2>/dev/null | head -5 || echo "无Git信息")

PM2进程:
$(cat pm2/pm2_list.txt 2>/dev/null || echo "无PM2信息")

========================================
EOF

echo "=========================================="
echo "备份完成！"
echo "备份位置: ${BACKUP_DIR}"
echo "总大小: ${BACKUP_SIZE}"
echo "=========================================="
echo ""
echo "下一步: 创建压缩包（可选）"
echo "命令: cd ${BACKUP_BASE} && tar -czf complete_backup_${TIMESTAMP}.tar.gz complete_backup_${TIMESTAMP}/"
echo ""
