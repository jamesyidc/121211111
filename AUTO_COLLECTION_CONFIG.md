# 27币种价格追踪系统 - 自动运行配置 ✅

## 📊 系统概述

**系统名称**: 27币种涨跌幅追踪器  
**运行模式**: 自动采集（PM2守护进程）  
**采集间隔**: **每30分钟一次**  
**数据源**: **OKX永续合约API**  
**时区**: 北京时间 (UTC+8)

---

## ⚙️ 运行配置

### PM2进程信息

| 配置项 | 值 |
|--------|-----|
| **进程名称** | `coin-price-tracker` |
| **进程ID** | 34 |
| **运行状态** | ✅ Online |
| **脚本路径** | `/home/user/webapp/source_code/coin_price_tracker.py` |
| **解释器** | Python3 |
| **自动重启** | ✅ 启用 |
| **运行时长** | 持续运行 |

### 采集配置

```python
# 采集间隔
INTERVAL = 30 * 60  # 1800秒 = 30分钟

# 27个币种
SYMBOLS = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "LTC", "DOGE", "SUI", "TRX", "TON",
    "ETC", "BCH", "HBAR", "XLM", "FIL", "LINK", "CRO", "DOT", "UNI", "NEAR",
    "APT", "CFX", "CRV", "STX", "LDO", "TAO", "AAVE"
]

# OKX API
API_ENDPOINT = "https://www.okx.com/api/v5/market/ticker"
INSTRUMENT_ID = "{SYMBOL}-USDT-SWAP"
```

---

## 📁 数据存储

### 文件路径

| 文件类型 | 路径 |
|---------|------|
| **主数据文件** | `/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl` |
| **失败队列** | `/home/user/webapp/data/coin_price_tracker/failed_queue.json` |
| **错误日志** | `/home/user/webapp/logs/coin_price_tracker_error.log` |
| **输出日志** | `/home/user/.pm2/logs/coin-price-tracker-out.log` |

### 数据格式

```json
{
  "timestamp": 1767455200,
  "collect_time": "2026-01-04 00:00:00",
  "base_date": "2026-01-04",
  "coins": {
    "BTC": {
      "base_price": 90012.70,
      "current_price": 91065.00,
      "change_pct": 1.17
    },
    "ETH": { ... },
    ...
  }
}
```

---

## 🔄 工作流程

### 采集周期

```
00:00 → 采集（基准点）
  ↓ 30分钟
00:30 → 采集
  ↓ 30分钟
01:00 → 采集
  ↓ 30分钟
01:30 → 采集
  ...
23:30 → 采集
  ↓ 30分钟
00:00 → 新一天（新基准点）
```

### 每次采集流程

1. **获取当天基准价** (北京时间 00:00:00)
   ```
   - 如果缓存有：直接使用
   - 如果缓存无：从OKX获取
   ```

2. **获取当前价格** (所有27个币种)
   ```
   - 并发请求OKX API
   - 每个币种独立请求
   - 失败自动重试3次
   ```

3. **计算涨跌幅**
   ```
   change_pct = (current_price - base_price) / base_price × 100
   ```

4. **保存数据**
   ```
   - 追加到JSONL文件
   - 失败任务加入队列
   ```

5. **下次采集优先处理失败任务**

---

## 📊 当前状态

### 数据统计

- ✅ **总记录数**: 673条
- ✅ **时间范围**: 2026-01-03 00:00:00 ~ 2026-01-17 00:12:27
- ✅ **数据完整性**: 100% (27/27币种)
- ✅ **平均采集间隔**: 28-30分钟
- ✅ **运行状态**: 正常

### 最近采集记录

| 时间 | 基准日期 | 数据完整性 | 状态 |
|------|---------|-----------|------|
| 2026-01-16 22:30:00 | 2026-01-16 | 27/27 | ✅ |
| 2026-01-16 23:00:00 | 2026-01-16 | 27/27 | ✅ |
| 2026-01-16 23:30:00 | 2026-01-16 | 27/27 | ✅ |
| 2026-01-17 00:00:00 | 2026-01-17 | 27/27 | ✅ (新基准) |
| 2026-01-17 00:30:00 | 2026-01-17 | 27/27 | ✅ (预期) |

---

## 🛠️ 管理命令

### PM2进程管理

```bash
# 查看进程状态
pm2 status coin-price-tracker

# 查看实时日志
pm2 logs coin-price-tracker

# 查看最近30行日志
pm2 logs coin-price-tracker --lines 30 --nostream

# 重启进程
pm2 restart coin-price-tracker

# 停止进程
pm2 stop coin-price-tracker

# 启动进程
pm2 start coin-price-tracker

# 删除进程
pm2 delete coin-price-tracker
```

