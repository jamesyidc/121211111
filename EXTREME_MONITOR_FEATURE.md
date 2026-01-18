# 极值变化监控功能说明

## 📋 功能概述

当锚点系统检测到任何币种的盈利率创新高或亏损率创新低时，系统会：
1. 更新极值记录到 JSONL 文件
2. **自动写入历史监控记录表**（新增功能）
3. 发送 Telegram 通知
4. 在前端页面显示极值告警

## 🎯 核心功能

### 1. 极值检测逻辑

**创新高（最大盈利）**:
- 条件：当前盈利率 > 0
- 触发：当前盈利率 > 历史最大盈利（或无历史记录）
- 标记：`extreme_max_profit`

**创新低（最大亏损）**:
- 条件：当前盈利率 < 0
- 触发：当前盈利率 < 历史最大亏损（或无历史记录）
- 标记：`extreme_max_loss`

### 2. 数据存储

#### JSONL存储 (data/extreme_jsonl/extreme_real.jsonl)

每个币种的极值记录：
```json
{
    "inst_id": "SUI-USDT-SWAP",
    "pos_side": "short",
    "record_type": "max_profit",
    "profit_rate": 11.92,
    "timestamp": "2026-01-15 01:18:40",
    "pos_size": 5.0,
    "avg_price": 1.9120,
    "mark_price": 1.8892,
    "upl": 0.1140,
    "margin": 0.9560,
    "leverage": 10.0,
    "created_at": "2026-01-15 01:18:40",
    "updated_at": "2026-01-15 01:18:40"
}
```

#### SQLite存储 (databases/anchor_system.db - anchor_monitors表)

**新增功能**：极值变化会自动写入历史监控记录表

字段映射：
| 字段 | 说明 | 示例值 |
|------|------|--------|
| timestamp | 时间戳 | 2026-01-15 01:18:40 |
| inst_id | 币种ID | SUI-USDT-SWAP |
| pos_side | 持仓方向 | short/long |
| pos_size | 持仓数量 | 5.00 |
| avg_price | 开仓均价 | 1.9120 |
| mark_price | 标记价格 | 1.8892 |
| upl | 未实现盈亏 | 0.1140 |
| upl_ratio | 盈亏比率 | 11.92 |
| margin | 保证金 | 0.9560 |
| leverage | 杠杆倍数 | 10.0 |
| profit_rate | 利润率 | 11.92 |
| **alert_type** | **告警类型** | **extreme_max_profit** |
| alert_sent | 是否已发送 | 0 |

### 3. 前端显示

#### 历史监控记录板块

访问：https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real

**极值记录显示**：
- 🚀 **最高盈利极值刷新** - 绿色徽章（alert_type=extreme_max_profit）
- 📉 **最大亏损极值刷新** - 红色徽章（alert_type=extreme_max_loss）

**与普通记录的区别**：
- 普通盈利目标：绿色徽章 "盈利目标"
- 普通止损警告：红色徽章 "止损警告"
- **极值创新高**：绿色徽章 "最高盈利刷新" 🚀
- **极值创新低**：红色徽章 "最大亏损刷新" 📉

#### 告警历史板块

极值告警会显示特殊标题：
- 🚀 最高盈利极值刷新预警
- 📉 最大亏损极值刷新预警

## 📊 数据流程图

```
OKEx API (获取持仓)
    ↓
extreme_monitor_jsonl.py (每分钟检查)
    ↓
检测到极值变化
    ├─→ update_extreme() → extreme_real.jsonl (JSONL存储)
    ├─→ write_to_anchor_monitors() → anchor_monitors表 (SQLite存储) ⭐ 新增
    └─→ send_telegram_notification() → Telegram通知
    ↓
前端页面显示
    ├─→ /api/anchor-system/monitors → 历史监控记录
    ├─→ /api/anchor-system/alerts → 告警历史
    └─→ /api/anchor-system/profit-records → 历史极值记录
```

## 🔧 技术实现

### 核心代码

**extreme_monitor_jsonl.py** (新增函数):

