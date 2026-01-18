# 恐慌指数与SAR多空占比系统部署文档

## 系统概述

本系统包含两个数据采集与统计模块：
1. **恐慌清洗指数采集器** - 监控全网爆仓数据并计算恐慌/清洗指数
2. **SAR多空占比统计器** - 统计各币种2小时内的多空占比情况

## 数据存储

所有数据使用 **JSONL 格式** 存储在 `/home/user/webapp/data/panic_jsonl/` 目录：

```
data/panic_jsonl/
├── panic_wash_index.jsonl      # 恐慌清洗指数数据
└── sar_bias_stats.jsonl        # SAR多空占比统计数据
```

### 数据格式

#### 恐慌清洗指数记录
```json
{
  "record_time": "2026-01-14 13:52:04",
  "record_date": "2026-01-14",
  "hour_1_amount": 3939665.69,
  "hour_24_amount": 374048177.64,
  "hour_24_people": 86030,
  "total_position": 40000000000.00,
  "panic_index": 0.02,
  "wash_index": 0.94,
  "created_at": "2026-01-14 13:52:04"
}
```

#### SAR多空占比统计记录
```json
{
  "record_time": "2026-01-14 13:52:13",
  "bullish_over_80_count": 11,
  "bearish_over_80_count": 1,
  "bullish_over_80_symbols": "BTC,ETH,SOL,BNB,DOGE,LINK,UNI,LTC,ETC,FIL,APT",
  "bearish_over_80_symbols": "DOT",
  "total_symbols": 20,
  "stats_detail": [...],
  "created_at": "2026-01-14 13:52:13"
}
```

## 系统组件

### 1. 恐慌清洗指数采集器

**文件**: `panic_collector_jsonl.py`

#### 功能
- 每 **3 分钟** 采集一次全网爆仓数据
- 计算恐慌指数 = 24小时爆仓人数(万人) / 全网持仓量(亿美元)
- 计算清洗指数 = 24小时爆仓金额(亿美元) / 全网持仓量(亿美元) × 100

#### 数据源
- **24小时爆仓**: `https://api.btc123.fans/bicoin.php?from=24hbaocang`
- **1小时爆仓**: `https://api.btc123.fans/bicoin.php?from=1hbaocang`
- **全网持仓**: 使用估算值 400 亿美元（原API失效）

#### 指数等级
| 恐慌指数 | 等级 | 颜色 |
|---------|------|------|
| < 5 | 低恐慌 | 绿色 |
| 5-10 | 中度恐慌 | 黄色 |
| > 10 | 高度恐慌 | 红色 |

### 2. SAR多空占比统计器

**文件**: `sar_bias_collector.py`

#### 功能
- 每 **3 分钟** 统计一次所有币种的2小时多空占比
- 统计偏多占比 > 80% 的币种数量和列表
- 统计偏空占比 > 80% 的币种数量和列表

#### 监控币种（20个）
```
BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, LINK, DOT,
MATIC, UNI, LTC, ATOM, ETC, XLM, NEAR, ALGO, FIL, APT
```

## API接口

### 恐慌清洗指数API

#### 获取最新数据
```
GET /api/panic/latest
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "record_time": "2026-01-14 13:52:04",
    "panic_index": 0.02,
    "wash_index": 0.94,
    "panic_level": "低恐慌",
    "level_color": "green",
    "hour_24_people": 8.6,
    "total_position": 400.0,
    "hour_1_amount": 393.97,
    "hour_24_amount": 37404.82,
    "market_zone": "8.6万人/400.0亿美元"
  }
}
```

### SAR多空占比统计API

#### 获取最新统计
```
GET /api/sar-slope/bias-stats/latest
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "record_time": "2026-01-14 13:52:13",
    "bullish_over_80_count": 11,
    "bearish_over_80_count": 1,
    "bullish_over_80_symbols": ["BTC", "ETH", "SOL", ...],
    "bearish_over_80_symbols": ["DOT"],
    "total_symbols": 20
  }
}
```

#### 获取历史数据
```
GET /api/sar-slope/bias-stats/history?limit=100
```

## PM2进程管理

### 当前运行的进程

| ID | 进程名 | 功能 | 状态 |
|----|--------|------|------|
| 8 | panic-collector | 恐慌指数采集器 | ✅ online |
| 9 | sar-bias-collector | SAR多空占比统计器 | ✅ online |

### 常用命令

