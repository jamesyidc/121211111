# 实时交易系统完整备份

## 📦 备份信息

**备份时间**: 2026-01-19 13:35:29
**备份版本**: V6.2 (JSONL + PM2监控)
**备份类型**: 完整系统备份

## 📁 备份内容

### 1. 前端文件 (public/)
- live-trading-v2.html - 主界面
- live-trading-v2.js - 主逻辑
- live-trading*.html/js - 其他版本

### 2. JSONL存储系统
- data/trading/*.jsonl - 数据文件
- src/services/jsonlStorageService.ts - 存储服务
- src/services/liveTradingStorageAdapter.ts - 适配器
- scripts/migrate-to-jsonl.cjs - 迁移脚本

### 3. 后端路由
- src/routes/liveTradingRoutes.ts
- src/routes/liveTradingRoutesV2.ts
- functions/api/live-trading/ - Workers函数

### 4. PM2配置
- ecosystem.config.cjs - 主配置
- ecosystem.pm2-monitor.config.cjs - 监控配置
- pm2-monitor-server.cjs - 监控服务器

### 5. 交易服务
- tradingAccountService.ts - 账户服务
- tradingRuleService.ts - 规则服务
- tradingSignalService.ts - 信号服务
- tradingScheduler.ts - 调度服务

### 6. 数据库和工具
- trading.db - SQLite数据库
- okex-trading-api.js - OKX API
- okxAPIHelper.ts - API辅助工具

### 7. 配置文件
- package.json - 依赖配置
- tsconfig.json - TypeScript配置
- wrangler.jsonc - Cloudflare配置
- .env.example - 环境变量示例

## 🔄 恢复步骤

1. **解压备份文件**
   ```bash
   tar -xzf live-trading-system-backup-YYYYMMDD.tar.gz
   cd live-trading-system
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **恢复JSONL数据**
   ```bash
   cp -r data/trading /home/user/webapp/data/
   ```

4. **配置PM2**
   ```bash
   pm2 start ecosystem.config.cjs
   pm2 start ecosystem.pm2-monitor.config.cjs
   pm2 save
   ```

5. **启动服务**
   ```bash
   npm run dev          # Vite开发服务器
   npm run dev:sandbox  # Wrangler服务器
   ```

## 📝 注意事项

1. 恢复前备份现有数据
2. 检查环境变量配置
3. 确认端口未被占用 (3000, 8080, 9000)
4. 验证OKX API密钥配置

## 🔗 访问地址

- 实时交易: http://localhost:3000/live-trading-v2.html
- PM2监控: http://localhost:9000
- API服务: http://localhost:8080

## 📞 技术支持

参考项目文档:
- SYSTEM_UPGRADE_20260119.md
- RESTORE_DEPLOYMENT_20260119.md
- QUICK_GUIDE.md

