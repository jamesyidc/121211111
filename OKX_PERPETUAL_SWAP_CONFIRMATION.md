# OKX永续合约数据确认说明

## ✅ 数据源确认

### 当前系统配置

**数据来源**: OKX永续合约市场（OKX Perpetual Swap）

**合约格式**:
```
{币种}-USDT-SWAP

示例:
- BTC-USDT-SWAP  (比特币永续合约)
- ETH-USDT-SWAP  (以太坊永续合约)
- XRP-USDT-SWAP  (瑞波币永续合约)
```

**API接口**:
```
基础URL: https://www.okx.com/api/v5
接口: /market/ticker
参数: instId={币种}-USDT-SWAP
```

**数据示例**:
```bash
# BTC永续合约价格查询
curl "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP"

# 返回示例
{
  "code": "0",
  "msg": "",
  "data": [{
    "instId": "BTC-USDT-SWAP",
    "last": "95417.50",      # 最新成交价
    "lastSz": "0.001",
    "askPx": "95417.60",
    "bidPx": "95417.50",
    "open24h": "96810.40",
    "high24h": "97200.00",
    "low24h": "94800.00",
    "volCcy24h": "1234567890",
    "vol24h": "12345",
    "ts": "1737003600000"
  }]
}
```

## 🔄 失败重试机制

### 已实现功能 ✅

1. **即时重试**
   - 单次采集内最多重试3次
   - 重试间隔0.5秒
   - 适用于临时网络波动

2. **失败队列**
   - 失败任务自动记录到队列
   - 持久化存储到 `failed_queue.json`
   - 下次采集优先处理（最多10个）

3. **无限重试**
   - 失败任务持续重试直到成功
   - 无重试次数上限
   - 自动从队列移除成功的任务

4. **失败检测**
   系统会在以下情况判定为失败：
   - HTTP请求超时（>10秒）
   - HTTP状态码非200
   - OKX API返回错误码（code != "0"）
   - 返回的价格数据为空或为0
   - 网络异常或其他未知错误

### 数据结构

**失败任务记录**:
```json
{
  "symbol": "BTC",                        # 币种
  "collect_time": "2026-01-16 12:00:00", # 采集时间点
  "failed_at": "2026-01-16 12:01:30",    # 失败时间
  "reason": "获取失败（3次尝试）",         # 失败原因
  "retry_count": 2                        # 已重试次数
}
```

**失败队列文件**: `data/coin_price_tracker/failed_queue.json`

### 重试流程

```
开始新一轮采集
    ↓
检查失败队列 (failed_queue.json)
    ↓
[有失败任务]
    ↓
优先处理失败队列（最多10个）
    ├── 成功 → 从队列移除 ✅
    └── 失败 → retry_count+1，保留在队列 ⚠️
    ↓
正常采集27个币种
    ├── 成功 → 保存数据 ✅
    └── 失败 → 添加到失败队列 ⚠️
    ↓
显示统计信息
    ├── 成功数量: X/27
    ├── 失败队列: Y个任务
    └── 按币种分组统计
    ↓
等待30分钟
    ↓
进入下一轮采集
```

## 📊 当前系统状态

### 运行状态 ✅
```
✅ 采集成功率: 27/27 (100%)
✅ 失败队列: 0个任务
✅ 系统状态: 正常运行
✅ PM2进程: coin-price-tracker (online)
```

### 数据统计
```
采集频率: 每30分钟
数据点数: 48个/天
基准时间: 每天UTC+8 00:00
数据源: OKX永续合约
币种数量: 27个
```

### 27个币种清单
```
BTC, ETH, XRP, BNB, SOL, LTC, DOGE, SUI, TRX, TON,
ETC, BCH, HBAR, XLM, FIL, LINK, CRO, DOT, UNI, NEAR,
APT, CFX, CRV, STX, LDO, TAO, AAVE
```

## 🔍 监控方法

### 1. 查看最新采集日志
```bash
cd /home/user/webapp && tail -50 logs/coin_price_tracker.log
```

### 2. 查看失败队列
```bash
cd /home/user/webapp && cat data/coin_price_tracker/failed_queue.json | jq '.'
```

### 3. 查看失败队列统计
```bash
cd /home/user/webapp && cat data/coin_price_tracker/failed_queue.json | jq 'group_by(.symbol) | map({symbol: .[0].symbol, count: length})'
```

### 4. 查看最近5条数据
```bash
cd /home/user/webapp && tail -5 data/coin_price_tracker/coin_prices_30min.jsonl | jq '.collect_time, .valid_coins, .total_coins'
```

### 5. 实时监控日志
```bash
cd /home/user/webapp && tail -f logs/coin_price_tracker.log
```

## 📁 关键文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 采集脚本 | `source_code/coin_price_tracker.py` | 主程序 |
| 数据文件 | `data/coin_price_tracker/coin_prices_30min.jsonl` | JSONL格式 |
| 失败队列 | `data/coin_price_tracker/failed_queue.json` | JSON格式 |
| 运行日志 | `logs/coin_price_tracker.log` | 文本日志 |

## 🎯 数据质量保证

### 多层验证
1. ✅ **HTTP层**: 状态码200
2. ✅ **API层**: OKX返回码为"0"
3. ✅ **数据层**: 价格 > 0
4. ✅ **逻辑层**: 基准价格 > 0

### 错误处理
- 网络超时自动重试
- API错误详细记录
- 失败任务持久化
- 优先重试机制

## ✨ 系统优势

1. **可靠性高**
   - 3次即时重试
   - 无限次跨周期重试
   - PM2自动重启

2. **数据完整**
   - 失败任务不丢失
   - 持久化存储
   - 优先补全缺失数据

3. **监控完善**
   - 详细日志记录
   - 实时统计信息
   - 失败原因追踪

4. **易于维护**
   - 代码结构清晰
   - 文档齐全
   - 监控命令简单

## 📈 历史数据支持

系统同时支持历史数据查询：

**历史数据页面**: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/coin-price-history

**功能特性**:
- 日期范围: 2026-01-03 至 2026-01-16
- 时间粒度: 30分钟
- 每天数据点: 48个
- 基准时间: 每天00:00
- 支持CSV导出

## 🎉 总结

### 已确认 ✅
- **数据源**: OKX永续合约市场
- **合约格式**: {币种}-USDT-SWAP
- **失败重试**: 完整实现
- **优先重试**: 失败队列机制
- **持久化**: failed_queue.json
- **无限重试**: 直到成功

### 当前状态 ✅
- **采集成功率**: 27/27 (100%)
- **失败队列**: 0个任务
- **系统状态**: 正常运行
- **下次采集**: 自动进行

---

**最后更新**: 2026-01-16 13:35
**系统状态**: ✅ 生产环境运行中
**数据源**: OKX永续合约 (XXX-USDT-SWAP)
**失败重试**: ✅ 已完全实现
