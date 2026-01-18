# OKX 27币种涨跌指标集成总结

## 📅 完成时间
2026-01-16

## ✅ 已完成的功能

### 1. 修复SAR加载失败问题

**问题**：anchor-system-real页面SAR斜率数据显示"--"

**原因**：
- 前端调用的API端点 `/api/sar-slope/latest-jsonl` 不存在
- 实际只有 `/api/sar-slope/latest` 端点

**修复**：
1. 在`app_new.py`中添加了`/api/sar-slope/latest-jsonl`端点
2. 从JSONL文件直接读取数据：`/home/user/webapp/data/sar_slope_jsonl/latest_sar_slope.jsonl`
3. 返回格式与前端期望的格式一致

**调整筛选阈值**：
- **原阈值**：偏多比>80% (slope_value > 0.8)，偏空比>80% (slope_value < -0.8)
- **问题**：实际slope_value范围为±0.5556，无法达到±0.8
- **新阈值**：偏多比≥33% (slope_value ≥ 0.33)，偏空比≥33% (slope_value ≤ -0.33)
- **当前统计**：
  - 偏多比≥33%：13个币种（APT、BNB、CFX、CRV、DOT、ETH、FIL、LDO、NEAR、STX、SUI、TAO、UNI）
  - 偏空比≥33%：10个币种（AAVE、BCH、BTC、CRO、DOGE、HBAR、LINK、SOL、TRX、XLM）

---

### 2. OKX 27币种涨跌指标实现

#### 2.1 实时数据采集
**采集器**：`okx_day_change_collector.py`
- **采集频率**：每60秒一次
- **币种数量**：27个
- **数据来源**：OKX API (`https://www.okx.com/api/v5/market/tickers`)

**监控币种列表**：
```
BTC, ETH, XRP, BNB, SOL, LTC, DOGE, SUI, TRX, TON, 
ETC, BCH, HBAR, XLM, FIL, LINK, CRO, DOT, UNI, NEAR, 
APT, CFX, CRV, STX, LDO, TAO, AAVE
```

**计算公式**：
```
当日涨跌% = (当前价格 - UTC+8开盘价) / UTC+8开盘价 × 100
总涨跌指标 = Σ(各币种涨跌%)
平均涨跌 = 总涨跌指标 / 币种数量
```

**数据存储**：
- **路径**：`/home/user/webapp/data/okx_trading_jsonl/okx_day_change.jsonl`
- **格式**：JSONL（每行一个JSON对象）
- **字段**：
  - `record_time`: 记录时间（字符串）
  - `timestamp`: Unix时间戳
  - `total_change`: 总涨跌幅
  - `average_change`: 平均涨跌幅
  - `day_changes`: 各币种涨跌详情（对象）
  - `success_count`: 成功采集币种数
  - `failed_count`: 失败币种数
  - `total_symbols`: 总币种数

**PM2进程**：
- **名称**：`okx-day-change-collector`
- **状态**：✅ 运行中
- **运行时间**：38分钟

#### 2.2 历史数据回填

**回填脚本**：`okx_day_change_backfill_hourly.py`
- **回填时间范围**：2026-01-03 00:00 至 2026-01-15 23:00
- **回填粒度**：小时级（每小时一个数据点）
- **预计数据点**：311个
- **当前进度**：正在进行中（已完成约14小时，共64条记录）

**为什么使用小时粒度**：
- 分钟级回填需要约18,000+个数据点（13天×24小时×60分钟）
- 小时级回填只需311个数据点，大幅减少API调用和时间
- 实时采集器仍然按分钟采集最新数据

**数据排序**：
- 自动按时间戳排序，保证数据的时间连续性
- 最早记录：2026-01-03 00:00:00
- 最新记录：2026-01-16 17:50:11+

#### 2.3 API端点

**1. 获取最新数据**
```
GET /api/okx-day-change/latest?limit=<条数>
```
- **默认limit**：60（最近1小时，每分钟1条）
- **返回字段**：
  ```json
  {
    "success": true,
    "count": 60,
    "data": [...],
    "data_source": "JSONL"
  }
  ```

