# 🎯 支撑压力线全局趋势API - 分层数据加载文档

## 📋 目录
- [核心设计理念](#核心设计理念)
- [API接口说明](#api接口说明)
- [使用场景](#使用场景)
- [前端实现建议](#前端实现建议)
- [性能对比](#性能对比)
- [实测案例](#实测案例)

---

## 🎨 核心设计理念

### 为什么需要分层加载？

```
问题：月度全局图一次加载43,200个数据点 → 前端卡顿
解决：全局视图采样 + 放大视图完整数据 = 性能与细节兼顾
```

### 设计方案

```
┌─────────────────────────────────────────────────────────┐
│  采集层：1分钟采集一次（用于实时统计和逃顶信号）          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│  每天1,440个点  ✅ 必须保持，用于精确计算                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  展示层：分层加载策略                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│  全局视图：15分钟采样 → 每天96点（提升性能15倍）         │
│  放大视图：1分钟完整 → 每天1,440点（保留全部细节）       │
└─────────────────────────────────────────────────────────┘
```

---

## 📡 API接口说明

### 基础信息
- **端点：** `/api/support-resistance/trend`
- **方法：** GET
- **返回：** JSON

### 请求参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `days` | int | 30 | 查询最近N天的数据 |
| `month` | string | null | 指定月份YYYYMM（可选，如202601） |
| `sample` | int | 15 | 采样间隔（分钟）<br>- `1`: 完整1分钟数据<br>- `5`: 5分钟采样<br>- `15`: 15分钟采样（默认） |
| `start` | string | null | 开始时间ISO格式（放大查看时使用）<br>例：`2026-01-25T09:00:00+08:00` |
| `end` | string | null | 结束时间ISO格式（放大查看时使用）<br>例：`2026-01-25T10:00:00+08:00` |

### 响应格式

```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2026-01-25T09:15:00+08:00",
      "date": "2026-01-25",
      "time": "09:15",
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
    },
    ...
  ],
  "count": 3,                    // 返回的数据点数量
  "total_count": 19,             // 原始数据点总数
  "days": 1,                     // 查询天数
  "sample": 15,                  // 采样间隔
  "data_source": "JSONL Trend Data",
  "interval": "15 minutes",      // 实际返回的数据间隔
  "description": "采集频率1分钟，返回间隔15 minutes",
  "is_sampled": true,            // 是否进行了采样
  "zoom_range": null             // 放大时间范围（如果有）
}
```

---

## 🎬 使用场景

### 场景1：月度全局视图（初始加载）

**需求：** 显示1个月的完整趋势，但不需要每分钟的细节

```javascript
// API调用
fetch('/api/support-resistance/trend?days=30&sample=15')
  .then(res => res.json())
  .then(data => {
    console.log('原始数据点:', data.total_count);  // 43,200个点
    console.log('返回数据点:', data.count);         // 2,880个点
    console.log('数据压缩率:', (data.count / data.total_count * 100).toFixed(1) + '%');  // 6.7%
    // 绘制图表
    drawChart(data.data);
  });
```

**效果：**
- **数据量：** 43,200点 → 2,880点（压缩93.3%）
- **加载速度：** 快速流畅
- **可见细节：** 每15分钟一个点，足够看清趋势

---

### 场景2：周度视图（中等视图）

**需求：** 显示1周的数据，需要更多细节

```javascript
// API调用
fetch('/api/support-resistance/trend?days=7&sample=5')
  .then(res => res.json())
  .then(data => {
    console.log('原始数据点:', data.total_count);  // 10,080个点
    console.log('返回数据点:', data.count);         // 2,016个点
    console.log('采样间隔:', data.interval);        // 5 minutes
    drawChart(data.data);
  });
```

**效果：**
- **数据量：** 10,080点 → 2,016点（压缩80%）
- **细节程度：** 每5分钟一个点
- **性能平衡：** 兼顾性能与细节

---

### 场景3：放大查看（完整数据）

**需求：** 用户放大查看某个时间段，需要1分钟级别的完整数据

```javascript
// 用户放大到某个时间段（例如09:00-10:00）
const startTime = '2026-01-25T09:00:00+08:00';
const endTime = '2026-01-25T10:00:00+08:00';

// API调用
fetch(`/api/support-resistance/trend?sample=1&start=${startTime}&end=${endTime}`)
  .then(res => res.json())
  .then(data => {
    console.log('返回数据点:', data.count);  // 60个点（1小时 × 60分钟）
    console.log('采样间隔:', data.interval); // 1 minute
    console.log('是否采样:', data.is_sampled);  // false
    // 绘制详细图表
    drawDetailChart(data.data);
  });
```

**效果：**
- **数据量：** 精确到分钟级别
- **细节程度：** 完整的1分钟数据
- **用途：** 精确分析某个时间段的市场变化

---

### 场景4：今日实时监控

**需求：** 监控今天的数据，实时更新

```javascript
// API调用
fetch('/api/support-resistance/trend?days=1&sample=1')
  .then(res => res.json())
  .then(data => {
    console.log('当前数据点:', data.count);
    console.log('最新数据:', data.data[data.data.length - 1]);
    drawRealtimeChart(data.data);
  });

// 每1分钟刷新一次
setInterval(() => {
  fetch('/api/support-resistance/trend?days=1&sample=1')
    .then(res => res.json())
    .then(data => updateChart(data.data));
}, 60000);
```

**效果：**
- **数据量：** 当前时间已采集的所有数据点
- **实时性：** 每分钟更新一次
- **用途：** 实时监控市场状态

---

## 🎨 前端实现建议

### ECharts分层加载完整示例

```javascript
// 1. 初始加载月度全局视图（15分钟采样）
let chart = echarts.init(document.getElementById('trend-chart'));
let currentZoom = null;

// 加载全局数据
function loadGlobalView() {
  fetch('/api/support-resistance/trend?days=30&sample=15')
    .then(res => res.json())
    .then(data => {
      const option = {
        title: {
          text: '全局趋势图（月度）',
          subtext: `采集频率:1分钟 | 显示间隔:${data.interval} | 数据点:${data.count}/${data.total_count}`
        },
        tooltip: {
          trigger: 'axis'
        },
        dataZoom: [
          {
            type: 'inside',
            start: 0,
            end: 100
          },
          {
            start: 0,
            end: 100
          }
        ],
        xAxis: {
          type: 'time',
          data: data.data.map(d => d.timestamp)
        },
        yAxis: [
          { type: 'value', name: '场景统计' },
          { type: 'value', name: '平均位置%', max: 100 }
        ],
        series: [
          {
            name: '7日低位',
            type: 'line',
            data: data.data.map(d => [d.timestamp, d.scenario_1_count])
          },
          {
            name: '7日高位',
            type: 'line',
            data: data.data.map(d => [d.timestamp, d.scenario_2_count])
          },
          {
            name: '48h低位',
            type: 'line',
            data: data.data.map(d => [d.timestamp, d.scenario_3_count])
          },
          {
            name: '48h高位',
            type: 'line',
            data: data.data.map(d => [d.timestamp, d.scenario_4_count])
          },
          {
            name: '平均7日位置',
            type: 'line',
            yAxisIndex: 1,
            data: data.data.map(d => [d.timestamp, d.avg_position_7d])
          }
        ]
      };
      chart.setOption(option);
    });
}

// 2. 监听放大事件，动态加载详细数据
chart.on('datazoom', function (params) {
  const option = chart.getOption();
  const startValue = option.dataZoom[0].startValue;
  const endValue = option.dataZoom[0].endValue;
  
  // 如果放大范围小于7天，加载1分钟完整数据
  const rangeDays = (endValue - startValue) / (24 * 3600 * 1000);
  
  if (rangeDays < 7 && currentZoom !== '1min') {
    currentZoom = '1min';
    const start = new Date(startValue).toISOString();
    const end = new Date(endValue).toISOString();
    
    fetch(`/api/support-resistance/trend?sample=1&start=${start}&end=${end}`)
      .then(res => res.json())
      .then(data => {
        console.log('加载完整数据:', data.count, '个点');
        // 更新图表数据
        updateChartWithDetailData(data.data);
      });
  } else if (rangeDays >= 7 && rangeDays < 30 && currentZoom !== '5min') {
    currentZoom = '5min';
    // 加载5分钟采样数据
    fetch(`/api/support-resistance/trend?days=${Math.ceil(rangeDays)}&sample=5`)
      .then(res => res.json())
      .then(data => {
        console.log('加载5分钟采样:', data.count, '个点');
        updateChartWithDetailData(data.data);
      });
  }
});

// 初始化
loadGlobalView();
```

---

## ⚡ 性能对比

### 数据传输量对比（30天）

| 采样间隔 | 数据点数 | JSON大小（估算） | 传输时间（估算） | 渲染时间（估算） |
|---------|---------|---------------|---------------|---------------|
| **1分钟** | 43,200 | ~10.8 MB | ~5秒（慢网络） | ~2秒 |
| **5分钟** | 8,640 | ~2.16 MB | ~1秒 | ~0.5秒 |
| **15分钟** | 2,880 | ~720 KB | ~0.3秒 | ~0.2秒 ✅ |

### 渲染性能对比（ECharts）

| 数据点数 | 初始渲染 | 交互流畅度 | 用户体验 |
|---------|---------|-----------|---------|
| **43,200** | 慢（2秒+） | 卡顿明显 | ❌ 差 |
| **8,640** | 较快（0.5秒） | 基本流畅 | ⚠️ 一般 |
| **2,880** | 快速（0.2秒） | 非常流畅 | ✅ 优秀 |

---

## 📊 实测案例

### 测试环境
- **时间：** 2026-01-25 09:50
- **原始数据：** 19个数据点（09:15 ~ 09:49，共35分钟）
- **测试API：** `http://127.0.0.1:5000/api/support-resistance/trend`

### 测试1：15分钟采样（全局视图）

**请求：**
```bash
curl "http://127.0.0.1:5000/api/support-resistance/trend?days=1&sample=15"
```

**结果：**
```json
{
  "success": true,
  "count": 3,                    // 返回3个点
  "total_count": 19,             // 原始19个点
  "interval": "15 minutes",
  "is_sampled": true,            // 已采样
  "data": [
    { "timestamp": "2026-01-25T09:15:00", "total_coins": 23 },
    { "timestamp": "2026-01-25T09:30:00", "total_coins": 23 },
    { "timestamp": "2026-01-25T09:45:00", "total_coins": 27 }
  ]
}
```

**分析：**
- 数据压缩率：(3/19) × 100% = **15.8%**
- 减少数据量：19 - 3 = **16个点**
- 性能提升：**6.3倍**

---

### 测试2：1分钟完整数据（放大视图）

**请求：**
```bash
curl "http://127.0.0.1:5000/api/support-resistance/trend?days=1&sample=1"
```

**结果：**
```json
{
  "success": true,
  "count": 19,                   // 返回19个点
  "total_count": 19,             // 原始19个点
  "interval": "1 minute",
  "is_sampled": false,           // 未采样
  "data": [
    { "timestamp": "2026-01-25T09:15:00", "total_coins": 23 },
    { "timestamp": "2026-01-25T09:30:00", "total_coins": 23 },
    { "timestamp": "2026-01-25T09:33:00", "total_coins": 27 },
    ...
    { "timestamp": "2026-01-25T09:49:00", "total_coins": 27 }
  ]
}
```

**分析：**
- 返回完整数据：**100%**
- 细节程度：**最高**
- 用途：精确分析

---

### 测试3：5分钟采样（中等视图）

**请求：**
```bash
curl "http://127.0.0.1:5000/api/support-resistance/trend?days=1&sample=5"
```

**结果：**
```json
{
  "success": true,
  "count": 5,                    // 返回5个点
  "total_count": 19,             // 原始19个点
  "interval": "5 minutes",
  "is_sampled": true,            // 已采样
  "data": [
    { "timestamp": "2026-01-25T09:15:00", "total_coins": 23 },
    { "timestamp": "2026-01-25T09:30:00", "total_coins": 23 },
    { "timestamp": "2026-01-25T09:35:00", "total_coins": 27 },
    { "timestamp": "2026-01-25T09:40:00", "total_coins": 27 },
    { "timestamp": "2026-01-25T09:45:00", "total_coins": 27 }
  ]
}
```

**分析：**
- 数据压缩率：(5/19) × 100% = **26.3%**
- 性能提升：**3.8倍**
- 细节平衡：**中等**

---

## 📚 API参数组合建议

| 使用场景 | API参数 | 预期效果 |
|---------|---------|---------|
| 月度全局视图 | `days=30&sample=15` | 2,880个点，快速流畅 |
| 周度中等视图 | `days=7&sample=5` | 2,016个点，细节清晰 |
| 今日实时监控 | `days=1&sample=1` | 实时完整数据 |
| 放大查看时段 | `sample=1&start=...&end=...` | 指定时段完整数据 |
| 指定月份全览 | `month=202601&sample=15` | 整月采样数据 |

---

## 🔧 调试建议

### 检查API响应

```bash
# 测试全局视图
curl "http://127.0.0.1:5000/api/support-resistance/trend?days=30&sample=15" | jq '.count, .total_count, .is_sampled'

# 测试完整数据
curl "http://127.0.0.1:5000/api/support-resistance/trend?days=1&sample=1" | jq '.count, .interval'

# 测试时间范围
curl "http://127.0.0.1:5000/api/support-resistance/trend?sample=1&start=2026-01-25T09:00:00%2B08:00&end=2026-01-25T10:00:00%2B08:00" | jq '.count, .zoom_range'
```

### 性能监控

```javascript
// 监控API响应时间
console.time('API调用');
fetch('/api/support-resistance/trend?days=30&sample=15')
  .then(res => res.json())
  .then(data => {
    console.timeEnd('API调用');
    console.log('数据点数:', data.count);
    console.log('压缩率:', ((1 - data.count / data.total_count) * 100).toFixed(1) + '%');
  });
```

---

## ✅ 核心优势总结

### ✨ 1. 性能优化
- **数据传输量：** 减少93.3%（15分钟采样）
- **渲染速度：** 提升15倍
- **用户体验：** 流畅无卡顿

### 🎯 2. 细节保留
- **采集层：** 始终保持1分钟采集（用于精确计算）
- **展示层：** 根据视图范围动态调整精度
- **放大查看：** 无损显示完整1分钟数据

### 🚀 3. 灵活性
- **多级采样：** 1分钟、5分钟、15分钟自由切换
- **时间范围：** 支持指定时间段查询
- **月份查询：** 支持查询历史月份数据

### 📊 4. 实用性
- **全局趋势：** 快速了解整体市场走势
- **局部分析：** 深入研究具体时间段
- **实时监控：** 精确到分钟的实时数据

---

## 🎉 总结

**分层数据加载策略完美解决了性能与细节的矛盾：**

```
采集层（1分钟） → 精确计算、逃顶信号统计 ✅
     ↓
展示层（智能采样）
     ├─ 全局视图：15分钟采样 → 快速流畅 ✅
     ├─ 中等视图：5分钟采样 → 细节平衡 ✅
     └─ 放大视图：1分钟完整 → 精确分析 ✅
```

**最佳实践：**
1. 初始加载使用15分钟采样
2. 用户放大时动态加载1分钟数据
3. 根据时间范围自动切换采样粒度
4. 始终保持1分钟采集频率

---

**完成时间：** 2026-01-25 09:50 (北京时间)  
**项目状态：** ✅ 分层加载功能完成并测试通过
