#!/bin/bash
################################################################################
# 支撑压力线系统 - 快速部署脚本
# 用途: 在新服务器上快速部署支撑压力线系统
# 使用: bash quick_deploy_support_resistance.sh [backup_file]
################################################################################

set -e  # 遇到错误立即退出

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "🚀 支撑压力线系统 - 快速部署"
echo "================================================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 步骤1: 检查Python和依赖
echo "📋 步骤1: 检查Python环境"
echo "----------------------------------------"

if ! command -v python3 &> /dev/null; then
    print_error "Python3未安装"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
print_success "Python版本: $PYTHON_VERSION"

# 检查pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3未安装"
    exit 1
fi
print_success "pip3已安装"

echo ""

# 步骤2: 安装Python依赖
echo "📦 步骤2: 安装Python依赖"
echo "----------------------------------------"

REQUIRED_PACKAGES="pytz"

for package in $REQUIRED_PACKAGES; do
    if python3 -c "import $package" 2>/dev/null; then
        print_success "$package 已安装"
    else
        print_info "正在安装 $package..."
        pip3 install "$package" -q
        print_success "$package 安装完成"
    fi
done

echo ""

# 步骤3: 检查数据库
echo "🗄️  步骤3: 检查数据库"
echo "----------------------------------------"

if [ ! -f "crypto_data.db" ]; then
    print_error "数据库文件 crypto_data.db 不存在"
    print_info "请先复制数据库文件或执行数据恢复"
    exit 1
fi

# 检查表是否存在
TABLE_EXISTS=$(python3 << 'EOF'
import sqlite3
try:
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='support_resistance_snapshots'")
    exists = cursor.fetchone() is not None
    conn.close()
    print("yes" if exists else "no")
except:
    print("error")
EOF
)

if [ "$TABLE_EXISTS" = "yes" ]; then
    # 统计记录数
    RECORD_COUNT=$(python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM support_resistance_snapshots")
count = cursor.fetchone()[0]
conn.close()
print(count)
EOF
)
    print_success "数据库表存在，共 $RECORD_COUNT 条记录"
elif [ "$TABLE_EXISTS" = "no" ]; then
    print_info "表不存在，将自动创建"
else
    print_error "数据库检查失败"
    exit 1
fi

echo ""

# 步骤4: 数据恢复 (如果提供了备份文件)
if [ -n "$1" ]; then
    echo "📥 步骤4: 数据恢复"
    echo "----------------------------------------"
    
    BACKUP_FILE="$1"
    
    if [ ! -f "$BACKUP_FILE" ]; then
        print_error "备份文件不存在: $BACKUP_FILE"
        exit 1
    fi
    
    print_info "从备份恢复: $BACKUP_FILE"
    
    python3 backup_support_resistance_data.py restore --file "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        print_success "数据恢复完成"
    else
        print_error "数据恢复失败"
        exit 1
    fi
    
    echo ""
fi

# 步骤5: 检查采集器脚本
echo "🤖 步骤5: 检查采集器"
echo "----------------------------------------"

if [ ! -f "support_resistance_snapshot_collector.py" ]; then
    print_error "采集器脚本不存在: support_resistance_snapshot_collector.py"
    exit 1
fi

print_success "采集器脚本存在"

