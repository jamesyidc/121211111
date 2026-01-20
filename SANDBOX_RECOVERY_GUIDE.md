# 沙箱崩溃恢复指南

## 📋 概述

如果沙箱死机崩溃并重启，所有 PM2 进程和 Flask 应用都会停止。本文档提供快速恢复步骤。

---

## 🚨 问题现象

沙箱重启后可能出现的问题：
- ❌ 网页无法访问（Flask 应用未运行）
- ❌ 数据停止更新（PM2 采集器未运行）
- ❌ PM2 进程列表为空

---

## ⚡ 快速恢复（推荐）

### 方法 1：一键启动脚本

```bash
cd /home/user/webapp
bash start_all_services.sh
```

这个脚本会：
1. ✅ 检查并清理现有 PM2 进程
2. ✅ 从 ecosystem.config.cjs 启动所有数据采集器（10个）
3. ✅ 启动 Flask 应用
4. ✅ 保存 PM2 配置
5. ✅ 显示最终服务状态

**预计执行时间**：30-60 秒

---

### 方法 2：PM2 恢复（如果之前已保存配置）

```bash
# 1. 恢复之前保存的 PM2 配置
pm2 resurrect

# 2. 查看进程状态
pm2 list

# 3. 如果 flask-app 没有启动，手动启动
cd /home/user/webapp
pm2 start source_code/app_new.py --name flask-app --interpreter python3
```

**注意**：这个方法只在之前运行过 `pm2 save` 的情况下有效。

---

## 🔧 手动恢复步骤

如果自动脚本失败，可以按照以下步骤手动恢复：

### 步骤 1：启动数据采集器

```bash
cd /home/user/webapp/major-events-system
pm2 start ecosystem.config.cjs
pm2 save
```

这会启动以下采集器：
- major-events-monitor
- anchor-data-collector
- unified-data-collector
- sar-slope-collector
- escape-signal-calculator
- coin-price-tracker
- support-resistance-collector
- panic-wash-collector
- anchor-profit-monitor
- liquidation-1h-collector
- gdrive-detector

### 步骤 2：启动 Flask 应用

```bash
cd /home/user/webapp
pm2 start source_code/app_new.py \
    --name flask-app \
    --interpreter python3 \
    --max-memory-restart 1500M
pm2 save
```

### 步骤 3：验证服务状态

```bash
# 查看所有进程
pm2 list

# 查看日志（确认无错误）
pm2 logs --lines 20 --nostream

# 测试 Flask 应用
curl http://localhost:5000/
```

---

## 🔍 验证清单

恢复后，请逐一验证以下项目：

### 1. PM2 进程检查

```bash
pm2 list
```

**预期结果**：应该看到 **12 个进程**全部 `online`：

| ID | 进程名 | 状态 |
|----|--------|------|
| 0 | major-events-monitor | online |
| 1 | anchor-data-collector | online |
| 2 | unified-data-collector | online |
| 3 | sar-slope-collector | online |
| 4 | escape-signal-calculator | online |
| 5 | coin-price-tracker | online |
| 6 | flask-app | online |
| 7 | support-resistance-collector | online |
| 9 | panic-wash-collector | online |
| 10 | anchor-profit-monitor | online |
| 11 | liquidation-1h-collector | online |
| 12 | gdrive-detector | online |

### 2. Flask 应用检查

```bash
# 测试根路径
curl -I http://localhost:5000/

# 测试 API
curl http://localhost:5000/api/panic/latest
```

**预期结果**：
- HTTP 200 响应
- API 返回 JSON 数据

### 3. 数据采集检查

等待 2-3 分钟后，检查各个系统是否有新数据：

```bash
# 检查 Escape Signal 数据
tail -1 /home/user/webapp/data/escape_signal_jsonl/escape_signal_stats.jsonl

# 检查 Coin Price 数据
tail -1 /home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl

# 检查 Panic 数据
tail -1 /home/user/webapp/data/panic_jsonl/panic_wash_index.jsonl

# 检查 1h 爆仓数据
tail -1 /home/user/webapp/data/liquidation_1h/liquidation_1h.jsonl
```

### 4. 网页访问检查

访问以下 URL，确认页面正常加载：

- **Major Events**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/major-events
- **Escape Signal**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/escape-signal-history
- **Coin Price**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/coin-price-tracker
- **Panic**: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/panic

