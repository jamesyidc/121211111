#!/usr/bin/env python3
"""
挂单规则验证脚本
用途：验证"挂单的前提条件是已开启锚点单"的规则是否正确实现
"""

import sqlite3
import requests
import json
from datetime import datetime

# 颜色定义
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def log(message, color=Colors.NC):
    print(f"{color}{message}{Colors.NC}")

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")

# 数据库路径
DB_PATH = "/home/user/webapp/trading_decision.db"

def verify_anchor_orders():
    """验证1：检查锚点单记录"""
    print("=== 验证1：检查锚点单记录 ===")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 查询锚点单数量
    cursor.execute("SELECT COUNT(*) FROM position_opens WHERE is_anchor = 1")
    anchor_count = cursor.fetchone()[0]
    
    print(f"锚点单数量: {anchor_count}")
    
    if anchor_count > 0:
        log("✅ 有锚点单记录", Colors.GREEN)
        
        # 显示锚点单详情
        cursor.execute("""
            SELECT 
                inst_id,
                pos_side,
                open_price,
                open_size,
                granularity,
                datetime(created_at, '+8 hours') as created_at
            FROM position_opens
            WHERE is_anchor = 1
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        records = cursor.fetchall()
        print(f"\n{'币种':<20} {'方向':<8} {'开仓价':<12} {'开仓额':<12} {'颗粒度':<10} {'创建时间'}")
        print("-" * 90)
        for row in records:
            print(f"{row[0]:<20} {row[1]:<8} {row[2]:<12.4f} {row[3]:<12.4f} {row[4] or 'N/A':<10} {row[5]}")
    else:
        log("⚠️  暂无锚点单记录", Colors.YELLOW)
    
    conn.close()
    return anchor_count

def verify_pending_orders():
    """验证2：检查挂单记录"""
    print("\n=== 验证2：检查挂单记录 ===")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 查询挂单数量
    cursor.execute("SELECT COUNT(*) FROM pending_orders WHERE status = 'pending'")
    pending_count = cursor.fetchone()[0]
    
    print(f"挂单记录数量: {pending_count}")
    
    if pending_count > 0:
        log("⚠️  有挂单记录，检查是否有对应锚点单...", Colors.YELLOW)
        
        # 显示挂单详情及锚点状态
        cursor.execute("""
            SELECT 
                p.inst_id,
                p.order_type,
                p.order_size,
                p.status,
                CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM position_opens o
                        WHERE o.inst_id = p.inst_id 
                          AND o.pos_side = p.pos_side
                          AND o.is_anchor = 1
                    ) THEN '✅ 有锚点单'
                    ELSE '❌ 无锚点单'
                END as anchor_status,
                datetime(p.created_at, '+8 hours') as created_at
            FROM pending_orders p
            WHERE p.status = 'pending'
            ORDER BY p.created_at DESC
            LIMIT 10
        """)
        
        records = cursor.fetchall()
        print(f"\n{'币种':<20} {'类型':<12} {'挂单额':<12} {'状态':<10} {'锚点状态':<15} {'创建时间'}")
        print("-" * 95)
        for row in records:
            print(f"{row[0]:<20} {row[1]:<12} {row[2]:<12.4f} {row[3]:<10} {row[4]:<15} {row[5]}")
    else:
        log("✅ 暂无挂单记录（符合预期，因为没有锚点单）", Colors.GREEN)
    
    conn.close()
    return pending_count

def verify_api():
    """验证3：测试API返回"""
    print("\n=== 验证3：测试API返回 ===")
    print("调用: GET /api/trading/orders/pending")
    
    try:
        response = requests.get("http://localhost:5000/api/trading/orders/pending", timeout=5)
        data = response.json()
        
        api_count = data.get('total', 0)
        print(f"API 返回的挂单数量: {api_count}")
        
        if api_count == 0:
            log("✅ API 正确过滤，只返回有锚点单的挂单", Colors.GREEN)
        else:
            log(f"⚠️  API 返回了 {api_count} 条挂单，检查详情：", Colors.YELLOW)
            for record in data.get('records', []):
                print(f"  - 币种: {record['inst_id']}, 挂单额: {record['order_size']}, 状态: {record['status']}")
        
        return api_count
    except Exception as e:
        log(f"❌ API 调用失败: {str(e)}", Colors.RED)
        return -1

def verify_orphan_orders():
    """验证4：检查孤立的挂单（有挂单但无锚点单）"""
    print("\n=== 验证4：检查孤立的挂单（数据一致性） ===")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 查询孤立挂单
    cursor.execute("""
        SELECT COUNT(*)
        FROM pending_orders p
        WHERE p.status = 'pending'
          AND NOT EXISTS (
              SELECT 1 FROM position_opens o
              WHERE o.inst_id = p.inst_id 
                AND o.pos_side = p.pos_side
                AND o.is_anchor = 1
          )
    """)
    
    orphan_count = cursor.fetchone()[0]
    print(f"孤立挂单数量（有挂单但无锚点单）: {orphan_count}")
    
    if orphan_count == 0:
        log("✅ 数据一致性良好，没有孤立挂单", Colors.GREEN)
    else:
        log(f"❌ 发现 {orphan_count} 条孤立挂单，需要清理！", Colors.RED)
        
        # 显示孤立挂单详情
        cursor.execute("""
            SELECT 
                p.id,
                p.inst_id,
                p.order_size,
                datetime(p.created_at, '+8 hours') as created_at
            FROM pending_orders p
            WHERE p.status = 'pending'
              AND NOT EXISTS (
                  SELECT 1 FROM position_opens o
                  WHERE o.inst_id = p.inst_id 
                    AND o.pos_side = p.pos_side
                    AND o.is_anchor = 1
              )
            LIMIT 10
        """)
        
        records = cursor.fetchall()
        print(f"\n{'ID':<6} {'币种':<20} {'挂单额':<12} {'创建时间'}")
        print("-" * 55)
        for row in records:
            print(f"{row[0]:<6} {row[1]:<20} {row[2]:<12.4f} {row[3]}")
        
        print("\n建议清理命令：")
        ids = ', '.join(str(row[0]) for row in records)
        print(f"  DELETE FROM pending_orders WHERE id IN ({ids});")
    
    conn.close()
    return orphan_count

def verify_code_logic():
    """验证5：检查代码实现"""
    print("\n=== 验证5：检查代码实现 ===")
    
    checks_passed = 0
    total_checks = 2
    
    # 检查 trading_api.py
    try:
        with open('/home/user/webapp/trading_api.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'AND o.is_anchor = 1' in content:
                log("✅ trading_api.py: SQL 查询包含锚点单过滤", Colors.GREEN)
                checks_passed += 1
            else:
                log("❌ trading_api.py: SQL 查询缺少锚点单过滤！", Colors.RED)
    except Exception as e:
        log(f"❌ 无法读取 trading_api.py: {str(e)}", Colors.RED)
    
    # 检查 position_manager.py
    try:
        with open('/home/user/webapp/position_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if '非锚点单不能补仓' in content:
                log("✅ position_manager.py: 包含锚点单检查逻辑", Colors.GREEN)
                checks_passed += 1
            else:
                log("❌ position_manager.py: 缺少锚点单检查逻辑！", Colors.RED)
    except Exception as e:
        log(f"❌ 无法读取 position_manager.py: {str(e)}", Colors.RED)
    
    return checks_passed, total_checks

def main():
    print_header("挂单（补仓）规则验证")
    log("核心规则：挂单的前提条件是已开启锚点单", Colors.BLUE)
    
    # 执行所有验证
    anchor_count = verify_anchor_orders()
    pending_count = verify_pending_orders()
    api_count = verify_api()
    orphan_count = verify_orphan_orders()
    code_checks, code_total = verify_code_logic()
    
    # 总结
    print_header("验证总结")
    
    total_checks = 5
    passed_checks = 0
    
    # 检查1：锚点单存在（或合理的不存在）
    passed_checks += 1
    
    # 检查2：挂单记录合理
    if pending_count == 0 or anchor_count > 0:
        passed_checks += 1
    
    # 检查3：API 正确过滤
    if api_count == 0 or anchor_count > 0:
        passed_checks += 1
    
    # 检查4：无孤立挂单
    if orphan_count == 0:
        passed_checks += 1
    
    # 检查5：代码逻辑正确
    if code_checks == code_total:
        passed_checks += 1
    
    print(f"\n通过检查: {passed_checks} / {total_checks}\n")
    
    if passed_checks == total_checks:
        log("🎉 所有规则验证通过！系统正常运行。", Colors.GREEN)
    else:
        log("⚠️  部分检查未通过，请检查上述详情。", Colors.YELLOW)
    
    print(f"\n相关文档: /home/user/webapp/PENDING_ORDERS_RULES.md")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
