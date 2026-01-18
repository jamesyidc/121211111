# ✅ Coin Price Tracker 数据格式确认

## 📋 数据存储格式

**当前格式**: ✅ **JSONL (JSON Lines)**

**存储路径**: `/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl`

---

## 🔍 系统架构确认

### 1. 数据采集 (coin_price_tracker.py)

**采集方式**:
```python
def save_to_jsonl(self, record):
    """保存数据到JSONL文件"""
    with open(JSONL_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
```

**特点**:
- ✅ 追加写入（append mode）
- ✅ UTF-8编码
- ✅ 每行一个JSON对象
- ✅ 不使用数据库

### 2. 数据读取 (app_new.py API)

**读取方式**:
```python
def api_coin_price_tracker_history():
    """从JSONL文件读取数据"""
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                records.append(record)
```

**特点**:
- ✅ 逐行读取
- ✅ JSON解析
- ✅ 支持时间范围过滤
- ✅ 不使用数据库

---

## 📁 数据文件现状

```bash
/home/user/webapp/data/coin_price_tracker/
├── coin_prices_30min.jsonl              # 主数据文件 (1.8M, 716条记录)
├── coin_prices_30min.jsonl.backup       # 备份文件
├── coin_prices_30min.jsonl.backup_base_price  # 基准价格修复前备份
├── coin_prices_30min.jsonl.backup_format      # 格式修复前备份
├── coin_prices_3min.jsonl               # 3分钟测试数据（旧）
├── failed_records.json                  # 失败任务队列
└── exports/                             # CSV导出目录
```

---

## 📊 数据格式示例

### JSONL格式 (当前使用)

每行一个独立的JSON对象：

```json
{"collect_time":"2026-01-17 21:44:45","timestamp":1768648485,"base_date":"2026-01-17","day_changes":{"BTC":{"base_price":94639.9,"current_price":95299.2,"change_pct":0.6967},"ETH":{"base_price":3268.06,"current_price":3301.35,"change_pct":1.0186},...},"total_change":83.0347,"average_change":3.0754,"total_coins":27,"valid_coins":27,"success_count":27,"failed_count":0}
{"collect_time":"2026-01-17 22:00:00","timestamp":1768649400,"base_date":"2026-01-17",...}
```

**优点**:
- ✅ 追加写入效率高
- ✅ 文件损坏影响小（只影响单行）
- ✅ 易于备份和恢复
- ✅ 支持流式处理
- ✅ 不需要数据库维护
- ✅ 易于版本控制
- ✅ 易于数据迁移

---

## 🔧 相关脚本

### 1. 采集脚本
```
/home/user/webapp/source_code/coin_price_tracker.py
```
- 每30分钟采集一次
- 直接写入JSONL文件
- 失败任务保存到队列

### 2. API服务
```
/home/user/webapp/source_code/app_new.py
```
- 路由: `/api/coin-price-tracker/history`
- 直接读取JSONL文件
- 支持时间范围过滤

### 3. 数据修复脚本
```
/home/user/webapp/fix_data_format.py         # 格式修复
/home/user/webapp/fix_base_prices.py          # 基准价格修复
/home/user/webapp/align_data_sources.py       # 数据对齐
```
- 都是读取JSONL → 处理 → 写回JSONL
- 修复前自动备份

---

## 🚫 不使用的格式

### ❌ 不使用数据库
- ❌ SQLite
- ❌ MySQL
- ❌ PostgreSQL
- ❌ MongoDB

### ❌ 不使用单文件JSON
```json
// 这种格式不使用
{
  "data": [
    {...},
    {...}
  ]
}
```

原因：
- 追加写入需要重写整个文件
- 文件损坏会丢失所有数据
- 处理大文件效率低

---

## 📈 数据增长预估

### 当前状态
- 文件大小: 1.8 MB
- 记录数: 716条
- 时间范围: 2026-01-03 ~ 2026-01-17 (15天)
- 每条记录: ~2.5 KB

### 增长预测
- 每天数据: 48条 (30分钟间隔)
- 每天增长: ~120 KB
- 每月增长: ~3.6 MB
- 每年增长: ~43 MB

**结论**: JSONL格式完全满足需求，无需数据库

---

## ✅ 数据完整性保证

### 1. 备份机制
```python
# 修复脚本中的自动备份
backup_file = f"{jsonl_file}.backup_{timestamp}"
shutil.copy2(jsonl_file, backup_file)
```

### 2. 追加写入
- 使用 `'a'` 模式打开文件
- 每次写入独立的一行
- 不会覆盖现有数据

### 3. 失败重试
- 采集失败的任务保存到队列
- 下次优先重试
- 确保数据不丢失

### 4. 数据验证
```python
# API读取时跳过空行
for line in f:
    if line.strip():
        record = json.loads(line)
```

---

## 🎯 最佳实践

### 1. 定期备份
```bash
# 推荐每天备份一次
cp coin_prices_30min.jsonl coin_prices_30min.jsonl.backup_$(date +%Y%m%d)
```

### 2. 数据清理
```bash
# 如果文件过大，可以归档旧数据
# 保留最近3个月的数据，旧数据移到归档目录
```

### 3. 监控文件大小
```bash
# 定期检查
ls -lh coin_prices_30min.jsonl
```

---

## 📝 总结

✅ **Coin Price Tracker 使用 JSONL 格式存储数据**

**理由**:
1. ✅ 简单高效 - 追加写入，无需数据库维护
2. ✅ 安全可靠 - 文件损坏只影响单行，易于恢复
3. ✅ 易于处理 - Python原生支持，易于读写
4. ✅ 灵活性高 - 易于备份、迁移、版本控制
5. ✅ 性能足够 - 当前数据量下性能完全满足需求

**不会改为**:
- ❌ 数据库（SQLite/MySQL/PostgreSQL）
- ❌ 单文件JSON
- ❌ CSV格式（会丢失嵌套结构）
- ❌ 其他格式

---

**确认时间**: 2026-01-17 22:10:00
**数据格式**: JSONL (JSON Lines)
**存储路径**: /home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl
**状态**: ✅ 已确认，保持不变
