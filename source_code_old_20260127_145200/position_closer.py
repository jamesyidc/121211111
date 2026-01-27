#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仓位平仓管理器
实现禁止开空单时的自动平仓逻辑
"""

import sqlite3
from datetime import datetime
import pytz
from typing import Dict, List, Tuple, Optional

# 配置
DB_PATH = '/home/user/webapp/trading_decision.db'
ANCHOR_DB_PATH = '/home/user/webapp/anchor_system.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


class PositionCloser:
    """仓位平仓管理器"""
    
    def __init__(self):
        """初始化"""
        self.db_path = DB_PATH
        self.anchor_db_path = ANCHOR_DB_PATH
    
    def get_config(self) -> Dict:
        """获取配置"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT allow_long, allow_short, allow_anchor, enabled
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
                'allow_anchor': bool(row[2]),
                'enabled': bool(row[3])
            }
        return {
            'allow_long': False,
            'allow_short': True,
            'allow_anchor': True,
            'enabled': False
        }
    
    def get_anchor_positions(self) -> List[Dict]:
        """获取所有锚点单"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT inst_id, pos_side, open_size, open_price, open_percent
        FROM position_opens
        WHERE is_anchor = 1
        ORDER BY inst_id, pos_side
        ''')
        
        anchors = []
        for row in cursor.fetchall():
            anchors.append({
                'inst_id': row[0],
                'pos_side': row[1],
                'anchor_size': float(row[2]) if row[2] else 0,
                'anchor_price': float(row[3]) if row[3] else 0,
                'anchor_percent': float(row[4]) if row[4] else 0
            })
        
        conn.close()
        return anchors
    
    def get_current_positions(self) -> List[Dict]:
        """获取当前所有持仓（从anchor_system数据库）"""
        try:
            conn = sqlite3.connect(self.anchor_db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT inst_id, pos_side, pos AS size, 
                   avg_px AS avg_price, upl_ratio AS profit_rate,
                   upl AS unrealized_pnl, last AS current_price
            FROM positions
            WHERE pos > 0
            ORDER BY inst_id, pos_side
            ''')
            
            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'inst_id': row[0],
                    'pos_side': row[1],
                    'size': float(row[2]),
                    'avg_price': float(row[3]),
                    'profit_rate': float(row[4]) if row[4] else 0,
                    'unrealized_pnl': float(row[5]) if row[5] else 0,
                    'current_price': float(row[6]) if row[6] else 0
                })
            
            conn.close()
            return positions
        except Exception as e:
            print(f"❌ 获取持仓失败: {e}")
            return []
    
    def get_position_adds(self, inst_id: str, pos_side: str) -> List[Dict]:
        """获取补仓记录"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT add_size, add_price, level, profit_rate_trigger, timestamp
        FROM position_adds
        WHERE inst_id = ? AND pos_side = ?
        ORDER BY timestamp ASC
        ''', (inst_id, pos_side))
        
        adds = []
        for row in cursor.fetchall():
            adds.append({
                'add_size': float(row[0]),
                'add_price': float(row[1]),
                'level': row[2],
                'profit_rate_trigger': float(row[3]),
                'timestamp': row[4]
            })
        
        conn.close()
        return adds
    
    def calculate_close_size(self, inst_id: str, pos_side: str, 
                            current_size: float) -> Tuple[float, str]:
        """
        计算需要平仓的数量
        返回：(平仓数量, 原因说明)
        """
        # 查找是否有锚点单
        anchors = self.get_anchor_positions()
        anchor = None
        
        for a in anchors:
            if a['inst_id'] == inst_id and a['pos_side'] == pos_side:
                anchor = a
                break
        
        if not anchor:
            # 没有锚点单，全部平仓
            return current_size, "没有锚点单，全部平仓"
        
        # 有锚点单，只保留锚点单部分
        anchor_size = anchor['anchor_size']
        
        if current_size <= anchor_size:
            # 当前持仓小于等于锚点单，不平仓
            return 0, f"当前持仓 {current_size} <= 锚点单 {anchor_size}，无需平仓"
        
        # 平掉超过锚点单的部分
        close_size = current_size - anchor_size
        return close_size, f"保留锚点单 {anchor_size}，平掉补仓部分 {close_size}"
    
    def check_should_close_profitable_short(self, position: Dict) -> Tuple[bool, float, str]:
        """
        检查是否应该平掉盈利的空单
        返回：(是否平仓, 平仓数量, 原因)
        """
        # 只处理空单
        if position['pos_side'] != 'short':
            return False, 0, "不是空单"
        
        # 只处理盈利的仓位
        if position['profit_rate'] <= 0:
            return False, 0, f"未盈利（{position['profit_rate']:.2f}%）"
        
        # 计算需要平仓的数量
        close_size, reason = self.calculate_close_size(
            position['inst_id'],
            position['pos_side'],
            position['size']
        )
        
        if close_size <= 0:
            return False, 0, reason
        
        return True, close_size, f"盈利 {position['profit_rate']:.2f}%，{reason}"
    
    def check_should_close_breakeven_short(self, position: Dict) -> Tuple[bool, float, str]:
        """
        检查是否应该平掉回本的空单（补仓后不亏了）
        返回：(是否平仓, 平仓数量, 原因)
        """
        # 只处理空单
        if position['pos_side'] != 'short':
            return False, 0, "不是空单"
        
        # 只处理不亏损的仓位（>=0）
        if position['profit_rate'] < 0:
            return False, 0, f"仍在亏损（{position['profit_rate']:.2f}%）"
        
        # 检查是否有补仓记录
        adds = self.get_position_adds(position['inst_id'], position['pos_side'])
        
        if not adds:
            return False, 0, "没有补仓记录"
        
        # 有补仓且不亏损，平掉补仓部分
        close_size, reason = self.calculate_close_size(
            position['inst_id'],
            position['pos_side'],
            position['size']
        )
        
        if close_size <= 0:
            return False, 0, reason
        
        return True, close_size, f"补仓后回本（{position['profit_rate']:.2f}%），{reason}"
    
    def record_close_action(self, inst_id: str, pos_side: str, 
                           close_size: float, close_price: float,
                           reason: str, close_type: str) -> int:
        """
        记录平仓动作
        close_type: 'profitable' 或 'breakeven'
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 先检查表是否存在
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS position_closes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inst_id TEXT NOT NULL,
            pos_side TEXT NOT NULL,
            close_size REAL NOT NULL,
            close_price REAL NOT NULL,
            close_type TEXT NOT NULL,
            reason TEXT,
            timestamp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        INSERT INTO position_closes (
            inst_id, pos_side, close_size, close_price,
            close_type, reason, timestamp, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (inst_id, pos_side, close_size, close_price,
              close_type, reason, timestamp, timestamp))
        
        close_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return close_id
    
    def scan_and_close_positions(self, dry_run: bool = True) -> Dict:
        """
        扫描并平仓符合条件的仓位
        dry_run: 是否为模拟运行（不实际执行）
        """
        config = self.get_config()
        
        # 只有在禁止开空单时才执行
        if config['allow_short']:
            return {
                'success': False,
                'message': '系统允许开空单，无需自动平仓',
                'actions': []
            }
        
        positions = self.get_current_positions()
        actions = []
        
        for pos in positions:
            # 跳过多单
            if pos['pos_side'] != 'short':
                continue
            
            # 检查是否应该平仓（盈利）
            should_close, close_size, reason = self.check_should_close_profitable_short(pos)
            
            if should_close:
                action = {
                    'inst_id': pos['inst_id'],
                    'pos_side': pos['pos_side'],
                    'current_size': pos['size'],
                    'close_size': close_size,
                    'close_price': pos['current_price'],
                    'profit_rate': pos['profit_rate'],
                    'close_type': 'profitable',
                    'reason': reason,
                    'status': 'pending'
                }
                
                if not dry_run:
                    # 实际执行平仓（这里需要调用OKEx API）
                    # TODO: 调用 OKExTrader 执行平仓
                    
                    # 记录平仓动作
                    close_id = self.record_close_action(
                        pos['inst_id'],
                        pos['pos_side'],
                        close_size,
                        pos['current_price'],
                        reason,
                        'profitable'
                    )
                    action['close_id'] = close_id
                    action['status'] = 'executed'
                
                actions.append(action)
                continue
            
            # 检查是否应该平仓（回本）
            should_close, close_size, reason = self.check_should_close_breakeven_short(pos)
            
            if should_close:
                action = {
                    'inst_id': pos['inst_id'],
                    'pos_side': pos['pos_side'],
                    'current_size': pos['size'],
                    'close_size': close_size,
                    'close_price': pos['current_price'],
                    'profit_rate': pos['profit_rate'],
                    'close_type': 'breakeven',
                    'reason': reason,
                    'status': 'pending'
                }
                
                if not dry_run:
                    # 实际执行平仓
                    # TODO: 调用 OKExTrader 执行平仓
                    
                    # 记录平仓动作
                    close_id = self.record_close_action(
                        pos['inst_id'],
                        pos['pos_side'],
                        close_size,
                        pos['current_price'],
                        reason,
                        'breakeven'
                    )
                    action['close_id'] = close_id
                    action['status'] = 'executed'
                
                actions.append(action)
        
        return {
            'success': True,
            'message': f'扫描完成，发现 {len(actions)} 个需要平仓的仓位',
            'dry_run': dry_run,
            'actions': actions
        }
    
    def get_close_history(self, limit: int = 50) -> List[Dict]:
        """获取平仓历史"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # 先检查表是否存在
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS position_closes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inst_id TEXT NOT NULL,
            pos_side TEXT NOT NULL,
            close_size REAL NOT NULL,
            close_price REAL NOT NULL,
            close_type TEXT NOT NULL,
            reason TEXT,
            timestamp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        SELECT id, inst_id, pos_side, close_size, close_price,
               close_type, reason, timestamp, created_at
        FROM position_closes
        ORDER BY created_at DESC
        LIMIT ?
        ''', (limit,))
        
        closes = []
        for row in cursor.fetchall():
            closes.append({
                'id': row[0],
                'inst_id': row[1],
                'pos_side': row[2],
                'close_size': row[3],
                'close_price': row[4],
                'close_type': row[5],
                'reason': row[6],
                'timestamp': row[7],
                'created_at': row[8]
            })
        
        conn.close()
        return closes


