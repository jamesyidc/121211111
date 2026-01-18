# OKX数据回填分析

## 当前状态

### OKX 27币种涨跌数据
- **数据开始时间**: 2026-01-16 17:12:13
- **当前记录数**: 19条
- **采集频率**: 每60秒一次
- **数据源**: OKX Public API (实时数据)

### 监控的27个币种
```
BTC, ETH, XRP, BNB, SOL, LTC, DOGE, SUI, TRX, TON,
ETC, BCH, HBAR, XLM, FIL, LINK, CRO, DOT, UNI, NEAR,
APT, CFX, CRV, STX, LDO, TAO, AAVE
```

## 回填需求

用户要求: **补全前面到1月3日的数据**

### 技术限制

**OKX Public API限制**:
1. **只提供当前数据**: OKX的ticker API (`/api/v5/market/tickers`) 只返回当前市场数据
2. **无历史分钟数据**: 不提供过去日期的分钟级别开盘价和当前价
3. **sodUtc8字段**: 这是UTC+8时区的当日开盘价,只有当天有效

**可用的历史数据API**:
- `/api/v5/market/candles`: K线数据 (最小时间粒度1分钟)
  - 可以获取历史K线
  - 但需要逐个币种、逐分钟请求
  - 时间范围: 1月3日00:00 到 1月16日17:12
  - 总计: **13天 × 24小时 × 60分钟 × 27币种 = 506,880次请求**

### 解决方案

#### 方案1: 使用K线数据回填 (推荐但复杂)

**步骤**:
1. 对每个币种,获取1月3日-1月16日的1分钟K线
2. 计算每分钟的当日涨跌幅:
   - 获取当日00:00的开盘价 (sodUtc8等价)
   - 计算 (当前价 - 开盘价) / 开盘价 × 100
3. 生成JSONL记录

**优点**:
- 数据完整准确
- 可以完全复现历史数据

**缺点**:
- 需要大量API请求 (50万+)
- 耗时很长 (可能需要几小时)
- 可能触发API限流

**实现代码**:
```python
# backfill_okx_data.py
import requests
import time
from datetime import datetime, timedelta
import json

SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP',
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'UNI-USDT-SWAP', 'NEAR-USDT-SWAP',
    'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP', 'STX-USDT-SWAP',
    'LDO-USDT-SWAP', 'TAO-USDT-SWAP', 'AAVE-USDT-SWAP'
]

def get_daily_candles(symbol, date_str):
    """获取某日的分钟K线"""
    # 构造时间戳
    start_time = datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S")
    end_time = start_time + timedelta(days=1)
    
    url = "https://www.okx.com/api/v5/market/candles"
    params = {
        "instId": symbol,
        "bar": "1m",
        "after": int(end_time.timestamp() * 1000),
        "before": int(start_time.timestamp() * 1000),
        "limit": 1440  # 24小时×60分钟
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['code'] == '0':
        return data['data']
    return []

def calculate_day_change(candles, day_open_price):
    """计算每分钟的涨跌幅"""
    results = []
    for candle in candles:
        timestamp, open_price, high, low, close, vol = candle[:6]
        change_pct = ((float(close) - day_open_price) / day_open_price) * 100
        results.append({
            'timestamp': int(timestamp),
            'price': float(close),
            'change_pct': round(change_pct, 4)
        })
    return results

# 主循环
for date_offset in range(13, -1, -1):  # 从1月3日到1月16日
    target_date = (datetime.now() - timedelta(days=date_offset)).strftime("%Y-%m-%d")
    print(f"处理日期: {target_date}")
    
    # 获取当日所有币种数据
    # ... (实现略)
```

#### 方案2: 使用每日快照数据 (简化版)

如果不需要分钟级别,只需要每小时或每天的快照:
- 减少数据点: 13天 × 24小时 = 312个时间点
- 只需要 312 × 27 = 8,424次请求
- 更快,但精度降低

#### 方案3: 接受现有数据,不回填 (推荐)

**理由**:
1. OKX涨跌指标是**实时趋势指标**,主要用于当前市场判断
2. 历史回填价值有限,因为是"当日涨跌",过去的当日涨跌对现在意义不大
3. 从今天开始积累数据,2-3天后就有足够的历史数据用于分析

**建议**:
- ✅ 保持当前采集器运行
- ✅ 让数据自然积累
- ✅ 等待3-7天后就有完整的周数据

## 推荐方案

**采用方案3**: 不进行回填,从今天开始自然积累数据

**原因**:
1. 回填成本高 (API请求、时间、复杂度)
2. OKX涨跌是实时指标,历史数据价值有限
3. 3-7天后就有足够数据用于趋势分析
4. 采集器已经稳定运行,每分钟自动采集

## 当前采集器状态

- ✅ `okx-day-change-collector` 正常运行
- ✅ 每60秒采集一次
- ✅ 27个币种全覆盖 (25个成功 + 2个不存在)
- ✅ 数据实时写入JSONL
- ✅ API端点已就绪
- ✅ 前端已集成显示

## 结论

**建议**: 等待数据自然积累,3-7天后即可进行完整的趋势分析。

如果用户坚持要回填历史数据,可以实施方案1,但需要:
1. **时间投入**: 预计2-4小时
2. **API限流风险**: 可能需要添加延迟
3. **价值评估**: 考虑是否值得投入

