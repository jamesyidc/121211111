# 🎉 极值追踪系统首页集成完成 - 用户使用指南

## ✅ 完成状态
**所有功能已成功集成并运行！**

---

## 🌐 访问链接

### 1. 首页
**URL**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai

在首页你可以看到：
- ⚠️ **极值追踪系统**卡片（红色渐变背景）
- 显示快照总数、活跃快照、已完成快照和触发类型统计
- 点击"查看追踪 🔥"按钮进入详情页

### 2. 极值追踪系统页面
**URL**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/extreme-tracking

这是专门的极值追踪系统页面，包含：
- 🏠 **返回首页按钮**（左上角蓝色按钮）
- 统计卡片区（快照总数、活跃快照、已完成快照、触发类型统计）
- 快照列表（可筛选：全部/活跃中/已完成）
- 详细的快照信息和价格追踪数据

### 3. API接口

#### 统计数据API
```
GET https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/api/extreme-tracking/stats
```

#### 快照列表API
```
GET https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/api/extreme-tracking/snapshots
```

#### 活跃快照
```
GET https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/api/extreme-tracking/snapshots?status=active
```

#### 已完成快照
```
GET https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/api/extreme-tracking/snapshots?status=completed
```

---

## 🎯 5种极值触发条件

系统会自动监控并捕捉以下5种极值事件：

1. **2h_peak** (2小时峰值)
   - 触发条件：2小时逃顶信号峰值 > 50
   - 监控数据：/api/escape-signal-stats

2. **27coins_high** (27币涨幅超100%)
   - 触发条件：27个币种涨跌幅总和 > 100%
   - 监控数据：/api/okx-day-change/latest

3. **27coins_low** (27币跌幅低于-80%)
   - 触发条件：27个币种涨跌幅总和 < -80%
   - 监控数据：/api/okx-day-change/latest

4. **24h_peak** (24小时峰值)
   - 触发条件：24小时逃顶信号峰值 > 200
   - 监控数据：/api/escape-signal-stats

5. **1h_liquidation_high** (1小时爆仓超3000万)
   - 触发条件：1小时爆仓金额 > 3000万美元
   - 监控数据：/api/panic/latest

---

## 🔥 核心特性

### 4小时冷却期
- 同一类型的极值事件在4小时内只会触发一次
- 避免短时间内重复捕获相同事件
- 冷却状态保存在数据库中

### 价格追踪机制
当极值事件触发时，系统会：
1. 📸 **创建快照** - 记录27个币种的当前价格、涨跌幅、成交量
2. ⏱️ **追踪价格** - 在1h/3h/6h/12h/24h这5个时间点记录价格变化
3. 📊 **生成报告** - 计算总涨跌幅和各时间段的价格波动
4. ✅ **标记完成** - 24小时后将快照标记为已完成

### 实时数据展示
- 页面每30秒自动刷新统计数据
- 支持筛选查看不同状态的快照
- 颜色标识：
  - 🟢 涨幅/完成状态
  - 🔴 跌幅
  - 🟡 活跃状态

---

## 📱 使用流程

### 第一步：访问首页
1. 打开首页链接：https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai
2. 向下滚动找到 "⚠️ 极值追踪系统" 卡片
3. 查看当前统计数据

### 第二步：查看详情
1. 点击卡片或"查看追踪 🔥"按钮
2. 进入极值追踪系统页面
3. 查看详细的快照列表

### 第三步：筛选快照
1. 点击顶部的筛选按钮（全部/活跃中/已完成）
2. 查看不同状态的快照
3. 展开快照卡片查看详细追踪数据

### 第四步：返回首页
1. 点击左上角的 "🏠 返回首页" 按钮
2. 或在API文档区点击"查看详情 →"按钮

---

## 🔍 页面功能说明

### 首页卡片
- **快照总数**: 累计捕获的极值事件总数
- **活跃快照**: 正在追踪中的事件（未满24小时）
- **已完成**: 已完成24小时追踪的事件
- **触发类型**: 各类型事件的数量统计

