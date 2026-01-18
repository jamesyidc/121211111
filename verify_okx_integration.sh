#!/bin/bash
# OKX集成功能验证脚本

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║           OKX 27币种涨跌指标 - 功能验证                          ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

BASE_URL="http://localhost:5000"

# 1. 验证SAR斜率API
echo "1️⃣  验证SAR斜率JSONL端点..."
RESPONSE=$(curl -s "${BASE_URL}/api/sar-slope/latest-jsonl")
SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
COUNT=$(echo "$RESPONSE" | jq -r '.data | length')

if [ "$SUCCESS" = "true" ] && [ "$COUNT" -gt 0 ]; then
    echo "   ✅ SAR斜率API正常 (返回${COUNT}条记录)"
    BULLISH=$(echo "$RESPONSE" | jq '[.data[] | select(.sar_position == "bullish")] | length')
    BEARISH=$(echo "$RESPONSE" | jq '[.data[] | select(.sar_position == "bearish")] | length')
    echo "   📊 偏多: ${BULLISH}个 | 偏空: ${BEARISH}个"
else
    echo "   ❌ SAR斜率API异常"
fi
echo ""

# 2. 验证OKX涨跌API
echo "2️⃣  验证OKX涨跌数据端点..."
RESPONSE=$(curl -s "${BASE_URL}/api/okx-day-change/latest?limit=10")
SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
COUNT=$(echo "$RESPONSE" | jq -r '.count')

if [ "$SUCCESS" = "true" ] && [ "$COUNT" -gt 0 ]; then
    echo "   ✅ OKX涨跌API正常 (返回${COUNT}条记录)"
    LATEST_TIME=$(echo "$RESPONSE" | jq -r '.data[-1].record_time')
    TOTAL_CHANGE=$(echo "$RESPONSE" | jq -r '.data[-1].total_change')
    echo "   📊 最新时间: ${LATEST_TIME}"
    echo "   📊 总涨跌: ${TOTAL_CHANGE}%"
else
    echo "   ❌ OKX涨跌API异常"
fi
echo ""

# 3. 验证数据文件
echo "3️⃣  验证数据文件..."
OKX_FILE="/home/user/webapp/data/okx_trading_jsonl/okx_day_change.jsonl"
if [ -f "$OKX_FILE" ]; then
    LINES=$(wc -l < "$OKX_FILE")
    FIRST_TIME=$(head -1 "$OKX_FILE" | jq -r '.record_time')
    LAST_TIME=$(tail -1 "$OKX_FILE" | jq -r '.record_time')
    echo "   ✅ 数据文件存在"
    echo "   📊 记录数: ${LINES}"
    echo "   📊 时间范围: ${FIRST_TIME} ~ ${LAST_TIME}"
else
    echo "   ❌ 数据文件不存在"
fi
echo ""

# 4. 验证PM2进程
echo "4️⃣  验证PM2进程状态..."
OKX_COLLECTOR=$(pm2 jlist | jq -r '.[] | select(.name == "okx-day-change-collector") | .pm2_env.status')
FLASK_APP=$(pm2 jlist | jq -r '.[] | select(.name == "flask-app") | .pm2_env.status')

if [ "$OKX_COLLECTOR" = "online" ]; then
    echo "   ✅ OKX采集器运行中"
else
    echo "   ❌ OKX采集器未运行"
fi

if [ "$FLASK_APP" = "online" ]; then
    echo "   ✅ Flask应用运行中"
else
    echo "   ❌ Flask应用未运行"
fi
echo ""

# 5. 验证前端页面
echo "5️⃣  验证前端页面..."
ANCHOR_PAGE=$(curl -s "${BASE_URL}/anchor-system-real" | grep -c "OKX 27币种总涨跌")
ESCAPE_PAGE=$(curl -s "${BASE_URL}/escape-signal-history" | grep -c "OKX 27币种总涨跌")

if [ "$ANCHOR_PAGE" -gt 0 ]; then
    echo "   ✅ anchor-system-real页面已集成OKX曲线"
else
    echo "   ❌ anchor-system-real页面未集成OKX曲线"
fi

if [ "$ESCAPE_PAGE" -gt 0 ]; then
    echo "   ✅ escape-signal-history页面已集成OKX曲线"
else
    echo "   ❌ escape-signal-history页面未集成OKX曲线"
fi
echo ""

# 6. 回填进度检查
echo "6️⃣  回填进度检查..."
BACKFILL_LOG="/home/user/webapp/logs/okx_backfill.log"
if [ -f "$BACKFILL_LOG" ]; then
    LAST_LINE=$(tail -3 "$BACKFILL_LOG" | head -1)
    echo "   📊 最新回填: $LAST_LINE"
else
    echo "   ⚠️  回填日志不存在"
fi
echo ""

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                         验证完成                                  ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 访问地址:"
echo "   主页面: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/anchor-system-real"
echo "   历史页面: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history"
echo ""
