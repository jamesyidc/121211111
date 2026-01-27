#!/bin/bash
# 快速检查 Google Drive 数据源状态

echo "=============================================="
echo "🔍 Google Drive 数据源诊断工具"
echo "=============================================="
echo ""

# 当前日期
TODAY=$(TZ='Asia/Shanghai' date '+%Y-%m-%d')
echo "📅 今天日期 (北京时间): $TODAY"
echo ""

# 调用 API
echo "🌐 正在检查 API 状态..."
RESPONSE=$(curl -s "http://localhost:5000/api/gdrive-monitor/status")

# 提取关键信息
STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data_source_status', 'unknown'))")
MESSAGE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data_source_message', 'N/A'))")
GDRIVE_DATES=$(echo "$RESPONSE" | python3 -c "import sys, json; dates=json.load(sys.stdin).get('gdrive_dates', {}); print(', '.join(f'{k} ({v}个文件)' for k, v in sorted(dates.items(), reverse=True)) if dates else '无数据')")

echo ""
echo "=============================================="
echo "📊 诊断结果"
echo "=============================================="
echo ""
echo "数据源状态: $STATUS"
echo "状态消息:   $MESSAGE"
echo "可用数据:   $GDRIVE_DATES"
echo ""

# 根据状态给出建议
case "$STATUS" in
  "active")
    echo "✅ 数据源正常！"
    ;;
  "stale")
    echo "⚠️  数据源已过时，需要检查外部数据生成程序"
    echo ""
    echo "建议操作："
    echo "1. 检查负责生成 TXT 文件的外部程序是否运行"
    echo "2. 查看 Google Drive 根文件夹是否有新文件"
    echo "3. 检查数据生成程序的日志"
    ;;
  "empty")
    echo "❌ Google Drive 中没有任何数据文件"
    ;;
  "error")
    echo "❌ 无法访问 Google Drive，请检查网络连接"
    ;;
  *)
    echo "❓ 状态未知"
    ;;
esac

echo ""
echo "=============================================="
echo "🌐 查看详细监控页面："
echo "https://5000-iypypqmz2wvn9dmtq7ewn-583b4d74.sandbox.novita.ai/gdrive-monitor-status"
echo "=============================================="