### 极值追踪页面

#### 统计卡片区
- 4个统计卡片展示关键指标
- 触发类型统计网格显示各类型计数

#### 快照列表区
- 筛选按钮：全部 | 活跃中 | 已完成
- 快照卡片展示：
  - 快照ID和触发时间
  - 状态标签（活跃中/已完成）
  - 触发类型标签
  - 27币总涨跌幅
  - 逃顶信号数据
  - 爆仓金额（如有）
  - 价格追踪表（1h/3h/6h/12h/24h）

---

## 📊 API响应示例

### 统计数据API
```json
{
  "success": true,
  "stats": {
    "total_snapshots": 5,
    "active_snapshots": 2,
    "completed_snapshots": 3,
    "trigger_types": {
      "2h_peak": 2,
      "27coins_high": 1,
      "1h_liquidation_high": 2
    }
  }
}
```

### 快照列表API
```json
{
  "success": true,
  "data": [
    {
      "snapshot_id": "EXT_20260118_150000",
      "trigger_time": 1705590000,
      "trigger_datetime": "2026-01-18 15:00:00",
      "status": "active",
      "triggers": [
        {
          "type": "2h_peak",
          "value": 52
        }
      ],
      "coins_snapshot": {
        "total_change": 15.67,
        "coins": [...]
      },
      "tracking": {
        "1h": {
          "total_change": 2.34,
          "status": "completed"
        }
      }
    }
  ],
  "count": 1
}
```

---

## 🚀 后台运行状态

### PM2进程监控
- **进程名**: extreme-value-tracker
- **状态**: ✅ 在线运行
- **内存占用**: ~43 MB
- **检查周期**: 每10分钟
- **日志位置**: logs/extreme_tracker_out.log

### 数据存储
- **快照文件**: data/extreme_tracking/extreme_snapshots.jsonl
- **冷却文件**: data/extreme_tracking/trigger_cooldown.jsonl
- **格式**: JSONL (每行一个JSON对象)

---

## 💡 重要提示

### 当前状态
- ✅ 系统已启动并正常运行
- ✅ 首页集成完成
- ✅ 极值追踪页面可访问
- ✅ 返回首页按钮正常工作
- ✅ API端点正常响应
- ⏳ 等待第一个极值事件触发

### 注意事项
1. **页面自动刷新**: 每30秒自动更新数据，无需手动刷新
2. **冷却期机制**: 同一类型事件4小时内只触发一次
3. **追踪周期**: 快照创建后需要24小时才能完成追踪
4. **数据格式**: 所有时间均为北京时间 (UTC+8)

---

## 📞 技术支持

### 查看日志
```bash
# 查看极值追踪器日志
pm2 logs extreme-value-tracker

# 查看Flask应用日志
pm2 logs flask-app

# 查看所有进程状态
pm2 status
```

### 重启服务
```bash
# 重启极值追踪器
pm2 restart extreme-value-tracker

# 重启Flask应用
pm2 restart flask-app

# 重启所有服务
pm2 restart all
```

---

## 🎯 下一步建议

1. **持续监控**: 观察极值追踪器的运行日志，等待第一个事件触发
2. **数据验证**: 当有极值事件时，验证快照创建和追踪逻辑是否正确
3. **性能优化**: 如快照数量增多，考虑添加分页和搜索功能
4. **告警集成**: 可考虑集成Telegram通知，实时推送极值事件

---

## ✨ 总结

极值追踪系统已完整集成到首页，并提供独立的详情页面。系统现已具备：

- ✅ 完整的前端界面和交互
- ✅ 返回首页的导航功能
- ✅ 实时数据展示和自动刷新
- ✅ 5种极值触发条件监控
- ✅ 27币价格追踪机制
- ✅ 4小时冷却期保护
- ✅ PM2后台稳定运行

**系统已就绪，正在持续监控市场，等待极值事件触发！** 🚀

---

*创建时间: 2026-01-18 15:20 UTC*
*版本: 极值追踪系统 v1.1*
*作者: Claude Code Agent*
