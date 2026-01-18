#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单维护管理器
维护逻辑：亏损>-10% → 买入10倍持仓 → 平掉95% → 剩余1U
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库路径
DB_PATH = '/home/user/webapp/trading_decision.db'

class AnchorMaintenanceManager:
    """锚点单维护管理器"""
    
    def __init__(self, db_path: str = DB_PATH):
        """初始化"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # 锚点单维护决策日志表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS anchor_maintenance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inst_id TEXT NOT NULL,
            pos_side TEXT NOT NULL,
            original_size REAL NOT NULL,
            original_price REAL NOT NULL,
            original_margin REAL NOT NULL,
            current_price REAL NOT NULL,
            profit_rate REAL NOT NULL,
            step TEXT NOT NULL,
            action TEXT NOT NULL,
            trade_size REAL,
            trade_price REAL,
            remaining_size REAL,
            remaining_margin REAL,
            trigger_reason TEXT,
            decision_log TEXT,
            status TEXT DEFAULT 'pending',
            executed_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ 锚点单维护管理器数据库初始化完成")
    
    def check_maintenance_needed(self, position: Dict) -> Dict:
        """
        检查锚点单是否需要维护
        
        Args:
            position: 持仓信息
                - inst_id: 币种
                - pos_side: 方向
                - pos_size: 持仓数量
                - avg_price: 平均价格
                - mark_price: 当前价格
                - profit_rate: 收益率
                - margin: 保证金
                - is_anchor: 是否锚点单
        
        Returns:
            dict: 决策结果
        """
        # 只处理锚点单
        if not position.get('is_anchor'):
            return {
                'need_maintenance': False,
                'reason': '不是锚点单'
            }
        
        profit_rate = position.get('profit_rate', 0)
        
        # 检查是否触发维护条件：亏损 >= 10%
        if profit_rate <= -10:
            return {
                'need_maintenance': True,
                'trigger_type': 'loss_trigger',
                'profit_rate': profit_rate,
                'inst_id': position['inst_id'],
                'pos_side': position['pos_side'],
                'original_size': position['pos_size'],
                'original_price': position['avg_price'],
                'original_margin': position['margin'],
                'current_price': position['mark_price'],
                'reason': f'⚠️  锚点单亏损达到 {profit_rate:.2f}%，触发维护条件'
            }
        
        return {
            'need_maintenance': False,
            'reason': f'锚点单盈亏 {profit_rate:.2f}%，未达到维护阈值(-10%)'
        }
    
    def calculate_maintenance_plan(self, position: Dict) -> Dict:
        """
        计算维护方案
        
        维护流程：
        1. 买入10倍原持仓（投入10倍保证金）
        2. 平掉到剩余1U保证金
        3. 保留1U的仓位
        
        注意：10倍杠杆下，投入10倍保证金 = 10倍实际价值
        
        Args:
            position: 持仓信息
        
        Returns:
            dict: 维护方案
        """
        original_size = position['pos_size']
        original_margin = position['margin']
        current_price = position['mark_price']
        leverage = position.get('lever', 10)  # 默认10倍杠杆
        
        # 步骤1：投入10倍保证金买入
        buy_margin = original_margin * 10  # 投入10倍保证金
        buy_value = buy_margin * leverage  # 10倍杠杆下的实际价值
        buy_size = buy_value / current_price  # 买入张数
        
        # 买入后的总仓位
        total_size_after_buy = original_size + buy_size
        total_margin_after_buy = original_margin + buy_margin
        
        # 步骤2：计算要保留≤2U，需要平掉多少
        target_remaining_margin = min(2.0, total_margin_after_buy)  # 目标保留2U，但不超过总额
        close_margin = total_margin_after_buy - target_remaining_margin
        close_percent = (close_margin / total_margin_after_buy) * 100
        
        # 按比例计算平仓数量
        close_size = (close_margin / total_margin_after_buy) * total_size_after_buy
        
        # 步骤3：剩余持仓（≤2U）
        remaining_size = total_size_after_buy - close_size
        remaining_margin = total_margin_after_buy - close_margin
        
        return {
            'step1_buy': {
                'action': 'buy',
                'size': buy_size,
                'margin': buy_margin,
                'value': buy_value,
                'leverage': leverage,
                'description': f'投入10倍保证金: {buy_margin:.2f} USDT ({leverage}x杠杆 = {buy_value:.2f} USDT价值, {buy_size:.4f} 张)'
            },
            'after_buy': {
                'total_size': total_size_after_buy,
                'total_margin': total_margin_after_buy,
                'description': f'买入后总仓位: {total_size_after_buy:.4f} 张 ({total_margin_after_buy:.2f} USDT)'
            },
            'step2_close': {
                'action': 'close',
                'size': close_size,
                'margin': close_margin,
                'percent': close_percent,
                'description': f'平掉{close_percent:.1f}%: {close_size:.4f} 张 ({close_margin:.2f} USDT)'
            },
            'step3_remaining': {
                'size': remaining_size,
                'margin': remaining_margin,
                'target_margin': target_remaining_margin,
                'description': f'保留1U: {remaining_size:.4f} 张 ({remaining_margin:.2f} USDT)'
            },
            'original': {
                'size': original_size,
                'margin': original_margin
            }
        }
    
    def scan_positions(self, positions: List[Dict]) -> List[Dict]:
        """
        扫描所有持仓，检查是否需要维护
        
        Args:
            positions: 持仓列表
        
        Returns:
            list: 需要维护的持仓列表
        """
        results = []
        
        for pos in positions:
            # 检查是否需要维护
            check_result = self.check_maintenance_needed(pos)
            
            if check_result['need_maintenance']:
                # 计算维护方案
                plan = self.calculate_maintenance_plan(pos)
                
                # 构建决策日志
                decision_log = {
                    'step1': f"🔴 触发条件: 锚点单亏损 {check_result['profit_rate']:.2f}%",
                    'step2': f"📊 原始仓位: {pos['pos_size']:.4f} 张 ({pos['margin']:.2f} USDT)",
                    'step3': f"🛒 {plan['step1_buy']['description']}",
                    'step4': f"📈 {plan['after_buy']['description']}",
                    'step5': f"💰 {plan['step2_close']['description']}",
                    'step6': f"✅ {plan['step3_remaining']['description']}"
                }
                
                result = {
                    'inst_id': pos['inst_id'],
                    'pos_side': pos['pos_side'],
                    'original_size': pos['pos_size'],
                    'original_price': pos['avg_price'],
                    'original_margin': pos['margin'],
                    'current_price': pos['mark_price'],
                    'profit_rate': check_result['profit_rate'],
                    'trigger_reason': check_result['reason'],
                    'maintenance_plan': plan,
                    'decision_log': decision_log,
                    'can_execute': True
                }
                
                results.append(result)
        
        return results
    
    def save_maintenance_log(self, maintenance_data: Dict, step: str, status: str = 'pending') -> int:
        """
        保存维护日志
        
        Args:
            maintenance_data: 维护数据
            step: 步骤 (buy/close/complete)
            status: 状态 (pending/executed/failed)
        
        Returns:
            int: 日志ID
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 根据步骤确定交易数量和价格
            trade_size = None
            trade_price = maintenance_data.get('current_price')
            remaining_size = None
            remaining_margin = None
            action = step
            
            if step == 'buy':
                trade_size = maintenance_data['maintenance_plan']['step1_buy']['size']
                remaining_size = maintenance_data['maintenance_plan']['after_buy']['total_size']
                remaining_margin = maintenance_data['maintenance_plan']['after_buy']['total_margin']
            elif step == 'close':
                trade_size = maintenance_data['maintenance_plan']['step2_close']['size']
                remaining_size = maintenance_data['maintenance_plan']['step3_remaining']['size']
                remaining_margin = maintenance_data['maintenance_plan']['step3_remaining']['margin']
            
            cursor.execute('''
            INSERT INTO anchor_maintenance_logs (
                inst_id, pos_side, original_size, original_price, original_margin,
                current_price, profit_rate, step, action, trade_size, trade_price,
                remaining_size, remaining_margin, trigger_reason, decision_log, status, executed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                maintenance_data['inst_id'],
                maintenance_data['pos_side'],
                maintenance_data['original_size'],
                maintenance_data['original_price'],
                maintenance_data['original_margin'],
                maintenance_data['current_price'],
                maintenance_data['profit_rate'],
                step,
                action,
                trade_size,
                trade_price,
                remaining_size,
                remaining_margin,
                maintenance_data['trigger_reason'],
                json.dumps(maintenance_data['decision_log'], ensure_ascii=False),
                status,
                timestamp if status == 'executed' else None
            ))
            
            log_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ 锚点单维护日志已保存: ID={log_id}, Step={step}, Status={status}")
            return log_id
            
        except Exception as e:
            print(f"❌ 保存维护日志失败: {e}")
            return 0
    
    def get_maintenance_logs(self, limit: int = 50) -> List[Dict]:
        """
        获取维护日志
        
        Args:
            limit: 返回数量
        
        Returns:
            list: 日志列表
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM anchor_maintenance_logs
            ORDER BY created_at DESC
            LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            logs = []
            for row in rows:
                log = dict(row)
                # 解析 decision_log JSON
                if log['decision_log']:
                    try:
                        log['decision_log'] = json.loads(log['decision_log'])
                    except:
                        pass
                logs.append(log)
            
            return logs
            
        except Exception as e:
            print(f"❌ 获取维护日志失败: {e}")
            return []

if __name__ == '__main__':
    # 测试
    manager = AnchorMaintenanceManager()
    
    # 模拟一个亏损的锚点单（10倍杠杆）
    test_position = {
        'inst_id': 'BTC-USDT-SWAP',
        'pos_side': 'short',
        'pos_size': 10.0,
        'avg_price': 50000.0,
        'mark_price': 55000.0,  # 价格上涨，空单亏损
        'profit_rate': -12.5,  # 亏损12.5%
        'margin': 0.5,  # 保证金0.5 USDT
        'lever': 10,  # 10倍杠杆
        'is_anchor': 1
    }
    
    print("\n=== 锚点单维护测试 ===\n")
    
    # 1. 检查是否需要维护
    check_result = manager.check_maintenance_needed(test_position)
    print(f"1. 检查结果: {json.dumps(check_result, indent=2, ensure_ascii=False)}\n")
    
    if check_result['need_maintenance']:
        # 2. 计算维护方案
        plan = manager.calculate_maintenance_plan(test_position)
        print(f"2. 维护方案:")
        print(f"   步骤1: {plan['step1_buy']['description']}")
        print(f"   买入后: {plan['after_buy']['description']}")
        print(f"   步骤2: {plan['step2_close']['description']}")
        print(f"   最终: {plan['step3_remaining']['description']}\n")
        
        # 3. 扫描持仓
        results = manager.scan_positions([test_position])
        if results:
            print(f"3. 扫描结果: 发现 {len(results)} 个需要维护的锚点单")
            for r in results:
                print(f"\n   币种: {r['inst_id']}")
                print(f"   盈亏: {r['profit_rate']:.2f}%")
                print(f"   决策日志:")
                for key, value in r['decision_log'].items():
                    print(f"     {value}")
