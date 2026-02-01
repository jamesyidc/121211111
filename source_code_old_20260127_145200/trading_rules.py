#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易规则模块 - 止盈、锚点单维护等核心逻辑
"""

import sqlite3
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/trading_decision.db'


class TakeProfitRules:
    """止盈规则"""
    
    def __init__(self, db_path):
        """初始化"""
        self.db_path = db_path
    
    # 允许开多单的情况 - 空单止盈规则
    SHORT_ALLOWED_LONG = [
        {'profit_rate': 10, 'close_percent': 20},
        {'profit_rate': 20, 'close_percent': 25},
        {'profit_rate': 30, 'close_percent': 35},
        {'profit_rate': 40, 'close_percent': 75},
        {'profit_rate': 50, 'close_percent': 100, 'keep_size': 2}  # 留2U
    ]
    
    # 不允许开多单的情况 - 空单止盈规则
    SHORT_NOT_ALLOWED_LONG = [
        {'profit_rate': 5, 'close_percent': 25},
        {'profit_rate': 10, 'close_percent': 30},
        {'profit_rate': 20, 'close_percent': 40},
        {'profit_rate': 30, 'close_percent': 50},
        {'profit_rate': 40, 'close_percent': 75},
        {'profit_rate': 50, 'close_percent': 100, 'keep_size': 2}  # 留2U
    ]
    
    # 允许开多单的情况 - 多单止盈规则
    LONG_ALLOWED = [
        {'profit_rate': 10, 'close_percent': 20},
        {'profit_rate': 20, 'close_percent': 50},
        {'profit_rate': 30, 'close_percent': 75},
        {'profit_rate': 40, 'close_percent': 100}  # 全部止盈
    ]
    
    # 不允许开多单的情况 - 多单止盈规则
    LONG_NOT_ALLOWED = [
        {'profit_rate': 5, 'close_percent': 25},
        {'profit_rate': 10, 'close_percent': 50},
        {'profit_rate': 20, 'close_percent': 75},
        {'profit_rate': 30, 'close_percent': 75},
        {'profit_rate': 40, 'close_percent': 100}  # 全部止盈
    ]
    
    @staticmethod
    def get_take_profit_decision(pos_side, profit_rate, current_size, allow_long):
        """
        获取止盈决策
        
        Args:
            pos_side: 持仓方向（short/long）
            profit_rate: 收益率（%）
            current_size: 当前持仓量（USDT）
            allow_long: 是否允许开多单
            
        Returns:
            dict: 止盈决策 {'should_close': bool, 'close_size': float, 'close_percent': float, 'reason': str}
        """
        if pos_side == 'short':
            rules = TakeProfitRules.SHORT_ALLOWED_LONG if allow_long else TakeProfitRules.SHORT_NOT_ALLOWED_LONG
        else:  # long
            rules = TakeProfitRules.LONG_ALLOWED if allow_long else TakeProfitRules.LONG_NOT_ALLOWED
        
        # 从高到低检查止盈点
        for rule in reversed(rules):
            if profit_rate >= rule['profit_rate']:
                close_percent = rule['close_percent']
                
                if close_percent == 100:
                    # 检查是否需要保留底仓
                    if 'keep_size' in rule and current_size > rule['keep_size']:
                        close_size = current_size - rule['keep_size']
                        actual_percent = (close_size / current_size) * 100
                        return {
                            'should_close': True,
                            'close_size': close_size,
                            'close_percent': actual_percent,
                            'keep_size': rule['keep_size'],
                            'reason': f"收益率达到{rule['profit_rate']}%，止盈{actual_percent:.1f}%，保留{rule['keep_size']}U底仓"
                        }
                    else:
                        # 全部止盈
                        return {
                            'should_close': True,
                            'close_size': current_size,
                            'close_percent': 100,
                            'reason': f"收益率达到{rule['profit_rate']}%，全部止盈"
                        }
                else:
                    # 按百分比止盈
                    close_size = current_size * (close_percent / 100)
                    return {
                        'should_close': True,
                        'close_size': close_size,
                        'close_percent': close_percent,
                        'reason': f"收益率达到{rule['profit_rate']}%，止盈剩余仓位的{close_percent}%"
                    }
        
        # 未达到止盈条件
        return {
            'should_close': False,
            'close_size': 0,
            'close_percent': 0,
            'reason': '未达到止盈条件'
        }
    
    def save_decision(self, inst_id, pos_side, action, decision_type, current_size, 
                     target_size, close_size, close_percent, profit_rate, current_price, 
                     reason, executed=0):
        """保存交易决策记录"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            INSERT INTO trading_decisions (
                inst_id, pos_side, action, decision_type, current_size, target_size,
                close_size, close_percent, profit_rate, current_price, reason,
                executed, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (inst_id, pos_side, action, decision_type, current_size, target_size,
                  close_size, close_percent, profit_rate, current_price, reason,
                  executed, timestamp))
            
            conn.commit()
            conn.close()
            print(f"✅ 交易决策已保存: {inst_id} - {reason}")
            return True
        except Exception as e:
            print(f"❌ 保存交易决策失败: {e}")
            return False