def test_position_closer():
    """测试平仓管理器"""
    print("=" * 60)
    print("🔍 测试平仓管理器")
    print("=" * 60)
    print()
    
    closer = PositionCloser()
    
    # 1. 获取配置
    print("1. 系统配置")
    config = closer.get_config()
    print(f"   允许开空单: {config['allow_short']}")
    print(f"   允许锚点单: {config['allow_anchor']}")
    print()
    
    # 2. 获取锚点单
    print("2. 锚点单列表")
    anchors = closer.get_anchor_positions()
    if anchors:
        for anchor in anchors:
            print(f"   {anchor['inst_id']} {anchor['pos_side']}: {anchor['anchor_size']} @ {anchor['anchor_price']}")
    else:
        print("   暂无锚点单")
    print()
    
    # 3. 获取当前持仓
    print("3. 当前持仓")
    positions = closer.get_current_positions()
    if positions:
        for pos in positions:
            print(f"   {pos['inst_id']} {pos['pos_side']}: {pos['size']} @ {pos['avg_price']}, 浮盈: {pos['profit_rate']:.2f}%")
    else:
        print("   暂无持仓")
    print()
    
    # 4. 扫描需要平仓的仓位（模拟运行）
    print("4. 扫描平仓（模拟运行）")
    result = closer.scan_and_close_positions(dry_run=True)
    print(f"   结果: {result['message']}")
    
    if result['actions']:
        print(f"\n   发现 {len(result['actions'])} 个需要平仓的仓位：")
        for i, action in enumerate(result['actions'], 1):
            print(f"\n   平仓动作 #{i}:")
            print(f"     交易对: {action['inst_id']}")
            print(f"     方向: {action['pos_side']}")
            print(f"     当前持仓: {action['current_size']}")
            print(f"     平仓数量: {action['close_size']}")
            print(f"     平仓价格: {action['close_price']}")
            print(f"     浮盈率: {action['profit_rate']:.2f}%")
            print(f"     平仓类型: {action['close_type']}")
            print(f"     原因: {action['reason']}")
    else:
        print("   暂无需要平仓的仓位")
    
    print()
    print("✅ 测试完成")


if __name__ == '__main__':
    test_position_closer()
