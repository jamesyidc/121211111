# 📊 OKEx 双账户配置报告

## 报告生成时间
- **生成时间**: 2026-01-05 05:31 UTC
- **配置类型**: 主账户 + 子账户双API接入

---

## 一、账户配置概览

### 1.1 主账户（Primary Account）
```
API Key: 0b05a729-40eb-4809-b3eb-eb2de75b7e9e
Secret Key: 4E4DA8BE3B18D01AA07185A006BF9F8E
Passphrase: Tencent@123
账户类型: 主账户
权限: 读取 + 交易 + 提现（完整权限）
```

**当前状态**: ✅ 在线
**持仓数量**: 30个
**未实现盈亏**: +$15.51

### 1.2 子账户（Sub-Account）
```
API Key: 8650e46c-059b-431d-93cf-55f8c79babdb
Secret Key: 4C2BD2AC6A08615EA7F36A6251857FCE
Passphrase: Wu666666.
账户类型: 子账户
权限: 读取（只读权限）
```

**当前状态**: ✅ 在线
**持仓数量**: 9个
**未实现盈亏**: -$42.70
**账户权益**: $243.69 USD

---

## 二、持仓对比分析

### 2.1 主账户持仓概况（TOP 10）

| 序号 | 币种 | 方向 | 持仓量 | 杠杆 | 收益率 | 盈亏 |
|------|------|------|--------|------|--------|------|
| 1 | STX-USDT-SWAP | 📉 空 | 1.00 | 3x | +8.69% | +$0.10 |
| 2 | NEAR-USDT-SWAP | 📉 空 | 0.50 | 10x | +9.23% | +$0.08 |
| 3 | AAVE-USDT-SWAP | 📉 空 | 0.60 | 10x | +4.80% | +$0.05 |
| 4 | DOGE-USDT-SWAP | 📉 空 | 0.06 | 10x | +10.78% | +$0.10 |
| 5 | TON-USDT-SWAP | 📉 空 | 4.00 | 10x | +3.80% | +$0.03 |
| 6 | FIL-USDT-SWAP | 📉 空 | 65.00 | 10x | +18.92% | +$0.19 |
| 7 | XLM-USDT-SWAP | 📉 空 | 0.40 | 10x | +7.82% | +$0.07 |
| 8 | CFX-USDT-SWAP | 📉 空 | 8.00 | 10x | +13.79% | +$0.09 |
| 9 | HBAR-USDT-SWAP | 📉 空 | 0.70 | 10x | +11.01% | +$0.10 |
| 10 | SOL-USDT-SWAP | 📉 空 | 0.06 | 10x | +2.02% | +$0.02 |

**主账户特点**:
- ✅ 全部盈利（显示的10个均为绿色）
- 平均收益率: +9.09%
- 最高收益: FIL-USDT-SWAP +18.92%

### 2.2 子账户持仓概况（全部9个）

| 序号 | 币种 | 方向 | 持仓量 | 杠杆 | 收益率 | 盈亏 |
|------|------|------|--------|------|--------|------|
| 1 | SOL-USDT-SWAP | 📉 空 | 1.00 | 10x | -40.28% | -$5.26 |
| 2 | CFX-USDT-SWAP | 📉 空 | 119.00 | 10x | -53.11% | -$4.77 |
| 3 | CRV-USDT-SWAP | 📉 空 | 264.00 | 10x | -51.66% | -$5.49 |
| 4 | BNB-USDT-SWAP | 📉 空 | 12.00 | 10x | -16.52% | -$1.74 |
| 5 | LDO-USDT-SWAP | 📉 空 | 170.00 | 10x | -25.87% | -$2.72 |
| 6 | TAO-USDT-SWAP | 📉 空 | 5.00 | 10x | -80.96% | -$0.98 |
| 7 | LINK-USDT-SWAP | 📉 空 | 15.00 | 10x | -30.58% | -$6.05 |
| 8 | TON-USDT-SWAP | 📉 空 | 87.00 | 10x | -59.48% | -$9.08 |
| 9 | CFX-USDT-SWAP | 📉 空 | 198.00 | 10x | -43.83% | -$6.61 |

