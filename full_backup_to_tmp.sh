#!/bin/bash
# 完整备份脚本 - 包含所有23个子系统
# 版本: 3.0 Final
# 日期: 2026-01-12
# 目标: 备份到/tmp，分割成<1.3GB的文件

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/complete_system_backup_${TIMESTAMP}"
WEBAPP_DIR="/home/user/webapp"

echo "=============================================================================="
echo " 加密货币分析系统 - 完整备份（23个子系统）"
echo "=============================================================================="
echo ""
echo "备份时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "源目录: ${WEBAPP_DIR}"
echo "备份目录: ${BACKUP_DIR}"
echo ""
echo "=============================================================================="
echo ""

# 创建备份目录结构
echo "[步骤 1/15] 创建备份目录结构..."
mkdir -p "${BACKUP_DIR}"/{databases,source_code,configs,logs,docs,git,pm2,dependencies,system_info}
echo "  ✓ 目录结构创建完成"
echo ""

# 备份数据库
echo "[步骤 2/15] 备份数据库文件（13个）..."
if [ -d "${WEBAPP_DIR}/databases" ]; then
    cp -v "${WEBAPP_DIR}/databases/"*.db "${BACKUP_DIR}/databases/" 2>/dev/null || echo "  注意: 部分数据库不存在"
    DB_SIZE=$(du -sh "${BACKUP_DIR}/databases" | cut -f1)
    DB_COUNT=$(ls "${BACKUP_DIR}/databases/"*.db 2>/dev/null | wc -l)
    echo "  ✓ 已备份 ${DB_COUNT} 个数据库，总大小: ${DB_SIZE}"
else
    echo "  ✗ 数据库目录不存在"
fi
echo ""

# 备份源代码
echo "[步骤 3/15] 备份源代码..."
if [ -d "${WEBAPP_DIR}/source_code" ]; then
    cp -r "${WEBAPP_DIR}/source_code" "${BACKUP_DIR}/"
    PY_COUNT=$(find "${BACKUP_DIR}/source_code" -name "*.py" | wc -l)
    HTML_COUNT=$(find "${BACKUP_DIR}/source_code" -name "*.html" | wc -l)
    echo "  ✓ Python文件: ${PY_COUNT} 个"
    echo "  ✓ HTML模板: ${HTML_COUNT} 个"
else
    echo "  ✗ 源代码目录不存在"
fi
echo ""

# 备份根目录脚本
echo "[步骤 4/15] 备份根目录脚本..."
cp "${WEBAPP_DIR}/"*.py "${BACKUP_DIR}/" 2>/dev/null || echo "  注意: 部分Python脚本不存在"
cp "${WEBAPP_DIR}/"*.sh "${BACKUP_DIR}/" 2>/dev/null || echo "  注意: 部分Shell脚本不存在"
SCRIPT_COUNT=$(ls "${BACKUP_DIR}/"*.py "${BACKUP_DIR}/"*.sh 2>/dev/null | wc -l)
echo "  ✓ 已备份 ${SCRIPT_COUNT} 个脚本"
echo ""

# 备份配置文件
echo "[步骤 5/15] 备份配置文件..."
cp "${WEBAPP_DIR}/"*.json "${BACKUP_DIR}/configs/" 2>/dev/null || echo "  注意: 部分JSON配置不存在"
cp "${WEBAPP_DIR}/"*.conf "${BACKUP_DIR}/configs/" 2>/dev/null || echo "  注意: 部分conf配置不存在"
cp "${WEBAPP_DIR}/"*.yaml "${BACKUP_DIR}/configs/" 2>/dev/null || echo "  注意: 部分YAML配置不存在"
cp "${WEBAPP_DIR}/"*.yml "${BACKUP_DIR}/configs/" 2>/dev/null || echo "  注意: 部分YML配置不存在"
CONFIG_COUNT=$(ls "${BACKUP_DIR}/configs/" 2>/dev/null | wc -l)
echo "  ✓ 已备份 ${CONFIG_COUNT} 个配置文件"
echo ""

