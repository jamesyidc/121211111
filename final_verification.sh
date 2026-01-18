#!/bin/bash

echo "================================================================================"
echo "🎯 锚点系统极值监控 - 最终验证报告"
echo "================================================================================"
echo ""

echo "1️⃣ 系统状态检查"
echo "----------------"
pm2 list | grep -E "extreme-monitor|flask-app" | head -2
echo ""

echo "2️⃣ 数据统计"
echo "----------------"
echo "JSONL记录总数: $(wc -l < data/extreme_jsonl/extreme_real.jsonl)"
echo "备份文件数量: $(ls -1 data/extreme_jsonl/*.backup* 2>/dev/null | wc -l)"
echo ""

echo "3️⃣ API验证"
echo "----------------"
curl -s "http://localhost:5000/api/anchor-system/profit-records?trade_mode=real" | \
python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"API响应: ✅\"); print(f\"总记录数: {d['total']}\"); print(f\"数据源: {d['data_source']}\"); print(f\"状态: {'成功' if d['success'] else '失败'}\")"
echo ""

echo "4️⃣ 监控器活动"
echo "----------------"
echo "最近5条日志:"
tail -5 logs/extreme_monitor.log 2>/dev/null || tail -5 /home/user/.pm2/logs/extreme-monitor-out.log
echo ""

echo "5️⃣ 极值更新记录"
echo "----------------"
grep "创新高\|创新低" logs/extreme_monitor.log 2>/dev/null | tail -3 || echo "暂无极值更新"
echo ""

echo "================================================================================"
echo "✅ 验证完成 - $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"
