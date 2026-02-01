#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多单自动开仓执行器
功能：当空单盈利≥40%时，按规则自动开多单
规则：
1. 单次开仓金额 = 可开仓额 × 10%
2. 开仓价格间隔 ≥ 0.5%
3. 单个币最多3次开仓
4. 单币上限 = 30%可开仓额
"""

import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库路径
TRADING_DB = '/home/user/webapp/trading_decision.db'
CRYPTO_DB = '/home/user/webapp/crypto_data.db'

class LongPositionExecutor:
    """多单自动开仓执行器"""
    
    def __init__(self):
        """初始化"""
        self.trading_db = TRADING_DB
        self.crypto_db = CRYPTO_DB
        self.open_percent = 10.0  # 单次开仓百分比：10%
        self.price_interval = 0.5  # 价格间隔：0.5%
        self.max_opens_per_coin = 3  # 单币最大开仓次数：3次
        self.max_single_coin_percent = 30.0  # 单币最大占比：30%
        
        print("🚀 多单自动开仓执行器启动")
        print(f"💰 单次开仓: 可开仓额 × {self.open_percent}%")
        print(f"📏 价格间隔: ≥ {self.price_interval}%")
        print(f"🔢 单币最大开仓次数: {self.max_opens_per_coin}次")
        print(f"📊 单币最大占比: {self.max_single_coin_percent}%可开仓额")
        print("=" * 60)
    
    def get_market_config(self) -> Dict:
        """获取市场配置"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM market_config ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'total_capital': row['total_capital'],
                    'position_limit_percent': row['position_limit_percent'],
                    'enabled': row['enabled']
                }
            else:
                # 默认配置
                return {
                    'total_capital': 1000.0,
                    'position_limit_percent': 60.0,
                    'enabled': False
                }
                
        except Exception as e:
            print(f"❌ 获取市场配置失败: {e}")
            return {
                'total_capital': 1000.0,
                'position_limit_percent': 60.0,
                'enabled': False
            }
    
    def calculate_open_amount(self) -> Tuple[float, float]:
        """计算开仓金额"""
        config = self.get_market_config()
        
        # 可开仓额 = 总本金 × 可开仓百分比
        available_capital = config['total_capital'] * config['position_limit_percent'] / 100
        
        # 单次开仓金额 = 可开仓额 × 10%
        open_amount = available_capital * self.open_percent / 100
        
        return open_amount, available_capital
    
    def get_long_position_count(self, inst_id: str) -> int:
        """获取该币种多单开仓次数"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) 
                FROM position_opens 
                WHERE inst_id = ? AND pos_side = 'long'
            ''', (inst_id,))
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            print(f"❌ 获取开仓次数失败: {e}")
            return 0
    
    def get_last_long_open_price(self, inst_id: str) -> Optional[float]:
        """获取该币种最后一次多单开仓价格"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT open_price 
                FROM position_opens 
                WHERE inst_id = ? AND pos_side = 'long'
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (inst_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row[0]
            return None
            
        except Exception as e:
            print(f"❌ 获取最后开仓价格失败: {e}")
            return None
    
    def get_coin_total_value(self, inst_id: str) -> float:
        """获取该币种多单总仓位价值"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT SUM(open_size * open_price) as total_value
                FROM position_opens 
                WHERE inst_id = ? AND pos_side = 'long'
            ''', (inst_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                return row[0]
            return 0.0
            
        except Exception as e:
            print(f"❌ 获取币种总仓位失败: {e}")
            return 0.0
    
    def get_current_price(self, inst_id: str) -> Optional[float]:
        """获取当前价格"""
        try:
            # 从inst_id提取symbol（例如：UNI-USDT-SWAP -> UNIUSDT）
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
            print(f"❌ 获取{inst_id}价格失败: {e}")
            return None
    
    def check_can_open_long(self, inst_id: str, current_price: float, open_amount: float, available_capital: float) -> Tuple[bool, str]:
        """检查是否可以开多单"""
        
        # 检查1：开仓次数
        open_count = self.get_long_position_count(inst_id)
        if open_count >= self.max_opens_per_coin:
            return False, f"已达到最大开仓次数（{open_count}/{self.max_opens_per_coin}次）"
        
        # 检查2：价格间隔
        last_price = self.get_last_long_open_price(inst_id)
        if last_price:
            price_diff_percent = abs((current_price - last_price) / last_price * 100)
            if price_diff_percent < self.price_interval:
                return False, f"价格间隔不足{self.price_interval}%（当前{price_diff_percent:.2f}%）"
        
        # 检查3：单币限制
        current_total = self.get_coin_total_value(inst_id)
        max_single_coin = available_capital * self.max_single_coin_percent / 100
        projected_total = current_total + open_amount
        
        if projected_total > max_single_coin:
            return False, f"超过单币种限制：当前{current_total:.2f}U + 新增{open_amount:.2f}U = {projected_total:.2f}U > 上限{max_single_coin:.2f}U"
        
        return True, "所有检查通过"
    
    def record_long_position(self, inst_id: str, open_price: float, open_size: float, 
                            open_amount: float, trigger_info: Dict) -> int:
        """记录多单开仓"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 获取当前开仓序号
            open_count = self.get_long_position_count(inst_id)
            open_sequence = open_count + 1
            
            # 插入开仓记录
            cursor.execute('''
            INSERT INTO position_opens 
            (inst_id, pos_side, open_price, open_size, open_percent, granularity, 
             total_positions, is_anchor, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                'long',
                open_price,
                open_size,
                self.open_percent,
                f'long_from_short_profit',  # 标记为"来自空单盈利"
                open_sequence,
                0,  # is_anchor=0，这是普通多单
                timestamp,
                timestamp
            ))
            
            position_id = cursor.lastrowid
            
            # 记录决策日志
            cursor.execute('''
            INSERT INTO trading_decisions
            (inst_id, pos_side, action, decision_type, current_size, target_size, 
             close_size, close_percent, profit_rate, current_price, reason, 
             executed, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                'long',
                'open',
                'long_from_short_profit',
                0,
                open_size,
                0,
                0,
                trigger_info.get('short_profit_rate', 0),
                open_price,
                f"空单{trigger_info.get('from_inst', inst_id)}盈利{trigger_info.get('short_profit_rate', 0):.2f}%触发，开多单{open_amount:.2f}U（第{open_sequence}次）",
                1,
                timestamp,
                timestamp
            ))
            
            conn.commit()
            conn.close()
            
            return position_id
            
        except Exception as e:
            print(f"❌ 记录开仓失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def execute_long_open(self, inst_id: str, trigger_info: Dict) -> Tuple[bool, str, Dict]:
        """执行多单开仓"""
        print(f"\n{'='*60}")
        print(f"🔄 处理多单开仓: {inst_id}")
        print(f"📊 触发原因: 空单{trigger_info.get('from_inst', inst_id)}盈利{trigger_info.get('short_profit_rate', 0):.2f}%")
        print(f"{'='*60}\n")
        
        # 1. 获取当前价格
        current_price = self.get_current_price(inst_id)
        if not current_price:
            msg = "无法获取当前价格"
            print(f"❌ {msg}")
            return False, msg, {}
        
        print(f"✅ 当前价格: {current_price:.4f}")
        
        # 2. 计算开仓金额
        open_amount, available_capital = self.calculate_open_amount()
        print(f"✅ 可开仓额: {available_capital:.2f} USDT")
        print(f"✅ 单次开仓: {open_amount:.2f} USDT（{self.open_percent}%）")
        
        # 3. 检查是否可以开仓
        can_open, reason = self.check_can_open_long(inst_id, current_price, open_amount, available_capital)
        if not can_open:
            print(f"❌ 无法开仓: {reason}")
            return False, reason, {}
        
        print(f"✅ 开仓检查: {reason}")
        
        # 4. 计算开仓数量
        open_size = open_amount / current_price
        print(f"✅ 开仓数量: {open_size:.4f} {inst_id.split('-')[0]}")
        
        # 5. 记录开仓
        position_id = self.record_long_position(
            inst_id=inst_id,
            open_price=current_price,
            open_size=open_size,
            open_amount=open_amount,
            trigger_info=trigger_info
        )
        
        if position_id > 0:
            print(f"✅ 开仓成功！持仓ID: #{position_id}")
            print(f"{'='*60}\n")
            
            result = {
                'position_id': position_id,
                'inst_id': inst_id,
                'pos_side': 'long',
                'open_price': current_price,
                'open_size': open_size,
                'open_amount': open_amount,
                'open_percent': self.open_percent,
                'trigger_from': trigger_info.get('from_inst', inst_id),
                'trigger_profit_rate': trigger_info.get('short_profit_rate', 0)
            }
            
            return True, "开仓成功", result
        else:
            msg = "记录开仓失败"
            print(f"❌ {msg}")
            return False, msg, {}
    
    def scan_and_execute(self) -> Dict:
        """扫描监控日志并执行开仓"""
        from long_position_monitor import LongPositionMonitor
        
        print(f"\n{'='*60}")
        print(f"🔍 开始扫描达到开仓条件的锚点单 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 1. 执行监控扫描
        monitor = LongPositionMonitor()
        scan_result = monitor.scan_positions()
        
        # 2. 获取达到开仓条件的币种
        ready_positions = [r for r in scan_result['results'] if r['status'] == 'ready_to_open']
        
        if not ready_positions:
            print("📭 暂无达到开仓条件的锚点单")
            return {
                'success': True,
                'total_scanned': scan_result['total'],
                'ready_to_open': 0,
                'executed': 0,
                'failed': 0,
                'results': []
            }
        
        print(f"🔥 找到 {len(ready_positions)} 个达到开仓条件的锚点单\n")
        
        # 3. 逐个执行开仓
        results = []
        executed_count = 0
        failed_count = 0
        
        for pos in ready_positions:
            inst_id = pos['inst_id']
            
            # 触发信息
            trigger_info = {
                'from_inst': inst_id,
                'short_profit_rate': pos['profit_rate'],
                'short_open_price': pos['open_price'],
                'current_price': pos['current_price']
            }
            
            # 执行开仓
            success, message, result = self.execute_long_open(inst_id, trigger_info)
            
            if success:
                executed_count += 1
            else:
                failed_count += 1
            
            results.append({
                'inst_id': inst_id,
                'success': success,
                'message': message,
                'result': result
            })
        
        # 4. 汇总
        print(f"{'='*60}")
        print(f"📊 执行完成汇总:")
        print(f"   扫描总数: {scan_result['total']} 个")
        print(f"   达到开仓条件: {len(ready_positions)} 个")
        print(f"   成功开仓: {executed_count} 个")
        print(f"   开仓失败: {failed_count} 个")
        print(f"{'='*60}\n")
        
        return {
            'success': True,
            'total_scanned': scan_result['total'],
            'ready_to_open': len(ready_positions),
            'executed': executed_count,
            'failed': failed_count,
            'results': results
        }

def main():
    """主函数"""
    executor = LongPositionExecutor()
    result = executor.scan_and_execute()
    
    # 显示详细结果
    if result['executed'] > 0:
        print("\n✅ 成功开仓的多单:")
        for r in result['results']:
            if r['success']:
                print(f"  - {r['inst_id']}: {r['message']}")
    
    if result['failed'] > 0:
        print("\n❌ 开仓失败的币种:")
        for r in result['results']:
            if not r['success']:
                print(f"  - {r['inst_id']}: {r['message']}")

if __name__ == "__main__":
    main()
