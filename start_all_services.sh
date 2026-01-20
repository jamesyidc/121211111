#!/bin/bash
#
# 全局服务启动脚本
# 用于沙箱重启后自动恢复所有服务
# 
# 使用方法:
#   bash /home/user/webapp/start_all_services.sh
#

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🚀 开始启动所有服务..."
echo "=========================================="
echo ""

# 工作目录
WEBAPP_DIR="/home/user/webapp"
cd "$WEBAPP_DIR"

echo "📁 当前目录: $(pwd)"
echo ""

# ============================================
# 1. 检查并启动 PM2
# ============================================
echo "1️⃣ 检查 PM2 状态..."

if ! command -v pm2 &> /dev/null; then
    echo "❌ PM2 未安装，正在安装..."
    npm install -g pm2
else
    echo "✅ PM2 已安装: $(pm2 --version)"
fi

echo ""

# ============================================
# 2. 停止所有现有的 PM2 进程（清理）
# ============================================
echo "2️⃣ 清理现有的 PM2 进程..."
pm2 delete all 2>/dev/null || echo "⚠️ 没有运行中的 PM2 进程"
echo ""

# ============================================
# 3. 从 ecosystem 配置启动所有服务
# ============================================
echo "3️⃣ 从 ecosystem.config.cjs 启动所有数据采集器..."
cd "$WEBAPP_DIR/major-events-system"
pm2 start ecosystem.config.cjs
echo "✅ 所有数据采集器已启动"
echo ""

# ============================================
# 4. 单独启动 Flask 应用
# ============================================
echo "4️⃣ 启动 Flask 应用..."
cd "$WEBAPP_DIR"
pm2 start source_code/app_new.py \
    --name flask-app \
    --interpreter python3 \
    --cwd "$WEBAPP_DIR" \
    --max-memory-restart 1500M \
    --log-date-format "YYYY-MM-DD HH:mm:ss"

echo "✅ Flask 应用已启动"
echo ""

# ============================================
# 5. 保存 PM2 配置（用于下次重启）
# ============================================
echo "5️⃣ 保存 PM2 配置..."
pm2 save
echo "✅ PM2 配置已保存到 ~/.pm2/dump.pm2"
echo ""

# ============================================
# 6. 设置 PM2 开机自启动（可选）
# ============================================
# 注意：沙箱环境可能不支持 systemd
# echo "6️⃣ 设置 PM2 开机自启动..."
# pm2 startup
# echo "✅ PM2 已配置为开机自启动"
# echo ""

# ============================================
# 7. 显示最终状态
# ============================================
echo "=========================================="
echo "📊 最终服务状态:"
echo "=========================================="
pm2 list

echo ""
echo "=========================================="
echo "✅ 所有服务启动完成！"
echo "=========================================="
echo ""
echo "📋 服务列表:"
echo "  - major-events-monitor"
echo "  - anchor-data-collector"
echo "  - unified-data-collector"
echo "  - sar-slope-collector"
echo "  - escape-signal-calculator"
echo "  - coin-price-tracker"
echo "  - support-resistance-collector"
echo "  - panic-wash-collector"
echo "  - anchor-profit-monitor"
echo "  - liquidation-1h-collector"
echo "  - flask-app"
echo ""
echo "🌐 Flask 应用地址:"
echo "  - http://localhost:5000"
echo ""
echo "📝 常用命令:"
echo "  - 查看所有进程: pm2 list"
echo "  - 查看日志: pm2 logs"
echo "  - 重启所有: pm2 restart all"
echo "  - 停止所有: pm2 stop all"
echo "  - 删除所有: pm2 delete all"
echo ""
