#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单纠错系统
功能：检测极端盈利的锚点单，并进行纠错处理
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库路径
TRADING_DB = '/home/user/webapp/trading_decision.db'
ANCHOR_DB = '/home/user/webapp/anchor_system.db'
CRYPTO_DB = '/home/user/webapp/crypto_data.db'

class AnchorCorrectionSystem:
    """锚点单纠错系统"""
    
    def __init__(self):
        """初始化"""
        self.trading_db = TRADING_DB
        self.anchor_db = ANCHOR_DB
        self.crypto_db = CRYPTO_DB
        self.profit_threshold = 100.0  # 盈利阈值100%
        self.days_threshold = 15  # 时间阈值15天
        
    def get_anchor_positions(self) -> List[Dict]:
        """获取所有锚点单"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    id,
                    inst_id,
                    pos_side,
                    open_price,
                    open_size,
                    open_percent,
                    timestamp,
                    created_at
                FROM position_opens
                WHERE is_anchor = 1
                ORDER BY created_at DESC
            ''')
            
            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'id': row['id'],
                    'inst_id': row['inst_id'],
                    'pos_side': row['pos_side'],
                    'open_price': row['open_price'],
                    'open_size': row['open_size'],
                    'open_percent': row['open_percent'],
                    'timestamp': row['timestamp'],
                    'created_at': row['created_at']
                })
            
            conn.close()
            return positions
            
        except Exception as e:
            print(f"❌ 获取锚点单失败: {e}")
            return []
    
    def get_current_price(self, inst_id: str) -> Optional[float]:
        """获取当前价格"""
        try:
            # 先从anchor_system.db获取
            conn = sqlite3.connect(self.anchor_db, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT mark_price
                FROM anchor_monitors
                WHERE inst_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (inst_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row[0]
            
            # 如果没有，从crypto_data.db获取
            symbol = inst_id.replace('-USDT-SWAP', 'USDT')
            conn = sqlite3.connect(self.crypto_db, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT current_price
                FROM support_resistance_levels
                WHERE symbol = ?
                ORDER BY record_time DESC
                LIMIT 1
            ''', (symbol,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row[0]
            
            return None
            
        except Exception as e:
            print(f"❌ 获取价格失败 {inst_id}: {e}")
            return None
    
    def calculate_profit_rate(self, open_price: float, current_price: float, pos_side: str) -> float:
        """计算收益率（含10x杠杆）"""
        if pos_side == 'long':
            return (current_price - open_price) / open_price * 10 * 100
        else:  # short
            return (open_price - current_price) / open_price * 10 * 100
    
    def check_days_since_open(self, created_at: str) -> int:
        """计算开仓天数"""
        try:
            # 解析时间字符串
            open_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            open_time = BEIJING_TZ.localize(open_time)
            
            # 当前时间
            now = datetime.now(BEIJING_TZ)
            
            # 计算天数
            days = (now - open_time).days
            return days
            
        except Exception as e:
            print(f"❌ 计算开仓天数失败: {e}")
            return 0
    
    def get_related_positions(self, inst_id: str) -> List[Dict]:
        """获取关联的所有持仓（包括多单）"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取所有相关持仓（锚点单 + 多单）
            cursor.execute('''
                SELECT 
                    id,
                    inst_id,
                    pos_side,
                    open_price,
                    open_size,
                    open_percent,
                    is_anchor,
                    granularity,
                    timestamp
                FROM position_opens
                WHERE inst_id = ?
                ORDER BY id DESC
            ''', (inst_id,))
            
            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'id': row['id'],
                    'inst_id': row['inst_id'],
                    'pos_side': row['pos_side'],
                    'open_price': row['open_price'],
                    'open_size': row['open_size'],
                    'open_percent': row['open_percent'],
                    'is_anchor': row['is_anchor'],
                    'granularity': row['granularity'],
                    'timestamp': row['timestamp']
                })
            
            conn.close()
            return positions
            
        except Exception as e:
            print(f"❌ 获取关联持仓失败: {e}")
            return []
    
    def scan_extreme_anchors(self) -> List[Dict]:
        """扫描极端盈利的锚点单"""
        print("=" * 80)
        print("🔍 锚点单纠错系统 - 扫描极端盈利锚点单")
        print("=" * 80)
        print(f"📊 触发条件:")
        print(f"   1️⃣  盈利 ≥ {self.profit_threshold}%（极端情况）")
        print(f"   2️⃣  开仓时间 > {self.days_threshold}天（过时）")
        print("=" * 80)
        print()
        
        anchors = self.get_anchor_positions()
        extreme_anchors = []
        
        for anchor in anchors:
            inst_id = anchor['inst_id']
            open_price = anchor['open_price']
            pos_side = anchor['pos_side']
            created_at = anchor['created_at']
            
            # 获取当前价格
            current_price = self.get_current_price(inst_id)
            if not current_price:
                continue
            
            # 计算收益率
            profit_rate = self.calculate_profit_rate(open_price, current_price, pos_side)
            
            # 计算开仓天数
            days = self.check_days_since_open(created_at)
            
            # 检查是否需要纠错
            if profit_rate >= self.profit_threshold and days > self.days_threshold:
                # 获取关联持仓
                related_positions = self.get_related_positions(inst_id)
                
                extreme_anchors.append({
                    'anchor': anchor,
                    'current_price': current_price,
                    'profit_rate': profit_rate,
                    'days': days,
                    'related_positions': related_positions
                })
                
                print(f"🚨 发现极端盈利锚点单:")
                print(f"   币种: {inst_id}")
                print(f"   方向: {pos_side}")
                print(f"   开仓价: {open_price}")
                print(f"   当前价: {current_price}")
                print(f"   收益率: {profit_rate:.2f}%")
                print(f"   开仓天数: {days}天")
                print(f"   关联持仓: {len(related_positions)}个")
                print()
        
        print(f"📊 扫描结果: 共找到 {len(extreme_anchors)} 个需要纠错的锚点单")
        print("=" * 80)
        print()
        
        return extreme_anchors
    
    def close_position(self, position_id: int, inst_id: str, pos_side: str, reason: str) -> bool:
        """关闭持仓"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 删除持仓记录
            cursor.execute('''
                DELETE FROM position_opens
                WHERE id = ?
            ''', (position_id,))
            
            # 记录平仓决策
            cursor.execute('''
                INSERT INTO trading_decisions (
                    inst_id,
                    pos_side,
                    action,
                    decision_type,
                    reason,
                    executed,
                    timestamp,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                'close',
                'anchor_correction',
                reason,
                1,
                now,
                now
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ 关闭持仓失败: {e}")
            return False
    
    def recreate_anchor(self, inst_id: str, pos_side: str, current_price: float) -> bool:
        """重新创建锚点单"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 创建新锚点单
            cursor.execute('''
                INSERT INTO position_opens (
                    inst_id,
                    pos_side,
                    open_price,
                    open_size,
                    open_percent,
                    is_anchor,
                    total_positions,
                    timestamp,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                current_price,
                1.0,  # 默认仓位
                1.0,  # 默认占比1%
                1,
                1,
                now,
                now
            ))
            
            new_id = cursor.lastrowid
            
            # 记录决策
            cursor.execute('''
                INSERT INTO trading_decisions (
                    inst_id,
                    pos_side,
                    action,
                    decision_type,
                    current_price,
                    reason,
                    executed,
                    timestamp,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                'open',
                'anchor_correction',
                current_price,
                f'纠错系统：重新创建锚点单（新价格{current_price}）',
                1,
                now,
                now
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 重新创建锚点单: {inst_id}, 新价格={current_price}, ID={new_id}")
            return True
            
        except Exception as e:
            print(f"❌ 重新创建锚点单失败: {e}")
            return False
    
    def correct_anchor(self, extreme_anchor: Dict) -> Dict:
        """纠错单个锚点单"""
        anchor = extreme_anchor['anchor']
        inst_id = anchor['inst_id']
        pos_side = anchor['pos_side']
        current_price = extreme_anchor['current_price']
        profit_rate = extreme_anchor['profit_rate']
        days = extreme_anchor['days']
        related_positions = extreme_anchor['related_positions']
        
        print("=" * 80)
        print(f"🔧 开始纠错: {inst_id}")
        print("=" * 80)
        print(f"📊 锚点单信息:")
        print(f"   盈利率: {profit_rate:.2f}%")
        print(f"   开仓天数: {days}天")
        print(f"   关联持仓: {len(related_positions)}个")
        print()
        
        closed_count = 0
        failed_count = 0
        
        # 1. 关闭所有关联持仓
        print("📍 步骤1: 关闭所有关联持仓")
        for pos in related_positions:
            reason = f"纠错系统：极端盈利{profit_rate:.2f}%，开仓{days}天，重置锚点单"
            
            if self.close_position(pos['id'], pos['inst_id'], pos['pos_side'], reason):
                print(f"   ✅ 已关闭: ID={pos['id']}, {pos['pos_side']}, 价格={pos['open_price']}")
                closed_count += 1
            else:
                print(f"   ❌ 关闭失败: ID={pos['id']}")
                failed_count += 1
        
        print()
        
        # 2. 重新创建锚点单
        print("📍 步骤2: 重新创建锚点单")
        recreate_success = self.recreate_anchor(inst_id, pos_side, current_price)
        
        print()
        print("=" * 80)
        print(f"📊 纠错完成:")
        print(f"   关闭持仓: {closed_count}个")
        print(f"   失败: {failed_count}个")
        print(f"   重建锚点: {'✅ 成功' if recreate_success else '❌ 失败'}")
        print("=" * 80)
        print()
        
        return {
            'inst_id': inst_id,
            'closed_count': closed_count,
            'failed_count': failed_count,
            'recreate_success': recreate_success
        }
    
    def correct_all(self) -> Dict:
        """纠错所有极端盈利锚点单"""
        extreme_anchors = self.scan_extreme_anchors()
        
        if not extreme_anchors:
            print("✅ 没有需要纠错的锚点单")
            return {
                'total': 0,
                'corrected': 0,
                'failed': 0,
                'results': []
            }
        
        results = []
        corrected_count = 0
        failed_count = 0
        
        for extreme_anchor in extreme_anchors:
            result = self.correct_anchor(extreme_anchor)
            results.append(result)
            
            if result['recreate_success']:
                corrected_count += 1
            else:
                failed_count += 1
        
        print("=" * 80)
        print("🎉 纠错系统执行完成")
        print("=" * 80)
        print(f"📊 执行结果:")
        print(f"   扫描锚点单: {len(extreme_anchors)}个")
        print(f"   成功纠错: {corrected_count}个")
        print(f"   失败: {failed_count}个")
        print("=" * 80)
        
        return {
            'total': len(extreme_anchors),
            'corrected': corrected_count,
            'failed': failed_count,
            'results': results
        }

def main():
    """主函数"""
    correction = AnchorCorrectionSystem()
    result = correction.correct_all()
    
    import json
    print("\n📄 执行结果JSON:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
