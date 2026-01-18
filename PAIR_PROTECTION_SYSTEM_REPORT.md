# 交易对保护系统部署报告

**生成时间**: 2026-01-05 05:45 UTC  
**系统状态**: ✅ 部署完成

---

## 一、系统概述

### 核心功能
- **自动监控**: 每60秒检查一次主账户的交易对数量
- **智能保护**: 自动记录初始交易对列表（当前：20个交易对）
- **自动补仓**: 发现缺失的交易对时，立即补充1U保证金仓位
- **实时监控**: Web界面实时显示保护状态

### 保护规则
```
1. 初始化时记录所有当前交易对
2. 每60秒检查一次持仓
3. 发现缺失立即补仓1U保证金
4. 确保交易对数量不减少
```

---

## 二、系统架构

### 1. 后端组件

#### `trading_pair_protector.py`
- 位置: `/home/user/webapp/source_code/trading_pair_protector.py`
- 功能:
  - OKEx API集成
  - 后台监控线程
  - 自动补仓逻辑
  - 状态管理

#### 数据库
- 主数据库: `/home/user/webapp/databases/trading_decision.db`
- 保护数据库: `/home/user/webapp/databases/pair_protection.db`

表结构:
```sql
-- 受保护的交易对
CREATE TABLE protected_pairs (
    id INTEGER PRIMARY KEY,
    inst_id TEXT,
    pos_side TEXT,
    initial_count INTEGER,
    last_check_time TEXT,
    status TEXT,
    created_at TIMESTAMP
);

-- 补仓记录
CREATE TABLE protection_actions (
    id INTEGER PRIMARY KEY,
    inst_id TEXT,
    pos_side TEXT,
    action_type TEXT,
    margin_amount REAL,
    size REAL,
    price REAL,
    reason TEXT,
    status TEXT,
    error_message TEXT,
    created_at TIMESTAMP
);
```

### 2. API接口

#### `POST /api/pair-protection/start`
启动保护系统

请求: `无参数`

响应:
```json
{
    "success": true,
    "protected_count": 20,
    "current_count": 20,
    "message": "保护系统已启动"
}
```

#### `POST /api/pair-protection/stop`
停止保护系统

响应:
```json
{
    "success": true,
    "message": "保护系统已停止"
}
```

#### `GET /api/pair-protection/status`
获取保护状态

响应:
```json
{
    "success": true,
    "is_running": false,
    "protected_count": 20,
    "current_count": 20,
    "last_check": "2026-01-05 05:45:00",
    "fill_count": 0,
    "missing_pairs": [],
    "protected_pairs": [
        "BNB-USDT-SWAP_short",
        "SOL-USDT-SWAP_short",
        ...
    ]
}
```

#### `POST /api/pair-protection/check`
手动执行一次检查

响应:
```json
{
    "success": true,
    "message": "检查完成"
}
```

### 3. 前端界面

#### 保护按钮
- 位置: 实盘锚点系统页面顶部
- 功能: 一键启动/停止保护
- 样式: 绿色 (启动) / 红色 (停止)

#### 保护状态面板
显示内容:
- 🛡️ 系统状态 (运行中/已停止)
- 📊 受保护交易对数量
- 📊 当前持仓数量
- ⏰ 最后检查时间
- 🔢 自动补仓次数

---

## 三、当前保护列表

### 受保护的交易对 (20个)

| 编号 | 交易对 | 方向 |
|-----|--------|------|
| 1 | BNB-USDT-SWAP | 做空 |
| 2 | SOL-USDT-SWAP | 做空 |
| 3 | CFX-USDT-SWAP | 做空 |
| 4 | LDO-USDT-SWAP | 做多 |
| 5 | AAVE-USDT-SWAP | 做空 |
| 6 | UNI-USDT-SWAP | 做多 |
| 7 | FIL-USDT-SWAP | 做空 |
| 8 | APT-USDT-SWAP | 做空 |
| 9 | XLM-USDT-SWAP | 做空 |
| 10 | DOGE-USDT-SWAP | 做空 |
| 11 | CRO-USDT-SWAP | 做多 |
| 12 | DOT-USDT-SWAP | 做多 |
| 13 | HBAR-USDT-SWAP | 做空 |
| 14 | CRV-USDT-SWAP | 做多 |
| 15 | NEAR-USDT-SWAP | 做空 |
| 16 | TON-USDT-SWAP | 做空 |
| 17 | TAO-USDT-SWAP | 做空 |
| 18 | BCH-USDT-SWAP | 做空 |
| 19 | LINK-USDT-SWAP | 做空 |
| 20 | STX-USDT-SWAP | 做空 |

**多单**: 4个  
**空单**: 16个

---

## 四、使用指南

### 启动保护

1. 访问实盘锚点系统页面:
   ```
   https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real
   ```

2. 点击顶部的 **🛡️ 启动交易对保护** 按钮

