# V1V2和价格涨速监控系统修复报告

## 修复时间
2026-01-16 10:30:00 (北京时间)

## 修复内容

### 1. V1V2成交额监控系统 (/v1v2-monitor)
**问题**: 采集器未运行，数据库为空，API返回空数据
**解决方案**:
- 创建PM2配置文件 `ecosystem_data_collectors.config.js`
- 启动 `v1v2-collector` 采集器
- 采集频率: 30秒/次
- 监控币种: 27个主流币种

**修复后状态**:
- ✅ 采集器正常运行 (PM2 ID: 24)
- ✅ 数据库正常写入 (v1v2_data.db)
- ✅ API正常返回数据 (/api/v1v2/latest)
- ✅ 页面可正常访问

**API测试结果**:
```json
{
    "count": 27,
    "data": [
        {
            "collect_time": "2026-01-16 10:25:00",
            "level": "V1",
            "symbol": "BTC",
            "v1": 200000,
            "v2": 100000,
            "volume": 5185050.46584
        },
        ...
    ],
    "success": true,
    "total": 27,
    "update_time": "2026-01-16 10:25:00",
    "v1_count": 3,
    "v2_count": 0
}
```

### 2. 1分钟涨速监控系统 (/price-speed-monitor)
**问题**: 采集器未运行，数据库为空(0字节)，API返回错误
**解决方案**:
- 启动 `price-speed-collector` 采集器
- 采集频率: 15秒/次
- 计算周期: 1分钟 (需要4个数据点)
- 监控币种: 27个主流币种

**修复后状态**:
- ✅ 采集器正常运行 (PM2 ID: 23)
- ✅ 数据库正常写入 (price_speed_data.db)
- ✅ API正常返回数据 (/api/price-speed/latest)
- ✅ 页面可正常访问

**API测试结果**:
```json
{
    "count": 27,
    "data": [
        {
            "alert_level": "general_up",
            "alert_type": "UP",
            "change_percent": 0.532978,
            "current_price": 1.509,
            "previous_price": 1.501,
            "symbol": "FIL",
            "timestamp": "2026-01-16 10:26:41"
        },
        ...
    ],
    "success": true,
    "update_time": "2026-01-16 10:27:13"
}
```

## 采集器配置

### PM2配置文件: ecosystem_data_collectors.config.js
```javascript
module.exports = {
  apps: [
    {
      name: 'price-speed-collector',
      script: 'source_code/price_speed_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      max_memory_restart: '200M'
    },
    {
      name: 'v1v2-collector',
      script: 'source_code/v1v2_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      max_memory_restart: '200M'
    }
  ]
};
```

### 采集器特性

#### price-speed-collector
- **采集间隔**: 15秒
- **计算窗口**: 60秒 (1分钟)
- **数据源**: OKEx API (ticker接口)
- **预警级别**:
  - 一般上涨/下跌: ±0.5%
  - 较强上涨/下跌: ±1.0%
  - 很强上涨/下跌: ±1.5%
  - 超强上涨/下跌: ±2.0%
- **数据保留**: 7天自动清理

#### v1v2-collector
- **采集间隔**: 30秒
- **计算窗口**: 5分钟
- **数据源**: OKEx API (candlesticks接口)
- **阈值类型**:
  - V1: 高成交额阈值
  - V2: 中成交额阈值
  - NONE: 低成交额
- **数据存储**: 每个币种独立表

## 系统访问地址

### 当前沙箱环境
- **基础URL**: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai
- **V1V2监控**: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/v1v2-monitor
- **价格涨速监控**: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/price-speed-monitor

### API端点
- **V1V2最新数据**: /api/v1v2/latest
- **价格涨速最新数据**: /api/price-speed/latest
- **价格涨速历史**: /api/price-speed/history?limit=100

## PM2进程管理

### 查看进程状态
```bash
pm2 list
pm2 info price-speed-collector
pm2 info v1v2-collector
```

### 查看日志
```bash
pm2 logs price-speed-collector --lines 50
pm2 logs v1v2-collector --lines 50
```

### 重启采集器
```bash
pm2 restart price-speed-collector
pm2 restart v1v2-collector
```

## 数据库信息

### price_speed_data.db
- **price_history**: 价格历史记录
- **price_speed_alerts**: 涨跌速预警历史
- **latest_price_speed**: 最新状态 (每个币种一条)

### v1v2_data.db
- **volume_{symbol}**: 每个币种的独立数据表 (27个表)
- 存储5分钟成交额数据
- 自动判断V1/V2/NONE级别

## 验证测试

### 1. 采集器运行状态
```bash
✅ price-speed-collector: online (PID: 767828)
✅ v1v2-collector: online (PID: 767829)
```

### 2. 数据采集测试
```bash
✅ 价格涨速: 27/27 币种成功采集
✅ V1V2成交额: 27/27 币种成功采集
✅ 1分钟后开始计算涨跌幅
✅ V1/V2级别自动判断正常
```

### 3. API测试
```bash
✅ /api/v1v2/latest: 返回27条数据
✅ /api/price-speed/latest: 返回27条数据
✅ 数据格式正确，时间戳准确
```

### 4. 页面访问测试
```bash
✅ /v1v2-monitor: 页面正常加载
✅ /price-speed-monitor: 页面正常加载
✅ 前端可正常获取API数据
```

## 监控币种列表

BTC, ETH, XRP, BNB, SOL, LTC, DOGE, SUI, TRX, TON,
ETC, BCH, HBAR, XLM, FIL, LINK, CRO, DOT, AAVE, UNI,
NEAR, APT, CFX, CRV, STX, LDO, TAO

共27个币种

## 注意事项

1. **数据积累时间**:
   - 价格涨速: 需要1分钟 (4个数据点) 后才能计算涨跌幅
   - V1V2成交额: 立即开始采集，30秒后即有数据

2. **预警机制**:
   - 价格涨速系统会自动标记异常涨跌
   - V1V2系统会自动判断成交额级别

3. **数据清理**:
   - 价格历史数据保留7天
   - 预警历史数据保留7天

4. **性能监控**:
   - 每个采集器内存限制: 200MB
   - 自动重启: 超过内存限制时

## Git提交记录

```
011e22d feat: 修复v1v2和价格涨速监控系统
- 创建 ecosystem_data_collectors.config.js PM2配置
- 启动两个采集器
- 系统现在正常工作
```

## 完成状态

✅ **全部完成** (2026-01-16 10:30:00)

- V1V2成交额监控系统: 修复完成
- 1分钟涨速监控系统: 修复完成
- 采集器运行正常
- API返回正常
- 页面可正常访问
- PM2配置已保存

## 后续维护

### 日常检查
```bash
# 检查采集器状态
pm2 status | grep -E "price-speed|v1v2"

# 查看最新日志
pm2 logs price-speed-collector --lines 20 --nostream
pm2 logs v1v2-collector --lines 20 --nostream

# 检查数据库大小
ls -lh price_speed_data.db v1v2_data.db
```

### 数据查询
```bash
# 查询最新价格涨速
curl http://localhost:5000/api/price-speed/latest | jq '.data[0:5]'

# 查询V1V2数据
curl http://localhost:5000/api/v1v2/latest | jq '.data[0:5]'
```

---

**报告生成时间**: 2026-01-16 10:30:00
**修复工程师**: Claude AI
**状态**: ✅ 全部完成
