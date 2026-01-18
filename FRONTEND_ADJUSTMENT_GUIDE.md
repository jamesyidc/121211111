# 前端调整实施指南

## 📋 阶段5：前端调整任务清单

### 🎯 调整目标
根据用户需求，将Query页面的前端显示调整为与V5.5一致的格式。

---

## 1️⃣ 币种列表调整

### 当前格式
```
序号 | 币名 | 急涨 | 急跌 | 更新时间 | 历史高位 | 高位时间 | 距离高位跌幅 | 24涨幅 | +4% | -3% | 排行 | 当前价格 | 最高占比 | 最低占比
```

### 目标格式
```
优先级 | 币名 | 急涨 | 急跌 | 更新时间 | 历史高位 | 高位时间 | 距离高位跌幅 | 24涨幅 | 排行 | 当前价格 | 最高占比 | 最低占比 | 计次 | 计次得分
```

### 修改要点
1. **优先级列放在第一位** ⭐
   - 显示等级数字 (1-6)
   - 可选：显示等级名称 (等级1-等级6)
   - 按优先级排序 (API已实现)

2. **移除列**
   - 删除：`+4%` 列
   - 删除：`-3%` 列

3. **新增列**
   - 添加：`计次` 列（显示count字段）
   - 添加：`计次得分` 列（显示星级，如 ★★★、☆☆）

### 实施位置
- **文件**: `source_code/app_new.py`
- **模板**: `MAIN_HTML` (从132行开始)
- **关键代码区域**:
  - 表头定义：搜索 `<thead>` 或表格列名
  - 数据行渲染：搜索币种数据循环（通常是JavaScript中的forEach或map）

---

## 2️⃣ 聚合数据显示调整

### 当前显示
根据截图，页面顶部显示：
```
急涨: XX
急跌: XX
计次: XX
差值: XX
比值: XX
状态: XXXX
```

### 目标显示
确保显示的是**透明标签的聚合数据**，而不是前端计算的结果。

### API字段映射
从`/api/latest`返回的数据：
```javascript
{
  "rush_up": 34,              // 急涨（透明标签）
  "rush_down": 8,             // 急跌（透明标签）
  "count_aggregate": 6,       // 计次（透明标签）
  "diff": 26,                 // 差值
  "ratio": 3.25,              // 比值
  "status": "震荡无序",       // 状态
  "price_lowest": 0,          // 比价最低
  "price_newhigh": 0          // 比价创新高
}
```

### 实施位置
- **文件**: `source_code/app_new.py`
- **模板**: `MAIN_HTML`
- **关键代码区域**:
  - 搜索聚合数据显示的HTML元素（可能有id或class）
  - 搜索JavaScript中更新聚合数据的函数

---

## 3️⃣ 优先级和星级显示样式

### 优先级显示
```html
<!-- 等级1-5：简单文字 -->
<td class="priority priority-1">1</td>

<!-- 等级6：显示星级 -->
<td class="priority priority-6">
  6 <span class="count-score">★★★</span>
</td>
```

### CSS样式建议
```css
/* 优先级颜色 */
.priority-1 { background-color: #ff4444; color: white; } /* 红色 - 最高优先级 */
.priority-2 { background-color: #ff8844; color: white; } /* 橙红 */
.priority-3 { background-color: #ffaa44; color: white; } /* 橙色 */
.priority-4 { background-color: #ffcc44; color: white; } /* 黄橙 */
.priority-5 { background-color: #ffee44; } /* 黄色 */
.priority-6 { background-color: #f0f0f0; } /* 灰色 - 等级6 */

/* 星级样式 */
.count-score {
  margin-left: 5px;
  font-size: 14px;
}

.count-score.solid {
  color: #ffd700; /* 金色实心星 */
}

.count-score.hollow {
  color: #cccccc; /* 灰色空心星 */
}
```

---

## 4️⃣ JavaScript数据处理

### 币种数据渲染
当前可能的代码：
```javascript
coins.forEach(coin => {
  // 旧代码
  row = `
    <td>${index}</td>
    <td>${coin.symbol}</td>
    <td>${coin.rush_up}</td>
    ...
  `;
});
```

修改为：
```javascript
coins.forEach(coin => {
  // 新代码：优先级在前
  const priorityClass = `priority-${coin.priority}`;
  const countScore = coin.count_score_display || '';
  const scoreClass = coin.count_score_type === 'solid' ? 'solid' : 'hollow';
  
  row = `
    <td class="priority ${priorityClass}">${coin.priority}</td>
    <td>${coin.symbol}</td>
    <td>${coin.rush_up}</td>
    <td>${coin.rush_down}</td>
    ...
    <td>${coin.count}</td>
    <td><span class="count-score ${scoreClass}">${countScore}</span></td>
  `;
});
```

