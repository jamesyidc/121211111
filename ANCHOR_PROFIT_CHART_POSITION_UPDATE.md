# 空单盈利统计图表位置调整完成

## ✅ 调整内容

### 原位置
之前图表位于页面中间的 `main-grid` 区域，与"收益率趋势图"和"最新告警"并列显示。

### 新位置
现在图表位于**页面顶部**，具体位置：
- ✅ Header（标题和按钮）之后
- ✅ 持仓摘要卡片（主账户持仓、主账户盈亏、子账户持仓等）之前
- ✅ 全宽显示，独立卡片

## 📐 布局结构

```
┌─────────────────────────────────────────┐
│  🔴 实盘锚点系统 Header                    │
│  [🔄 刷新数据] [🛡️ 启动交易对保护] [🏠 返回] │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  💰 空单盈利统计                          │
│  ┌───────────────────────────────────┐  │
│  │   📈 曲线图（4条线）                │  │
│  │   - 盈利 ≤ 40%  (橙色)            │  │
│  │   - 亏损 < 0%    (红色)            │  │
│  │   - 盈利 ≥ 80%   (绿色)            │  │
│  │   - 盈利 ≥ 120%  (蓝色)            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  💼 主账户持仓 | 📈 主账户盈亏 | 👥 子账户  │
│  (持仓摘要卡片)                          │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  其他内容区域...                         │
└─────────────────────────────────────────┘
```

## 🎨 样式特点

- **全宽显示**: 占据整行宽度
- **独立卡片**: 白色背景，圆角边框
- **统一高度**: 400px 图表高度
- **底部间距**: margin-bottom: 30px
- **实时更新**: 右上角显示"最后更新"时间

## 🔧 技术细节

### HTML结构
```html
<!-- 空单盈利统计图表 -->
<div class="card" style="margin-bottom: 30px;">
    <div class="card-header">
        <div class="card-title">
            <span>💰</span>
            空单盈利统计
        </div>
        <div class="update-time" id="profitStatsUpdateTime">
            最后更新: --
        </div>
    </div>
    <div class="chart-container" id="profitStatsChart" 
         style="height: 400px; background: white; border-radius: 0 0 15px 15px;">
    </div>
</div>
```

### JavaScript集成
- ✅ `profitStatsChart` - ECharts实例
- ✅ `loadProfitStats()` - 加载数据函数
- ✅ `renderProfitStatsChart()` - 渲染图表函数
- ✅ 60秒定时刷新
- ✅ 窗口resize自动调整

## 📊 数据流

```
anchor_profit_monitor.py (每分钟采集)
           ↓
anchor_profit_stats.jsonl (JSONL存储)
           ↓
/api/anchor-profit/history?limit=60 (API)
           ↓
loadProfitStats() (前端加载)
           ↓
renderProfitStatsChart() (ECharts渲染)
           ↓
profitStatsChart (顶部显示)
```

## ✅ 验证结果

- ✅ 图表已移至页面顶部
- ✅ 原main-grid中的重复图表已删除
- ✅ 仅保留一个图表实例
- ✅ 功能正常（自动刷新、数据加载）
- ✅ 样式统一（与其他卡片一致）
- ✅ ID唯一性（无重复元素）

## 🌐 访问地址

**页面地址**: https://5000-igsydcyqs9jlcot56rnqk-b32ec7bb.sandbox.novita.ai/anchor-system-real

**API地址**: https://5000-igsydcyqs9jlcot56rnqk-b32ec7bb.sandbox.novita.ai/api/anchor-profit/history?limit=60

## 📝 Git提交

**Commit**: `ad3f246`

**标题**: feat: 将空单盈利统计图表移到页面顶部

**详情**:
- 将空单盈利统计图表从main-grid移到header之后
- 位置：header-actions按钮组之后，持仓摘要卡片之前
- 删除原main-grid中的重复图表
- 保持图表功能不变（每60秒自动刷新）

## 🎯 效果对比

### 调整前
- 图表在页面中间
- 与其他图表并列显示
- 宽度受grid限制

### 调整后
- ✅ 图表在页面顶部
- ✅ 独立全宽显示
- ✅ 视觉优先级更高
- ✅ 更易于查看关键指标

---

**状态**: ✅ 已完成并上线
**完成时间**: 2026-01-15 07:05
