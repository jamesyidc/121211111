#!/bin/bash
# 系统健康检查和自动清理脚本

echo "================================"
echo "系统健康检查"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================"

# 1. 检查硬盘使用
echo -e "\n=== 硬盘使用情况 ==="
df -h | grep -E "Filesystem|/dev/root"
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "⚠️ 警告: 硬盘使用率 ${DISK_USAGE}% (超过80%)"
    echo "开始清理..."
    # 清理临时文件
    cd /home/user
    rm -f *.html *.png *.jpg 2>/dev/null
    rm -rf temp_download uploaded_files 2>/dev/null
    cd /home/user/webapp
    rm -f *.log.* nohup.out 2>/dev/null
    echo "✓ 清理完成"
else
    echo "✓ 硬盘使用率正常: ${DISK_USAGE}%"
fi

# 2. 检查内存使用
echo -e "\n=== 内存使用情况 ==="
free -h | grep -E "Mem|Swap"

# 3. 检查系统负载
echo -e "\n=== 系统负载 ==="
uptime

# 4. 检查关键进程
echo -e "\n=== 关键进程状态 ==="
if pgrep -f "app_new.py" > /dev/null; then
    echo "✓ Flask应用运行中 (PID: $(pgrep -f app_new.py))"
else
    echo "❌ Flask应用未运行"
fi

# 检查采集器数量
COLLECTOR_COUNT=$(ps aux | grep "collector.py" | grep -v grep | wc -l)
echo "✓ 运行中的采集器: $COLLECTOR_COUNT 个"

# 5. 检查端口占用
echo -e "\n=== 端口占用情况 ==="
ss -tulpn 2>/dev/null | grep -E "5000|3000|8080" | awk '{print $5, $7}' | sed 's/.*:/Port: /' || echo "无关键端口占用"

# 6. 检查PM2
echo -e "\n=== PM2状态 ==="
if command -v pm2 &> /dev/null; then
    PM2_COUNT=$(pm2 list | grep -c "online" || echo "0")
    echo "✓ PM2已安装, 运行中进程: $PM2_COUNT"
else
    echo "ℹ PM2未安装"
fi

# 7. 清理僵尸进程
echo -e "\n=== 检查僵尸进程 ==="
ZOMBIE_COUNT=$(ps aux | grep defunct | grep -v grep | wc -l)
if [ $ZOMBIE_COUNT -gt 0 ]; then
    echo "⚠️ 发现 $ZOMBIE_COUNT 个僵尸进程"
else
    echo "✓ 无僵尸进程"
fi

echo -e "\n================================"
echo "健康检查完成"
echo "================================"
