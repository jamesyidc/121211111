# 🔍 历史查询系统问题分析与修复方案

**问题时间**: 2026-01-15  
**报告人**: 用户  
**问题描述**: 急涨/急跌历史趋势图中的"计次"数据错误，且数据采集在03:11后停止

---

## 📋 问题诊断

### 问题1: 计次数据错误

**现状**:
```
时间: 2026-01-15 00:29:00 | 计次: 1
时间: 2026-01-15 00:39:00 | 计次: 2
时间: 2026-01-15 00:40:00 | 计次: 1  ← 应该递增，但重置了
时间: 2026-01-15 00:50:00 | 计次: 1
时间: 2026-01-15 01:00:00 | 计次: 1
...
时间: 2026-01-15 01:30:00 | 计次: 2
时间: 2026-01-15 01:40:00 | 计次: 3
时间: 2026-01-15 02:41:00 | 计次: 4
时间: 2026-01-15 03:11:00 | 计次: 4
时间: 2026-01-15 10:58:00 | 计次: 4  ← 7小时后才有数据
```

**预期**:
计次应该是累加的，代表连续出现某种状态的次数。例如：
- 如果连续5次都是"温和上涨"，计次应该是1→2→3→4→5
- 如果状态改变，计次重置为1

**根本原因**:
计次数据来源于Google Drive上传的TXT文件中的"透明标签_计次"字段：

```
透明标签_计次=1
```

这个TXT文件是由**外部程序**（Windows客户端）生成的，计次计算逻辑在客户端，服务器端只是解析读取。

---

### 问题2: 数据采集停止

**现状**:
- 最后一条数据: `2026-01-15 03:11:00`
- 之后中断7小时
- 下一条数据: `2026-01-15 10:58:00`

**可能原因**:
1. Google Drive上传程序在03:11-10:58期间未运行或异常
2. 网络问题导致文件上传失败
3. 文件生成程序崩溃或被关闭

---

## 🏗️ 数据流架构分析

### 当前架构

```
外部程序（Windows客户端）
    ↓ 生成TXT文件
    ↓ 包含: 透明标签_计次=数字
    ↓ 上传到Google Drive
    ↓
GDrive检测器 (gdrive-detector)
    ↓ 每30秒检测新文件
    ↓ 解析TXT文件
    ↓ 提取透明标签数据
    ↓ 计次 = 从TXT读取
    ↓
保存到JSONL
    ↓ crypto_aggregate.jsonl
    ↓
前端页面展示
    ↓ /query 历史查询页面
```

**关键发现**:
- ✅ GDrive检测器正常运行（PM2 ID: 15, online, 10小时）
- ✅ 检测逻辑正常（每30秒扫描一次）
- ✅ 最新快照: 2026-01-15 11:08:00
- ❌ **计次数据由外部程序生成**，服务器端无法控制

---

## 🔍 计次计算逻辑分析

### TXT文件解析代码

文件: `/home/user/webapp/txt_parser_enhanced.py`

```python
def parse_transparent_labels(content):
    """解析TXT文件中的透明标签聚合数据"""
    
    label_mappings = {
        '透明标签_计次': 'count_aggregate',  # ← 直接读取
        # ...
    }
    
    for line in lines:
        if line.startswith('透明标签_计次'):
            value_part = line.split('=', 1)[1].strip()
            # 提取数字
            match = re.search(r'-?\d+', value_part)
            if match:
                aggregate_data['count_aggregate'] = int(match.group())
```

**问题**: 服务器端只是**被动读取**TXT文件中的计次值，不进行任何计算。

---

## 📊 数据验证

### GDrive检测器日志

```
[2026-01-15 11:08:37]    发现 21 个文件
[2026-01-15 11:09:08]    当前最新快照: 2026-01-15 10:58:00
[2026-01-15 11:09:08]    发现 22 个文件

📄 处理文件: 2026-01-15_1108.txt (时间: 2026-01-15 11:08:00)
[2026-01-15 11:09:09]    找到文件ID: 1dChdkiWq67oS3eW2LFPGXKcykV2mt9AL
[2026-01-15 11:09:10]   📊 解析到 29 条币种记录
[2026-01-15 11:09:10]   📈 聚合数据: 急涨=4, 急跌=49, 计次=4, 状态=震荡无序
✅ 已写入 30940 条记录到JSONL
```

**结论**: 
- ✅ GDrive检测器工作正常
- ✅ 文件解析正常
- ❌ 计次数据来自TXT文件本身

---

## 🛠️ 解决方案

### 方案1: 修复外部上传程序（推荐）

**原因**: 计次数据由Windows客户端生成

**操作**:
1. 检查Windows客户端的计次计算逻辑
2. 确保计次正确累加
3. 修复03:11-10:58期间的数据缺失问题

**需要检查**:
- Windows客户端是否正常运行
- 上传到Google Drive的逻辑是否正确
- 计次计算是否有bug

---

