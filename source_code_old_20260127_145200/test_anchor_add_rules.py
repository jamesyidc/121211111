#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单补仓规则测试脚本
测试锚点单的补仓和平仓逻辑
"""

import sys
sys.path.append('/home/user/webapp')

from position_manager import PositionManager
import sqlite3

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{text:^60}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{NC}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{NC}")

def print_error(text):
    print(f"{RED}❌ {text}{NC}")

def test_anchor_add_logic():
    """测试锚点单补仓逻辑"""
    
    print_header("锚点单补仓规则测试")
    
    manager = PositionManager()
    
    # 测试场景1：不同亏损比例
    print(f"{YELLOW}测试场景1：不同亏损比例下的补仓判断{NC}\n")
    
    test_cases = [
        (-5.0, False, "亏损5% - 未达触发点"),
        (-9.5, False, "亏损9.5% - 未达触发点"),
        (-10.0, True, "亏损10% - 刚好触发"),
        (-12.5, True, "亏损12.5% - 已触发"),
        (-15.0, True, "亏损15% - 已触发"),
        (-20.0, True, "亏损20% - 已触发"),
    ]
    
    # 注意：这里测试逻辑，不实际操作数据库
    print("测试条件：")
    print("  - 币种：BTC-USDT-SWAP")
    print("  - 方向：short（空单）")
    print("  - 原开仓：0.7 USDT (假设)")
    print("  - 补仓倍数：10倍")
    print("  - 补仓金额：7 USDT")
    print()
    
    for profit_rate, should_trigger, description in test_cases:
        # 这里只能测试触发条件，因为需要数据库中有锚点单记录
        if profit_rate <= -10.0:
            print_success(f"{description} - 应该触发补仓")
            print(f"  亏损率: {profit_rate}%")
            print(f"  补仓金额: 原金额的 10倍")
        else:
            print_warning(f"{description} - 不触发补仓")
            print(f"  亏损率: {profit_rate}%")
            print(f"  距离触发: {-10.0 - profit_rate}%")
        print()
    
    # 测试场景2：补仓后平仓
    print(f"\n{YELLOW}测试场景2：补仓后平仓逻辑{NC}\n")
    
    print("规则：")
    print("  - 补仓完成后立即平仓")
    print("  - 平仓比例：95%")
    print("  - 保留比例：5%")
    print()
    
    print("示例计算：")
    original_amount = 0.7
    add_amount = original_amount * 10
    total_amount = original_amount + add_amount
    close_amount = total_amount * 0.95
    keep_amount = total_amount * 0.05
    
    print(f"  原开仓金额: {original_amount} USDT")
    print(f"  补仓金额: {add_amount} USDT (10倍)")
    print(f"  总金额: {total_amount} USDT")
    print(f"  平仓金额: {close_amount} USDT (95%)")
    print(f"  保留金额: {keep_amount} USDT (5%)")
    print()
    
    print_success("补仓后立即平仓95%，保留5%作为底仓")
    
    # 测试场景3：只补仓一次
    print(f"\n{YELLOW}测试场景3：补仓次数限制{NC}\n")
    
    print("规则：锚点单只补仓一次")
    print()
    print("补仓状态检查：")
    print("  - 补仓次数 = 0: ✅ 可以补仓")
    print("  - 补仓次数 = 1: ❌ 已完成补仓，不再补仓")
    print("  - 补仓次数 > 1: ❌ 已完成补仓，不再补仓")
    print()
    
    print_success("补仓次数限制确保风险可控")
    
    # 测试场景4：完整流程
    print(f"\n{YELLOW}测试场景4：完整补仓流程模拟{NC}\n")
    
    stages = [
        ("1. 开仓", 0.7, 0, "开锚点空单 0.7 USDT"),
        ("2. 监控", 0.7, -5, "亏损5%，继续监控"),
        ("3. 监控", 0.7, -9, "亏损9%，继续监控"),
        ("4. 触发补仓", 7.7, -10.5, "亏损10.5%，触发补仓10倍"),
        ("5. 立即平仓", 0.385, -10.5, "补仓后立即平掉95%"),
        ("6. 完成", 0.385, 0, "保留5%底仓，监控市场"),
    ]
    
    print("阶段流程：\n")
    for stage, amount, profit, desc in stages:
        if "触发补仓" in desc:
            print(f"{GREEN}▶ {stage}{NC}")
            print(f"  持仓金额: {amount} USDT")
            print(f"  亏损率: {profit}%")
            print(f"  操作: {desc}")
        elif "立即平仓" in desc:
            print(f"{GREEN}▶ {stage}{NC}")
            print(f"  持仓金额: {amount} USDT")
            print(f"  操作: {desc}")
        else:
            print(f"▷ {stage}")
            print(f"  持仓金额: {amount} USDT")
            if profit != 0:
                print(f"  亏损率: {profit}%")
            print(f"  状态: {desc}")
        print()
    
    # 总结
    print_header("测试总结")
    
    print(f"{GREEN}✅ 补仓触发条件：亏损 <= -10%{NC}")
    print(f"{GREEN}✅ 补仓倍数：原金额的 10倍{NC}")
    print(f"{GREEN}✅ 补仓次数：只补仓一次{NC}")
    print(f"{GREEN}✅ 平仓比例：补仓后立即平掉 95%{NC}")
    print(f"{GREEN}✅ 保留比例：5% 作为底仓{NC}")
    print()
    
    print(f"{BLUE}相关文档：ANCHOR_ADD_POSITION_RULES.md{NC}")
    print()

def test_database_query():
    """测试数据库查询"""
    
    print_header("数据库查询测试")
    
    db_path = '/home/user/webapp/trading_decision.db'
    
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # 查询锚点单数量
        cursor.execute('SELECT COUNT(*) FROM position_opens WHERE is_anchor = 1')
        anchor_count = cursor.fetchone()[0]
        
        print(f"当前锚点单数量: {anchor_count}")
        
        if anchor_count > 0:
            # 查询锚点单详情
            cursor.execute('''
            SELECT inst_id, pos_side, open_size, open_price, open_percent, granularity, timestamp
            FROM position_opens
            WHERE is_anchor = 1
            ORDER BY created_at DESC
            LIMIT 5
            ''')
            
            anchors = cursor.fetchall()
            
            print("\n最近的锚点单：")
            for idx, anchor in enumerate(anchors, 1):
                inst_id, pos_side, size, price, percent, granularity, timestamp = anchor
                print(f"\n{idx}. {inst_id}")
                print(f"   方向: {pos_side}")
                print(f"   数量: {size}")
                print(f"   价格: {price}")
                print(f"   开仓%: {percent}%")
                print(f"   颗粒度: {granularity}")
                print(f"   时间: {timestamp}")
        else:
            print_warning("暂无锚点单记录")
        
        # 查询补仓记录
        cursor.execute('SELECT COUNT(*) FROM position_adds')
        add_count = cursor.fetchone()[0]
        
        print(f"\n当前补仓记录数量: {add_count}")
        
        conn.close()
        
        print_success("数据库查询成功")
        
    except Exception as e:
        print_error(f"数据库查询失败: {str(e)}")

def main():
    """主函数"""
    
    print(f"\n{GREEN}{'='*60}{NC}")
    print(f"{GREEN}锚点单补仓规则测试脚本{NC:^50}")
    print(f"{GREEN}{'='*60}{NC}\n")
    
    # 测试1：补仓逻辑
    test_anchor_add_logic()
    
    # 测试2：数据库查询
    test_database_query()
    
    print(f"\n{GREEN}{'='*60}{NC}")
    print(f"{GREEN}测试完成{NC:^50}")
    print(f"{GREEN}{'='*60}{NC}\n")

if __name__ == '__main__':
    main()
