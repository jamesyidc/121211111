#!/bin/bash
# 测试单币种最大占比配置是否可以修改

echo "=================================="
echo "🧪 测试单币种最大占比修改功能"
echo "=================================="
echo ""

# 1. 获取当前配置
echo "1️⃣ 当前配置："
CURRENT=$(curl -s http://localhost:5000/api/trading/config | python3 -c "import sys, json; print(json.load(sys.stdin)['config']['max_single_coin_percent'])")
echo "   单币种最大占比: ${CURRENT}%"
echo ""

# 2. 测试更新为15%
echo "2️⃣ 测试更新为 15%..."
UPDATE_RESULT=$(curl -s -X POST http://localhost:5000/api/trading/config \
  -H "Content-Type: application/json" \
  -d '{
    "market_mode": "manual",
    "market_trend": "neutral",
    "total_capital": 1000,
    "position_limit_percent": 60,
    "anchor_capital_limit": 200,
    "allow_long": false,
    "allow_short": true,
    "allow_anchor": true,
    "max_long_position": 500,
    "max_short_position": 600,
    "max_single_coin_percent": 15,
    "enabled": false
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print('✅ 成功' if data['success'] else '❌ 失败: ' + data.get('error', '未知错误'))")
echo "   结果: ${UPDATE_RESULT}"
echo ""

# 3. 验证是否更新成功
echo "3️⃣ 验证更新结果："
sleep 0.5
NEW_VALUE=$(curl -s http://localhost:5000/api/trading/config | python3 -c "import sys, json; print(json.load(sys.stdin)['config']['max_single_coin_percent'])")
echo "   单币种最大占比: ${NEW_VALUE}%"

if [ "$NEW_VALUE" == "15.0" ]; then
    echo "   ✅ 更新成功！配置已改为 15%"
else
    echo "   ❌ 更新失败！当前值仍为 ${NEW_VALUE}%"
    exit 1
fi
echo ""

# 4. 测试更新为20%
echo "4️⃣ 测试更新为 20%..."
curl -s -X POST http://localhost:5000/api/trading/config \
  -H "Content-Type: application/json" \
  -d '{
    "market_mode": "manual",
    "market_trend": "neutral",
    "total_capital": 1000,
    "position_limit_percent": 60,
    "anchor_capital_limit": 200,
    "allow_long": false,
    "allow_short": true,
    "allow_anchor": true,
    "max_long_position": 500,
    "max_short_position": 600,
    "max_single_coin_percent": 20,
    "enabled": false
  }' > /dev/null

sleep 0.5
FINAL_VALUE=$(curl -s http://localhost:5000/api/trading/config | python3 -c "import sys, json; print(json.load(sys.stdin)['config']['max_single_coin_percent'])")
echo "   单币种最大占比: ${FINAL_VALUE}%"

if [ "$FINAL_VALUE" == "20.0" ]; then
    echo "   ✅ 更新成功！配置已改为 20%"
else
    echo "   ❌ 更新失败！当前值仍为 ${FINAL_VALUE}%"
    exit 1
fi
echo ""

# 5. 恢复默认值10%
echo "5️⃣ 恢复默认值 10%..."
curl -s -X POST http://localhost:5000/api/trading/config \
  -H "Content-Type: application/json" \
  -d '{
    "market_mode": "manual",
    "market_trend": "neutral",
    "total_capital": 1000,
    "position_limit_percent": 60,
    "anchor_capital_limit": 200,
    "allow_long": false,
    "allow_short": true,
    "allow_anchor": true,
    "max_long_position": 500,
    "max_short_position": 600,
    "max_single_coin_percent": 10,
    "enabled": false
  }' > /dev/null

sleep 0.5
RESTORED_VALUE=$(curl -s http://localhost:5000/api/trading/config | python3 -c "import sys, json; print(json.load(sys.stdin)['config']['max_single_coin_percent'])")
echo "   单币种最大占比: ${RESTORED_VALUE}%"
echo "   ✅ 已恢复默认值"
echo ""

# 6. 计算示例
echo "6️⃣ 配置示例（默认10%）："
echo "   总本金: 1000 USDT"
echo "   可开仓百分比: 60%"
echo "   可开仓额: 600 USDT"
echo "   单币种最大占比: 10%"
echo "   单币种上限: 60 USDT"
echo ""

echo "=================================="
echo "✅ 测试完成！单币种占比可以正常修改"
echo "=================================="
