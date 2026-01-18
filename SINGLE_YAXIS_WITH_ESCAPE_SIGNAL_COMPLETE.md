# 🎯 单Y轴图表 + 2小时逃顶信号 - 完成报告

## ✅ 完成时间
2026-01-15 07:45:00

---

## 📊 需求回顾

您提出的修改需求：

1. ❌ **不要左右分开的双Y轴**
2. ✅ **只用颜色区分**：
   - 🟢 绿色系 → 多头指标
   - 🔴 红色系 → 空头指标
3. ✅ **显示指标提示**："多头指标" 和 "空头指标"
4. ✅ **添加2小时逃顶信号统计**（橙色）
5. ✅ **数据存储为JSONL**

---

## ✨ 实现结果

### 图表配置

#### 单Y轴设计
- **Y轴名称**: "数量"
- **刻度颜色**: 灰色（中性）
- **网格线**: 虚线分割

#### 图例分组
```
【多头指标】(绿色粗体)
  🟢 多头≥120%  (深绿 #059669)
  🟢 多头≥80%   (绿色 #10b981)
  🟢 多头≤40%   (浅绿 #86efac)
  🟢 多头亏损   (青绿 #22c55e)

【空头指标】(红色粗体)
  🔴 空单≤40%   (浅红 #fca5a5)
  🔴 空单亏损   (深红 #dc2626)
  🔴 空单≥80%   (红色 #f87171)
  🔴 空单≥120%  (暗红 #b91c1c)

【逃顶信号】(橙色粗体)
  ⚡ 2h逃顶信号 (橙色 #f97316, 钻石形)
```

### 数据采集

#### 数据源
1. **持仓数据**: `/api/anchor-system/current-positions?trade_mode=real`
2. **逃顶信号**: `/home/user/webapp/data/escape_signal_jsonl/escape_signal_stats.jsonl`

#### 采集频率
- **间隔**: 每60秒采集一次
- **服务**: `anchor-profit-monitor` (PM2)

#### 数据格式
```json
{
  "timestamp": 1768462961,
  "datetime": "2026-01-15 07:42:41",
  "stats": {
    "long": {
      "lte_40": 8,
      "loss": 0,
      "gte_80": 10,
      "gte_120": 8,
      "total": 22
    },
    "short": {
      "lte_40": 10,
      "loss": 0,
      "gte_80": 3,
      "gte_120": 0,
      "total": 22
    }
  },
  "escape_signal_2h": 0,
  "long_positions": [...],
  "short_positions": [...]
}
```

---

## 📈 当前数据展示

### 最新数据（2026-01-15 07:44:41）

#### 🟢 多头指标
```
盈利 ≥ 120%  ████████████  8个
盈利 ≥ 80%   ██████████████  10个
盈利 ≤ 40%   ████████████  8个
亏损 < 0%                 0个
```

#### 🔴 空头指标
```
盈利 ≥ 120%               0个
盈利 ≥ 80%   ████████  3个
盈利 ≤ 40%   █████████████  9个
亏损 < 0%                 0个
```

#### ⚡ 逃顶信号
```
2小时逃顶信号: 0个
```

---

## 🎨 视觉效果

### 线条样式
- **多头线条**: 绿色系，圆形点，线宽2px
- **空单线条**: 红色系，圆形点，线宽2px
- **逃顶信号**: 橙色，钻石形点，线宽3px，加粗显示

### 图表特性
✅ 所有线条使用同一个Y轴  
✅ 只用颜色区分不同指标  
✅ 图例清晰分组显示  
✅ 逃顶信号突出显示（钻石形 + 加粗）  
✅ 鼠标悬停显示详细数值  
✅ 点击图例可隐藏/显示对应线条  

---

## 🔧 技术实现

### 后端修改
**文件**: `source_code/anchor_profit_monitor.py`

```python
def get_escape_signal_2h():
    """获取最近的2小时逃顶信号数量"""
    # 从escape_signal_stats.jsonl读取最后一行
    # 返回signal_2h_count字段
    
def save_to_jsonl(timestamp, stats, long_positions, short_positions, escape_signal_2h=0):
    """保存时包含逃顶信号数据"""
    data = {
        ...
        'escape_signal_2h': escape_signal_2h,
        ...
    }
```

### 前端修改
**文件**: `source_code/templates/anchor_system_real.html`

#### 数据提取
```javascript
// 2小时逃顶信号（橙色）
const escape2hData = dataList.map(d => d.escape_signal_2h || 0);
```

#### Y轴配置（改为单轴）
```javascript
yAxis: {
    type: 'value',
    name: '数量',  // 单一Y轴名称
    minInterval: 1,
    axisLabel: {
        color: '#4b5563',  // 中性颜色
        formatter: '{value}'
    },
    splitLine: {
        show: true,
        lineStyle: {
            color: '#e5e7eb',
            type: 'dashed'
        }
    }
}
```

#### 逃顶信号线配置
```javascript
{
    name: '⚡ 2h逃顶信号',
    type: 'line',
    data: escape2hData,
    smooth: true,
    itemStyle: { color: '#f97316' },
    lineStyle: { 
        width: 3,  // 加粗
        color: '#f97316', 
        type: 'solid' 
    },
    symbol: 'diamond',  // 钻石形
    symbolSize: 7,
    emphasis: {
        focus: 'series',
        itemStyle: {
            borderColor: '#f97316',
            borderWidth: 2
        }
    }
}
```

---

## 🌐 访问地址

**实盘页面**: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real

---

## 🎯 验证步骤

### 1. 打开页面
访问上述地址

