#!/bin/bash
echo "========================================"
echo "  历史数据查询页面涨跌速集成测试"
echo "========================================"
echo ""

echo "【1】页面访问测试"
status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/query)
echo "  查询页面: HTTP $status"
echo ""

echo "【2】页面元素测试"
curl -s http://localhost:5000/query | grep -q "急涨速" && echo "  ✅ 包含'急涨速'统计" || echo "  ❌ 缺少'急涨速'统计"
curl -s http://localhost:5000/query | grep -q "急跌速" && echo "  ✅ 包含'急跌速'统计" || echo "  ❌ 缺少'急跌速'统计"
curl -s http://localhost:5000/query | grep -q "priceSpeedUpCount" && echo "  ✅ 包含上涨计数器" || echo "  ❌ 缺少上涨计数器"
curl -s http://localhost:5000/query | grep -q "loadPriceSpeedData" && echo "  ✅ 包含数据加载函数" || echo "  ❌ 缺少数据加载函数"
echo ""

echo "【3】API端点测试"
api_result=$(curl -s http://localhost:5000/api/price-speed/latest)
echo "$api_result" | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'  ✅ API返回: {d.get(\"count\",0)}个币种数据')" 2>/dev/null || echo "  ❌ API调用失败"
echo ""

echo "【4】涨跌速数据统计"
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('price_speed_data.db')
cursor = conn.cursor()

# 统计各级别
cursor.execute("""
    SELECT 
        SUM(CASE WHEN alert_level LIKE '%up%' AND alert_level != 'normal' THEN 1 ELSE 0 END) as up_count,
        SUM(CASE WHEN alert_level LIKE '%down%' AND alert_level != 'normal' THEN 1 ELSE 0 END) as down_count,
        SUM(CASE WHEN alert_level = 'normal' THEN 1 ELSE 0 END) as normal_count
    FROM latest_price_speed
""")

up, down, normal = cursor.fetchone()
print(f"  急涨速: {up}个")
print(f"  急跌速: {down}个")
print(f"  正常: {normal}个")
conn.close()
PYEOF
echo ""

echo "【5】系统服务状态"
ps aux | grep "price_speed_collector" | grep -v grep > /dev/null && echo "  ✅ 涨跌速采集器运行中" || echo "  ❌ 涨跌速采集器未运行"
ps aux | grep "app_new.py" | grep -v grep > /dev/null && echo "  ✅ Flask应用运行中" || echo "  ❌ Flask应用未运行"
echo ""

echo "========================================"
echo "  测试完成！"
echo "========================================"