---

## 🐛 故障排查

### 问题 1：PM2 进程启动失败

**症状**：某些进程显示 `errored` 或 `stopped`

**解决方案**：
```bash
# 查看错误日志
pm2 logs <进程名> --lines 50 --err

# 重启失败的进程
pm2 restart <进程名>

# 如果仍然失败，删除并重新启动
pm2 delete <进程名>
cd /home/user/webapp/major-events-system
pm2 start ecosystem.config.cjs
```

### 问题 2：Flask 应用无法访问

**症状**：`curl http://localhost:5000/` 返回连接失败

**解决方案**：
```bash
# 检查 Flask 进程状态
pm2 list | grep flask-app

# 查看 Flask 日志
pm2 logs flask-app --lines 50

# 重启 Flask
pm2 restart flask-app

# 如果端口被占用
lsof -i:5000
kill -9 <PID>
pm2 restart flask-app
```

### 问题 3：数据停止更新

**症状**：网页数据显示为旧时间

**解决方案**：
```bash
# 检查对应的采集器进程
pm2 list

# 查看采集器日志
pm2 logs <采集器名> --lines 50

# 重启采集器
pm2 restart <采集器名>

# 清除浏览器缓存并刷新页面
```

### 问题 4：内存不足

**症状**：进程频繁重启，系统变慢

**解决方案**：
```bash
# 查看内存使用情况
pm2 list
free -h

# 重启占用内存最大的进程
pm2 restart flask-app

# 如果内存持续不足，调整 max_memory_restart
pm2 delete flask-app
pm2 start source_code/app_new.py \
    --name flask-app \
    --interpreter python3 \
    --max-memory-restart 1000M
```

---

## 📝 常用 PM2 命令

```bash
# 查看所有进程
pm2 list

# 查看实时日志
pm2 logs

# 查看特定进程日志
pm2 logs <进程名>

# 重启所有进程
pm2 restart all

# 重启特定进程
pm2 restart <进程名>

# 停止所有进程
pm2 stop all

# 停止特定进程
pm2 stop <进程名>

# 删除所有进程
pm2 delete all

# 删除特定进程
pm2 delete <进程名>

# 保存当前 PM2 配置
pm2 save

# 恢复保存的 PM2 配置
pm2 resurrect

# 查看进程详细信息
pm2 describe <进程名>

# 查看进程监控
pm2 monit
```

---

## 🔄 定期维护建议

### 每日检查

```bash
# 1. 检查所有进程是否在线
pm2 list

# 2. 检查日志是否有错误
pm2 logs --lines 100 --nostream | grep -i error

# 3. 检查内存使用情况
pm2 list
```

### 每周维护

```bash
# 1. 重启所有进程（释放内存）
pm2 restart all

# 2. 清理日志文件
pm2 flush

# 3. 保存当前配置
pm2 save
```

### 数据备份

```bash
# 备份重要数据目录
tar -czf backup_$(date +%Y%m%d).tar.gz \
    /home/user/webapp/data \
    /home/user/webapp/databases \
    /home/user/webapp/logs

# 或者备份到 AI Drive（如果可用）
cp backup_$(date +%Y%m%d).tar.gz /mnt/aidrive/
```

---

## 📞 支持信息

- **GitHub 仓库**: https://github.com/jamesyidc/121211111
- **Pull Request**: https://github.com/jamesyidc/121211111/pull/1
- **相关文档**:
  - [批量修复总结](./BATCH_FIX_SUMMARY.md)
  - [Escape Signal 修复](./ESCAPE_SIGNAL_FIX_SUMMARY.md)
  - [Coin Price Tracker 修复](./COIN_PRICE_TRACKER_FIX_SUMMARY.md)
  - [Support-Resistance 修复](./SUPPORT_RESISTANCE_FIX_SUMMARY.md)
  - [Panic Wash Index 修复](./PANIC_FIX_SUMMARY.md)

---

## ⚠️ 重要提醒

1. **沙箱重启后**，必须手动执行恢复脚本或 PM2 命令
2. **PM2 配置**会在 `pm2 save` 后保存到 `~/.pm2/dump.pm2`
3. **建议**定期执行 `pm2 save` 保存最新配置
4. **如果沙箱环境支持**，可以考虑将启动脚本添加到系统启动项

---

**最后更新**: 2026-01-20  
**系统状态**: Production Ready