**2. 获取历史数据**
```
GET /api/okx-day-change/history?limit=<条数>&time=<时间点>
```
- 支持查询指定时间范围的数据

---

### 3. 前端页面集成

#### 3.1 anchor-system-real 页面（已完成）
**页面地址**：`https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/anchor-system-real`

**集成内容**：
1. **逃顶信号趋势图**：新增OKX 27币种总涨跌曲线
   - 紫色曲线显示总涨跌%
   - 使用右Y轴显示百分比
   - 与24小时/2小时信号曲线同时展示

2. **数据对齐**：
   - OKX数据按时间对齐到逃顶信号的时间点
   - 自动处理时间格式差异

3. **图表配置**：
   - 左Y轴：信号数量
   - 右Y轴：OKX总涨跌%
   - 三条曲线：24小时信号、2小时信号、OKX涨跌

#### 3.2 escape-signal-history 页面（已完成）
**页面地址**：`https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history`

**集成内容**：
1. **数据加载**：
   - 同时加载逃顶信号数据、空单盈利数据、OKX涨跌数据
   - API调用：`/api/okx-day-change/latest?limit=10080` （7天数据）

2. **图表更新**：
   - 添加OKX 27币种总涨跌曲线
   - 紫色曲线，右Y轴显示
   - 与逃顶信号、空单盈利标记同时展示

3. **时间对齐**：
   - 自动将OKX数据对齐到逃顶信号的时间轴
   - 支持不同数据源的时间戳格式

---

### 4. 1小时爆仓金额曲线

**API端点**：
```
GET /api/panic/hour1-curve?hours=<小时数>
```

**功能**：
- 返回指定小时数的1小时爆仓金额曲线
- 数据粒度：1分钟一个点
- 数据来源：`panic_wash_index.jsonl`

**返回字段**：
- `record_time`: 记录时间
- `hour_1_amount`: 1小时爆仓金额（万美金）
- `hour_24_amount`: 24小时爆仓金额（万美金）
- `panic_index`: 恐慌指数
- `wash_index`: 清洗指数

**数据源**：
- 路径：`/home/user/webapp/data/panic_jsonl/panic_wash_index.jsonl`
- 采集频率：每60秒一次
- 采集器：`panic-collector` (PM2进程)

---

## 📊 当前运行状态

### PM2进程列表
| 进程名 | 状态 | 运行时间 | 功能 |
|--------|------|----------|------|
| flask-app | ✅ online | 3秒 | Flask Web服务 |
| okx-day-change-collector | ✅ online | 38分钟 | OKX实时采集器 |
| panic-collector | ✅ online | 49分钟 | 爆仓数据采集器 |
| sar-jsonl-collector | ✅ online | 18小时 | SAR数据采集器 |

### 数据文件状态
| 文件路径 | 当前记录数 | 时间范围 |
|----------|-----------|----------|
| `data/okx_trading_jsonl/okx_day_change.jsonl` | 64+ | 2026-01-03 00:00 ~ 2026-01-16 17:50+ |
| `data/panic_jsonl/panic_wash_index.jsonl` | 持续更新 | 每60秒一条 |
| `data/sar_slope_jsonl/latest_sar_slope.jsonl` | 27条 | 最新SAR斜率 |

### 回填进度
- **当前时间点**：2026-01-03 14:00
- **完成数量**：64/311（约20.6%）
- **预计完成时间**：约60分钟后

---

## 🔧 技术架构

### 数据流程
```
OKX API
  ↓
okx_day_change_collector.py (每60秒)
  ↓
okx_day_change.jsonl (JSONL存储)
  ↓
OKXTradingJSONLManager (数据管理)
  ↓
Flask API (/api/okx-day-change/latest)
  ↓
前端页面 (ECharts图表展示)
```

