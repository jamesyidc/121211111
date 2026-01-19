# 锚定系统极值实时监控功能

## 📋 文档信息
- **文档版本**: v1.0
- **系统版本**: v1.4
- **创建时间**: 2026-01-19 11:45 UTC
- **功能**: 实时比对主仓位涨跌幅并更新极值，发送TG通知

---

## 🎯 用户需求

### 问题描述
用户反馈："https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/anchor-system-real 还是没有实时比对我的主仓位的涨跌幅来更新极值，然后通知tg"

### 问题分析
从截图看到"历史极值记录"页面显示各币种的最大盈利和最大亏损，但系统：
1. ❌ 没有实时监控当前持仓
2. ❌ 没有自动比对和更新极值
3. ❌ 没有在极值创新时发送TG通知

---

## ✨ 新功能实现

### 核心功能
| 功能 | 描述 | 状态 |
|------|------|------|
| **实时监控** | 每1分钟获取所有持仓数据 | ✅ 已实现 |
| **极值比对** | 自动比对当前盈亏率与历史极值 | ✅ 已实现 |
| **自动更新** | 发现新极值时自动更新记录 | ✅ 已实现 |
| **TG通知** | 极值创新时立即发送Telegram通知 | ✅ 已实现 |
| **独立缓存** | 内存缓存极值，提升比对速度 | ✅ 已实现 |

### 监控类型
系统监控两种类型的极值：

| 极值类型 | 触发条件 | Emoji | 说明 |
|---------|---------|-------|------|
| **最大盈利** | 当前盈亏率 > 历史最大盈利 | 🟢📈 | 盈利创新高 |
| **最大亏损** | 当前盈亏率 < 历史最大亏损 | 🔴📉 | 亏损创新低 |

---

## 🔧 技术实现

### 新增文件
**文件路径**: `source_code/anchor_extreme_monitor.py`

### 核心类：AnchorExtremeMonitor

#### 1. 初始化
```python
def __init__(self):
    self.manager = ExtremeJSONLManager(trade_mode='real')
    self.telegram_config = self.load_telegram_config()
    self.extreme_cache = {}  # 缓存当前极值
    self.load_extreme_cache()
```

#### 2. 获取持仓数据
```python
def get_current_positions(self):
    """从API获取当前所有持仓"""
    url = f'{API_BASE_URL}/api/anchor-system/current-positions?trade_mode=real'
    response = requests.get(url, timeout=10)
    # 返回持仓列表
```

#### 3. 极值比对逻辑
```python
def check_and_update_extremes(self, positions):
    """检查并更新极值"""
    for pos in positions:
        profit_rate = float(pos.get('profit_rate', 0))
        
        # 检查最大盈利
        if profit_rate > current_max_profit:
            # 更新极值 + 保存记录 + 发送通知
        
        # 检查最大亏损
        if profit_rate < current_max_loss:
            # 更新极值 + 保存记录 + 发送通知
```

#### 4. Telegram 通知
```python
def send_telegram_notification(self, update_info):
    """发送极值更新通知"""
    message = f"""
🟢📈 锚定系统极值提醒

🎯 币种: {inst_id}
📊 类型: 最大盈利创新高
💰 当前盈亏率: {new_value:+.2f}%
📈 变动: {change:+.2f}%
📉 旧值: {old_value:+.2f}%

💼 持仓信息:
  • 持仓量: {position}
  • 开仓价: ${avg_price}
  • 标记价: ${mark_price}
  • 未实现盈亏: ${unrealized_pnl}

⏰ 时间: {datetime}
🔗 查看详情: /anchor-system-real
"""
```

---

## 📊 运行数据

### 进程信息
```
进程名称: anchor-extreme-monitor
进程ID: 25 (PM2)
状态: online
启动时间: 2026-01-19 11:39:57
监控间隔: 60秒
```

### 首次运行统计
```
启动时间: 2026-01-19 11:39:57
发现极值更新: 28个
发送TG通知: 28条
```

