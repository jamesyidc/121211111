#!/bin/bash
echo "======================================"
echo "K线指标系统API测试 - 修复验证"
echo "======================================"
echo ""

echo "1️⃣ 测试无参数调用（全部数据）"
echo "--------------------------------------"
RESULT1=$(curl -s "http://localhost:5000/api/kline-indicators/latest" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Success:', d.get('success'), '| Count:', d.get('count'))")
echo $RESULT1
echo ""

echo "2️⃣ 测试5分钟周期筛选"
echo "--------------------------------------"
RESULT2=$(curl -s "http://localhost:5000/api/kline-indicators/latest?timeframe=5m" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Success:', d.get('success'), '| Count:', d.get('count'))")
echo $RESULT2
echo ""

echo "3️⃣ 测试BTC币种筛选"
echo "--------------------------------------"
RESULT3=$(curl -s "http://localhost:5000/api/kline-indicators/latest?symbol=BTC-USDT-SWAP" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Success:', d.get('success'), '| Count:', d.get('count'))")
echo $RESULT3
echo ""

echo "4️⃣ 测试组合筛选（BTC + 5分钟）"
echo "--------------------------------------"
RESULT4=$(curl -s "http://localhost:5000/api/kline-indicators/latest?symbol=BTC-USDT-SWAP&timeframe=5m" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Success:', d.get('success'), '| Count:', d.get('count'))")
echo $RESULT4
echo ""

echo "✅ 所有测试完成！"
