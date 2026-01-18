#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开仓决策日志模块
记录开仓的完整决策过程
"""

import sqlite3
from datetime import datetime
import pytz
from typing import Dict, List, Optional
import json

DB_PATH = '/home/user/webapp/trading_decision.db'
CRYPTO_DATA_DB = '/home/user/webapp/crypto_data.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class OpenPositionDecisionLogger:
    """开仓决策日志记录器"""
    
    def __init__(self):
        """初始化"""
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建开仓决策日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS open_position_decision_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inst_id TEXT NOT NULL,
                pos_side TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                action TEXT NOT NULL,
                decision_time TEXT NOT NULL,
                open_price REAL,
                open_amount REAL,
                pressure1 REAL,
                pressure2 REAL,
                position_48h REAL,
                position_7d REAL,
                market_trend TEXT,
                available_capital REAL,
                current_position_value REAL,
                max_single_coin REAL,
                decision_steps TEXT,
                trigger_reason TEXT,
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
                allow_long, allow_short, enabled, simulation_mode,
                total_capital, position_limit_percent, max_single_coin_percent,
                market_mode, market_trend
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
                'simulation_mode': bool(row[3]),
                'total_capital': float(row[4]),
                'position_limit_percent': float(row[5]),
                'max_single_coin_percent': float(row[6]),
                'market_mode': row[7],
                'market_trend': row[8]
            }
        
        return None
    
    def get_pressure_lines(self, inst_id: str) -> Optional[Dict]:
        """获取压力线数据"""
        # 将inst_id转换为symbol格式
        # BTC-USDT-SWAP -> BTCUSDT
        symbol = inst_id.replace('-SWAP', '').replace('-', '')
        
        try:
            conn = sqlite3.connect(CRYPTO_DATA_DB)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    resistance_line_1,
                    resistance_line_2,
                    distance_to_resistance_1,
                    distance_to_resistance_2,
                    position_48h,
                    position_7d,
                    current_price
                FROM support_resistance_levels
                WHERE symbol = ?
                ORDER BY record_time DESC
                LIMIT 1
            ''', (symbol,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'pressure1': row[0],
                    'pressure2': row[1],
                    'distance_to_r1': row[2],
                    'distance_to_r2': row[3],
                    'position_48h': row[4],
                    'position_7d': row[5],
                    'current_price': row[6]
                }
        except Exception as e:
            print(f"获取压力线数据失败: {e}")
        
        return None
    
    def get_coin_position_value(self, inst_id: str) -> float:
        """获取币种当前持仓价值"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(open_size * open_price) as position_value
            FROM position_opens
            WHERE inst_id = ? AND status = 'open'
        ''', (inst_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return float(row[0]) if row[0] else 0.0
    
    def check_short_open_conditions(self, inst_id: str) -> Dict:
        """检查空单开仓条件"""
        decision_steps = []
        can_open = False
        
        # 1. 获取配置
        config = self.get_config()
        if not config:
            decision_steps.append("❌ 无法获取系统配置")
            return {
                'can_open': False,
                'reason': '无法获取系统配置',
                'decision_steps': decision_steps
            }
        
        decision_steps.append("✅ 系统配置加载成功")
        decision_steps.append(f"   - 允许开空单: {config['allow_short']}")
        decision_steps.append(f"   - 系统启用: {config['enabled']}")
        decision_steps.append(f"   - 模拟模式: {config['simulation_mode']}")
        
        # 2. 检查系统开关
        if not config['enabled']:
            decision_steps.append("❌ 系统未启用")
            return {
                'can_open': False,
                'reason': '系统未启用',
                'decision_steps': decision_steps
            }
        
        if not config['allow_short']:
            decision_steps.append("❌ 不允许开空单")
            return {
                'can_open': False,
                'reason': '不允许开空单',
                'decision_steps': decision_steps
            }
        
        decision_steps.append("✅ 系统开关检查通过")
        
        # 3. 获取压力线数据
        pressure_data = self.get_pressure_lines(inst_id)
        if not pressure_data:
            decision_steps.append("❌ 无法获取压力线数据")
            return {
                'can_open': False,
                'reason': '无法获取压力线数据',
                'decision_steps': decision_steps
            }
        
        decision_steps.append("✅ 压力线数据获取成功")
        decision_steps.append(f"   - 压力线1: {pressure_data['pressure1']}")
        decision_steps.append(f"   - 压力线2: {pressure_data['pressure2']}")
        decision_steps.append(f"   - 48h位置: {pressure_data['position_48h']}")
        decision_steps.append(f"   - 7d位置: {pressure_data['position_7d']}")
        
        # 4. 检查压力线条件
        pressure_sum = pressure_data['pressure1'] + pressure_data['pressure2']
        if pressure_sum < 8:
            decision_steps.append(f"❌ 压力线之和 {pressure_sum:.2f} < 8")
            return {
                'can_open': False,
                'reason': f'压力线之和{pressure_sum:.2f}<8',
                'decision_steps': decision_steps,
                'pressure_data': pressure_data
            }
        
        decision_steps.append(f"✅ 压力线之和 {pressure_sum:.2f} >= 8")
        
        # 5. 检查位置条件
        if pressure_data['position_48h'] < 90 or pressure_data['position_7d'] < 90:
            decision_steps.append(f"❌ 位置不满足: 48h={pressure_data['position_48h']}, 7d={pressure_data['position_7d']}")
            return {
                'can_open': False,
                'reason': '48h或7d位置<90',
                'decision_steps': decision_steps,
                'pressure_data': pressure_data
            }
        
        decision_steps.append("✅ 位置条件满足（48h>=90, 7d>=90）")
        
        # 6. 计算可开仓额和单币种限制
        available_capital = config['total_capital'] * config['position_limit_percent'] / 100
        max_single_coin = available_capital * config['max_single_coin_percent'] / 100
        open_amount = available_capital * 0.01  # 开仓1%
        
        decision_steps.append(f"✅ 资金计算")
        decision_steps.append(f"   - 可开仓额: {available_capital:.2f} USDT")
        decision_steps.append(f"   - 单币种上限: {max_single_coin:.2f} USDT")
        decision_steps.append(f"   - 建议开仓: {open_amount:.2f} USDT (1%)")
        
        # 7. 检查单币种限制
        current_position = self.get_coin_position_value(inst_id)
        if current_position + open_amount > max_single_coin:
            decision_steps.append(f"❌ 超过单币种限制")
            decision_steps.append(f"   - 当前持仓: {current_position:.2f} USDT")
            decision_steps.append(f"   - 新增后: {current_position + open_amount:.2f} USDT")
            return {
                'can_open': False,
                'reason': '超过单币种限制',
                'decision_steps': decision_steps,
                'pressure_data': pressure_data
            }
        
        decision_steps.append(f"✅ 单币种限制检查通过")
        decision_steps.append(f"   - 当前持仓: {current_position:.2f} USDT")
        decision_steps.append(f"   - 新增后: {current_position + open_amount:.2f} USDT")
        
        # 所有条件满足
        decision_steps.append("🎯 满足所有开仓条件，建议开仓")
        
        return {
            'can_open': True,
            'reason': '满足所有开仓条件',
            'open_amount': open_amount,
            'open_price': pressure_data['current_price'],
            'decision_steps': decision_steps,
            'pressure_data': pressure_data,
            'config': config
        }
    
    def record_open_decision(self, inst_id: str, pos_side: str, 
                           decision_result: Dict, action: str = 'open'):
        """记录开仓决策日志"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        pressure_data = decision_result.get('pressure_data', {})
        config = decision_result.get('config', {})
        
        cursor.execute('''
            INSERT INTO open_position_decision_logs (
                inst_id, pos_side, decision_type, action, decision_time,
                open_price, open_amount, pressure1, pressure2,
                position_48h, position_7d, market_trend,
                available_capital, current_position_value, max_single_coin,
                decision_steps, trigger_reason, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inst_id, pos_side, 'open', action, now,
            decision_result.get('open_price'),
            decision_result.get('open_amount'),
            pressure_data.get('pressure1'),
            pressure_data.get('pressure2'),
            pressure_data.get('position_48h'),
            pressure_data.get('position_7d'),
            config.get('market_trend'),
            config.get('total_capital', 0) * config.get('position_limit_percent', 60) / 100,
            self.get_coin_position_value(inst_id),
            config.get('total_capital', 0) * config.get('position_limit_percent', 60) * config.get('max_single_coin_percent', 10) / 10000,
            json.dumps(decision_result['decision_steps'], ensure_ascii=False),
            decision_result['reason'],
            'can_open' if decision_result['can_open'] else 'skip'
        ))
        
        conn.commit()
        conn.close()
    
    def get_decision_logs(self, limit: int = 50) -> List[Dict]:
        """获取开仓决策日志"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM open_position_decision_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            log = dict(row)
            if log['decision_steps']:
                log['decision_steps'] = json.loads(log['decision_steps'])
            logs.append(log)
        
        conn.close()
        return logs


def test_open_decision_logger():
    """测试开仓决策日志"""
    print("🧪 测试开仓决策日志")
    print("=" * 80)
    
    logger = OpenPositionDecisionLogger()
    
    # 测试BTC-USDT-SWAP
    test_inst_id = "BTC-USDT-SWAP"
    
    print(f"\n📊 测试币种: {test_inst_id}")
    result = logger.check_short_open_conditions(test_inst_id)
    
    print(f"\n决策结果: {'✅ 可以开仓' if result['can_open'] else '❌ 不可开仓'}")
    print(f"原因: {result['reason']}")
    print("\n决策步骤:")
    for step in result['decision_steps']:
        print(f"  {step}")
    
    # 记录决策日志
    logger.record_open_decision(test_inst_id, 'short', result)
    print("\n✅ 决策日志已记录")
    
    # 获取最近的日志
    print("\n📝 最近的决策日志:")
    logs = logger.get_decision_logs(limit=5)
    for log in logs:
        print(f"\n时间: {log['decision_time']}")
        print(f"币种: {log['inst_id']}")
        print(f"结果: {log['result']}")
    
    print("\n✅ 测试完成")


if __name__ == '__main__':
    test_open_decision_logger()
