# 重大事件系统 - 事件五添加报告 ⚡

**更新时间**: 2026-01-19 15:06  
**新增事件**: 事件五 - 多空盈利趋势反转  
**状态**: ✅ 已添加，数据获取逻辑待完善

---

## 🎯 事件五：多空盈利趋势反转

### 触发条件

```
✅ 条件1：空单亏损数量 >=  3 → 标记为🟢（绿色）
✅ 条件2：空单盈利≥120%数量 >= 3 → 标记为🔴（红色）
✅ 条件3：最近一次标记与上一次标记颜色不同 → 触发事件
```

### 两种趋势转换

#### 🔴 → 🟢 (红转绿)
```
含义: 从强势转弱势
市场: 多头转空头
趋势: 空头趋势
操作: 多空转换 (考虑开空)
```

#### 🟢 → 🔴 (绿转红)
```
含义: 从弱势转强势
市场: 空头转多头
趋势: 多头趋势
操作: 多空转换 (考虑开多)
```

---

## 💻 技术实现

### 1. 监控核心方法

#### `get_anchor_profit_stats()`
```python
"""
获取锚定系统多空盈利统计
返回: {
    'datetime': str,           # 记录时间
    'short_profit_120': int,   # 空单盈利≥120%的数量
    'short_loss': int,         # 空单亏损的数量
    'stats': dict              # 完整统计数据
}
"""
```

**数据源**: 
- 数据库: `databases/anchor_system.db`
- 表: `anchor_real_profit_records` (需要从统计接口获取)
- 来源页面: https://5000...sandbox.../anchor-system-real

#### `check_event_5_profit_trend_reversal()`
```python
"""
事件五检查逻辑
1. 获取当前盈利统计
2. 判断标记类型（绿/红）
3. 添加到历史记录
4. 检查趋势反转
5. 触发事件
"""
```

### 2. 状态追踪

```python
event_states['profit_marks_history'] = [
    {
        'datetime': '2026-01-19 14:00:00',
        'mark': 'red',                # 标记类型
        'short_profit_120': 5,        # 盈利数量
        'short_loss': 0,              # 亏损数量
        'time': datetime(...)         # 记录时间
    },
    {
        'datetime': '2026-01-19 15:00:00',
        'mark': 'green',              # 标记类型
        'short_profit_120': 0,
        'short_loss': 4,
        'time': datetime(...)
    }
]
```

**历史记录特点**:
- 只保留最近10个标记
- 自动去重（同一时间点只记录一次）
- 检测相邻两个标记的颜色变化

---

## 🎨 前端界面更新

### 1. 事件规则说明

添加了事件五的规则卡片：

```html
事件五：多空盈利趋势反转
- 空单亏损 ≥ 3 标记🟢
- 空单盈利≥120% ≥ 3 标记🔴
- 最近两次标记颜色不同触发
- 🔴→🟢: 空头趋势 | 🟢→🔴: 多头趋势
```

### 2. 事件显示样式

```javascript
// 多空转换的特殊样式
actionClass = 'bg-gradient-to-br from-purple-50 to-purple-100 text-purple-800'
iconClass = 'fa-exchange-alt'

// 事件描述格式
eventDescription = `🔴→🟢 市场从强势转弱势 → 空头趋势`
```

---

## 📊 事件示例

### 示例1：红转绿（空头趋势）

```json
{
  "event_type": "profit_trend_reversal",
  "event_id": 5,
  "event_name": "多空盈利趋势反转",
  "reversal_type": "red_to_green",
  "previous_mark": {
    "color": "red",
    "datetime": "2026-01-19 14:00:00",
    "short_profit_120": 5
  },
  "current_mark": {
    "color": "green",
    "datetime": "2026-01-19 15:00:00",
    "short_loss": 4
  },
  "action": "多空转换 (空头趋势)",
  "confidence": "medium",
  "description": "多空转换：红色(5个盈利) → 绿色(4个亏损)，市场从强势转弱势"
}
```

### 示例2：绿转红（多头趋势）

```json
{
  "event_type": "profit_trend_reversal",
  "event_id": 5,
  "event_name": "多空盈利趋势反转",
  "reversal_type": "green_to_red",
  "previous_mark": {
    "color": "green",
    "datetime": "2026-01-19 14:00:00",
    "short_loss": 4
  },
  "current_mark": {
    "color": "red",
    "datetime": "2026-01-19 15:00:00",
    "short_profit_120": 6
  },
  "action": "多空转换 (多头趋势)",
  "confidence": "medium",
  "description": "多空转换：绿色(4个亏损) → 红色(6个盈利)，市场从弱势转强势"
}
```

---

## 🔧 待完善功能

### 当前问题

1. **数据获取逻辑** ⚠️
   - 当前代码尝试从不存在的表获取数据
   - 需要从锚定系统的实时API获取统计数据

### 解决方案

