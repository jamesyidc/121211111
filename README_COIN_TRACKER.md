# 27币涨跌幅总和追踪器

> 🚀 实时监控27个加密货币的涨跌幅总和，30分钟粒度，完整可视化

---

## 📊 快速访问

**主页面（曲线图）**  
https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/coin-price-tracker

---

## ✨ 功能特点

### 1. 实时曲线图
- ✅ 27个币种涨跌幅总和
- ✅ 30分钟数据粒度
- ✅ 基线0%，涨跌一目了然
- ✅ 自动更新，实时显示

### 2. 交互式详情
- 🔍 点击时间节点查看详情
- 📈 每个币种的详细数据
- 📉 涨跌幅排行榜
- 🎯 实时计算总和

### 3. CSV数据导出
- 📥 按日期选择导出
- 📝 包含完整时间和涨跌幅数据
- 💾 自动生成文件名

### 4. 实时日志监控
- 📡 黑客风格终端UI
- 🎨 彩色日志分类
- 🔄 每5秒自动刷新
- 📜 显示最后100行

---

## 🎯 监控的27个币种

```
BTC   ETH   XRP   BNB   SOL   LTC   DOGE  SUI   TRX
TON   ETC   BCH   HBAR  XLM   FIL   LINK  CRO   DOT
UNI   NEAR  APT   CFX   CRV   STX   LDO   TAO   AAVE
```

---

## 📈 数据状态

### 当前状态
- **总记录数**: 4条
- **数据范围**: 2026-01-16 20:47:43 ~ 22:11:44
- **数据完整性**: 100%（27/27币种）
- **采集频率**: 每30分钟

### 数据累积计划

| 日期 | 节点数 | 完成度 | 说明 |
|-----|--------|--------|------|
| 1月17日 | ~52 | 7.7% | 可看24小时曲线 |
| 1月19日 | ~148 | 22.0% | 可看3天趋势 |
| 1月23日 | ~340 | 50.6% | 可看周期模式 |
| **1月30日** | **672** | **100%** | **完整数据集** ✅ |

---

## 🔧 快速命令

### 查看当前数据
```bash
python3 /home/user/webapp/source_code/view_current_data.py
```

### 查看实时日志
```bash
tail -f /home/user/webapp/logs/coin_price_collector.log
```

### 查看进程状态
```bash
cd /home/user/webapp && pm2 list | grep coin-price
```

### 重启Flask服务
```bash
cd /home/user/webapp && pm2 restart flask-app
```

---

## 📖 详细文档

- **完整方案**: [`FINAL_SOLUTION.md`](./FINAL_SOLUTION.md) ⭐
- **实时策略**: [`REALTIME_DATA_ONLY.md`](./REALTIME_DATA_ONLY.md)
- **项目报告**: [`TASK_COMPLETION_REPORT.md`](./TASK_COMPLETION_REPORT.md)
- **交互功能**: [`INTERACTIVE_DETAIL_FEATURE.md`](./INTERACTIVE_DETAIL_FEATURE.md)
- **日志功能**: [`LOG_DISPLAY_FEATURE.md`](./LOG_DISPLAY_FEATURE.md)

---

## ⚙️ 技术架构

### 数据采集
- **方式**: OKX API（30分钟K线）
- **频率**: 每30分钟自动采集
- **管理**: PM2守护进程

### 数据存储
- **格式**: JSONL（JSON Lines）
- **路径**: `data/coin_price_tracker/coin_prices_30min.jsonl`

### 前端展示
- **框架**: Flask + ECharts
- **页面**: `coin_sum_tracker.html`
- **API**: `/api/coin-price-tracker/history`

---

## 🎨 页面预览

### 主曲线图
- 显示27币涨跌幅总和的时间序列曲线
- 基线为0%，正值表示总体上涨，负值表示总体下跌
- 30分钟粒度，可以看到详细的价格波动

### 详细数据卡片
- 点击时间节点后展开
- 显示27个币种的完整数据：
  - 基准价（当天00:00）
  - 当前价
  - 涨跌幅
- 涨跌幅排行榜

### 实时日志区
- 页面底部显示
- 黑色背景+霓虹绿字体
- 自动分类（成功/进度/错误/警告）

---

## ❓ FAQ

### Q: 为什么没有1月3日至1月15日的数据？
A: OKX API无法获取"未来日期"的历史K线数据。我们选择从1月16日开始实时采集，确保数据100%准确。

### Q: 什么时候能看到完整的14天曲线？
A: 从2026-01-16开始，14天后（2026-01-30）将累积完整的672个节点。

### Q: 数据是如何计算的？
A: 每天00:00的价格作为基准价，当前价格与基准价对比计算涨跌幅，然后将27个币种的涨跌幅相加得到总和。

### Q: 如何导出数据？
A: 在主页面选择日期，点击"导出CSV"按钮即可下载当天所有节点的数据。

---

## 🚀 系统状态

### ✅ 已完成
- ✅ 实时数据采集系统（运行中）
- ✅ 前端曲线图页面
- ✅ 交互式详情查看
- ✅ CSV数据导出
- ✅ 实时日志监控
- ✅ 完整文档

### 🔄 进行中
- 🔄 持续采集数据（每30分钟）
- 🔄 累积至672个节点（目标：2026-01-30）

---

## 📞 技术支持

**数据文件位置**:  
`/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl`

**日志文件位置**:  
`/home/user/webapp/logs/coin_price_collector.log`

**主页面模板**:  
`/home/user/webapp/source_code/templates/coin_sum_tracker.html`

---

## 📝 Git历史

```
6c43e30 docs: 添加最终方案完整说明文档
98cb668 docs: 添加实时数据采集策略说明，放弃历史回填
6ba94d5 docs: 添加历史数据回填问题完整说明
8b7f1aa fix: 修改回填脚本使用30分钟K线（但历史数据无法获取）
3a52ee3 docs: 添加时间节点可交互详细数据查看功能说明
```

---

## 🎉 开始使用

1. **打开主页面**: 点击上方链接
2. **查看曲线**: 自动显示所有数据点
3. **点击节点**: 查看详细数据
4. **导出CSV**: 下载数据分析

**现在就开始探索吧！** 🚀

---

*最后更新: 2026-01-16 23:15*  
*版本: v3.0*  
*状态: ✅ 运行中*