### 手动运行脚本

```bash
cd /home/user/webapp
python3 source_code/coin_price_tracker.py
```

### 数据查询

```bash
# 查看总记录数
wc -l data/coin_price_tracker/coin_prices_30min.jsonl

# 查看最新5条记录
tail -5 data/coin_price_tracker/coin_prices_30min.jsonl

# 查看今天的记录
grep "2026-01-17" data/coin_price_tracker/coin_prices_30min.jsonl

# 验证JSON格式
cat data/coin_price_tracker/coin_prices_30min.jsonl | jq -s '.'
```

---

## 🔍 监控指标

### 健康检查项

- ✅ **PM2进程状态**: Online
- ✅ **采集间隔**: 30分钟 ±2分钟
- ✅ **数据完整性**: 27/27币种
- ✅ **API成功率**: >95%
- ✅ **文件大小增长**: ~2KB/30分钟

### 告警条件

- ⚠️ PM2进程状态: Stopped/Errored
- ⚠️ 超过1小时未采集数据
- ⚠️ 数据完整性 <20/27币种
- ⚠️ API成功率 <80%
- ⚠️ 磁盘空间不足

---

## 🔧 故障排查

### 问题1: 进程停止

```bash
# 检查PM2状态
pm2 status coin-price-tracker

# 查看错误日志
tail -50 /home/user/webapp/logs/coin_price_tracker_error.log

# 重启进程
pm2 restart coin-price-tracker
```

### 问题2: 数据未更新

```bash
# 检查最新记录时间
tail -1 data/coin_price_tracker/coin_prices_30min.jsonl | jq '.collect_time'

# 查看实时日志
pm2 logs coin-price-tracker

# 手动触发采集
python3 source_code/coin_price_tracker.py
```

### 问题3: API请求失败

```bash
# 检查网络连接
curl -I https://www.okx.com/api/v5/market/ticker

# 查看失败队列
cat data/coin_price_tracker/failed_queue.json

# 查看详细错误
grep "ERROR" logs/coin_price_tracker_error.log | tail -20
```

---

## 📈 数据使用

### Web界面

**URL**: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/coin-price-tracker

功能：
- 📊 27币涨跌幅总和曲线图
- 📅 日期选择器（查看历史数据）
- 🔍 每个时间点的27币详情
- 📥 CSV数据导出
- 📝 实时日志监控

### API接口

```bash
# 查询指定时间范围的数据
curl "http://localhost:5000/api/coin-price-tracker/history?start_time=2026-01-17%2000:00:00&end_time=2026-01-17%2023:59:59"

# 返回格式
{
  "success": true,
  "count": 48,
  "data": [ ... ]
}
```

---

## ✅ 系统保障

### 自动化保障

- ✅ **PM2守护进程**: 自动重启
- ✅ **失败重试机制**: 3次重试
- ✅ **失败队列**: 下次优先处理
- ✅ **日志记录**: 完整日志
- ✅ **数据备份**: JSONL追加模式

### 数据质量保障

- ✅ **时区统一**: 北京时间 (UTC+8)
- ✅ **基准价正确**: 每天00:00北京时间
- ✅ **涨跌幅准确**: 基于正确时区计算
- ✅ **数据完整**: 27/27币种
- ✅ **格式标准**: JSON Lines

---

## 📝 维护建议

### 日常检查

1. **每天检查一次**PM2进程状态
2. **每周检查一次**数据完整性
3. **每月检查一次**磁盘空间

### 数据备份

```bash
# 备份数据文件
cp data/coin_price_tracker/coin_prices_30min.jsonl \
   data/coin_price_tracker/backup/coin_prices_$(date +%Y%m%d).jsonl

# 压缩备份
tar -czf coin_tracker_backup_$(date +%Y%m%d).tar.gz \
   data/coin_price_tracker/
```

### 日志清理

```bash
# PM2日志清理
pm2 flush coin-price-tracker

# 自定义日志清理（保留最近30天）
find logs/ -name "coin_price_tracker_*.log" -mtime +30 -delete
```

---

## 🚀 未来规划

1. ✅ **持续采集**: 已完成，每30分钟自动运行
2. 📊 **数据分析**: 可添加统计分析功能
3. 📧 **告警通知**: 可添加异常告警（邮件/Telegram）
4. 📈 **性能优化**: 可优化并发请求
5. 🔄 **数据归档**: 可添加定期归档机制

---

**文档更新时间**: 2026-01-17  
**系统版本**: v1.0  
**维护状态**: ✅ 正常运行

---

🎉 **系统已配置完成，将自动每30分钟从OKX采集27个币种的价格数据！**