**子账户特点**:
- ❌ 全部亏损（9个均为红色）
- 平均亏损率: -44.70%
- 最大亏损: TAO-USDT-SWAP -80.96%

---

## 三、汇总统计

### 3.1 持仓数量
```
主账户: 30 个持仓
子账户: 9 个持仓
总持仓: 39 个
```

### 3.2 盈亏对比
```
主账户未实现盈亏: +$15.51  🟢
子账户未实现盈亏: -$42.70  🔴
总未实现盈亏: -$27.19
```

### 3.3 风险分析
- **主账户**: 策略有效，整体盈利
- **子账户**: 风险较高，多个持仓严重亏损
- **建议**: 子账户需要及时止损或调整策略

---

## 四、配置文件说明

### 4.1 主配置文件
**文件**: `/home/user/webapp/source_code/okex_api_config.py`
- 主账户API配置
- 默认生产环境使用

### 4.2 子账户配置文件
**文件**: `/home/user/webapp/source_code/okex_api_config_subaccount.py`
- 子账户API配置
- 仅读取权限

### 4.3 账户管理器
**文件**: `/home/user/webapp/source_code/okex_account_manager.py`
- 支持主账户/子账户切换
- 统一的API接口

**使用示例**:
```python
from okex_account_manager import switch_account, get_account_info

# 切换到主账户
switch_account("main")
info = get_account_info()
print(info)

# 切换到子账户
switch_account("sub")
info = get_account_info()
print(info)
```

---

## 五、API使用指南

### 5.1 获取主账户持仓
```bash
cd /home/user/webapp
python3 << 'EOF'
from source_code.okex_account_manager import MAIN_ACCOUNT
# 使用MAIN_ACCOUNT配置调用API
EOF
```

### 5.2 获取子账户持仓
```bash
cd /home/user/webapp
python3 << 'EOF'
from source_code.okex_account_manager import SUB_ACCOUNT
# 使用SUB_ACCOUNT配置调用API
EOF
```

### 5.3 系统中切换账户
在 `anchor_config.json` 中配置账户类型：
```json
{
  "account_type": "main"  // 或 "sub"
}
```

---

## 六、安全建议

### 6.1 权限隔离
- ✅ 主账户：完整权限，谨慎使用
- ✅ 子账户：只读权限，安全查询

### 6.2 密钥管理
- [ ] 使用环境变量存储密钥
- [ ] 定期轮换API密钥
- [ ] 限制API调用IP白名单
- [ ] 启用API操作通知

### 6.3 风险控制
- [ ] 设置止损阈值
- [ ] 监控异常API调用
- [ ] 定期审计API使用记录

---

## 七、验证清单

- ✅ 主账户API连接成功
- ✅ 子账户API连接成功
- ✅ 主账户持仓查询正常（30个）
- ✅ 子账户持仓查询正常（9个）
- ✅ 账户切换功能正常
- ✅ 配置文件创建完成
- ✅ 对比报告生成成功

---

## 八、下一步操作

### 8.1 系统集成
- [ ] 在Web界面添加账户切换功能
- [ ] 实现双账户持仓合并展示
- [ ] 添加账户级别的风险监控

### 8.2 功能扩展
- [ ] 支持多子账户管理
- [ ] 实现账户间持仓对比分析
- [ ] 添加账户级别的盈亏统计

### 8.3 优化建议
- [ ] 子账户亏损持仓需要关注
- [ ] TAO-USDT-SWAP亏损-80.96%，建议止损
- [ ] TON-USDT-SWAP亏损-59.48%，建议调整

---

**报告生成时间**: 2026-01-05 05:31 UTC  
**配置状态**: ✅ 完成  
**API连接**: ✅ 正常  
**双账户**: ✅ 已配置  

**🎉 OKEx双账户配置完成！**
