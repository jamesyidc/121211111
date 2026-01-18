# 27币种价格追踪器 - 完整总结

## 📊 系统概述

### 功能说明
- **目的**: 独立的币种价格追踪系统，监控27个币种相对于当天UTC+8 00:00的涨跌幅
- **基准时间**: 每天UTC+8 00:00（北京时间凌晨0点）的价格作为0%基准
- **采集间隔**: 每30分钟采集一次
- **数据粒度**: 30分钟/点，每天48个数据点

### 与OKX系统的区别

| 特性 | OKX日涨跌系统 | 新币价追踪系统 |
|-----|------------|--------------|
| 基准时间 | UTC 00:00 (早上8点) | UTC+8 00:00 (凌晨0点) |
| 采集频率 | 1分钟 | 30分钟 |
| 数据源 | OKX K线API | OKX实时价格API |
| 计算方式 | K线涨跌幅 | 价格相对涨跌幅 |
| 数据存储 | okx_day_change.jsonl | coin_prices_30min.jsonl |
| 用途 | 分钟级市场监控 | 半小时级趋势分析 |

---

## 🎯 核心代码

### 1. 数据采集脚本

**文件路径**: `source_code/coin_price_tracker.py`

**核心功能**:
- ✅ 每天凌晨自动获取UTC+8 00:00的基准价格
- ✅ 每30分钟采集一次27个币种的当前价格
- ✅ 计算相对于基准价格的涨跌幅
- ✅ 数据保存为JSONL格式

**关键方法**:
```python
def get_today_start(self):
    """获取今天UTC+8的0点时间"""
    now = datetime.now(TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start

def fetch_base_prices(self):
    """获取今天0点的基准价格（UTC+8 00:00的小时K线开盘价）"""
    # 使用1小时K线获取0点的开盘价
    
def calculate_changes(self, base_prices, current_prices):
    """计算涨跌幅: (current - base) / base * 100"""
```

---

## 📁 数据格式

### JSONL数据结构

**文件路径**: `data/coin_price_tracker/coin_prices_30min.jsonl`

```json
{
  "collect_time": "2026-01-16 20:47:43",
  "timestamp": 1768567663,
  "base_date": "2026-01-16",
  "coins": {
    "BTC": {
      "base_price": 96810.4,
      "current_price": 95407.5,
      "change_pct": -1.4491
    },
    "ETH": {
      "base_price": 3369.46,
      "current_price": 3308.45,
      "change_pct": -1.8107
    },
    // ... 其他25个币种
  },
  "total_coins": 27,
  "valid_coins": 27
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `collect_time` | string | 采集时间（UTC+8） |
| `timestamp` | int | Unix时间戳 |
| `base_date` | string | 基准日期 |
| `coins` | object | 27个币种的详细数据 |
| `coins.*.base_price` | float | 当天0点的基准价格 |
| `coins.*.current_price` | float | 当前价格 |
| `coins.*.change_pct` | float | 涨跌幅（%） |
| `total_coins` | int | 总币种数（27） |
| `valid_coins` | int | 成功采集的币种数 |

---

## 🌐 API端点

### 1. 获取最新N条数据

**端点**: `/api/coin-price-tracker/latest`

**方法**: GET

**参数**:
- `limit`: 返回最新N条记录（默认48，即24小时）

**示例**:
```bash
curl "http://localhost:5000/api/coin-price-tracker/latest?limit=10"
```

**响应**:
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "collect_time": "2026-01-16 20:47:43",
      "coins": { ... },
      // ...
    }
  ]
}
```

### 2. 查询历史数据

**端点**: `/api/coin-price-tracker/history`

**方法**: GET

**参数**:
- `start_time`: 开始时间（格式: YYYY-MM-DD HH:MM:SS）
- `end_time`: 结束时间（格式: YYYY-MM-DD HH:MM:SS）

**示例**:
```bash
curl "http://localhost:5000/api/coin-price-tracker/history?start_time=2026-01-16%2000:00:00&end_time=2026-01-16%2023:59:59"
```

**响应**:
```json
{
  "success": true,
  "count": 48,
  "start_time": "2026-01-16 00:00:00",
  "end_time": "2026-01-16 23:59:59",
  "data": [ ... ]
}
```

---

## 🚀 服务管理

### PM2守护进程

**进程名**: `coin-price-tracker`

