# 极值追踪系统 - 追踪点27币完整快照功能

## 📋 文档信息
- **文档版本**: v1.0
- **系统版本**: v1.5
- **创建时间**: 2026-01-19 12:20 UTC
- **功能**: 在1h/3h/6h/12h/24h追踪点保存27币完整快照

---

## 🎯 用户需求

### 问题描述
从用户截图可以看到，极值追踪页面在1h、3h追踪点只显示了"27币总涨跌幅"，但**没有显示27个币当时的详细价格和涨跌幅快照**。

### 用户期望
- ✅ 显示27币总涨跌幅（已有）
- ❌ **显示每个币种的具体价格**（缺失）
- ❌ **显示每个币种的涨跌幅**（缺失）
- ❌ **显示从触发时刻到追踪点的价格变化**（缺失）

---

## ✨ 新功能实现

### 完整追踪数据结构

#### 修改前（只有总和）
```json
{
  "1h": {
    "timestamp": 1768789860,
    "datetime": "2026-01-19 10:31:00",
    "period": "1h",
    "total_change": -172.72  // ❌ 只有总涨跌幅
  }
}
```

#### 修改后（完整快照）
```json
{
  "1h": {
    "timestamp": 1768789860,
    "datetime": "2026-01-19 10:31:00",
    "period": "1h",
    "total_change": -172.72,
    "coins_snapshot": [  // ✅ 新增：27币完整快照
      {
        "symbol": "BTC",
        // 触发时刻的数据
        "trigger_price": 94561.0,
        "trigger_base_price": 95068.0,
        "trigger_day_change": -0.53,
        // 1h后的数据
        "current_price": 93200.5,
        "current_base_price": 95068.0,
        "current_day_change": -1.96,
        // 从触发到现在的变化
        "price_change_from_trigger": -1.44
      },
      {
        "symbol": "ETH",
        "trigger_price": 3309.0,
        "trigger_base_price": 3332.01,
        "trigger_day_change": -0.69,
        "current_price": 3250.8,
        "current_base_price": 3332.01,
        "current_day_change": -2.44,
        "price_change_from_trigger": -1.76
      }
      // ... 其余25个币种
    ]
  }
}
```

### 数据字段说明

每个币种在追踪点包含以下信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 币种符号（BTC, ETH等） |
| **触发时刻数据** | | |
| `trigger_price` | float | 触发极值时的价格 |
| `trigger_base_price` | float | 触发时的基准价（当日开盘价） |
| `trigger_day_change` | float | 触发时的日涨跌幅（%） |
| **追踪点数据** | | |
| `current_price` | float | 追踪点（1h/3h等）的价格 |
| `current_base_price` | float | 追踪点的基准价 |
| `current_day_change` | float | 追踪点的日涨跌幅（%） |
| **变化数据** | | |
| `price_change_from_trigger` | float | 从触发到追踪点的价格变化（%） |

---

## 🔧 技术实现

### 代码修改位置
**文件**: `source_code/extreme_value_tracker.py`

### 核心修改：update_tracking 函数

#### 修改前逻辑
```python
tracking_data = {
    'timestamp': int(time.time()),
    'datetime': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
    'period': period,
    'total_change': self.calculate_total_change(coins_data),
    'coins': []  # ❌ 空数组，没有保存数据
}
```

#### 修改后逻辑
```python
tracking_data = {
    'timestamp': int(time.time()),
    'datetime': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
    'period': period,
    'total_change': self.calculate_total_change(coins_data),
    'coins_snapshot': []  # ✅ 改名并填充数据
}

# 保存当前时刻27币的完整数据
original_coins = {c['symbol']: c for c in snapshot['coins_snapshot']['coins']}

if 'day_changes' in coins_data:
    for symbol, coin_info in coins_data['day_changes'].items():
        # 获取原始快照数据（触发时刻）
        original_coin = original_coins.get(symbol, {})
        original_price = original_coin.get('current_price', 0)
        original_base_price = original_coin.get('base_price', 0)
        original_day_change = original_coin.get('day_change_percent', 0)
        
        # 当前数据（追踪点）
        if isinstance(coin_info, dict):
            current_price = coin_info.get('current_price', 0)
            base_price = coin_info.get('base_price', 0)
            current_day_change = coin_info.get('change_pct', 0)
        
        # 计算价格变化
        price_change_from_trigger = 0
        if original_price > 0 and current_price > 0:
            price_change_from_trigger = ((current_price - original_price) / original_price * 100)
        
        # 保存完整数据
        tracking_data['coins_snapshot'].append({
            'symbol': symbol,
            'trigger_price': original_price,
            'trigger_base_price': original_base_price,
            'trigger_day_change': original_day_change,
            'current_price': current_price,
            'current_base_price': base_price,
            'current_day_change': current_day_change,
            'price_change_from_trigger': round(price_change_from_trigger, 2)
        })
```

---

## 📊 数据示例

### 触发快照（时间：09:00:42）
```json
{
  "snapshot_id": "EXT_1768784442",
  "trigger_datetime": "2026-01-19 09:00:42",
  "coins_snapshot": {
    "total_change": -185.0,
    "coins": [
      {
        "symbol": "BTC",
        "current_price": 94561.0,
        "base_price": 95068.0,
        "day_change_percent": -0.53
      }
    ]
  }
}
```

### 1h追踪点（时间：10:00:42）
```json
{
  "1h": {
    "timestamp": 1768788042,
    "datetime": "2026-01-19 10:00:42",
    "total_change": -180.5,
    "coins_snapshot": [
      {
        "symbol": "BTC",
        "trigger_price": 94561.0,        // 触发时
        "trigger_base_price": 95068.0,
        "trigger_day_change": -0.53,
        "current_price": 93800.0,         // 1h后
        "current_base_price": 95068.0,
        "current_day_change": -1.33,
        "price_change_from_trigger": -0.80  // 1h内跌了0.80%
      }
    ]
  }
}
```

