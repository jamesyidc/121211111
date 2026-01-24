# 支撑压力线系统 - 完整文件清单

**生成时间**: 2026-01-24 20:20 (北京时间)  
**系统版本**: 按日期存储版本  
**状态**: ✅ 最新重构完成

---

## 📋 目录
1. [核心Python文件](#核心python文件)
2. [HTML前端文件](#html前端文件)
3. [数据存储](#数据存储)
4. [PM2配置](#pm2配置)
5. [API路由](#api路由)
6. [数据库](#数据库)
7. [文档文件](#文档文件)

---

## 🐍 核心Python文件

### 1. 数据管理器 (最新)
```
文件: source_code/support_resistance_daily_manager.py
状态: ✅ 最新 (按日期存储)
大小: 12.9 KB
功能: 
  - 按日期分文件存储和读取
  - 统一levels和snapshots格式
  - 支持按日期查询历史数据
  - 自动清理旧数据
关键方法:
  - write_level_record()
  - write_snapshot_record()
  - get_latest_levels()
  - get_latest_snapshot()
  - get_levels_by_date()
  - get_snapshots_by_date()
  - get_available_dates()
  - cleanup_old_data(days)
```

### 2. Levels采集器
```
文件: source_code/support_resistance_collector.py
状态: ✅ 已更新 (使用新管理器)
大小: ~15 KB
功能:
  - 每30秒采集27个币种的支撑压力线
  - 计算支撑线、压力线、位置百分比
  - 判断告警场景
  - 写入数据库和JSONL
监控币种: 27个 (BTC, ETH, XRP, BNB, SOL, LTC, DOGE, SUI, TRX, TON, ETC, BCH, HBAR, XLM, FIL, LINK, CRO, DOT, AAVE, UNI, NEAR, APT, CFX, CRV, STX, LDO, TAO)
采集频率: 30秒
数据源: OKX API
```

### 3. Snapshots采集器
```
文件: source_code/support_resistance_snapshot_collector.py
状态: ✅ 已更新 (使用新管理器)
大小: ~10 KB
功能:
  - 每60秒生成场景快照
  - 统计4种告警场景的币种数量
  - 记录符合条件的币种列表
  - 写入数据库和JSONL
采集频率: 60秒
场景统计:
  - 场景1: 7天位置 <= 5% (低位支撑)
  - 场景2: 7天位置 >= 95% (高位压力)
  - 场景3: 48小时位置 <= 5% (短期支撑)
  - 场景4: 48小时位置 >= 95% (短期压力)
```

### 4. API适配器
```
文件: support_resistance_api_adapter.py
状态: ✅ 已更新 (使用新管理器)
位置: /home/user/webapp/
大小: 11.9 KB
功能:
  - 为Flask应用提供统一的数据访问接口
  - 格式化数据返回
  - 支持按日期查询
关键方法:
  - get_all_symbols_latest()
  - get_symbol_detail(symbol, limit, date)
  - get_snapshots(limit, date)
  - get_statistics()
```

### 5. 旧版管理器 (保留，向后兼容)
```
文件: support_resistance_jsonl_manager.py
状态: ⚠️ 旧版 (已被新管理器替代)
位置: /home/user/webapp/
大小: 13.5 KB
功能: 单文件JSONL存储 (不再使用)
```

### 6. 数据迁移脚本
```
文件: source_code/migrate_support_resistance_to_daily.py
状态: ✅ 已执行
大小: ~8 KB
功能:
  - 将旧的单文件JSONL迁移到按日期分文件
  - 迁移结果: 739,569条记录 (99.999%成功)
```

### 7. 数据导出工具
```
文件: source_code/export_support_resistance_data.py
状态: ✅ 可用
功能: 导出支撑压力线数据为JSON
```

### 8. 数据导入工具
```
文件: source_code/import_support_resistance_data.py
状态: ✅ 可用
功能: 从JSON导入支撑压力线数据
```

### 9. 数据同步工具
```
文件: source_code/sync_support_resistance_snapshots.py
状态: ✅ 可用
功能: 同步快照数据
```

---

## 🌐 HTML前端文件

### 1. 主页面
```
文件: source_code/templates/support_resistance.html
状态: ✅ 在用
路由: /support-resistance
大小: ~50 KB
功能:
  - 27个币种支撑压力线实时展示
  - 4种告警场景统计卡片
  - 历史趋势图表 (ECharts)
  - 抄底/逃顶信号标记
  - 实时数据更新 (每30秒)
数据源:
  - /api/support-resistance/latest
  - /api/support-resistance/snapshots
  - /api/support-resistance/chart-data
  - /api/support-resistance/signals-computed
特性:
  - 响应式布局
  - 颜色标识 (绿色支撑/红色压力)
  - 分页展示
  - 日期筛选
```

---

## 💾 数据存储

### 1. JSONL数据目录 (最新按日期存储)
```
目录: /home/user/webapp/data/support_resistance_daily/
状态: ✅ 使用中
文件格式: support_resistance_YYYYMMDD.jsonl
文件数量: 27个 (2025-12-25 ~ 2026-01-24)
总大小: 797.62 MB
数据类型: 
  - type: "level" (支撑压力线记录)
  - type: "snapshot" (场景快照)
示例文件:
  - support_resistance_20251225.jsonl
  - support_resistance_20251226.jsonl
  - ...
  - support_resistance_20260124.jsonl (今日)
```

### 2. JSONL数据目录 (旧版单文件)
```
目录: /home/user/webapp/data/support_resistance_jsonl/
状态: ⚠️ 旧版 (保留，向后兼容)
文件:
  - support_resistance_levels.jsonl (697 MB, 仅今日数据)
  - support_resistance_snapshots.jsonl (25 MB, 26天历史)
  - okex_kline_ohlc.jsonl (15 MB)
  - daily_baseline_prices.jsonl (4.2 MB)
总大小: 741.2 MB
说明: 数据已迁移到新目录，此目录保留以便回退
```

---

## ⚙️ PM2配置

### 1. Levels采集器进程
```
PM2名称: support-resistance-collector
启动命令: pm2 start source_code/support_resistance_collector.py --interpreter python3 --name support-resistance-collector
运行状态: ✅ 应该在运行
日志位置: 
  - 输出: ~/.pm2/logs/support-resistance-collector-out.log
  - 错误: ~/.pm2/logs/support-resistance-collector-error.log
  - 应用: source_code/support_resistance.log
```

### 2. Snapshots采集器进程
```
PM2名称: support-resistance-snapshots
启动命令: pm2 start source_code/support_resistance_snapshot_collector.py --interpreter python3 --name support-resistance-snapshots
运行状态: ✅ 应该在运行
日志位置:
  - 输出: ~/.pm2/logs/support-resistance-snapshots-out.log
  - 错误: ~/.pm2/logs/support-resistance-snapshots-error.log
  - 应用: source_code/support_resistance_snapshot.log
```

### 3. Flask应用进程
```
PM2名称: flask-app-new (或类似)
文件: source_code/app_new.py
端口: 5000
状态: ✅ 提供API和页面服务
```

### PM2管理命令
```bash
# 查看所有进程
pm2 list

# 查看支撑压力线相关进程
pm2 list | grep support

# 重启采集器
pm2 restart support-resistance-collector
pm2 restart support-resistance-snapshots

# 查看日志
pm2 logs support-resistance-collector
pm2 logs support-resistance-snapshots

# 停止进程
pm2 stop support-resistance-collector
pm2 stop support-resistance-snapshots

# 删除进程
pm2 delete support-resistance-collector
pm2 delete support-resistance-snapshots
```

---

## 🔌 API路由

### Flask应用 (source_code/app_new.py)

#### 1. 获取最新数据
```
路由: /api/support-resistance/latest
方法: GET
功能: 获取所有币种的最新支撑压力线数据
返回: JSON (27个币种数据 + 4种场景统计)
数据源: SupportResistanceDailyManager.get_latest_levels()
更新时间: 每30秒
示例:
  curl http://localhost:5000/api/support-resistance/latest
```

#### 2. 获取快照数据
```
路由: /api/support-resistance/snapshots
方法: GET
参数:
  - all: true/false (是否返回所有历史)
  - date: YYYY-MM-DD (按日期过滤)
  - limit: 数字 (返回条数)
功能: 获取场景快照历史数据
返回: JSON (快照列表)
数据源: SupportResistanceAPIAdapter.get_snapshots()
示例:
  curl http://localhost:5000/api/support-resistance/snapshots?limit=100
  curl http://localhost:5000/api/support-resistance/snapshots?date=2026-01-24
  curl http://localhost:5000/api/support-resistance/snapshots?all=true
```

#### 3. 获取图表数据
```
路由: /api/support-resistance/chart-data
方法: GET
参数:
  - all: true/false
  - date: YYYY-MM-DD
  - page: 页码
  - items_per_page: 每页条数
功能: 获取预计算的图表数据（后端处理）
返回: JSON (categories, 4种场景series, 信号点)
数据源: SupportResistanceAPIAdapter.get_snapshots()
特性: 后端计算图表数据，前端直接展示
示例:
  curl http://localhost:5000/api/support-resistance/chart-data?page=1
```

#### 4. 获取信号数据
```
路由: /api/support-resistance/signals-computed
方法: GET
功能: 获取抄底/逃顶信号标记点
返回: JSON (buy_signals, sell_signals, 24h统计)
数据源: SupportResistanceAPIAdapter.get_snapshots()
信号规则:
  - 抄底: scenario_1 >= 8 且 scenario_2 >= 8
  - 逃顶: scenario_3 >= 5 且 scenario_4 >= 5
示例:
  curl http://localhost:5000/api/support-resistance/signals-computed
```

#### 5. 获取可用日期列表
```
路由: /api/support-resistance/dates
方法: GET
功能: 获取有数据的所有日期列表
返回: JSON (dates数组)
数据源: SupportResistanceDailyManager.get_available_dates()
格式: YYYY-MM-DD (倒序)
示例:
  curl http://localhost:5000/api/support-resistance/dates
```

#### 6. 获取最新信号
```
路由: /api/support-resistance/latest-signal
方法: GET
功能: 获取最新的抄底或逃顶信号
返回: JSON (最新信号详情)
数据源: 数据库
示例:
  curl http://localhost:5000/api/support-resistance/latest-signal
```

#### 7. 获取逃顶最大值统计
```
路由: /api/support-resistance/escape-max-stats
方法: GET
功能: 获取逃顶快照数的历史最大值统计
返回: JSON (24h最大值, 2h最大值, 当前值)
数据源: 数据库
示例:
  curl http://localhost:5000/api/support-resistance/escape-max-stats
```

#### 8. 数据导出
```
路由: /api/support-resistance/export
方法: POST
功能: 导出支撑压力线数据
返回: JSON (download_url)
```

#### 9. 数据下载
```
路由: /api/support-resistance/download/<filename>
方法: GET
功能: 下载导出的数据文件
```

#### 10. 数据导入
```
路由: /api/support-resistance/import
方法: POST
功能: 导入支撑压力线数据
```

#### 11. Telegram信号推送
```
路由: /api/telegram/signals/support-resistance
方法: GET
功能: 为Telegram推送准备的信号接口
```

### 页面路由

#### 主页面
```
路由: /support-resistance
方法: GET
功能: 支撑压力线系统主页面
模板: source_code/templates/support_resistance.html
```

---

## 🗄️ 数据库

### SQLite数据库
```
文件: /home/user/webapp/databases/support_resistance.db
状态: ✅ 在用 (向后兼容)
大小: 242 MB
说明: 虽然主要使用JSONL，但数据库仍保留用于兼容性
```

### 表结构

#### 1. support_resistance_levels (支撑压力线记录)
```sql
CREATE TABLE support_resistance_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    current_price REAL,
    support_line_1 REAL,
    support_line_2 REAL,
    resistance_line_1 REAL,
    resistance_line_2 REAL,
    distance_to_support_1 REAL,
    distance_to_support_2 REAL,
    distance_to_resistance_1 REAL,
    distance_to_resistance_2 REAL,
    position_s2_r1 REAL,
    position_s1_r2 REAL,
    position_s1_r2_upper REAL,
    position_s1_r1 REAL,
    position_7d REAL,
    position_48h REAL,
    alert_scenario_1 INTEGER,
    alert_scenario_2 INTEGER,
    alert_scenario_3 INTEGER,
    alert_scenario_4 INTEGER,
    alert_7d_low INTEGER,
    alert_7d_high INTEGER,
    alert_48h_low INTEGER,
    alert_48h_high INTEGER,
    alert_triggered INTEGER DEFAULT 0,
    baseline_price_24h REAL,
    price_change_24h REAL,
    change_percent_24h REAL,
    record_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_time_beijing TEXT
);

-- 索引
CREATE INDEX idx_symbol ON support_resistance_levels(symbol);
CREATE INDEX idx_record_time ON support_resistance_levels(record_time);
CREATE INDEX idx_alerts ON support_resistance_levels(alert_scenario_1, alert_scenario_2, alert_scenario_3, alert_scenario_4);
```

#### 2. support_resistance_snapshots (场景快照)
```sql
CREATE TABLE support_resistance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TIMESTAMP,
    snapshot_date TEXT,
    scenario_1_count INTEGER DEFAULT 0,
    scenario_2_count INTEGER DEFAULT 0,
    scenario_3_count INTEGER DEFAULT 0,
    scenario_4_count INTEGER DEFAULT 0,
    scenario_1_coins TEXT,
    scenario_2_coins TEXT,
    scenario_3_coins TEXT,
    scenario_4_coins TEXT,
    total_coins INTEGER DEFAULT 27,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_snapshot_time ON support_resistance_snapshots(snapshot_time);
CREATE INDEX idx_snapshot_date ON support_resistance_snapshots(snapshot_date);
```

#### 3. daily_baseline_prices (每日基准价格)
```sql
CREATE TABLE daily_baseline_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    baseline_price REAL NOT NULL,
    baseline_date TEXT NOT NULL,
    baseline_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE UNIQUE INDEX idx_symbol_date ON daily_baseline_prices(symbol, baseline_date);
```

---

## 📚 文档文件

### 系统文档
```
1. SUPPORT_RESISTANCE_REFACTOR_COMPLETE.md (459行)
   - 完整重构报告
   - 架构说明
   - 性能对比
   - 使用示例

2. SUPPORT_RESISTANCE_MIGRATION_REPORT.md
   - 数据迁移详细报告
   - 迁移统计
   - 验证结果

3. SUPPORT_RESISTANCE_DATA_REPORT.md
   - 数据统计分析
   - 时间范围
   - 文件分布

4. SUPPORT_RESISTANCE_ARCHITECTURE_ANALYSIS.md
   - 架构分析
   - 设计决策

5. SUPPORT_RESISTANCE_FIX_SUMMARY.md
   - 历史修复记录
   - 问题总结

6. SUPPORT_RESISTANCE_DATABASE_FIX_REPORT.md
   - 数据库修复报告

7. SUPPORT_RESISTANCE_FIX_REPORT.md
   - 系统修复报告
```

### 迁移脚本
```
1. migrate_support_resistance_to_daily.py
   - 数据迁移脚本
   - 状态: 已执行完成

2. migrate_support_resistance_to_jsonl.py
   - 旧的JSONL迁移脚本

3. update_support_resistance_jsonl.py
   - JSONL更新工具
```

---

## 🔄 数据流图

```
OKX API
   ↓
[support_resistance_collector.py] (每30秒)
   ↓
[support_resistance_daily_manager.py]
   ↓
data/support_resistance_daily/support_resistance_YYYYMMDD.jsonl
   ↓
[support_resistance_snapshot_collector.py] (每60秒)
   ↓
[support_resistance_daily_manager.py]
   ↓
data/support_resistance_daily/support_resistance_YYYYMMDD.jsonl
   ↓
[support_resistance_api_adapter.py]
   ↓
[Flask API Routes] (app_new.py)
   ↓
[前端页面] (support_resistance.html)
   ↓
用户浏览器
```

---

## ⚡ 快速诊断命令

### 检查PM2进程
```bash
pm2 list | grep support
pm2 describe support-resistance-collector
pm2 describe support-resistance-snapshots
```

### 检查日志
```bash
tail -f source_code/support_resistance.log
tail -f source_code/support_resistance_snapshot.log
pm2 logs support-resistance-collector --lines 50
pm2 logs support-resistance-snapshots --lines 50
```

### 检查数据文件
```bash
ls -lh data/support_resistance_daily/
ls -lh data/support_resistance_jsonl/
du -sh data/support_resistance_daily/
du -sh data/support_resistance_jsonl/
```

### 检查最新数据
```bash
# 查看今日数据
tail -5 data/support_resistance_daily/support_resistance_$(date +%Y%m%d).jsonl | python3 -m json.tool

# 测试API
curl http://localhost:5000/api/support-resistance/latest | python3 -m json.tool
curl http://localhost:5000/api/support-resistance/dates | python3 -m json.tool
```

### 检查数据库
```bash
sqlite3 databases/support_resistance.db "SELECT COUNT(*) FROM support_resistance_levels;"
sqlite3 databases/support_resistance.db "SELECT COUNT(*) FROM support_resistance_snapshots;"
sqlite3 databases/support_resistance.db "SELECT MAX(record_time) FROM support_resistance_levels;"
```

---

## 🎯 系统健康检查清单

- [ ] PM2进程运行正常 (support-resistance-collector, support-resistance-snapshots)
- [ ] 今日JSONL文件存在且有数据
- [ ] API响应正常 (/api/support-resistance/latest)
- [ ] 前端页面可访问 (/support-resistance)
- [ ] 数据库有最新记录
- [ ] 日志无严重错误
- [ ] 磁盘空间充足 (>10%)

---

**生成时间**: 2026-01-24 20:20 (北京时间)  
**系统版本**: 按日期存储版本  
**维护人**: GenSpark AI Developer
