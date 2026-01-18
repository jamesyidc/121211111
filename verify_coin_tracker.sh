#!/bin/bash
# 27币种价格追踪器 - 快速验证脚本

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║          27币种价格追踪器 - 系统验证                              ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查PM2进程
echo "🔍 1. 检查PM2进程状态..."
pm2 status coin-price-tracker | grep "coin-price-tracker"
if [ $? -eq 0 ]; then
    echo "   ✅ PM2进程在线"
else
    echo "   ❌ PM2进程不存在"
    exit 1
fi
echo ""

# 2. 检查数据文件
echo "🔍 2. 检查数据文件..."
JSONL_FILE="data/coin_price_tracker/coin_prices_30min.jsonl"
if [ -f "$JSONL_FILE" ]; then
    LINES=$(wc -l < "$JSONL_FILE")
    echo "   ✅ 数据文件存在"
    echo "   📊 记录数: $LINES"
    
    # 显示最新记录时间和币种数
    LATEST=$(tail -1 "$JSONL_FILE" | jq -r '{time: .collect_time, valid: .valid_coins, total: .total_coins}')
    echo "   📈 最新记录: $LATEST"
else
    echo "   ❌ 数据文件不存在"
    exit 1
fi
echo ""

# 3. 测试API端点
echo "🔍 3. 测试API端点..."

# 测试latest端点
echo "   测试 /api/coin-price-tracker/latest..."
LATEST_API=$(curl -s "http://localhost:5000/api/coin-price-tracker/latest?limit=3")
SUCCESS=$(echo "$LATEST_API" | jq -r '.success')
COUNT=$(echo "$LATEST_API" | jq -r '.count')

if [ "$SUCCESS" = "true" ]; then
    echo "   ✅ latest端点正常"
    echo "   📊 返回记录数: $COUNT"
else
    echo "   ❌ latest端点异常"
    echo "$LATEST_API" | jq '.'
    exit 1
fi
echo ""

# 4. 验证数据质量
echo "🔍 4. 验证数据质量..."
LATEST_RECORD=$(tail -1 "$JSONL_FILE" | jq -r '{
    time: .collect_time,
    base_date: .base_date,
    valid: .valid_coins,
    total: .total_coins
}')

VALID_COUNT=$(tail -1 "$JSONL_FILE" | jq -r '.valid_coins')
TOTAL_COUNT=$(tail -1 "$JSONL_FILE" | jq -r '.total_coins')

if [ "$VALID_COUNT" = "27" ] && [ "$TOTAL_COUNT" = "27" ]; then
    echo "   ✅ 数据质量: 100% (27/27)"
    echo "   📋 最新记录:"
    echo "$LATEST_RECORD" | jq '.'
else
    echo "   ⚠️  数据质量: $VALID_COUNT/$TOTAL_COUNT"
fi
echo ""

# 5. 显示涨跌TOP5
echo "🔍 5. 当前涨跌TOP5..."
tail -1 "$JSONL_FILE" | jq -r '.coins | to_entries[] | {symbol: .key, change: .value.change_pct} | "\(.symbol): \(.change)%"' | sort -t: -k2 -n | tail -5 | tac
echo ""

# 6. 检查日志
echo "🔍 6. 最近日志（最后10行）..."
tail -10 logs/coin_price_tracker.log
echo ""

# 7. 下次采集时间
echo "🔍 7. 下次采集时间..."
tail -5 logs/coin_price_tracker.log | grep "下次采集时间" | tail -1
echo ""

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                    验证完成！                                     ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📚 API端点:"
echo "  - GET /api/coin-price-tracker/latest?limit=N"
echo "  - GET /api/coin-price-tracker/history?start_time=...&end_time=..."
echo ""
echo "🔗 访问地址:"
echo "  https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai"
echo ""
