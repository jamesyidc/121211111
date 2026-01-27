#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单管理模块
提供锚点单的创建、更新、查询、关闭等管理功能
"""

import sqlite3
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/trading_decision.db'


class AnchorPositionManager:
    """锚点单管理器"""
    
    def __init__(self, db_path=None):
        """初始化锚点单管理器"""
        self.db_path = db_path or DB_PATH
    
    def create_anchor(self, inst_id, pos_side, anchor_size, anchor_price, notes=''):
        """
        创建锚点单
        
        Args:
            inst_id: 币种ID
            pos_side: 持仓方向 (long/short)
            anchor_size: 锚点单仓位大小
            anchor_price: 锚点单开仓价格
            notes: 备注
        
        Returns:
            (bool, str): (是否成功, 消息)
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # 检查是否已存在活跃锚点单
            cursor.execute('''
            SELECT id FROM anchor_positions
            WHERE inst_id = ? AND pos_side = ? AND status = 'active'
            ''', (inst_id, pos_side))
            
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return False, f"❌ {inst_id} {pos_side}方向已存在活跃锚点单"
            
            # 创建新锚点单
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            INSERT INTO anchor_positions (
                inst_id, pos_side, anchor_size, anchor_price,
                current_price, profit_rate, upl, status,
                open_time, update_time, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id, pos_side, anchor_size, anchor_price,
                anchor_price, 0.0, 0.0, 'active',
                timestamp, timestamp, notes
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 锚点单创建成功: {inst_id} {pos_side} {anchor_size}U @ {anchor_price}")
            return True, f"锚点单创建成功: {inst_id} {pos_side} {anchor_size}U @ {anchor_price}"
        
        except Exception as e:
            print(f"❌ 创建锚点单失败: {e}")
            return False, f"创建失败: {str(e)}"
    
    def update_anchor(self, inst_id, pos_side, current_price):
        """
        更新锚点单的当前价格和收益率
        
        Args:
            inst_id: 币种ID
            pos_side: 持仓方向
            current_price: 当前价格
        
        Returns:
            (bool, dict): (是否成功, 锚点单信息)
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # 获取锚点单
            cursor.execute('''
            SELECT id, anchor_price, anchor_size
            FROM anchor_positions
            WHERE inst_id = ? AND pos_side = ? AND status = 'active'
            ''', (inst_id, pos_side))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False, None
            
            anchor_id, anchor_price, anchor_size = row
            
            # 计算收益率和浮动盈亏
            if pos_side == 'long':
                profit_rate = ((current_price - anchor_price) / anchor_price) * 100
                upl = (current_price - anchor_price) * anchor_size
            else:  # short
                profit_rate = ((anchor_price - current_price) / anchor_price) * 100
                upl = (anchor_price - current_price) * anchor_size
            
            # 更新锚点单
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            UPDATE anchor_positions
            SET current_price = ?, profit_rate = ?, upl = ?, update_time = ?, updated_at = ?
            WHERE id = ?
            ''', (current_price, profit_rate, upl, timestamp, timestamp, anchor_id))
            
            conn.commit()
            conn.close()
            
            return True, {
                'id': anchor_id,
                'inst_id': inst_id,
                'pos_side': pos_side,
                'anchor_price': anchor_price,
                'anchor_size': anchor_size,
                'current_price': current_price,
                'profit_rate': profit_rate,
                'upl': upl,
                'update_time': timestamp
            }
        
        except Exception as e:
            print(f"❌ 更新锚点单失败: {e}")
            return False, None
    
    def get_anchor(self, inst_id, pos_side):
        """
        获取活跃的锚点单
        
        Args:
            inst_id: 币种ID
            pos_side: 持仓方向
        
        Returns:
            dict or None: 锚点单信息
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, inst_id, pos_side, anchor_size, anchor_price,
                   current_price, profit_rate, upl, status,
                   open_time, update_time, notes
            FROM anchor_positions
            WHERE inst_id = ? AND pos_side = ? AND status = 'active'
            ''', (inst_id, pos_side))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'inst_id': row[1],
                    'pos_side': row[2],
                    'anchor_size': row[3],
                    'anchor_price': row[4],
                    'current_price': row[5],
                    'profit_rate': row[6],
                    'upl': row[7],
                    'status': row[8],
                    'open_time': row[9],
                    'update_time': row[10],
                    'notes': row[11]
                }
            return None
        
        except Exception as e:
            print(f"❌ 获取锚点单失败: {e}")
            return None
    
    def get_all_anchors(self, status='active'):
        """
        获取所有锚点单
        
        Args:
            status: 状态筛选 (active/closed/all)
        
        Returns:
            list: 锚点单列表
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            if status == 'all':
                cursor.execute('''
                SELECT id, inst_id, pos_side, anchor_size, anchor_price,
                       current_price, profit_rate, upl, status,
                       open_time, update_time, close_time, notes
                FROM anchor_positions
                ORDER BY updated_at DESC
                ''')
            else:
                cursor.execute('''
                SELECT id, inst_id, pos_side, anchor_size, anchor_price,
                       current_price, profit_rate, upl, status,
                       open_time, update_time, close_time, notes
                FROM anchor_positions
                WHERE status = ?
                ORDER BY updated_at DESC
                ''', (status,))
            
            rows = cursor.fetchall()
            conn.close()
            
            anchors = []
            for row in rows:
                anchors.append({
                    'id': row[0],
                    'inst_id': row[1],
                    'pos_side': row[2],
                    'anchor_size': row[3],
                    'anchor_price': row[4],
                    'current_price': row[5],
                    'profit_rate': row[6],
                    'upl': row[7],
                    'status': row[8],
                    'open_time': row[9],
                    'update_time': row[10],
                    'close_time': row[11],
                    'notes': row[12]
                })
            
            return anchors
        
        except Exception as e:
            print(f"❌ 获取锚点单列表失败: {e}")
            return []
    
    def close_anchor(self, inst_id, pos_side, final_price, notes=''):
        """
        关闭锚点单
        
        Args:
            inst_id: 币种ID
            pos_side: 持仓方向
            final_price: 平仓价格
            notes: 关闭备注
        
        Returns:
            (bool, str): (是否成功, 消息)
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # 获取锚点单
            cursor.execute('''
            SELECT id, anchor_price, anchor_size
            FROM anchor_positions
            WHERE inst_id = ? AND pos_side = ? AND status = 'active'
            ''', (inst_id, pos_side))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False, f"❌ 未找到活跃的锚点单: {inst_id} {pos_side}"
            
            anchor_id, anchor_price, anchor_size = row
            
            # 计算最终收益
            if pos_side == 'long':
                profit_rate = ((final_price - anchor_price) / anchor_price) * 100
                upl = (final_price - anchor_price) * anchor_size
            else:  # short
                profit_rate = ((anchor_price - final_price) / anchor_price) * 100
                upl = (anchor_price - final_price) * anchor_size
            
            # 关闭锚点单
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            UPDATE anchor_positions
            SET current_price = ?, profit_rate = ?, upl = ?,
                status = 'closed', close_time = ?, update_time = ?,
                notes = ?, updated_at = ?
            WHERE id = ?
            ''', (
                final_price, profit_rate, upl,
                timestamp, timestamp,
                notes or '手动关闭', timestamp,
                anchor_id
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 锚点单已关闭: {inst_id} {pos_side} 收益率{profit_rate:.2f}% 盈亏{upl:.2f}U")
            return True, f"锚点单已关闭: 收益率{profit_rate:.2f}% 盈亏{upl:.2f}U"
        
        except Exception as e:
            print(f"❌ 关闭锚点单失败: {e}")
            return False, f"关闭失败: {str(e)}"
    
    def is_anchor_position(self, inst_id, pos_side):
        """
        检查是否为锚点单
        
        Args:
            inst_id: 币种ID
            pos_side: 持仓方向
        
        Returns:
            bool: 是否为锚点单
        """
        anchor = self.get_anchor(inst_id, pos_side)
        return anchor is not None
    
    def get_anchor_statistics(self):
        """
        获取锚点单统计信息
        
        Returns:
            dict: 统计信息
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # 活跃锚点单数量
            cursor.execute('SELECT COUNT(*) FROM anchor_positions WHERE status = "active"')
            active_count = cursor.fetchone()[0]
            
            # 已关闭锚点单数量
            cursor.execute('SELECT COUNT(*) FROM anchor_positions WHERE status = "closed"')
            closed_count = cursor.fetchone()[0]
            
            # 活跃锚点单总盈亏
            cursor.execute('SELECT SUM(upl) FROM anchor_positions WHERE status = "active"')
            active_upl = cursor.fetchone()[0] or 0
            
            # 已关闭锚点单总盈亏
            cursor.execute('SELECT SUM(upl) FROM anchor_positions WHERE status = "closed"')
            closed_upl = cursor.fetchone()[0] or 0
            
            # 平均收益率
            cursor.execute('SELECT AVG(profit_rate) FROM anchor_positions WHERE status = "active"')
            avg_profit_rate = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'active_count': active_count,
                'closed_count': closed_count,
                'total_count': active_count + closed_count,
                'active_upl': active_upl,
                'closed_upl': closed_upl,
                'total_upl': active_upl + closed_upl,
                'avg_profit_rate': avg_profit_rate
            }
        
        except Exception as e:
            print(f"❌ 获取锚点单统计失败: {e}")
            return {
                'active_count': 0,
                'closed_count': 0,
                'total_count': 0,
                'active_upl': 0,
                'closed_upl': 0,
                'total_upl': 0,
                'avg_profit_rate': 0
            }


if __name__ == '__main__':
    print("=" * 80)
    print("锚点单管理模块测试")
    print("=" * 80)
    
    manager = AnchorPositionManager()
    
    # 测试1: 创建锚点单
    print("\n测试1: 创建锚点单")
    success, msg = manager.create_anchor(
        inst_id='BTC-USDT-SWAP',
        pos_side='short',
        anchor_size=10.0,
        anchor_price=50000.0,
        notes='测试锚点单'
    )
    print(f"结果: {msg}")
    
    # 测试2: 更新锚点单
    print("\n测试2: 更新锚点单")
    success, anchor = manager.update_anchor('BTC-USDT-SWAP', 'short', 49500.0)
    if success:
        print(f"收益率: {anchor['profit_rate']:.2f}%")
        print(f"浮动盈亏: {anchor['upl']:.2f}U")
    
    # 测试3: 获取锚点单
    print("\n测试3: 获取锚点单")
    anchor = manager.get_anchor('BTC-USDT-SWAP', 'short')
    if anchor:
        print(f"锚点单: {anchor['inst_id']} {anchor['pos_side']}")
        print(f"仓位: {anchor['anchor_size']}U @ {anchor['anchor_price']}")
        print(f"当前: {anchor['current_price']} 收益率: {anchor['profit_rate']:.2f}%")
    
    # 测试4: 获取统计
    print("\n测试4: 获取统计信息")
    stats = manager.get_anchor_statistics()
    print(f"活跃锚点单: {stats['active_count']}")
    print(f"总盈亏: {stats['total_upl']:.2f}U")
    print(f"平均收益率: {stats['avg_profit_rate']:.2f}%")
    
    print("\n" + "=" * 80)
    print("✅ 锚点单管理模块测试完成")
    print("=" * 80)
