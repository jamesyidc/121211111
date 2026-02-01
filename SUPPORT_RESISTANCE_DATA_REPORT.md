# 支撑阻力系统 - JSONL 数据统计报告

## 📍 访问地址
https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/support-resistance

## 📊 数据文件概览

### 数据目录
```
/home/user/webapp/data/support_resistance_jsonl/
```

### 文件列表

#### 1️⃣ support_resistance_levels.jsonl
- **文件大小**: 697 MB
- **记录总数**: 709,327 条
- **数据范围**: 2026-01-24 11:23:53 ~ 2026-01-24 19:30:35
- **时间跨度**: 约 8 小时（今天的数据）
- **数据频率**: 约 88,666 条/小时
- **说明**: 实时支撑阻力位数据，包含27个币种的详细支撑阻力位计算结果

**数据结构示例**:
```json
{
    "id": 404,
    "symbol": "ETCUSDT",
    "current_price": 11.98,
    "support_line_1": 11.83,
    "support_line_2": 11.83,
    "resistance_line_1": 12.49,
    "resistance_line_2": 12.07,
    "support_1_days": 7,
    "support_2_hours": 48,
    "resistance_1_days": 7,
    "resistance_2_hours": 48,
    "distance_to_support_1": 1.27,
    "distance_to_support_2": 1.27,
    "distance_to_resistance_1": 4.26,
    "distance_to_resistance_2": 0.75,
    "record_time": "2026-01-24 11:23:53",
    "record_time_beijing": "2026-01-24 11:23:53",
    "position_s2_r1": 22.73,
    "position_s1_r2": 62.50
}
```

**字段说明**:
- `support_line_1/2`: 支撑位1和2
- `resistance_line_1/2`: 阻力位1和2
- `support_1_days`: 支撑位1的历史天数
- `support_2_hours`: 支撑位2的历史小时数
- `distance_to_support_1/2`: 当前价格到支撑位的距离百分比
- `distance_to_resistance_1/2`: 当前价格到阻力位的距离百分比
- `position_s2_r1`: 当前价格在支撑2和阻力1之间的位置百分比
- `position_s1_r2`: 当前价格在支撑1和阻力2之间的位置百分比

---

#### 2️⃣ support_resistance_snapshots.jsonl
- **文件大小**: 25 MB
- **记录总数**: 30,256 条
- **数据范围**: 2025-12-25 09:52:25 ~ 2026-01-19 23:04:57
- **时间跨度**: 26 天
- **数据频率**: 约 1,164 条/天（约 48 条/小时）
- **说明**: 支撑阻力场景快照数据，记录4种场景的币种分布

**数据结构示例**:
```json
{
    "id": 4711,
    "snapshot_time": "2025-12-25 09:52:25",
    "snapshot_date": "2025-12-25",
    "scenario_1_count": 1,
    "scenario_2_count": 1,
    "scenario_3_count": 8,
    "scenario_4_count": 8,
    "scenario_1_coins": "[{...}]",
    "scenario_2_coins": "[{...}]",
    "scenario_3_coins": "[{...}]",
    "scenario_4_coins": "[{...}]",
    "total_coins": 27,
    "created_at": "2025-12-25 01:52:25",
    "snapshot_time_beijing": "2025-12-25 09:52:25"
}
```

**4种场景说明**:
- **场景1**: 价格接近支撑2和阻力1之间
- **场景2**: 价格接近支撑1和阻力2之间
- **场景3**: 价格接近支撑1和阻力2（95%以上位置）
- **场景4**: 价格接近支撑1和阻力1（95%以上位置）

---

#### 3️⃣ okex_kline_ohlc.jsonl
- **文件大小**: 15 MB
- **记录总数**: 50,000 条
- **说明**: OKEx K线数据（OHLC: Open, High, Low, Close）
- **用途**: 用于计算支撑阻力位的历史价格数据

---

#### 4️⃣ daily_baseline_prices.jsonl
- **文件大小**: 4.2 MB
- **记录总数**: 14,684 条
- **说明**: 每日基准价格数据
- **用途**: 记录每天开盘时的基准价格，用于日内涨跌幅计算

---

## 📅 数据时间线总结

```
时间线可视化：

2025-12-25  ━━━┳━━━  snapshots 开始记录
                ┃
2025-12-26      ┃
  ...           ┃     snapshots 持续记录（26天）
2026-01-18      ┃
                ┃
2026-01-19  ━━━┻━━━  snapshots 最后记录

2026-01-24  ━━━━━━━  levels 当天实时数据（8小时）
            11:23:53 ~ 19:30:35
```

### 时间跨度统计
- **最早数据**: 2025-12-25 09:52:25（snapshots）
- **最新数据**: 2026-01-24 19:30:35（levels）
- **总时间跨度**: 约 31 天