### 3h追踪点（时间：12:00:42）
```json
{
  "3h": {
    "timestamp": 1768795242,
    "datetime": "2026-01-19 12:00:42",
    "total_change": -163.2,
    "coins_snapshot": [
      {
        "symbol": "BTC",
        "trigger_price": 94561.0,        // 触发时
        "current_price": 95200.0,         // 3h后
        "price_change_from_trigger": +0.68  // 3h内涨了0.68%
      }
    ]
  }
}
```

---

## 🎯 用户价值

### 1. **完整的价格追踪**
- ✅ 看到每个币种在追踪点的具体价格
- ✅ 对比触发时刻和追踪点的价格变化
- ✅ 了解市场恢复或继续下跌的具体情况

### 2. **精准的策略分析**
- ✅ 分析哪些币种在1h/3h/6h后反弹最快
- ✅ 识别市场领涨/领跌币种
- ✅ 制定更精准的止损和止盈策略

### 3. **历史数据回测**
- ✅ 回溯分析极值事件后的价格走势
- ✅ 验证交易策略的有效性
- ✅ 优化入场和出场时机

### 4. **投资决策支持**
- ✅ 极值触发后1h内是否应该立即抄底？
- ✅ 3h后市场是否企稳？
- ✅ 24h后哪些币种表现最好？

---

## 📈 前端展示建议

### 追踪点详情页面

#### 布局建议
```
┌─────────────────────────────────────────────────────────┐
│  极值快照: EXT_1768784442                                │
│  触发时间: 2026-01-19 09:00:42                          │
│  触发类型: 27币跌幅重度 (-185.0%)                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  1小时追踪 (10:00:42)                                   │
│  总涨跌: -180.5%  [展开27币详情 ▼]                      │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 币种 | 触发价 | 1h后价 | 变化% | 日涨跌 | 基准价  │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ BTC  | 94561  | 93800  | -0.80% | -1.33% | 95068  │ │
│  │ ETH  | 3309   | 3280   | -0.88% | -1.56% | 3332   │ │
│  │ ...  | ...    | ...    | ...    | ...    | ...    │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  3小时追踪 (12:00:42)                                   │
│  总涨跌: -163.2%  [展开27币详情 ▼]                      │
└─────────────────────────────────────────────────────────┘
```

#### 交互功能
1. **折叠/展开**: 默认只显示总涨跌，点击展开显示27币详情
2. **颜色标识**: 
   - 🟢 绿色：从触发到追踪点价格上涨
   - 🔴 红色：从触发到追踪点价格下跌
3. **排序功能**: 按价格变化幅度排序
4. **筛选功能**: 只显示涨幅>5%或跌幅>5%的币种

---

## 🧪 测试计划

### 测试场景

| 测试项 | 描述 | 预期结果 |
|-------|------|----------|
| 数据完整性 | 检查1h追踪点是否包含27币数据 | ✅ coins_snapshot包含27个元素 |
| 价格准确性 | 验证价格数据与API一致 | ✅ 价格匹配 |
| 变化计算 | 验证price_change_from_trigger计算正确 | ✅ 计算准确 |
| 多时间点 | 检查1h/3h/6h/12h/24h都有完整数据 | ✅ 所有追踪点都有数据 |

### 验证命令
```bash
# 查看最新快照的3h追踪数据
cd /home/user/webapp
tail -1 data/extreme_tracking/extreme_snapshots.jsonl | \
  python3 -c "import sys, json; d=json.load(sys.stdin); \
  print('3h coins:', len(d['tracking']['3h']['coins_snapshot']) if d['tracking']['3h'] else 0)"
```

---

## 🔄 部署状态

### 代码状态
- ✅ 代码修改完成
- ✅ 进程已重启
- ⏳ 等待下次追踪更新验证

### 下次追踪时间
- **EXT_1768786246**: 3h追踪将在 12:30 左右触发
- **预计验证时间**: 约10-15分钟后

### 验证计划
1. 等待12:27左右进行3h追踪更新
2. 检查更新后的数据是否包含 `coins_snapshot`
3. 验证27个币种数据是否完整
4. 确认前端API返回正确数据

---

## 📝 API 影响

### API端点
- `/api/extreme-tracking/snapshots` - 返回所有快照
- `/api/extreme-tracking/snapshot/<id>` - 返回单个快照详情

### 返回数据变化
**新增字段**: `tracking[period].coins_snapshot`

**向后兼容**: 
- ✅ 旧快照仍然可读取（没有coins_snapshot字段）
- ✅ 新快照包含完整数据
- ✅ 前端需要检查字段是否存在

---

## 🚀 后续优化

### 短期（本周）
- [ ] 前端实现27币详情展开/折叠
- [ ] 添加价格变化趋势图
- [ ] 实现币种排序和筛选

### 中期（本月）
- [ ] 添加历史追踪数据对比
- [ ] 实现追踪点数据导出（CSV/Excel）
- [ ] 优化数据加载性能

### 长期（规划）
- [ ] 机器学习预测未来追踪点价格
- [ ] 自动识别最佳入场/出场时机
- [ ] 生成交易策略回测报告

---

## 🔗 相关链接

- **极值追踪页面**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/extreme-tracking
- **系统首页**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/
- **PR链接**: https://github.com/jamesyidc/121211111/pull/1

---

**功能完成时间**: 2026-01-19 12:20 UTC  
**系统版本**: v1.5  
**状态**: ✅ 代码已部署，等待验证  
**用户需求**: ⏳ 实现中（等待下次追踪更新）
