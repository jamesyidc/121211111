#!/bin/bash

echo "================================================================================"
echo "📊 加密货币得分系统 API 测试报告"
echo "================================================================================"
echo "测试时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. 测试统计API
echo "1️⃣ 测试统计API: /api/score/statistics"
echo "--------------------------------------------------------------------------------"
curl -s http://localhost:5009/api/score/statistics | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ 更新时间: {data[\"update_time\"]}')
print(f'✅ 统计数据条数: {len(data[\"statistics\"])}')
for stat in data['statistics']:
    print(f'   {stat[\"time_range\"]}: 做多={stat[\"avg_long_score\"]}, 做空={stat[\"avg_short_score\"]}, 差值={stat[\"avg_diff\"]:+.2f} {stat[\"trend\"]}')
" || echo "❌ 统计API测试失败"
echo ""

# 2. 测试币种API
echo "2️⃣ 测试币种API: /api/score/coins"
echo "--------------------------------------------------------------------------------"
curl -s http://localhost:5009/api/score/coins | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ 币种总数: {len(data)}')
print(f'✅ 币种列表: {list(data.keys())[:5]} ...')
# 显示BTC的详细数据
if 'BTC-USDT-SWAP' in data:
    btc_data = data['BTC-USDT-SWAP']
    print(f'✅ BTC数据示例:')
    for time_range, scores in list(btc_data.items())[:3]:
        print(f'   {time_range}: 做多={scores[\"long_score\"]}, 做空={scores[\"short_score\"]}, 差值={scores[\"diff\"]:+.2f}')
" || echo "❌ 币种API测试失败"
echo ""

# 3. 测试数据库
echo "3️⃣ 测试数据库查询"
echo "--------------------------------------------------------------------------------"
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()

# 检查score_history表
cursor.execute('SELECT COUNT(*) FROM score_history')
history_count = cursor.fetchone()[0]
print(f'✅ 得分历史记录数: {history_count}')

# 检查score_statistics表
cursor.execute('SELECT COUNT(*) FROM score_statistics')
stats_count = cursor.fetchone()[0]
print(f'✅ 统计记录数: {stats_count}')

# 显示最新统计
cursor.execute('''
    SELECT time_range, avg_long_score, avg_short_score, avg_diff, coin_count
    FROM score_statistics
    WHERE update_time = (SELECT MAX(update_time) FROM score_statistics)
    ORDER BY time_range
''')
rows = cursor.fetchall()
print(f'✅ 最新统计摘要:')
for row in rows:
    print(f'   {row[0]}: 做多={row[1]:.2f}, 做空={row[2]:.2f}, 差值={row[3]:+.2f}, 币种数={row[4]}')

conn.close()
PYEOF
echo ""

# 4. 服务状态
echo "4️⃣ 服务运行状态"
echo "--------------------------------------------------------------------------------"
if ps aux | grep -q "[p]ython3 score_system.py"; then
    echo "✅ 服务正在运行"
    echo "   进程信息:"
    ps aux | grep "[p]ython3 score_system.py" | awk '{print "   PID: "$2", CPU: "$3"%, MEM: "$4"%"}'
else
    echo "❌ 服务未运行"
fi
echo ""

# 5. 日志检查
echo "5️⃣ 最新日志信息"
echo "--------------------------------------------------------------------------------"
tail -10 score_system.log | grep -E "(更新|采集|完成|ERROR)" || echo "无相关日志"
echo ""

echo "================================================================================"
echo "测试完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"
