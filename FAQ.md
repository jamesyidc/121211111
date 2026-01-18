# 常见问题解答 (FAQ)

## Q1: 价格数据来自哪里？
**A**: 所有价格数据来自 **OKX永续合约**

- 合约格式：`{SYMBOL}-USDT-SWAP`
- 例如：`BTC-USDT-SWAP`、`ETH-USDT-SWAP`等
- 共27个币种的永续合约

---

## Q2: 如果获取失败会怎么样？
**A**: 系统有完善的失败重试机制

1. **自动记录失败任务**
   - 失败的币种和时间点会被记录到队列
   - 保存到 `data/coin_price_tracker/failed_queue.json`

2. **优先重试**
   - 下次采集时优先重试失败的任务
   - 最多重试10个失败任务/次

3. **持续重试**
   - 直到成功才从队列移除
   - 无最大重试次数限制

---

## Q3: 如何查看失败列表？
**A**: 有多种方式查看

### 方法1：查看失败队列文件
```bash
cd /home/user/webapp
cat data/coin_price_tracker/failed_queue.json | jq '.'
```

### 方法2：查看采集日志
```bash
cd /home/user/webapp
tail -100 logs/coin_price_tracker.log | grep "失败队列"
```

### 方法3：查看数据完整性
```bash
cd /home/user/webapp
tail -10 data/coin_price_tracker/coin_prices_30min.jsonl | jq '{time: .collect_time, valid: .valid_coins, total: .total_coins}'
```

---

## Q4: 数据采集频率是多少？
**A**: 每30分钟采集一次

- 采集间隔：30分钟
- 每天数据点：48个（00:00, 00:30, 01:00, ..., 23:30）
- 基准时间：每天UTC+8 00:00

---

## Q5: 基准价格是如何确定的？
**A**: 每天UTC+8 00:00（北京时间凌晨0点）的价格

- 使用1小时K线获取00:00的开盘价
- 每天凌晨0点自动更新基准价格
- 全天的涨跌幅都相对于这个基准计算

---

## Q6: 涨跌幅如何计算？
**A**: 公式：`(当前价格 - 基准价格) / 基准价格 × 100%`

**示例**：
- 基准价格（00:00）：$95,392.80
- 当前价格（09:30）：$95,500.00
- 涨跌幅：(95500 - 95392.80) / 95392.80 × 100% = +0.11%

---

## Q7: 历史数据从什么时候开始？
**A**: 从2026年1月3日开始回填

- 回填时间范围：2026-01-03 00:00 ~ 2026-01-16 23:30
- 回填粒度：30分钟/点
- 总数据点：672个（14天 × 48点/天）
- 回填状态：正在进行中

---

## Q8: 页面访问地址是什么？
**A**: 有两个页面

### 实时监控页面
```
https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/coin-price-tracker
```
- 显示最近24小时的实时数据
- 自动刷新

### 历史数据查询页面
```
https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/coin-price-history
```
- 按日期查询（1月3日-1月16日）
- 详细数据表格
- 支持CSV导出

---

## Q9: 如何查看某个时间点的失败情况？
**A**: 查看JSONL数据文件

```bash
cd /home/user/webapp
grep "2026-01-16 13:30" data/coin_price_tracker/coin_prices_30min.jsonl | jq '.'
```

查看 `valid_coins` 字段：
- `valid_coins: 27` - 全部成功
- `valid_coins: 26` - 有1个失败
- `valid_coins: 25` - 有2个失败

失败的币种其 `current_price` 会是 `0`。

---

## Q10: 系统会自动恢复失败的数据吗？
**A**: 会的，完全自动

1. **自动记录**：失败时自动加入队列
2. **自动重试**：下次采集优先重试
3. **自动更新**：重试成功后自动更新数据
4. **自动清理**：成功后自动从队列移除

完全无需人工干预！

---

## Q11: 重试次数有限制吗？
**A**: 单次3次，跨周期无限制

- **单次采集**：每个币种最多重试3次（间隔0.5秒）
- **跨周期重试**：无限制，直到成功
- **优先级**：失败任务优先处理

---

## Q12: 如何监控系统运行状态？
**A**: 使用PM2和日志监控

### 查看进程状态
```bash
pm2 status coin-price-tracker
```

### 查看实时日志
```bash
pm2 logs coin-price-tracker --lines 50
```

### 查看失败队列统计
```bash
cd /home/user/webapp
cat data/coin_price_tracker/failed_queue.json | jq 'length'
```

### 查看最近采集成功率
```bash
cd /home/user/webapp
tail -10 data/coin_price_tracker/coin_prices_30min.jsonl | jq '.valid_coins'
```

---

## Q13: 数据文件在哪里？
**A**: 所有数据在 `data/coin_price_tracker/` 目录

```
data/coin_price_tracker/
├── coin_prices_30min.jsonl  # 价格数据（每30分钟一条）
└── failed_queue.json         # 失败队列（失败任务列表）
```

---

## Q14: 如何手动触发重试？
**A**: 重启采集器即可

```bash
cd /home/user/webapp
pm2 restart coin-price-tracker
```

重启后会自动：
1. 加载失败队列
2. 优先重试失败任务
3. 继续正常采集

---

## Q15: 如果某个币种一直失败怎么办？
**A**: 查看日志分析原因

```bash
cd /home/user/webapp
tail -100 logs/coin_price_tracker.log | grep "币种名称"
```

常见原因：
- API限流（HTTP 429）
- 合约不存在或暂停交易
- 网络问题
- OKX服务异常

建议：等待下次自动重试，系统会持续尝试。

---

## Q16: 数据可以导出吗？
**A**: 可以，有两种方式

### 方式1：页面导出（推荐）
1. 访问历史数据页面
2. 选择日期并查询
3. 点击【导出CSV】按钮

### 方式2：直接读取JSONL
```bash
cd /home/user/webapp
cat data/coin_price_tracker/coin_prices_30min.jsonl | jq -r '.coins | to_entries[] | "\(.key),\(.value.base_price),\(.value.current_price),\(.value.change_pct)"' > export.csv
```

---

## Q17: 系统性能如何？
**A**: 轻量高效

- CPU占用：< 1%
- 内存占用：~30MB
- 磁盘写入：~1MB/天
- 网络请求：27个币种 × 2次/30分钟 = 54次/30分钟

---

## Q18: 有告警功能吗？
**A**: 目前仅日志告警

失败时会在日志中输出：
```
⚠️  失败的币种: BTC, ETH, XRP
⚠️  添加到失败队列: BTC @ 2026-01-16 13:30:00
```

可配合日志监控工具实现告警。

---

## Q19: 数据精度如何？
**A**: 精确到小数点后8位

- 价格：最多8位小数（如 $0.00001234）
- 涨跌幅：4位小数（如 +1.2345%）
- 时间戳：秒级精度

---

## Q20: 系统会自动处理跨日问题吗？
**A**: 会的，完全自动

- 每天凌晨0点自动检测
- 自动获取新的基准价格
- 自动重置涨跌幅计算基准
- 无需人工干预

---

**更新时间**: 2026-01-16 13:20  
**文档版本**: v1.0.0
