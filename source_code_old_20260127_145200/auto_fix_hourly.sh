#!/bin/bash
# 每小时自动修复脚本
# 功能：修复沙箱、重启服务、清理硬盘

LOG_FILE="/home/user/webapp/auto_fix.log"
MAX_LOG_SIZE=10485760  # 10MB

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查并轮转日志文件
check_log_size() {
    if [ -f "$LOG_FILE" ]; then
        SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
        if [ "$SIZE" -gt "$MAX_LOG_SIZE" ]; then
            mv "$LOG_FILE" "$LOG_FILE.old"
            log "日志文件已轮转"
        fi
    fi
}

log "=========================================="
log "🔧 开始执行每小时自动修复任务"
log "=========================================="

# 1. 清理硬盘空间
log "📦 1. 清理硬盘空间..."

# 清理临时文件
log "  - 清理 /tmp 目录..."
find /tmp -type f -atime +7 -delete 2>/dev/null || true
find /tmp -type d -empty -delete 2>/dev/null || true

# 清理日志文件（保留最近7天）
log "  - 清理旧日志文件..."
find /home/user/webapp -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
find /home/user/webapp -name "*.log.*" -type f -delete 2>/dev/null || true

# 清理Python缓存
log "  - 清理Python缓存..."
find /home/user/webapp -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find /home/user/webapp -type f -name "*.pyc" -delete 2>/dev/null || true
find /home/user/webapp -type f -name "*.pyo" -delete 2>/dev/null || true

# 清理npm缓存
log "  - 清理npm缓存..."
npm cache clean --force 2>/dev/null || true

# 清理apt缓存
log "  - 清理apt缓存..."
apt-get clean 2>/dev/null || true

# 显示磁盘使用情况
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}')
log "  ✅ 磁盘清理完成，当前使用率: $DISK_USAGE"

# 2. 检查并修复3000端口服务
log "📡 2. 检查3000端口服务..."
PORT_3000=$(lsof -ti:3000 2>/dev/null)
if [ -z "$PORT_3000" ]; then
    log "  ⚠️  3000端口无服务运行"
    # 尝试启动服务（如果有启动脚本）
    if [ -f "/home/user/webapp/start_3000.sh" ]; then
        log "  🔄 启动3000端口服务..."
        bash /home/user/webapp/start_3000.sh &
        sleep 3
        if lsof -ti:3000 >/dev/null 2>&1; then
            log "  ✅ 3000端口服务启动成功"
        else
            log "  ❌ 3000端口服务启动失败"
        fi
    fi
else
    log "  ✅ 3000端口服务运行正常 (PID: $PORT_3000)"
    # 检查进程健康状态
    if ! kill -0 $PORT_3000 2>/dev/null; then
        log "  ⚠️  进程异常，尝试重启..."
        kill -9 $PORT_3000 2>/dev/null || true
        sleep 2
        if [ -f "/home/user/webapp/start_3000.sh" ]; then
            bash /home/user/webapp/start_3000.sh &
        fi
    fi
fi

# 3. 检查并修复8080端口服务
log "📡 3. 检查8080端口服务..."
PORT_8080=$(lsof -ti:8080 2>/dev/null)
if [ -z "$PORT_8080" ]; then
    log "  ⚠️  8080端口无服务运行"
    # 尝试启动服务（如果有启动脚本）
    if [ -f "/home/user/webapp/start_8080.sh" ]; then
        log "  🔄 启动8080端口服务..."
        bash /home/user/webapp/start_8080.sh &
        sleep 3
        if lsof -ti:8080 >/dev/null 2>&1; then
            log "  ✅ 8080端口服务启动成功"
        else
            log "  ❌ 8080端口服务启动失败"
        fi
    fi
else
    log "  ✅ 8080端口服务运行正常 (PID: $PORT_8080)"
    # 检查进程健康状态
    if ! kill -0 $PORT_8080 2>/dev/null; then
        log "  ⚠️  进程异常，尝试重启..."
        kill -9 $PORT_8080 2>/dev/null || true
        sleep 2
        if [ -f "/home/user/webapp/start_8080.sh" ]; then
            bash /home/user/webapp/start_8080.sh &
        fi
    fi
fi

# 4. 检查并修复PM2服务
log "🔄 4. 检查PM2服务..."
if command -v pm2 >/dev/null 2>&1; then
    # 检查PM2守护进程
    if ! pm2 ping >/dev/null 2>&1; then
        log "  ⚠️  PM2守护进程未运行，尝试启动..."
        pm2 resurrect 2>/dev/null || pm2 startup 2>/dev/null || true
    fi
    
    # 获取PM2服务列表
    PM2_LIST=$(pm2 jlist 2>/dev/null)
    if [ -n "$PM2_LIST" ] && [ "$PM2_LIST" != "[]" ]; then
        log "  📊 PM2服务状态:"
        pm2 status | grep -E "online|errored|stopped" | while read line; do
            log "    $line"
        done
        
        # 重启所有errored或stopped状态的服务
        ERRORED=$(pm2 jlist 2>/dev/null | grep -o '"status":"errored"' | wc -l)
        STOPPED=$(pm2 jlist 2>/dev/null | grep -o '"status":"stopped"' | wc -l)
        
        if [ "$ERRORED" -gt 0 ] || [ "$STOPPED" -gt 0 ]; then
            log "  🔄 重启异常服务..."
            pm2 restart all 2>&1 | while read line; do log "    $line"; done
            sleep 3
            log "  ✅ PM2服务已重启"
        else
            log "  ✅ 所有PM2服务运行正常"
        fi
    else
        log "  ℹ️  无PM2管理的服务"
    fi
else
    log "  ℹ️  PM2未安装"
fi

# 5. 检查5003端口（主服务）
log "📡 5. 检查5003端口服务..."
PORT_5003=$(lsof -ti:5003 2>/dev/null)
if [ -z "$PORT_5003" ]; then
    log "  ⚠️  5003端口无服务运行，尝试重启..."
    cd /home/user/webapp
    nohup python3 home_data_api_v2.py > api_v2_final.log 2>&1 &
    sleep 5
    if lsof -ti:5003 >/dev/null 2>&1; then
        log "  ✅ 5003端口服务启动成功"
    else
        log "  ❌ 5003端口服务启动失败"
    fi
else
    log "  ✅ 5003端口服务运行正常 (PID: $PORT_5003)"
fi

# 6. 内存清理
log "🧹 6. 清理内存缓存..."
sync
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || log "  ℹ️  需要root权限清理内存缓存"

# 7. 检查系统资源
log "📊 7. 系统资源状态:"
MEM_USAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')
log "  - CPU使用率: $CPU_USAGE"
log "  - 内存使用率: $MEM_USAGE"
log "  - 磁盘使用率: $DISK_USAGE"

# 8. 检查网络连接
log "🌐 8. 检查网络连接..."
if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    log "  ✅ 网络连接正常"
else
    log "  ⚠️  网络连接异常"
fi

log "=========================================="
log "✅ 每小时自动修复任务执行完成"
log "=========================================="
echo ""

# 轮转日志
check_log_size

exit 0
