# 🚀 快速启动指南

## 📱 立即访问

### 🌐 Web 应用
```
https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai
```

点击上面的链接即可访问完整的加密货币数据分析系统！

## 📊 系统状态

### 查看所有服务
```bash
cd /home/user/webapp
pm2 list
```

### 查看实时日志
```bash
pm2 logs
# 或查看特定服务
pm2 logs flask-app
```

### 监控服务
```bash
pm2 monit
```

## 🔧 常用管理命令

### 重启服务
```bash
# 重启单个服务
pm2 restart flask-app

# 重启所有服务
pm2 restart all
```

### 停止/启动服务
```bash
# 停止所有服务
pm2 stop all

# 启动所有服务
pm2 start ecosystem_all_services.config.js
```

### 查看服务详情
```bash
pm2 describe flask-app
```

## 📂 重要目录

- **源代码**: `/home/user/webapp/source_code/`
- **数据目录**: `/home/user/webapp/data/`
- **日志目录**: `/home/user/webapp/logs/`
- **配置文件**: `/home/user/webapp/ecosystem_all_services.config.js`

## 🔑 核心功能

### ✅ 已恢复的功能

1. **Flask Web 应用** - 主页和所有路由
2. **PM2 服务管理** - 11 个服务全部运行
3. **数据采集系统** - 8 个数据采集器
4. **监控系统** - 2 个监控服务
5. **缓存系统** - 服务器端缓存已启用
6. **API 接口** - 所有 API 端点正常

### 🎯 核心服务

1. **flask-app** - Web 应用和 API 服务
2. **coin-price-tracker** - 币价追踪
3. **support-resistance-snapshot** - 支撑阻力
4. **price-speed-collector** - 价格速度
5. **v1v2-collector** - V1V2 数据
6. **crypto-index-collector** - 加密指数
7. **okx-day-change-collector** - OKX 日变化
8. **sar-slope-collector** - SAR 斜率
9. **liquidation-1h-collector** - 清算数据
10. **anchor-profit-monitor** - 锚点盈利监控
11. **escape-signal-monitor** - 逃顶信号监控

## 💡 提示

- 所有服务通过 PM2 管理，自动重启
- 日志文件自动轮转
- 数据采集器每 30 分钟自动重启
- 系统已保存到 PM2，重启后自动恢复

## 📞 故障排查

### 服务无法启动
```bash
# 查看错误日志
pm2 logs flask-app --err --lines 100

# 重启服务
pm2 restart flask-app
```

### 端口被占用
```bash
# 查看端口使用
lsof -i :5000

# 或使用 netstat
netstat -tlnp | grep 5000
```

### 磁盘空间不足
```bash
# 清理旧日志
cd /home/user/webapp
find logs/ -name "*.log" -mtime +7 -delete

# 查看磁盘使用
df -h
```

## 📚 更多信息

查看完整部署报告：
```bash
cat /home/user/webapp/DEPLOYMENT_SUMMARY_2026-01-27.md
```

---
**最后更新**: 2026-01-27
**状态**: ✅ 所有系统运行正常
