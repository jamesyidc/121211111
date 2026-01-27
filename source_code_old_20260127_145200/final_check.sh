#!/bin/bash
echo "=========================================="
echo "   V1V2系统最终功能验证"
echo "=========================================="
echo ""

# 1. 页面检查
echo "【1】页面可访问性测试"
echo "---"
status1=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/)
echo "首页: HTTP $status1"
status2=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/v1v2-monitor)
echo "V1V2监控页: HTTP $status2"
status3=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/v1v2-settings)
echo "V1V2设置页: HTTP $status3"
echo ""

# 2. 导航按钮检查
echo "【2】导航按钮测试"
echo "---"
curl -s http://localhost:5000/v1v2-monitor | grep -q "返回首页" && echo "✅ V1V2监控页包含'返回首页'按钮" || echo "❌ 缺少'返回首页'按钮"
curl -s http://localhost:5000/v1v2-monitor | grep -q "V1V2设置" && echo "✅ V1V2监控页包含'V1V2设置'按钮" || echo "❌ 缺少'V1V2设置'按钮"
echo ""

# 3. 首页集成检查
echo "【3】首页V1V2模块测试"
echo "---"
curl -s http://localhost:5000/ | grep -q "V1V2成交系统" && echo "✅ 首页包含V1V2模块" || echo "❌ 首页缺少V1V2模块"
curl -s http://localhost:5000/ | grep -q "v1v2-v1-count" && echo "✅ 首页包含V1级别统计" || echo "❌ 缺少V1统计"
curl -s http://localhost:5000/ | grep -q "v1v2-v2-count" && echo "✅ 首页包含V2级别统计" || echo "❌ 缺少V2统计"
echo ""

# 4. API测试
echo "【4】API端点测试"
echo "---"
api1=$(curl -s http://localhost:5000/api/v1v2/latest | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('count',0))")
echo "V1V2数据API: 返回 $api1 个币种"
api2=$(curl -s http://localhost:5000/api/v1v2/settings | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('settings',{})))")
echo "V1V2设置API: 返回 $api2 个币种配置"
echo ""

# 5. 采集器状态
echo "【5】采集器运行状态"
echo "---"
ps aux | grep "v1v2_collector.py" | grep -v grep > /dev/null && echo "✅ V1V2采集器运行中" || echo "❌ V1V2采集器未运行"
ps aux | grep "app_new.py" | grep -v grep > /dev/null && echo "✅ Flask应用运行中" || echo "❌ Flask应用未运行"
echo ""

# 6. 最新数据
echo "【6】最新采集数据"
echo "---"
tail -3 v1v2_collector.log | grep "本轮采集完成" | tail -1
echo ""

# 7. Git状态
echo "【7】Git提交状态"
echo "---"
git log --oneline -1
echo ""

echo "=========================================="
echo "   验证完成！"
echo "=========================================="
