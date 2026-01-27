# 按日期存储和调用数据 - 完整实施指南

**文档版本**: v1.0  
**更新时间**: 2026-01-27  
**适用系统**: 支撑压力线系统

---

## 📋 目录

1. [概述](#概述)
2. [当前状态](#当前状态)
3. [目标架构](#目标架构)
4. [实施方案](#实施方案)
5. [代码示例](#代码示例)
6. [迁移策略](#迁移策略)
7. [测试验证](#测试验证)
8. [性能优化](#性能优化)

---

## 概述

### 什么是"按日期存储和调用"？

将数据按照日期维度进行组织和存储，每天的数据保存在独立的文件中，便于：
- 快速查询特定日期的数据
- 历史数据归档和清理
- 并行读写提高性能
- 数据备份和恢复

### 为什么需要按日期存储？

#### 当前问题
```
单文件JSONL模式:
support_resistance_levels.jsonl (697MB)
├─ 问题1: 文件过大，读取慢
├─ 问题2: 无法快速定位特定日期
├─ 问题3: 清理旧数据困难
└─ 问题4: 并发写入有风险
```

#### 按日期存储优势
```
按日期目录模式:
support_resistance_daily/
├─ 2026-01-23/
│  ├─ levels.jsonl (每天25MB左右)
│  └─ snapshots.jsonl
├─ 2026-01-24/
│  ├─ levels.jsonl
│  └─ snapshots.jsonl
└─ 2026-01-27/
   ├─ levels.jsonl
   └─ snapshots.jsonl

优势:
✅ 文件小，读写快
✅ 快速定位日期
✅ 自动清理旧数据 (删除整个日期目录)
✅ 支持并发写入不同日期
✅ 便于数据分析和统计
```

---

## 当前状态

### 现有文件结构
```
/home/user/webapp/data/
├── support_resistance_jsonl/           # 旧格式（当前使用）
│   ├── support_resistance_levels.jsonl      697MB
│   ├── support_resistance_snapshots.jsonl    25MB
│   ├── daily_baseline_prices.jsonl         4.2MB
│   └── okex_kline_ohlc.jsonl                15MB
│
└── support_resistance_daily/           # 新格式（待实施）
    └── (空目录)
```

### 现有管理器代码

#### 文件位置
```
source_code/support_resistance_daily_manager.py
```

#### 主要类
```python
class SupportResistanceDailyManager:
    """按日期管理支撑阻力数据"""
    
    def __init__(self):
        self.base_dir = '/home/user/webapp/data/support_resistance_daily'
    
    def get_latest_levels(self, symbols=None):
        """获取最新数据（今日）"""
        pass
    
    def get_levels_by_date(self, date_str, symbols=None):
        """获取指定日期数据"""
        pass
    
    def save_levels(self, data_list, date_str=None):
        """保存数据到指定日期"""
        pass
```

---

## 目标架构

### 目录结构设计
```
data/support_resistance_daily/
│
├── 2026-01-23/
│   ├── levels.jsonl              # 当天所有币种的支撑阻力数据
│   ├── snapshots.jsonl           # 当天的快照数据
│   └── metadata.json             # 元数据（记录数量、时间范围等）
│
├── 2026-01-24/
│   ├── levels.jsonl
│   ├── snapshots.jsonl
│   └── metadata.json
│
├── 2026-01-25/
│   ├── levels.jsonl
│   ├── snapshots.jsonl
│   └── metadata.json
│
└── index.json                    # 总索引文件（可选，加速查询）
    └── {
          "dates": ["2026-01-23", "2026-01-24", "2026-01-25"],
          "summary": {
            "2026-01-23": {"records": 1500, "coins": 27},
            "2026-01-24": {"records": 1520, "coins": 27}
          }
        }
```

### 数据格式

#### levels.jsonl 格式
```json
{"symbol": "BTCUSDT", "current_price": 89304.9, "support_line_1": 87200.1, "support_line_2": 88633.0, "resistance_line_1": 95495.0, "resistance_line_2": 90042.9, "position_7d": 25.37, "position_48h": 47.66, "record_time": "2026-01-23 22:00:01", "record_time_beijing": "2026-01-23 22:00:01"}
{"symbol": "ETHUSDT", "current_price": 2928.83, ...}
...
```

#### snapshots.jsonl 格式
```json
{"snapshot_time": "2026-01-23 23:00:00", "snapshot_date": "2026-01-23", "total_coins": 27, "scenario_1_count": 2, "scenario_2_count": 3, ...}
{"snapshot_time": "2026-01-23 23:05:00", ...}
```

#### metadata.json 格式
```json
{
  "date": "2026-01-23",
  "created_at": "2026-01-23 00:00:00",
  "updated_at": "2026-01-23 23:59:59",
  "statistics": {
    "levels": {
      "total_records": 1500,
      "unique_coins": 27,
      "time_range": {
        "start": "2026-01-23 00:00:00",
        "end": "2026-01-23 23:59:59"
      }
    },
    "snapshots": {
      "total_snapshots": 288,
      "interval": "5分钟"
    }
  },
  "file_sizes": {
    "levels.jsonl": 25165824,
    "snapshots.jsonl": 524288
  }
}
```

---

## 实施方案

### 方案A: 完整迁移（推荐用于新系统）

#### 步骤
1. 停止数据采集器
2. 运行迁移脚本（分批处理）
3. 验证数据完整性
4. 切换API到新数据源
5. 恢复数据采集器（写入新格式）

#### 优点
- 数据结构清晰
- 完全使用新格式
- 性能最优

#### 缺点
- 需要停机时间
- 迁移过程较长（697MB数据）

### 方案B: 渐进式迁移（推荐用于生产系统）⭐

#### 步骤
1. **保持采集器运行**（继续写入旧格式）
2. **后台迁移**（夜间分批迁移历史数据）
3. **双写模式**（新数据同时写入新旧两个格式）
4. **逐步切换**（API优先读新格式，fallback到旧格式）
5. **验证完成**（确认新格式完整后停止旧格式）

#### 优点
- ✅ 零停机时间
- ✅ 风险可控
- ✅ 可以随时回滚

#### 缺点
- 实施周期较长
- 短期内需要双倍存储

### 方案C: 仅新数据按日期存储（最简单）⭐⭐

#### 步骤
1. 修改数据采集器，从今天开始写入按日期目录
2. 历史数据保持原格式（JSONL）
3. API查询时：
   - 今天的数据 → 从按日期目录读取
   - 历史数据 → 从JSONL文件读取

#### 优点
- ✅ 最简单，风险最低
- ✅ 立即生效
- ✅ 无需迁移历史数据

#### 缺点
- 历史数据仍是单文件格式

---

## 代码示例

### 1. 数据管理器实现

#### 完整代码
```python
#!/usr/bin/env python3
"""
支撑阻力线数据按日期管理器
按日期组织数据，每天一个目录
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import pytz

class SupportResistanceDailyManager:
    """按日期管理支撑阻力数据"""
    
    def __init__(self, base_dir='/home/user/webapp/data/support_resistance_daily'):
        """
        初始化
        Args:
            base_dir: 数据根目录
        """
        self.base_dir = base_dir
        self.timezone = pytz.timezone('Asia/Shanghai')
        os.makedirs(base_dir, exist_ok=True)
    
    def _get_date_dir(self, date_str=None):
        """
        获取指定日期的目录路径
        Args:
            date_str: 日期字符串 '2026-01-23'，None表示今天
        Returns:
            日期目录的完整路径
        """
        if date_str is None:
            now = datetime.now(self.timezone)
            date_str = now.strftime('%Y-%m-%d')
        
        date_dir = os.path.join(self.base_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)
        return date_dir
    
    def _get_levels_file(self, date_str=None):
        """获取levels文件路径"""
        date_dir = self._get_date_dir(date_str)
        return os.path.join(date_dir, 'levels.jsonl')
    
    def _get_snapshots_file(self, date_str=None):
        """获取snapshots文件路径"""
        date_dir = self._get_date_dir(date_str)
        return os.path.join(date_dir, 'snapshots.jsonl')
    
    def _get_metadata_file(self, date_str=None):
        """获取metadata文件路径"""
        date_dir = self._get_date_dir(date_str)
        return os.path.join(date_dir, 'metadata.json')
    
    # ===== 写入数据 =====
    
    def save_levels(self, data_list, date_str=None):
        """
        保存支撑阻力数据
        Args:
            data_list: 数据列表，每项是一个字典
            date_str: 日期字符串，None表示今天
        """
        levels_file = self._get_levels_file(date_str)
        
        with open(levels_file, 'a', encoding='utf-8') as f:
            for data in data_list:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        # 更新元数据
        self._update_metadata(date_str)
    
    def save_level(self, data, date_str=None):
        """保存单条数据"""
        self.save_levels([data], date_str)
    
    def save_snapshot(self, snapshot_data, date_str=None):
        """
        保存快照数据
        Args:
            snapshot_data: 快照数据字典
            date_str: 日期字符串，None表示今天
        """
        snapshots_file = self._get_snapshots_file(date_str)
        
        with open(snapshots_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(snapshot_data, ensure_ascii=False) + '\n')
        
        # 更新元数据
        self._update_metadata(date_str)
    
    # ===== 读取数据 =====
    
    def get_latest_levels(self, symbols=None):
        """
        获取最新数据（今日）
        Args:
            symbols: 币种列表，None表示全部
        Returns:
            数据列表
        """
        return self.get_levels_by_date(None, symbols)
    
    def get_levels_by_date(self, date_str, symbols=None):
        """
        获取指定日期的数据
        Args:
            date_str: 日期字符串 '2026-01-23'，None表示今天
            symbols: 币种列表，None表示全部
        Returns:
            数据列表
        """
        levels_file = self._get_levels_file(date_str)
        
        if not os.path.exists(levels_file):
            return []
        
        # 读取文件，获取每个币种的最新记录
        latest_by_symbol = {}
        
        with open(levels_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    symbol = data.get('symbol', '')
                    
                    # 如果指定了币种，跳过不在列表中的
                    if symbols and symbol not in symbols:
                        continue
                    
                    # 保留最新记录
                    record_time = data.get('record_time', '')
                    if symbol not in latest_by_symbol or \
                       record_time > latest_by_symbol[symbol].get('record_time', ''):
                        latest_by_symbol[symbol] = data
                except:
                    continue
        
        return list(latest_by_symbol.values())
    
    def get_snapshots_by_date(self, date_str=None, limit=None):
        """
        获取指定日期的快照
        Args:
            date_str: 日期字符串，None表示今天
            limit: 限制返回数量，None表示全部
        Returns:
            快照列表
        """
        snapshots_file = self._get_snapshots_file(date_str)
        
        if not os.path.exists(snapshots_file):
            return []
        
        snapshots = []
        with open(snapshots_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    snapshot = json.loads(line.strip())
                    snapshots.append(snapshot)
                except:
                    continue
        
        # 如果有限制，返回最新N条
        if limit:
            snapshots = snapshots[-limit:]
        
        return snapshots
    
    def get_latest_snapshot(self, date_str=None):
        """获取最新快照"""
        snapshots = self.get_snapshots_by_date(date_str, limit=1)
        return snapshots[0] if snapshots else None
    
    # ===== 历史数据查询 =====
    
    def get_date_range(self, start_date, end_date, symbols=None):
        """
        获取日期范围内的数据
        Args:
            start_date: 开始日期 '2026-01-20'
            end_date: 结束日期 '2026-01-25'
            symbols: 币种列表
        Returns:
            {日期: [数据列表]}
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        result = {}
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            data = self.get_levels_by_date(date_str, symbols)
            if data:
                result[date_str] = data
            current += timedelta(days=1)
        
        return result
    
    # ===== 元数据管理 =====
    
    def _update_metadata(self, date_str=None):
        """更新元数据"""
        metadata_file = self._get_metadata_file(date_str)
        levels_file = self._get_levels_file(date_str)
        snapshots_file = self._get_snapshots_file(date_str)
        
        if date_str is None:
            now = datetime.now(self.timezone)
            date_str = now.strftime('%Y-%m-%d')
        
        # 统计数据
        levels_count = 0
        if os.path.exists(levels_file):
            with open(levels_file, 'r') as f:
                levels_count = sum(1 for _ in f)
        
        snapshots_count = 0
        if os.path.exists(snapshots_file):
            with open(snapshots_file, 'r') as f:
                snapshots_count = sum(1 for _ in f)
        
        # 生成元数据
        metadata = {
            'date': date_str,
            'updated_at': datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S'),
            'statistics': {
                'levels': {
                    'total_records': levels_count
                },
                'snapshots': {
                    'total_snapshots': snapshots_count
                }
            },
            'file_sizes': {
                'levels.jsonl': os.path.getsize(levels_file) if os.path.exists(levels_file) else 0,
                'snapshots.jsonl': os.path.getsize(snapshots_file) if os.path.exists(snapshots_file) else 0
            }
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def get_metadata(self, date_str=None):
        """获取元数据"""
        metadata_file = self._get_metadata_file(date_str)
        
        if not os.path.exists(metadata_file):
            return None
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # ===== 维护操作 =====
    
    def list_dates(self):
        """列出所有可用的日期"""
        if not os.path.exists(self.base_dir):
            return []
        
        dates = []
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            if os.path.isdir(item_path) and len(item) == 10:  # YYYY-MM-DD
                dates.append(item)
        
        return sorted(dates)
    
    def cleanup_old_data(self, keep_days=30):
        """
        清理旧数据
        Args:
            keep_days: 保留最近N天的数据
        """
        cutoff_date = datetime.now(self.timezone) - timedelta(days=keep_days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        removed = []
        for date_str in self.list_dates():
            if date_str < cutoff_str:
                date_dir = self._get_date_dir(date_str)
                import shutil
                shutil.rmtree(date_dir)
                removed.append(date_str)
        
        return removed


# 使用示例
if __name__ == '__main__':
    manager = SupportResistanceDailyManager()
    
    # 保存数据
    data = {
        'symbol': 'BTCUSDT',
        'current_price': 89304.9,
        'support_line_1': 87200.1,
        'support_line_2': 88633.0,
        'resistance_line_1': 95495.0,
        'resistance_line_2': 90042.9,
        'position_7d': 25.37,
        'position_48h': 47.66,
        'record_time': '2026-01-23 22:00:01',
        'record_time_beijing': '2026-01-23 22:00:01'
    }
    manager.save_level(data)
    
    # 读取最新数据
    latest = manager.get_latest_levels()
    print(f"找到 {len(latest)} 条最新数据")
    
    # 列出所有日期
    dates = manager.list_dates()
    print(f"可用日期: {dates}")
```

### 2. 采集器修改示例

#### 原采集器（写入单文件）
```python
# support_resistance_collector.py (旧版本)

def save_data(data):
    """保存数据到单文件"""
    with open('/home/user/webapp/data/support_resistance_jsonl/support_resistance_levels.jsonl', 'a') as f:
        f.write(json.dumps(data) + '\n')
```

#### 新采集器（按日期写入）
```python
# support_resistance_collector.py (新版本)

from support_resistance_daily_manager import SupportResistanceDailyManager

manager = SupportResistanceDailyManager()

def save_data(data):
    """保存数据到按日期目录"""
    manager.save_level(data)  # 自动写入今天的目录
```

### 3. API端点修改

#### 原API（读取单文件）
```python
@app.route('/api/support-resistance/latest')
def api_support_resistance_latest_old():
    """旧版：从单文件读取"""
    latest_by_symbol = {}
    
    with open('/home/user/webapp/data/support_resistance_jsonl/support_resistance_levels.jsonl', 'r') as f:
        # 读取最后1MB
        f.seek(0, 2)
        file_size = f.tell()
        read_size = min(1024 * 1024, file_size)
        f.seek(max(0, file_size - read_size))
        
        for line in f:
            data = json.loads(line)
            symbol = data['symbol']
            latest_by_symbol[symbol] = data
    
    return jsonify({'data': list(latest_by_symbol.values())})
```

#### 新API（按日期读取+fallback）
```python
@app.route('/api/support-resistance/latest')
def api_support_resistance_latest():
    """新版：从按日期目录读取，fallback到单文件"""
    try:
        from support_resistance_daily_manager import SupportResistanceDailyManager
        
        manager = SupportResistanceDailyManager()
        
        # 尝试从按日期目录读取
        latest_levels = manager.get_latest_levels()
        
        # 如果没有数据，fallback到单文件
        if not latest_levels:
            print("⚠️ 按日期数据为空，fallback到JSONL文件")
            return api_support_resistance_latest_from_jsonl()
        
        # 格式化数据
        coins_data = []
        for level in latest_levels:
            coins_data.append({
                'symbol': level['symbol'],
                'current_price': level['current_price'],
                'support_line_1': level['support_line_1'],
                # ... 其他字段
            })
        
        return jsonify({
            'success': True,
            'data': coins_data,
            'data_source': 'Daily Directory'
        })
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        # 异常时也fallback
        return api_support_resistance_latest_from_jsonl()
```

---

## 迁移策略

### 推荐：渐进式迁移方案

#### 第1阶段：准备（1天）
```bash
# 1. 创建按日期目录结构
mkdir -p /home/user/webapp/data/support_resistance_daily

# 2. 部署新的管理器代码
cp support_resistance_daily_manager.py /home/user/webapp/source_code/

# 3. 测试管理器功能
python3 test_daily_manager.py
```

#### 第2阶段：双写模式（1周）
```python
# 修改采集器，同时写入新旧两个位置
def save_data(data):
    # 写入旧格式（保底）
    with open(old_file, 'a') as f:
        f.write(json.dumps(data) + '\n')
    
    # 写入新格式
    manager.save_level(data)
```

#### 第3阶段：API切换（2天）
```python
# API优先使用新格式，fallback到旧格式
def get_data():
    # 尝试新格式
    data = manager.get_latest_levels()
    if data:
        return data
    
    # fallback到旧格式
    return read_from_old_jsonl()
```

#### 第4阶段：历史数据迁移（可选，分批进行）
```bash
# 按月份分批迁移
python3 migrate_support_resistance_to_daily.py --start-date 2026-01-01 --end-date 2026-01-31
python3 migrate_support_resistance_to_daily.py --start-date 2025-12-01 --end-date 2025-12-31
```

#### 第5阶段：验证和清理（1天）
```bash
# 验证数据完整性
python3 verify_migration.py

# 确认后停止双写，只写入新格式
# 保留旧文件作为备份
mv support_resistance_levels.jsonl support_resistance_levels.jsonl.backup
```

---

## 测试验证

### 测试脚本
```python
#!/usr/bin/env python3
"""测试按日期存储功能"""

from support_resistance_daily_manager import SupportResistanceDailyManager
import json

def test_save_and_read():
    """测试保存和读取"""
    manager = SupportResistanceDailyManager()
    
    # 测试数据
    test_data = {
        'symbol': 'TESTCOIN',
        'current_price': 100.0,
        'support_line_1': 95.0,
        'support_line_2': 97.0,
        'resistance_line_1': 105.0,
        'resistance_line_2': 103.0,
        'record_time': '2026-01-27 15:00:00'
    }
    
    # 保存
    print("📝 保存测试数据...")
    manager.save_level(test_data)
    
    # 读取
    print("📖 读取最新数据...")
    latest = manager.get_latest_levels(['TESTCOIN'])
    
    if latest:
        print(f"✅ 成功读取: {latest[0]['symbol']}")
        assert latest[0]['symbol'] == 'TESTCOIN'
        assert latest[0]['current_price'] == 100.0
        print("✅ 数据验证通过")
    else:
        print("❌ 读取失败")
        return False
    
    return True

def test_date_query():
    """测试日期查询"""
    manager = SupportResistanceDailyManager()
    
    # 获取今天的数据
    today_data = manager.get_latest_levels()
    print(f"📅 今天的数据: {len(today_data)} 条")
    
    # 列出所有日期
    dates = manager.list_dates()
    print(f"📅 可用日期: {dates}")
    
    return True

def test_metadata():
    """测试元数据"""
    manager = SupportResistanceDailyManager()
    
    metadata = manager.get_metadata()
    if metadata:
        print("📊 元数据:")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    return True

if __name__ == '__main__':
    print("🧪 开始测试...\n")
    
    tests = [
        ("保存和读取", test_save_and_read),
        ("日期查询", test_date_query),
        ("元数据", test_metadata)
    ]
    
    passed = 0
    for name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {name}")
        print('='*50)
        try:
            if test_func():
                print(f"✅ {name} 测试通过")
                passed += 1
            else:
                print(f"❌ {name} 测试失败")
        except Exception as e:
            print(f"❌ {name} 测试异常: {e}")
    
    print(f"\n{'='*50}")
    print(f"测试结果: {passed}/{len(tests)} 通过")
    print('='*50)
```

### 运行测试
```bash
cd /home/user/webapp/source_code
python3 test_daily_manager.py
```

---

## 性能优化

### 1. 索引文件加速查询
```python
# 创建索引文件加速日期查找
index = {
    "dates": ["2026-01-23", "2026-01-24", ...],
    "latest_date": "2026-01-27",
    "summary": {
        "2026-01-23": {
            "records": 1500,
            "coins": ["BTC", "ETH", ...],
            "time_range": ["00:00:00", "23:59:59"]
        }
    }
}
```

### 2. 缓存机制
```python
from functools import lru_cache

class SupportResistanceDailyManager:
    @lru_cache(maxsize=128)
    def get_levels_by_date_cached(self, date_str):
        """带缓存的日期查询"""
        return self.get_levels_by_date(date_str)
```

### 3. 并行读取
```python
from concurrent.futures import ThreadPoolExecutor

def get_multi_dates_parallel(date_list):
    """并行读取多个日期"""
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(manager.get_levels_by_date, date_list)
    return list(results)
```

### 4. 压缩旧数据
```bash
# 压缩30天前的数据
find /home/user/webapp/data/support_resistance_daily/ \
  -type f -name "*.jsonl" -mtime +30 \
  -exec gzip {} \;
```

---

## 总结

### 当前状态
- ✅ 目录结构已设计
- ✅ 管理器代码已实现
- ✅ Fallback机制已部署
- ⏳ 等待实施

### 推荐方案
**方案C: 仅新数据按日期存储** ⭐⭐
- 最简单
- 风险最低
- 立即生效
- 历史数据保持JSONL格式

### 下一步行动
1. 修改采集器（5分钟）
2. 测试新格式写入（10分钟）
3. 验证API读取（5分钟）
4. 监控运行24小时
5. 确认稳定后完全切换

---

**文档版本**: v1.0  
**更新时间**: 2026-01-27  
**状态**: 就绪，等待实施
