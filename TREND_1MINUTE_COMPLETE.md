# 🎯 支撑压力线全局趋势采集器 - 1分钟粒度完成报告

## ✅ 修复完成时间
**2026-01-25 09:37 (北京时间)**

---

## 📊 核心变更

### 采集频率优化
```
修改前：每15分钟采集一次
修改后：每1分钟采集一次 ✅
```

### 数据密度对比
| 指标 | 修改前 (15分钟) | 修改后 (1分钟) | 提升倍数 |
|------|----------------|---------------|---------|
| 每小时数据点 | 4个 | 60个 | **15x** |
| 每天数据点 | 96个 | 1,440个 | **15x** |
| 一个月数据点 | ~2,880个 | ~43,200个 | **15x** |

---

## 🔧 技术实现

### 1️⃣ 采集器修改
**文件：** `source_code/support_resistance_trend_collector.py`

**关键修改：**
```python
# 修改前
if current_minute % 15 == 0 and current_second < 30:
    collect_trend_point()

# 修改后
if current_second < 10:
    collect_trend_point()
```

### 2️⃣ API更新
**文件：** `source_code/app_new.py`

**API端点：** `/api/support-resistance/trend`

**返回字段更新：**
```json
{
  "interval": "1 minute",
  "description": "每1分钟采集一次，每天1,440个点"
}
```

---

## 📈 实时数据验证

### 当前数据状态（09:37）
```
✅ API状态: 成功
📊 总数据点: 7
⏱️  采集间隔: 1 minute
📝 描述: 每1分钟采集一次，每天1,440个点

=== 最新5个数据点 ===
2026-01-25T09:33 | 币种:27 | 7d低:3 高:0 | 48h低:5 高:0 | 平均7d:21.9% 48h:39.5%
2026-01-25T09:34 | 币种:27 | 7d低:3 高:0 | 48h低:5 高:0 | 平均7d:21.9% 48h:39.5%
2026-01-25T09:35 | 币种:27 | 7d低:3 高:0 | 48h低:5 高:0 | 平均7d:21.9% 48h:39.5%
2026-01-25T09:36 | 币种:27 | 7d低:3 高:0 | 48h低:5 高:0 | 平均7d:21.9% 48h:39.5%
2026-01-25T09:37 | 币种:27 | 7d低:3 高:0 | 48h低:5 高:0 | 平均7d:21.9% 48h:39.5%
```

### 数据采集时间线
```
09:15 ← 旧的15分钟采集
09:30 ← 旧的15分钟采集
09:33 ← 新的1分钟采集 ✅
09:34 ← 新的1分钟采集 ✅
09:35 ← 新的1分钟采集 ✅
09:36 ← 新的1分钟采集 ✅
09:37 ← 新的1分钟采集 ✅
...每分钟持续采集中...
```

---

## 📊 趋势指标说明

### 采集的关键指标
| 指标名称 | 说明 | 用途 |
|---------|------|------|
| `total_coins` | 监控的总币种数量 | 确认数据完整性（27个） |
| `scenario_1_count` | 7日低位币种数量（≤10%） | 买入信号 |
| `scenario_2_count` | 7日高位币种数量（≥90%） | 卖出信号 |
| `scenario_3_count` | 48h低位币种数量（≤10%） | 短期买入 |
| `scenario_4_count` | 48h高位币种数量（≥90%） | 短期卖出 |
| `avg_position_7d` | 7日平均位置百分比 | 整体市场情绪 |
| `avg_position_48h` | 48h平均位置百分比 | 短期波动趋势 |
| `near_support_count` | 接近支撑线数量 | 反弹机会 |
| `near_resistance_count` | 接近压力线数量 | 回调风险 |
| `escape_signal` | 逃顶信号数量 | 高位警报 |
| `buy_signal` | 买入信号数量 | 低位机会 |
| `sell_signal` | 卖出信号数量 | 高位提示 |

---

## 🌐 访问地址

### API端点
**全局趋势数据（1分钟粒度）：**
```
https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/api/support-resistance/trend?days=30
```

**参数说明：**
- `days` - 查询最近N天的数据（默认30天）
- `month` - 指定月份YYYYMM（可选）

**示例：**
```bash
# 查询最近1天
curl "https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/api/support-resistance/trend?days=1"

# 查询2026年1月全部数据
curl "https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/api/support-resistance/trend?month=202601"
```

### 前端页面
**旧版页面：**
```
https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/support-resistance
```

**新版页面 v2.0：**
```
https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/support-resistance-v2
```

---

## 📁 数据存储

### 文件路径
```
/home/user/webapp/data/support_resistance_trend/
├── support_resistance_trend_202601.jsonl  (当前月数据)
└── support_resistance_trend_YYYYMM.jsonl  (历史月份)
```

### 文件格式（JSONL）
每行一个JSON对象：
```json
{
  "timestamp": "2026-01-25T09:37:00.123456+08:00",
  "date": "2026-01-25",
  "time": "09:37",
  "total_coins": 27,
  "scenario_1_count": 3,
  "scenario_2_count": 0,
  "scenario_3_count": 5,
  "scenario_4_count": 0,
  "avg_position_7d": 21.9,
  "avg_position_48h": 39.5,
  "near_support_count": 23,
  "near_resistance_count": 1,
  "escape_signal": 5,
  "buy_signal": 8,
  "sell_signal": 0
}
```

---

## 🚀 数据积累预测

### 数据增长时间表
| 时间段 | 预计数据点数 | 文件大小估算 | 可视化效果 |
|--------|-------------|-------------|-----------|
| **1小时后** | ~60点 | ~15KB | 可见短期趋势 |
| **6小时后** | ~360点 | ~90KB | 日内波动清晰 |
| **1天后** | ~1,440点 | ~360KB | 完整日度分析 |
| **1周后** | ~10,080点 | ~2.5MB | 周度模式识别 |
| **1月后** | ~43,200点 | ~10.8MB | 完整月度全景 |

