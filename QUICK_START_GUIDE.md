# 🚀 系统快速启动指南

## 📋 系统概览

**项目**: 加密货币数据分析系统  
**状态**: ✅ 运行中  
**访问URL**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai

---

## 🎯 快速命令

### 查看服务状态
```bash
cd /home/user/webapp && pm2 list
```

### 查看日志
```bash
# 查看所有日志
cd /home/user/webapp && pm2 logs

# 查看特定服务日志
cd /home/user/webapp && pm2 logs flask-app
cd /home/user/webapp && pm2 logs coin-price-tracker
```

### 重启服务
```bash
# 重启所有服务
cd /home/user/webapp && pm2 restart all

# 重启特定服务
cd /home/user/webapp && pm2 restart flask-app
```

### 停止/启动服务
```bash
# 停止所有
cd /home/user/webapp && pm2 stop all

# 启动所有
cd /home/user/webapp && pm2 start ecosystem_all_services.config.js
```

---

## 🔍 主要功能页面

| 页面 | URL路径 | 描述 |
|-----|--------|------|
| 主页 | / | 系统主页和导航 |
| 查询页面 | /query | 数据查询界面 |
| 交易决策 | /trading-decision | 交易决策分析 |
| 交易管理器 | /trading-manager | 交易管理界面 |
| 仪表板 | /dashboard | 数据仪表板 |
| 锚点监控 | /anchor-auto-monitor | 锚点自动监控 |
| API文档 | /api/docs | API接口文档 |

---

## 📡 主要API端点

### 数据查询
```bash
# 获取最新数据
curl http://localhost:5000/api/latest

# 查询历史数据
curl "http://localhost:5000/api/query?start_date=2026-01-20&end_date=2026-01-27"

# 获取图表数据
curl http://localhost:5000/api/chart
```

### 交易相关
```bash
# 获取交易配置
curl http://localhost:5000/api/trading/config

# 获取交易决策
curl http://localhost:5000/api/trading/decisions

# 获取交易信号
curl http://localhost:5000/api/trading/signals
```

### 特定数据
```bash
# SAR斜率数据
curl http://localhost:5000/api/sar-slope/latest-jsonl

# 锚点系统当前持仓
curl "http://localhost:5000/api/anchor-system/current-positions?trade_mode=real"

# Panic指数
curl http://localhost:5000/api/panic/latest
```

---

## 🛠️ 维护操作

### 清理磁盘空间
```bash
cd /home/user/webapp

# 清理PM2日志
pm2 flush

# 删除7天前的日志
find logs/ -name "*.log" -mtime +7 -delete

# 清理临时文件
rm -rf extract_key_files/
```

### 检查磁盘使用
```bash
df -h
du -sh /home/user/webapp/*
```

### 备份配置
```bash
cd /home/user/webapp
tar -czf configs_backup_$(date +%Y%m%d).tar.gz configs/ ecosystem*.js
```

---

## 🏗️ 服务架构

### 核心服务
- **flask-app**: 主Web应用 (端口5000)

### 数据采集器
1. **coin-price-tracker**: 币价追踪
2. **support-resistance-snapshot**: 支撑阻力快照
3. **price-speed-collector**: 价格速度采集
4. **v1v2-collector**: V1V2数据采集
5. **crypto-index-collector**: 加密指数采集
6. **okx-day-change-collector**: OKX日变化采集
7. **sar-slope-collector**: SAR斜率采集
8. **liquidation-1h-collector**: 1小时清算采集

### 监控服务
9. **anchor-profit-monitor**: 锚点利润监控
10. **escape-signal-monitor**: 逃顶信号监控

---

## 📂 目录结构

```
/home/user/webapp/
├── source_code/          # Python源代码
│   └── app.py           # 主Flask应用
├── configs/             # 配置文件
│   ├── anchor_config.json
│   ├── telegram_config.json
│   └── trading_config.json
├── ecosystem_*.js       # PM2配置文件
├── templates/           # HTML模板
├── static/             # 静态资源
├── logs/               # 日志文件
└── data/               # 数据目录 (JSONL文件)
```

---

## 🔥 常见问题

### Q: 如何查看实时日志？
```bash
cd /home/user/webapp && pm2 logs --lines 50
```

### Q: 服务崩溃了怎么办？
```bash
# 查看哪个服务崩溃
cd /home/user/webapp && pm2 list

# 查看错误日志
cd /home/user/webapp && pm2 logs <service-name> --err

# 重启服务
cd /home/user/webapp && pm2 restart <service-name>
```

### Q: 如何更新配置？
1. 编辑配置文件: `configs/*.json`
2. 重启相关服务: `pm2 restart <service-name>`

### Q: 磁盘空间不足？
```bash
# 清理日志
cd /home/user/webapp && pm2 flush
cd /home/user/webapp && find logs/ -name "*.log" -mtime +3 -delete

# 删除下载的备份文件
rm -rf /home/user/webapp/1-23完整5.4g/
```

---

## 🚨 紧急操作

### 全部重启
```bash
cd /home/user/webapp
pm2 delete all
pm2 start ecosystem_all_services.config.js
```

### 只启动Flask应用
```bash
cd /home/user/webapp
pm2 start ecosystem_flask.config.js
```

### 停止所有服务
```bash
cd /home/user/webapp && pm2 stop all
```

---

## 📞 系统信息

- **Python版本**: Python 3.x
- **Flask**: Web框架
- **PM2**: 进程管理
- **数据格式**: JSONL (JSON Lines)
- **压缩**: gzip (flask_compress)

---

## ✅ 健康检查

```bash
# 1. 检查PM2服务
cd /home/user/webapp && pm2 list

# 2. 测试Flask应用
curl http://localhost:5000/

# 3. 测试API
curl http://localhost:5000/api/latest

# 4. 检查磁盘空间
df -h

# 5. 检查内存
free -h
```

---

**系统已完全恢复并运行正常！** 🎉