### 文件结构
```
/home/user/webapp/
├── source_code/
│   ├── app_new.py                          # Flask应用（添加了OKX和SAR API）
│   ├── okx_day_change_collector.py         # OKX实时采集器
│   ├── okx_day_change_backfill_hourly.py   # OKX历史回填脚本
│   ├── okx_trading_jsonl_manager.py        # OKX数据管理器
│   └── templates/
│       ├── anchor_system_real.html         # 已集成OKX曲线
│       └── escape_signal_history.html      # 已集成OKX曲线
└── data/
    ├── okx_trading_jsonl/
    │   └── okx_day_change.jsonl           # OKX数据存储
    ├── panic_jsonl/
    │   └── panic_wash_index.jsonl         # 爆仓数据存储
    └── sar_slope_jsonl/
        └── latest_sar_slope.jsonl         # SAR斜率数据
```

---

## 🎯 核心指标

### OKX 27币种涨跌指标
- **当前总涨跌**：实时更新（最近数据约-23.3%）
- **平均涨跌**：实时更新（最近数据约-0.86%）
- **成功率**：100%（27/27币种）

### SAR斜率指标
- **偏多比≥33%**：13个币种
- **偏空比≥33%**：10个币种
- **数据更新**：每5分钟

### 爆仓金额指标
- **1小时爆仓金额**：实时更新
- **24小时爆仓金额**：实时更新
- **恐慌指数**：实时更新

---

## 🌐 访问地址

**主系统**：
- https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/anchor-system-real

**历史数据页面**：
- https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history

**API端点测试**：
```bash
# OKX最新数据
curl "https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/api/okx-day-change/latest?limit=10"

# SAR斜率数据
curl "https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/api/sar-slope/latest-jsonl"

# 1小时爆仓曲线
curl "https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/api/panic/hour1-curve?hours=1"
```

---

## 📝 Git提交记录

```
295b92e - feat: 修复SAR加载失败并添加OKX27币种涨跌指标
933e797 - feat: 添加1小时爆仓曲线API endpoint
2f6ac7e - docs: 添加实现总结文档
cd47871 - fix: 降低SAR斜率筛选阈值到33%
32210de - feat: 添加OKX历史数据回填功能
```

---

## ✅ 全部完成的任务

1. ✅ 修复SAR加载失败问题（添加JSONL端点）
2. ✅ 调整SAR筛选阈值到合理范围（33%）
3. ✅ 实现OKX 27币种涨跌实时采集器
4. ✅ 创建OKX数据JSONL管理器
5. ✅ 添加OKX API端点（latest和history）
6. ✅ 在anchor-system-real页面集成OKX曲线
7. ✅ 在escape-signal-history页面集成OKX曲线
8. ✅ 创建OKX历史数据回填脚本（小时粒度）
9. ✅ 启动历史数据回填（从1月3日开始）
10. ✅ 添加1小时爆仓金额曲线API
11. ✅ 数据排序和时间对齐处理

---

## 📌 注意事项

1. **数据回填**：
   - 历史回填使用小时粒度（每小时一个点）
   - 实时采集使用分钟粒度（每分钟一个点）
   - 两种粒度的数据会自动合并和排序

2. **API频率限制**：
   - OKX API有频率限制
   - 回填脚本已加入延迟（0.5秒/批）
   - 实时采集器每60秒采集一次

3. **数据存储**：
   - 所有数据使用JSONL格式
   - 按时间戳排序
   - 支持快速追加和读取

4. **前端展示**：
   - 图表自动加载最新数据
   - 支持时间对齐和空值处理
   - 响应式布局，支持移动端

---

## 🎉 总结

所有功能已全部实现并投入运行：
- ✅ SAR加载问题已修复
- ✅ OKX 27币种涨跌指标已上线
- ✅ 历史数据回填正在进行中
- ✅ 前端页面已完整集成
- ✅ API端点全部可用
- ✅ PM2进程稳定运行

系统现在可以实时监控27个主流加密货币的涨跌情况，并将其作为市场情绪的综合指标，与逃顶信号、爆仓数据、SAR趋势等多个维度的数据结合，为交易决策提供全面的数据支持。