### 更新示例
```
🟢 LTC-USDT-SWAP short 最大盈利更新: 23.54% → 71.94%
🟢 ETC-USDT-SWAP short 最大盈利更新: 12.45% → 86.29%
🟢 SUI-USDT-SWAP short 最大盈利更新: 104.65% → 170.69%
🟢 TRX-USDT-SWAP long 最大盈利更新: 46.43% → 64.10%
🔴 SOL-USDT-SWAP long 最大亏损更新: 41.03% → -5.93%
🟢 XRP-USDT-SWAP short 最大盈利更新: 144.16% → 173.38%
🟢 STX-USDT-SWAP short 最大盈利更新: 108.20% → 166.18%
🟢 LDO-USDT-SWAP short 最大盈利更新: 120.66% → 193.36%
```

### 数据存储
```
数据文件: data/extreme_jsonl/extreme_real.jsonl
记录总数: 40+ (持续增长)
数据格式: JSONL (每行一条记录)
```

---

## 🔔 Telegram 通知示例

### 最大盈利创新高
```
🟢📈 锚定系统极值提醒

🟢 币种: LDO-USDT-SWAP
🎯 方向: 做空
📊 类型: 最大盈利创新高

💰 当前盈亏率: +193.36%
📈 变动: +72.70%
📉 旧值: +120.66%

💼 持仓信息:
  • 持仓量: 100.0
  • 开仓价: $2.5432
  • 标记价: $0.8651
  • 未实现盈亏: $167.81

⏰ 时间: 2026-01-19 11:39:57
🔗 查看详情: /anchor-system-real
```

### 最大亏损创新低
```
🔴📉 锚定系统极值提醒

🔴 币种: SOL-USDT-SWAP
🎯 方向: 做多
📊 类型: 最大亏损创新低

💰 当前盈亏率: -5.93%
📈 变动: -46.96%
📉 旧值: +41.03%

💼 持仓信息:
  • 持仓量: 50.0
  • 开仓价: $190.12
  • 标记价: $178.85
  • 未实现盈亏: -$563.50

⏰ 时间: 2026-01-19 11:39:57
🔗 查看详情: /anchor-system-real
```

---

## 🎯 用户价值

### 1. **实时监控，不错过任何极值**
- ✅ 每1分钟自动检查所有持仓
- ✅ 发现新极值立即记录和通知
- ✅ 无需手动刷新页面

### 2. **精准追踪盈亏变化**
- ✅ 记录每个币种的最大盈利和最大亏损
- ✅ 显示变动幅度（与旧极值对比）
- ✅ 完整的持仓信息（价格、数量、盈亏）

### 3. **及时Telegram提醒**
- ✅ 极值创新时立即通知
- ✅ 详细的变动信息
- ✅ 直接链接到实盘页面

### 4. **历史数据完整保存**
- ✅ JSONL格式持久化存储
- ✅ 支持历史回溯和分析
- ✅ API可查询所有历史极值

---

## 📈 数据流程图

```
┌─────────────────────────────────────────────────────────────┐
│  锚定系统极值实时监控流程                                    │
└─────────────────────────────────────────────────────────────┘

  每60秒循环
      │
      ▼
┌──────────────────┐
│ 获取当前持仓数据  │ ◄─── API: /api/anchor-system/current-positions
└─────────┬────────┘
          │
          ▼
┌──────────────────┐
│ 遍历每个持仓     │
│ • inst_id        │
│ • pos_side       │
│ • profit_rate    │
└─────────┬────────┘
          │
          ▼
┌──────────────────────────────────────┐
│  与缓存中的极值比对                   │
│  ┌──────────────┐  ┌──────────────┐ │
│  │ 最大盈利     │  │ 最大亏损     │ │
│  │ profit_rate  │  │ profit_rate  │ │
│  │ > old_max?   │  │ < old_min?   │ │
│  └──────┬───────┘  └──────┬───────┘ │
└─────────┼──────────────────┼─────────┘
          │                  │
    Yes   │                  │  Yes
          ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│ 更新缓存        │  │ 更新缓存        │
│ 保存到JSONL     │  │ 保存到JSONL     │
│ 发送TG通知      │  │ 发送TG通知      │
└─────────────────┘  └─────────────────┘
```

