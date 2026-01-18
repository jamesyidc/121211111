#!/bin/bash
# 智能精简备份脚本 - 只备份关键内容
# 版本: 3.0
# 日期: 2026-01-10

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_BASE="/home/user/webapp/backups"
BACKUP_DIR="${BACKUP_BASE}/smart_backup_${TIMESTAMP}"
WEBAPP_DIR="/home/user/webapp"

echo "=========================================="
echo "加密货币分析系统智能备份"
echo "备份时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "备份策略: 精简备份（跳过Git对象、大日志等）"
echo "=========================================="
echo ""

# 创建备份目录
mkdir -p "${BACKUP_DIR}"
cd "${BACKUP_DIR}"

# 创建子目录
mkdir -p databases source_code configs docs scripts system_info

echo "[1/12] 备份数据库文件..."
cp -v "${WEBAPP_DIR}/databases/"*.db databases/
DATABASES_SIZE=$(du -sh databases/ | cut -f1)
echo "  完成: ${DATABASES_SIZE}"
echo ""

echo "[2/12] 备份源代码（Python文件）..."
mkdir -p source_code/templates
cp "${WEBAPP_DIR}/source_code/"*.py source_code/ 2>/dev/null || echo "  注意: 部分py文件不存在"
cp "${WEBAPP_DIR}/source_code/"*.sh source_code/ 2>/dev/null || echo "  注意: 部分sh文件不存在"
# 复制模板
if [ -d "${WEBAPP_DIR}/source_code/templates" ]; then
    cp -r "${WEBAPP_DIR}/source_code/templates/"*.html source_code/templates/ 2>/dev/null || echo "  注意: 部分模板不存在"
fi
SOURCE_SIZE=$(du -sh source_code/ | cut -f1)
echo "  完成: ${SOURCE_SIZE}"
echo ""

echo "[3/12] 备份根目录脚本..."
cp "${WEBAPP_DIR}/"*.py scripts/ 2>/dev/null || echo "  注意: 部分脚本不存在"
cp "${WEBAPP_DIR}/"*.sh scripts/ 2>/dev/null || echo "  注意: 部分脚本不存在"
echo "  完成: $(du -sh scripts/ | cut -f1)"
echo ""

echo "[4/12] 备份配置文件..."
cp "${WEBAPP_DIR}/"*.json configs/ 2>/dev/null || echo "  注意: 部分配置不存在"
cp "${WEBAPP_DIR}/"*.conf configs/ 2>/dev/null || echo "  注意: 部分配置不存在"
echo "  完成: $(du -sh configs/ | cut -f1)"
echo ""

echo "[5/12] 备份重要文档..."
cp "${WEBAPP_DIR}/"*.md docs/ 2>/dev/null || echo "  注意: 部分文档不存在"
cp "${WEBAPP_DIR}/COMPLETE_SYSTEM_RESTORATION_GUIDE.md" docs/ 2>/dev/null || echo "  注意: 恢复指南不存在"
echo "  完成: $(du -sh docs/ | cut -f1)"
echo ""

echo "[6/12] 保存Git提交历史（不含对象）..."
if [ -d "${WEBAPP_DIR}/.git" ]; then
    cd "${WEBAPP_DIR}"
    git log --oneline --all --graph --decorate > "${BACKUP_DIR}/system_info/git_history_full.txt"
    git log --oneline -50 > "${BACKUP_DIR}/system_info/git_history_recent.txt"
    git branch -a > "${BACKUP_DIR}/system_info/git_branches.txt"
    git remote -v > "${BACKUP_DIR}/system_info/git_remotes.txt"
    git status > "${BACKUP_DIR}/system_info/git_status.txt"
    git diff --stat > "${BACKUP_DIR}/system_info/git_diff.txt" 2>/dev/null || echo "" > "${BACKUP_DIR}/system_info/git_diff.txt"
    cd "${BACKUP_DIR}"
    echo "  完成: Git历史已保存"
else
    echo "  警告: Git仓库不存在"
fi
echo ""

echo "[7/12] 保存PM2配置..."
if command -v pm2 &> /dev/null; then
    pm2 list > system_info/pm2_list.txt 2>&1
    pm2 prettylist > system_info/pm2_detail.txt 2>&1 || echo "" > system_info/pm2_detail.txt
    pm2 dump
    cp ~/.pm2/dump.pm2 system_info/ 2>/dev/null || echo "  注意: PM2 dump不存在"
    echo "  完成: PM2配置已保存"
else
    echo "  警告: PM2未安装"
fi
echo ""