class AnchorMaintenance:
    """锚点单维护"""
    
    def __init__(self, db_path):
        """初始化"""
        self.db_path = db_path
    
    def save_maintenance(self, inst_id, pos_side, original_size, original_price, 
                        maintenance_price, maintenance_size, profit_rate, action, status):
        """保存锚点单维护记录"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            INSERT INTO anchor_maintenance (
                inst_id, pos_side, original_size, original_price, maintenance_price,
                maintenance_size, profit_rate, action, status, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (inst_id, pos_side, original_size, original_price, maintenance_price,
                  maintenance_size, profit_rate, action, status, timestamp))
            
            conn.commit()
            conn.close()
            print(f"✅ 锚点单维护记录已保存: {inst_id}")
            return True
        except Exception as e:
            print(f"❌ 保存锚点单维护记录失败: {e}")
            return False
    
    def get_latest_maintenance(self, inst_id, pos_side):
        """获取最新的维护记录"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, inst_id, pos_side, original_size, original_price, maintenance_price,
                   maintenance_size, profit_rate, action, status, timestamp
            FROM anchor_maintenance
            WHERE inst_id = ? AND pos_side = ?
            ORDER BY created_at DESC
            LIMIT 1
            ''', (inst_id, pos_side))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'inst_id': result[1],
                    'pos_side': result[2],
                    'original_size': result[3],
                    'original_price': result[4],
                    'maintenance_price': result[5],
                    'maintenance_size': result[6],
                    'profit_rate': result[7],
                    'action': result[8],
                    'status': result[9],
                    'timestamp': result[10]
                }
            return None
        except Exception as e:
            print(f"❌ 获取维护记录失败: {e}")
            return None
    
    def update_maintenance_status(self, maintenance_id, new_status):
        """更新维护记录状态"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE anchor_maintenance
            SET status = ?
            WHERE id = ?
            ''', (new_status, maintenance_id))
            
            conn.commit()
            conn.close()
            print(f"✅ 维护记录状态已更新: {new_status}")
            return True
        except Exception as e:
            print(f"❌ 更新维护记录状态失败: {e}")
            return False
    
    @staticmethod
    def check_maintenance_needed(position, market_trend):
        """
        检查是否需要维护锚点单
        
        Args:
            position: 持仓信息
            market_trend: 市场趋势（bullish/bearish/neutral）
            
        Returns:
            dict: 维护决策
        """
        inst_id = position.get('instId')
        pos_side = position.get('posSide')
        profit_rate = position.get('profit_rate', 0)
        current_size = position.get('pos_size', 0)
        current_price = position.get('markPx', 0)
        
        # 只有空单才能作为锚点单
        if pos_side != 'short':
            return {
                'need_maintenance': False,
                'reason': '只有空单才能作为锚点单'
            }
        
        # 在多头主导的行情中，锚点单收益率≤-10%时触发维护
        if market_trend == 'bullish' and profit_rate <= -10:
            # 需要维护：在现价买入2倍原仓位
            maintenance_size = current_size * 2
            
            return {
                'need_maintenance': True,
                'action': 'add_position',
                'current_size': current_size,
                'add_size': maintenance_size,
                'target_size': current_size + maintenance_size,
                'add_price': current_price,
                'profit_rate': profit_rate,
                'reason': f'多头行情中锚点单亏损{profit_rate:.2f}%，需要在{current_price}价位加仓{maintenance_size}U'
            }
        
        # 检查是否需要卖出75%（收益率回正后）
        if profit_rate > 0 and current_size > 2:
            # 检查是否有维护记录
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM anchor_maintenance
                WHERE inst_id = ? AND pos_side = ? AND status = 'maintained'
            ''', (inst_id, pos_side))
            has_maintenance = cursor.fetchone()[0] > 0
            conn.close()
            
            if has_maintenance:
                # 收益回正，卖出75%
                sell_size = current_size * 0.75
                keep_size = current_size - sell_size
                
                return {
                    'need_maintenance': True,
                    'action': 'reduce_position',
                    'current_size': current_size,
                    'sell_size': sell_size,
                    'keep_size': keep_size,
                    'profit_rate': profit_rate,
                    'reason': f'收益率回正至{profit_rate:.2f}%，卖出75%仓位（{sell_size}U），保留{keep_size}U'
                }
        
        return {
            'need_maintenance': False,
            'reason': '不需要维护'
        }


def save_trading_decision(decision):
    """保存交易决策到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        INSERT INTO trading_decisions (
            inst_id, pos_side, action, decision_type, current_size, target_size,
            close_size, close_percent, profit_rate, current_price, reason,
            executed, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            decision.get('inst_id'),
            decision.get('pos_side'),
            decision.get('action'),
            decision.get('decision_type'),
            decision.get('current_size', 0),
            decision.get('target_size', 0),
            decision.get('close_size', 0),
            decision.get('close_percent', 0),
            decision.get('profit_rate', 0),
            decision.get('current_price', 0),
            decision.get('reason'),
            0,  # 未执行
            timestamp
        ))
        
        conn.commit()
        conn.close()
        print(f"✅ 交易决策已保存: {decision.get('inst_id')} - {decision.get('reason')}")
        return True
    except Exception as e:
        print(f"❌ 保存交易决策失败: {e}")
        return False


def save_anchor_maintenance(maintenance):
    """保存锚点单维护记录"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        INSERT INTO anchor_maintenance (
            inst_id, pos_side, original_size, original_price, maintenance_price,
            maintenance_size, profit_rate, action, status, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            maintenance.get('inst_id'),
            maintenance.get('pos_side'),
            maintenance.get('original_size', 0),
            maintenance.get('original_price', 0),
            maintenance.get('maintenance_price', 0),
            maintenance.get('maintenance_size', 0),
            maintenance.get('profit_rate', 0),
            maintenance.get('action'),
            maintenance.get('status', 'pending'),
            timestamp
        ))
        
        conn.commit()
        conn.close()
        print(f"✅ 锚点单维护记录已保存: {maintenance.get('inst_id')}")
        return True
    except Exception as e:
        print(f"❌ 保存锚点单维护记录失败: {e}")
        return False


if __name__ == '__main__':
    print("=" * 80)
    print("交易规则模块测试")
    print("=" * 80)
    
    # 测试止盈规则
    print("\n【测试1】空单止盈规则（允许开多单）")
    decision = TakeProfitRules.get_take_profit_decision('short', 42, 100, True)
    print(f"收益率42%，当前100U: {decision}")
    
    print("\n【测试2】空单止盈规则（不允许开多单）")
    decision = TakeProfitRules.get_take_profit_decision('short', 15, 100, False)
    print(f"收益率15%，当前100U: {decision}")
    
    print("\n【测试3】多单止盈规则（允许开多单）")
    decision = TakeProfitRules.get_take_profit_decision('long', 25, 100, True)
    print(f"收益率25%，当前100U: {decision}")
    
    print("\n✅ 测试完成")