```python
def write_to_anchor_monitors(self, position: Dict, record_type: str, profit_rate: float):
    """将极值变化写入anchor_monitors表（历史监控记录）"""
    try:
        import sqlite3
        
        db_path = '/home/user/webapp/databases/anchor_system.db'
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ)
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # 设置alert_type为extreme类型
        alert_type = f"extreme_{record_type}"  # extreme_max_profit 或 extreme_max_loss
        
        # 插入记录
        cursor.execute('''
            INSERT INTO anchor_monitors (
                timestamp, inst_id, pos_side, pos_size, avg_price, mark_price,
                upl, upl_ratio, margin, leverage, profit_rate, alert_type, alert_sent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            position.get('instId', ''),
            position.get('posSide', 'long'),
            abs(float(position.get('pos', 0))),
            float(position.get('avgPx', 0)),
            float(position.get('markPx', 0)),
            float(position.get('upl', 0)),
            float(position.get('uplRatio', 0)),
            float(position.get('margin', 0)),
            float(position.get('lever', 10)),
            profit_rate,
            alert_type,
            0  # alert_sent默认0
        ))
        
        conn.commit()
        conn.close()
        
        self.log(f"✅ 极值变化已写入anchor_monitors表: {position.get('instId')} {position.get('posSide')} {record_type}")
    except Exception as e:
        self.log(f"❌ 写入anchor_monitors失败: {e}")
```

### 调用时机

在 `check_and_update_extreme()` 函数中，当检测到极值变化时：

```python
# 检查是否创新高
if current_profit_rate > 0:
    if current_max_profit is None or current_profit_rate > current_max_profit:
        self.update_extreme(inst_id, pos_side, 'max_profit', current_profit_rate, position)
        # ⭐ 新增：写入anchor_monitors表
        self.write_to_anchor_monitors(position, 'max_profit', current_profit_rate)
        ...

# 检查是否创新低
elif current_profit_rate < 0:
    if current_max_loss is None or current_profit_rate < current_max_loss:
        self.update_extreme(inst_id, pos_side, 'max_loss', current_profit_rate, position)
        # ⭐ 新增：写入anchor_monitors表
        self.write_to_anchor_monitors(position, 'max_loss', current_profit_rate)
        ...
```

## 📈 使用示例

### 实际案例

```
[2026-01-15 01:18:40] 🔍 开始检查极值...
[2026-01-15 01:18:40] 📊 获取到 43 个持仓
[2026-01-15 01:18:40] 🔄 更新极值: SUI-USDT-SWAP short max_profit = 11.92%
[2026-01-15 01:18:40] 💾 已备份到: data/extreme_jsonl/extreme_real.jsonl.backup_20260115_011840
[2026-01-15 01:18:40] ✅ 已写入 92 条记录到JSONL
[2026-01-15 01:18:40] ✅ 极值变化已写入anchor_monitors表: SUI-USDT-SWAP short max_profit ⭐
[2026-01-15 01:18:40] 🎉 SUI-USDT-SWAP short 创新高: 10.83% → 11.92%
[2026-01-15 01:18:41] ✅ Telegram通知发送成功
[2026-01-15 01:18:41] ✅ 本次检查完成
```

### API查询

**查询所有监控记录**（包含极值）:
```bash
GET /api/anchor-system/monitors?limit=50
```

**查询仅极值记录**（通过前端过滤）:
```bash
GET /api/anchor-system/monitors?limit=100
# 前端过滤 alert_type.startsWith('extreme_')
```

**查询历史极值记录**（仅JSONL数据）:
```bash
GET /api/anchor-system/profit-records?trade_mode=real
```

## 🎨 前端显示效果

### 历史监控记录表

| 时间 | 币种 | 方向 | 数量 | 开仓价 | 盯盘价 | 杠杆 | 盈利比例 | **告警类型** | 发送状态 |
|------|------|------|------|--------|--------|------|----------|------------|---------|
| 2026-01-15 01:18:40 | SUI-USDT-SWAP | 做空 | 5.00 | 1.9120 | 1.8892 | 10x | +11.92% | 🚀 **最高盈利刷新** | 已发送 |
| 2025-12-30 11:15:25 | CRV-USDT-SWAP | 做空 | 16.00 | 0.4024 | 0.3843 | 10x | +44.94% | 盈利目标 | 已发送 |

### 告警样式

```html
<!-- 极值创新高 -->
<div class="alert-item profit">
    <div class="alert-header">
        <div class="alert-title">🚀 最高盈利极值刷新预警</div>
        <div class="alert-time">2026-01-15 01:18:40</div>
    </div>
    <div class="alert-details">
        SUI-USDT-SWAP • 做空 • <strong style="color: #48bb78;">+11.92%</strong>
    </div>
</div>

<!-- 极值创新低 -->
<div class="alert-item loss">
    <div class="alert-header">
        <div class="alert-title">📉 最大亏损极值刷新预警</div>
        <div class="alert-time">2026-01-15 00:10:33</div>
    </div>
    <div class="alert-details">
        SOL-USDT-SWAP • 做空 • <strong style="color: #f56565;">-14.40%</strong>
    </div>
</div>
```

## 🔄 监控频率

