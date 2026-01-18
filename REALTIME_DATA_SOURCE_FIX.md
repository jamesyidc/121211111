# 🔧 实盘数据源修复报告

## 修复时间
- **修复时间**: 2026-01-05 05:40 UTC
- **修复类型**: 实盘数据从数据库改为OKEx API实时获取

---

## 一、问题描述

### 1.1 原始问题
实盘锚点系统显示的数据来源于数据库的历史记录，而不是OKEx API的实时数据。

**表现**:
- 开仓价格显示的是数据库中的维护价格
- 标记价格和盈亏数据不是实时的
- 用户看到的是"快照"数据，而不是实时持仓

### 1.2 问题根源
代码第12436行：
```python
if db_record:
    avg_price = float(db_record['open_price'])  # ❌ 使用数据库价格
```

---

## 二、修复方案

### 2.1 修复策略
**实盘模式**: 完全使用OKEx API的实时数据
**模拟盘模式**: 继续使用数据库数据

### 2.2 修复内容

#### 修复前 (❌ 错误)
```python
# 如果数据库中有记录，使用数据库的开仓价格
if db_record:
    avg_price = float(db_record['open_price'])  # 数据库价格
    is_anchor = int(db_record['is_anchor']) if db_record['is_anchor'] else 0
else:
    avg_price = okex_avg_price  # OKEx价格
    is_anchor = 0
```

#### 修复后 (✅ 正确)
```python
# ✅ 实盘模式：完全使用 OKEx API 的实时数据
avg_price = float(pos.get('avgPx', 0) or 0)  # OKEx实时开仓均价
mark_price = float(pos.get('markPx', 0) or 0)  # OKEx实时标记价
lever = int(pos.get('lever', 10) or 10)  # OKEx实时杠杆
upl = float(pos.get('upl', 0) or 0)  # OKEx实时未实现盈亏
margin = float(pos.get('margin', 0) or 0)  # OKEx实时保证金

# 判断是否为锚点单（只从数据库获取标记）
is_anchor = 0
if db_record and db_record['is_anchor']:
    is_anchor = int(db_record['is_anchor'])
```

---

## 三、验证结果

### 3.1 修复前后对比

#### 示例：STX-USDT-SWAP
| 字段 | 修复前（数据库） | 修复后（OKEx API） | 说明 |
|------|-----------------|-------------------|------|
| 开仓均价 | $0.2673 | $0.3591 | ✅ 现在是实时均价 |
| 标记价 | 固定值 | $0.3495 | ✅ 实时更新 |
| 收益率 | -92.15% | +8.02% | ✅ 实时计算 |
| 盈亏 | 历史值 | $0.096 | ✅ 实时盈亏 |

### 3.2 API测试结果
```bash
curl 'http://localhost:5000/api/anchor-system/current-positions?trade_mode=real'
```

**返回示例**:
```json
{
  "positions": [
    {
      "inst_id": "STX-USDT-SWAP",
      "avg_price": 0.3591,      // ✅ OKEx实时均价
      "mark_price": 0.3495,     // ✅ OKEx实时标记价
      "pos_size": 1.0,
      "lever": 3,
      "margin": 0.0,            // ✅ OKEx实时保证金
      "upl": 0.096,             // ✅ OKEx实时盈亏
      "profit_rate": 8.02,      // ✅ 实时计算收益率
      "is_anchor": 1            // ✅ 锚点标记保留
    }
  ],
  "total": 30,
  "trade_mode": "real",
  "success": true
}
```

---

## 四、数据来源说明

### 4.1 实盘模式 (trade_mode=real)

| 数据项 | 来源 | 说明 |
|--------|------|------|
| inst_id | OKEx API | 交易对名称 |
| pos_side | OKEx API | 持仓方向 |
| pos_size | OKEx API | 持仓数量 |
| avg_price | OKEx API | ✅ 实时开仓均价 |
| mark_price | OKEx API | ✅ 实时标记价格 |
| lever | OKEx API | ✅ 实时杠杆倍数 |
| margin | OKEx API | ✅ 实时保证金 |
| upl | OKEx API | ✅ 实时未实现盈亏 |
| profit_rate | 实时计算 | ✅ upl/margin*100 |
| is_anchor | 数据库标记 | 是否为锚点单（仅标记）|

### 4.2 模拟盘模式 (trade_mode=paper)

| 数据项 | 来源 | 说明 |
|--------|------|------|
| 所有字段 | 数据库 | 模拟盘数据完全来自数据库 |

---

## 五、修复文件

### 5.1 修改的文件
- `/home/user/webapp/source_code/app_new.py`
  - 函数: `get_current_positions()`
  - 行数: 12400-12450

### 5.2 修改说明
1. 移除了对数据库开仓价格的使用
2. 所有价格、数量、盈亏数据都从OKEx API获取
3. 保留数据库的`is_anchor`标记（用于识别锚点单）

---

## 六、收益率计算逻辑

### 6.1 主要方法（推荐）
```python
if margin > 0:
    profit_rate = (upl / margin) * 100
```

**说明**: 
- 使用未实现盈亏除以保证金
- 自动包含杠杆效应
- 最准确的收益率计算

### 6.2 备用方法
```python
if pos_side == 'short':
    profit_rate = ((avg_price - mark_price) / avg_price) * lever * 100
else:  # long
    profit_rate = ((mark_price - avg_price) / avg_price) * lever * 100
```

**说明**:
- 当margin=0时使用
- 基于价格变动和杠杆计算
- 仍然准确

---

## 七、系统访问

### 7.1 实盘锚点系统
**URL**: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real

### 7.2 API接口
**URL**: http://localhost:5000/api/anchor-system/current-positions?trade_mode=real

---

## 八、验证清单

- ✅ 实盘模式使用OKEx API实时数据
- ✅ 开仓均价来自OKEx（不是数据库）
- ✅ 标记价格实时更新
- ✅ 收益率实时计算
- ✅ 盈亏数据实时准确
- ✅ 锚点标记保留
- ✅ Flask应用重启成功
- ✅ API测试通过

---

## 九、注意事项

### 9.1 数据一致性
- **实盘数据**: 每次API调用都获取最新数据
- **刷新频率**: 跟随前端刷新频率（通常5-10秒）
- **数据延迟**: OKEx API响应通常<1秒

### 9.2 锚点标记
- **来源**: 数据库的`is_anchor`字段
- **用途**: 仅用于标识是否为锚点单
- **不影响**: 价格、盈亏等实时数据

### 9.3 性能影响
- **API调用**: 每次请求调用一次OKEx API
- **响应时间**: 约500ms（包含API调用）
- **优化建议**: 可考虑添加短期缓存（5-10秒）

---

## 十、后续建议

### 10.1 功能增强
- [ ] 添加数据刷新时间戳显示
- [ ] 添加API调用状态指示器
- [ ] 实现WebSocket实时推送
- [ ] 添加历史数据对比功能

### 10.2 监控告警
- [ ] API调用失败告警
- [ ] 数据异常告警
- [ ] 响应时间监控

---

**修复完成时间**: 2026-01-05 05:40 UTC  
**修复状态**: ✅ 成功  
**数据来源**: ✅ OKEx API实时数据  
**系统状态**: ✅ 正常运行  

**🎉 实盘数据源已修复为OKEx API实时获取！**
