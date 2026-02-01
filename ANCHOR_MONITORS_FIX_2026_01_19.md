# 锚定系统历史监控记录修复

**修复时间**: 2026-01-19 14:30  
**问题**: 历史监控记录没有更新，最后记录停留在 2026-01-17 16:53:52  
**状态**: ✅ **已修复并正常运行**

---

## 🔍 问题诊断

### 发现的问题
1. **数据库中最后的记录**: 2026-01-17 16:53:52（2天前）
2. **数据库记录总数**: 43,500条
3. **前端显示**: 历史监控记录表格没有更新

### 根本原因
- 系统中有多个监控程序：
  - `anchor_profit_monitor.py`: 监控盈利统计，**只写入JSONL文件**
  - `anchor_extreme_monitor.py`: 监控极值，**只写入JSONL文件**
  - `anchor_system.py`: 主监控程序，**负责写入数据库**

- **`anchor_system.py` 没有在运行**，导致数据库没有更新
- 前端的"历史监控记录"从数据库 `anchor_monitors` 表读取数据
- 由于数据库没有更新，前端显示的是2天前的数据

---

## ✅ 修复方案

### 1. 启动缺失的监控程序
```bash
pm2 start source_code/anchor_system.py \
    --name anchor-system-monitor \
    --interpreter python3 \
    --log-date-format "YYYY-MM-DD HH:mm:ss"
```

### 2. 保存PM2配置
```bash
pm2 save
```

---

## 📊 验证结果

### 数据库更新情况
```
✅ 最新5条监控记录:
  2026-01-19 14:27:11 | SOL-USDT-SWAP | short | 100.05% | profit_target
  2026-01-19 14:27:10 | HBAR-USDT-SWAP | short | 179.69% | profit_target
  2026-01-19 14:27:08 | CFX-USDT-SWAP | short | 127.73% | profit_target
  2026-01-19 14:27:07 | XLM-USDT-SWAP | short | 147.03% | profit_target
  2026-01-19 14:27:05 | FIL-USDT-SWAP | short | 164.30% | profit_target

📊 今天的记录数: 27条
```

### API测试结果
```bash
✅ API Success: True
📊 Total records: 10

✨ 最新5条监控记录:
  1. 2026-01-19 14:27:22 | CRV-USDT-SWAP | short | 128.26%
  2. 2026-01-19 14:27:21 | DOT-USDT-SWAP | short | 153.20%
  3. 2026-01-19 14:27:19 | LDO-USDT-SWAP | short | 187.73%
  4. 2026-01-19 14:27:18 | APT-USDT-SWAP | short | 182.87%
  5. 2026-01-19 14:27:16 | CRO-USDT-SWAP | short | 133.38%
```

### PM2进程状态
```bash
✅ anchor-system-monitor    | online  | pid: 247668
✅ anchor-profit-monitor    | online  | pid: 193182
✅ anchor-extreme-monitor   | online  | pid: 222514
```

---

## 🔧 技术细节

### 程序职责分工

#### 1. anchor_system.py (anchor-system-monitor)
- **作用**: 主监控程序
- **数据源**: OKEx API (实盘) / SQLite (模拟盘)
- **写入目标**: `databases/anchor_system.db` → `anchor_monitors` 表
- **监控内容**:
  - 所有持仓的盈亏情况
  - 触发盈利目标（>= 40%）
  - 触发止损警告（<= -10%）
  - 极值记录更新
- **数据字段**:
  ```sql
  CREATE TABLE anchor_monitors (
      id INTEGER PRIMARY KEY,
      timestamp TEXT,
      inst_id TEXT,
      pos_side TEXT,
      pos_size REAL,
      avg_price REAL,
      mark_price REAL,
      upl REAL,
      upl_ratio REAL,
      margin REAL,
      leverage REAL,
      profit_rate REAL,
      alert_type TEXT,
      alert_sent INTEGER
  )
  ```

#### 2. anchor_profit_monitor.py
- **作用**: 盈利统计监控
- **写入目标**: `data/anchor_profit_stats/anchor_profit_stats.jsonl`
- **监控内容**:
  - 多头/空单统计
  - 盈利分布（<= 40%, >= 80%, >= 120%）
  - 2小时逃顶信号

#### 3. anchor_extreme_monitor.py
- **作用**: 极值实时监控
- **写入目标**: `data/extreme_jsonl/extreme_real.jsonl`
- **监控内容**:
  - 每个币种的最高利润 (max_profit)
  - 每个币种的最大亏损 (max_loss)
  - 发送Telegram通知

---

## 📈 数据流程

```
锚定持仓数据
    ↓
┌────────────────────────────────────┐
│ anchor_system.py                   │
│ (anchor-system-monitor)            │
│ - 每60秒采集持仓数据               │
│ - 计算盈亏率                       │
│ - 检查触发条件                     │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│ databases/anchor_system.db         │
│ → anchor_monitors (历史记录)       │
│ → anchor_alerts (告警记录)         │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│ API: /api/anchor-system/monitors   │
│ 返回最新监控记录                   │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│ 前端: 锚定系统实盘页面             │
│ "历史监控记录" 表格显示            │
└────────────────────────────────────┘
```

---

## ⚙️ 配置文件