```bash
# 查看所有进程
pm2 list

# 查看特定进程日志
pm2 logs panic-collector
pm2 logs sar-bias-collector

# 重启进程
pm2 restart panic-collector
pm2 restart sar-bias-collector

# 停止进程
pm2 stop panic-collector
pm2 stop sar-bias-collector

# 查看进程详情
pm2 show panic-collector
pm2 show sar-bias-collector

# 保存当前进程列表
pm2 save

# 查看最近20行日志（不持续）
pm2 logs panic-collector --lines 20 --nostream
pm2 logs sar-bias-collector --lines 20 --nostream
```

## 日志文件

```
/home/user/webapp/logs/
├── panic_collector_out.log       # 恐慌指数采集器输出日志
├── panic_collector_error.log     # 恐慌指数采集器错误日志
├── sar_bias_collector_out.log    # SAR统计器输出日志
└── sar_bias_collector_error.log  # SAR统计器错误日志
```

## 前端页面

### 恐慌清洗指数页面
```
https://5000-xxx.sandbox.novita.ai/panic
```

显示内容：
- 恐慌指数（实时）
- 清洗指数（实时）
- 24小时爆仓人数
- 24小时爆仓金额
- 1小时爆仓金额
- 全网持仓量
- 恐慌等级（低/中/高）

### SAR斜率系统页面
```
https://5000-xxx.sandbox.novita.ai/sar-slope
```

显示内容（页面顶部）：
- 偏多占比 > 80% 的币种数量
- 偏空占比 > 80% 的币种数量
- 各币种的具体多空占比数据

## 测试验证

### 测试恐慌指数采集
```bash
cd /home/user/webapp
python3 panic_collector_jsonl.py once
```

### 测试SAR多空占比统计
```bash
cd /home/user/webapp
python3 sar_bias_collector.py once
```

### 测试API
```bash
# 恐慌指数API
curl http://localhost:5000/api/panic/latest | python3 -m json.tool

# SAR多空占比API
curl http://localhost:5000/api/sar-slope/bias-stats/latest | python3 -m json.tool
```

## 数据查看

### 查看最新数据
```bash
cd /home/user/webapp

# 恐慌指数最新记录
tail -1 data/panic_jsonl/panic_wash_index.jsonl | python3 -m json.tool

# SAR多空占比最新记录
tail -1 data/panic_jsonl/sar_bias_stats.jsonl | python3 -m json.tool
```

### 统计信息
```bash
cd /home/user/webapp

# 恐慌指数记录总数
wc -l data/panic_jsonl/panic_wash_index.jsonl

# SAR多空占比记录总数
wc -l data/panic_jsonl/sar_bias_stats.jsonl
```

## 采集频率

- **恐慌指数采集器**: 每 3 分钟（180秒）
- **SAR多空占比统计器**: 每 3 分钟（180秒）

修改采集频率：编辑对应的 `.py` 文件，修改 `run(interval=180)` 中的数值。

## 故障排查

### 采集器未运行
```bash
pm2 list  # 查看进程状态
pm2 restart panic-collector  # 重启
pm2 logs panic-collector  # 查看日志
```

### API返回错误
```bash
pm2 restart flask-app  # 重启Flask应用
pm2 logs flask-app  # 查看错误日志
```

### 数据未更新
1. 检查采集器进程状态：`pm2 list`
2. 查看采集器日志：`pm2 logs panic-collector --lines 50`
3. 检查JSONL文件最后修改时间：`ls -lh data/panic_jsonl/`

## 系统监控建议

1. **每日检查**: 确认采集器正常运行
2. **数据验证**: 定期查看最新记录是否合理
3. **磁盘空间**: 监控 JSONL 文件大小（每月约增长 50-100MB）
4. **API响应**: 测试API是否正常返回数据

## 备份与恢复

### 备份数据
```bash
cd /home/user/webapp
tar -czf panic_data_backup_$(date +%Y%m%d).tar.gz data/panic_jsonl/
```

### 恢复数据
```bash
cd /home/user/webapp
tar -xzf panic_data_backup_YYYYMMDD.tar.gz
```

## 版本信息

- **创建日期**: 2026-01-14
- **Python版本**: 3.x
- **依赖库**: requests, pytz
- **数据格式**: JSONL
- **PM2配置**: ecosystem_panic_sar.config.js

---

**最后更新**: 2026-01-14  
**维护者**: AI Assistant
