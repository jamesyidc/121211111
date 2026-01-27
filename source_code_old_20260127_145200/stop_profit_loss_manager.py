#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
止盈止损管理模块
负责监控仓位盈亏，按照规则自动执行止盈止损
"""

import sqlite3
from datetime import datetime
import pytz
from typing import Dict, List, Tuple, Optional
import json

# 数据库路径
DB_PATH = '/home/user/webapp/trading_decision.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class StopProfitLossManager:
    """止盈止损管理器"""
    
    # 止盈规则配置
    PROFIT_RULES = {
        'short': {  # 空单
            'allow_long': [  # 允许开多单时
                {'profit_rate': 10, 'close_percent': 20},
                {'profit_rate': 20, 'close_percent': 25},
                {'profit_rate': 30, 'close_percent': 35},
                {'profit_rate': 40, 'close_percent': 75},
                {'profit_rate': 50, 'close_type': 'keep_2u'},  # 留2U
            ],
            'no_long': [  # 不允许开多单时
                {'profit_rate': 5, 'close_percent': 25},
                {'profit_rate': 10, 'close_percent': 30},
                {'profit_rate': 20, 'close_percent': 40},
                {'profit_rate': 30, 'close_percent': 50},
                {'profit_rate': 40, 'close_percent': 75},
                {'profit_rate': 50, 'close_type': 'keep_2u'},  # 留2U
            ]
        },
        'long': {  # 多单
            'allow_long': [  # 允许开多单时
                {'profit_rate': 10, 'close_percent': 20},
                {'profit_rate': 20, 'close_percent': 50},
                {'profit_rate': 30, 'close_percent': 75},
                {'profit_rate': 40, 'close_type': 'close_all'},  # 全部平仓
            ],
            'no_long': [  # 不允许开多单时
                {'profit_rate': 5, 'close_percent': 25},
                {'profit_rate': 10, 'close_percent': 50},
                {'profit_rate': 20, 'close_percent': 75},
                {'profit_rate': 30, 'close_percent': 75},
                {'profit_rate': 40, 'close_type': 'close_all'},  # 全部平仓
            ]
        }
    }
    
    # 止损规则配置
    LOSS_RULES = {
        'short': -30,  # 空单-30%止损
        'long': -20    # 多单-20%止损
    }
    
    def __init__(self):
        """初始化"""
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建止盈止损记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stop_profit_loss_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inst_id TEXT NOT NULL,
                pos_side TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_time TEXT NOT NULL,
                avg_open_price REAL NOT NULL,
                current_price REAL NOT NULL,
                profit_rate REAL NOT NULL,
                profit_amount REAL NOT NULL,
                remaining_position REAL NOT NULL,
                close_percent REAL NOT NULL,
                close_amount REAL NOT NULL,
                after_position REAL NOT NULL,
                decision_log TEXT,
                execution_result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建止盈止损决策日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stop_profit_loss_decision_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inst_id TEXT NOT NULL,
                pos_side TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                action TEXT NOT NULL,
                trigger_time TEXT NOT NULL,
                current_price REAL,
                profit_rate REAL,
                remaining_position REAL,
                close_amount REAL,
                decision_steps TEXT,
                trigger_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_config(self) -> Dict:
        """获取市场配置"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT allow_long, allow_short, enabled, simulation_mode
            FROM market_config
            ORDER BY updated_at DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'allow_long': bool(row[0]),
                'allow_short': bool(row[1]),
                'enabled': bool(row[2]),
                'simulation_mode': bool(row[3])
            }
        
        return {
            'allow_long': False,
            'allow_short': True,
            'enabled': False,
            'simulation_mode': True
        }
    
    def get_all_positions(self) -> List[Dict]:
        """获取所有持仓（排除锚点单）"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 直接使用同步的数据，包括mark_price和profit_rate
        # 排除锚点单：is_anchor = 0 或 NULL
        cursor.execute('''
            SELECT 
                inst_id,
                pos_side,
                open_size as total_size,
                open_price as avg_price,
                mark_price,
                profit_rate,
                upl,
                lever,
                margin,
                is_anchor,
                timestamp as latest_open_time
            FROM position_opens
            WHERE (is_anchor = 0 OR is_anchor IS NULL)
            ORDER BY timestamp DESC
        ''')
        
        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return positions
    
    def get_current_price(self, inst_id: str) -> Optional[float]:
        """获取当前价格（从最新的开仓或补仓记录）"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 尝试从开仓记录获取
        cursor.execute('''
            SELECT open_price
            FROM position_opens
            WHERE inst_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (inst_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return float(row[0])
        
        return None
    
    def calculate_profit_rate(self, pos_side: str, avg_price: float, current_price: float) -> float:
        """计算盈亏率"""
        if pos_side == 'short':
            # 空单：(开仓价 - 当前价) / 开仓价 * 100
            return ((avg_price - current_price) / avg_price) * 100
        else:
            # 多单：(当前价 - 开仓价) / 开仓价 * 100
            return ((current_price - avg_price) / avg_price) * 100
    
    def check_profit_trigger(self, pos_side: str, profit_rate: float, allow_long: bool) -> Optional[Dict]:
        """检查是否触发止盈"""
        # 选择规则集
        rule_key = 'allow_long' if allow_long else 'no_long'
        rules = self.PROFIT_RULES[pos_side][rule_key]
        
        # 找到应该触发的止盈规则（取最高的已达到的规则）
        triggered_rule = None
        for rule in rules:
            if profit_rate >= rule['profit_rate']:
                triggered_rule = rule
            else:
                break
        
        return triggered_rule
    
    def check_loss_trigger(self, pos_side: str, profit_rate: float) -> bool:
        """检查是否触发止损"""
        loss_threshold = self.LOSS_RULES[pos_side]
        return profit_rate <= loss_threshold
    
    def calculate_close_amount(self, remaining_position: float, rule: Dict) -> Tuple[float, float]:
        """计算应该平仓的数量"""
        if 'close_type' in rule:
            if rule['close_type'] == 'keep_2u':
                # 留2U，其他全部平仓
                close_amount = remaining_position - 2
                after_position = 2
            elif rule['close_type'] == 'close_all':
                # 全部平仓
                close_amount = remaining_position
                after_position = 0
        else:
            # 按百分比平仓
            close_percent = rule['close_percent']
            close_amount = remaining_position * (close_percent / 100)
            after_position = remaining_position - close_amount
        
        return round(close_amount, 2), round(after_position, 2)
    
    def scan_positions(self, dry_run: bool = True) -> List[Dict]:
        """扫描所有仓位，检查止盈止损触发"""
        config = self.get_config()
        
        if not config['enabled']:
            return [{
                'status': 'skipped',
                'reason': '系统未启用'
            }]
        
        positions = self.get_all_positions()
        results = []
        
        for pos in positions:
            inst_id = pos['inst_id']
            pos_side = pos['pos_side']
            avg_price = pos['avg_price']
            total_size = pos['total_size']
            
            # 使用同步的mark_price和profit_rate
            current_price = pos.get('mark_price')
            profit_rate = pos.get('profit_rate')
            
            # 如果没有同步数据，尝试获取
            if not current_price:
                current_price = self.get_current_price(inst_id)
            if not current_price:
                continue
            
            # 如果没有profit_rate，计算它
            if profit_rate is None:
                profit_rate = self.calculate_profit_rate(pos_side, avg_price, current_price)
            
            decision_log = []
            
            # 检查止盈
            profit_rule = self.check_profit_trigger(pos_side, profit_rate, config['allow_long'])
            if profit_rule:
                decision_log.append(f"✅ 触发止盈：盈利率{profit_rate:.2f}%达到{profit_rule['profit_rate']}%阈值")
                
                close_amount, after_position = self.calculate_close_amount(total_size, profit_rule)
                
                decision_log.append(f"💰 当前剩余仓位：{total_size:.2f} USDT")
                decision_log.append(f"📊 应该平仓：{close_amount:.2f} USDT ({profit_rule.get('close_percent', 100)}%)")
                decision_log.append(f"📌 平仓后剩余：{after_position:.2f} USDT")
                
                result = {
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'trigger_type': 'profit',
                    'profit_rate': profit_rate,
                    'avg_price': avg_price,
                    'current_price': current_price,
                    'remaining_position': total_size,
                    'close_amount': close_amount,
                    'after_position': after_position,
                    'decision_log': decision_log,
                    'can_execute': True
                }
                
                # 记录决策日志
                self.record_decision_log(
                    inst_id=inst_id,
                    pos_side=pos_side,
                    decision_type='profit',
                    action='close',
                    current_price=current_price,
                    profit_rate=profit_rate,
                    remaining_position=total_size,
                    close_amount=close_amount,
                    decision_steps=decision_log,
                    trigger_reason=f"盈利{profit_rate:.2f}%，触发{profit_rule['profit_rate']}%止盈规则"
                )
                
                results.append(result)
                continue
            
            # 检查止损
            if self.check_loss_trigger(pos_side, profit_rate):
                decision_log.append(f"🛑 触发止损：亏损率{profit_rate:.2f}%达到{self.LOSS_RULES[pos_side]}%阈值")
                decision_log.append(f"💰 当前剩余仓位：{total_size:.2f} USDT")
                decision_log.append(f"⚠️ 全部平仓止损")
                
                result = {
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'trigger_type': 'loss',
                    'profit_rate': profit_rate,
                    'avg_price': avg_price,
                    'current_price': current_price,
                    'remaining_position': total_size,
                    'close_amount': total_size,
                    'after_position': 0,
                    'decision_log': decision_log,
                    'can_execute': True
                }
                
                # 记录决策日志
                self.record_decision_log(
                    inst_id=inst_id,
                    pos_side=pos_side,
                    decision_type='loss',
                    action='close',
                    current_price=current_price,
                    profit_rate=profit_rate,
                    remaining_position=total_size,
                    close_amount=total_size,
                    decision_steps=decision_log,
                    trigger_reason=f"亏损{profit_rate:.2f}%，触发{self.LOSS_RULES[pos_side]}%止损规则"
                )
                
                results.append(result)
        
        return results
    
    def record_decision_log(self, inst_id: str, pos_side: str, decision_type: str,
                          action: str, current_price: float, profit_rate: float,
                          remaining_position: float, close_amount: float,
                          decision_steps: List[str], trigger_reason: str):
        """记录决策日志"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO stop_profit_loss_decision_logs (
                inst_id, pos_side, decision_type, action, trigger_time,
                current_price, profit_rate, remaining_position, close_amount,
                decision_steps, trigger_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inst_id, pos_side, decision_type, action, now,
            current_price, profit_rate, remaining_position, close_amount,
            json.dumps(decision_steps, ensure_ascii=False),
            trigger_reason
        ))
        
        conn.commit()
        conn.close()
    
    def get_decision_logs(self, limit: int = 50) -> List[Dict]:
        """获取决策日志"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM stop_profit_loss_decision_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            log = dict(row)
            # 解析decision_steps
            if log['decision_steps']:
                log['decision_steps'] = json.loads(log['decision_steps'])
            logs.append(log)
        
        conn.close()
        return logs
    
    def execute_close(self, inst_id: str, pos_side: str, close_amount: float,
                     trigger_type: str, profit_rate: float, 
                     current_price: float, avg_price: float) -> Dict:
        """执行平仓（模拟）"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 计算盈亏金额
        if pos_side == 'short':
            profit_amount = close_amount * (avg_price - current_price) / avg_price
        else:
            profit_amount = close_amount * (current_price - avg_price) / avg_price
        
        # 记录止盈止损记录
        cursor.execute('''
            INSERT INTO stop_profit_loss_records (
                inst_id, pos_side, trigger_type, trigger_time,
                avg_open_price, current_price, profit_rate, profit_amount,
                remaining_position, close_percent, close_amount, after_position,
                decision_log, execution_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inst_id, pos_side, trigger_type, now,
            avg_price, current_price, profit_rate, profit_amount,
            close_amount, 100, close_amount, 0,
            '模拟平仓', 'success'
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'inst_id': inst_id,
            'close_amount': close_amount,
            'profit_amount': profit_amount
        }


def test_stop_profit_loss_manager():
    """测试止盈止损管理器"""
    print("🧪 测试止盈止损管理器")
    print("=" * 80)
    
    manager = StopProfitLossManager()
    
    # 测试1：获取配置
    print("\n📋 测试1：获取配置")
    config = manager.get_config()
    print(f"allow_long: {config['allow_long']}")
    print(f"allow_short: {config['allow_short']}")
    print(f"enabled: {config['enabled']}")
    print(f"simulation_mode: {config['simulation_mode']}")
    
    # 测试2：扫描仓位
    print("\n📊 测试2：扫描仓位")
    results = manager.scan_positions(dry_run=True)
    print(f"发现 {len(results)} 个触发机会")
    for result in results:
        if 'inst_id' in result:
            print(f"\n币种: {result['inst_id']}")
            print(f"方向: {result['pos_side']}")
            print(f"类型: {result['trigger_type']}")
            print(f"盈亏率: {result['profit_rate']:.2f}%")
            print(f"应平仓: {result['close_amount']:.2f} USDT")
            print("决策日志:")
            for log in result['decision_log']:
                print(f"  {log}")
    
    # 测试3：获取决策日志
    print("\n📝 测试3：获取决策日志")
    logs = manager.get_decision_logs(limit=10)
    print(f"最近 {len(logs)} 条决策日志")
    
    print("\n✅ 测试完成")


if __name__ == '__main__':
    test_stop_profit_loss_manager()