# 备份日志
echo "[步骤 6/15] 备份重要日志..."
if [ -d "${WEBAPP_DIR}/logs" ]; then
    # 只备份最近的日志（每个文件最后1000行）
    mkdir -p "${BACKUP_DIR}/logs"
    for log in $(find "${WEBAPP_DIR}/logs" -name "*.log" 2>/dev/null); do
        logname=$(basename "$log")
        tail -1000 "$log" > "${BACKUP_DIR}/logs/${logname}" 2>/dev/null || true
    done
fi
# 备份根目录日志
for log in "${WEBAPP_DIR}"/*.log; do
    if [ -f "$log" ]; then
        logname=$(basename "$log")
        tail -1000 "$log" > "${BACKUP_DIR}/logs/${logname}" 2>/dev/null || true
    fi
done
LOG_COUNT=$(find "${BACKUP_DIR}/logs" -name "*.log" 2>/dev/null | wc -l)
echo "  ✓ 已备份 ${LOG_COUNT} 个日志文件（保留最后1000行）"
echo ""

# 备份文档
echo "[步骤 7/15] 备份文档..."
cp "${WEBAPP_DIR}/"*.md "${BACKUP_DIR}/docs/" 2>/dev/null || echo "  注意: 部分Markdown文档不存在"
cp "${WEBAPP_DIR}/"*.txt "${BACKUP_DIR}/docs/" 2>/dev/null || echo "  注意: 部分TXT文档不存在"
DOC_COUNT=$(ls "${BACKUP_DIR}/docs/" 2>/dev/null | wc -l)
echo "  ✓ 已备份 ${DOC_COUNT} 个文档"
echo ""

# 备份Git（完整）
echo "[步骤 8/15] 备份Git仓库（完整）..."
if [ -d "${WEBAPP_DIR}/.git" ]; then
    echo "  正在复制.git目录（这可能需要几分钟）..."
    cp -r "${WEBAPP_DIR}/.git" "${BACKUP_DIR}/git/"
    
    # 生成Git信息
    cd "${WEBAPP_DIR}"
    git log --oneline --all --graph --decorate > "${BACKUP_DIR}/git/git_history_full.txt" 2>/dev/null || true
    git log --oneline -100 > "${BACKUP_DIR}/git/git_history_recent.txt" 2>/dev/null || true
    git branch -a > "${BACKUP_DIR}/git/git_branches.txt" 2>/dev/null || true
    git remote -v > "${BACKUP_DIR}/git/git_remotes.txt" 2>/dev/null || true
    git status > "${BACKUP_DIR}/git/git_status.txt" 2>/dev/null || true
    git diff --stat > "${BACKUP_DIR}/git/git_diff.txt" 2>/dev/null || true
    cd - > /dev/null
    
    GIT_SIZE=$(du -sh "${BACKUP_DIR}/git" | cut -f1)
    echo "  ✓ Git仓库备份完成，大小: ${GIT_SIZE}"
else
    echo "  ✗ Git仓库不存在"
fi
echo ""

# 备份PM2配置
echo "[步骤 9/15] 备份PM2配置..."
if command -v pm2 &> /dev/null; then
    pm2 list > "${BACKUP_DIR}/pm2/pm2_list.txt" 2>&1
    pm2 prettylist > "${BACKUP_DIR}/pm2/pm2_detail.txt" 2>&1 || true
    pm2 dump
    cp ~/.pm2/dump.pm2 "${BACKUP_DIR}/pm2/" 2>/dev/null || echo "  注意: PM2 dump文件不存在"
    cp ~/.pm2/module_conf.json "${BACKUP_DIR}/pm2/" 2>/dev/null || echo "  注意: PM2 module_conf不存在"
    
    # 备份PM2日志（最近1000行）
    mkdir -p "${BACKUP_DIR}/pm2/logs"
    for log in ~/.pm2/logs/*.log; do
        if [ -f "$log" ]; then
            logname=$(basename "$log")
            tail -1000 "$log" > "${BACKUP_DIR}/pm2/logs/${logname}" 2>/dev/null || true
        fi
    done
    
    PM2_LOG_COUNT=$(ls "${BACKUP_DIR}/pm2/logs/" 2>/dev/null | wc -l)
    echo "  ✓ PM2配置和日志已备份（${PM2_LOG_COUNT} 个日志）"
else
    echo "  ✗ PM2未安装"
fi
echo ""

# 备份Python依赖
echo "[步骤 10/15] 备份Python依赖..."
if command -v pip3 &> /dev/null; then
    pip3 list > "${BACKUP_DIR}/dependencies/pip_list.txt"
    pip3 freeze > "${BACKUP_DIR}/dependencies/requirements.txt"
    python3 --version > "${BACKUP_DIR}/dependencies/python_version.txt" 2>&1
    echo "  ✓ Python依赖已备份"
else
    echo "  ✗ pip3未安装"
fi
echo ""

# 备份Node.js依赖
echo "[步骤 11/15] 备份Node.js依赖..."
if [ -f "${WEBAPP_DIR}/package.json" ]; then
    cp "${WEBAPP_DIR}/package.json" "${BACKUP_DIR}/dependencies/"
    cp "${WEBAPP_DIR}/package-lock.json" "${BACKUP_DIR}/dependencies/" 2>/dev/null || true
fi
if command -v npm &> /dev/null; then
    npm list -g --depth=0 > "${BACKUP_DIR}/dependencies/npm_global.txt" 2>/dev/null || true
    node --version > "${BACKUP_DIR}/dependencies/node_version.txt" 2>&1
    npm --version > "${BACKUP_DIR}/dependencies/npm_version.txt" 2>&1
    echo "  ✓ Node.js依赖已备份"
fi
echo ""

# 生成系统信息
echo "[步骤 12/15] 生成系统信息..."
cat > "${BACKUP_DIR}/system_info/SYSTEM_INFO.txt" << SYSEOF
============================================================================
系统信息
============================================================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份类型: 完整备份（包含Git完整历史）
系统信息: $(uname -a)
主机名: $(hostname)
Python版本: $(python3 --version 2>&1)
Node.js版本: $(node --version 2>&1 || echo "未安装")
PM2版本: $(pm2 --version 2>&1 || echo "未安装")
工作目录: ${WEBAPP_DIR}
备份目录: ${BACKUP_DIR}

磁盘使用:
$(df -h /)

内存使用:
$(free -h)

SYSEOF
echo "  ✓ 系统信息已生成"
echo ""

# 生成数据库结构
echo "[步骤 13/15] 分析数据库结构..."
python3 << 'PYEOF'
import sqlite3
import os
import json
import sys

db_dir = "/tmp/complete_system_backup_${TIMESTAMP}/databases"
output_file = "/tmp/complete_system_backup_${TIMESTAMP}/system_info/DATABASE_STRUCTURE.json"

db_info = {}
total_tables = 0
total_records = 0

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
                        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                        count = cursor.fetchone()[0]
                        cursor.execute(f"PRAGMA table_info(`{table}`)")
                        columns = [row[1] for row in cursor.fetchall()]
                        table_info[table] = {
                            "row_count": count,
                            "columns": columns,
                            "column_count": len(columns)
                        }
                        total_records += count
                    except Exception as e:
                        table_info[table] = {"error": str(e)}
                
                db_info[db_file] = {
                    "table_count": len(tables),
                    "table_list": tables,
                    "table_details": table_info
                }
                total_tables += len(tables)
                conn.close()
                print(f"  ✓ 分析完成: {db_file} ({len(tables)} 个表)")
            except Exception as e:
                db_info[db_file] = {"error": str(e)}
                print(f"  ✗ 错误: {db_file} - {str(e)}")

# 添加汇总信息
db_info["_summary"] = {
    "total_databases": len([k for k in db_info.keys() if not k.startswith("_")]),
    "total_tables": total_tables,
    "total_records": total_records
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(db_info, f, indent=2, ensure_ascii=False)

print(f"\n  ✓ 已分析 {len(db_info)-1} 个数据库，{total_tables} 个表，约{total_records:,}条记录")
print(f"  ✓ 详情见: DATABASE_STRUCTURE.json")
PYEOF
echo ""

# 生成文件清单
echo "[步骤 14/15] 生成文件清单..."
find "${BACKUP_DIR}" -type f > "${BACKUP_DIR}/system_info/all_files.txt"
find "${BACKUP_DIR}" -name "*.py" > "${BACKUP_DIR}/system_info/python_files.txt"
find "${BACKUP_DIR}" -name "*.html" > "${BACKUP_DIR}/system_info/html_files.txt"
find "${BACKUP_DIR}" -name "*.db" > "${BACKUP_DIR}/system_info/database_files.txt"
find "${BACKUP_DIR}" -name "*.json" > "${BACKUP_DIR}/system_info/json_files.txt"

TOTAL_FILES=$(wc -l < "${BACKUP_DIR}/system_info/all_files.txt")
echo "  ✓ 已生成文件清单，总文件数: ${TOTAL_FILES}"
echo ""

# 计算备份大小
echo "[步骤 15/15] 计算备份大小..."
BACKUP_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
echo "BACKUP_SIZE=${BACKUP_SIZE}" > "${BACKUP_DIR}/BACKUP_SIZE.txt"
echo "  ✓ 备份总大小: ${BACKUP_SIZE}"
echo ""

# 生成备份清单
cat > "${BACKUP_DIR}/BACKUP_MANIFEST.txt" << MANIFEST
============================================================================
加密货币分析系统 - 完整备份清单
============================================================================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份目录: ${BACKUP_DIR}
总大小: ${BACKUP_SIZE}
总文件数: ${TOTAL_FILES}

目录结构:
$(tree -L 2 -d "${BACKUP_DIR}" 2>/dev/null || find "${BACKUP_DIR}" -maxdepth 2 -type d)

数据库文件（${DB_COUNT}个）:
$(ls -lh "${BACKUP_DIR}/databases/"*.db 2>/dev/null | awk '{print $9, $5}' | sed 's|.*/||')