### 2. 查看图表
在页面顶部找到 "💰 多空单盈利统计" 卡片

### 3. 观察图表特征
应该看到：
- ✅ 只有1个Y轴（左侧，标签为"数量"）
- ✅ 图例分为3组：【多头指标】【空头指标】【逃顶信号】
- ✅ 9条线：4条绿色 + 4条红色 + 1条橙色
- ✅ 橙色线使用钻石形点标记
- ✅ 所有线条在同一个坐标系中

### 4. 查看控制台日志（F12 → Console）
应该看到：
```
📊 图表数据: {
  times: [...],
  long: {...},
  short: {...},
  escape2h: [0, 0, 0]
}
```

### 5. 测试交互
- 鼠标悬停：显示所有指标的具体数值
- 点击图例：隐藏/显示对应线条
- 等待60秒：自动刷新显示最新数据

---

## 📂 文件变更

### 修改的文件
1. `source_code/anchor_profit_monitor.py`
   - 添加 `get_escape_signal_2h()` 函数
   - 修改 `save_to_jsonl()` 添加 escape_signal_2h 参数
   - 修改 `collect_once()` 调用逃顶信号采集

2. `source_code/templates/anchor_system_real.html`
   - 修改 `renderProfitStatsChart()` 函数
   - 改为单Y轴配置
   - 添加图例分组
   - 添加逃顶信号数据提取和渲染

### 数据文件
```
data/anchor_profit_stats/anchor_profit_stats.jsonl
  → 包含 escape_signal_2h 字段

data/escape_signal_jsonl/escape_signal_stats.jsonl
  → 逃顶信号数据源
```

---

## 📊 数据流程图

```
┌──────────────────────────────────────┐
│  escape_signal_stats.jsonl          │
│  (2小时逃顶信号原始数据)              │
└───────────────┬──────────────────────┘
                │
                │ 读取最后一行
                ↓
┌──────────────────────────────────────┐
│  anchor_profit_monitor.py            │
│  ┌────────────────────────────────┐  │
│  │ get_escape_signal_2h()         │  │
│  │  → 返回 signal_2h_count        │  │
│  └────────────────────────────────┘  │
│               +                      │
│  ┌────────────────────────────────┐  │
│  │ get_positions_by_side()        │  │
│  │  → 多头 + 空单持仓数据         │  │
│  └────────────────────────────────┘  │
│               ↓                      │
│  ┌────────────────────────────────┐  │
│  │ save_to_jsonl()                │  │
│  │  → 保存到 anchor_profit_stats  │  │
│  └────────────────────────────────┘  │
└───────────────┬──────────────────────┘
                │ 每分钟写入
                ↓
┌──────────────────────────────────────┐
│  anchor_profit_stats.jsonl           │
│  {                                   │
│    stats: {long, short},             │
│    escape_signal_2h: 0               │
│  }                                   │
└───────────────┬──────────────────────┘
                │
                │ API 读取
                ↓
┌──────────────────────────────────────┐
│  Flask API                           │
│  GET /api/anchor-profit/history      │
└───────────────┬──────────────────────┘
                │
                │ AJAX 请求
                ↓
┌──────────────────────────────────────┐
│  anchor_system_real.html             │
│  ┌────────────────────────────────┐  │
│  │ renderProfitStatsChart()       │  │
│  │  → 提取 escape2hData           │  │
│  │  → 渲染橙色钻石线             │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 🎉 完成状态

✅ **所有需求已实现**

- [x] 改为单Y轴（不再左右分开）
- [x] 只用颜色区分（绿色/红色/橙色）
- [x] 显示指标提示（图例分组）
- [x] 添加2小时逃顶信号（橙色钻石线）
- [x] 数据存储为JSONL
- [x] 每分钟自动采集
- [x] 前端每60秒刷新

---

## 📝 Git 提交记录

最新提交：
```
abe41cc - feat: 改为单Y轴图表并添加2小时逃顶信号
```

主要改动：
- 2个文件修改
- 148行新增
- 181行删除

---

## 🚀 服务状态

### PM2 服务
```bash
$ pm2 status

anchor-profit-monitor  ✓ online  (采集服务)
flask-app              ✓ online  (Web服务)
```

### 数据状态
- **历史记录**: 54条数据
- **时间范围**: 最近54分钟
- **采集状态**: 正常运行
- **逃顶信号**: 当前为0

---

## 🎯 最终效果

### 图表展示
```
          数量 (单Y轴)
            ↓
    15 ├──────────────────────────
       │    🟢 多头≥80% (10个)
    10 ├──🟢 多头≥120% (8个)──────
       │    🟢 多头≤40% (8个)
     5 ├──🔴 空单≤40% (9个)───────
       │ 🔴 空单≥80% (3个)
       │ ⚡ 逃顶信号 (0个)
     0 └──────────────────────────
        07:42 07:43 07:44 07:45
```

### 颜色说明
- **🟢 绿色系**: 多头指标（4条线）
- **🔴 红色系**: 空单指标（4条线）
- **⚡ 橙色**: 2小时逃顶信号（1条线，钻石形）

---

## 💡 使用提示

1. **查看图表**: 打开页面后自动加载
2. **交互操作**: 
   - 鼠标悬停查看数值
   - 点击图例隐藏/显示线条
3. **自动刷新**: 每60秒更新一次
4. **数据说明**: 
   - 多头/空单：实时持仓盈利统计
   - 逃顶信号：来自support-resistance页面的2小时信号

---

**✅ 功能已完全实现并测试通过！**

访问地址: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real
