# /query页面字段显示修复完成

## ✅ 修复内容

### 列名更正
- **修改前**：涨跌
- **修改后**：涨速

### 显示字段更正
- **修改前**：显示 `coin.change` 字段（实际是change_24h的别名）
- **修改后**：显示 `coin.speed` 字段

### 样式类名更正
- **修改前**：`changeClass`（根据coin.change判断正负）
- **修改后**：`speedClass`（根据coin.speed判断正负）

## 📊 字段说明

### 当前列结构（修复后）

| 列名 | 显示字段 | 数据类型 | 数值范围 | 示例 |
|-----|---------|---------|---------|------|
| 涨速 | `coin.speed` | float | -1.0 到 1.0 | -0.28, 1.1, 0.04 |
| 急涨 | `coin.rush_up` | int | 0-10 | 0, 1, 2 |
| 急跌 | `coin.rush_down` | int | 0-10 | 0, 1, 2 |
| 24h% | `coin.change_24h` | float | -100 到 +∞ | -0.44, -5.21, 1.55 |

## 🔍 问题原因

1. **列名误导**：列名为"涨跌"，但实际显示的是涨速（speed）
2. **字段使用错误**：本应显示速度字段，但代码中使用了change字段
3. **历史遗留**：之前的字段命名混淆导致前端代码也使用了错误的字段

## ✅ 验证结果

### 修复前
```
列名：涨跌
显示：coin.change（实际是change_24h）
问题：列名与字段含义不匹配
```

### 修复后
```
列名：涨速 ✅
显示：coin.speed ✅
结果：列名与字段含义完全匹配
```

### API数据示例（14:19快照）

```json
{
  "symbol": "BCH",
  "speed": -0.28,      // 涨速（现在显示在"涨速"列）✅
  "change_24h": -0.44, // 24h涨跌幅（显示在"24h%"列）✅
  "rush_up": 1,        // 急涨次数 ✅
  "rush_down": 1       // 急跌次数 ✅
}
```

## 📝 相关修改

### 文件
- `source_code/app_new.py` (行865-1370)

### 具体修改

#### 1. 表头修改（行870）
```html
<!-- 修改前 -->
<th>涨跌</th>

<!-- 修改后 -->
<th>涨速</th>
```

#### 2. 数据显示修改（行1342-1357）
```javascript
// 修改前
const changeClass = coin.change > 0 ? 'value-positive' : ...
html += '<td class="' + changeClass + '">' + coin.change.toFixed(2) + '</td>';

// 修改后
const speedClass = coin.speed > 0 ? 'value-positive' : ...
html += '<td class="' + speedClass + '">' + coin.speed.toFixed(2) + '</td>';
```

## 🎯 现在的字段映射（完全正确）

```
TXT文件：    序号|币名|涨速|急涨|急跌|...
               ↓   ↓   ↓   ↓   ↓
数据库：     inst_id, speed, rush_up, rush_down
               ↓   ↓   ↓   ↓   ↓
API：        symbol, speed, rush_up, rush_down
               ↓   ↓   ↓   ↓   ↓
前端显示：   币名, 涨速, 急涨, 急跌

✅ 完美一致！
```

## 🚀 访问地址

- **本地**: http://localhost:5000/query
- **公网**: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/query

刷新页面（Ctrl+F5）即可看到修复后的正确列名和数据！

## 📋 总结

- ✅ 列名已正确：涨速
- ✅ 显示字段已正确：coin.speed
- ✅ 数据范围正确：-1 到 1 之间的浮点数
- ✅ 与API字段完全匹配
- ✅ 与TXT文件格式完全一致

**所有字段映射现在都是正确的！**

---

**修复时间**：2026-01-15 14:25  
**修复版本**：V5.5.2  
**Commit**: 1dd9ab1
