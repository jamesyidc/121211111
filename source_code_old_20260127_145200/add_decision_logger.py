#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补仓决策日志模块
记录补仓的完整决策过程
"""

import sqlite3
from datetime import datetime
import pytz
from typing import Dict, List, Optional
import json

DB_PATH = '/home/user/webapp/trading_decision.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class AddPositionDecisionLogger:
    """补仓决策日志记录器"""
    
    # 空单补仓规则
    SHORT_ADD_RULES = [
        {
            'stage': 1,
            'max_position': 10,  # 10U以下
            'max_coins': 7,
            'trigger_loss': -2,
            'add_intervals': [-1, -2, -3],
            'add_percent': 1
        },
        {
            'stage': 2,
            'max_position': 20,  # 10-20U
            'max_coins': 2,
            'trigger_loss': -5,
            'add_intervals': [-7, -9],
            'add_percent': 3.5
        },
        {
            'stage': 3,
            'max_position': float('inf'),  # 20U以上
            'max_coins': 1,
            'trigger_loss': -10,
            'add_intervals': [-15, -18, -21],
            'add_percent': 7
        }
    ]
    
    # 多单补仓规则
    LONG_ADD_RULES = {
        'trigger_interval': 0.5,  # 每下跌0.5%补一次
        'max_adds': 3,  # 最多补3次
        'add_percent': 10  # 每次补10%可开仓额
    }
    
    def __init__(self):
        """初始化"""
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建补仓决策日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS add_position_decision_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inst_id TEXT NOT NULL,
                pos_side TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                action TEXT NOT NULL,
                decision_time TEXT NOT NULL,
                current_loss_rate REAL,
                current_position_value REAL,
                stage_info TEXT,
                add_level INTEGER,
                add_price REAL,
                add_amount REAL,
                add_percent REAL,
                after_avg_price REAL,
                after_position_value REAL,
                available_capital REAL,
                decision_steps TEXT,
                trigger_reason TEXT,
                risk_control TEXT,
                result TEXT,
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
            SELECT 
                total_capital, position_limit_percent, enabled, simulation_mode
            FROM market_config
            ORDER BY updated_at DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'total_capital': float(row[0]),
                'position_limit_percent': float(row[1]),
                'enabled': bool(row[2]),
                'simulation_mode': bool(row[3])
            }
        
        return None
    
    def get_position_info(self, inst_id: str, pos_side: str) -> Optional[Dict]:
        """获取持仓信息"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取开仓记录
        cursor.execute('''
            SELECT 
                SUM(open_size) as total_size,
                SUM(open_size * open_price) / SUM(open_size) as avg_price,
                COUNT(*) as add_count,
                MIN(open_price) as min_price,
                MAX(open_price) as max_price
            FROM position_opens
            WHERE inst_id = ? AND pos_side = ? AND status = 'open'
        ''', (inst_id, pos_side))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return {
                'total_size': float(row[0]),
                'avg_price': float(row[1]),
                'add_count': int(row[2]),
                'min_price': float(row[3]),
                'max_price': float(row[4])
            }
        
        return None
    
    def get_current_price(self, inst_id: str) -> Optional[float]:
        """获取当前价格"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT open_price
            FROM position_opens
            WHERE inst_id = ?
            ORDER BY open_time DESC
            LIMIT 1
        ''', (inst_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return float(row[0]) if row else None
    
    def calculate_loss_rate(self, pos_side: str, avg_price: float, current_price: float) -> float:
        """计算亏损率"""
        if pos_side == 'short':
            return ((current_price - avg_price) / avg_price) * 100
        else:
            return ((avg_price - current_price) / avg_price) * 100
    
    def get_short_stage(self, position_value: float) -> Optional[Dict]:
        """获取空单补仓阶段"""
        for rule in self.SHORT_ADD_RULES:
            if position_value < rule['max_position']:
                return rule
        return self.SHORT_ADD_RULES[-1]  # 返回最后一个阶段
    
    def check_short_add_conditions(self, inst_id: str) -> Dict:
        """检查空单补仓条件"""
        decision_steps = []
        
        # 1. 获取配置
        config = self.get_config()
        if not config:
            decision_steps.append("❌ 无法获取系统配置")
            return {
                'can_add': False,
                'reason': '无法获取系统配置',
                'decision_steps': decision_steps
            }
        
        decision_steps.append("✅ 系统配置加载成功")
        
        # 2. 获取持仓信息
        position = self.get_position_info(inst_id, 'short')
        if not position:
            decision_steps.append("❌ 该币种无持仓")
            return {
                'can_add': False,
                'reason': '该币种无持仓',
                'decision_steps': decision_steps
            }
        
        decision_steps.append(f"✅ 持仓信息获取成功")
        decision_steps.append(f"   - 持仓总额: {position['total_size']:.2f} USDT")
        decision_steps.append(f"   - 平均价格: {position['avg_price']:.4f}")
        decision_steps.append(f"   - 已补仓次数: {position['add_count'] - 1}")
        
        # 3. 获取当前价格
        current_price = self.get_current_price(inst_id)
        if not current_price:
            decision_steps.append("❌ 无法获取当前价格")
            return {
                'can_add': False,
                'reason': '无法获取当前价格',
                'decision_steps': decision_steps
            }
        
        # 4. 计算亏损率
        loss_rate = self.calculate_loss_rate('short', position['avg_price'], current_price)
        decision_steps.append(f"✅ 当前亏损率: {loss_rate:.2f}%")
        
        # 5. 判断补仓阶段
        stage = self.get_short_stage(position['total_size'])
        decision_steps.append(f"✅ 当前阶段: Stage {stage['stage']}")
        decision_steps.append(f"   - 阶段仓位上限: {stage['max_position']} USDT")
        decision_steps.append(f"   - 触发亏损率: {stage['trigger_loss']}%")
        decision_steps.append(f"   - 补仓间隔: {stage['add_intervals']}")
        decision_steps.append(f"   - 补仓比例: {stage['add_percent']}%")
        
        # 6. 检查是否达到触发亏损率
        if loss_rate > stage['trigger_loss']:
            decision_steps.append(f"❌ 亏损率 {loss_rate:.2f}% 未达到触发阈值 {stage['trigger_loss']}%")
            return {
                'can_add': False,
                'reason': f'亏损率未达到{stage["trigger_loss"]}%',
                'decision_steps': decision_steps,
                'stage': stage,
                'loss_rate': loss_rate
            }
        
        decision_steps.append(f"✅ 亏损率 {loss_rate:.2f}% 达到触发阈值 {stage['trigger_loss']}%")
        
        # 7. 计算补仓金额
        available_capital = config['total_capital'] * config['position_limit_percent'] / 100
        add_amount = available_capital * stage['add_percent'] / 100
        
        decision_steps.append(f"✅ 补仓金额计算")
        decision_steps.append(f"   - 可开仓额: {available_capital:.2f} USDT")
        decision_steps.append(f"   - 补仓金额: {add_amount:.2f} USDT ({stage['add_percent']}%)")
        
        # 8. 预测补仓后的情况
        after_position = position['total_size'] + add_amount
        after_avg_price = (position['total_size'] * position['avg_price'] + add_amount * current_price) / after_position
        
        decision_steps.append(f"✅ 补仓后预测")
        decision_steps.append(f"   - 补仓后总仓位: {after_position:.2f} USDT")
        decision_steps.append(f"   - 补仓后平均价: {after_avg_price:.4f}")
        
        # 9. 风险控制检查
        stop_loss_distance = -30 - loss_rate  # 距离-30%止损的距离
        decision_steps.append(f"⚠️ 风险控制")
        decision_steps.append(f"   - 当前亏损: {loss_rate:.2f}%")
        decision_steps.append(f"   - 止损线: -30%")
        decision_steps.append(f"   - 距离止损: {abs(stop_loss_distance):.2f}%")
        
        if stop_loss_distance < 5:
            decision_steps.append(f"⚠️ 警告: 距离止损线较近，谨慎补仓")
        
        # 10. 检查补仓间隔
        next_add_level = position['add_count']  # 下一个补仓Level
        if next_add_level > len(stage['add_intervals']):
            decision_steps.append(f"❌ 该阶段补仓次数已达上限")
            return {
                'can_add': False,
                'reason': '该阶段补仓次数已达上限',
                'decision_steps': decision_steps,
                'stage': stage,
                'loss_rate': loss_rate
            }
        
        decision_steps.append(f"🎯 满足所有补仓条件，建议补仓")
        
        return {
            'can_add': True,
            'reason': '满足补仓条件',
            'add_amount': add_amount,
            'add_price': current_price,
            'add_level': next_add_level,
            'after_avg_price': after_avg_price,
            'after_position': after_position,
            'decision_steps': decision_steps,
            'stage': stage,
            'loss_rate': loss_rate,
            'position': position
        }
    
    def check_long_add_conditions(self, inst_id: str) -> Dict:
        """检查多单补仓条件"""
        decision_steps = []
        
        # 1. 获取持仓信息
        position = self.get_position_info(inst_id, 'long')
        if not position:
            decision_steps.append("❌ 该币种无持仓")
            return {
                'can_add': False,
                'reason': '该币种无持仓',
                'decision_steps': decision_steps
            }
        
        decision_steps.append(f"✅ 持仓信息获取成功")
        decision_steps.append(f"   - 持仓总额: {position['total_size']:.2f} USDT")
        decision_steps.append(f"   - 平均价格: {position['avg_price']:.4f}")
        decision_steps.append(f"   - 已补仓次数: {position['add_count'] - 1}")
        
        # 2. 检查补仓次数限制
        if position['add_count'] - 1 >= self.LONG_ADD_RULES['max_adds']:
            decision_steps.append(f"❌ 补仓次数已达上限 {self.LONG_ADD_RULES['max_adds']}")
            return {
                'can_add': False,
                'reason': f'补仓次数已达上限{self.LONG_ADD_RULES["max_adds"]}',
                'decision_steps': decision_steps
            }
        
        # 3. 获取当前价格
        current_price = self.get_current_price(inst_id)
        if not current_price:
            decision_steps.append("❌ 无法获取当前价格")
            return {
                'can_add': False,
                'reason': '无法获取当前价格',
                'decision_steps': decision_steps
            }
        
        # 4. 计算亏损率
        loss_rate = self.calculate_loss_rate('long', position['avg_price'], current_price)
        decision_steps.append(f"✅ 当前亏损率: {loss_rate:.2f}%")
        
        # 5. 检查是否达到补仓间隔
        expected_loss = (position['add_count']) * self.LONG_ADD_RULES['trigger_interval']
        if loss_rate < expected_loss:
            decision_steps.append(f"❌ 亏损率 {loss_rate:.2f}% 未达到 {expected_loss:.2f}%")
            return {
                'can_add': False,
                'reason': f'亏损率未达到{expected_loss:.2f}%',
                'decision_steps': decision_steps,
                'loss_rate': loss_rate
            }
        
        decision_steps.append(f"✅ 亏损率 {loss_rate:.2f}% 达到 {expected_loss:.2f}%")
        
        # 6. 计算补仓金额
        config = self.get_config()
        available_capital = config['total_capital'] * config['position_limit_percent'] / 100
        add_amount = available_capital * self.LONG_ADD_RULES['add_percent'] / 100
        
        decision_steps.append(f"✅ 补仓金额计算")
        decision_steps.append(f"   - 可开仓额: {available_capital:.2f} USDT")
        decision_steps.append(f"   - 补仓金额: {add_amount:.2f} USDT ({self.LONG_ADD_RULES['add_percent']}%)")
        
        # 7. 预测补仓后情况
        after_position = position['total_size'] + add_amount
        after_avg_price = (position['total_size'] * position['avg_price'] + add_amount * current_price) / after_position
        
        decision_steps.append(f"✅ 补仓后预测")
        decision_steps.append(f"   - 补仓后总仓位: {after_position:.2f} USDT")
        decision_steps.append(f"   - 补仓后平均价: {after_avg_price:.4f}")
        
        # 8. 风险控制
        stop_loss_distance = -20 - loss_rate
        decision_steps.append(f"⚠️ 风险控制")
        decision_steps.append(f"   - 当前亏损: {loss_rate:.2f}%")
        decision_steps.append(f"   - 止损线: -20%")
        decision_steps.append(f"   - 距离止损: {abs(stop_loss_distance):.2f}%")
        
        decision_steps.append(f"🎯 满足所有补仓条件，建议补仓")
        
        return {
            'can_add': True,
            'reason': '满足补仓条件',
            'add_amount': add_amount,
            'add_price': current_price,
            'add_level': position['add_count'],
            'after_avg_price': after_avg_price,
            'after_position': after_position,
            'decision_steps': decision_steps,
            'loss_rate': loss_rate,
            'position': position
        }
    
    def record_add_decision(self, inst_id: str, pos_side: str, decision_result: Dict):
        """记录补仓决策日志"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        stage_info = decision_result.get('stage', {})
        
        cursor.execute('''
            INSERT INTO add_position_decision_logs (
                inst_id, pos_side, decision_type, action, decision_time,
                current_loss_rate, current_position_value, stage_info,
                add_level, add_price, add_amount, add_percent,
                after_avg_price, after_position_value, available_capital,
                decision_steps, trigger_reason, risk_control, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inst_id, pos_side, 'add', 'add' if decision_result['can_add'] else 'skip', now,
            decision_result.get('loss_rate'),
            decision_result.get('position', {}).get('total_size'),
            json.dumps(stage_info, ensure_ascii=False) if stage_info else None,
            decision_result.get('add_level'),
            decision_result.get('add_price'),
            decision_result.get('add_amount'),
            stage_info.get('add_percent') if stage_info else self.LONG_ADD_RULES['add_percent'],
            decision_result.get('after_avg_price'),
            decision_result.get('after_position'),
            None,  # available_capital
            json.dumps(decision_result['decision_steps'], ensure_ascii=False),
            decision_result['reason'],
            None,  # risk_control
            'can_add' if decision_result['can_add'] else 'skip'
        ))
        
        conn.commit()
        conn.close()
    
    def get_decision_logs(self, limit: int = 50) -> List[Dict]:
        """获取补仓决策日志"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM add_position_decision_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            log = dict(row)
            if log['decision_steps']:
                log['decision_steps'] = json.loads(log['decision_steps'])
            if log['stage_info']:
                log['stage_info'] = json.loads(log['stage_info'])
            logs.append(log)
        
        conn.close()
        return logs


def test_add_decision_logger():
    """测试补仓决策日志"""
    print("🧪 测试补仓决策日志")
    print("=" * 80)
    
    logger = AddPositionDecisionLogger()
    
    # 测试空单补仓
    print("\n📊 测试空单补仓: BTC-USDT-SWAP")
    result = logger.check_short_add_conditions("BTC-USDT-SWAP")
    
    print(f"\n决策结果: {'✅ 可以补仓' if result['can_add'] else '❌ 不可补仓'}")
    print(f"原因: {result['reason']}")
    print("\n决策步骤:")
    for step in result['decision_steps']:
        print(f"  {step}")
    
    print("\n✅ 测试完成")


if __name__ == '__main__':
    test_add_decision_logger()
