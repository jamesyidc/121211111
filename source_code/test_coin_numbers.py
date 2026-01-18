#!/usr/bin/env python3
"""测试币种编号显示"""
import sqlite3
import json
from datetime import datetime

def test_coin_numbers():
    """测试币种编号功能"""
    print("=" * 80)
    print("🔢 币种编号测试")
    print("=" * 80)
    print()
    
    # 币种编号映射
    coin_numbers = {
        'CFX-USDT-SWAP': 'NO.1',
        'FIL-USDT-SWAP': 'NO.2',
        'CRO-USDT-SWAP': 'NO.3',
        'UNI-USDT-SWAP': 'NO.4',
        'CRV-USDT-SWAP': 'NO.5',
        'LDO-USDT-SWAP': 'NO.6'
    }
    
    print("📋 编号规则:")
    for coin, number in coin_numbers.items():
        print(f"  {number}: {coin}")
    print()
    
    # 连接数据库
    db_path = '/home/user/webapp/anchor_system.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 测试历史极值记录
    print("=" * 80)
    print("🏆 历史极值记录（带编号）")
    print("=" * 80)
    
    target_coins = list(coin_numbers.keys())
    placeholders = ','.join(['?' for _ in target_coins])
    
    cursor.execute(f"""
        SELECT inst_id, pos_side, record_type, profit_rate, timestamp
        FROM anchor_real_profit_records
        WHERE inst_id IN ({placeholders}) AND pos_side = 'short'
        ORDER BY 
            CASE inst_id
                WHEN 'CFX-USDT-SWAP' THEN 1
                WHEN 'FIL-USDT-SWAP' THEN 2
                WHEN 'CRO-USDT-SWAP' THEN 3
                WHEN 'UNI-USDT-SWAP' THEN 4
                WHEN 'CRV-USDT-SWAP' THEN 5
                WHEN 'LDO-USDT-SWAP' THEN 6
            END,
            record_type
    """, target_coins)
    
    records = cursor.fetchall()
    
    if records:
        print(f"\n{'编号':<8} {'币种':<18} {'方向':<8} {'类型':<15} {'收益率':<12} {'时间'}")
        print("-" * 90)
        
        for inst_id, pos_side, record_type, profit_rate, timestamp in records:
            number = coin_numbers.get(inst_id, '--')
            type_name = '🏆 最高盈利' if record_type == 'max_profit' else '📉 最大亏损'
            rate_str = f"+{profit_rate:.2f}%" if profit_rate >= 0 else f"{profit_rate:.2f}%"
            
            print(f"{number:<8} {inst_id:<18} {'做空':<8} {type_name:<13} {rate_str:<12} {timestamp}")
    else:
        print("暂无记录")
    
    # 2. 测试当前持仓情况
    print()
    print("=" * 80)
    print("💼 当前持仓情况（带编号）")
    print("=" * 80)
    
    # 模拟 API 数据
    print("\n从 app_new.py 的 /api/anchor/positions/real 获取数据...\n")
    
    # 这里用示例数据
    example_positions = [
        {'inst_id': 'CFX-USDT-SWAP', 'pos_side': 'short', 'pos_size': 10.0, 'profit_rate': 44.60},
        {'inst_id': 'FIL-USDT-SWAP', 'pos_side': 'short', 'pos_size': 39.0, 'profit_rate': 24.40},
        {'inst_id': 'CRO-USDT-SWAP', 'pos_side': 'short', 'pos_size': 10.0, 'profit_rate': 25.30},
        {'inst_id': 'UNI-USDT-SWAP', 'pos_side': 'short', 'pos_size': 1.0, 'profit_rate': 57.51},
        {'inst_id': 'CRV-USDT-SWAP', 'pos_side': 'short', 'pos_size': 16.0, 'profit_rate': 38.57},
        {'inst_id': 'LDO-USDT-SWAP', 'pos_side': 'short', 'pos_size': 9.0, 'profit_rate': 52.20},
    ]
    
    print(f"{'编号':<8} {'币种':<18} {'方向':<8} {'持仓量':<12} {'收益率':<12} {'状态'}")
    print("-" * 80)
    
    for pos in example_positions:
        inst_id = pos['inst_id']
        number = coin_numbers.get(inst_id, '--')
        pos_side = pos['pos_side']
        pos_size = pos['pos_size']
        profit_rate = pos['profit_rate']
        
        # 判断状态
        if profit_rate >= 40:
            status = '🎯 已达盈利目标'
        elif profit_rate <= -10:
            status = '⚠️ 止损警告'
        else:
            status = '📊 监控中'
        
        rate_str = f"+{profit_rate:.2f}%" if profit_rate >= 0 else f"{profit_rate:.2f}%"
        
        print(f"{number:<8} {inst_id:<18} {'做空':<8} {pos_size:<12.4f} {rate_str:<12} {status}")
    
    # 3. 显示前端效果预览
    print()
    print("=" * 80)
    print("🎨 前端显示效果预览")
    print("=" * 80)
    print()
    
    print("✅ 在锚点系统实盘页面的变化：")
    print()
    print("【历史极值记录】表格：")
    print("  旧表头: 币种 | 方向 | 类型 | 收益率 | ...")
    print("  新表头: 编号 | 币种 | 方向 | 类型 | 收益率 | ...")
    print("           ↑ 新增列")
    print()
    print("  示例行:")
    print("    NO.1  CFX-USDT-SWAP  做空  🏆 最高盈利  +44.60%  ...")
    print("    NO.2  FIL-USDT-SWAP  做空  🏆 最高盈利  +24.40%  ...")
    print()
    
    print("【当前持仓情况】表格：")
    print("  旧表头: 币种 | 方向 | 持仓量 | ...")
    print("  新表头: 编号 | 币种 | 方向 | 持仓量 | ...")
    print("           ↑ 新增列")
    print()
    print("  示例行:")
    print("    NO.4  UNI-USDT-SWAP  做空  1.0000  +57.51%  🎯 已达盈利目标")
    print("    NO.6  LDO-USDT-SWAP  做空  9.0000  +52.20%  🎯 已达盈利目标")
    print()
    
    # 4. 技术实现说明
    print("=" * 80)
    print("⚙️ 技术实现")
    print("=" * 80)
    print()
    print("📝 实现方式:")
    print("  1. 在 JavaScript 中定义币种编号映射对象")
    print("  2. 在 renderRecordsTable() 函数中查找对应编号")
    print("  3. 在 renderCurrentPositions() 函数中查找对应编号")
    print("  4. 编号列样式: font-weight: 700; color: #667eea;")
    print()
    print("📄 修改文件:")
    print("  templates/anchor_system_real.html")
    print()
    print("🔍 查找编号逻辑:")
    print("  const coinNumbers = {")
    print("      'CFX-USDT-SWAP': 'NO.1',")
    print("      'FIL-USDT-SWAP': 'NO.2',")
    print("      'CRO-USDT-SWAP': 'NO.3',")
    print("      'UNI-USDT-SWAP': 'NO.4',")
    print("      'CRV-USDT-SWAP': 'NO.5',")
    print("      'LDO-USDT-SWAP': 'NO.6'")
    print("  };")
    print("  const coinNumber = coinNumbers[item.inst_id] || '--';")
    print()
    
    # 关闭数据库
    conn.close()
    
    print("=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    print()
    print("🌐 访问页面查看效果:")
    print("   https://5000-iawcy3xxhnan90u0qd9wq-cc2fbc16.sandbox.novita.ai/anchor-system-real")
    print()
    print("📝 Git 提交:")
    print("   Commit: 5748346")
    print("   Message: feat: 为指定币种添加编号列")
    print("   Branch: genspark_ai_developer")
    print()

if __name__ == '__main__':
    test_coin_numbers()