源代码统计:
- Python文件: ${PY_COUNT} 个
- HTML模板: ${HTML_COUNT} 个
- Shell脚本: $(ls "${BACKUP_DIR}/"*.sh 2>/dev/null | wc -l) 个

配置文件: ${CONFIG_COUNT} 个
文档文件: ${DOC_COUNT} 个
日志文件: ${LOG_COUNT} 个

Git信息:
$(cat "${BACKUP_DIR}/git/git_history_recent.txt" 2>/dev/null | head -5 || echo "Git信息不可用")

PM2进程:
$(cat "${BACKUP_DIR}/pm2/pm2_list.txt" 2>/dev/null | head -10 || echo "PM2信息不可用")

============================================================================
备份完整性: $([ -d "${BACKUP_DIR}/databases" ] && echo "✓" || echo "✗") 数据库
            $([ -d "${BACKUP_DIR}/source_code" ] && echo "✓" || echo "✗") 源代码
            $([ -d "${BACKUP_DIR}/git" ] && echo "✓" || echo "✗") Git仓库
            $([ -d "${BACKUP_DIR}/pm2" ] && echo "✓" || echo "✗") PM2配置
            $([ -f "${BACKUP_DIR}/dependencies/requirements.txt" ] && echo "✓" || echo "✗") Python依赖
============================================================================
MANIFEST

echo "=============================================================================="
echo " 备份完成！"
echo "=============================================================================="
echo ""
echo "备份位置: ${BACKUP_DIR}"
echo "总大小: ${BACKUP_SIZE}"
echo "总文件数: ${TOTAL_FILES}"
echo ""
echo "下一步: 压缩并分割备份"
echo "命令: cd /tmp && tar -czf - complete_system_backup_${TIMESTAMP}/ | split -b 1300M - complete_backup_${TIMESTAMP}.tar.gz."
echo ""
echo "=============================================================================="
