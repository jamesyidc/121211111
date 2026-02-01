# 🚀 系统快速访问指南

## 📡 服务访问

### 主应用
**Flask Web应用**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai

### 主要页面
- 🏠 **主页**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/
- 🔍 **查询页面**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/query
- 📊 **仪表板**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/dashboard
- 💰 **交易管理器**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/trading-manager
- 🎯 **交易决策**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/trading-decision
- ⚓ **锚点监控**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/anchor-auto-monitor

### 主要API端点
- 📈 **最新数据**: /api/latest
- 📊 **图表数据**: /api/chart
- 🔍 **查询API**: /api/query
- 📚 **API文档**: /api/docs
- 💹 **SAR斜率**: /api/sar-slope/latest-jsonl
- 🏦 **交易配置**: /api/trading/config
- 📋 **交易决策**: /api/trading/decisions
- 🔔 **交易信号**: /api/trading/signals

## 🛠️ PM2 服务管理

### 查看所有服务
```bash
pm2 list
```

### 查看日志
```bash
pm2 logs                    # 所有服务
pm2 logs flask-app          # Flask应用
pm2 logs --nostream         # 不实时刷新
```

### 重启服务
```bash
pm2 restart all             # 重启所有
pm2 restart flask-app       # 重启Flask
pm2 restart 0               # 按ID重启
```

### 停止/启动服务
```bash
pm2 stop all               # 停止所有
pm2 start all              # 启动所有
pm2 delete all             # 删除所有
```

### 保存PM2配置
```bash
pm2 save                   # 保存当前进程列表
```

## 📊 服务状态总览

### 运行中的服务 (11个)
1. **flask-app** - Flask Web应用服务器
2. **coin-price-tracker** - 币价追踪器
3. **support-resistance-snapshot** - 支撑阻力快照
4. **price-speed-collector** - 价格速度采集器
5. **v1v2-collector** - V1V2数据采集器
6. **crypto-index-collector** - 加密指数采集器
7. **okx-day-change-collector** - OKX日变化采集器
8. **sar-slope-collector** - SAR斜率采集器
9. **liquidation-1h-collector** - 1小时清算采集器
10. **anchor-profit-monitor** - 锚点利润监控
11. **escape-signal-monitor** - 逃顶信号监控

## 🔧 常用命令

### 检查系统状态
```bash
# 磁盘使用
df -h

# PM2进程
pm2 status

# 内存使用
free -h

# 查看Flask日志
tail -f /home/user/webapp/logs/flask-app-out-0.log
```

### 测试API
```bash
# 测试主页
curl http://localhost:5000/

# 测试API端点
curl http://localhost:5000/api/latest

# 测试SAR斜率
curl http://localhost:5000/api/sar-slope/latest-jsonl
```

### 清理磁盘空间
```bash
# 清理PM2日志
pm2 flush

# 删除旧日志
find /home/user/webapp/logs -name "*.log" -mtime +7 -delete

# 清理下载的备份
rm -rf /home/user/webapp/downloaded_backup
rm -rf /home/user/webapp/extract_key_files
```

## 📝 配置文件位置

### PM2配置
- `/home/user/webapp/ecosystem_all_services.config.js` - 所有服务
- `/home/user/webapp/ecosystem_flask.config.js` - Flask应用

### 应用配置
- `/home/user/webapp/configs/anchor_config.json` - 锚点配置
- `/home/user/webapp/configs/telegram_config.json` - Telegram配置
- `/home/user/webapp/configs/trading_config.json` - 交易配置
- `/home/user/webapp/configs/v1v2_settings.json` - V1V2设置

### 主应用代码
- `/home/user/webapp/source_code/app.py` - Flask主应用
- `/home/user/webapp/source_code/` - 所有Python脚本

## 🔍 故障排查

### 服务不响应
```bash
pm2 restart flask-app
pm2 logs flask-app --err
```

### 磁盘空间满
```bash
pm2 flush
df -h
```

### API返回错误
```bash
pm2 logs flask-app --lines 100
curl -v http://localhost:5000/api/latest
```

## 🎯 快速恢复命令

如果需要完全重启所有服务：
```bash
cd /home/user/webapp
pm2 delete all
pm2 start ecosystem_all_services.config.js
pm2 save
```

## ✅ 系统健康检查

```bash
# 一键检查脚本
cd /home/user/webapp
echo "=== PM2 状态 ==="
pm2 list
echo ""
echo "=== 磁盘使用 ==="
df -h | grep -E "Filesystem|/dev/root"
echo ""
echo "=== 测试API ==="
curl -s http://localhost:5000/api/latest | head -c 100
echo ""
echo "=== 服务URL ==="
echo "Flask应用: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai"
```

---

## 📞 支持信息

- **系统恢复时间**: 2026-01-27 15:00 UTC
- **备份来源**: Google Drive (5.2GB)
- **恢复状态**: ✅ 完全成功
- **服务数量**: 11个PM2进程
- **主要功能**: Flask API + 数据采集 + 交易监控
