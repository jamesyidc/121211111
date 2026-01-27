# 系统恢复部署报告
**日期**: 2026年1月27日  
**操作**: 从 Google Drive 完整备份恢复系统

## 📦 部署概况

### 1. 数据下载
- ✅ 从 Google Drive 下载了完整备份（约 5.4GB）
- ✅ 包含以下文件：
  - `home_user.tar.gz` (3.3GB，分3个部分)
  - `opt.tar.gz` (408MB)
  - `usr.tar.gz` (1.6GB)
  - `var.tar.gz` (17MB)
  - `root_and_etc.tar.gz` (380KB)

### 2. 系统恢复
- ✅ 解压并恢复 `/home/user/webapp` 目录
- ✅ 恢复了所有源代码文件
- ✅ 恢复了所有数据文件（JSONL格式）
- ✅ 恢复了 PM2 配置文件

### 3. 依赖安装
- ✅ Python 依赖安装完成
- ✅ Flask 3.0.0
- ✅ Flask-CORS 4.0.0
- ✅ Google API 客户端库
- ✅ APScheduler 3.10.4
- ✅ PyTZ 2023.3

### 4. PM2 服务启动
已启动以下 11 个服务：

#### Web 服务
1. **flask-app** - Flask Web 应用 (端口 5000)
   - 状态: ✅ 运行中
   - 内存: ~90MB
   - 配置: source_code/app_new.py

#### 数据采集器 (8个)
2. **coin-price-tracker** - 币价追踪器
3. **support-resistance-snapshot** - 支撑阻力快照
4. **price-speed-collector** - 价格速度采集
5. **v1v2-collector** - V1V2数据采集
6. **crypto-index-collector** - 加密指数采集
7. **okx-day-change-collector** - OKX日变化采集
8. **sar-slope-collector** - SAR斜率采集
9. **liquidation-1h-collector** - 1小时清算数据

#### 监控服务 (2个)
10. **anchor-profit-monitor** - 锚点盈利监控
11. **escape-signal-monitor** - 逃顶信号监控

### 5. 系统访问

#### 🌐 Flask 应用访问地址
```
https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai
```

#### 📊 数据目录结构
```
/home/user/webapp/data/
├── aligned_data_30min.jsonl
├── anchor_daily/
├── anchor_unified/
├── coin_change_tracker/
├── coin_price_tracker/
├── crypto_index_jsonl/
├── dashboard_jsonl/
├── escape_signal_daily/
├── escape_signal_jsonl/
├── extreme_jsonl/
├── extreme_tracking/
├── fear_greed_jsonl/
├── gdrive_jsonl/
├── liquidation_1h/
├── okx_trading_jsonl/
├── okx_trading_logs/
├── panic_jsonl/
├── price_comparison_jsonl/
├── price_speed_jsonl/
├── query_jsonl/
├── sar_jsonl/
├── sar_slope_jsonl/
├── support_resistance_jsonl/
└── v1v2_jsonl/
```

## 🎯 核心功能已恢复

### 1. Flask 路由系统
- ✅ 主页路由
- ✅ API 路由
- ✅ 数据查询路由
- ✅ 文件服务路由

### 2. 缓存系统
- ✅ 服务器端缓存 (ServerCache)
- ✅ 缓存装饰器 (@cached_response)
- ✅ 缓存键管理
- ✅ 缓存过期控制

### 3. API 端点
所有 API 端点已恢复：
- `/api/*` - 各类数据 API
- `/api/anchor-profit/latest` - 锚点盈利
- `/api/escape-signal-stats` - 逃顶信号
- 以及更多...

### 4. 数据采集系统
- ✅ 实时价格追踪
- ✅ 支撑阻力分析
- ✅ 技术指标计算
- ✅ 市场情绪监控

## 📈 系统状态

### 磁盘使用
- 总容量: 26GB
- 已使用: 24GB (92%)
- 可用: 2.3GB
- ⚠️ 建议定期清理旧日志和临时文件

### 内存使用
- Flask 应用: ~90MB
- 各采集器: 15-37MB 每个
- 总计: ~350MB

### 服务状态
所有服务运行正常，状态为 `online`

## 🔧 PM2 管理命令

### 查看服务状态
```bash
cd /home/user/webapp
pm2 list
pm2 status
```

### 查看日志
```bash
pm2 logs flask-app
pm2 logs --lines 50
```

### 重启服务
```bash
pm2 restart flask-app
pm2 restart all
```

### 停止服务
```bash
pm2 stop flask-app
pm2 stop all
```

### 删除服务
```bash
pm2 delete flask-app
pm2 delete all
```

### 重新加载配置
```bash
pm2 start ecosystem_all_services.config.js
```

## 🎉 部署成功

所有系统组件已成功恢复并运行！

- ✅ Flask 应用
- ✅ PM2 服务管理
- ✅ 数据采集器
- ✅ 监控系统
- ✅ 缓存系统
- ✅ API 路由

## 📝 注意事项

1. **磁盘空间**: 当前可用空间较少，建议定期清理
2. **日志管理**: 日志文件在 `/home/user/webapp/logs/`
3. **数据备份**: 定期备份数据目录到 Google Drive
4. **服务监控**: 使用 `pm2 monit` 实时监控服务状态

## 🔗 相关链接

- Flask 应用: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai
- 项目目录: /home/user/webapp
- 配置文件: ecosystem_all_services.config.js

---
**部署完成时间**: 2026-01-27 14:46 UTC
**部署状态**: ✅ 成功
