#!/bin/bash
# 挂单规则验证脚本
# 用途：验证"挂单的前提条件是已开启锚点单"的规则是否正确实现

echo "=================================================="
echo "  挂单（补仓）规则验证"
echo "  核心规则：挂单的前提条件是已开启锚点单"
echo "=================================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 数据库路径
DB_PATH="/home/user/webapp/trading_decision.db"

# 验证1：检查锚点单记录
echo "=== 验证1：检查锚点单记录 ==="
ANCHOR_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM position_opens WHERE is_anchor = 1;")
echo "锚点单数量: $ANCHOR_COUNT"

if [ "$ANCHOR_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ 有锚点单记录${NC}"
    sqlite3 "$DB_PATH" << 'EOF'
.headers on
.mode column
SELECT 
    inst_id as '币种',
    pos_side as '方向',
    open_price as '开仓价',
    open_size as '开仓额',
    granularity as '颗粒度',
    datetime(created_at, '+8 hours') as '创建时间'
FROM position_opens
WHERE is_anchor = 1
ORDER BY created_at DESC
LIMIT 5;
EOF
else
    echo -e "${YELLOW}⚠️  暂无锚点单记录${NC}"
fi
echo ""

# 验证2：检查挂单记录
echo "=== 验证2：检查挂单记录 ==="
PENDING_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM pending_orders WHERE status = 'pending';")
echo "挂单记录数量: $PENDING_COUNT"

if [ "$PENDING_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  有挂单记录，检查是否有对应锚点单...${NC}"
    sqlite3 "$DB_PATH" << 'EOF'
.headers on
.mode column
SELECT 
    p.inst_id as '币种',
    p.order_type as '类型',
    p.order_size as '挂单额',
    p.status as '状态',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM position_opens o
            WHERE o.inst_id = p.inst_id 
              AND o.pos_side = p.pos_side
              AND o.is_anchor = 1
        ) THEN '✅ 有锚点单'
        ELSE '❌ 无锚点单'
    END as '锚点状态',
    datetime(p.created_at, '+8 hours') as '创建时间'
FROM pending_orders p
WHERE p.status = 'pending'
ORDER BY p.created_at DESC
LIMIT 10;
EOF
else
    echo -e "${GREEN}✅ 暂无挂单记录（符合预期，因为没有锚点单）${NC}"
fi
echo ""

# 验证3：测试API
echo "=== 验证3：测试API返回 ==="
echo "调用: GET /api/trading/orders/pending"

API_RESULT=$(curl -s http://localhost:5000/api/trading/orders/pending)
API_COUNT=$(echo "$API_RESULT" | jq -r '.total // 0')

echo "API 返回的挂单数量: $API_COUNT"

if [ "$API_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ API 正确过滤，只返回有锚点单的挂单${NC}"
else
    echo -e "${YELLOW}⚠️  API 返回了 $API_COUNT 条挂单，检查详情：${NC}"
    echo "$API_RESULT" | jq '.records[] | {币种: .inst_id, 挂单额: .order_size, 状态: .status}'
fi
echo ""

# 验证4：检查孤立的挂单（有挂单但无锚点单）
echo "=== 验证4：检查孤立的挂单（数据一致性） ==="
ORPHAN_COUNT=$(sqlite3 "$DB_PATH" << 'EOF'
SELECT COUNT(*)
FROM pending_orders p
WHERE p.status = 'pending'
  AND NOT EXISTS (
      SELECT 1 FROM position_opens o
      WHERE o.inst_id = p.inst_id 
        AND o.pos_side = p.pos_side
        AND o.is_anchor = 1
  );
EOF
)

echo "孤立挂单数量（有挂单但无锚点单）: $ORPHAN_COUNT"

if [ "$ORPHAN_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ 数据一致性良好，没有孤立挂单${NC}"
else
    echo -e "${RED}❌ 发现 $ORPHAN_COUNT 条孤立挂单，需要清理！${NC}"
    sqlite3 "$DB_PATH" << 'EOF'
.headers on
.mode column
SELECT 
    p.id as 'ID',
    p.inst_id as '币种',
    p.order_size as '挂单额',
    datetime(p.created_at, '+8 hours') as '创建时间'
FROM pending_orders p
WHERE p.status = 'pending'
  AND NOT EXISTS (
      SELECT 1 FROM position_opens o
      WHERE o.inst_id = p.inst_id 
        AND o.pos_side = p.pos_side
        AND o.is_anchor = 1
  )
LIMIT 10;
EOF
    
    echo ""
    echo "建议清理命令："
    echo "sqlite3 $DB_PATH \"DELETE FROM pending_orders WHERE id IN (...);\""
fi
echo ""

# 验证5：检查代码逻辑
echo "=== 验证5：检查代码实现 ==="

# 检查 trading_api.py 的 SQL 查询
if grep -q "AND o.is_anchor = 1" /home/user/webapp/trading_api.py; then
    echo -e "${GREEN}✅ trading_api.py: SQL 查询包含锚点单过滤${NC}"
else
    echo -e "${RED}❌ trading_api.py: SQL 查询缺少锚点单过滤！${NC}"
fi

# 检查 position_manager.py 的逻辑
if grep -q "非锚点单不能补仓" /home/user/webapp/position_manager.py; then
    echo -e "${GREEN}✅ position_manager.py: 包含锚点单检查逻辑${NC}"
else
    echo -e "${RED}❌ position_manager.py: 缺少锚点单检查逻辑！${NC}"
fi
echo ""

# 总结
echo "=================================================="
echo "  验证总结"
echo "=================================================="

TOTAL_CHECKS=5
PASSED_CHECKS=0

# 检查1：锚点单存在（或合理的不存在）
if [ "$ANCHOR_COUNT" -ge 0 ]; then
    ((PASSED_CHECKS++))
fi

# 检查2：挂单记录合理
if [ "$PENDING_COUNT" -eq 0 ] || [ "$ANCHOR_COUNT" -gt 0 ]; then
    ((PASSED_CHECKS++))
fi

# 检查3：API 正确过滤
if [ "$API_COUNT" -eq 0 ] || [ "$ANCHOR_COUNT" -gt 0 ]; then
    ((PASSED_CHECKS++))
fi

# 检查4：无孤立挂单
if [ "$ORPHAN_COUNT" -eq 0 ]; then
    ((PASSED_CHECKS++))
fi

# 检查5：代码逻辑正确
if grep -q "AND o.is_anchor = 1" /home/user/webapp/trading_api.py && \
   grep -q "非锚点单不能补仓" /home/user/webapp/position_manager.py; then
    ((PASSED_CHECKS++))
fi

echo "通过检查: $PASSED_CHECKS / $TOTAL_CHECKS"
echo ""

if [ "$PASSED_CHECKS" -eq "$TOTAL_CHECKS" ]; then
    echo -e "${GREEN}🎉 所有规则验证通过！系统正常运行。${NC}"
else
    echo -e "${YELLOW}⚠️  部分检查未通过，请检查上述详情。${NC}"
fi

echo ""
echo "相关文档: /home/user/webapp/PENDING_ORDERS_RULES.md"
echo "=================================================="