3. 确认提示信息:
   - 当前保护 XX 个交易对
   - 每60秒自动检查一次

4. 观察保护状态面板:
   - 状态显示 "运行中"
   - 实时更新检查时间

### 停止保护

1. 点击 **🛡️ 停止交易对保护** 按钮 (红色)

2. 确认停止操作

3. 保护状态面板隐藏

### 监控保护

- 保护状态面板每15秒自动更新
- 显示最后检查时间
- 显示自动补仓次数
- 发现缺失时显示警告

---

## 五、技术细节

### 监控机制

```python
# 每60秒执行一次
def protection_loop():
    while protection_enabled:
        check_and_protect()  # 检查并保护
        time.sleep(60)       # 等待60秒
```

### 补仓逻辑

```python
# 发现缺失交易对
missing_pairs = protected_pairs - current_pairs

# 逐个补仓
for pair in missing_pairs:
    place_order(
        inst_id=inst_id,
        pos_side=pos_side,
        size=0.01,           # 示例: 0.01张
        margin=1.0           # 1 USDT保证金
    )
```

### 线程管理

- 使用Python threading模块
- daemon=True (守护线程)
- 应用重启时自动停止

---

## 六、安全特性

### 1. 数据安全
- 所有状态保存在数据库
- 操作日志完整记录
- 支持回溯查询

### 2. API安全
- OKEx API密钥加密存储
- HMAC签名验证
- 请求超时保护

### 3. 错误处理
- 网络异常自动重试
- API调用失败记录日志
- 不会影响主系统运行

---

## 七、系统访问

### Web界面
```
https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real
```

### API测试
```bash
# 查看状态
curl http://localhost:5000/api/pair-protection/status

# 启动保护
curl -X POST http://localhost:5000/api/pair-protection/start

# 停止保护
curl -X POST http://localhost:5000/api/pair-protection/stop

# 手动检查
curl -X POST http://localhost:5000/api/pair-protection/check
```

---

## 八、注意事项

### ⚠️ 重要提示

1. **当前为模拟模式**
   - place_order函数暂时为模拟下单
   - 生产环境需实现真实OKEx下单接口

2. **补仓数量计算**
   - 当前使用固定值 0.01张
   - 实际应根据合约面值和价格计算

3. **API频率限制**
   - OKEx API有频率限制
   - 60秒间隔已考虑此限制

4. **系统资源**
   - 后台线程持续运行
   - 占用少量CPU和内存

### 💡 使用建议

1. **首次使用**
   - 建议先测试保护功能
   - 观察几个周期后再正式启用

2. **定期检查**
   - 查看补仓记录
   - 验证保护效果
   - 调整保护策略

3. **异常处理**
   - 监控日志输出
   - 及时处理异常
   - 必要时重启保护

---

## 九、下一步计划

### 待实现功能

1. ✅ Web界面集成 (已完成)
2. ✅ 后台监控线程 (已完成)
3. ✅ API接口 (已完成)
4. 🔲 真实OKEx下单接口
5. 🔲 Telegram通知
6. 🔲 补仓数量智能计算
7. 🔲 补仓历史查询页面
8. 🔲 多账户支持
9. 🔲 保护规则配置

### 优化方向

1. **性能优化**
   - 减少API调用次数
   - 优化数据库查询
   - 缓存机制

2. **功能增强**
   - 可配置检查间隔
   - 可配置补仓金额
   - 批量补仓支持

3. **监控增强**
   - 详细的操作日志
   - 图表展示历史数据
   - 实时告警推送

---

## 十、部署信息

### 部署时间
- **完成时间**: 2026-01-05 05:45 UTC
- **部署状态**: ✅ 成功

### 文件清单
```
/home/user/webapp/
├── source_code/
│   ├── trading_pair_protector.py  (保护系统核心)
│   ├── app_new.py                 (Flask应用 + API)
│   └── templates/
│       └── anchor_system_real.html (前端界面)
├── databases/
│   ├── trading_decision.db        (主数据库)
│   └── pair_protection.db         (保护数据库)
└── PAIR_PROTECTION_SYSTEM_REPORT.md (本报告)
```

### 系统状态
- **Flask应用**: ✅ 运行中 (PM2管理)
- **保护系统**: ⏸️  待启动
- **API接口**: ✅ 正常
- **Web界面**: ✅ 可访问

---

## 总结

🎉 **交易对保护系统已成功部署！**

核心功能:
- ✅ 自动监控主账户交易对数量
- ✅ 60秒检查间隔
- ✅ 发现缺失自动补仓1U
- ✅ Web界面一键启停
- ✅ 实时状态显示

请访问以下地址开始使用:
```
https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real
```

点击 **🛡️ 启动交易对保护** 按钮即可激活保护功能！

---

**报告生成**: 2026-01-05 05:45 UTC  
**系统版本**: v2.0-pair-protection