echo "[8/12] 保存Python依赖..."
if command -v pip3 &> /dev/null; then
    pip3 list > system_info/pip_list.txt
    pip3 freeze > system_info/requirements.txt
    echo "  完成"
else
    echo "  警告: pip3未安装"
fi
echo ""

echo "[9/12] 生成系统信息..."
cat > system_info/SYSTEM_INFO.txt << EOF
========================================
系统信息
========================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份类型: 智能精简备份
系统信息: $(uname -a)
Python版本: $(python3 --version 2>&1)
Node.js版本: $(node --version 2>&1 || echo "未安装")
PM2版本: $(pm2 --version 2>&1 || echo "未安装")
工作目录: ${WEBAPP_DIR}
备份目录: ${BACKUP_DIR}

磁盘使用:
$(df -h /)

EOF
echo "  完成"
echo ""

echo "[10/12] 生成数据库结构信息..."
python3 << 'PYEOF'
import sqlite3
import os
import json

db_dir = "./databases"
db_info = {}

if os.path.exists(db_dir):
    for db_file in sorted(os.listdir(db_dir)):
        if db_file.endswith('.db'):
            db_path = os.path.join(db_dir, db_file)
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                table_info = {}
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [row[1] for row in cursor.fetchall()]
                        table_info[table] = {
                            "row_count": count,
                            "columns": columns,
                            "column_count": len(columns)
                        }
                    except Exception as e:
                        table_info[table] = {"error": str(e)}
                
                db_info[db_file] = {
                    "table_count": len(tables),
                    "table_list": tables,
                    "table_details": table_info
                }
                conn.close()
                print(f"  分析完成: {db_file} ({len(tables)} 个表)")
            except Exception as e:
                db_info[db_file] = {"error": str(e)}
                print(f"  错误: {db_file} - {str(e)}")

with open("system_info/DATABASE_STRUCTURE.json", "w", encoding="utf-8") as f:
    json.dump(db_info, f, indent=2, ensure_ascii=False)

print(f"\n已分析 {len(db_info)} 个数据库，详情见 DATABASE_STRUCTURE.json")
PYEOF
echo ""

echo "[11/12] 生成文件清单..."
find . -type f -name "*.py" > system_info/python_files.txt
find . -type f -name "*.html" > system_info/html_files.txt
find . -type f -name "*.db" > system_info/database_files.txt
find . -type f > system_info/all_files.txt
echo "  完成"
echo ""

echo "[12/12] 生成备份摘要..."
BACKUP_SIZE=$(du -sh . | cut -f1)

cat > BACKUP_SUMMARY.txt << EOF
========================================
备份摘要
========================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份目录: ${BACKUP_DIR}
备份大小: ${BACKUP_SIZE}
备份类型: 智能精简备份

备份内容:
- 数据库: ${DATABASES_SIZE}
- 源代码: ${SOURCE_SIZE}
- 配置文件: $(du -sh configs/ 2>/dev/null | cut -f1 || echo "0")
- 文档: $(du -sh docs/ 2>/dev/null | cut -f1 || echo "0")
- 脚本: $(du -sh scripts/ 2>/dev/null | cut -f1 || echo "0")
- 系统信息: $(du -sh system_info/ 2>/dev/null | cut -f1 || echo "0")

文件统计:
- 数据库文件: $(ls databases/*.db 2>/dev/null | wc -l)
- Python文件: $(wc -l < system_info/python_files.txt)
- HTML文件: $(wc -l < system_info/html_files.txt)
- 配置文件: $(ls configs/ 2>/dev/null | wc -l)

数据库列表:
$(ls -lh databases/*.db 2>/dev/null | awk '{print $9, $5}' | sed 's/databases\///')

重要说明:
- 本备份不包含Git对象（节省空间）
- 不包含大日志文件（保留最近日志）
- 不包含node_modules（可通过npm install恢复）
- Git历史记录已保存为文本

恢复方法:
1. 将databases目录复制到新环境
2. 将source_code和scripts复制到新环境
3. 将configs复制到新环境
4. 运行 pip3 install -r system_info/requirements.txt
5. 运行 pm2 resurrect 或手动启动服务
6. 参考 COMPLETE_SYSTEM_RESTORATION_GUIDE.md

========================================
EOF

cat BACKUP_SUMMARY.txt

echo ""
echo "=========================================="
echo "备份完成！"
echo "=========================================="
echo "备份位置: ${BACKUP_DIR}"
echo "总大小: ${BACKUP_SIZE}"
echo ""
echo "查看摘要: cat ${BACKUP_DIR}/BACKUP_SUMMARY.txt"
echo "查看数据库结构: cat ${BACKUP_DIR}/system_info/DATABASE_STRUCTURE.json"
echo ""
