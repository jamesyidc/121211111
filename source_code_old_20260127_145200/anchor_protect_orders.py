#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单挂单保护模块
为锚点单创建保护挂单，防止急速拉升
"""

import sqlite3
from datetime import datetime
import pytz
from typing import Dict, List, Optional
import json

DB_PATH = '/home/user/webapp/trading_decision.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class AnchorProtectOrderManager:
    """锚点单保护挂单管理器"""
    
    # 挂单保护规则
    PROTECT_RULES = [
        {
            'order_type': 'protect_1',
            'price_offset_percent': 4,  # 币价上方4%
            'leverage': 10,  # 10倍杠杆
            'close_percent': 95  # 触发后平掉95%
        },
        {
            'order_type': 'protect_2',
            'price_offset_percent': 10,  # 币价上方10%
            'leverage': 20,  # 20倍杠杆
            'close_percent': 95  # 触发后平掉95%
        }
    ]
    
    def __init__(self):
        """初始化"""
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建保护挂单表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anchor_protect_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anchor_id INTEGER NOT NULL,
                inst_id TEXT NOT NULL,
                pos_side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                anchor_open_price REAL NOT NULL,
                trigger_price REAL NOT NULL,
                price_offset_percent REAL NOT NULL,
                leverage INTEGER NOT NULL,
                close_percent REAL NOT NULL,
                anchor_position_size REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_time TEXT NOT NULL,
                triggered_time TEXT,
                executed_time TEXT,
                execution_result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建挂单决策日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS protect_order_decision_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inst_id TEXT NOT NULL,
                anchor_id INTEGER NOT NULL,
                decision_type TEXT NOT NULL,
                action TEXT NOT NULL,
                decision_time TEXT NOT NULL,
                anchor_open_price REAL,
                protect_order_info TEXT,
                decision_steps TEXT,
                trigger_reason TEXT,
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_anchor_position(self, inst_id: str) -> Optional[Dict]:
        """获取锚点单信息"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id, inst_id, pos_side, anchor_price, anchor_size,
                current_price, status
            FROM anchor_positions
            WHERE inst_id = ? AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
        ''', (inst_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        
        return None
    
    def check_existing_protect_orders(self, anchor_id: int) -> List[Dict]:
        """检查是否已存在保护挂单"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM anchor_protect_orders
            WHERE anchor_id = ? AND status = 'pending'
        ''', (anchor_id,))
        
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return orders
    
    def create_protect_orders(self, inst_id: str, dry_run: bool = True) -> Dict:
        """为锚点单创建保护挂单"""
        decision_steps = []
        
        # 1. 获取锚点单信息
        anchor = self.get_anchor_position(inst_id)
        if not anchor:
            decision_steps.append("❌ 该币种无锚点单")
            return {
                'success': False,
                'reason': '该币种无锚点单',
                'decision_steps': decision_steps
            }
        
        decision_steps.append(f"✅ 锚点单信息获取成功")
        decision_steps.append(f"   - 锚点单ID: {anchor['id']}")
        decision_steps.append(f"   - 开仓价格: {anchor['anchor_price']:.4f}")
        decision_steps.append(f"   - 仓位大小: {anchor['anchor_size']:.2f} USDT")
        
        # 2. 检查是否已存在保护挂单
        existing_orders = self.check_existing_protect_orders(anchor['id'])
        if existing_orders:
            decision_steps.append(f"⚠️ 已存在 {len(existing_orders)} 个保护挂单")
            return {
                'success': False,
                'reason': '已存在保护挂单',
                'existing_orders': existing_orders,
                'decision_steps': decision_steps
            }
        
        decision_steps.append("✅ 无现有保护挂单，可以创建")
        
        # 3. 创建保护挂单
        created_orders = []
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        for rule in self.PROTECT_RULES:
            # 计算触发价格
            trigger_price = anchor['anchor_price'] * (1 + rule['price_offset_percent'] / 100)
            
            order_info = {
                'anchor_id': anchor['id'],
                'inst_id': inst_id,
                'pos_side': anchor['pos_side'],
                'order_type': rule['order_type'],
                'anchor_open_price': anchor['anchor_price'],
                'trigger_price': trigger_price,
                'price_offset_percent': rule['price_offset_percent'],
                'leverage': rule['leverage'],
                'close_percent': rule['close_percent'],
                'anchor_position_size': anchor['anchor_size'],
                'status': 'pending',
                'created_time': now
            }
            
            decision_steps.append(f"✅ 创建保护挂单: {rule['order_type']}")
            decision_steps.append(f"   - 触发价格: {trigger_price:.4f} (+{rule['price_offset_percent']}%)")
            decision_steps.append(f"   - 杠杆倍数: {rule['leverage']}x")
            decision_steps.append(f"   - 平仓比例: {rule['close_percent']}%")
            
            created_orders.append(order_info)
            
            # 如果不是dry_run，保存到数据库
            if not dry_run:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO anchor_protect_orders (
                        anchor_id, inst_id, pos_side, order_type,
                        anchor_open_price, trigger_price, price_offset_percent,
                        leverage, close_percent, anchor_position_size,
                        status, created_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_info['anchor_id'],
                    order_info['inst_id'],
                    order_info['pos_side'],
                    order_info['order_type'],
                    order_info['anchor_open_price'],
                    order_info['trigger_price'],
                    order_info['price_offset_percent'],
                    order_info['leverage'],
                    order_info['close_percent'],
                    order_info['anchor_position_size'],
                    order_info['status'],
                    order_info['created_time']
                ))
                
                conn.commit()
                conn.close()
        
        # 4. 记录决策日志
        self.record_decision_log(
            inst_id=inst_id,
            anchor_id=anchor['id'],
            decision_type='create',
            action='create',
            anchor_open_price=anchor['anchor_price'],
            protect_order_info=created_orders,
            decision_steps=decision_steps,
            trigger_reason=f"为锚点单创建保护挂单，防止急速拉升",
            result='success'
        )
        
        decision_steps.append(f"🎯 成功创建 {len(created_orders)} 个保护挂单")
        
        return {
            'success': True,
            'anchor': anchor,
            'created_orders': created_orders,
            'decision_steps': decision_steps
        }
    
    def scan_trigger_conditions(self) -> List[Dict]:
        """扫描所有挂单，检查触发条件"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有待触发的保护挂单
        cursor.execute('''
            SELECT * FROM anchor_protect_orders
            WHERE status = 'pending'
        ''')
        
        pending_orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        results = []
        
        for order in pending_orders:
            # 获取当前价格（从最新开仓记录）
            current_price = self.get_current_price(order['inst_id'])
            if not current_price:
                continue
            
            # 检查是否达到触发价格
            if current_price >= order['trigger_price']:
                results.append({
                    'order': order,
                    'current_price': current_price,
                    'triggered': True,
                    'reason': f"当前价{current_price:.4f}达到触发价{order['trigger_price']:.4f}"
                })
        
        return results
    
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
    
    def execute_protect_order(self, order_id: int, current_price: float, dry_run: bool = True) -> Dict:
        """执行保护挂单（触发后平仓95%）"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取挂单信息
        cursor.execute('SELECT * FROM anchor_protect_orders WHERE id = ?', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return {'success': False, 'reason': '挂单不存在'}
        
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 计算平仓数量
        close_amount = order[10] * (order[9] / 100)  # anchor_position_size * close_percent
        remaining_amount = order[10] - close_amount
        
        execution_result = {
            'order_id': order_id,
            'inst_id': order[2],
            'trigger_price': order[6],
            'current_price': current_price,
            'close_amount': close_amount,
            'remaining_amount': remaining_amount,
            'close_percent': order[9],
            'execution_time': now
        }
        
        if not dry_run:
            # 更新挂单状态
            cursor.execute('''
                UPDATE anchor_protect_orders
                SET status = 'executed',
                    triggered_time = ?,
                    executed_time = ?,
                    execution_result = ?
                WHERE id = ?
            ''', (now, now, json.dumps(execution_result, ensure_ascii=False), order_id))
            
            conn.commit()
        
        conn.close()
        
        return {
            'success': True,
            'execution_result': execution_result
        }
    
    def record_decision_log(self, inst_id: str, anchor_id: int, decision_type: str,
                          action: str, anchor_open_price: float,
                          protect_order_info: List[Dict], decision_steps: List[str],
                          trigger_reason: str, result: str):
        """记录决策日志"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO protect_order_decision_logs (
                inst_id, anchor_id, decision_type, action, decision_time,
                anchor_open_price, protect_order_info, decision_steps,
                trigger_reason, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inst_id, anchor_id, decision_type, action, now,
            anchor_open_price,
            json.dumps(protect_order_info, ensure_ascii=False),
            json.dumps(decision_steps, ensure_ascii=False),
            trigger_reason, result
        ))
        
        conn.commit()
        conn.close()
    
    def get_protect_orders(self, inst_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """获取保护挂单记录"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if inst_id:
            cursor.execute('''
                SELECT * FROM anchor_protect_orders
                WHERE inst_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (inst_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM anchor_protect_orders
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
        
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return orders
    
    def get_decision_logs(self, limit: int = 50) -> List[Dict]:
        """获取决策日志"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM protect_order_decision_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            log = dict(row)
            if log['protect_order_info']:
                log['protect_order_info'] = json.loads(log['protect_order_info'])
            if log['decision_steps']:
                log['decision_steps'] = json.loads(log['decision_steps'])
            logs.append(log)
        
        conn.close()
        return logs


def test_protect_order_manager():
    """测试保护挂单管理器"""
    print("🧪 测试保护挂单管理器")
    print("=" * 80)
    
    manager = AnchorProtectOrderManager()
    
    # 测试创建保护挂单
    print("\n📊 测试: 为锚点单创建保护挂单")
    result = manager.create_protect_orders("BTC-USDT-SWAP", dry_run=True)
    
    print(f"\n结果: {'✅ 成功' if result['success'] else '❌ 失败'}")
    print(f"原因: {result.get('reason', '成功创建')}")
    print("\n决策步骤:")
    for step in result['decision_steps']:
        print(f"  {step}")
    
    if result['success'] and 'created_orders' in result:
        print(f"\n创建了 {len(result['created_orders'])} 个保护挂单:")
        for order in result['created_orders']:
            print(f"\n  {order['order_type']}:")
            print(f"    触发价格: {order['trigger_price']:.4f}")
            print(f"    杠杆: {order['leverage']}x")
            print(f"    平仓比例: {order['close_percent']}%")
    
    print("\n✅ 测试完成")


if __name__ == '__main__':
    test_protect_order_manager()
