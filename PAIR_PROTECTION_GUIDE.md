# 🛡️ 交易对保护系统

## 功能说明
自动监控主账户的交易对数量，当发现交易对减少时自动补仓1U保证金。

## 使用方法

### 1. 启动保护
访问实盘锚点系统页面，点击"保护交易对"按钮

### 2. API接口

#### 启动保护
```bash
POST /api/pair-protection/start
```

#### 停止保护
```bash
POST /api/pair-protection/stop
```

#### 查看状态
```bash
GET /api/pair-protection/status
```

#### 手动检查
```bash
POST /api/pair-protection/check
```

## 功能特性

1. **自动记录**: 启动时自动记录当前所有交易对
2. **定时检查**: 每60秒检查一次（可配置）
3. **自动补仓**: 发现缺失立即补仓1U保证金
4. **补仓记录**: 所有补仓动作都有详细记录
5. **状态监控**: 实时查看保护状态

## 数据库表

### protected_pairs（受保护交易对）
- inst_id: 交易对名称
- pos_side: 持仓方向
- initial_count: 初始数量
- last_check_time: 最后检查时间
- status: 状态（active/inactive）

### protection_actions（补仓记录）
- inst_id: 交易对名称
- pos_side: 持仓方向
- action_type: 动作类型
- margin_amount: 保证金金额
- size: 补仓数量
- reason: 补仓原因
- status: 执行状态

## 配置说明

```python
CHECK_INTERVAL = 60  # 检查间隔（秒）
DEFAULT_MARGIN = 1.0  # 默认保证金1 USDT
```

## 系统文件

1. `/home/user/webapp/source_code/trading_pair_protector.py` - 保护系统核心
2. `/home/user/webapp/databases/pair_protection.db` - 保护数据库

## 测试命令

```bash
cd /home/user/webapp/source_code
python3 trading_pair_protector.py
```

## 注意事项

1. ⚠️  当前为模拟模式，不会真实下单
2. ⚠️  实盘模式需要配置真实下单接口
3. ⚠️  建议先在模拟盘测试
4. ⚠️  保护系统会占用API调用配额
