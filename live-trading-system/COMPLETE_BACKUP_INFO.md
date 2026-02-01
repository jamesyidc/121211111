# 实时交易系统完整备份说明

## 备份时间
2026-01-19 14:22:00

## 备份内容

### 🔥 核心API服务器
- ✅ **okex-trading-api.js** (20KB) - OKX交易API核心服务器
- ✅ **sandbox-api-server.cjs** (5.3KB) - Sandbox API服务器

### 📱 前端文件 (public/)
- live-trading-v2.html + live-trading-v2.js (V2版本)
- live-trading.html + live-trading.js (V1版本)
- live-trading-debug.html + live-trading-debug.js
- live-trading-debug2.html + live-trading-debug2.js
- public/static/api-manager.js
- public/static/api-wrapper.js
- public/static/live-trading.js
- filtered-signals-api.js

### 💾 JSONL数据存储 (data/trading/)
- accounts.jsonl - 账户数据
- positions.jsonl - 持仓数据
- orders.jsonl - 订单数据
- trade_history.jsonl - 交易历史
- tpsl_config.jsonl - 止盈止损配置
- defense_config.jsonl - 防守加仓配置

### 🔧 核心服务 (src/services/)
- jsonlStorageService.ts - JSONL存储服务
- liveTradingStorageAdapter.ts - 存储适配器
- tradingAccountService.ts - 账户服务
- tradingRuleService.ts - 规则服务
- tradingSignalService.ts - 信号服务
- tradingScheduler.ts - 调度器
- okxService.ts - OKX服务

### 🛣️ 路由系统
- src/routes/liveTradingRoutes.ts - 实时交易路由V1
- src/routes/liveTradingRoutesV2.ts - 实时交易路由V2
- src/routes/pm2MonitorRoutes.ts - PM2监控路由
- functions/api/pm2/[[path]].ts - PM2 API端点

### ⚙️ PM2配置
- ecosystem.config.cjs - 主服务配置
- ecosystem.pm2-monitor.config.cjs - 监控服务配置
- pm2-monitor-server.cjs - PM2监控服务器

### 📦 配置文件
- package.json + package-lock.json
- tsconfig.json
- wrangler.jsonc
- vite.config.ts
- .env.example
- trading.db (数据库文件)

### 🔧 工具和脚本
- src/utils/okxAPIHelper.ts - OKX API助手
- scripts/migrate-to-jsonl.cjs - JSONL迁移脚本
- scripts/migrate-db-to-jsonl.js - 数据库迁移脚本
- run-live-trading-migrations.js - 运行迁移
- test-okx-tpsl-api.ts - API测试

## 文件统计
- 总文件数: 81
- 总大小: 1.4M

## 快速恢复步骤

### 1. 解压备份
```bash
tar -xzf live-trading-COMPLETE-backup-YYYYMMDD_HHMMSS.tar.gz
cd live-trading-system
```

### 2. 复制到目标目录
```bash
cp -r * /home/user/webapp/
cd /home/user/webapp
```

### 3. 安装依赖
```bash
npm install
```

### 4. 启动服务
```bash
# 启动主服务
pm2 start ecosystem.config.cjs

# 启动PM2监控
pm2 start ecosystem.pm2-monitor.config.cjs

# 保存PM2配置
pm2 save
```

### 5. 验证服务
```bash
pm2 list
curl http://localhost:3000/live-trading-v2.html
curl http://localhost:8080/api/coins/all
curl http://localhost:9000/api/pm2/list
```

## 系统访问地址

- **实时交易V2**: http://localhost:3000/live-trading-v2.html
- **PM2监控**: http://localhost:9000
- **API服务**: http://localhost:8080

## 重要说明

1. ✅ **API服务器已包含**: okex-trading-api.js 和 sandbox-api-server.cjs
2. ✅ **完整的JSONL存储系统**
3. ✅ **独立的PM2监控系统**
4. ✅ **完整的路由配置**
5. ✅ **所有配置文件**

## 环境变量配置

请根据 .env.example 创建 .env 文件并配置:
- OKX API credentials
- Telegram Bot配置
- 其他必要的环境变量

## 技术支持

如有问题，请查看:
- RESTORE_GUIDE.md - 详细恢复指南
- TROUBLESHOOTING.md - 故障排查
- logs/ 目录 - 系统日志

---
备份创建时间: 2026-01-19 14:22:00
备份版本: v2.0 (完整版)
状态: ✅ 包含所有API服务器和核心功能
