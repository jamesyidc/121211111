# 🚀 快速访问指南

## 📊 主页面
**27币涨跌幅总和追踪器（1月10-16日，北京时间）**

🔗 **访问地址：**
```
https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/coin-price-tracker
```

---

## ✨ 功能特性

### 1️⃣ 查看曲线图
- 自动显示1月10-16日的27币涨跌幅总和曲线
- X轴：时间（MM-DD HH:MM，北京时间 UTC+8）
- Y轴：27币涨跌幅总和（%）
- 基线：0%
- 数据点：336个（7天 × 48节点/天）

### 2️⃣ 查看每日详细
1. 从下拉框选择日期（1月10-16日）
2. 点击"🔍 查看当日详细"
3. 查看该日48个时间点的数据

### 3️⃣ 查看币种详情
1. 在每日详细表格中找到想查看的时间点
2. 点击"📊 查看27币详情"
3. 查看该时间点所有27个币种的：
   - 基准价格（当日00:00）
   - 当前价格
   - 涨跌幅

### 4️⃣ 导出CSV
- 点击"📥 导出CSV"按钮
- 自动下载文件：`coin_sum_2026-01-10_to_2026-01-16_BeijingTime.csv`
- 包含字段：
  - 时间（北京时间）
  - 27币涨跌幅总和(%)

### 5️⃣ 实时日志
- 页面底部显示数据采集实时日志
- 自动每5秒刷新
- 显示最后100行日志
- 可以手动刷新/暂停/清空

---

## 📈 数据说明

### 时间范围
- **开始：** 2026-01-10 00:00:00（北京时间 UTC+8）
- **结束：** 2026-01-16 23:30:00（北京时间 UTC+8）
- **粒度：** 30分钟
- **总节点：** 336个

### 币种列表（27个）
```
BTC, ETH, XRP, BNB, SOL, LTC, DOGE, SUI, 
TRX, TON, ETC, BCH, HBAR, XLM, FIL, LINK, 
CRO, DOT, UNI, NEAR, APT, CFX, CRV, STX, 
LDO, TAO, AAVE
```

### 数据来源
- **交易所：** OKX
- **合约类型：** 永续合约（USDT结算）
- **数据接口：** OKX API `/market/candles`
- **更新频率：** 每30分钟自动采集

### 涨跌幅计算
- **基准价：** 每日00:00:00的K线收盘价（北京时间）
- **当前价：** 当前时间点的K线收盘价
- **涨跌幅：** `(当前价 - 基准价) / 基准价 × 100%`
- **总和：** 27个币种涨跌幅相加

---

## ⚠️ 重要提示

### ✅ 可用数据
- **1月10-16日：** 完整数据，100%准确
- **总节点数：** 336个
- **数据完整性：** ✅ 100%

### ❌ 不可用数据
- **1月3-9日：** 因OKX API限制，无法获取
- **原因：** OKX历史数据仅保留最近约6.2天
- **影响：** 无法回填这7天的数据

### 🔄 实时采集
- **状态：** ✅ 运行中
- **频率：** 每30分钟自动采集
- **下次采集：** 自动触发
- **数据累积：** 持续增长

---

## 🔧 系统监控

### 检查PM2状态
```bash
cd /home/user/webapp && pm2 status
```

### 查看数据文件
```bash
cd /home/user/webapp && wc -l data/coin_price_tracker/coin_prices_30min.jsonl
```

### 查看采集日志
```bash
cd /home/user/webapp && pm2 logs coin-price-tracker --nostream | tail -20
```

### 重启服务
```bash
cd /home/user/webapp && pm2 restart flask-app
cd /home/user/webapp && pm2 restart coin-price-tracker
```

---

## 📝 相关文档

### 详细报告
```
/home/user/webapp/FINAL_BACKFILL_REPORT.md
```

### 项目README
```
/home/user/webapp/README_COIN_TRACKER.md
```

### 数据文件
```
/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl
```

---

## 🎯 快速验证

### 测试API
```bash
cd /home/user/webapp && curl -s "http://localhost:5000/api/coin-price-tracker/history?start_time=2026-01-10%2000:00:00&end_time=2026-01-16%2023:30:00" | jq '.data | length'
```

### 测试页面
```bash
cd /home/user/webapp && curl -s "http://localhost:5000/coin-price-tracker" | grep "title"
```

---

## 💡 使用建议

### 1. 数据分析
- 观察27币涨跌幅总和的趋势
- 找出极值时间点
- 分析单币种贡献

### 2. 导出数据
- 定期导出CSV备份
- 用Excel/Python进一步分析
- 制作自定义图表

### 3. 实时监控
- 关注页面底部日志
- 检查数据采集状态
- 及时发现问题

---

**最后更新：** 2026-01-16 23:50（北京时间 UTC+8）  
**系统状态：** ✅ 正常运行  
**数据完整性：** ✅ 100%（336/336节点）

🎉 **享受数据分析！**
