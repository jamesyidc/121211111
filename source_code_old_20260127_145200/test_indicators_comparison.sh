#!/bin/bash
# Test and compare indicator data for UNI-USDT-SWAP

echo "=========================================="
echo "UNI-USDT-SWAP 技术指标对比测试"
echo "=========================================="
echo

echo "1. 从API获取5分钟指标数据:"
echo "-------------------------------------------"
curl -s "http://localhost:5000/api/kline-indicators/latest?symbol=UNI-USDT-SWAP&timeframe=5m" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data['success'] and len(data['data']) > 0:
    d = data['data'][0]
    print(f'时间: {d[\"record_time\"]}')
    print(f'价格: \${d[\"current_price\"]}')
    print(f'RSI(14): {d[\"rsi_14\"]:.2f}')
    print(f'SAR: {d[\"sar\"]:.4f} [{d[\"sar_position\"]}]')
    print(f'SAR象限: {d[\"sar_quadrant\"]}')
    print(f'布林带:')
    print(f'  上轨: {d[\"bb_upper\"]:.4f}')
    print(f'  中轨: {d[\"bb_middle\"]:.4f}')
    print(f'  下轨: {d[\"bb_lower\"]:.4f}')
    if d.get('amplitude'):
        print(f'振幅: {d[\"amplitude\"]:.4f}%')
    if d.get('change_pct'):
        print(f'涨跌幅: {d[\"change_pct\"]:.4f}%')
"

echo
echo "2. 从API获取1小时指标数据:"
echo "-------------------------------------------"
curl -s "http://localhost:5000/api/kline-indicators/latest?symbol=UNI-USDT-SWAP&timeframe=1h" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data['success'] and len(data['data']) > 0:
    d = data['data'][0]
    print(f'时间: {d[\"record_time\"]}')
    print(f'价格: \${d[\"current_price\"]}')
    print(f'RSI(14): {d[\"rsi_14\"]:.2f}')
    print(f'SAR: {d[\"sar\"]:.4f} [{d[\"sar_position\"]}]')
    print(f'SAR象限: {d[\"sar_quadrant\"]}')
    print(f'布林带:')
    print(f'  上轨: {d[\"bb_upper\"]:.4f}')
    print(f'  中轨: {d[\"bb_middle\"]:.4f}')
    print(f'  下轨: {d[\"bb_lower\"]:.4f}')
"

echo
echo "3. 数据说明:"
echo "-------------------------------------------"
echo "✅ 数据来源: OKEx K线 API"
echo "✅ 计算方式: TA-Lib专业库"
echo "✅ 计算参数:"
echo "   - RSI: 14周期"
echo "   - SAR: 加速0.02, 最大0.2"
echo "   - 布林带: 20周期, 2倍标准差"
echo "✅ 北京时间记录"
echo

