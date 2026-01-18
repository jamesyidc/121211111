# PM2 进程备份完成

## 📦 备份文件
- **压缩包**: pm2_backup_20260118_140748.tar.gz
- **大小**: 17KB
- **创建时间**: 2026-01-18 14:15
- **位置**: /home/user/webapp/backups/

## 📋 备份内容
1. **20个运行进程的完整配置**
2. **所有 ecosystem 配置文件**
3. **自动恢复脚本 (restore.sh)**
4. **详细恢复指南 (RESTORE_GUIDE.md)**

## 🔄 如何恢复

### 方法1：解压并使用恢复脚本
```bash
cd /home/user/webapp/backups
tar -xzf pm2_backup_20260118_140748.tar.gz
cd pm2_backup_20260118_140748
chmod +x restore.sh
./restore.sh
```

### 方法2：快速查看备份内容
```bash
tar -tzf pm2_backup_20260118_140748.tar.gz
```

### 方法3：解压到指定目录
```bash
tar -xzf pm2_backup_20260118_140748.tar.gz -C /path/to/restore/
```

## 📊 备份的进程清单
- flask-app (主应用)
- coin-price-tracker (币价追踪)
- anchor-profit-monitor (锚点利润监控)
- escape-signal-monitor (逃顶信号监控)
- gdrive-detector (Google Drive检测)
- liquidation-1h-collector (1小时爆仓数据采集)
- panic-collector (恐慌指数采集)
- 及其他13个数据采集/监控进程

**总计**: 20个进程，总内存使用 ~943MB

## ⚠️ 重要提示
1. 恢复前建议先备份当前运行状态
2. 恢复会停止并删除所有当前PM2进程
3. 确保相关配置文件路径正确
4. 恢复后请验证所有进程状态: `pm2 list`

## 📁 文件结构
pm2_backup_20260118_140748.tar.gz
├── pm2_list.txt                          # 进程列表（人类可读）
├── pm2_processes.json                    # 进程详细数据（JSON）
├── pm2_processes_pretty.txt              # 格式化进程信息
├── ecosystem.*.config.js                 # 所有配置文件
├── restore.sh                            # 自动恢复脚本
├── RESTORE_GUIDE.md                      # 恢复指南
└── BACKUP_INFO.txt                       # 备份元信息

---
备份创建者: Claude Code Agent
备份时间: 2026-01-18 14:07:48
系统: Linux Sandbox
