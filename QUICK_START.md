# 🚀 快速启动指南

## 沙箱重启后的快速恢复

如果沙箱崩溃重启，使用以下命令一键恢复所有服务：

```bash
cd /home/user/webapp
bash start_all_services.sh
```

这会自动启动：
- ✅ 10 个数据采集器进程
- ✅ 1 个 Flask Web 应用
- ✅ 保存 PM2 配置

**预计时间**: 30-60 秒

---

## 📚 详细文档

- **[沙箱恢复指南](./SANDBOX_RECOVERY_GUIDE.md)** - 完整的恢复步骤和故障排查
- **[批量修复总结](./BATCH_FIX_SUMMARY.md)** - 所有系统修复的总结
- **[各系统修复报告](./BATCH_FIX_SUMMARY.md#相关文档)** - 各个子系统的详细修复文档

---

## 🔍 快速验证

启动后，验证服务是否正常：

```bash
# 查看所有进程（应该有 11 个 online）
pm2 list

# 测试 Flask 应用
curl http://localhost:5000/

# 查看日志（确认无错误）
pm2 logs --lines 20 --nostream
```

---

## 🌐 访问地址

所有服务正常运行后，可以访问：

| 系统 | URL |
|------|-----|
| Major Events Monitor | https://5000-{YOUR_SANDBOX_ID}.sandbox.novita.ai/major-events |
| Escape Signal History | https://5000-{YOUR_SANDBOX_ID}.sandbox.novita.ai/escape-signal-history |
| Coin Price Tracker | https://5000-{YOUR_SANDBOX_ID}.sandbox.novita.ai/coin-price-tracker |
| Support-Resistance | https://5000-{YOUR_SANDBOX_ID}.sandbox.novita.ai/support-resistance |
| Panic Wash Index | https://5000-{YOUR_SANDBOX_ID}.sandbox.novita.ai/panic |
| 多空单盈利统计 | https://5000-{YOUR_SANDBOX_ID}.sandbox.novita.ai/anchor-profit |

---

## ⚠️ 重要提醒

1. **沙箱每次重启后**都需要手动运行恢复脚本
2. **PM2 配置**已保存，但需要手动执行 `pm2 resurrect` 或运行启动脚本
3. **建议**定期执行 `pm2 save` 保存最新的进程配置

---

## 📞 需要帮助？

查看完整文档：[SANDBOX_RECOVERY_GUIDE.md](./SANDBOX_RECOVERY_GUIDE.md)

GitHub 仓库：https://github.com/jamesyidc/121211111