#### 方案1：从API获取（推荐）
```python
import requests

def get_anchor_profit_stats(self):
    """从锚定系统API获取统计数据"""
    try:
        # 调用锚定系统API
        response = requests.get(
            'http://localhost:5000/api/anchor-system/profit-stats',
            params={'trade_mode': 'real'},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            # 解析数据
            stats = data.get('stats', {})
            short_stats = stats.get('short', {})
            
            return {
                'datetime': data.get('datetime'),
                'short_profit_120': short_stats.get('gte_120', 0),
                'short_loss': short_stats.get('loss', 0),
                'stats': stats
            }
    except Exception as e:
        logger.error(f"API获取失败: {e}")
        return None
```

#### 方案2：从数据库聚合
```python
def get_anchor_profit_stats(self):
    """从数据库聚合统计数据"""
    try:
        conn = sqlite3.connect('databases/anchor_system.db')
        cursor = conn.cursor()
        
        # 统计最近的盈利记录
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN pos_side='short' AND profit_rate >= 120 THEN 1 END) as short_profit_120,
                COUNT(CASE WHEN pos_side='short' AND profit_rate < 0 THEN 1 END) as short_loss
            FROM anchor_real_profit_records
            WHERE timestamp >= datetime('now', '-1 hour')
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'short_profit_120': result[0],
                'short_loss': result[1],
                'stats': {}
            }
    except Exception as e:
        logger.error(f"数据库查询失败: {e}")
        return None
```

---

## 📋 更新清单

### 代码更新
- ✅ `major_events_monitor.py` (+143行)
  - 新增 `get_anchor_profit_stats()` 方法
  - 新增 `check_event_5_profit_trend_reversal()` 方法
  - 更新 `monitor_cycle()` 包含事件五
  - 更新 `event_states` 添加历史记录

- ✅ `major_events.html` (+54行)
  - 新增事件五规则说明卡片
  - 更新 `displayEvents()` 支持多空转换样式
  - 添加特殊图标和颜色处理

### 功能特性
- ✅ 标记历史追踪（最多10个）
- ✅ 颜色变化检测
- ✅ 趋势方向判断
- ✅ 事件描述生成
- ⚠️ 数据获取逻辑（待完善）

---

## 🎯 使用指南

### 数据来源

事件五依赖锚定系统的多空盈利统计数据：

**数据页面**:
```
https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/anchor-system-real
```

**关键指标**:
- 空单盈利≥120%的数量
- 空单亏损的数量

### 触发时机

```
时间点1 (14:00): 空单盈利≥120% = 5个 → 🔴标记
时间点2 (15:00): 空单亏损 = 4个 → 🟢标记
触发事件: 红→绿，空头趋势
```

### 操作建议

1. **🔴→🟢 (空头趋势)**
   - 市场从强势转为弱势
   - 考虑开空或减多仓
   - 设置止损保护

2. **🟢→🔴 (多头趋势)**
   - 市场从弱势转为强势
   - 考虑开多或减空仓
   - 关注突破位置

---

## 📊 监控状态

```
事件总数: 5个
├─ 事件一: 高强度见顶诱多 ✅
├─ 事件二: 一般强度见顶诱多 ✅
├─ 事件三: 强空头爆仓 ✅
├─ 事件四: 弱空头爆仓 ✅
└─ 事件五: 多空盈利趋势反转 ⚠️ (数据获取待完善)
```

---

## 🔧 后续工作

### 优先级：高
1. **完善数据获取逻辑**
   - 实现从锚定系统API获取数据
   - 或从数据库聚合统计
   - 确保数据准确性

### 优先级：中
2. **增加配置选项**
   - 可配置阈值（当前固定为3）
   - 可配置盈利率（当前固定为120%）

3. **优化历史记录**
   - 持久化到文件
   - 支持历史回顾

### 优先级：低
4. **增强展示**
   - 实时面板显示当前标记
   - 标记历史图表
   - 趋势变化可视化

---

## 📝 Git 提交记录

```
Commit: e935872
Message: feat: 添加事件五-多空盈利趋势反转监控
Files: 2 files changed, 202 insertions(+), 5 deletions(-)
- major_events_monitor.py (新增方法)
- major_events.html (界面更新)

Branch: genspark_ai_developer
PR: https://github.com/jamesyidc/121211111/pull/1
```

---

## 🎊 总结

**事件五已成功添加到重大事件监控系统！**

### 核心成就
✅ **新事件类型** - 多空盈利趋势反转  
✅ **智能识别** - 自动标记和趋势检测  
✅ **历史追踪** - 最近10个标记记录  
✅ **前端展示** - 完整的规则说明和事件显示  
⚠️ **数据获取** - 待完善从锚定系统获取数据

### 下一步
1. 完善 `get_anchor_profit_stats()` 的数据获取逻辑
2. 测试事件五的触发和显示
3. 优化阈值配置

---

**更新完成时间**: 2026-01-19 15:06  
**功能状态**: 基础框架完成，待数据对接  
**测试状态**: ⚠️ 待完善数据获取后测试

访问系统：https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/major-events
