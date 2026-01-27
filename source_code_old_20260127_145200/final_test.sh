#!/bin/bash
echo "========================================"
echo "   1分钟涨跌速系统部署验证"
echo "========================================"
echo ""
echo "【1】页面访问测试"
status1=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/)
echo "  首页: HTTP $status1"
status2=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/price-speed-monitor)
echo "  涨跌速监控页: HTTP $status2"
echo ""
echo "【2】首页模块测试"
curl -s http://localhost:5000/ | grep -q "1分钟涨跌速" && echo "  ✅ 首页包含涨跌速模块" || echo "  ❌ 首页缺少涨跌速模块"
echo ""
echo "【3】API测试"
api_result=$(curl -s http://localhost:5000/api/price-speed/latest)
echo "$api_result" | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'  ✅ API返回成功: {d.get(\"count\",0)}个币种')" 2>/dev/null || echo "  ❌ API返回失败"
echo ""
echo "【4】采集器状态"
ps aux | grep "price_speed_collector" | grep -v grep > /dev/null && echo "  ✅ 采集器运行中" || echo "  ❌ 采集器未运行"
echo ""
echo "【5】数据库状态"
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('price_speed_data.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM latest_price_speed")
count = cursor.fetchone()[0]
print(f"  数据库记录: {count}个币种")
conn.close()
PYEOF
echo ""
echo "【6】最新采集"
tail -3 price_speed_collector.log | grep "本轮采集完成" | tail -1
echo ""
echo "========================================"