### anchor_config.json
```json
{
  "monitor": {
    "profit_target": 40.0,
    "loss_limit": -10.0,
    "check_interval": 60,
    "alert_cooldown": 30,
    "only_short_positions": true,
    "trade_mode": "real"
  },
  "database": {
    "path": "/home/user/webapp/databases/anchor_system.db"
  },
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  }
}
```

### PM2配置
```bash
pm2 list | grep anchor
│ 27 │ anchor-system-monitor   │ online  │ 247668   │ 0min   │
│ 25 │ anchor-extreme-monitor  │ online  │ 222514   │ 2h     │
│ 9  │ anchor-profit-monitor   │ online  │ 193182   │ 6h     │
```

---

## 🎯 API端点

### GET /api/anchor-system/monitors
**描述**: 获取持仓监控历史记录

**参数**:
- `limit` (可选): 返回记录数量，默认100

**返回示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 43543,
      "timestamp": "2026-01-19 14:27:22",
      "inst_id": "CRV-USDT-SWAP",
      "pos_side": "short",
      "pos_size": 15.0,
      "avg_price": 0.4506,
      "mark_price": 0.3928,
      "upl": 0.8669,
      "upl_ratio": 1.2826,
      "margin": 0.6759,
      "leverage": 10.0,
      "profit_rate": 128.26,
      "alert_type": "profit_target",
      "alert_sent": 0
    }
  ],
  "total": 10
}
```

### GET /api/anchor-system/alerts
**描述**: 获取告警历史记录

**参数**:
- `limit` (可选): 返回记录数量，默认50

---

## 🔔 监控触发条件

### 盈利目标 (profit_target)
- **条件**: 收益率 >= 40%
- **alert_type**: `profit_target`
- **动作**: 记录到数据库，发送Telegram通知（如配置）

### 止损警告 (loss_warning)
- **条件**: 收益率 <= -10%
- **alert_type**: `loss_warning`
- **动作**: 记录到数据库，发送Telegram通知

### 极值记录 (extreme_max_profit / extreme_max_loss)
- **条件**: 刷新历史最高盈利或最大亏损
- **alert_type**: `extreme_max_profit` 或 `extreme_max_loss`
- **动作**: 更新极值记录，发送通知

---

## 📱 前端页面

### 访问地址
```
https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/anchor-system-real
```

### 显示内容
1. **持仓概览**: 当前持仓数量、盈亏情况
2. **历史监控记录**: 
   - 时间戳
   - 币种 (inst_id)
   - 方向 (pos_side)
   - 持仓量 (pos_size)
   - 开仓价 (avg_price)
   - 标记价 (mark_price)
   - 盈亏额 (upl)
   - 收益率 (profit_rate)
   - 告警类型 (alert_type)
3. **告警记录**: 历史触发的告警
4. **27币实时涨跌**: 27个主流币种的实时价格和涨跌幅

---

## ✅ 修复完成确认

### 修复前
- ❌ 数据库最后记录: 2026-01-17 16:53:52
- ❌ 前端显示: 无更新
- ❌ anchor-system-monitor: 未运行

### 修复后
- ✅ 数据库最新记录: 2026-01-19 14:27:22
- ✅ 前端显示: 正常更新
- ✅ anchor-system-monitor: 在线运行
- ✅ API响应: 正常
- ✅ 今天新增记录: 27条

---

## 🚨 注意事项

### 1. 数据库路径
- **生产环境**: `/home/user/webapp/databases/anchor_system.db`
- **确保目录存在**: `mkdir -p /home/user/webapp/databases/`

### 2. OKEx API配置
- **配置文件**: `source_code/okex_api_config.py`
- **必需字段**: 
  - `OKEX_API_KEY`
  - `OKEX_SECRET_KEY`
  - `OKEX_PASSPHRASE`
  - `OKEX_REST_URL`

### 3. 监控频率
- **检测间隔**: 60秒
- **告警冷却**: 30分钟（同一币种同一类型告警）

### 4. PM2自动重启
- 配置已保存: `pm2 save`
- 开机自启动: `pm2 startup`（如需要）

---

## 📚 相关文件

### 核心代码
- `source_code/anchor_system.py`: 主监控程序
- `source_code/anchor_profit_monitor.py`: 盈利统计监控
- `source_code/anchor_extreme_monitor.py`: 极值监控

### 配置文件
- `source_code/anchor_config.json`: 监控配置
- `source_code/okex_api_config.py`: OKEx API配置
- `configs/telegram_config.json`: Telegram配置

### 数据文件
- `databases/anchor_system.db`: 主数据库
- `data/anchor_profit_stats/anchor_profit_stats.jsonl`: 盈利统计
- `data/extreme_jsonl/extreme_real.jsonl`: 极值记录

### 日志文件
- `/home/user/.pm2/logs/anchor-system-monitor-out.log`: 标准输出
- `/home/user/.pm2/logs/anchor-system-monitor-error.log`: 错误日志

---

## 🎉 总结

**问题**: 历史监控记录没有更新（2天未更新）  
**原因**: `anchor_system.py` 监控程序未运行  
**修复**: 启动 `anchor-system-monitor` 进程  
**结果**: 数据库正常更新，前端正常显示  

**当前状态**: ✅ 系统完全正常运行

---

**作者**: GenSpark AI Developer  
**最后更新**: 2026-01-19 14:30 Beijing Time