### 方案2: 服务器端重新计算计次（备选）

**思路**: 不依赖TXT文件中的计次，服务器端自己计算

**实现步骤**:

1. **修改解析逻辑**，根据状态变化计算计次

```python
# 新增计次计算模块
class CountCalculator:
    def __init__(self):
        self.last_status = None
        self.current_count = 0
    
    def calculate_count(self, current_status):
        """根据状态变化计算计次"""
        if current_status == self.last_status:
            # 状态未变，计次+1
            self.current_count += 1
        else:
            # 状态改变，重置为1
            self.current_count = 1
            self.last_status = current_status
        
        return self.current_count
```

2. **在GDrive检测器中应用**

```python
# 初始化计算器（需要持久化状态）
count_calculator = CountCalculator()

# 解析每个文件时
status = aggregate_data.get('status', '')
calculated_count = count_calculator.calculate_count(status)

# 使用计算的计次，而不是TXT中的计次
aggregate_data['count_aggregate'] = calculated_count
```

3. **持久化计数器状态**

```python
# 保存到文件，以便重启后恢复
import json

STATE_FILE = '/home/user/webapp/data/count_calculator_state.json'

def save_state():
    state = {
        'last_status': count_calculator.last_status,
        'current_count': count_calculator.current_count,
        'last_update': datetime.now().isoformat()
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            count_calculator.last_status = state['last_status']
            count_calculator.current_count = state['current_count']
```

---

### 方案3: 数据修复脚本（补救措施）

针对已经错误的历史数据，创建修复脚本：

```python
#!/usr/bin/env python3
"""
修复crypto_aggregate.jsonl中的计次数据
根据状态变化重新计算计次
"""
import json
from datetime import datetime

def fix_count_aggregate(input_file, output_file):
    """修复计次数据"""
    
    records = []
    with open(input_file, 'r') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    # 按时间排序
    records.sort(key=lambda x: x['snapshot_time'])
    
    # 重新计算计次
    last_status = None
    current_count = 0
    
    for record in records:
        status = record.get('status', '')
        
        if status == last_status:
            current_count += 1
        else:
            current_count = 1
            last_status = status
        
        record['count_aggregate'] = current_count
        record['count_aggregate_fixed'] = True  # 标记已修复
    
    # 写入修复后的数据
    with open(output_file, 'w') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ 修复完成！共处理 {len(records)} 条记录")

if __name__ == '__main__':
    fix_count_aggregate(
        '/home/user/webapp/data/gdrive_jsonl/crypto_aggregate.jsonl',
        '/home/user/webapp/data/gdrive_jsonl/crypto_aggregate_fixed.jsonl'
    )
```

---

## 🔧 立即行动

### 紧急修复步骤

#### 步骤1: 检查外部上传程序

```bash
# 检查Windows客户端是否运行
# 检查最近上传的文件时间
# 查看客户端日志
```

#### 步骤2: 验证数据完整性

```bash
# 查看最新的快照时间
cd /home/user/webapp
pm2 logs gdrive-detector --lines 50

# 检查聚合数据文件
tail -20 data/gdrive_jsonl/crypto_aggregate.jsonl
```

#### 步骤3: 临时修复计次显示（前端）

如果服务器端无法立即修复，可以在前端临时计算：

```javascript
// 前端重新计算计次
let lastStatus = null;
let currentCount = 0;

trendData.forEach(point => {
    if (point.status === lastStatus) {
        currentCount++;
    } else {
        currentCount = 1;
        lastStatus = point.status;
    }
    point.count_aggregate = currentCount;  // 覆盖错误的计次
});
```

---

## 📊 建议的完整解决方案

### 长期方案: 服务器端独立计算

**优势**:
- ✅ 不依赖外部程序
- ✅ 数据更可靠
- ✅ 便于调试和修复

**实施**:
1. 创建服务器端计次计算模块
2. 修改GDrive检测器集成计算逻辑
3. 持久化计数器状态
4. 修复历史错误数据
5. 前端对接新的计次数据

**预期效果**:
- ✅ 计次数据正确累加
- ✅ 状态改变时正确重置
- ✅ 数据缺失时不受影响

---

## 🎯 总结

### 问题根源

1. **计次数据错误**: 由外部程序生成，服务器端只是被动读取
2. **数据采集中断**: 外部程序在03:11-10:58期间未上传文件

### 立即修复

1. ✅ 检查外部上传程序状态
2. ✅ 确认Windows客户端运行正常
3. ⚠️ 修复客户端计次计算逻辑

### 长期优化

1. 🔧 服务器端独立计算计次
2. 🔧 不依赖外部程序的计次数据
3. 🔧 添加数据验证和异常检测
4. 🔧 修复历史错误数据

---

**创建时间**: 2026-01-15 11:20  
**问题状态**: 已诊断，待修复  
**优先级**: 高（影响用户体验）

**下一步**: 需要用户提供外部上传程序的访问权限或源码，以修复计次计算逻辑。