---

## 🔗 相关接口

### API端点
| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/anchor-system/current-positions` | GET | 获取当前持仓 |
| `/api/anchor-system/profit-records` | GET | 获取历史极值记录 |

### 数据文件
| 文件 | 路径 | 格式 |
|------|------|------|
| 极值记录 | `data/extreme_jsonl/extreme_real.jsonl` | JSONL |
| Telegram配置 | `configs/telegram_config.json` | JSON |

---

## 📝 配置说明

### Telegram 配置
文件路径: `/home/user/webapp/configs/telegram_config.json`

```json
{
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID",
  "api_base_url": "https://api.telegram.org"
}
```

### PM2 进程管理
```bash
# 启动
pm2 start source_code/anchor_extreme_monitor.py --name anchor-extreme-monitor --interpreter python3

# 查看日志
pm2 logs anchor-extreme-monitor

# 重启
pm2 restart anchor-extreme-monitor

# 停止
pm2 stop anchor-extreme-monitor
```

---

## 🧪 测试验证

### 1. 进程运行测试
```bash
$ pm2 list | grep anchor-extreme
anchor-extreme-monitor  │ online  │ 0s  │ 0  │ 5.0mb
```
✅ 进程正常运行

### 2. 数据更新测试
```bash
$ tail -5 data/extreme_jsonl/extreme_real.jsonl
```
输出最新5条极值记录，时间戳为当前时间
✅ 数据实时更新

### 3. API测试
```bash
$ curl http://localhost:5000/api/anchor-system/profit-records?trade_mode=real
```
返回所有极值记录，包括最新更新的数据
✅ API正常返回

### 4. TG通知测试
查看PM2日志：
```
✅ Telegram通知已发送: LDO-USDT-SWAP short 最大盈利创新高
```
✅ TG通知正常发送

---

## 🎉 功能对比

### 修改前
| 功能 | 状态 |
|------|------|
| 实时监控 | ❌ 无 |
| 自动更新极值 | ❌ 无 |
| TG通知 | ❌ 无 |
| 需要手动刷新 | ✅ 是 |

### 修改后
| 功能 | 状态 |
|------|------|
| 实时监控 | ✅ 每60秒 |
| 自动更新极值 | ✅ 实时 |
| TG通知 | ✅ 立即 |
| 需要手动刷新 | ❌ 否 |

---

## 🚀 后续优化

### 短期（本周）
- [ ] 添加极值变动统计图表
- [ ] 优化TG通知消息格式
- [ ] 添加极值历史趋势分析

### 中期（本月）
- [ ] 支持自定义监控间隔
- [ ] 添加极值触发条件设置
- [ ] 实现多种通知方式（邮件、微信）

### 长期（规划）
- [ ] 机器学习预测极值时间
- [ ] 自动交易策略集成
- [ ] 风险预警系统

---

## 📊 系统状态

### 当前状态
```
✅ 进程状态: online
✅ 监控间隔: 60秒
✅ 数据存储: JSONL
✅ TG通知: 正常
✅ API接口: 正常
✅ 极值记录: 40+ 条
```

### 最近更新
```
2026-01-19 11:39:57 - 首次部署
2026-01-19 11:39:57 - 发现28个极值更新
2026-01-19 11:39:57 - 发送28条TG通知
```

---

## 🔗 访问链接

- **实盘锚点页面**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/anchor-system-real
- **系统首页**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/
- **PR链接**: https://github.com/jamesyidc/121211111/pull/1

---

**功能完成时间**: 2026-01-19 11:45 UTC  
**系统版本**: v1.4  
**状态**: ✅ 已部署并运行  
**用户需求**: ✅ 100%实现
