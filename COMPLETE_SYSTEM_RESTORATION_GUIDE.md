# 加密货币分析系统完整恢复部署指南

**版本**: v1.0  
**创建日期**: 2026-01-10  
**备份时间**: 2026-01-10 14:24  
**系统规模**: 23个子系统，11个数据库，100+页面

---

## 目录

1. [系统概览](#系统概览)
2. [23个子系统清单](#23个子系统清单)
3. [数据库架构](#数据库架构)
4. [完整恢复步骤](#完整恢复步骤)
5. [重点系统详细说明](#重点系统详细说明)
6. [验证清单](#验证清单)

---

## 系统概览

### 技术栈
- **后端**: Python 3.x + Flask
- **进程管理**: PM2
- **数据库**: SQLite (11个数据库文件)
- **前端**: HTML/CSS/JavaScript + ECharts
- **部署**: 单机部署，5个PM2进程

### 目录结构
```
/home/user/webapp/
├── databases/              # 11个SQLite数据库
├── source_code/           # 所有Python源代码
│   ├── app_new.py        # 主Flask应用
│   ├── templates/        # 所有HTML页面模板
│   └── *.py              # 各系统采集器和处理器
├── configs/              # JSON配置文件
├── logs/                 # 系统日志
└── *.py                  # 根目录脚本
```

---

## 23个子系统清单

### 核心系统（⭐ 重点）

#### 1. ⭐ SAR斜率系统
- **功能**: SAR指标斜率分析和趋势预测
- **数据库**: `sar_slope_data.db`
- **关键表**:
  - `sar_raw_data` (77,864条): 原始SAR数据
  - `sar_conversion_points` (4,388,195条): 转折点记录
  - `sar_consecutive_changes` (77,810条): 连续变化
  - `sar_period_averages` (10,171条): 周期平均值
  - `sar_anomaly_alerts` (4,718条): 异常告警
  - `sar_bias_trend` (1,799条): 偏移趋势
- **页面**: `/sar-analysis`
- **采集器**: 无（通过API实时计算）
- **API接口**: 
  - `/api/sar/data` - 获取SAR数据
  - `/api/sar/analysis` - 获取分析结果

#### 2. ⭐ 历史数据查询系统
- **功能**: 加密货币历史数据查询和展示
- **数据库**: `crypto_data.db`
- **关键表**:
  - `crypto_snapshots` (15,796条): 快照数据
  - `crypto_summary` (1条): 汇总数据
  - `crypto_coin_detail` (29条): 币种详情
- **页面**: `/query`
- **采集器**: `gdrive_final_detector.py` (自动导入Google Drive TXT文件)
- **API接口**:
  - `/api/query?time=YYYY-MM-DD HH:MM` - 查询指定时间数据

#### 3. 恐慌清洗指数系统
- **功能**: 市场恐慌情绪和清洗程度分析
- **数据库**: `crypto_data.db`
- **关键表**:
  - `escape_signal_stats` (9,616条): 逃顶信号统计
  - `escape_snapshot_stats` (6,417条): 快照统计
- **页面**: `/escape-signal-history`
- **采集器**: `escape-stats-filler` (PM2进程)
- **API接口**:
  - `/api/escape-signal-stats` - 获取统计数据

#### 4. 比价系统
- **功能**: 币种间价格比较和相对强弱分析
- **数据库**: `crypto_data.db` (复用)
- **关键表**: `crypto_snapshots`
- **页面**: 集成在 `/query` 页面
- **采集器**: 与历史查询系统共用

#### 5. 星星系统
- **功能**: 基于计次得分的星级评估系统
- **数据库**: `crypto_data.db` (复用)
- **关键字段**: `count`, `count_score` 在 `crypto_summary` 表
- **页面**: 集成在 `/query` 页面
- **计算规则**:
  - 截止6点前: ≤2得2颗实心星, ≤3得1颗实心星
  - 截止12点前: ≤3得3颗实心星, ≤4得2颗实心星
  - 截止18点前: ≤3得3颗实心星, ≤5得2颗实心星
  - 截止24点前: ≤4得3颗实心星, ≤6得2颗实心星

#### 6. 币种池系统
- **功能**: 动态管理交易币种池
- **数据库**: `trading_decision.db`
- **关键表**: `market_config` (21条)
- **页面**: 无独立页面（后台管理）
- **配置文件**: `market_config.json`

#### 7. 实时市场原始数据
- **功能**: OKEx交易所实时数据采集
- **数据库**: `support_resistance.db`, `crypto_data.db`
- **关键表**: 
  - `okex_kline_ohlc` (50,000条K线数据)
  - `okex_technical_indicators`
- **采集器**: `support-resistance-collector` (PM2进程)
- **更新频率**: 实时（WebSocket）

#### 8. 数据采集监控
- **功能**: 监控所有数据采集器状态
- **数据库**: 无专用数据库
- **监控方式**: PM2进程监控 + 日志监控
- **页面**: 集成在各系统页面底部
- **关键进程**:
  - `support-resistance-collector`
  - `support-resistance-snapshot`
  - `gdrive-detector`
  - `escape-stats-filler`

#### 9. 深度图得分系统
- **功能**: 市场深度分析和评分
- **数据库**: `crypto_data.db` (集成)
- **状态**: 待开发

#### 10. 深度图可视化
- **功能**: 市场深度数据可视化展示
- **数据库**: `crypto_data.db` (集成)
- **状态**: 待开发

#### 11. 平均分页面
- **功能**: SAR周期平均值展示
- **数据库**: `sar_slope_data.db`
- **关键表**: `sar_period_averages`
- **页面**: 集成在 `/sar-analysis`

#### 12. OKEx加密指数
- **功能**: OKEx交易所指数数据
- **数据库**: `crypto_data.db`
- **关键表**: `okex_technical_indicators`
- **状态**: 数据结构已建立，待填充

#### 13. 位置系统
- **功能**: 价格相对位置分析
- **数据库**: `crypto_data.db`
- **关键表**: `position_system`
- **状态**: 表已创建，待实现

#### 14. ⭐ 支撑压力线系统
- **功能**: 动态支撑压力位计算和信号检测
- **数据库**: `support_resistance.db`
- **关键表**:
  - `support_resistance_levels` (484,417条): 支撑压力位
  - `support_resistance_snapshots` (19,098条): 快照记录
  - `daily_baseline_prices` (621条): 每日基准价
- **页面**: `/support-resistance`
- **采集器**: 
  - `support-resistance-collector` (实时采集)
  - `support-resistance-snapshot` (每分钟快照)
- **API接口**:
  - `/api/support-resistance/latest` - 最新数据
  - `/api/support-resistance/snapshots` - 历史快照
  - `/api/support-resistance/latest-signal` - 最新信号
- **信号规则**:
  - 抄底信号: 情况1≥8 AND 情况2≥8
  - 逃顶信号: (情况3+情况4)≥8

#### 15. 决策交易信号系统
- **功能**: 自动交易信号生成和决策
- **数据库**: `trading_decision.db`
- **关键表**: `trading_decisions` (3,949条)
- **页面**: `/trading-signals`
- **API接口**: `/api/trading-signals`

#### 16. 决策K线指标系统
- **功能**: K线技术指标分析
- **数据库**: `crypto_data.db`, `support_resistance.db`
- **关键表**: `okex_technical_indicators`, `okex_kline_ohlc`
- **页面**: 集成在各分析页面

#### 17. V1V2成交系统
- **功能**: 双向成交量分析
- **数据库**: `v1v2_data.db`
- **关键表**: 每个币种一个表（如 `volume_btc`, `volume_eth` 等）
- **数据量**: 27个币种，每个约1,458条记录
- **页面**: `/v1v2-analysis`
- **更新频率**: 实时更新

#### 18. 1分钟涨跌幅系统
- **功能**: 短周期价格变动监控
- **数据库**: `price_speed_data.db`
- **关键表**: 
  - `price_speed_1min`
  - `price_speed_5min`
- **状态**: 表已创建，待数据填充

#### 19. ⭐ Google Drive监控系统
- **功能**: 自动监控Google Drive并导入TXT数据
- **数据库**: 无专用数据库
- **配置文件**: `daily_folder_config.json`
- **采集器**: `gdrive-detector` (PM2进程)
- **监控目标**: Google Drive文件夹 (folder_id: 1sCHpLo3BdxjXmeW9mo30Gijpzkux0eNm)
- **导入目标**: `crypto_data.db` 的 `crypto_snapshots` 表
- **日志**: `gdrive_final_detector.log`

#### 20. TG消息推送系统
- **功能**: Telegram消息推送和告警
- **配置文件**: `telegram_config.json`
- **API接口**: 
  - `/api/telegram/signals/support-resistance` - 推送支撑压力信号
  - `/api/telegram/signals/trading` - 推送交易信号
- **状态**: 已集成到各系统

#### 21. ⭐ 资金监控系统
- **功能**: 多时间维度资金流向监控
- **数据库**: `fund_monitor.db`
- **关键表**:
  - `fund_monitor_5min` (38,565条): 5分钟数据
  - `fund_monitor_aggregated` (115,695条): 聚合数据
  - `fund_monitor_abnormal_history` (99,153条): 异常记录
  - `fund_monitor_config` (1条): 配置
- **页面**: `/fund-monitor`
- **监控维度**: 5分钟、1小时、4小时、12小时、24小时

#### 22. ⭐ 锚点系统
- **功能**: 价格锚点监控和回调分析
- **数据库**: `anchor_system.db`, `trading_decision.db`
- **关键表**:
  - `anchor_monitors` (43,011条): 监控记录
  - `anchor_alerts` (5,422条): 告警记录
  - `anchor_profit_records` (35条): 收益记录
  - `anchor_real_profit_records` (39条): 真实收益
  - `anchor_positions` (交易系统中): 仓位管理
  - `anchor_triggers` (268条): 触发记录
- **页面**: `/anchor-monitor`
- **API接口**:
  - `/api/anchor/stats` - 统计数据
  - `/api/anchor/alerts` - 告警列表
  - `/api/anchor/profit` - 收益记录
- **回调等级**:
  - 1级: ≥2%
  - 2级: ≥3%
  - 3级: ≥4%
  - 4级: ≥5%
  - 5级: ≥6%

#### 23. ⭐ 自动交易系统
- **功能**: 全自动交易执行和仓位管理
- **数据库**: `trading_decision.db`
- **关键表**:
  - `trading_decisions` (3,949条): 交易决策
  - `position_opens` (14条): 开仓记录
  - `position_adds` (16条): 加仓记录
  - `position_closes` (16条): 平仓记录
  - `pending_orders` (24条): 挂单
  - `anchor_positions` (1条): 当前持仓
  - `long_position_monitoring` (20,127条): 多头监控
  - `anchor_maintenance` 系列: 维护记录
- **页面**: `/auto-trading`
- **策略**: 基于锚点系统+支撑压力线的综合策略
- **风控**: 
  - 最大持仓限制
  - 止盈止损自动触发
  - 极端修正记录

---

## 数据库架构

### 数据库文件清单

| 数据库文件 | 大小 | 表数量 | 总记录数 | 主要用途 |
|-----------|------|-------|---------|---------|
| `sar_slope_data.db` | 505MB | 8 | 4,560,557 | SAR斜率系统 |
| `support_resistance.db` | 184MB | 5 | 554,136 | 支撑压力线系统 |
| `fund_monitor.db` | 42MB | 5 | 253,414 | 资金监控系统 |
| `anchor_system.db` | 13MB | 13 | 48,621 | 锚点系统 |
| `v1v2_data.db` | 12MB | 28 | 39,402 | V1V2成交系统 |
| `crypto_data.db` | 4.8MB | 16 | 31,883 | 历史数据、逃顶信号 |
| `trading_decision.db` | 4.3MB | 29 | 24,842 | 自动交易系统 |
| `count_monitor.db` | 16KB | 3 | 11 | 计数监控 |
| `pair_protection.db` | 20KB | 3 | 20 | 对冲保护 |
| `signal_data.db` | 16KB | 3 | 0 | 信号数据（待用） |
| `price_speed_data.db` | 24KB | 3 | 0 | 涨跌幅（待用） |

### 数据库关系图

```
crypto_data.db (历史查询核心)
    ├─→ crypto_snapshots (快照数据)
    ├─→ crypto_summary (汇总数据)
    ├─→ crypto_coin_detail (币种详情)
    ├─→ escape_signal_stats (逃顶统计)
    └─→ escape_snapshot_stats (快照统计)

support_resistance.db (支撑压力核心)
    ├─→ support_resistance_levels (支撑压力位)
    ├─→ support_resistance_snapshots (快照)
    ├─→ daily_baseline_prices (基准价)
    └─→ okex_kline_ohlc (K线数据)

sar_slope_data.db (SAR分析核心)
    ├─→ sar_raw_data (原始数据)
    ├─→ sar_conversion_points (转折点)
    ├─→ sar_consecutive_changes (连续变化)
    ├─→ sar_period_averages (周期平均)
    ├─→ sar_anomaly_alerts (异常告警)
    └─→ sar_bias_trend (偏移趋势)

anchor_system.db (锚点核心)
    ├─→ anchor_monitors (监控记录)
    ├─→ anchor_alerts (告警)
    ├─→ anchor_profit_records (收益)
    └─→ extreme_corrections_log (极端修正)

trading_decision.db (交易核心)
    ├─→ trading_decisions (决策)
    ├─→ position_opens/adds/closes (仓位)
    ├─→ anchor_positions (锚点仓位)
    ├─→ pending_orders (挂单)
    └─→ anchor_triggers (触发器)

fund_monitor.db (资金监控)
    ├─→ fund_monitor_5min (5分钟数据)
    ├─→ fund_monitor_aggregated (聚合)
    └─→ fund_monitor_abnormal_history (异常)

v1v2_data.db (成交分析)
    └─→ volume_{coin} (每个币种一表)
```

---

## 完整恢复步骤

### 前置要求

1. **操作系统**: Linux (Ubuntu/Debian推荐)
2. **Python**: 3.8+ (推荐3.10+)
3. **Node.js**: 14+ (用于PM2)
4. **磁盘空间**: 至少5GB可用空间
5. **网络**: 可访问互联网（用于安装依赖）

### 步骤 1: 环境准备

```bash
# 1.1 更新系统
sudo apt update && sudo apt upgrade -y

# 1.2 安装Python3和pip
sudo apt install python3 python3-pip python3-venv -y

# 1.3 安装Node.js和PM2
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y
sudo npm install -g pm2

# 1.4 创建工作目录
mkdir -p /home/user/webapp
cd /home/user/webapp

# 1.5 验证安装
python3 --version  # 应该显示 Python 3.x
node --version     # 应该显示 v20.x
pm2 --version      # 应该显示 PM2 版本
```

### 步骤 2: 恢复文件

```bash
# 2.1 解压备份文件（假设备份文件在 /tmp/backup.tar.gz）
cd /home/user
tar -xzf /path/to/backup.tar.gz -C webapp/

# 2.2 验证目录结构
ls -la webapp/
# 应该看到: databases/, source_code/, configs/, logs/, *.py 等

# 2.3 设置权限
chmod +x webapp/*.sh
chmod +x webapp/source_code/*.sh
chmod 755 webapp/databases/
```

### 步骤 3: 恢复数据库

```bash
# 3.1 确认数据库文件完整性
cd /home/user/webapp/databases
ls -lh *.db

# 应该看到11个数据库文件:
# - crypto_data.db
# - sar_slope_data.db
# - support_resistance.db
# - anchor_system.db
# - trading_decision.db
# - fund_monitor.db
# - v1v2_data.db
# - signal_data.db
# - count_monitor.db
# - pair_protection.db
# - price_speed_data.db

# 3.2 验证数据库（可选）
sqlite3 crypto_data.db "SELECT COUNT(*) FROM crypto_snapshots;"
# 应该返回一个数字（如15796）

# 3.3 备份原数据库（如果有）
cp crypto_data.db crypto_data.db.backup
```

### 步骤 4: 安装Python依赖

```bash
# 4.1 创建虚拟环境（推荐）
cd /home/user/webapp
python3 -m venv venv
source venv/bin/activate

# 4.2 安装依赖
pip install -r dependencies/requirements.txt

# 主要依赖包括:
# - Flask==2.3.0
# - flask-cors==4.0.0
# - requests==2.31.0
# - numpy==1.24.0
# - pandas==2.0.0
# - pytz==2023.3
# - python-telegram-bot==20.0
# - websockets==11.0

# 4.3 验证安装
pip list | grep -i flask
pip list | grep -i requests
```

### 步骤 5: 配置文件恢复

```bash
# 5.1 恢复配置文件
cd /home/user/webapp/configs
cp *.json ../
cp *.yaml ../ 2>/dev/null || true

# 5.2 检查关键配置
cat daily_folder_config.json  # Google Drive配置
cat market_config.json         # 市场配置
cat telegram_config.json       # Telegram配置（需要填入真实token）

# 5.3 修改配置（如需要）
# 编辑 daily_folder_config.json 设置 Google Drive folder_id
# 编辑 telegram_config.json 设置 Telegram bot token
```

### 步骤 6: 恢复Git仓库（可选）

```bash
# 6.1 解压Git仓库
cd /home/user/webapp
tar -xzf git/git_repository.tar.gz

# 6.2 验证Git状态
git status
git log --oneline -10

# 6.3 设置远程仓库（如果有）
git remote -v
# 如果需要，添加远程仓库:
# git remote add origin https://your-repo-url.git
```

### 步骤 7: 启动PM2进程

```bash
# 7.1 进入工作目录
cd /home/user/webapp

# 7.2 启动Flask应用
pm2 start source_code/app_new.py --name flask-app --interpreter python3

# 7.3 启动支撑压力线采集器
pm2 start source_code/support_resistance_collector.py \
    --name support-resistance-collector --interpreter python3

# 7.4 启动支撑压力线快照采集器
pm2 start source_code/support_resistance_snapshot_collector.py \
    --name support-resistance-snapshot --interpreter python3

# 7.5 启动Google Drive监控
pm2 start gdrive_final_detector.py \
    --name gdrive-detector --interpreter python3

# 7.6 启动逃顶信号统计补全
pm2 start source_code/auto_fill_escape_stats.sh \
    --name escape-stats-filler

# 7.7 保存PM2配置
pm2 save
pm2 startup  # 设置开机自启（按提示执行命令）

# 7.8 查看进程状态
pm2 status
pm2 logs --lines 20
```

### 步骤 8: 验证系统

```bash
# 8.1 检查Flask应用
curl http://localhost:5000/
# 应该返回HTML内容

# 8.2 检查API接口
curl http://localhost:5000/api/query?time=2026-01-08%2013:00
# 应该返回JSON数据

# 8.3 检查数据库连接
python3 << EOF
import sqlite3
conn = sqlite3.connect('databases/crypto_data.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM crypto_snapshots")
print(f"crypto_snapshots: {cursor.fetchone()[0]} records")
conn.close()
print("✅ Database connection OK")
EOF

# 8.4 检查PM2进程
pm2 list
# 应该看到5个进程都是 'online' 状态

# 8.5 查看日志
tail -f logs/*.log
pm2 logs --lines 50
```

### 步骤 9: 配置防火墙（如需要）

```bash
# 9.1 允许Flask端口（默认5000）
sudo ufw allow 5000/tcp

# 9.2 启用防火墙
sudo ufw enable

# 9.3 查看状态
sudo ufw status
```

### 步骤 10: 设置系统服务（可选）

```bash
# 10.1 创建systemd服务文件
sudo cat > /etc/systemd/system/crypto-system.service << 'EOF'
[Unit]
Description=Crypto Analysis System
After=network.target

[Service]
Type=forking
User=user
WorkingDirectory=/home/user/webapp
ExecStart=/usr/bin/pm2 resurrect
ExecReload=/usr/bin/pm2 reload all
ExecStop=/usr/bin/pm2 kill
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# 10.2 启用服务
sudo systemctl enable crypto-system
sudo systemctl start crypto-system
sudo systemctl status crypto-system
```

---

## 重点系统详细说明

### 1. ⭐ SAR斜率系统

#### 系统架构
```
数据流:
OKEx API → sar_raw_data → 
    ├→ sar_conversion_points (转折点检测)
    ├→ sar_consecutive_changes (连续变化)
    ├→ sar_period_averages (周期统计)
    ├→ sar_anomaly_alerts (异常告警)
    └→ sar_bias_trend (偏移趋势)
```

#### 数据库表详情

**`sar_raw_data`** (77,864条)
```sql
CREATE TABLE sar_raw_data (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    sar_value REAL,
    price REAL,
    sar_direction TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`sar_conversion_points`** (4,388,195条) - 最大表
```sql
CREATE TABLE sar_conversion_points (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    conversion_type TEXT,  -- 'up_to_down', 'down_to_up'
    sar_value REAL,
    price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`sar_consecutive_changes`** (77,810条)
```sql
CREATE TABLE sar_consecutive_changes (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    start_timestamp TEXT,
    end_timestamp TEXT,
    direction TEXT,  -- 'up', 'down'
    change_count INTEGER,
    total_change REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 恢复后验证
```bash
# 1. 检查数据完整性
cd /home/user/webapp
python3 << EOF
import sqlite3
conn = sqlite3.connect('databases/sar_slope_data.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"✅ Found {len(tables)} tables: {tables}")

for table in tables:
    if table != 'sqlite_sequence':
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count:,} records")
conn.close()
EOF

# 2. 访问页面
curl http://localhost:5000/sar-analysis

# 3. 测试API
curl http://localhost:5000/api/sar/data?symbol=BTCUSDT&limit=10
```

#### 关键文件
- 数据库: `databases/sar_slope_data.db`
- 页面: `source_code/templates/sar_analysis.html`
- API: `source_code/app_new.py` (搜索 `/sar-analysis`, `/api/sar/`)

---

### 2. ⭐ 历史数据查询系统

#### 系统架构
```
数据流:
Google Drive TXT文件 → gdrive-detector → 解析 → crypto_snapshots
    ├→ crypto_summary (汇总)
    └→ crypto_coin_detail (明细)
```

#### 数据库表详情

**`crypto_snapshots`** (15,796条)
```sql
CREATE TABLE crypto_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TEXT NOT NULL,
    coin_symbol TEXT NOT NULL,
    last_price REAL,
    change_24h REAL,
    rush_up INTEGER DEFAULT 0,
    rush_down INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(snapshot_time, coin_symbol)
);
```

**`crypto_summary`** (1条 - 最新汇总)
```sql
CREATE TABLE crypto_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TEXT NOT NULL UNIQUE,
    rush_up_total INTEGER DEFAULT 0,
    rush_down_total INTEGER DEFAULT 0,
    count INTEGER DEFAULT 0,
    count_score TEXT,
    status TEXT,
    ratio REAL,
    diff INTEGER,
    position_lowest INTEGER DEFAULT 0,
    position_newhigh INTEGER DEFAULT 0,
    rise_24h_count INTEGER DEFAULT 0,
    fall_24h_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`crypto_coin_detail`** (29条 - 币种详情)
```sql
CREATE TABLE crypto_coin_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TEXT NOT NULL,
    priority_level TEXT,
    coin_symbol TEXT NOT NULL,
    rush_up INTEGER DEFAULT 0,
    rush_down INTEGER DEFAULT 0,
    current_price REAL,
    change_24h REAL,
    historical_high REAL,
    max_ratio REAL,
    min_ratio REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(snapshot_time, coin_symbol)
);
```

#### Google Drive 配置

**`daily_folder_config.json`**
```json
{
  "folder_id": "1sCHpLo3BdxjXmeW9mo30Gijpzkux0eNm",
  "file_pattern": "YYYY-MM-DD_HHMM.txt",
  "import_interval": 60,
  "last_imported_file": "2026-01-08_1350.txt"
}
```

#### 恢复后验证
```bash
# 1. 检查数据
cd /home/user/webapp
python3 << EOF
import sqlite3
conn = sqlite3.connect('databases/crypto_data.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM crypto_snapshots")
print(f"crypto_snapshots: {cursor.fetchone()[0]:,} records")

cursor.execute("SELECT * FROM crypto_summary ORDER BY id DESC LIMIT 1")
row = cursor.fetchone()
print(f"Latest summary: {row}")

cursor.execute("SELECT COUNT(*) FROM crypto_coin_detail")
print(f"crypto_coin_detail: {cursor.fetchone()[0]} coins")

conn.close()
EOF

# 2. 测试查询API
curl "http://localhost:5000/api/query?time=2026-01-08%2013:00"

# 3. 检查Google Drive监控
pm2 logs gdrive-detector --lines 20

# 4. 访问页面
curl http://localhost:5000/query
```

#### 关键文件
- 数据库: `databases/crypto_data.db`
- 页面: `source_code/templates/query.html`
- 采集器: `gdrive_final_detector.py`
- 配置: `daily_folder_config.json`
- API: `source_code/app_new.py` (搜索 `/query`, `/api/query`)

---

### 3. ⭐ 恐慌清洗指数系统

#### 系统架构
```
数据流:
support_resistance_snapshots → escape-stats-filler →
    ├→ escape_signal_stats (按时间点统计)
    └→ escape_snapshot_stats (快照统计)
```

#### 数据库表详情

**`escape_signal_stats`** (9,616条)
```sql
CREATE TABLE escape_signal_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_time TEXT NOT NULL UNIQUE,
    signal_24h_count INTEGER DEFAULT 0,
    signal_2h_count INTEGER DEFAULT 0,
    max_signal_24h INTEGER DEFAULT 0,
    max_signal_2h INTEGER DEFAULT 0,
    decline_strength_level INTEGER DEFAULT 0,
    rise_strength_level INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`escape_snapshot_stats`** (6,417条)
```sql
CREATE TABLE escape_snapshot_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_time TEXT NOT NULL,
    escape_24h_count INTEGER,
    escape_2h_count INTEGER,
    max_escape_24h INTEGER,
    max_escape_2h INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 计算逻辑

**逃顶信号定义**:
```python
# 从 support_resistance_snapshots 计算
escape_signal = (scenario_3_count + scenario_4_count) >= 8

# 24h信号数: 过去24小时内触发逃顶信号的快照数
# 2h信号数: 过去2小时内触发逃顶信号的快照数
```

#### 恢复后验证
```bash
# 1. 检查数据
cd /home/user/webapp
python3 << EOF
import sqlite3
from datetime import datetime
import pytz

conn = sqlite3.connect('databases/crypto_data.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM escape_signal_stats")
print(f"escape_signal_stats: {cursor.fetchone()[0]:,} records")

cursor.execute("SELECT stat_time, signal_24h_count, signal_2h_count FROM escape_signal_stats ORDER BY stat_time DESC LIMIT 5")
print("\\nLatest 5 records:")
for row in cursor.fetchall():
    print(f"  {row[0]}: 24h={row[1]}, 2h={row[2]}")

conn.close()
EOF

# 2. 测试API
curl http://localhost:5000/api/escape-signal-stats | python3 -m json.tool

# 3. 检查自动补全进程
pm2 logs escape-stats-filler --lines 20

# 4. 手动触发补全（测试）
cd /home/user/webapp
python3 fill_escape_signal_stats.py

# 5. 访问页面
curl http://localhost:5000/escape-signal-history
```

#### 关键文件
- 数据库: `databases/crypto_data.db`
- 页面: `source_code/templates/escape_signal_history.html`
- 补全脚本: `fill_escape_signal_stats.py`
- 自动任务: `source_code/auto_fill_escape_stats.sh`
- API: `source_code/app_new.py` (搜索 `/escape-signal-history`, `/api/escape-signal-stats`)

---

### 4. ⭐ 支撑压力线系统

#### 系统架构
```
数据流:
OKEx WebSocket → support-resistance-collector →
    ├→ support_resistance_levels (实时计算)
    ├→ daily_baseline_prices (每日基准)
    └→ okex_kline_ohlc (K线数据)

快照采集:
support-resistance-snapshot (每分钟) →
    support_resistance_snapshots
```

#### 数据库表详情

**`support_resistance_levels`** (484,417条) - 主表
```sql
CREATE TABLE support_resistance_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    record_time TEXT NOT NULL,
    current_price REAL,
    support_line_1 REAL,
    support_line_2 REAL,
    resistance_line_1 REAL,
    resistance_line_2 REAL,
    position_s2_r1 REAL,      -- 支撑2→压力1位置
    position_s1_r2 REAL,      -- 支撑1→压力2位置
    position_s1_r2_upper REAL, -- 支撑1→压力2上部位置
    position_s1_r1 REAL,      -- 支撑1→压力1位置
    alert_scenario_1 INTEGER, -- 情况1: 支撑2→压力1 (<=5%)
    alert_scenario_2 INTEGER, -- 情况2: 支撑1→压力2 (<=5%)
    alert_scenario_3 INTEGER, -- 情况3: 支撑1→压力2 (>=95%)
    alert_scenario_4 INTEGER, -- 情况4: 支撑1→压力1 (>=95%)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, record_time)
);
```

**`support_resistance_snapshots`** (19,098条)
```sql
CREATE TABLE support_resistance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    scenario_1_count INTEGER DEFAULT 0,
    scenario_2_count INTEGER DEFAULT 0,
    scenario_3_count INTEGER DEFAULT 0,
    scenario_4_count INTEGER DEFAULT 0,
    scenario_1_coins TEXT,  -- JSON格式
    scenario_2_coins TEXT,  -- JSON格式
    scenario_3_coins TEXT,  -- JSON格式
    scenario_4_coins TEXT,  -- JSON格式
    total_coins INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL
);
```

**`daily_baseline_prices`** (621条)
```sql
CREATE TABLE daily_baseline_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    baseline_price REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);
```

#### 信号规则

**抄底信号**: `scenario_1 >= 8 AND scenario_2 >= 8`
- 情况1: 价格接近支撑2 (position_s2_r1 <= 5%)
- 情况2: 价格接近支撑1 (position_s1_r2 <= 5%)

**逃顶信号**: `(scenario_3 + scenario_4) >= 8`
- 情况3: 价格接近压力2 (position_s1_r2 >= 95%)
- 情况4: 价格接近压力1 (position_s1_r1 >= 95%)

#### 恢复后验证
```bash
# 1. 检查数据
cd /home/user/webapp
python3 << EOF
import sqlite3
conn = sqlite3.connect('databases/support_resistance.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM support_resistance_levels")
print(f"support_resistance_levels: {cursor.fetchone()[0]:,} records")

cursor.execute("SELECT COUNT(*) FROM support_resistance_snapshots")
print(f"support_resistance_snapshots: {cursor.fetchone()[0]:,} records")

cursor.execute("SELECT COUNT(*) FROM daily_baseline_prices")
print(f"daily_baseline_prices: {cursor.fetchone()[0]:,} records")

# 最新快照
cursor.execute("""
    SELECT snapshot_time, scenario_1_count, scenario_2_count, 
           scenario_3_count, scenario_4_count
    FROM support_resistance_snapshots
    ORDER BY snapshot_time DESC LIMIT 1
""")
row = cursor.fetchone()
print(f"\\nLatest snapshot: {row}")

conn.close()
EOF

# 2. 检查采集器
pm2 logs support-resistance-collector --lines 20
pm2 logs support-resistance-snapshot --lines 20

# 3. 测试API
curl http://localhost:5000/api/support-resistance/latest | python3 -m json.tool
curl http://localhost:5000/api/support-resistance/latest-signal | python3 -m json.tool

# 4. 访问页面
curl http://localhost:5000/support-resistance
```

#### 关键文件
- 数据库: `databases/support_resistance.db`
- 页面: `source_code/templates/support_resistance.html`
- 实时采集器: `source_code/support_resistance_collector.py`
- 快照采集器: `source_code/support_resistance_snapshot_collector.py`
- API: `source_code/app_new.py` (搜索 `/support-resistance`, `/api/support-resistance/`)

---

### 5. ⭐ 锚点系统

#### 系统架构
```
数据流:
价格监控 → anchor_monitors →
    ├→ anchor_alerts (告警触发)
    ├→ anchor_profit_records (收益记录)
    └→ extreme_corrections_log (极端修正)

交易系统集成:
anchor_positions (trading_decision.db) →
    ├→ anchor_triggers
    └→ anchor_maintenance系列
```

#### 数据库表详情

**`anchor_monitors`** (43,011条) - anchor_system.db
```sql
CREATE TABLE anchor_monitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    anchor_price REAL NOT NULL,
    current_price REAL NOT NULL,
    correction_percent REAL NOT NULL,
    correction_level INTEGER NOT NULL,  -- 1-5级
    monitor_time TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`anchor_alerts`** (5,422条) - anchor_system.db
```sql
CREATE TABLE anchor_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    anchor_price REAL NOT NULL,
    alert_price REAL NOT NULL,
    correction_percent REAL NOT NULL,
    correction_level INTEGER NOT NULL,
    alert_time TEXT NOT NULL,
    alert_type TEXT,  -- 'new', 'upgrade', 'downgrade'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`anchor_profit_records`** (35条) - anchor_system.db
```sql
CREATE TABLE anchor_profit_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    profit_percent REAL NOT NULL,
    entry_time TEXT NOT NULL,
    exit_time TEXT NOT NULL,
    hold_hours REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`anchor_positions`** (1条) - trading_decision.db
```sql
CREATE TABLE anchor_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    anchor_price REAL NOT NULL,
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL,
    entry_time TEXT NOT NULL,
    stop_loss_price REAL,
    take_profit_price REAL,
    max_correction_percent REAL DEFAULT 0,
    current_correction_percent REAL DEFAULT 0,
    status TEXT DEFAULT 'open',  -- 'open', 'closed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`anchor_triggers`** (268条) - trading_decision.db
```sql
CREATE TABLE anchor_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    trigger_price REAL NOT NULL,
    correction_percent REAL NOT NULL,
    correction_level INTEGER NOT NULL,
    trigger_time TEXT NOT NULL,
    trigger_action TEXT,  -- 'open', 'add', 'alert'
    executed INTEGER DEFAULT 0,  -- 0: pending, 1: executed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 回调等级定义

| 等级 | 回调幅度 | 操作建议 |
|------|---------|---------|
| 1级 | ≥2% | 关注 |
| 2级 | ≥3% | 准备 |
| 3级 | ≥4% | 轻仓 |
| 4级 | ≥5% | 中仓 |
| 5级 | ≥6% | 重仓 |

#### 恢复后验证
```bash
# 1. 检查锚点系统数据库
cd /home/user/webapp
python3 << EOF
import sqlite3

# anchor_system.db
conn1 = sqlite3.connect('databases/anchor_system.db')
cursor1 = conn1.cursor()

cursor1.execute("SELECT COUNT(*) FROM anchor_monitors")
print(f"anchor_monitors: {cursor1.fetchone()[0]:,} records")

cursor1.execute("SELECT COUNT(*) FROM anchor_alerts")
print(f"anchor_alerts: {cursor1.fetchone()[0]:,} records")

cursor1.execute("SELECT COUNT(*) FROM anchor_profit_records")
print(f"anchor_profit_records: {cursor1.fetchone()[0]} records")

# trading_decision.db
conn2 = sqlite3.connect('databases/trading_decision.db')
cursor2 = conn2.cursor()

cursor2.execute("SELECT COUNT(*) FROM anchor_positions")
print(f"anchor_positions: {cursor2.fetchone()[0]} records")

cursor2.execute("SELECT COUNT(*) FROM anchor_triggers")
print(f"anchor_triggers: {cursor2.fetchone()[0]} records")

# 当前持仓
cursor2.execute("SELECT * FROM anchor_positions WHERE status='open'")
rows = cursor2.fetchall()
print(f"\\nCurrent open positions: {len(rows)}")
for row in rows:
    print(f"  {row}")

conn1.close()
conn2.close()
EOF

# 2. 测试API
curl http://localhost:5000/api/anchor/stats | python3 -m json.tool
curl http://localhost:5000/api/anchor/alerts | python3 -m json.tool

# 3. 访问页面
curl http://localhost:5000/anchor-monitor
```

#### 关键文件
- 数据库: `databases/anchor_system.db`, `databases/trading_decision.db`
- 页面: `source_code/templates/anchor_monitor.html`
- API: `source_code/app_new.py` (搜索 `/anchor-monitor`, `/api/anchor/`)
- 配置: 集成在 `market_config.json`

---

### 6. ⭐ 自动交易系统

#### 系统架构
```
决策流程:
支撑压力信号 + 锚点信号 → trading_decisions →
    ├→ position_opens (开仓)
    ├→ position_adds (加仓)
    ├→ position_closes (平仓)
    └→ pending_orders (挂单)

仓位管理:
long_position_monitoring → anchor_maintenance →
    ├→ anchor_adjustment_plans
    └→ anchor_maintenance_logs

风控系统:
position_extreme_records (极端记录)
anchor_warning_monitor (预警监控)
```

#### 数据库表详情

**`trading_decisions`** (3,949条)
```sql
CREATE TABLE trading_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    decision_type TEXT NOT NULL,  -- 'open', 'add', 'close', 'hold'
    current_price REAL NOT NULL,
    decision_reason TEXT,
    signal_source TEXT,  -- 'support_resistance', 'anchor', 'manual'
    decision_time TEXT NOT NULL,
    executed INTEGER DEFAULT 0,  -- 0: pending, 1: executed, 2: rejected
    execution_time TEXT,
    execution_price REAL,
    execution_quantity REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`position_opens`** (14条)
```sql
CREATE TABLE position_opens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL,
    open_time TEXT NOT NULL,
    open_reason TEXT,
    stop_loss_price REAL,
    take_profit_price REAL,
    position_id TEXT UNIQUE,
    status TEXT DEFAULT 'open',  -- 'open', 'closed', 'partially_closed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`position_adds`** (16条)
```sql
CREATE TABLE position_adds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    add_price REAL NOT NULL,
    add_quantity REAL NOT NULL,
    add_time TEXT NOT NULL,
    add_reason TEXT,
    avg_price_after REAL,  -- 加仓后平均成本
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (position_id) REFERENCES position_opens(position_id)
);
```

**`position_closes`** (16条)
```sql
CREATE TABLE position_closes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    close_price REAL NOT NULL,
    close_quantity REAL NOT NULL,
    close_time TEXT NOT NULL,
    close_reason TEXT,
    profit_loss REAL,  -- 盈亏金额
    profit_loss_percent REAL,  -- 盈亏百分比
    hold_hours REAL,  -- 持仓时长（小时）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (position_id) REFERENCES position_opens(position_id)
);
```

**`pending_orders`** (24条)
```sql
CREATE TABLE pending_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    order_type TEXT NOT NULL,  -- 'limit_buy', 'limit_sell', 'stop_loss', 'take_profit'
    trigger_price REAL NOT NULL,
    order_quantity REAL NOT NULL,
    order_time TEXT NOT NULL,
    expires_at TEXT,
    status TEXT DEFAULT 'pending',  -- 'pending', 'triggered', 'cancelled', 'expired'
    triggered_at TEXT,
    triggered_price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`long_position_monitoring`** (20,127条) - 仓位监控
```sql
CREATE TABLE long_position_monitoring (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    position_id TEXT NOT NULL,
    current_price REAL NOT NULL,
    avg_cost REAL NOT NULL,
    profit_loss_percent REAL NOT NULL,
    max_profit_percent REAL DEFAULT 0,
    max_drawdown_percent REAL DEFAULT 0,
    monitor_time TEXT NOT NULL,
    alert_level INTEGER DEFAULT 0,  -- 0: normal, 1: warning, 2: danger
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 交易策略

**开仓条件**:
1. 支撑压力线抄底信号: `scenario_1 >= 8 AND scenario_2 >= 8`
2. 锚点回调信号: 回调≥3级 (≥4%)
3. 资金流向: 大额流入
4. 无重大风险告警

**加仓条件**:
1. 已有持仓
2. 价格进一步下跌 (加仓幅度: 1%, 2%, 3%...)
3. 总仓位未超过上限

**止盈条件**:
1. 达到目标盈利 (默认: 2%, 5%, 10%)
2. 支撑压力线逃顶信号
3. 技术指标超买

**止损条件**:
1. 跌破止损价 (默认: -3%)
2. 极端市场波动
3. 锚点系统预警

#### 恢复后验证
```bash
# 1. 检查交易数据
cd /home/user/webapp
python3 << EOF
import sqlite3
conn = sqlite3.connect('databases/trading_decision.db')
cursor = conn.cursor()

tables = [
    'trading_decisions',
    'position_opens', 
    'position_adds',
    'position_closes',
    'pending_orders',
    'long_position_monitoring'
]

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"{table}: {count:,} records")

# 当前持仓
cursor.execute("SELECT * FROM position_opens WHERE status='open'")
open_positions = cursor.fetchall()
print(f"\\nCurrent open positions: {len(open_positions)}")

# 待执行挂单
cursor.execute("SELECT * FROM pending_orders WHERE status='pending'")
pending = cursor.fetchall()
print(f"Pending orders: {len(pending)}")

conn.close()
EOF

# 2. 测试API
curl http://localhost:5000/api/trading-signals | python3 -m json.tool
curl http://localhost:5000/api/positions | python3 -m json.tool

# 3. 访问页面
curl http://localhost:5000/auto-trading
```

#### 关键文件
- 数据库: `databases/trading_decision.db`
- 页面: `source_code/templates/auto_trading.html`
- 决策引擎: `source_code/trading_decision_engine.py`
- API: `source_code/app_new.py` (搜索 `/auto-trading`, `/api/trading-`)
- 配置: `market_config.json`

---

## 验证清单

### 系统级验证

- [ ] **环境验证**
  - [ ] Python 3.8+ 已安装
  - [ ] PM2 已安装
  - [ ] 所有依赖包已安装 (`pip list | grep Flask`)

- [ ] **文件验证**
  - [ ] 所有11个数据库文件存在
  - [ ] source_code 目录包含所有.py文件
  - [ ] templates 目录包含所有.html文件
  - [ ] 配置文件已恢复

- [ ] **进程验证**
  - [ ] `pm2 status` 显示5个进程都是online
  - [ ] `pm2 logs` 无严重错误
  - [ ] Flask应用响应 `curl http://localhost:5000/`

### 数据库验证

```bash
# 运行此脚本验证所有数据库
cd /home/user/webapp
python3 << 'EOF'
import sqlite3
import os

databases = {
    'crypto_data.db': ['crypto_snapshots', 'escape_signal_stats'],
    'sar_slope_data.db': ['sar_raw_data', 'sar_conversion_points'],
    'support_resistance.db': ['support_resistance_levels', 'support_resistance_snapshots'],
    'anchor_system.db': ['anchor_monitors', 'anchor_alerts'],
    'trading_decision.db': ['trading_decisions', 'position_opens'],
    'fund_monitor.db': ['fund_monitor_5min', 'fund_monitor_aggregated'],
    'v1v2_data.db': ['volume_btc', 'volume_eth']
}

print("数据库验证报告")
print("="*80)

all_ok = True
for db_name, tables in databases.items():
    db_path = f'databases/{db_name}'
    
    if not os.path.exists(db_path):
        print(f"❌ {db_name}: 文件不存在")
        all_ok = False
        continue
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n✅ {db_name}:")
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   {table}: {count:,} 条记录")
            except Exception as e:
                print(f"   ❌ {table}: {e}")
                all_ok = False
        
        conn.close()
    except Exception as e:
        print(f"❌ {db_name}: 无法连接 - {e}")
        all_ok = False

print("\n" + "="*80)
if all_ok:
    print("✅ 所有数据库验证通过！")
else:
    print("❌ 部分数据库验证失败，请检查错误信息")
EOF
```

### 页面访问验证

```bash
# 测试所有主要页面
pages=(
    "/"
    "/query"
    "/sar-analysis"
    "/support-resistance"
    "/escape-signal-history"
    "/anchor-monitor"
    "/auto-trading"
    "/fund-monitor"
    "/v1v2-analysis"
)

echo "页面访问验证"
echo "========================================"
for page in "${pages[@]}"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5000$page")
    if [ "$status" -eq 200 ]; then
        echo "✅ $page: OK ($status)"
    else
        echo "❌ $page: FAILED ($status)"
    fi
done
```

### API接口验证

```bash
# 测试关键API
apis=(
    "/api/query?time=2026-01-08%2013:00"
    "/api/escape-signal-stats"
    "/api/support-resistance/latest"
    "/api/anchor/stats"
    "/api/sar/data?symbol=BTCUSDT&limit=10"
)

echo "API接口验证"
echo "========================================"
for api in "${apis[@]}"; do
    response=$(curl -s "http://localhost:5000$api")
    if echo "$response" | grep -q "success\|data\|symbol"; then
        echo "✅ $api: OK"
    else
        echo "❌ $api: FAILED"
    fi
done
```

### PM2进程验证

```bash
pm2 status | grep online
# 应该看到5个online状态的进程:
# - flask-app
# - support-resistance-collector
# - support-resistance-snapshot
# - gdrive-detector
# - escape-stats-filler
```

---

## 常见问题排查

### 问题 1: 数据库文件损坏

**症状**: SQLite错误 "database disk image is malformed"

**解决**:
```bash
cd /home/user/webapp/databases
sqlite3 damaged.db "PRAGMA integrity_check;"

# 如果损坏，尝试修复
sqlite3 damaged.db ".dump" | sqlite3 fixed.db
mv damaged.db damaged.db.bak
mv fixed.db damaged.db
```

### 问题 2: PM2进程无法启动

**症状**: `pm2 start` 后进程立即stopped

**解决**:
```bash
# 查看详细错误日志
pm2 logs flask-app --lines 100 --err

# 检查Python路径
which python3

# 尝试手动启动测试
cd /home/user/webapp
python3 source_code/app_new.py

# 检查依赖
pip list | grep Flask
```

### 问题 3: Google Drive监控无法导入

**症状**: gdrive-detector运行但不导入数据

**解决**:
```bash
# 1. 检查配置
cat daily_folder_config.json

# 2. 测试Google Drive访问
curl "https://drive.google.com/embeddedfolderview?id=1sCHpLo3BdxjXmeW9mo30Gijpzkux0eNm"

# 3. 查看日志
pm2 logs gdrive-detector --lines 100

# 4. 手动触发导入测试
cd /home/user/webapp
python3 gdrive_final_detector.py
```

### 问题 4: 端口占用

**症状**: Flask无法启动，端口5000被占用

**解决**:
```bash
# 查看占用进程
lsof -i :5000
netstat -tulpn | grep 5000

# 杀死占用进程
kill -9 <PID>

# 或更改Flask端口
# 编辑 source_code/app_new.py
# 修改 app.run(port=5001, ...)
```

### 问题 5: 时区问题

**症状**: 数据时间显示不正确

**解决**:
```bash
# 检查系统时区
timedatectl

# 设置时区为北京时间
sudo timedatectl set-timezone Asia/Shanghai

# 验证Python时区
python3 << EOF
from datetime import datetime
import pytz
beijing_tz = pytz.timezone('Asia/Shanghai')
now = datetime.now(beijing_tz)
print(f"当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
EOF
```

---

## 性能优化建议

### 数据库优化

```bash
# 1. 为大表创建索引（如未创建）
cd /home/user/webapp
sqlite3 databases/sar_slope_data.db << 'EOF'
CREATE INDEX IF NOT EXISTS idx_sar_conversion_symbol_time 
    ON sar_conversion_points(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_sar_raw_symbol_time 
    ON sar_raw_data(symbol, timestamp);
EOF

sqlite3 databases/support_resistance.db << 'EOF'
CREATE INDEX IF NOT EXISTS idx_sr_levels_symbol_time 
    ON support_resistance_levels(symbol, record_time);
CREATE INDEX IF NOT EXISTS idx_sr_snapshots_time 
    ON support_resistance_snapshots(snapshot_time);
EOF

# 2. 定期 VACUUM
sqlite3 databases/crypto_data.db "VACUUM;"
sqlite3 databases/sar_slope_data.db "VACUUM;"
```

### 日志管理

```bash
# 1. 设置日志轮转
cat > /etc/logrotate.d/crypto-system << EOF
/home/user/webapp/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF

# 2. 清理PM2日志
pm2 flush
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

### 内存优化

```bash
# 限制Flask进程内存
pm2 delete flask-app
pm2 start source_code/app_new.py --name flask-app \
    --interpreter python3 \
    --max-memory-restart 500M

# 监控内存使用
pm2 monit
```

---

## 备份策略

### 自动备份脚本

```bash
# 创建每日备份脚本
cat > /home/user/webapp/daily_backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/user/webapp/backups"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# 备份数据库
tar -czf $BACKUP_DIR/databases_$DATE.tar.gz databases/

# 保留最近7天的备份
find $BACKUP_DIR -name "databases_*.tar.gz" -mtime +7 -delete

echo "Backup completed: databases_$DATE.tar.gz"
EOF

chmod +x /home/user/webapp/daily_backup.sh

# 添加到crontab（每天凌晨3点）
(crontab -l 2>/dev/null; echo "0 3 * * * /home/user/webapp/daily_backup.sh") | crontab -
```

---

## 联系与支持

**系统版本**: v1.0  
**最后更新**: 2026-01-10  
**文档版本**: 完整版

---

**恢复成功标志**:
- ✅ 所有5个PM2进程在线
- ✅ 11个数据库文件完整且可访问
- ✅ Flask应用响应正常
- ✅ 所有页面可访问
- ✅ 数据实时更新
- ✅ 日志无严重错误

**完成此指南后，系统应能实现1:1还原，所有功能正常工作！**