**启动命令**:
```bash
pm2 start source_code/coin_price_tracker.py \
    --name coin-price-tracker \
    --interpreter python3
```

**管理命令**:
```bash
# 查看状态
pm2 status coin-price-tracker

# 查看日志
pm2 logs coin-price-tracker --lines 50

# 重启
pm2 restart coin-price-tracker

# 停止
pm2 stop coin-price-tracker
```

### 日志文件

- **正常日志**: `logs/coin_price_tracker.log`
- **错误日志**: `logs/coin_price_tracker_error.log`

---

## 📈 27个币种列表

| 序号 | 币种 | 说明 |
|-----|------|------|
| 1 | BTC | Bitcoin |
| 2 | ETH | Ethereum |
| 3 | XRP | Ripple |
| 4 | BNB | Binance Coin |
| 5 | SOL | Solana |
| 6 | LTC | Litecoin |
| 7 | DOGE | Dogecoin |
| 8 | SUI | Sui |
| 9 | TRX | TRON |
| 10 | TON | Toncoin |
| 11 | ETC | Ethereum Classic |
| 12 | BCH | Bitcoin Cash |
| 13 | HBAR | Hedera |
| 14 | XLM | Stellar |
| 15 | FIL | Filecoin |
| 16 | LINK | Chainlink |
| 17 | CRO | Crypto.com Coin |
| 18 | DOT | Polkadot |
| 19 | UNI | Uniswap |
| 20 | NEAR | NEAR Protocol |
| 21 | APT | Aptos |
| 22 | CFX | Conflux |
| 23 | CRV | Curve DAO Token |
| 24 | STX | Stacks |
| 25 | LDO | Lido DAO |
| 26 | TAO | Bittensor |
| 27 | AAVE | Aave |

---

## 🔍 验证方法

### 1. 检查进程状态
```bash
cd /home/user/webapp
pm2 status coin-price-tracker
```

**预期输出**: 
- status: `online`
- restarts: 0
- uptime: > 0

### 2. 检查数据文件
```bash
cd /home/user/webapp
ls -lh data/coin_price_tracker/coin_prices_30min.jsonl
tail -1 data/coin_price_tracker/coin_prices_30min.jsonl | jq '.'
```

**预期输出**:
- 文件存在且大小在增长
- JSON格式正确，包含27个币种数据

### 3. 测试API端点
```bash
# 测试最新数据
curl -s "http://localhost:5000/api/coin-price-tracker/latest?limit=3" | jq '.success'

# 测试历史数据
curl -s "http://localhost:5000/api/coin-price-tracker/history?start_time=2026-01-16%2000:00:00&end_time=2026-01-16%2023:59:59" | jq '.count'
```

**预期输出**:
- `.success` = `true`
- `.count` > 0

### 4. 查看日志
```bash
cd /home/user/webapp
tail -50 logs/coin_price_tracker.log
```

**预期输出**:
- `✅ 基准价格获取完成: 27/27`
- `✅ 当前价格获取完成: 27/27`
- `✅ 数据已保存: 27/27 个币种`
- `⏰ 下次采集时间: ...`

---

## 📊 数据示例

### 采集时日志输出

```
2026-01-16 20:47:43 - INFO - 📊 获取今天UTC+8 00:00的基准价格: 2026-01-16 00:00:00+08:00
2026-01-16 20:47:51 - INFO - ✅ 基准价格获取完成: 27/27
2026-01-16 20:47:51 - INFO - 📊 获取当前价格...
2026-01-16 20:47:51 - INFO - ✅ 当前价格获取完成: 27/27
2026-01-16 20:47:51 - INFO - ✅ 数据已保存: 27/27 个币种

2026-01-16 20:47:51 - INFO - 📈 涨幅TOP5:
2026-01-16 20:47:51 - INFO -   TRX: +0.30%
2026-01-16 20:47:51 - INFO -   BNB: -0.79%
2026-01-16 20:47:51 - INFO -   CRO: -0.85%
2026-01-16 20:47:51 - INFO -   SOL: -1.06%
2026-01-16 20:47:51 - INFO -   BTC: -1.45%

2026-01-16 20:47:51 - INFO - 📉 跌幅TOP5:
2026-01-16 20:47:51 - INFO -   DOGE: -4.58%
2026-01-16 20:47:51 - INFO -   STX: -4.62%
2026-01-16 20:47:51 - INFO -   DOT: -4.76%
2026-01-16 20:47:51 - INFO -   TAO: -5.04%
2026-01-16 20:47:51 - INFO -   APT: -7.03%

2026-01-16 20:47:51 - INFO - ⏰ 下次采集时间: 2026-01-16 21:17:51
```

