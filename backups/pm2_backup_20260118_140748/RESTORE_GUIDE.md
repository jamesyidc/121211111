# PM2进程备份恢复指南

**备份时间**: 2026-01-18 14:07:48  
**备份目录**: `/home/user/webapp/backups/pm2_backup_20260118_140748`  
**进程总数**: 20个

---

## 📋 备份内容清单

### 1. PM2进程列表
- `pm2_processes.json` - 完整的进程配置（JSON格式）
- `pm2_processes_pretty.txt` - 可读的进程详情
- `pm2_list.txt` - 进程列表快照

### 2. Ecosystem配置文件
- `ecosystem.config.js` - 主配置文件
- `ecosystem.config.new.js` - 新版配置
- `ecosystem.liquidation1h.config.js` - 1小时爆仓采集器
- `ecosystem.liquidation_alert.config.js` - 爆仓告警监控
- `ecosystem_all_services.config.js` - 所有服务配置
- `ecosystem_data_collectors.config.js` - 数据采集器
- `ecosystem_fear_greed.config.js` - 恐惧贪婪指数
- `ecosystem_flask.config.js` - Flask应用
- `ecosystem_monitor_2h.config.js` - 2小时监控
- `ecosystem_panic_sar.config.js` - Panic和SAR采集器

---

## 🔧 快速恢复方法

### 方法1: 使用PM2内置恢复（推荐）

```bash
# 1. 停止所有当前进程
pm2 delete all

# 2. 恢复进程（从~/.pm2/dump.pm2）
pm2 resurrect

# 3. 验证进程状态
pm2 list
```

### 方法2: 从备份的JSON恢复

```bash
# 1. 切换到备份目录
cd /home/user/webapp/backups/pm2_backup_20260118_140748

# 2. 从JSON启动所有进程
pm2 start pm2_processes.json

# 3. 保存当前进程列表
pm2 save

# 4. 验证进程状态
pm2 list
```

### 方法3: 使用Ecosystem配置文件

```bash
# 1. 复制ecosystem配置回项目目录
cp /home/user/webapp/backups/pm2_backup_20260118_140748/ecosystem*.js /home/user/webapp/

# 2. 启动所有服务
cd /home/user/webapp
pm2 start ecosystem_all_services.config.js

# 3. 保存进程列表
pm2 save

# 4. 设置开机自启
pm2 startup
```

---

## 📊 备份的进程详情

| ID | 进程名称 | 运行时间 | 内存使用 | 状态 |
|----|---------|---------|---------|------|
| 1 | coin-price-tracker | 7m | 30.9mb | online |
| 2 | support-resistance-snapshot | 24h | 16.0mb | online |
| 3 | price-speed-collector | 24h | 67.7mb | online |
| 4 | v1v2-collector | 24h | 30.1mb | online |
| 5 | crypto-index-collector | 24h | 31.2mb | online |
| 6 | okx-day-change-collector | 24h | 30.4mb | online |
| 7 | sar-slope-collector | 3h | 29.2mb | online |
| 8 | liquidation-1h-collector | 24h | 29.2mb | online |
| 9 | anchor-profit-monitor | 24h | 31.1mb | online |
| 10 | escape-signal-monitor | 24h | 37.2mb | online |
| 11 | flask-app | 2m | 389.7mb | online |
| 12 | escape-auto-updater | 21h | 11.5mb | online |
| 13 | sr-levels-updater | 21h | 12.0mb | online |
| 14 | panic-collector | 21h | 29.8mb | online |
| 15 | sar-jsonl-collector | 2h | 48.2mb | online |
| 16 | gdrive-updater | 4h | 35.1mb | online |
| 17 | extreme-market-monitor | 11h | 30.7mb | online |
| 18 | daily-task-runner | 5h | 12.6mb | online |
| 20 | gdrive-detector | 94m | 47.4mb | online |
| 22 | sar-slope-updater | 2h | 14.6mb | online |

**总计**: 20个进程，总内存使用约 **943MB**

---

## ⚠️ 重要注意事项

### 恢复前的检查

1. **检查端口占用**
   ```bash
   # Flask应用使用5000端口
   lsof -i :5000
   
   # 如有占用，先停止
   pm2 delete flask-app
   ```

2. **检查依赖环境**
   ```bash
   # Python环境
   which python3
   python3 --version
   
   # Node.js环境
   which node
   node --version
   
   # PM2版本
   pm2 --version
   ```

3. **检查必要目录**
   ```bash
   # 数据目录
   ls -la /home/user/webapp/data/
   
   # 日志目录
   ls -la /home/user/webapp/logs/
   
   # 配置目录
   ls -la /home/user/webapp/configs/
   ```

### 常见问题处理

**问题1: 进程启动失败**
```bash
# 查看进程日志
pm2 logs <进程名> --lines 50

# 查看错误日志
pm2 logs <进程名> --err --lines 50
```

**问题2: 端口冲突**
```bash
# 查找占用端口的进程
lsof -i :<端口号>

# 停止冲突的进程
pm2 delete <进程名>
```

**问题3: 内存不足**
```bash
# 查看系统内存
free -h

# 重启占用内存大的进程
pm2 restart flask-app
```

---

## 🔄 进程管理命令

### 查看进程
```bash
# 列出所有进程
pm2 list

# 详细信息
pm2 show <进程名>

# 实时监控
pm2 monit
```

### 控制进程
```bash
# 重启单个进程
pm2 restart <进程名>

# 重启所有进程
pm2 restart all

# 停止进程
pm2 stop <进程名>

# 删除进程
pm2 delete <进程名>
```

### 日志管理
```bash
# 查看所有日志
pm2 logs

# 查看特定进程日志
pm2 logs <进程名>

# 清空日志
pm2 flush

# 重载日志
pm2 reloadLogs
```

---

## 📦 完整备份打包

如需将此备份打包到AI Drive：

```bash
# 1. 打包备份目录
cd /home/user/webapp/backups
tar -czf pm2_backup_20260118_140748.tar.gz pm2_backup_20260118_140748/

# 2. 复制到AI Drive（如果挂载）
cp pm2_backup_20260118_140748.tar.gz /mnt/aidrive/pm2_backups/

# 3. 验证备份
tar -tzf pm2_backup_20260118_140748.tar.gz | head -20
```

恢复打包的备份：
```bash
# 1. 解压备份
cd /home/user/webapp/backups
tar -xzf pm2_backup_20260118_140748.tar.gz

# 2. 按照上述方法恢复
cd pm2_backup_20260118_140748
pm2 start pm2_processes.json
```

---

## 📝 验证清单

恢复完成后，请检查以下项目：

- [ ] 所有20个进程都在运行 (`pm2 list`)
- [ ] Flask应用可访问 (端口5000)
- [ ] 数据采集器正常工作
- [ ] 日志输出正常 (`pm2 logs`)
- [ ] 没有错误信息
- [ ] 进程已保存 (`pm2 save`)
- [ ] 开机自启已设置 (`pm2 startup`)

---

## 🆘 紧急恢复

如果系统重启或PM2丢失所有进程：

```bash
# 1. 快速恢复（使用~/.pm2/dump.pm2）
pm2 resurrect

# 如果上述命令失败，使用备份
cd /home/user/webapp/backups/pm2_backup_20260118_140748
pm2 start pm2_processes.json
pm2 save
```

---

**备份创建者**: Claude Code Agent  
**备份系统**: Linux Sandbox  
**备份路径**: `/home/user/webapp/backups/pm2_backup_20260118_140748`  
**备份完整性**: ✅ 已验证

如需帮助，请查看详细文档或联系系统管理员。
