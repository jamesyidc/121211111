#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
止盈规则管理系统
根据市场配置和盈利情况自动计算止盈比例
"""

import sqlite3
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pytz

# 配置
DB_PATH = '/home/user/webapp/trading_decision.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


class TakeProfitRules:
    """止盈规则管理器"""
    
    # 🔴 空单止盈规则
    SHORT_RULES = {
        'allow_long': {  # 允许开多单的情况（市场看空不强烈）
            'name': '空单-允许做多',
            'triggers': [
                {'profit': 10, 'close_percent': 20},   # 盈利10% → 止盈20%
                {'profit': 20, 'close_percent': 25},   # 盈利20% → 止盈25%
                {'profit': 30, 'close_percent': 35},   # 盈利30% → 止盈35%
                {'profit': 40, 'close_percent': 75},   # 盈利40% → 止盈75%
                {'profit': 50, 'close_percent': None, 'keep_amount': 2.0},  # 盈利50% → 留2U
            ]
        },
        'not_allow_long': {  # 不允许开多单的情况（市场强烈看空）
            'name': '空单-不允许做多',
            'triggers': [
                {'profit': 5,  'close_percent': 25},   # 盈利5%  → 止盈25%
                {'profit': 10, 'close_percent': 30},   # 盈利10% → 止盈30%
                {'profit': 20, 'close_percent': 40},   # 盈利20% → 止盈40%
                {'profit': 30, 'close_percent': 50},   # 盈利30% → 止盈50%
                {'profit': 40, 'close_percent': 75},   # 盈利40% → 止盈75%
                {'profit': 50, 'close_percent': None, 'keep_amount': 2.0},  # 盈利50% → 留2U
            ]
        }
    }
    
    # 🟢 多单止盈规则
    LONG_RULES = {
        'allow_long': {  # 允许开多单的情况（市场看多强烈）
            'name': '多单-允许做多',
            'triggers': [
                {'profit': 10, 'close_percent': 20},   # 盈利10% → 止盈20%
                {'profit': 20, 'close_percent': 50},   # 盈利20% → 止盈50%
                {'profit': 30, 'close_percent': 75},   # 盈利30% → 止盈75%
                {'profit': 40, 'close_percent': 100},  # 盈利40% → 全部止盈
            ]
        },
        'not_allow_long': {  # 不允许开多单的情况（市场看多不强烈）
            'name': '多单-不允许做多',
            'triggers': [
                {'profit': 5,  'close_percent': 25},   # 盈利5%  → 止盈25%
                {'profit': 10, 'close_percent': 50},   # 盈利10% → 止盈50%
                {'profit': 20, 'close_percent': 75},   # 盈利20% → 止盈75%
                {'profit': 30, 'close_percent': 75},   # 盈利30% → 止盈75%
                {'profit': 40, 'close_percent': 100},  # 盈利40% → 全部止盈
            ]
        }
    }
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_market_config(self) -> Dict:
        """获取市场配置"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM market_config LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            # 返回默认配置
            return {
                'market_mode': 'manual',
                'market_trend': 'neutral',
                'total_capital': 1000.0,
                'available_open_percent': 60.0,
                'anchor_limit': 200.0,
                'allow_long': False,  # 默认不允许开多单
                'allow_short': True,
                'allow_anchor': True,
                'max_single_coin_percent': 10.0
            }
        
        return {
            'market_mode': row[1],
            'market_trend': row[2],
            'total_capital': row[3],
            'available_open_percent': row[4],
            'anchor_limit': row[5],
            'allow_long': bool(row[6]),
            'allow_short': bool(row[7]),
            'allow_anchor': bool(row[8]),
            'max_single_coin_percent': row[9] if len(row) > 9 else 10.0
        }
    
    def get_take_profit_rule(self, pos_side: str, profit_rate: float, 
                             current_size: float) -> Optional[Dict]:
        """
        获取止盈规则
        
        Args:
            pos_side: 'long' 或 'short'
            profit_rate: 当前盈利率（百分比）
            current_size: 当前持仓总额（USDT）
            
        Returns:
            {
                'should_close': bool,  # 是否应该止盈
                'close_size': float,   # 止盈金额（USDT）
                'close_percent': float,  # 止盈百分比
                'reason': str,         # 止盈原因
                'keep_size': float,    # 保留金额（USDT）
                'rule_name': str       # 规则名称
            }
        """
        # 获取市场配置
        config = self.get_market_config()
        allow_long = config['allow_long']
        
        # 选择规则集
        if pos_side == 'short':
            rules = self.SHORT_RULES['allow_long'] if allow_long else self.SHORT_RULES['not_allow_long']
        else:  # long
            rules = self.LONG_RULES['allow_long'] if allow_long else self.LONG_RULES['not_allow_long']
        
        # 查找已触发的最高级别规则
        triggered_rule = None
        for trigger in rules['triggers']:
            if profit_rate >= trigger['profit']:
                triggered_rule = trigger
            else:
                break  # 规则是按盈利从小到大排序的，第一个未触发就停止
        
        if not triggered_rule:
            return None
        
        # 计算止盈金额
        if triggered_rule.get('keep_amount'):
            # 留固定金额（如2U）
            keep_amount = triggered_rule['keep_amount']
            if current_size <= keep_amount:
                # 当前持仓已经小于等于保留金额，不需要止盈
                return None
            
            close_size = current_size - keep_amount
            close_percent = (close_size / current_size) * 100
            
            return {
                'should_close': True,
                'close_size': close_size,
                'close_percent': close_percent,
                'reason': f"盈利{triggered_rule['profit']}%，留{keep_amount}U其他全部止盈",
                'keep_size': keep_amount,
                'rule_name': rules['name']
            }
        else:
            # 按百分比止盈
            close_percent = triggered_rule['close_percent']
            close_size = current_size * (close_percent / 100)
            keep_size = current_size - close_size
            
            return {
                'should_close': True,
                'close_size': close_size,
                'close_percent': close_percent,
                'reason': f"盈利{triggered_rule['profit']}%，止盈剩余总仓位的{close_percent}%",
                'keep_size': keep_size,
                'rule_name': rules['name']
            }
    
    def get_all_rules_summary(self) -> Dict:
        """获取所有规则摘要"""
        config = self.get_market_config()
        
        return {
            'current_config': {
                'allow_long': config['allow_long'],
                'allow_short': config['allow_short'],
                'market_mode': config['market_mode']
            },
            'short_rules': {
                'allow_long': self.SHORT_RULES['allow_long'],
                'not_allow_long': self.SHORT_RULES['not_allow_long']
            },
            'long_rules': {
                'allow_long': self.LONG_RULES['allow_long'],
                'not_allow_long': self.LONG_RULES['not_allow_long']
            },
            'active_rules': {
                'short': self.SHORT_RULES['allow_long'] if config['allow_long'] else self.SHORT_RULES['not_allow_long'],
                'long': self.LONG_RULES['allow_long'] if config['allow_long'] else self.LONG_RULES['not_allow_long']
            }
        }
    
    def check_take_profit_for_position(self, inst_id: str, pos_side: str) -> Optional[Dict]:
        """
        检查某个仓位是否需要止盈
        
        Args:
            inst_id: 币种ID
            pos_side: 'long' 或 'short'
            
        Returns:
            止盈决策字典，如果不需要止盈则返回None
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # 获取开仓记录
        cursor.execute('''
        SELECT open_price, open_size, open_percent, timestamp 
        FROM position_opens 
        WHERE inst_id = ? AND pos_side = ?
        ORDER BY created_at DESC LIMIT 1
        ''', (inst_id, pos_side))
        
        open_record = cursor.fetchone()
        if not open_record:
            conn.close()
            return None
        
        open_price = open_record[0]
        open_size = open_record[1]
        
        # 获取补仓记录
        cursor.execute('''
        SELECT SUM(add_size), MAX(add_price)
        FROM position_adds
        WHERE inst_id = ? AND pos_side = ?
        ''', (inst_id, pos_side))
        
        add_record = cursor.fetchone()
        conn.close()
        
        # 计算总持仓
        total_size = open_size
        avg_price = open_price
        
        if add_record and add_record[0]:
            total_add_size = add_record[0]
            total_size += total_add_size
            # 这里需要更精确的平均成本计算，暂时简化
            # TODO: 根据每次补仓的价格和数量计算加权平均价
        
        # TODO: 获取当前价格，计算盈利率
        # 这里需要调用OKX API获取实时价格
        # 暂时返回None，等待实现
        
        return None


if __name__ == '__main__':
    # 测试
    tp = TakeProfitRules()
    
    print("=== 止盈规则测试 ===\n")
    
    # 测试1: 空单，允许开多单，盈利15%
    print("测试1: 空单，允许开多单，盈利15%，当前持仓100 USDT")
    result = tp.get_take_profit_rule('short', 15.0, 100.0)
    if result:
        print(f"  规则: {result['rule_name']}")
        print(f"  止盈金额: {result['close_size']:.2f} USDT ({result['close_percent']:.1f}%)")
        print(f"  保留金额: {result['keep_size']:.2f} USDT")
        print(f"  原因: {result['reason']}")
    print()
    
    # 测试2: 空单，不允许开多单，盈利8%
    print("测试2: 空单，不允许开多单（强烈看空），盈利8%，当前持仓100 USDT")
    # 暂时修改配置测试
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('UPDATE market_config SET allow_long = 0')
    conn.commit()
    conn.close()
    
    result = tp.get_take_profit_rule('short', 8.0, 100.0)
    if result:
        print(f"  规则: {result['rule_name']}")
        print(f"  止盈金额: {result['close_size']:.2f} USDT ({result['close_percent']:.1f}%)")
        print(f"  保留金额: {result['keep_size']:.2f} USDT")
        print(f"  原因: {result['reason']}")
    print()
    
    # 测试3: 多单，允许开多单，盈利25%
    print("测试3: 多单，允许开多单（强烈看多），盈利25%，当前持仓100 USDT")
    # 恢复配置
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('UPDATE market_config SET allow_long = 1')
    conn.commit()
    conn.close()
    
    result = tp.get_take_profit_rule('long', 25.0, 100.0)
    if result:
        print(f"  规则: {result['rule_name']}")
        print(f"  止盈金额: {result['close_size']:.2f} USDT ({result['close_percent']:.1f}%)")
        print(f"  保留金额: {result['keep_size']:.2f} USDT")
        print(f"  原因: {result['reason']}")
    print()
    
    # 测试4: 空单，盈利50%，当前持仓10 USDT
    print("测试4: 空单，盈利50%，当前持仓10 USDT（触发留2U规则）")
    result = tp.get_take_profit_rule('short', 50.0, 10.0)
    if result:
        print(f"  规则: {result['rule_name']}")
        print(f"  止盈金额: {result['close_size']:.2f} USDT ({result['close_percent']:.1f}%)")
        print(f"  保留金额: {result['keep_size']:.2f} USDT")
        print(f"  原因: {result['reason']}")
    print()
    
    # 显示所有规则
    print("=== 所有止盈规则摘要 ===")
    summary = tp.get_all_rules_summary()
    print(f"\n当前市场配置:")
    print(f"  允许开多单: {summary['current_config']['allow_long']}")
    print(f"  允许开空单: {summary['current_config']['allow_short']}")
    print(f"  市场模式: {summary['current_config']['market_mode']}")
    
    print(f"\n当前生效的规则:")
    print(f"  空单规则: {summary['active_rules']['short']['name']}")
    print(f"  多单规则: {summary['active_rules']['long']['name']}")
