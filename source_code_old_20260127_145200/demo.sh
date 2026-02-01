#!/bin/bash
# 演示脚本 - 展示所有新功能

echo "=========================================="
echo "加密货币数据分析系统 - 功能演示"
echo "=========================================="
echo ""

echo "【功能1】按日期+时间查询历史数据"
echo "命令: python3 query_history.py '2025-12-06 13:42'"
echo "------------------------------------------"
python3 query_history.py '2025-12-06 13:42'
echo ""
echo ""

echo "【功能2】生成4指标曲线图"
echo "命令: python3 query_history.py chart '2025-12-05 00:00' '2025-12-06 23:59'"
echo "------------------------------------------"
python3 query_history.py chart '2025-12-05 00:00' '2025-12-06 23:59'
echo ""
echo ""

echo "【功能3】查看生成的图表"
echo "命令: ls -lh chart_*.png"
echo "------------------------------------------"
ls -lh chart_*.png
echo ""
echo ""

echo "【功能4】数据库查询 - 查看所有等级2的币种"
echo "命令: python3 -c \"查询等级2币种\""
echo "------------------------------------------"
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()
cursor.execute("""
    SELECT symbol, ratio1, ratio2, change_24h, snapshot_time
    FROM crypto_coin_data
    WHERE priority_level = '等级2'
    ORDER BY snapshot_time DESC
    LIMIT 5
""")
print("币种    最高占比    最低占比    24h涨幅    时间")
print("-" * 70)
for row in cursor.fetchall():
    print(f"{row[0]:<8} {row[1]:>9} {row[2]:>11} {row[3]:>9.2f}%   {row[4]}")
conn.close()
PYEOF
echo ""
echo ""

echo "=========================================="
echo "演示完成！"
echo ""
echo "更多用法请查看: QUERY_GUIDE.md"
echo "功能总结请查看: FEATURE_SUMMARY.md"
echo "=========================================="