# 创建快照表 (如果不存在)
python3 << 'EOF'
import sqlite3
try:
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_resistance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_time TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            scenario_1_count INTEGER DEFAULT 0,
            scenario_2_count INTEGER DEFAULT 0,
            scenario_3_count INTEGER DEFAULT 0,
            scenario_4_count INTEGER DEFAULT 0,
            scenario_1_coins TEXT,
            scenario_2_coins TEXT,
            scenario_3_coins TEXT,
            scenario_4_coins TEXT,
            total_coins INTEGER DEFAULT 27,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_time ON support_resistance_snapshots(snapshot_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_date ON support_resistance_snapshots(snapshot_date)')
    
    conn.commit()
    conn.close()
    print("✅ 数据库表初始化完成")
except Exception as e:
    print(f"❌ 初始化失败: {e}")
    exit(1)
EOF

echo ""

# 步骤6: 停止旧进程 (如果存在)
echo "🛑 步骤6: 清理旧进程"
echo "----------------------------------------"

OLD_PIDS=$(pgrep -f "support_resistance_snapshot_collector.py")
if [ -n "$OLD_PIDS" ]; then
    print_info "发现旧进程，正在停止..."
    pkill -f "support_resistance_snapshot_collector.py"
    sleep 2
    print_success "旧进程已停止"
else
    print_info "没有发现旧进程"
fi

echo ""

# 步骤7: 启动采集器
echo "▶️  步骤7: 启动采集器"
echo "----------------------------------------"

nohup python3 support_resistance_snapshot_collector.py > support_resistance_snapshot.log 2>&1 &
COLLECTOR_PID=$!

sleep 2

# 验证进程是否启动
if ps -p $COLLECTOR_PID > /dev/null; then
    print_success "采集器启动成功 (PID: $COLLECTOR_PID)"
else
    print_error "采集器启动失败"
    print_info "请查看日志: tail -f support_resistance_snapshot.log"
    exit 1
fi

echo ""

# 步骤8: 验证数据更新
echo "✅ 步骤8: 验证系统状态"
echo "----------------------------------------"

sleep 5  # 等待采集器运行一段时间

python3 << 'EOF'
import sqlite3
from datetime import datetime, timedelta
import pytz

try:
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 检查最新快照
    cursor.execute("SELECT MAX(snapshot_time), COUNT(*) FROM support_resistance_snapshots")
    latest_time, total_count = cursor.fetchone()
    
    conn.close()
    
    if latest_time:
        print(f"✅ 最新快照时间: {latest_time}")
        print(f"✅ 总快照数: {total_count}")
        
        # 检查时间是否新鲜 (10分钟内)
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        latest = beijing_tz.localize(datetime.strptime(latest_time, '%Y-%m-%d %H:%M:%S'))
        diff_minutes = (now - latest).total_seconds() / 60
        
        if diff_minutes <= 10:
            print(f"✅ 数据正常 (距今 {diff_minutes:.1f} 分钟)")
        else:
            print(f"⚠️  数据较旧 (距今 {diff_minutes:.1f} 分钟)")
    else:
        print("⚠️  暂无快照数据")
        
except Exception as e:
    print(f"❌ 验证失败: {e}")
EOF

echo ""

# 步骤9: 显示部署信息
echo "================================================================================"
echo "🎉 部署完成！"
echo "================================================================================"
echo ""
echo "📊 系统信息:"
echo "  • 采集器PID: $COLLECTOR_PID"
echo "  • 日志文件: $(pwd)/support_resistance_snapshot.log"
echo "  • 数据库: $(pwd)/crypto_data.db"
echo "  • 备份目录: $(pwd)/backups/"
echo ""
echo "🔧 常用命令:"
echo "  • 查看日志: tail -f support_resistance_snapshot.log"
echo "  • 查看进程: ps aux | grep support_resistance_snapshot_collector"
echo "  • 停止采集器: pkill -f support_resistance_snapshot_collector.py"
echo "  • 重启采集器: bash $0"
echo "  • 数据备份: python3 backup_support_resistance_data.py backup --days 30"
echo "  • 列出备份: python3 backup_support_resistance_data.py list"
echo ""
echo "🌐 API接口:"
echo "  • 最新数据: http://localhost:5000/api/support-resistance/latest"
echo "  • 历史数据: http://localhost:5000/api/support-resistance/snapshots?all=true"
echo "  • 指定日期: http://localhost:5000/api/support-resistance/snapshots?date=2025-12-14"
echo ""
echo "📋 下一步:"
echo "  1. 确认Flask应用正在运行 (python3 app_new.py)"
echo "  2. 访问支撑压力线页面查看曲线图"
echo "  3. 设置定时备份 (crontab -e)"
echo ""
echo "================================================================================"

exit 0