- **检查间隔**: 60秒（1分钟）
- **服务名称**: extreme-monitor (PM2管理)
- **日志路径**: /home/user/webapp/logs/extreme_monitor_error.log

## 📱 Telegram通知

当检测到极值变化时，会发送以下格式的通知：

**创新高**:
```
🎉 极值刷新 - 最高盈利

币种: SUI-USDT-SWAP
方向: 做空
利润率: 10.83% → 11.92% (+1.09%)
持仓: 5.00 张
开仓价: $1.9120
标记价: $1.8892
时间: 2026-01-15 01:18:40
```

**创新低**:
```
⚠️ 极值刷新 - 最大亏损

币种: SOL-USDT-SWAP
方向: 做空
利润率: -12.50% → -14.40% (-1.90%)
持仓: 10.00 张
开仓价: $145.50
标记价: $165.80
时间: 2026-01-15 00:10:33
```

## 🎯 应用场景

1. **盈利目标追踪**: 实时了解各币种的历史最佳表现
2. **风险预警**: 及时发现亏损扩大的趋势
3. **策略优化**: 分析极值出现的时间和市场条件
4. **交易决策**: 基于历史极值设置止盈止损位

## 🔍 数据查询示例

### SQL查询极值记录

```sql
-- 查询最近的极值变化
SELECT timestamp, inst_id, pos_side, profit_rate, alert_type
FROM anchor_monitors
WHERE alert_type LIKE 'extreme_%'
ORDER BY timestamp DESC
LIMIT 20;

-- 统计各币种的极值次数
SELECT inst_id, pos_side, 
       SUM(CASE WHEN alert_type = 'extreme_max_profit' THEN 1 ELSE 0 END) as max_profit_count,
       SUM(CASE WHEN alert_type = 'extreme_max_loss' THEN 1 ELSE 0 END) as max_loss_count
FROM anchor_monitors
WHERE alert_type LIKE 'extreme_%'
GROUP BY inst_id, pos_side
ORDER BY max_profit_count DESC;

-- 查询今日极值变化
SELECT *
FROM anchor_monitors
WHERE alert_type LIKE 'extreme_%'
  AND DATE(timestamp) = DATE('now')
ORDER BY timestamp DESC;
```

### Python查询示例

```python
import sqlite3

db_path = '/home/user/webapp/databases/anchor_system.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询最新的极值记录
cursor.execute("""
    SELECT timestamp, inst_id, pos_side, profit_rate, alert_type
    FROM anchor_monitors 
    WHERE alert_type LIKE 'extreme_%'
    ORDER BY timestamp DESC 
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]:.2f}% | {row[4]}")

conn.close()
```

## ✅ 测试验证

### 1. 检查监控服务状态
```bash
pm2 list | grep extreme-monitor
pm2 logs extreme-monitor --lines 50
```

### 2. 验证数据写入
```bash
# 查看JSONL文件
tail -10 data/extreme_jsonl/extreme_real.jsonl

# 查看SQLite数据库
sqlite3 databases/anchor_system.db \
  "SELECT * FROM anchor_monitors WHERE alert_type LIKE 'extreme_%' ORDER BY timestamp DESC LIMIT 5;"
```

### 3. 测试API
```bash
# 测试监控记录API
curl "http://localhost:5000/api/anchor-system/monitors?limit=10"

# 测试极值记录API
curl "http://localhost:5000/api/anchor-system/profit-records?trade_mode=real"
```

### 4. 查看前端显示
访问：https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real

## 🚀 部署状态

- ✅ 代码已修改并提交
- ✅ extreme-monitor服务已重启
- ✅ 数据写入功能已验证
- ✅ API正常返回数据
- ✅ 前端页面正常显示

## 📝 注意事项

1. **数据双写**: 极值记录会同时写入JSONL和SQLite，确保数据一致性
2. **alert_type格式**: 极值记录使用 `extreme_` 前缀，便于过滤和识别
3. **备份策略**: JSONL文件会在每次写入时自动备份
4. **监控频率**: 每60秒检查一次，避免频繁触发
5. **Telegram通知**: 需要配置telegram_config.json才能发送通知

## 🎉 功能亮点

1. **实时监控**: 每分钟自动检查所有持仓的极值变化
2. **双重存储**: JSONL文件 + SQLite数据库，数据安全可靠
3. **前端集成**: 无需额外页面，直接显示在历史监控记录中
4. **智能标记**: 极值记录使用特殊图标和颜色高亮显示
5. **通知推送**: Telegram实时推送极值变化通知

---

**完成时间**: 2026-01-15 01:20  
**功能状态**: ✅ 已上线运行  
**测试案例**: SUI-USDT-SWAP short 创新高 10.83% → 11.92%
