#!/bin/bash
# 启动3000端口服务脚本

LOG_FILE="/home/user/webapp/service_3000.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动3000端口服务..." >> "$LOG_FILE"

cd /home/user/webapp

# 检查是否已经有服务在运行
if lsof -ti:3000 >/dev/null 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 3000端口已被占用，先停止..." >> "$LOG_FILE"
    kill -9 $(lsof -ti:3000) 2>/dev/null || true
    sleep 2
fi

# 根据项目类型启动服务
# 如果是Node.js项目
if [ -f "package.json" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动Node.js服务..." >> "$LOG_FILE"
    # 使用PM2启动（如果安装了）
    if command -v pm2 >/dev/null 2>&1; then
        pm2 start npm --name "service-3000" -- run dev --watch >> "$LOG_FILE" 2>&1 &
    else
        # 直接启动
        PORT=3000 npm run dev >> "$LOG_FILE" 2>&1 &
    fi
# 如果是Python项目
elif [ -f "app.py" ] || [ -f "server.py" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动Python服务..." >> "$LOG_FILE"
    python3 server.py >> "$LOG_FILE" 2>&1 &
fi

sleep 3

if lsof -ti:3000 >/dev/null 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 3000端口服务启动成功" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ 3000端口服务启动失败" >> "$LOG_FILE"
fi