### 数据分布
| 文件 | 起始日期 | 结束日期 | 天数 | 状态 |
|------|---------|---------|------|------|
| snapshots | 2025-12-25 | 2026-01-19 | 26天 | ✅ 历史数据 |
| levels | 2026-01-24 | 2026-01-24 | 1天 | ⚡ 实时数据 |

---

## 🎯 数据采集频率

### support_resistance_levels.jsonl
- **采集频率**: 实时（约 88,666 条/小时）
- **27个币种**: 每次采集所有币种
- **单币种频率**: 约 3,284 条/小时/币种
- **换算**: 约 0.91 条/秒/币种

### support_resistance_snapshots.jsonl
- **采集频率**: 约 48 条/小时
- **换算**: 约 1 条/75 秒
- **说明**: 定期快照，记录场景分布

---

## 📈 数据量统计

### 总数据量
```
总文件大小: 741.2 MB
总记录数: 804,067 条

详细分布:
├── levels:      697 MB    (709,327 条) - 86.7%
├── snapshots:    25 MB     (30,256 条) - 3.8%
├── ohlc:         15 MB     (50,000 条) - 2.0%
└── baseline:    4.2 MB     (14,684 条) - 0.6%
```

### 每日数据增长估算
- **levels**: 约 2.2 GB/天（按24小时计算）
- **snapshots**: 约 1 MB/天
- **合计**: 约 2.2 GB/天

---

## 🔍 数据质量与完整性

### ✅ 数据完整性
- ✅ levels 文件包含今天的完整实时数据
- ✅ snapshots 文件包含历史26天的场景数据
- ✅ 所有文件格式为标准 JSONL
- ✅ 数据结构完整，字段齐全

### ⚠️ 数据注意事项
1. **levels 数据仅保留当天**: 建议定期归档或迁移到长期存储
2. **snapshots 数据停在 1月19日**: 采集器可能在1月19日后停止
3. **数据量较大**: levels 文件 697MB，建议优化查询性能
4. **实时数据**: levels 文件持续增长，需要定期清理

---

## 🛠️ 数据使用建议

### 查询优化
```bash
# 查询最新100条 levels 数据
tail -100 support_resistance_levels.jsonl

# 查询特定币种（如 BTC）
grep '"symbol": "BTCUSDT"' support_resistance_levels.jsonl | tail -10

# 查询特定时间段
awk -F'"' '/record_time/ && $4 >= "2026-01-24 18:00:00"' support_resistance_levels.jsonl
```

### 数据归档建议
```bash
# 按日期归档 levels 数据
cat support_resistance_levels.jsonl | \
  awk -F'"' '{date=$4; sub(/ .*/, "", date); print > "levels_"date".jsonl"}'

# 压缩历史数据
gzip levels_2026-01-23.jsonl
```

---

## 📊 场景分布统计（基于 snapshots）

### 最新场景分布（2026-01-19）
```
场景1: 0 个币种
场景2: 0 个币种
场景3: 0 个币种
场景4: 0 个币种
```

### 历史场景分布（2025-12-25）
```
场景1: 1 个币种  (TRXUSDT)
场景2: 1 个币种  (TRXUSDT)
场景3: 8 个币种  (CRV, DOGE, DOT, FIL, LDO, LTC, NEAR, XLM)
场景4: 8 个币种  (CRV, DOGE, DOT, FIL, LDO, LTC, NEAR, XLM)
```

---

## 🔗 相关信息

### 系统访问
- **前端页面**: https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/support-resistance
- **数据目录**: /home/user/webapp/data/support_resistance_jsonl/

### GitHub 仓库
- **仓库**: https://github.com/jamesyidc/121211111
- **分支**: genspark_ai_developer
- **PR**: https://github.com/jamesyidc/121211111/pull/1

---

## 📝 总结

### 数据现状
✅ **levels 数据**: 今天（2026-01-24）的实时数据，709,327 条记录  
✅ **snapshots 数据**: 历史26天（2025-12-25 ~ 2026-01-19）的场景数据，30,256 条记录  
✅ **总数据量**: 741.2 MB，804,067 条记录

### 关键发现
1. **levels 数据仅保留当天**: 历史数据未保存，建议实施归档策略
2. **snapshots 采集停止**: 最新数据停在 1月19日，可能需要重启采集器
3. **数据量快速增长**: 按当前频率，每天约产生 2.2GB 数据
4. **27个币种全覆盖**: 每次采集包含所有主流币种

### 建议措施
1. **启用数据归档**: 按日期归档 levels 数据，保留历史
2. **检查 snapshots 采集器**: 确认是否正常运行
3. **优化存储策略**: 考虑压缩或迁移历史数据
4. **监控磁盘空间**: 定期清理或归档，避免磁盘爆满

---

**报告生成时间**: 2026-01-24 19:30 北京时间  
**数据统计截止**: 2026-01-24 19:30:35  
**报告版本**: v1.0
