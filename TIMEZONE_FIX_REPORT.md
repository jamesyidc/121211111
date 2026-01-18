# 时区问题修复报告

## 问题描述

用户反馈前端页面显示的时间不正确，显示为 `05:06:26` 而不是北京时间 `13:07`。

## 根本原因

数据导入脚本 `fill_escape_signal_stats.py` 错误地使用了 `support_resistance_snapshots` 表的 `created_at` 字段（UTC时间），而不是 `snapshot_time` 字段（北京时间）。

### 表结构对比

**support_resistance_snapshots表**:
- `created_at`: UTC时间 (例如: 2026-01-06 05:07:26)
- `snapshot_time`: 北京时间 (例如: 2026-01-06 13:07:26)

## 修复方案

### 1. 修改数据采集逻辑

将所有SQL查询从使用 `created_at` 改为使用 `snapshot_time`:

**修复前**:
```python
cursor.execute('''
    SELECT COUNT(*) 
    FROM support_resistance_snapshots
    WHERE created_at > ? AND created_at <= ?
    AND (scenario_3_count + scenario_4_count) >= 8
''', (time_24h_ago, target_time_str))
```

**修复后**:
```python
cursor.execute('''
    SELECT COUNT(*) 
    FROM support_resistance_snapshots
    WHERE snapshot_time > ? AND snapshot_time <= ?
    AND (scenario_3_count + scenario_4_count) >= 8
''', (time_24h_ago, target_time_str))
```

### 2. 数据清理和重新导入

由于历史数据使用了错误的时区，需要：

1. **删除所有旧数据**: 9,073条带有错误UTC时间的记录
2. **重新导入TXT数据**: 4,796条历史记录（北京时间）
3. **重新补全数据**: 694条从support_resistance_snapshots计算的记录

## 执行步骤

### 步骤1: 停止自动补全任务

```bash
pm2 stop escape-stats-filler
```

### 步骤2: 修改脚本

修改 `fill_escape_signal_stats.py` 中所有的 `created_at` → `snapshot_time`

### 步骤3: 清空数据

```python
cursor.execute("DELETE FROM escape_signal_stats")
conn.commit()
```

### 步骤4: 重新导入TXT数据

```bash
python3 import_escape_signal_txt.py
# 成功导入: 4,796 条
```

### 步骤5: 重新补全数据

```bash
python3 fill_escape_signal_stats.py
# 成功补全: 694 条
```

### 步骤6: 重启自动任务

```bash
pm2 restart escape-stats-filler
pm2 save
```

## 修复结果

### 数据统计

- **总记录数**: 5,493 条（持续增长中）
- **时间范围**: 2026-01-02 18:13:51 → 2026-01-06 13:11:26
- **时区**: ✅ 北京时间 (UTC+8)
- **更新延迟**: < 1 分钟
- **数据连续性**: 实时采集，每分钟更新

### 验证结果

#### 1. 时间正确性

**修复前**:
```
最新记录: 2026-01-06 05:07:26 (UTC时间，错误)
当前时间: 2026-01-06 13:07:00 (北京时间)
差值: 8小时（时区错误）
```

**修复后**:
```
最新记录: 2026-01-06 13:11:26 (北京时间，正确)
当前时间: 2026-01-06 13:11:48 (北京时间)
差值: < 1分钟（实时更新）
```

#### 2. API返回验证

```bash
curl "http://localhost:5000/api/escape-signal-stats"
```

**返回结果**:
```json
{
  "total_count": 5493,
  "history_data": [
    {
      "stat_time": "2026-01-06 13:11:26",
      "signal_24h_count": 100,
      "signal_2h_count": 0
    }
  ]
}
```

✅ 时间正确显示为北京时间

#### 3. 前端页面验证

- 图表X轴时间显示正确（13:07, 13:08, 13:09...）
- 表格记录时间显示正确
- 数据实时更新

### 最新10条记录（北京时间）

```
2026-01-06 13:11:26: 24h=100, 2h=0
2026-01-06 13:10:26: 24h=100, 2h=0
2026-01-06 13:09:26: 24h=100, 2h=0
2026-01-06 13:08:26: 24h=100, 2h=0
2026-01-06 13:07:26: 24h=100, 2h=0
2026-01-06 13:06:26: 24h=100, 2h=0
2026-01-06 13:05:26: 24h=100, 2h=0
2026-01-06 13:04:26: 24h=100, 2h=0
2026-01-06 13:03:25: 24h=100, 2h=0
2026-01-06 13:02:25: 24h=100, 2h=0
```

## Git提交记录

### Commit: ce4871d

**标题**: fix: Use Beijing time (snapshot_time) instead of UTC time (created_at)

**变更**:
- 修改 `fill_escape_signal_stats.py`: 所有查询改用 `snapshot_time`
- 删除9,073条错误数据
- 重新导入4,796条TXT数据
- 重新补全694条计算数据
- 8 files changed, 1,604 insertions(+), 19 deletions(-)

## 技术细节

### 时间字段对比

| 表名 | 字段名 | 时区 | 用途 |
|------|--------|------|------|
| support_resistance_snapshots | created_at | UTC | 记录创建时间（系统时间） |
| support_resistance_snapshots | snapshot_time | Beijing | 快照业务时间（用于查询） |
| escape_signal_stats | stat_time | Beijing | 统计时间点 |
| escape_signal_stats | created_at | Beijing | 记录创建时间 |

### 修复的SQL查询

共修复了6处SQL查询：

1. 24小时信号数查询
2. 2小时信号数查询
3. 24小时最大值查询
4. 2小时最大值查询
5. 获取新快照查询
6. 获取最早快照时间查询

## 影响范围

### 受影响的组件

✅ **已修复**:
- `fill_escape_signal_stats.py` - 数据补全脚本
- `escape_signal_stats` 表 - 所有记录时间已更正
- `/api/escape-signal-stats` - API返回正确时间
- 前端图表 - 时间轴显示正确
- 前端表格 - 记录时间显示正确

### 不受影响的组件

- `import_escape_signal_txt.py` - TXT导入脚本（原本就正确）
- `support_resistance_snapshots` 表 - 源数据保持不变
- 其他系统功能 - 无影响

## 预防措施

### 代码规范

为避免类似问题，建议：

1. **统一时区标准**: 所有业务时间统一使用北京时间
2. **字段命名规范**: 
   - `*_time`: 业务时间（北京时间）
   - `created_at`: 记录创建时间（可以是UTC或北京时间，需明确注释）
3. **时区注释**: 在SQL查询和时间处理代码中添加时区注释

### 测试建议

1. **时区验证**: 在数据导入后立即验证时间是否正确
2. **对比当前时间**: 最新记录时间应与当前北京时间接近（< 2分钟）
3. **前端显示检查**: 确认前端页面显示的时间与预期一致

## 总结

### 问题

- 前端显示时间为UTC时间（05:07）而不是北京时间（13:07）
- 相差8小时，导致用户误解数据时效性

### 解决方案

- 修改数据采集脚本使用正确的时间字段（snapshot_time）
- 清理并重新导入所有历史数据
- 验证修复后数据的正确性

### 结果

✅ **修复成功**:
- 所有时间现在正确显示为北京时间
- 数据实时更新（延迟<1分钟）
- 前端页面时间显示正确
- API返回时间正确

### 影响

- 用户现在可以看到正确的北京时间
- 数据时效性一目了然
- 系统可信度提升

---

**报告时间**: 2026-01-06 13:12 (北京时间)
**修复人员**: Claude Code Assistant
**状态**: ✅ 已完成并验证
