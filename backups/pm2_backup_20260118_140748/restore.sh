#!/bin/bash
#
# PM2进程自动恢复脚本
# 备份时间: 2026-01-18 14:07:48
# 备份目录: /home/user/webapp/backups/pm2_backup_20260118_140748
#

set -e

BACKUP_DIR="/home/user/webapp/backups/pm2_backup_20260118_140748"
WEBAPP_DIR="/home/user/webapp"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           PM2进程自动恢复脚本                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "备份时间: 2026-01-18 14:07:48"
echo "备份目录: $BACKUP_DIR"
echo "进程总数: 20个"
echo ""

# 检查备份目录是否存在
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ 错误: 备份目录不存在!"
    echo "   目录: $BACKUP_DIR"
    exit 1
fi

echo "✅ 备份目录存在"

# 检查PM2是否安装
if ! command -v pm2 &> /dev/null; then
    echo "❌ 错误: PM2未安装!"
    echo "   请运行: npm install -g pm2"
    exit 1
fi

echo "✅ PM2已安装 (版本: $(pm2 --version))"

# 询问用户选择恢复方法
echo ""
echo "请选择恢复方法:"
echo "  1) 快速恢复 (pm2 resurrect) - 推荐"
echo "  2) 从备份JSON恢复"
echo "  3) 使用Ecosystem配置文件恢复"
echo "  4) 仅查看备份信息（不恢复）"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🔄 方法1: 快速恢复..."
        echo ""
        
        read -p "⚠️  警告: 这将停止所有当前进程，是否继续? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            echo "❌ 已取消"
            exit 0
        fi
        
        echo "📋 停止所有当前进程..."
        pm2 delete all || true
        
        echo "🔄 从PM2默认备份恢复..."
        pm2 resurrect
        
        echo "💾 保存进程列表..."
        pm2 save
        
        echo "✅ 快速恢复完成!"
        ;;
        
    2)
        echo ""
        echo "🔄 方法2: 从备份JSON恢复..."
        echo ""
        
        if [ ! -f "$BACKUP_DIR/pm2_processes.json" ]; then
            echo "❌ 错误: pm2_processes.json 不存在!"
            exit 1
        fi
        
        read -p "⚠️  警告: 这将停止所有当前进程，是否继续? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            echo "❌ 已取消"
            exit 0
        fi
        
        echo "📋 停止所有当前进程..."
        pm2 delete all || true
        
        echo "🚀 从JSON启动进程..."
        cd "$BACKUP_DIR"
        pm2 start pm2_processes.json
        
        echo "💾 保存进程列表..."
        pm2 save
        
        echo "✅ JSON恢复完成!"
        ;;
        
    3)
        echo ""
        echo "🔄 方法3: 使用Ecosystem配置文件恢复..."
        echo ""
        
        echo "📋 复制ecosystem配置文件到项目目录..."
        cp -v "$BACKUP_DIR"/ecosystem*.js "$WEBAPP_DIR/"
        
        echo ""
        echo "可用的Ecosystem配置文件:"
        ls -1 "$WEBAPP_DIR"/ecosystem*.js
        echo ""
        
        read -p "请输入要使用的配置文件名 (如: ecosystem_all_services.config.js): " config_file
        
        if [ ! -f "$WEBAPP_DIR/$config_file" ]; then
            echo "❌ 错误: 配置文件不存在!"
            exit 1
        fi
        
        read -p "⚠️  警告: 这将停止所有当前进程，是否继续? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            echo "❌ 已取消"
            exit 0
        fi
        
        echo "📋 停止所有当前进程..."
        pm2 delete all || true
        
        echo "🚀 启动进程..."
        cd "$WEBAPP_DIR"
        pm2 start "$config_file"
        
        echo "💾 保存进程列表..."
        pm2 save
        
        echo "✅ Ecosystem恢复完成!"
        ;;
        
    4)
        echo ""
        echo "📊 备份信息:"
        echo ""
        
        if [ -f "$BACKUP_DIR/pm2_list.txt" ]; then
            cat "$BACKUP_DIR/pm2_list.txt"
        else
            echo "pm2_list.txt 不存在"
        fi
        
        echo ""
        echo "📂 备份文件列表:"
        ls -lh "$BACKUP_DIR"
        
        exit 0
        ;;
        
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

# 显示恢复后的进程列表
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 当前运行的进程列表:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pm2 list

echo ""
echo "✅ 恢复完成!"
echo ""
echo "📝 后续步骤:"
echo "  1. 检查所有进程状态: pm2 list"
echo "  2. 查看进程日志: pm2 logs"
echo "  3. 监控进程: pm2 monit"
echo "  4. 设置开机自启: pm2 startup"
echo ""