---

## 🎨 前端集成（待开发）

### 建议的展示方式

1. **实时数据卡片**
   - 显示27个币种的当前涨跌幅
   - 按涨跌幅排序（涨幅榜/跌幅榜）
   - 显示相对于0点的变化

2. **30分钟趋势图**
   - X轴：时间（00:00 ~ 23:30）
   - Y轴：涨跌幅（%）
   - 多条曲线：27个币种或总体趋势

3. **日内波动监控**
   - 最大涨幅/跌幅
   - 波动最大的币种
   - 整体市场情绪

4. **对比分析**
   - 与OKX日涨跌数据对比
   - 显示北京时间0点vs UTC 0点的差异

---

## 🔧 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                  币价追踪系统架构                          │
└─────────────────────────────────────────────────────────┘

    OKX API
       │
       ├─ market/candles (获取0点基准价)
       └─ market/tickers (获取实时价格)
       │
       ↓
┌──────────────────────┐
│ coin_price_tracker.py│  ← PM2守护进程
│  - 基准价格获取       │     (每30分钟运行)
│  - 实时价格采集       │
│  - 涨跌幅计算         │
└──────────────────────┘
       │
       ↓ (写入JSONL)
┌─────────────────────────────┐
│ coin_prices_30min.jsonl     │
│  - collect_time             │
│  - base_date                │
│  - coins (27个币种数据)      │
└─────────────────────────────┘
       │
       ↓ (读取)
┌──────────────────────────────────┐
│  Flask API (app_new.py)          │
│  ├─ /api/coin-price-tracker/     │
│  │   latest                       │
│  └─ /api/coin-price-tracker/     │
│      history                      │
└──────────────────────────────────┘
       │
       ↓
┌──────────────────────────────┐
│  前端页面 (待开发)             │
│  - 实时卡片                   │
│  - 趋势图表                   │
│  - 统计分析                   │
└──────────────────────────────┘
```

---

## ✅ 当前状态

### 已完成 ✅
- [x] 数据采集脚本开发完成
- [x] PM2守护进程启动
- [x] 数据存储JSONL格式
- [x] API端点实现（2个）
- [x] 测试验证通过
- [x] Git代码提交

### 运行状态 🟢
- **进程状态**: 在线（online）
- **采集频率**: 30分钟/次
- **数据质量**: 27/27 币种全部成功
- **日志输出**: 正常
- **API服务**: 正常

### 待开发 🔨
- [ ] 前端展示页面
- [ ] 数据可视化图表
- [ ] 告警功能（大幅涨跌提醒）
- [ ] 历史数据回填（可选）
- [ ] 与其他系统的数据联动

---

## 📝 使用场景

### 1. 日内趋势监控
- 每30分钟查看市场变化
- 识别日内高点/低点
- 监控市场情绪转换

### 2. 基准对比分析
- 对比UTC 0点 vs UTC+8 0点的差异
- 分析不同时区开盘对币价的影响
- 研究日内波动规律

### 3. 策略回测
- 使用30分钟粒度的历史数据
- 验证日内交易策略
- 评估进出场时机

### 4. 市场报告
- 生成每日市场总结
- 统计涨跌幅分布
- 识别异常波动币种

---

## 🎯 总结

### 核心特点
1. ✅ **独立系统**: 与OKX日涨跌系统并行运行
2. ✅ **北京时间基准**: 以UTC+8 00:00为0%基准
3. ✅ **30分钟粒度**: 适合日内趋势分析
4. ✅ **27币种覆盖**: 主流币种全覆盖
5. ✅ **API就绪**: 2个端点可供前端调用

### 数据流向
```
OKX API → 采集器 → JSONL文件 → Flask API → 前端(待开发)
```

### 下一步
1. 开发前端展示页面
2. 添加数据可视化图表
3. 实现告警功能
4. 与其他系统联动

---

**文档生成时间**: 2026-01-16 20:50  
**系统版本**: v1.0.0  
**维护者**: AI Development Team