### 历史数据回填（可选）
如需回填历史数据（从2025-12-25至今），可参考以下方案：
1. 从每日数据文件中每15分钟取一个点
2. 或从每日数据中均匀采样到1分钟粒度
3. 预计回填数据量：31天 × 1,440点 = ~44,640点

---

## 🎨 前端可视化建议

### 推荐图表类型（ECharts）

#### 1. 场景统计趋势图（折线图）
```javascript
{
  xAxis: { type: 'time' },
  yAxis: { type: 'value' },
  series: [
    { name: '7日低位', data: scenario_1_count },
    { name: '7日高位', data: scenario_2_count },
    { name: '48h低位', data: scenario_3_count },
    { name: '48h高位', data: scenario_4_count }
  ]
}
```

#### 2. 平均位置图（双Y轴）
```javascript
{
  xAxis: { type: 'time' },
  yAxis: [
    { name: '7日平均位置%', max: 100 },
    { name: '48h平均位置%', max: 100 }
  ],
  series: [
    { name: '7日位置', yAxisIndex: 0, data: avg_position_7d },
    { name: '48h位置', yAxisIndex: 1, data: avg_position_48h }
  ]
}
```

#### 3. 信号指标图（面积图）
```javascript
{
  xAxis: { type: 'time' },
  yAxis: { type: 'value' },
  series: [
    { name: '买入信号', type: 'line', areaStyle: {}, data: buy_signal },
    { name: '卖出信号', type: 'line', areaStyle: {}, data: sell_signal },
    { name: '逃顶警报', type: 'line', areaStyle: {}, data: escape_signal }
  ]
}
```

#### 4. 接近度热力图
```javascript
{
  visualMap: { min: 0, max: 27 },
  series: [{
    type: 'heatmap',
    data: [
      [time, 'near_support', near_support_count],
      [time, 'near_resistance', near_resistance_count]
    ]
  }]
}
```

---

## 🔔 告警功能建议

### 建议告警阈值
| 告警类型 | 触发条件 | 优先级 | 建议动作 |
|---------|---------|--------|---------|
| **逃顶警报** | `escape_signal >= 5` | 🔴 高 | 考虑减仓 |
| **买入机会** | `buy_signal >= 10` | 🟢 中 | 考虑建仓 |
| **市场低迷** | `avg_position_7d < 20%` | 🟡 低 | 关注反弹 |
| **市场过热** | `avg_position_7d > 80%` | 🟡 低 | 警惕回调 |
| **短期超卖** | `scenario_3_count >= 10` | 🟢 中 | 短线机会 |
| **短期超买** | `scenario_4_count >= 10` | 🔴 高 | 短线风险 |

---

## ⚙️ 系统运行状态

### PM2进程管理
```bash
✅ support-resistance-collector   (每30分钟采集27币种)
✅ support-resistance-snapshots   (每60秒快照统计)
✅ support-resistance-trend       (每1分钟趋势数据) ← 新频率
```

### 查看进程状态
```bash
cd /home/user/webapp
pm2 list
pm2 logs support-resistance-trend --lines 50
```

### 手动采集（测试用）
```bash
cd /home/user/webapp
python3 -c "from source_code.support_resistance_trend_collector import collect_trend_point; collect_trend_point()"
```

---

## 📝 Git状态

### 代码提交
- **分支：** `genspark_ai_developer`
- **提交哈希：** `2c979f4`
- **提交信息：** "feat: 全局趋势采集间隔从15分钟改为1分钟"

### PR链接
**https://github.com/jamesyidc/121211111/pull/1**

### 主要变更文件
```
modified:   source_code/support_resistance_trend_collector.py
modified:   source_code/app_new.py
```

---

## ✨ 项目完成度

### 核心功能
- ✅ 27个币种实时监控
- ✅ 支撑压力线计算（7日 + 48h）
- ✅ 按日期存储JSONL数据
- ✅ 每30分钟采集币种数据
- ✅ 每60秒快照统计
- ✅ **每1分钟全局趋势采集** ← 新增
- ✅ 完整API接口
- ✅ 旧版页面修复
- ✅ 新版页面v2.0上线

### 数据完整性
- ✅ 数据库完全脱离（0%依赖）
- ✅ JSONL数据源100%覆盖
- ✅ 27天历史数据（2025-12-25至今）
- ✅ 实时数据更新
- ✅ **1分钟粒度趋势数据** ← 新增

---

## 🎉 总结

### 本次修复要点
1. ✅ **采集频率：** 15分钟 → 1分钟（15倍提升）
2. ✅ **数据密度：** 每天96点 → 1,440点
3. ✅ **月度数据：** 2,880点 → 43,200点
4. ✅ **时间轴支持：** 满足1分钟粒度图表需求
5. ✅ **API更新：** 返回正确的采集间隔描述
6. ✅ **实时验证：** 已成功采集5个1分钟数据点

### 数据可用性
- **当前数据点：** 7个（09:15至09:37）
- **持续增长：** 每分钟新增1个数据点
- **1小时后：** 将有60+个数据点可供分析
- **1天后：** 将有1,440个数据点，可绘制完整日度趋势图

### 下一步建议
1. **前端开发：** 创建趋势可视化页面（ECharts）
2. **数据积累：** 等待24小时以获得更完整的数据
3. **告警系统：** 实现实时告警功能
4. **历史回填：** 可选地回填历史数据到1分钟粒度

---

## 📞 联系方式

如有问题或需要进一步优化，请随时反馈！

**完成时间：** 2026-01-25 09:37 (北京时间)  
**项目状态：** ✅ 全部完成并正常运行
