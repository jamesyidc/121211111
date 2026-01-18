# 多空单盈利统计双Y轴图表 - 完成说明

## 📊 完成时间
2026-01-15 07:37:00

## ✅ 实现内容

### 1. 双Y轴图表配置
已成功实现双Y轴显示：

#### 左侧Y轴（🟢 绿色系 - 多头指标）
- **颜色**: 绿色系列 (#10b981)
- **位置**: 左侧 (position: 'left')
- **4条线**:
  1. 🟢 多头盈利 ≥ 120% - 深绿色 (#059669)
  2. 🟢 多头盈利 ≥ 80% - 绿色 (#10b981)
  3. 🟢 多头盈利 ≤ 40% - 浅绿色 (#86efac)
  4. 🟢 多头亏损 - 青绿色 (#22c55e)

#### 右侧Y轴（🔴 红色系 - 空单指标）
- **颜色**: 红色系列 (#ef4444)
- **位置**: 右侧 (position: 'right')
- **4条线**:
  1. 🔴 空单盈利 ≤ 40% - 浅红色 (#fca5a5)
  2. 🔴 空单亏损 - 深红色 (#dc2626)
  3. 🔴 空单盈利 ≥ 80% - 红色 (#f87171)
  4. 🔴 空单盈利 ≥ 120% - 暗红色 (#b91c1c)

### 2. 数据采集
- **采集频率**: 每1分钟采集一次
- **数据源**: `/api/anchor-system/current-positions?trade_mode=real`
- **采集内容**: 同时采集多头和空单持仓数据
- **存储格式**: JSONL文件

```json
{
  "datetime": "2026-01-15 07:36:25",
  "timestamp": 1768460185,
  "position_count": 44,
  "stats": {
    "long": {
      "lte_40": 8,
      "loss": 0,
      "gte_80": 10,
      "gte_120": 7,
      "total": 22
    },
    "short": {
      "lte_40": 8,
      "loss": 0,
      "gte_80": 4,
      "gte_120": 0,
      "total": 22
    }
  },
  "positions": [...]
}
```

### 3. 前端显示
- **图表标题**: 多空单盈利分布趋势（最近1小时）
- **数据窗口**: 显示最近60分钟的数据
- **自动刷新**: 每60秒自动刷新一次
- **图表位置**: 页面顶部，标题下方

### 4. 调试日志
添加了详细的控制台日志：

```javascript
📊 图表数据 - 多头 (🟢左Y轴): {
  times: ['07:34', '07:35', '07:36'],
  lte40: [8, 8, 8],
  loss: [0, 0, 0],
  gte80: [10, 10, 10],
  gte120: [7, 7, 7]
}

📊 图表数据 - 空单 (🔴右Y轴): {
  times: ['07:34', '07:35', '07:36'],
  lte40: [8, 8, 8],
  loss: [0, 0, 0],
  gte80: [4, 4, 4],
  gte120: [0, 0, 0]
}
```

## 📈 当前数据状态

### 最新采集数据（2026-01-15 07:36:25）
```
持仓总数: 44个
├─ 多头: 22个
│  ├─ 盈利 ≤ 40%: 8个
│  ├─ 亏损 (< 0%): 0个
│  ├─ 盈利 ≥ 80%: 10个
│  └─ 盈利 ≥ 120%: 7个
│
└─ 空单: 22个
   ├─ 盈利 ≤ 40%: 8个
   ├─ 亏损 (< 0%): 0个
   ├─ 盈利 ≥ 80%: 4个
   └─ 盈利 ≥ 120%: 0个
```

## 🔧 技术实现

### 后端 (anchor_profit_monitor.py)
```python
def get_positions_by_side(positions):
    """按方向分类持仓"""
    long_positions = [p for p in positions if p.get('pos_side') == 'long']
    short_positions = [p for p in positions if p.get('pos_side') == 'short']
    return long_positions, short_positions

def calculate_stats_both(long_positions, short_positions):
    """计算多头和空单的统计数据"""
    # 分别计算多头和空单的4个指标
    ...
```

### 前端 (anchor_system_real.html)
```javascript
// 双Y轴配置
yAxis: [
    {
        type: 'value',
        name: '多头数量',
        position: 'left',
        axisLabel: { color: '#10b981' },
        axisLine: { lineStyle: { color: '#10b981' } }
    },
    {
        type: 'value',
        name: '空单数量',
        position: 'right',
        axisLabel: { color: '#ef4444' },
        axisLine: { lineStyle: { color: '#ef4444' } }
    }
]

// 系列配置
series: [
    // 多头系列 (yAxisIndex: 0)
    { name: '🟢 多头盈利 ≥ 120%', yAxisIndex: 0, ... },
    { name: '🟢 多头盈利 ≥ 80%', yAxisIndex: 0, ... },
    { name: '🟢 多头盈利 ≤ 40%', yAxisIndex: 0, ... },
    { name: '🟢 多头亏损', yAxisIndex: 0, ... },
    
    // 空单系列 (yAxisIndex: 1)
    { name: '🔴 空单盈利 ≤ 40%', yAxisIndex: 1, ... },
    { name: '🔴 空单亏损', yAxisIndex: 1, ... },
    { name: '🔴 空单盈利 ≥ 80%', yAxisIndex: 1, ... },
    { name: '🔴 空单盈利 ≥ 120%', yAxisIndex: 1, ... }
]
```

## 🌐 访问地址

- **实盘页面**: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real
- **API - 最新数据**: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/api/anchor-profit/latest
- **API - 历史数据**: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/api/anchor-profit/history?limit=60

## 🔄 服务状态

### PM2 服务
```bash
anchor-profit-monitor  # 数据采集服务（每分钟）
flask-app             # Web服务（端口5000）
```

### 数据文件
```
/home/user/webapp/data/anchor_profit_stats/anchor_profit_stats.jsonl
```

### 日志位置
```
~/.pm2/logs/anchor-profit-monitor-out.log
~/.pm2/logs/anchor-profit-monitor-error.log
```

## 🎯 验证步骤

1. **打开页面**:
   ```
   https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real
   ```

2. **按F12打开开发者工具** → Console

3. **查看日志输出**:
   - 应看到 "📊 图表数据 - 多头 (🟢左Y轴)"
   - 应看到 "📊 图表数据 - 空单 (🔴右Y轴)"
   - 应看到 "✅ 空单盈利统计图表渲染完成"

4. **观察图表**:
   - 左侧Y轴（绿色标签）显示多头数量
   - 右侧Y轴（红色标签）显示空单数量
   - 图表中有8条线（4条绿色+4条红色）
   - 绿色线应该有数据（≥80%约10个，≥120%约7个）
   - 红色线应该有数据（≤40%约8个，≥80%约4个）

5. **等待60秒** → 图表应自动刷新

## 📝 Git 提交记录

1. `e1b68f5` - feat: 添加锚定系统空单盈利统计图表
2. `de4ee2f` - fix: 修复API重复endpoint问题
3. `3cf9d93` - docs: 添加锚定系统空单盈利监控完成说明文档
4. `ad3f246` - feat: 将空单盈利统计图表移到页面顶部
5. `4ba4e32` - docs: 添加空单盈利统计图表位置调整说明文档
6. `f03d7a0` - feat: 添加空单盈利统计图表加载日志
7. `6022f79` - docs: 添加空单盈利统计图表问题解决文档
8. `3ae09e0` - fix: 修复空单盈利监控数据采集问题
9. `8ccd8f4` - docs: 添加空单盈利数据采集修复文档
10. `7f9c3e6` - feat: 添加多头指标显示（绿色系）
11. `64f3cd5` - feat: 完善多空单盈利统计双Y轴图表显示

## ✨ 特性总结

✅ **双Y轴独立刻度** - 多头和空单各自独立Y轴
✅ **颜色区分明确** - 左侧绿色（多头），右侧红色（空单）
✅ **实时数据采集** - 每分钟自动采集最新持仓数据
✅ **自动刷新显示** - 前端每60秒自动更新图表
✅ **数据持久化** - JSONL格式存储历史数据
✅ **详细调试日志** - 完整的数据加载和渲染日志
✅ **向后兼容** - 兼容旧数据格式（只有空单数据时显示0）

## 🎉 完成状态

所有功能已完全实现并测试通过！

- ✅ 数据采集正常（46条历史记录）
- ✅ API端点正常响应
- ✅ 图表正常显示
- ✅ 双Y轴配置正确
- ✅ 颜色区分清晰
- ✅ 自动刷新工作正常

**请刷新页面查看完整的双Y轴图表！**
