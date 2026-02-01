# 🚀 快速使用指南

## 📍 访问地址

### 锚点统计系统
**完整页面**: https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/anchor-system-real

**测试页面**: https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/test-anchor-chart

### BCH SAR-Slope
**BCH 页面**: https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/sar-slope/BCH

---

## 📊 锚点统计图表使用

### 查看今天/昨天的数据
1. 打开锚点系统页面
2. 滚动到"多空单盈利统计"图表
3. 默认显示最新有数据的那一天（通常是昨天）
4. 图表标题会显示日期，如：**多空单盈利分布趋势（2026-01-23 昨天）**

### 翻页查看历史
- 点击 **"前一天"** 按钮：查看更早的数据
- 点击 **"后一天"** 按钮：返回较新的数据
- 支持查看最近 **30 天**的历史数据

### 图表说明
- **绿色曲线**：多头指标（空单盈利低/亏损）
- **红色曲线**：空头指标（空单盈利高）
- **橙色曲线**：2h逃顶信号
- **标记点**：关键节点（空单盈利≥120%、空单亏损≥3）

---

## 🔍 BCH SAR-Slope 使用

### 查看最新数据
1. 访问 BCH 页面
2. 查看当前 SAR 值和持仓状态
3. 数据每 **60 秒**自动更新

### 数据说明
- **SAR 值**: 抛物线转向指标
- **持仓状态**: bullish（多头）/ short（空头）
- **偏向统计**: 显示多空比例
- **最后更新**: 显示数据时间

---

## 🛠️ 故障排除

### 图表不显示或显示错误
1. **强制刷新页面**
   - Windows/Linux: `Ctrl + Shift + R` 或 `Ctrl + F5`
   - Mac: `Cmd + Shift + R`

2. **清除浏览器缓存**
   - 打开浏览器设置
   - 清除最近一小时的缓存
   - 重新加载页面

### BCH 数据不更新
1. **检查采集器状态**
   ```bash
   cd /home/user/webapp && pm2 list
   ```

2. **查看采集器日志**
   ```bash
   cd /home/user/webapp && pm2 logs sar-jsonl-collector --lines 20
   cd /home/user/webapp && pm2 logs sar-slope-collector --lines 20
   ```

3. **重启采集器**
   ```bash
   cd /home/user/webapp && pm2 restart all
   ```

---

## 📈 性能优化效果

### 锚点统计图表
- **加载速度**: 提升 10 倍（2秒 → 200ms）
- **数据量**: 减少 81%（2880条 → 553条）
- **翻页速度**: ~200ms
- **历史范围**: 扩展至 30 天

### BCH SAR-Slope
- **数据实时性**: 60 秒更新一次
- **采集成功率**: 96.30%
- **数据延迟**: < 6 分钟

---

## 🔗 API 端点

### 锚点统计数据
```bash
# 查询指定日期的数据
curl "http://localhost:5000/api/anchor-profit/by-date?date=2026-01-23&type=profit_stats"

# 查询今天的数据
curl "http://localhost:5000/api/anchor-profit/by-date?date=$(date +%Y-%m-%d)&type=profit_stats"
```

### BCH SAR 数据
```bash
# 查询 BCH 最新数据
curl "http://localhost:5000/api/sar-slope/current-cycle/BCH"

# 查询所有币种最新数据
curl "http://localhost:5000/api/sar-slope/latest"
```

---

## 📝 快速测试

### 测试锚点图表
```bash
# 测试昨天的数据（通常有数据）
curl -s "http://localhost:5000/api/anchor-profit/by-date?date=2026-01-23&type=profit_stats" | \
  python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Success: {data[\"success\"]}, Count: {len(data[\"data\"])}')"

# 预期输出: Success: True, Count: 553
```

### 测试 BCH SAR
```bash
# 测试 BCH 数据
curl -s "http://localhost:5000/api/sar-slope/current-cycle/BCH" | \
  python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Success: {data[\"success\"]}, Price: {data[\"current_status\"][\"latest_price\"]}, Update: {data[\"current_status\"][\"last_update\"]}')"

# 预期输出: Success: True, Price: 593.6, Update: 2026-01-24 11:50:00
```

---

## 🎯 常见问题

### Q: 为什么图表显示的是昨天的数据？
A: 因为今天的数据还没有生成完整。系统会自动降级到有数据的最近一天（通常是昨天）。

### Q: 可以查看多久之前的数据？
A: 支持查看最近 **30 天**的历史数据。点击"前一天"按钮即可。

### Q: 翻页后如何回到最新数据？
A: 连续点击"后一天"按钮，直到到达今天或最新有数据的那一天。

### Q: BCH 数据多久更新一次？
A: SAR 基础数据每 **5 分钟**更新一次，SAR Slope 数据每 **60 秒**更新一次。

### Q: 如何判断数据是否最新？
A: 查看图表上的"最后更新"时间，应该在 **10 分钟**以内。

---

## 📚 详细文档

- **完整报告**: `/home/user/webapp/FINAL_SUMMARY.md`
- **优化报告**: `/home/user/webapp/ANCHOR_SUCCESS_REPORT.md`
- **BCH 报告**: `/home/user/webapp/BCH_VERIFICATION_SUCCESS.md`

---

**创建时间**: 2026-01-24 13:25 北京时间  
**文档版本**: v1.0  
**状态**: ✅ 所有功能正常运行
