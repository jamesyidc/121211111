# 锚定系统空单盈利监控 - 完成说明

## 📋 功能概述

在锚定系统实盘页面添加了空单盈利统计图表，实时监控4个关键指标：

1. **盈利 ≤ 40%** - 橙色曲线
2. **亏损 (< 0%)** - 红色曲线
3. **盈利 ≥ 80%** - 绿色曲线
4. **盈利 ≥ 120%** - 蓝色曲线

## ✅ 已完成功能

### 1. 数据采集系统

**文件**: `source_code/anchor_profit_monitor.py`

- ✅ 每分钟自动采集空单持仓数据
- ✅ 统计4个盈利指标
- ✅ 数据存储到JSONL文件
- ✅ PM2自动管理服务
- ✅ 与anchor_system集成，复用get_positions()函数

**数据存储位置**: `/home/user/webapp/data/anchor_profit_stats/anchor_profit_stats.jsonl`

**PM2服务名**: `anchor-profit-monitor`

### 2. API接口

**已添加3个API端点**:

#### GET `/api/anchor-profit/latest`
获取最新的盈利统计数据
```bash
curl 'http://localhost:5000/api/anchor-profit/latest'
```

#### GET `/api/anchor-profit/history?limit=60`
获取历史数据（默认最近60条，即1小时）
```bash
curl 'http://localhost:5000/api/anchor-profit/history?limit=60'
```

#### POST `/api/anchor-profit/collect`
手动触发一次数据采集
```bash
curl -X POST 'http://localhost:5000/api/anchor-profit/collect'
```

### 3. 前端图表展示

**文件**: `source_code/templates/anchor_system_real.html`

- ✅ 在收益率趋势图后添加新图表卡片
- ✅ 使用ECharts渲染4条曲线
- ✅ 显示最近1小时的数据（60个点）
- ✅ 每60秒自动刷新一次
- ✅ 响应式设计，自动适配窗口大小

## 🎨 图表特性

- **标题**: 空单盈利分布趋势（最近1小时）
- **X轴**: 时间（HH:MM格式）
- **Y轴**: 数量（个）
- **提示框**: 鼠标悬停显示详细数据
- **图例**: 4个指标颜色说明
- **平滑曲线**: smooth: true
- **线宽**: 2px

## 📊 数据格式

JSONL文件每行格式：
```json
{
  "timestamp": 1768460297,
  "datetime": "2026-01-15 06:58:17",
  "stats": {
    "lte_40": 0,
    "loss": 0,
    "gte_80": 0,
    "gte_120": 0,
    "total": 0
  },
  "positions": []
}
```

## 🚀 运行状态

### PM2服务状态
```bash
pm2 status anchor-profit-monitor
```

### 查看日志
```bash
pm2 logs anchor-profit-monitor
```

### 重启服务
```bash
pm2 restart anchor-profit-monitor
```

## 🌐 访问地址

**本地**: http://localhost:5000/anchor-system-real

**公网**: https://5000-igsydcyqs9jlcot56rnqk-b32ec7bb.sandbox.novita.ai/anchor-system-real

## 🔧 技术栈

- **后端**: Python 3, Flask
- **前端**: JavaScript, ECharts 5.4.3
- **数据存储**: JSONL
- **进程管理**: PM2
- **数据来源**: OKEx API (通过anchor_system集成)

## 📝 Git提交记录

1. **e1b68f5** - feat: 添加锚定系统空单盈利统计图表
   - 创建监控脚本
   - 添加API端点
   - 前端图表展示
   
2. **de4ee2f** - fix: 修复API重复endpoint问题
   - 删除重复函数定义
   - 修复缩进错误

## ✨ 特色功能

1. **实时监控**: 每分钟采集一次数据
2. **自动刷新**: 前端每60秒自动更新图表
3. **历史追溯**: 可查看任意时长的历史数据
4. **可视化**: 直观的曲线图展示
5. **零配置**: PM2自动管理，无需手动启动

## 🎯 使用场景

- 监控空单整体盈利分布
- 识别极端盈利/亏损情况
- 评估交易策略效果
- 风险预警和决策支持

## ⚡ 性能优化

- 使用JSONL格式，追加写入，不影响历史数据
- 前端只加载最近60条数据，减少带宽
- ECharts图表懒加载，提升页面加载速度
- PM2进程管理，自动重启，保证服务稳定

## 📌 注意事项

1. 当前系统实盘无空单持仓，所以所有指标为0
2. 有空单持仓时，图表会显示实时变化的曲线
3. 数据每分钟更新一次，前端每60秒刷新一次
4. JSONL文件会持续增长，建议定期归档

## 🎉 完成状态

✅ 所有功能已完成
✅ API测试通过
✅ 前端集成完成
✅ PM2服务正常运行
✅ 数据采集正常
✅ Git提交完成

---

**完成时间**: 2026-01-15 07:00
**开发环境**: Sandbox
**状态**: ✅ 已上线运行
