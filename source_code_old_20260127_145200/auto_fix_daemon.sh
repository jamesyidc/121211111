#!/bin/bash
# 自动修复守护进程 - 每小时执行一次
# 使用后台循环代替cron

SCRIPT_DIR="/home/user/webapp"
FIX_SCRIPT="$SCRIPT_DIR/auto_fix_hourly.sh"
PID_FILE="$SCRIPT_DIR/auto_fix_daemon.pid"
LOG_FILE="$SCRIPT_DIR/auto_fix_daemon.log"

# 日志函数
daemon_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        daemon_log "守护进程已在运行 (PID: $OLD_PID)"
        echo "守护进程已在运行 (PID: $OLD_PID)"
        exit 1
    else
        daemon_log "清理旧PID文件"
        rm -f "$PID_FILE"
    fi
fi

# 写入当前PID
echo $$ > "$PID_FILE"

daemon_log "=========================================="
daemon_log "🚀 自动修复守护进程启动"
daemon_log "PID: $$"
daemon_log "执行间隔: 每小时"
daemon_log "=========================================="

# 首次立即执行
daemon_log "执行首次自动修复..."
bash "$FIX_SCRIPT"

# 无限循环，每小时执行一次
while true; do
    # 等待1小时（3600秒）
    NEXT_RUN=$(date -d "+1 hour" '+%Y-%m-%d %H:%M:%S')
    daemon_log "下次执行时间: $NEXT_RUN"
    
    sleep 3600
    
    daemon_log "=========================================="
    daemon_log "⏰ 开始执行定时自动修复"
    daemon_log "=========================================="
    
    # 执行修复脚本
    if [ -f "$FIX_SCRIPT" ]; then
        bash "$FIX_SCRIPT"
    else
        daemon_log "❌ 修复脚本不存在: $FIX_SCRIPT"
    fi
done
