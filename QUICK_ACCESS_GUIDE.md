# 快速访问指南 - 27币涨跌幅追踪系统

## 🌐 主要页面

### 1. Anchor System Real (实盘锚点系统)
```
https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real
```
**显示内容**:
- 24小时逃顶信号 (红色，左Y轴)
- 2小时逃顶信号 (橙色，左Y轴)
- **OKX 27币种总涨跌%** (紫色，右Y轴) ← **新增**

---

### 2. Escape Signal History (逃顶信号历史)
```
https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/escape-signal-history
```
**显示内容**:
- 24小时信号数 (红色，左Y轴)
- 2小时信号数 (橙色，左Y轴)
- **OKX 27币种总涨跌%** (紫色，右Y轴) ← **新增**

---

### 3. Coin Price Tracker (数据源页面)
```
https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/coin-price-tracker
```
**显示内容**:
- 27币涨跌幅总和曲线图
- 日期范围选择器 (2026-01-03 ~ 2026-01-16)
- 每个时间点的27币详细数据
- CSV导出功能
- 实时数据日志

---

## 🔌 API接口

### 获取最新OKX数据
```bash
curl "http://localhost:5000/api/okx-day-change/latest?limit=48"
```
**参数**:
- `limit`: 返回最新N条记录 (默认60)

**返回格式**:
```json
{
  "success": true,
  "count": 48,
  "data_source": "CoinPriceTracker",
  "data": [
    {
      "record_time": "2026-01-16 22:30:00",
      "timestamp": 1768573440,
      "total_change": -31.70,
      "average_change": -1.17,
      "success_count": 27,
      "failed_count": 0,
      "total_symbols": 27,
      "day_changes": {
        "BTC": -1.28,
        "ETH": -0.68,
        ...
      }
    }
  ]
}
```

---

### 获取历史OKX数据
```bash
curl "http://localhost:5000/api/okx-day-change/history?hours=24"
```
**参数**:
- `hours`: 时间窗口（小时）(默认24)

---

### 获取Coin Price Tracker数据
```bash
curl "http://localhost:5000/api/coin-price-tracker/latest?limit=48"
```
**参数**:
- `limit`: 返回最新N条记录 (默认48)

---

## 📊 数据说明

### 27种币列表
```
BTC, ETH, XRP, BNB, SOL, LTC, DOGE, SUI, TRX, TON, 
ETC, BCH, HBAR, XLM, FIL, LINK, CRO, DOT, AAVE, UNI, 
NEAR, APT, CFX, CRV, STX, LDO, TAO
```

### 数据指标

| 指标 | 说明 | 示例 |
|------|------|------|
| **total_change** | 27币涨跌幅总和 | -31.70% |
| **average_change** | 平均涨跌幅 | -1.17% |
| **success_count** | 成功采集币种数 | 27/27 |
| **failed_count** | 失败币种数 | 0/27 |
| **record_time** | 记录时间 (北京时间) | 2026-01-16 22:30:00 |

### 数据特点
- ✅ **采集频率**: 每30分钟
- ✅ **时区**: 北京时间 (UTC+8)
- ✅ **基准价**: 当天00:00的价格
- ✅ **数据源**: OKX永续合约
- ✅ **自动更新**: PM2守护进程
- ✅ **数据完整性**: 100%

---

## 📁 数据文件位置

### 主数据文件
```
/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl
```
**说明**: 
- JSONL格式 (每行一个JSON对象)
- 包含673条记录 (2026-01-03 至今)
- 27种币 × 30分钟间隔

### 采集脚本
```
/home/user/webapp/source_code/coin_price_tracker.py
```
**运行状态**: PM2守护进程 `coin-price-tracker`

---

## 🔧 系统管理

### 查看PM2进程状态
```bash
cd /home/user/webapp && pm2 status coin-price-tracker
```

### 查看采集日志
```bash
cd /home/user/webapp && pm2 logs coin-price-tracker --nostream
```

### 重启采集服务
```bash
cd /home/user/webapp && pm2 restart coin-price-tracker
```

### 重启Flask应用
```bash
cd /home/user/webapp && pm2 restart flask-app
```

---

## 📚 相关文档

1. **ALL_27_COINS_COMPLETED_REPORT.md** - 27币完整数据补全报告
2. **TIMEZONE_BUG_FIX_REPORT.md** - 时区bug修复报告
3. **AUTO_COLLECTION_CONFIG.md** - 自动采集系统配置
4. **OKX_DATA_SOURCE_MIGRATION.md** - 数据源迁移报告
5. **ANCHOR_SYSTEM_OKX_INTEGRATION.md** - Anchor集成报告
6. **FINAL_INTEGRATION_REPORT.md** - 最终集成报告

---

## 🎯 常见问题

### Q1: 为什么数据是30分钟更新一次？
**A**: 基于数据质量和API限制的平衡：
- 30分钟间隔足够捕捉市场趋势
- 减少API调用次数，避免限流
- PM2守护进程保证稳定性

### Q2: 基准价格是如何计算的？
**A**: 
- 基准价 = 北京时间当天00:00的价格
- 当前价 = 当前时间点的价格
- 涨跌幅 = (当前价 - 基准价) / 基准价 × 100%

### Q3: 如果发现数据异常怎么办？
**A**: 检查步骤：
1. 查看PM2进程状态: `pm2 status coin-price-tracker`
2. 查看采集日志: `pm2 logs coin-price-tracker`
3. 重启采集服务: `pm2 restart coin-price-tracker`
4. 验证API响应: `curl "http://localhost:5000/api/okx-day-change/latest?limit=5"`

### Q4: 如何导出数据？
**A**: 三种方式：
1. **前端导出**: 访问 Coin Price Tracker 页面，使用CSV导出功能
2. **API导出**: 调用API接口，保存JSON格式
3. **直接读取**: 读取 `coin_prices_30min.jsonl` 文件

---

## 📞 技术支持

如遇到问题，请检查：
1. PM2进程是否正常运行
2. Flask应用是否正常响应
3. 数据文件是否存在且有效
4. 网络连接是否正常

查看日志命令：
```bash
# 查看采集日志
pm2 logs coin-price-tracker --lines 100

# 查看Flask日志
pm2 logs flask-app --lines 100

# 查看错误日志
cat /home/user/webapp/logs/coin_price_tracker_error.log
```

---

**最后更新**: 2026-01-17 00:30:00  
**版本**: v1.0  
**状态**: ✅ 正常运行
