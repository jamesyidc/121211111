#!/usr/bin/env python3
"""系统状态检查脚本"""

import requests
import json
from datetime import datetime

def check_api(endpoint, name):
    """检查API端点"""
    try:
        url = f"http://localhost:5000/api/trading/{endpoint}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return f"✅ {name}: {data.get('success', False)}"
        else:
            return f"❌ {name}: HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ {name}: {str(e)}"

def main():
    print("=" * 60)
    print("交易系统状态检查")
    print("=" * 60)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 系统配置
    print("【系统配置】")
    try:
        resp = requests.get("http://localhost:5000/api/trading/config", timeout=5)
        config = resp.json()['config']
        print(f"  系统状态: {'✅ 已启用' if config['enabled'] else '❌ 未启用'}")
        print(f"  模拟模式: {'✅ 是' if config['simulation_mode'] else '❌ 否'}")
        print(f"  允许空单: {'✅ 是' if config['allow_short'] else '❌ 否'}")
        print(f"  允许多单: {'✅ 是' if config['allow_long'] else '❌ 否'}")
        print(f"  允许锚点: {'✅ 是' if config['allow_anchor'] else '❌ 否'}")
        print(f"  总资金: {config['total_capital']} USDT")
        print(f"  可开仓比例: {config['position_limit_percent']}%")
    except Exception as e:
        print(f"  ❌ 获取配置失败: {e}")
    
    print("\n【API端点检查】")
    endpoints = [
        ('config', '系统配置'),
        ('positions/opens', '持仓查询'),
        ('stop-profit-loss/decision-logs?limit=1', '止盈止损日志'),
        ('anchor/decision-logs?limit=1', '锚点单日志'),
        ('open/decision-logs?limit=1', '开仓决策日志'),
        ('add/decision-logs?limit=1', '补仓决策日志'),
        ('protect-orders/list?limit=1', '保护挂单'),
        ('auto-close/check', '自动平仓检查'),
    ]
    
    for endpoint, name in endpoints:
        print(f"  {check_api(endpoint, name)}")
    
    # 2. 持仓统计
    print("\n【持仓统计】")
    try:
        resp = requests.get("http://localhost:5000/api/trading/positions/opens", timeout=5)
        positions = resp.json()
        print(f"  持仓数量: {positions['total']} 个")
        if positions['total'] > 0:
            for pos in positions['records'][:5]:
                print(f"    - {pos['inst_id']} {pos['pos_side']} {pos.get('sz', 'N/A')} 张")
    except Exception as e:
        print(f"  ❌ 获取持仓失败: {e}")
    
    # 3. 日志统计
    print("\n【日志统计】")
    log_endpoints = [
        ('stop-profit-loss/decision-logs?limit=100', '止盈止损决策'),
        ('anchor/decision-logs?limit=100', '锚点单决策'),
        ('open/decision-logs?limit=100', '开仓决策'),
        ('add/decision-logs?limit=100', '补仓决策'),
    ]
    
    for endpoint, name in log_endpoints:
        try:
            resp = requests.get(f"http://localhost:5000/api/trading/{endpoint}", timeout=5)
            data = resp.json()
            print(f"  {name}: {data.get('count', 0)} 条")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    
    print("\n" + "=" * 60)
    print("访问地址:")
    print("  交易管理: https://5000-iawcy3xxhnan90u0qd9wq-cc2fbc16.sandbox.novita.ai/trading-manager")
    print("=" * 60)

if __name__ == "__main__":
    main()
