#!/bin/bash
# K线指标系统快速测试脚本

echo "======================================"
echo "K线指标系统测试"
echo "======================================"
echo ""

echo "1️⃣ 测试采集器状态 API"
echo "--------------------------------------"
curl -s "http://localhost:5000/api/kline-indicators/collector-status" | python3 -m json.tool
echo ""

echo "2️⃣ 测试5分钟指标数据（前3条）"
echo "--------------------------------------"
curl -s "http://localhost:5000/api/kline-indicators/latest?timeframe=5m" | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data['data'][:3], indent=2, ensure_ascii=False))"
echo ""

echo "3️⃣ 测试BTC数据"
echo "--------------------------------------"
curl -s "http://localhost:5000/api/kline-indicators/latest?symbol=BTC-USDT-SWAP" | python3 -m json.tool
echo ""

echo "4️⃣ 在线访问地址"
echo "--------------------------------------"
echo "监控页面: https://5000-iypypqmz2wvn9dmtq7ewn-583b4d74.sandbox.novita.ai/kline-indicators"
echo "API接口: https://5000-iypypqmz2wvn9dmtq7ewn-583b4d74.sandbox.novita.ai/api/kline-indicators/latest"
echo ""

echo "✅ 测试完成！"
