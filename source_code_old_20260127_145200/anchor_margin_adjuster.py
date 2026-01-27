#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单保证金调整器
功能：检查并调整保证金>2U的锚点单到1U
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DB_PATH = '/home/user/webapp/trading_decision.db'

class AnchorMarginAdjuster:
    """锚点单保证金调整器"""
    
    def __init__(self, db_path: str = DB_PATH):
        """初始化"""
        self.db_path = db_path
        self.max_margin = 2.0  # 最大保证金
        self.target_margin = 1.0  # 目标保证金
    
    def scan_over_limit_anchors(self) -> List[Dict]:
        """
        扫描保证金超过2U的锚点单
        
        Returns:
            list: 需要调整的锚点单列表
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT inst_id, pos_side, open_size, open_price, margin, 
                   mark_price, profit_rate, lever, is_anchor
            FROM position_opens
            WHERE is_anchor = 1 AND margin > ?
            ORDER BY margin DESC
            ''', (self.max_margin,))
            
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                position = dict(row)
                
                # 计算需要平仓的数量
                adjustment = self.calculate_adjustment(position)
                
                result = {
                    'inst_id': position['inst_id'],
                    'pos_side': position['pos_side'],
                    'current_size': position['open_size'],
                    'current_margin': position['margin'],
                    'target_margin': self.target_margin,
                    'close_size': adjustment['close_size'],
                    'close_percent': adjustment['close_percent'],
                    'remaining_size': adjustment['remaining_size'],
                    'remaining_margin': adjustment['remaining_margin'],
                    'profit_rate': position['profit_rate'],
                    'reason': f'保证金 {position["margin"]:.4f}U 超过限制 {self.max_margin}U，需调整到 {self.target_margin}U',
                    'decision_log': {
                        'step1': f'🔴 检测到超限: 当前保证金 {position["margin"]:.4f}U > {self.max_margin}U',
                        'step2': f'📊 当前仓位: {position["open_size"]:.4f} 张 ({position["margin"]:.2f} USDT)',
                        'step3': f'🎯 目标保证金: {self.target_margin} USDT',
                        'step4': f'💰 需平仓: {adjustment["close_size"]:.4f} 张 ({adjustment["close_percent"]:.1f}%)',
                        'step5': f'✅ 调整后: {adjustment["remaining_size"]:.4f} 张 ({adjustment["remaining_margin"]:.2f} USDT)'
                    }
                }
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logging.error(f"❌ 扫描失败: {e}")
            return []
    
    def calculate_adjustment(self, position: Dict) -> Dict:
        """
        计算调整方案
        
        Args:
            position: 持仓信息
        
        Returns:
            dict: 调整方案
        """
        current_margin = position['margin']
        current_size = position['open_size']
        
        # 计算需要保留的比例
        target_ratio = self.target_margin / current_margin
        
        # 计算保留和平仓的数量
        remaining_size = current_size * target_ratio
        close_size = current_size - remaining_size
        close_percent = (close_size / current_size) * 100
        
        return {
            'close_size': close_size,
            'close_percent': close_percent,
            'remaining_size': remaining_size,
            'remaining_margin': self.target_margin
        }
    
    def save_adjustment_log(self, adjustment: Dict) -> int:
        """
        保存调整日志到止盈止损表（因为这是平仓操作）
        
        Args:
            adjustment: 调整数据
        
        Returns:
            int: 日志ID
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 记录到止盈止损决策日志表
            cursor.execute('''
            INSERT INTO stop_profit_loss_decision_logs (
                inst_id, pos_side, trigger_type, action, 
                remaining_position, close_amount, avg_price, current_price,
                profit_rate, trigger_reason, decision_log, trigger_time, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                adjustment['inst_id'],
                adjustment['pos_side'],
                'anchor_margin_adjust',  # 类型：锚点单保证金调整
                'close',
                adjustment['remaining_size'],
                adjustment['close_size'],
                0,  # avg_price（从持仓获取）
                0,  # current_price（从持仓获取）
                adjustment['profit_rate'],
                adjustment['reason'],
                json.dumps(adjustment['decision_log'], ensure_ascii=False),
                timestamp,
                timestamp
            ))
            
            log_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logging.info(f"✅ 调整日志已保存: ID={log_id}")
            return log_id
            
        except Exception as e:
            logging.error(f"❌ 保存调整日志失败: {e}")
            return 0
    
    def execute_adjustment(self, inst_id: str, pos_side: str, close_size: float, dry_run: bool = True) -> bool:
        """
        执行调整（模拟）
        
        Args:
            inst_id: 币种
            pos_side: 方向
            close_size: 平仓数量
            dry_run: 是否模拟执行
        
        Returns:
            bool: 是否成功
        """
        if dry_run:
            logging.info(f"🔶 模拟执行: {inst_id} {pos_side} 平仓 {close_size:.4f} 张")
            return True
        
        # TODO: 对接OKEx API实际执行平仓
        # from okex_trader import OKexTrader
        # trader = OKexTrader()
        # return trader.close_position(inst_id, pos_side, close_size)
        
        logging.warning("⚠️ 实际执行需要对接OKEx API")
        return False
    
    def adjust_all_over_limit(self, dry_run: bool = True) -> Dict:
        """
        调整所有超限的锚点单
        
        Args:
            dry_run: 是否模拟执行
        
        Returns:
            dict: 执行结果
        """
        # 1. 扫描超限锚点单
        over_limit = self.scan_over_limit_anchors()
        
        if not over_limit:
            logging.info("✅ 所有锚点单保证金都在限制内（<= 2U）")
            return {
                'success': True,
                'count': 0,
                'message': '无需调整'
            }
        
        logging.info(f"⚠️  发现 {len(over_limit)} 个超限锚点单")
        
        # 2. 逐个调整
        adjusted = []
        failed = []
        
        for item in over_limit:
            logging.info(f"\n处理: {item['inst_id']} {item['pos_side']}")
            logging.info(f"  当前保证金: {item['current_margin']:.4f} USDT")
            logging.info(f"  需平仓: {item['close_size']:.4f} 张 ({item['close_percent']:.1f}%)")
            logging.info(f"  调整后: {item['remaining_margin']:.2f} USDT")
            
            # 执行调整
            success = self.execute_adjustment(
                item['inst_id'],
                item['pos_side'],
                item['close_size'],
                dry_run=dry_run
            )
            
            if success:
                # 保存日志
                self.save_adjustment_log(item)
                adjusted.append(item)
            else:
                failed.append(item)
        
        return {
            'success': len(failed) == 0,
            'count': len(adjusted),
            'adjusted': adjusted,
            'failed': failed,
            'message': f'成功调整 {len(adjusted)} 个，失败 {len(failed)} 个'
        }

def main():
    """主函数"""
    print("=" * 60)
    print("锚点单保证金检查与调整")
    print("=" * 60)
    
    adjuster = AnchorMarginAdjuster()
    
    # 1. 扫描超限锚点单
    print("\n1️⃣  扫描保证金超过2U的锚点单...\n")
    over_limit = adjuster.scan_over_limit_anchors()
    
    if not over_limit:
        print("✅ 所有锚点单保证金都在限制内（<= 2U）")
        print("\n当前锚点单列表:")
        
        # 显示所有锚点单
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT inst_id, margin, profit_rate
        FROM position_opens
        WHERE is_anchor = 1
        ORDER BY margin DESC
        ''')
        
        anchors = cursor.fetchall()
        conn.close()
        
        for inst_id, margin, profit in anchors:
            print(f"  ✅ {inst_id}: {margin:.4f} USDT (盈亏: {profit:.2f}%)")
        
        return
    
    # 2. 显示需要调整的锚点单
    print(f"⚠️  发现 {len(over_limit)} 个需要调整的锚点单:\n")
    
    for item in over_limit:
        print(f"【{item['inst_id']}】")
        print(f"  当前保证金: {item['current_margin']:.4f} USDT")
        print(f"  盈亏: {item['profit_rate']:.2f}%")
        print(f"  调整方案:")
        for key, value in item['decision_log'].items():
            print(f"    {value}")
        print()
    
    # 3. 询问是否执行
    print("=" * 60)
    response = input("是否执行调整？(yes/no，默认dry_run): ")
    
    if response.lower() in ['yes', 'y']:
        dry_run_response = input("模拟执行(dry_run)？(yes/no，默认yes): ")
        dry_run = dry_run_response.lower() not in ['no', 'n']
        
        print("\n2️⃣  开始调整...\n")
        result = adjuster.adjust_all_over_limit(dry_run=dry_run)
        
        print("\n" + "=" * 60)
        print(f"✅ 调整完成: {result['message']}")
        print("=" * 60)
    else:
        print("\n⏭️  跳过调整")

if __name__ == '__main__':
    main()
