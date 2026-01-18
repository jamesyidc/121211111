# 沙箱资源使用情况报告

生成时间：2026-01-15 14:23 UTC (22:23 北京时间)

---

## 📊 总体资源使用情况

### 磁盘使用
```
总容量：26GB
已使用：8.1GB (32%)
可用：  18GB (68%)
```

✅ **磁盘使用健康**：只使用了32%，还有充足空间

### 内存使用
```
总内存：  7.8GB
已使用：  1.1GB (14%)
可用：    5.1GB
缓存：    1.8GB
可用总计：6.7GB (86%)
```

✅ **内存使用健康**：只使用了14%，内存充足

---

## 📁 磁盘空间占用详细分析

### 1. 顶级目录占用（/home/user/）

| 目录 | 大小 | 占比 | 说明 |
|------|------|------|------|
| webapp | 1.2GB | 92% | 主要项目目录 |
| tmp | 128MB | 10% | 临时文件 |
| uploaded_files | 480KB | <1% | 上传文件 |
| 其他 | <1MB | <1% | 文档和脚本 |

**总计**：约1.3GB

---

### 2. webapp 目录占用详细（1.2GB）

| 目录/文件 | 大小 | 占比 | 说明 |
|-----------|------|------|------|
| **data/** | **823MB** | **69%** | **数据文件目录（最大）** |
| **databases/** | **305MB** | **25%** | **SQLite数据库** |
| source_code/ | 34MB | 3% | 源代码 |
| .git/ | 11MB | 1% | Git仓库 |
| logs/ | 8.5MB | <1% | 日志文件 |
| 日志文件 | 2.7MB | <1% | 各种.log文件 |
| 截图 | 1.1MB | <1% | PNG图片 |
| 其他 | 约1MB | <1% | 配置、文档等 |

---

### 3. data/ 目录占用详细（823MB）

| 子目录 | 大小 | 占比 | 说明 |
|--------|------|------|------|
| **support_resistance_jsonl** | **650MB** | **79%** | **支撑压力线数据（最大！）** |
| gdrive_jsonl | 76MB | 9% | Google Drive检测数据 |
| query_jsonl | 29MB | 4% | 查询数据 |
| anchor_jsonl | 26MB | 3% | 锚点系统数据 |
| sar_jsonl_backup_old_params | 15MB | 2% | 备份数据 |
| sar_jsonl | 13MB | 2% | SAR数据 |
| escape_signal_jsonl | 7.9MB | 1% | 逃顶信号数据 |
| anchor_profit_stats | 3.4MB | <1% | 盈利统计 |
| extreme_jsonl | 3.1MB | <1% | 极值数据 |
| **panic_jsonl** | **1.4MB** | **<1%** | **恐慌清洗指数数据** |
| 其他 | <1MB | <1% | 其他小文件 |

**⚠️ 最大占用者**：`support_resistance_jsonl` 占用 **650MB**（79%）

---

### 4. databases/ 目录占用详细（305MB）

| 数据库文件 | 大小 | 占比 | 说明 |
|-----------|------|------|------|
| **support_resistance.db** | **223MB** | **73%** | **支撑压力线数据库（最大！）** |
| fund_monitor.db | 42MB | 14% | 资金监控数据库 |
| anchor_system.db | 13MB | 4% | 锚点系统数据库 |
| v1v2_data.db | 12MB | 4% | V1V2数据 |
| crypto_data.db | 9.1MB | 3% | 加密货币数据 |
| trading_decision.db | 4.3MB | 1% | 交易决策数据 |
| support_resistance.db-wal | 4.0MB | 1% | WAL日志 |
| 其他 | <1MB | <1% | 小数据库 |

**⚠️ 最大占用者**：`support_resistance.db` 占用 **223MB**（73%）

---

## 💾 进程内存占用排名（PM2管理）

| 排名 | 进程名 | 内存 | CPU | 说明 |
|------|--------|------|-----|------|
| 1 | **flask-app** | **188MB** | 10.7% | **Flask Web服务器（最大）** |
| 2 | gdrive-detector | 104MB | 0% | Google Drive检测器 |
| 3 | sar-jsonl-collector | 42MB | 0% | SAR数据采集器 |
| 4 | escape-signals-2h-monitor | 40MB | 3.2% | 逃顶信号监控 |
| 5 | support-resistance-collector | 31MB | 3.6% | 支撑压力线采集器 |
| 6 | anchor-profit-monitor | 30MB | 0% | 锚点盈利监控 |
| 7 | **panic-collector** | **29MB** | 0% | **恐慌清洗指数采集器** |
| 8 | extreme-monitor | 28MB | 0% | 极值监控 |
| 9 | sar-bias-collector | 21MB | 0% | SAR偏差采集器 |
| 10 | support-resistance-snapshot | 14MB | 0% | 支撑压力线快照 |
| 11 | anchor-monitor-daemon | 13MB | 0% | 锚点监控守护进程 |
| 12 | escape-stats-filler | 1MB | 0% | 逃顶统计填充 |

**总计PM2进程内存**：约 **570MB**

---

## 🎯 资源使用总结

### ✅ 健康指标

1. **磁盘使用**：32% - 健康，还有68%可用空间
2. **内存使用**：14% - 健康，还有86%可用内存
3. **系统负载**：低负载，CPU使用率正常

### ⚠️ 资源占用TOP 3

#### 磁盘占用

1. **support_resistance_jsonl** - 650MB（数据文件）
   - 支撑压力线JSONL数据
   - 建议：定期清理历史数据

2. **support_resistance.db** - 223MB（数据库）
   - 支撑压力线SQLite数据库
   - 建议：定期vacuum优化

3. **flask-app** - 188MB（进程内存）
   - Flask Web服务器
   - 正常：Web服务需要较多内存

#### 内存占用

1. **flask-app** - 188MB（33%）
2. **gdrive-detector** - 104MB（18%）
3. **sar-jsonl-collector** - 42MB（7%）

---

## 📈 增长趋势预测

### panic_jsonl 增长预测

当前大小：**1.4MB**

**每条数据大小**：约 300-400 bytes
**采集频率**：3分钟/次
**每日数据量**：480条
**每日增长**：约 200KB

**预计**：
- 1个月后：约 6MB
- 6个月后：约 36MB
- 1年后：约 72MB

✅ **完全可控**，不会造成空间压力

---

## 🛠️ 优化建议

### 短期（可选）

1. **清理日志文件**
   ```bash
   # 清理旧日志（可节省约10MB）
   > fill_escape_signal_stats.log
   > gdrive_final_detector.log
   > gdrive_detector_jsonl.log
   ```

2. **清理截图文件**
   ```bash
   # 删除旧截图（可节省约1MB）
   rm -f *.png
   ```

3. **Git仓库清理**
   ```bash
   # 清理Git历史（可节省约5MB）
   git gc --aggressive
   ```

### 中期（建议）

1. **support_resistance数据优化**
   - 当前占用：650MB + 223MB = 873MB（总空间的72%）
   - 建议：定期清理6个月前的历史数据
   - 预计可节省：约400-500MB

2. **数据库优化**
   ```bash
   # 优化SQLite数据库
   sqlite3 databases/support_resistance.db "VACUUM;"
   sqlite3 databases/fund_monitor.db "VACUUM;"
   ```

### 长期（监控）

1. **设置数据保留策略**
   - JSONL数据：保留6个月
   - 数据库数据：保留1年
   - 日志文件：保留1个月

2. **定期备份到外部存储**
   - 每周备份到AI Drive或其他位置
   - 本地只保留最近数据

---

## 📊 当前状态评估

### 总体评分：✅ **优秀（A级）**

- 磁盘使用：✅ 健康（32%）
- 内存使用：✅ 健康（14%）
- 进程状态：✅ 稳定（12个进程运行正常）
- 数据增长：✅ 可控（恐慌指数每天增长200KB）

### 结论

**当前沙箱资源使用非常健康，无需立即优化。**

主要资源占用来自：
1. **支撑压力线系统**（873MB，72%）- 这是最大的数据源
2. **Flask Web服务器**（188MB内存）- 正常的Web服务开销
3. **各种数据采集器**（合计约400MB内存）- 正常运行所需

**恐慌清洗指数系统占用极小**：
- 磁盘：1.4MB（0.1%）
- 内存：29MB（5%）
- 完全不会造成资源压力 ✅

---

生成时间：2026-01-15 14:23 UTC  
报告版本：v1.0  
