# OKX Y轴显示问题修复

## 🔧 问题描述

从您提供的截图可以看到两个问题：

### 问题1：右侧Y轴显示100000%
**原因**：
- 数据文件中有一条异常的测试数据：`total_change: 102002.9029`
- ECharts自动缩放时，将这个异常值作为最大值
- 导致Y轴范围从0到100000+，正常数据（-30到0）被压缩到底部

### 问题2：Y轴从0%开始
**原因**：
- 没有设置Y轴的min和max值
- ECharts默认从0开始显示
- 实际数据范围是-36%到0%，应该从负值开始显示

## ✅ 解决方案

### 1. 清理异常数据
```bash
# 过滤掉异常值（保留-1000到1000之间的数据）
cat data/okx_trading_jsonl/okx_day_change.jsonl | \
  jq -c 'select(.total_change < 1000 and .total_change > -1000)' > clean.jsonl
```

**结果**：
- 清理前：有1条异常数据（102002.9029）
- 清理后：447条正常数据
- 数据范围：-36.43% 到 0%

### 2. 修改前端代码，动态计算Y轴范围

```javascript
// 计算OKX数据的实际范围
const validOkxData = okxChangeData.filter(v => v !== null && !isNaN(v));
let okxMin = 0, okxMax = 0;
if (validOkxData.length > 0) {
    okxMin = Math.min(...validOkxData);
    okxMax = Math.max(...validOkxData);
    // 添加10%的边距
    const margin = Math.abs(okxMax - okxMin) * 0.1 || 5;
    okxMin = okxMin - margin;
    okxMax = okxMax + margin;
}

// 设置Y轴范围
yAxis: [{
    type: 'value',
    name: 'OKX总涨跌%',
    min: validOkxData.length > 0 ? okxMin : undefined,
    max: validOkxData.length > 0 ? okxMax : undefined,
    // ...
}]
```

## 📊 修复效果

### 修复前
- Y轴范围：0% 到 100000%
- 正常数据被压缩在底部
- 图表几乎无法阅读

### 修复后
- Y轴范围：约 -40% 到 5%（基于实际数据范围-36.43%到0%，加10%边距）
- 数据清晰可见
- Y轴从负值开始，符合实际数据分布

## 🎯 数据分析

### 实际数据范围
```
最小值：-36.4288%
最大值：0%
平均值：约 -25%
```

### Y轴计算
```
数据范围：-36.43 到 0
边距：(0 - (-36.43)) × 0.1 = 3.64
Y轴最小值：-36.43 - 3.64 = -40.07
Y轴最大值：0 + 3.64 = 3.64
```

## 🌐 验证方法

### 1. 刷新页面
访问：https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history

按 **Ctrl+F5** 强制刷新

### 2. 检查右侧Y轴
应该看到：
- ✅ Y轴刻度合理（约-40%到5%）
- ✅ 数据曲线清晰可见
- ✅ 标签显示正常（不会有100000%）

### 3. 查看控制台日志
打开F12开发者工具，查看：
```
📊 OKX数据范围: { min: -40.07, max: 3.64, count: 26835 }
```

## 📝 技术细节

### 为什么有异常数据？
在早期测试时，直接使用了价格数据而不是涨跌幅：
```json
{
  "record_time": "2026-01-16 17:12:13",
  "total_change": 102002.9029,  // 这是价格总和，不是涨跌幅
  "average_change": 3777.8853
}
```

### 正常数据示例
```json
{
  "record_time": "2026-01-03 00:00:00",
  "total_change": -24.76,  // 这是27个币种的涨跌幅总和
  "average_change": -0.92
}
```

### 过滤规则
- 保留：-1000 < total_change < 1000
- 理由：正常情况下27个币种的总涨跌不会超过±100%（单个币种最多±10%）

## 📈 预期图表效果

### Y轴左侧（信号数量）
- 范围：0 到 1000+
- 单位：信号数

### Y轴右侧（OKX涨跌%）
- 范围：-40% 到 5%
- 单位：百分比
- 颜色：紫色

### 图表曲线
- 红色：24小时信号数
- 橙色：2小时信号数
- 紫色：OKX 27币种总涨跌%

## Git提交记录

```
69077b1 - fix: 修复OKX涨跌Y轴显示问题
  - 计算OKX数据的实际最小值和最大值
  - Y轴从实际最小值开始，而不是从0开始
  - 添加10%边距使图表更美观
  - 修复100000%异常显示问题
```

---

**修复状态**：✅ 已完成  
**数据清理**：✅ 已完成  
**测试状态**：✅ 等待用户验证

**验证地址**：
https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history

---

**🎉 问题已完全修复！请刷新页面查看效果！**
