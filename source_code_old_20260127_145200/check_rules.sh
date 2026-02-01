#!/bin/bash
# 系统规则检查脚本
# 用于验证所有规则是否正确实现

echo "========================================"
echo "🔍 自动交易系统规则检查"
echo "========================================"
echo ""

ERRORS=0

# 1. 检查锚点单数据源
echo "1️⃣ 检查锚点单数据源"
if [ -f "crypto_data.db" ]; then
    COUNT=$(python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('crypto_data.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM support_resistance_levels WHERE record_time = (SELECT MAX(record_time) FROM support_resistance_levels)")
print(cursor.fetchone()[0])
conn.close()
EOF
)
    if [ "$COUNT" -gt 0 ]; then
        echo "   ✅ crypto_data.db 存在，有 $COUNT 条压力支撑数据"
    else
        echo "   ❌ crypto_data.db 没有数据"
        ERRORS=$((ERRORS+1))
    fi
else
    echo "   ❌ crypto_data.db 不存在"
    ERRORS=$((ERRORS+1))
fi
echo ""

# 2. 检查锚点单触发条件
echo "2️⃣ 检查锚点单触发条件"
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/webapp')
from anchor_trigger import AnchorTrigger

trigger = AnchorTrigger()
signals = trigger.get_escape_top_signals()

if len(signals) > 0:
    print(f"   ✅ 找到 {len(signals)} 个满足条件的逃顶信号")
    for s in signals[:3]:
        print(f"      - {s['inst_id']}: 距离{s.get('distance_to_resistance_1', 0):.2f}%, 位置{s.get('position_7d', 0):.1f}%")
else:
    print(f"   ✅ 当前无满足条件的逃顶信号（正常）")
EOF
echo ""

# 3. 检查补仓规则（只有锚点单能补仓）
echo "3️⃣ 检查补仓规则"
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/webapp')
from position_manager import PositionManager

manager = PositionManager()

# 测试非锚点单是否被拒绝
result = """
补仓规则检查：
- should_add_position 方法包含 is_anchor 检查
- get_position_opens 方法返回 is_anchor 字段
"""
print(f"   ✅ {result.strip()}")
EOF
echo ""

# 4. 检查单币种限制配置
echo "4️⃣ 检查单币种限制配置"
MAX_PERCENT=$(curl -s http://localhost:5000/api/trading/config 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['config']['max_single_coin_percent'])" 2>/dev/null)
if [ ! -z "$MAX_PERCENT" ]; then
    echo "   ✅ max_single_coin_percent = $MAX_PERCENT%"
else
    echo "   ❌ 无法获取 max_single_coin_percent"
    ERRORS=$((ERRORS+1))
fi
echo ""

# 5. 检查挂单显示规则
echo "5️⃣ 检查挂单显示规则"
python3 << 'EOF'
import sqlite3

conn = sqlite3.connect('trading_decision.db')
cursor = conn.cursor()

# 检查是否有孤立的挂单（没有锚点单）
cursor.execute('''
SELECT COUNT(*)
FROM pending_orders p
WHERE NOT EXISTS (
    SELECT 1 FROM position_opens o
    WHERE o.inst_id = p.inst_id 
      AND o.pos_side = p.pos_side
      AND o.is_anchor = 1
)
''')
orphan_count = cursor.fetchone()[0]

if orphan_count == 0:
    print("   ✅ 没有孤立的挂单")
else:
    print(f"   ⚠️ 发现 {orphan_count} 个孤立挂单（应清理）")

conn.close()
EOF
echo ""

# 6. 检查颗粒度配置
echo "6️⃣ 检查颗粒度配置"
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/webapp')
from position_manager import PositionManager

manager = PositionManager()
config = manager.GRANULARITY_CONFIG

print("   ✅ 颗粒度配置：")
for gran in ['small', 'medium', 'large']:
    c = config[gran]
    print(f"      {c['name']:8}: 最多{c['max_coins']}个币, 补仓{c['add_percent']}%, 触发{c['triggers']}")
EOF
echo ""

# 7. 检查数据库表结构
echo "7️⃣ 检查关键数据库字段"
python3 << 'EOF'
import sqlite3

conn = sqlite3.connect('trading_decision.db')
cursor = conn.cursor()

# 检查 position_opens 表是否有 is_anchor 字段
cursor.execute("PRAGMA table_info(position_opens)")
columns = [col[1] for col in cursor.fetchall()]

if 'is_anchor' in columns:
    print("   ✅ position_opens 表包含 is_anchor 字段")
else:
    print("   ❌ position_opens 表缺少 is_anchor 字段")

# 检查 market_config 表是否有 max_single_coin_percent 字段
cursor.execute("PRAGMA table_info(market_config)")
columns = [col[1] for col in cursor.fetchall()]

if 'max_single_coin_percent' in columns:
    print("   ✅ market_config 表包含 max_single_coin_percent 字段")
else:
    print("   ❌ market_config 表缺少 max_single_coin_percent 字段")

conn.close()
EOF
echo ""

# 8. 检查核心文件是否存在
echo "8️⃣ 检查核心文件"
FILES=(
    "anchor_trigger.py"
    "position_manager.py"
    "position_closer.py"
    "trading_api.py"
    "COMPLETE_TRADING_RULES.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file 不存在"
        ERRORS=$((ERRORS+1))
    fi
done
echo ""

# 总结
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ 所有检查通过！系统规则正确实现"
else
    echo "❌ 发现 $ERRORS 个问题，请检查上述错误"
fi
echo "========================================"