---

## 5️⃣ 实施步骤

### Step 1: 备份模板 ✅
```bash
cp source_code/app_new.py source_code/app_new.py.backup_before_frontend_changes
```

### Step 2: 定位表格HTML
```bash
# 在MAIN_HTML中搜索表格
grep -n "<thead>" source_code/app_new.py
grep -n "币名" source_code/app_new.py
```

### Step 3: 修改表头
1. 定位`<thead>`部分
2. 将"序号"改为"优先级"
3. 移除"+4%"和"-3%"列
4. 添加"计次"和"计次得分"列

### Step 4: 修改数据行
1. 定位渲染币种数据的JavaScript代码
2. 修改列顺序（优先级第一）
3. 移除+4%和-3%的数据
4. 添加计次和计次得分的显示

### Step 5: 添加CSS样式
1. 在`<style>`标签中添加优先级和星级样式
2. 确保颜色对比度足够

### Step 6: 更新聚合数据显示
1. 确保使用`count_aggregate`而不是`count`
2. 显示`price_lowest`和`price_newhigh`（如果需要）

### Step 7: 测试
1. 重启Flask: `pm2 restart flask-app`
2. 访问Query页面
3. 验证：
   - ✅ 优先级列在第一位
   - ✅ 星级显示正确
   - ✅ +4%和-3%列已移除
   - ✅ 计次列正确显示
   - ✅ 聚合数据正确

---

## 📝 注意事项

### 1. 数据字段
确保从API获取以下字段：
- `priority` - 优先级数字 (1-6)
- `priority_name` - 优先级名称
- `count` - 计次值
- `count_score_display` - 星级显示 (例如: "★★★")
- `count_score_type` - 星级类型 ("solid" 或 "hollow")
- `max_ratio` - 最高占比
- `min_ratio` - 最低占比

### 2. 排序
- 已在API层实现按优先级排序
- 前端接收后直接显示即可
- 不需要前端再次排序

### 3. 兼容性
- 保持现有功能不变
- 只是调整显示格式
- 不影响数据查询和筛选功能

### 4. 响应式设计
- 考虑移动端显示
- 优先级列可能需要固定宽度
- 星级在小屏幕上的显示

---

## 🔍 查找代码的关键字

### 在MAIN_HTML中搜索
```bash
# 表格相关
grep -n "table" source_code/app_new.py
grep -n "thead" source_code/app_new.py
grep -n "币名" source_code/app_new.py

# 聚合数据相关
grep -n "急涨" source_code/app_new.py
grep -n "急跌" source_code/app_new.py
grep -n "计次" source_code/app_new.py

# JavaScript渲染相关
grep -n "forEach" source_code/app_new.py
grep -n "coins" source_code/app_new.py
```

---

## ✅ 验证清单

完成后检查以下项目：

### 显示正确性
- [ ] 优先级列在第一位
- [ ] 优先级数字显示 (1-6)
- [ ] 等级6显示星级
- [ ] 星级样式正确（实心/空心）
- [ ] +4%列已移除
- [ ] -3%列已移除
- [ ] 计次列显示
- [ ] 聚合数据使用count_aggregate

### 功能正确性
- [ ] 按优先级排序
- [ ] 数据刷新正常
- [ ] 筛选功能正常
- [ ] 分页功能正常

### 样式正确性
- [ ] 优先级颜色区分
- [ ] 星级颜色正确
- [ ] 移动端显示正常
- [ ] 无布局错乱

---

## 📊 预期效果

完成后，Query页面应该显示类似V5.5的格式：

```
优先级 | 币名 | 急涨 | 急跌 | 计次 | 计次得分 | ...
------|------|------|------|------|----------|----
  1   | BTC  |  1   |  0   |  13  |          | ...
  2   | ETH  |  1   |  0   |  4   |          | ...
  6   | UNI  |  0   |  1   |  10  |   ★★★    | ...
```

顶部聚合数据：
```
急涨: 34    急跌: 8    计次: 6
差值: 26    比值: 3.25   状态: 震荡无序
```

---

**文档创建时间**: 2026-01-14 23:10  
**状态**: 实施指南完成，等待前端修改  
**预计实施时间**: 20-30分钟
