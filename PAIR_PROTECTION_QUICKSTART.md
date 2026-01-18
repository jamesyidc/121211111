# 🛡️ 交易对保护系统 - 快速开始

## 一键使用指南

### 步骤1: 访问系统
```
https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real
```

### 步骤2: 启动保护
- 点击页面顶部的 **🛡️ 启动交易对保护** 按钮
- 确认弹窗信息

### 步骤3: 监控状态
- 观察保护状态面板（绿色背景）
- 查看受保护交易对数量
- 查看最后检查时间

## 核心功能

✅ **自动监控**: 每60秒检查一次  
✅ **智能保护**: 记录初始27个交易对  
✅ **自动补仓**: 发现缺失立即补1U  
✅ **实时显示**: 状态实时更新  

## 当前状态

- **受保护交易对**: 20个
- **检查间隔**: 60秒
- **补仓金额**: 1 USDT
- **系统状态**: 已部署，待启动

## 快速命令

```bash
# 查看状态
curl http://localhost:5000/api/pair-protection/status

# 启动保护
curl -X POST http://localhost:5000/api/pair-protection/start

# 停止保护
curl -X POST http://localhost:5000/api/pair-protection/stop
```

## 注意事项

⚠️ 当前为模拟模式，不会真实下单  
⚠️ 生产环境需实现真实OKEx API下单

---

**部署时间**: 2026-01-05 05:45 UTC  
**系统版本**: v2.0-pair-protection
