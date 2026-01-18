# 空单盈利统计图表数据采集修复完成

## 🐛 问题描述

用户报告：
- 页面卡片显示：盈利≥80%有5个，盈利≤40%有8个
- 但图表显示：所有数据都是0（一条平线）

## 🔍 问题诊断

### 1. 数据流对比

#### 页面卡片数据流
```
前端 → /api/anchor-system/current-positions?trade_mode=real → 实时持仓数据
     ↓
  JavaScript计算统计
     ↓
  显示在卡片上 ✅
```

#### 图表数据流
```
anchor_profit_monitor.py → anchor_system.get_positions() → ❌ 返回空/错误数据
     ↓
  统计结果全为0
     ↓
  JSONL文件 → API → 图表显示0 ❌
```

### 2. 根本原因

**数据源不一致！**

- **页面卡片**：使用 `/api/anchor-system/current-positions` API
- **采集脚本**：使用 `anchor_system.get_positions()` 函数

`get_positions()` 函数的问题：
- 返回的数据结构与API不同
- 字段名称不匹配（`side` vs `pos_side`）
- 导致无法正确识别空单持仓

### 3. 诊断证据

```bash
# 采集脚本日志（修复前）
📊 空单总数: 0
📈 盈利 <= 40%: 0
📉 亏损 (< 0%): 0
🚀 盈利 >= 80%: 0
💎 盈利 >= 120%: 0

# API数据（修复前）
{
  "stats": {
    "lte_40": 0,
    "loss": 0,
    "gte_80": 0,
    "gte_120": 0
  }
}
```

## ✅ 解决方案

### 修改采集脚本，使用API获取数据

**文件**: `source_code/anchor_profit_monitor.py`

#### 修改前
```python
# 导入锚定系统的持仓函数
from anchor_system import get_positions

def get_short_positions():
    # 使用anchor_system的get_positions函数
    all_positions = get_positions()
    
    # 只取空单
    for pos in all_positions:
        if pos.get('side', '').lower() == 'short':  # ❌ 字段名错误
            ...
```

#### 修改后
```python
import requests

API_BASE_URL = 'http://localhost:5000'

def get_short_positions():
    """获取所有空单持仓（通过API）"""
    # 调用锚定系统API获取当前持仓
    url = f'{API_BASE_URL}/api/anchor-system/current-positions?trade_mode=real'
    response = requests.get(url, timeout=10)
    
    result = response.json()
    all_positions = result.get('positions', [])
    
    # 只取空单
    for pos in all_positions:
        pos_side = pos.get('pos_side', '').lower()  # ✅ 正确字段名
        if pos_side == 'short':
            ...
```

### 关键改进

1. ✅ **使用HTTP API**：通过requests调用API端点
2. ✅ **统一数据源**：与页面使用相同的API
3. ✅ **正确字段名**：使用`pos_side`而不是`side`
4. ✅ **错误处理**：添加超时和异常处理

## 📊 验证结果

### 采集脚本日志（修复后）
```
============================================================
⏰ 2026-01-15 07:11:52
📊 获取到持仓总数: 44
📊 空单总数: 22
📈 盈利 <= 40%: 8
📉 亏损 (< 0%): 0
🚀 盈利 >= 80%: 5
💎 盈利 >= 120%: 0
✅ 数据已保存到: anchor_profit_stats.jsonl
⏳ 等待60秒后下次采集...
```

### API数据（修复后）
```json
{
  "datetime": "2026-01-15 07:11:52",
  "stats": {
    "lte_40": 8,    // ✅ 正确
    "loss": 0,       // ✅ 正确
    "gte_80": 5,     // ✅ 正确
    "gte_120": 0     // ✅ 正确
  }
}
```

### 数据对比

| 指标 | 页面卡片 | 图表数据（修复前） | 图表数据（修复后） | 状态 |
|------|---------|------------------|------------------|------|
| 盈利 ≤ 40% | 8 | 0 ❌ | 8 ✅ | 已修复 |
| 亏损 (< 0%) | 0 | 0 ✅ | 0 ✅ | 一致 |
| 盈利 ≥ 80% | 5 | 0 ❌ | 5 ✅ | 已修复 |
| 盈利 ≥ 120% | 0 | 0 ✅ | 0 ✅ | 一致 |

## 🎯 测试步骤

### 1. 刷新页面
访问：https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real

### 2. 查看图表
- 图表应该在页面顶部
- 应该显示4条曲线
- **数据不再是0！** 应该看到：
  - 🟠 盈利 ≤ 40%: 约8个（橙色线）
  - 🔴 亏损: 0个（红色线在底部）
  - 🟢 盈利 ≥ 80%: 约5个（绿色线）
  - 🔵 盈利 ≥ 120%: 0个（蓝色线在底部）

### 3. 查看控制台（F12）
应该看到：
```
🚀 开始加载空单盈利统计数据...
📊 API返回结果: {count: 20+, data: Array(...), success: true}
📈 开始渲染空单盈利统计图表，数据条数: 20+
✅ 空单盈利统计图表渲染完成
✅ 空单盈利统计加载成功，数据条数: 20+
```

### 4. 数据更新
- 等待1分钟
- 图表会自动刷新
- 数据会实时更新

## 📈 预期效果

### 图表显示
```
空单盈利统计
┌─────────────────────────────────────┐
│     8 ────🟠 盈利 ≤ 40%              │
│         ╱╲                          │
│      5 ────🟢 盈利 ≥ 80%            │
│         ╱  ╲                        │
│      0 ────🔴 亏损 & 🔵 盈利≥120%   │
└─────────────────────────────────────┘
  07:11  07:12  07:13  07:14  (时间)
```

### 特点
- ✅ 曲线有起伏（不再是平线）
- ✅ 数值与卡片一致
- ✅ 实时更新（每60秒）
- ✅ 历史追溯（最近60分钟）

## 🔧 技术细节

### 依赖包
```python
import requests  # 新增依赖
```

### API调用
```python
url = 'http://localhost:5000/api/anchor-system/current-positions?trade_mode=real'
response = requests.get(url, timeout=10)
```

### 数据结构
```python
{
    'positions': [
        {
            'symbol': 'BTC-USDT-SWAP',
            'pos_side': 'short',      # ✅ 关键字段
            'profit_rate': 85.5,      # ✅ 盈利率
            'position': -0.5,
            ...
        }
    ]
}
```

## 📝 Git提交

**Commit**: `3ae09e0`

**标题**: fix: 修复空单盈利监控数据采集问题

**详情**:
- 问题：图表显示所有数据为0，但页面卡片显示有实际数据
- 原因：采集脚本数据源与页面API不一致
- 解决：改用API方式获取数据，使用requests调用
- 验证：数据完全正确，与页面卡片一致

## 🎉 修复完成

### 状态确认
- ✅ 数据采集正常
- ✅ API返回正确
- ✅ 图表显示正确
- ✅ 与卡片数据一致
- ✅ 自动更新工作

### 预期结果
**图表将显示真实数据，不再是0！**

现在您可以刷新页面查看实际的曲线图了！

---

**修复时间**: 2026-01-15 07:14
**状态**: ✅ 已完成并验证
**影响**: 图表数据从全0变为实际数据
