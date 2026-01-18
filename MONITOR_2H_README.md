# 2小时逃顶信号监控器

## 📋 功能说明

监控支撑压力线系统的2小时逃顶信号数量，当超过设定阈值时自动发送Telegram警告消息。

## ⚙️ 配置参数

**文件位置**: `/home/user/webapp/monitor_escape_signals_2h.py`

**关键参数**:
- `THRESHOLD = 80` - 2小时信号数阈值（当前设置：80个）
- `CHECK_INTERVAL = 60` - 检查间隔（60秒 = 1分钟）
- `COOLDOWN_MINUTES = 30` - 冷却时间（30分钟，避免频繁推送）

## 🚀 启动/停止

```bash
# 启动监控器
cd /home/user/webapp
pm2 start ecosystem_monitor_2h.config.js

# 停止监控器
pm2 stop escape-signals-2h-monitor

# 重启监控器
pm2 restart escape-signals-2h-monitor

# 查看状态
pm2 status escape-signals-2h-monitor

# 查看日志
pm2 logs escape-signals-2h-monitor

# 查看最近20行日志（不跟踪）
pm2 logs escape-signals-2h-monitor --lines 20 --nostream
```

## 📊 监控逻辑

1. **每60秒检查一次** `/api/support-resistance/signals-computed` 接口
2. **获取2小时逃顶信号数** (`sell_signals_2h`)
3. **判断阈值**: 
   - 如果 `信号数 > 80`：发送警告
   - 如果 `信号数 <= 80`：正常，不发送
4. **冷却机制**: 发送警告后，30分钟内不会重复发送

## 📱 Telegram消息示例

当2小时信号数超过80时，会收到如下格式的消息：

```
🚨 逃顶信号警告

⚠️ 2小时内逃顶信号数已超过阈值！

📊 统计数据:
━━━━━━━━━━━━━━━
⏰ 2小时信号数: 100 个
📌 阈值: 80 个
🔺 超出: +20 个

📅 24小时信号数: 283 个

⏰ 触发时间: 2026-01-14 13:22:34

💡 建议:
• 市场可能处于高位震荡或回调阶段
• 建议关注已有仓位的止盈机会
• 避免追高，等待回调机会

📍 查看详情: http://localhost:5000/support-resistance
```

## 🔧 修改阈值

如果需要调整阈值（比如改为100），编辑文件：

```bash
nano /home/user/webapp/monitor_escape_signals_2h.py
```

找到第12行：
```python
THRESHOLD = 80  # 修改这个数字
```

修改后重启：
```bash
pm2 restart escape-signals-2h-monitor
```

## 📈 运行状态

当前运行状态：
- ✅ **监控器**: 已启动（PM2 进程ID: 7）
- ✅ **当前2h信号数**: 4（正常）
- ✅ **24h信号数**: 283
- ✅ **阈值**: 80
- ✅ **Telegram推送**: 已测试成功（消息ID: 5185）

## 📝 日志文件

- **输出日志**: `/home/user/webapp/logs/escape_signals_2h_monitor_out.log`
- **错误日志**: `/home/user/webapp/logs/escape_signals_2h_monitor_error.log`

## ⚠️ 注意事项

1. **Telegram配置**: 使用 `/home/user/webapp/configs/telegram_config.json` 中的配置
2. **依赖服务**: 
   - Flask API (`flask-app`) 必须运行
   - 支撑压力线采集器 (`support-resistance-collector`) 必须运行
3. **网络要求**: 需要能访问 Telegram API

## 🔍 故障排查

### 问题：没有收到Telegram消息

1. 检查监控器是否运行：
   ```bash
   pm2 status escape-signals-2h-monitor
   ```

2. 查看日志：
   ```bash
   pm2 logs escape-signals-2h-monitor --lines 50
   ```

3. 检查Telegram配置：
   ```bash
   cat /home/user/webapp/configs/telegram_config.json
   ```

4. 手动测试推送：
   ```bash
   cd /home/user/webapp
   python3 -c "
   import sys
   sys.path.insert(0, '/home/user/webapp')
   from monitor_escape_signals_2h import EscapeSignal2hMonitor
   m = EscapeSignal2hMonitor()
   m.send_alert(100, 283)
   "
   ```

### 问题：监控器频繁重启

1. 检查内存使用：
   ```bash
   pm2 monit
   ```

2. 查看错误日志：
   ```bash
   tail -50 /home/user/webapp/logs/escape_signals_2h_monitor_error.log
   ```

## 📅 更新历史

- **2026-01-14**: 初始版本，阈值80，检查间隔60秒，冷却时间30分钟
