# 🚀 系统快速使用指南

## 📱 访问应用

### Web界面
**主URL**: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai

### 主要页面
- 首页: `/`
- 仪表板: `/dashboard`
- 数据查询: `/query`
- 交易决策: `/trading-decision`
- 交易管理: `/trading-manager`
- 锚点监控: `/anchor-auto-monitor`

## 🔌 API使用

### 1. 恐慌指数API
```bash
curl "https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/api/panic/latest"
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "panic_index": 0.0808,
    "panic_level": "低恐慌",
    "wash_index": 1.297,
    "level_color": "green",
    "total_position": 102.81,
    "hour_24_people": 8.31,
    "hour_24_amount": 13337.92
  }
}
```

### 2. 锚点系统持仓API
```bash
curl "https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/api/anchor-system/current-positions?trade_mode=real"
```

### 3. SAR斜率API
```bash
curl "https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/api/sar-slope/latest"
```

### 4. 图表数据API
```bash
curl "https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/api/chart"
```

## 🎛️ PM2 管理命令

### 查看所有服务状态
```bash
cd /home/user/webapp && pm2 list
```

### 查看特定服务日志
```bash
cd /home/user/webapp && pm2 logs flask-app --lines 50
cd /home/user/webapp && pm2 logs coin-price-tracker --lines 50
```

### 重启服务
```bash
cd /home/user/webapp && pm2 restart flask-app
cd /home/user/webapp && pm2 restart all
```

### 停止/启动服务
```bash
cd /home/user/webapp && pm2 stop flask-app
cd /home/user/webapp && pm2 start flask-app
```

### 查看服务详情
```bash
cd /home/user/webapp && pm2 show flask-app
```

## 📊 数据收集器

### 11个活跃的数据收集器

1. **flask-app** - Flask Web应用 (端口5000)
2. **coin-price-tracker** - 币价追踪器
3. **support-resistance-snapshot** - 支撑阻力快照
4. **price-speed-collector** - 价格速度收集器
5. **v1v2-collector** - V1V2数据收集器
6. **crypto-index-collector** - 加密指数收集器
7. **okx-day-change-collector** - OKX日变化收集器
8. **sar-slope-collector** - SAR斜率收集器
9. **liquidation-1h-collector** - 1小时清算数据收集器
10. **anchor-profit-monitor** - 锚点盈利监控
11. **escape-signal-monitor** - 逃顶信号监控

## 🔧 配置文件位置

### 应用配置
- `/home/user/webapp/configs/anchor_config.json` - 锚点系统配置
- `/home/user/webapp/configs/telegram_config.json` - Telegram配置
- `/home/user/webapp/configs/trading_config.json` - 交易配置
- `/home/user/webapp/configs/v1v2_settings.json` - V1V2设置

### PM2配置
- `/home/user/webapp/ecosystem_all_services.config.js` - 所有服务配置

## 🐛 故障排查

### 检查Flask应用日志
```bash
cd /home/user/webapp && tail -f logs/flask-app-out-0.log
cd /home/user/webapp && tail -f logs/flask-app-error-0.log
```

### 检查PM2状态
```bash
cd /home/user/webapp && pm2 status
cd /home/user/webapp && pm2 monit  # 实时监控
```

### 重启所有服务
```bash
cd /home/user/webapp && pm2 restart all
```

### 检查端口占用
```bash
netstat -tulnp | grep 5000
```

## 💡 快速技巧

### 查看实时API调用
```bash
cd /home/user/webapp && pm2 logs flask-app | grep "GET /api"
```

### 监控内存使用
```bash
cd /home/user/webapp && pm2 list | grep online
```

### 清理PM2日志
```bash
cd /home/user/webapp && pm2 flush
```

## 📞 常见问题

### Q: 如何访问Web界面？
A: 直接访问 https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai

### Q: API不响应怎么办？
A: 
1. 检查Flask应用状态: `pm2 list`
2. 查看错误日志: `pm2 logs flask-app --err`
3. 重启应用: `pm2 restart flask-app`

### Q: 数据收集器停止了怎么办？
A: 
1. 查看状态: `pm2 list`
2. 重启特定收集器: `pm2 restart <服务名>`
3. 查看日志: `pm2 logs <服务名>`

### Q: 如何更新配置？
A: 
1. 编辑配置文件: `nano configs/xxx_config.json`
2. 重启相关服务: `pm2 restart <服务名>`

## 🎉 快速开始

1. **访问Web界面**
   ```
   打开浏览器访问: https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai
   ```

2. **测试API**
   ```bash
   curl https://5000-ikmpd2up5chrwx4jjjkih-5634da27.sandbox.novita.ai/api/panic/latest
   ```

3. **查看系统状态**
   ```bash
   cd /home/user/webapp && pm2 list
   ```

就这么简单！享受使用吧！ 🎊
