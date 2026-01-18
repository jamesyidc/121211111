#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单自动维护守护进程
功能：监控锚点单，当亏损≥10%时自动触发维护
维护逻辑：补仓10倍 → 立即平掉95%
"""

import sqlite3
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import pytz
import sys

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库路径
TRADING_DB = '/home/user/webapp/trading_decision.db'
ANCHOR_DB = '/home/user/webapp/anchor_system.db'

# 交易模式配置
# 可选值: 'paper' (模拟交易) 或 'live' (实盘交易)
TRADE_MODE = 'paper'  # 默认使用模拟交易（模拟盘）

class AnchorMaintenanceDaemon:
    """锚点单自动维护守护进程"""
    
    def __init__(self, trade_mode='paper'):
        """初始化"""
        self.trading_db = TRADING_DB
        self.anchor_db = ANCHOR_DB
        self.trade_mode = trade_mode  # 交易模式：paper 或 live
        self.check_interval = 30  # 30秒检查一次
        print("🚀 锚点单自动维护守护进程启动")
        print(f"📊 交易模式: {'🧪 模拟交易 (Paper Trading)' if trade_mode == 'paper' else '💰 实盘交易 (Live Trading)'}")
        print(f"📊 检查间隔: {self.check_interval}秒")
        print(f"🎯 触发条件: 亏损 ≥ 10%")
        print(f"💰 补仓倍数: 10倍")
        print(f"📉 平仓策略: 保留≤2U保证金")
        print("=" * 60)
    
    def get_anchor_positions(self) -> List[Dict]:
        """获取所有锚点单持仓"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取所有开仓的锚点单（仅查询当前交易模式的数据）
            cursor.execute('''
            SELECT 
                inst_id,
                pos_side,
                open_size,
                open_price,
                open_percent,
                total_positions,
                timestamp,
                created_at
            FROM position_opens
            WHERE is_anchor = 1 
              AND (trade_mode = ? OR trade_mode IS NULL)
            ORDER BY created_at DESC
            ''', (self.trade_mode,))
            
            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'inst_id': row['inst_id'],
                    'pos_side': row['pos_side'],
                    'open_size': row['open_size'],
                    'open_price': row['open_price'],
                    'open_percent': row['open_percent'],
                    'total_positions': row['total_positions'],
                    'timestamp': row['timestamp'],
                    'created_at': row['created_at']
                })
            
            conn.close()
            return positions
            
        except Exception as e:
            print(f"❌ 获取锚点单持仓失败: {e}")
            return []
    
    def get_current_price(self, inst_id: str) -> Optional[float]:
        """获取当前价格 - 从模拟交易数据库获取"""
        try:
            # 连接 crypto_data.db 获取模拟交易价格
            crypto_conn = sqlite3.connect('/home/user/webapp/crypto_data.db', timeout=5.0)
            crypto_cursor = crypto_conn.cursor()
            
            # 转换symbol格式: LDO-USDT-SWAP -> LDOUSDT
            symbol = inst_id.replace('-USDT-SWAP', 'USDT')
            
            crypto_cursor.execute('''
                SELECT current_price FROM support_resistance_levels 
                WHERE symbol = ? 
                ORDER BY record_time DESC LIMIT 1
            ''', (symbol,))
            
            price_row = crypto_cursor.fetchone()
            crypto_conn.close()
            
            if price_row and price_row[0]:
                return float(price_row[0])
            
            return None
            
        except Exception as e:
            print(f"❌ 获取价格失败 {inst_id}: {e}")
            return None
    
    def has_maintenance_record(self, inst_id: str, pos_side: str) -> bool:
        """检查是否已经维护过（锚点单只维护一次）"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT COUNT(*) as count
            FROM position_adds
            WHERE inst_id = ?
              AND pos_side = ?
              AND add_percent >= 900  -- 10倍补仓的特征
            ''', (inst_id, pos_side))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            print(f"❌ 检查维护记录失败: {e}")
            return False
    
    def calculate_profit_rate(self, open_price: float, current_price: float, pos_side: str) -> float:
        """计算收益率（含10x杠杆）"""
        if pos_side == 'long':
            return (current_price - open_price) / open_price * 10 * 100
        else:  # short
            return (open_price - current_price) / open_price * 10 * 100
    
    def check_single_position(self, position: Dict) -> Optional[Dict]:
        """检查单个锚点单是否需要维护或监控"""
        inst_id = position['inst_id']
        pos_side = position['pos_side']
        open_price = position['open_price']
        
        # 1. 检查是否已经维护过
        if self.has_maintenance_record(inst_id, pos_side):
            return None
        
        # 2. 获取当前价格
        current_price = self.get_current_price(inst_id)
        if not current_price:
            return None
        
        # 3. 计算收益率
        profit_rate = self.calculate_profit_rate(open_price, current_price, pos_side)
        
        # 4. 检查是否需要提前监控（亏损≥8%）或触发维护（亏损≥10%）
        if profit_rate <= -10.0:
            # 触发维护
            return {
                'inst_id': inst_id,
                'pos_side': pos_side,
                'open_price': open_price,
                'current_price': current_price,
                'profit_rate': profit_rate,
                'open_size': position['open_size'],
                'open_percent': position['open_percent'],
                'need_maintenance': True,
                'alert_level': 'critical'  # 严重告警
            }
        elif profit_rate <= -8.0:
            # 提前监控
            return {
                'inst_id': inst_id,
                'pos_side': pos_side,
                'open_price': open_price,
                'current_price': current_price,
                'profit_rate': profit_rate,
                'open_size': position['open_size'],
                'open_percent': position['open_percent'],
                'need_maintenance': False,
                'alert_level': 'warning'  # 预警
            }
        
        return None
    
    def record_maintenance_trigger(self, maintenance: Dict) -> bool:
        """记录维护触发决策"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 记录到trading_decisions表
            cursor.execute('''
            INSERT INTO trading_decisions (
                inst_id,
                pos_side,
                action,
                decision_type,
                current_size,
                target_size,
                close_size,
                close_percent,
                profit_rate,
                current_price,
                reason,
                executed,
                timestamp,
                created_at,
                trade_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                maintenance['inst_id'],
                maintenance['pos_side'],
                'maintenance',  # 维护动作
                'anchor_maintenance',  # 锚点维护
                maintenance['open_size'],
                maintenance['open_size'] * 0.05,  # 目标保留5%
                maintenance['open_size'] * 10.95,  # 补仓10倍后平掉95%
                95.0,  # 平仓95%
                maintenance['profit_rate'],
                maintenance['current_price'],
                f"锚点单亏损{maintenance['profit_rate']:.2f}%，触发维护：补仓10倍+平掉95%",
                0,  # 待执行
                now,
                now,
                self.trade_mode  # 交易模式
            ))
            
            decision_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            print(f"✅ 记录维护触发决策 #{decision_id}: {maintenance['inst_id']} 亏损{maintenance['profit_rate']:.2f}%")
            return decision_id
            
        except Exception as e:
            print(f"❌ 记录维护决策失败: {e}")
            return None
    
    def execute_maintenance(self, maintenance: Dict, decision_id: int) -> bool:
        """执行维护操作：补仓10倍 + 平仓到剩余≤2U"""
        try:
            inst_id = maintenance['inst_id']
            pos_side = maintenance['pos_side']
            open_size = maintenance['open_size']
            open_price = maintenance['open_price']
            current_price = maintenance['current_price']
            
            print(f"\n🔧 开始执行维护: {inst_id}")
            
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 1. 记录补仓（10倍原持仓）
            add_size = open_size * 10
            cursor.execute('''
            INSERT INTO position_adds (
                inst_id,
                pos_side,
                add_size,
                add_price,
                add_percent,
                profit_rate_trigger,
                level,
                total_size_after,
                status,
                timestamp,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                add_size,
                current_price,
                1000.0,  # 10倍 = 1000%
                maintenance['profit_rate'],
                0,  # 维护补仓level=0
                open_size * 11,  # 补仓后总量
                'executed',  # 状态为已执行
                now,
                now
            ))
            
            add_id = cursor.lastrowid
            print(f"  1️⃣  补仓记录 #{add_id}: {add_size:.4f} @ {current_price:.4f}")
            
            # 2. 记录平仓（保留不超过2U）
            # 计算平仓数量：补仓后总量 = 原持仓 + 10倍补仓 = 11倍原持仓
            # 保留不超过2U保证金对应的持仓量
            total_after_add = open_size * 11  # 补仓后总量
            total_margin_after_add = total_after_add * current_price / 10  # 10x杠杆，总保证金
            
            # 计算保留量：目标2U，但不超过总保证金
            target_remaining_margin = min(2.0, total_margin_after_add)  # 目标保留2U，但不超过总额
            remain_size = (target_remaining_margin * 10) / current_price  # 保证金在10x杠杆下对应的持仓量
            
            # 平仓数量 = 总量 - 保留量
            close_size = total_after_add - remain_size
            close_percent = (close_size / total_after_add) * 100  # 计算平仓百分比
            
            cursor.execute('''
            INSERT INTO position_closes (
                inst_id,
                pos_side,
                close_size,
                close_price,
                close_reason,
                profit_rate,
                unrealized_pnl,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                close_size,
                current_price,
                f"维护平仓保留≤2U (亏损{maintenance['profit_rate']:.2f}%触发)",
                maintenance['profit_rate'],
                0.0,  # 未实现盈亏待计算
                now
            ))
            
            close_id = cursor.lastrowid
            print(f"  2️⃣  平仓记录 #{close_id}: {close_size:.4f} @ {current_price:.4f} ({close_percent:.1f}%)")
            print(f"  3️⃣  保留持仓: {remain_size:.4f} (≈{target_remaining_margin:.2f}U保证金)")
            print(f"      实际保证金: {remain_size * current_price / 10:.2f} USDT")
            
            # 3. 记录维护日志（用于前端显示）
            # 步骤1：补仓
            cursor.execute('''
            INSERT INTO anchor_maintenance_logs (
                inst_id,
                pos_side,
                original_size,
                original_price,
                original_margin,
                current_price,
                profit_rate,
                step,
                action,
                trade_size,
                trade_price,
                remaining_size,
                remaining_margin,
                trigger_reason,
                decision_log,
                status,
                executed_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                open_size,
                open_price,
                open_size * open_price / 10,  # 10x杠杆保证金
                current_price,
                maintenance['profit_rate'],
                'step1',
                'add_position',
                add_size,
                current_price,
                total_after_add,
                total_after_add * current_price / 10,
                f"亏损{maintenance['profit_rate']:.2f}%触发维护",
                f"补仓10倍：{open_size:.4f} × 10 = {add_size:.4f}",
                'executed',
                now,
                now
            ))
            
            log_id_1 = cursor.lastrowid
            
            # 步骤2：平仓（需要先计算平均价格）
            # 计算平均价格：(原持仓成本 + 补仓成本) / (原持仓 + 补仓)
            original_cost = open_size * open_price
            add_cost = add_size * current_price
            total_cost = original_cost + add_cost
            total_size_after_add = open_size + add_size
            average_price = total_cost / total_size_after_add
            
            cursor.execute('''
            INSERT INTO anchor_maintenance_logs (
                inst_id,
                pos_side,
                original_size,
                original_price,
                original_margin,
                current_price,
                profit_rate,
                step,
                action,
                trade_size,
                trade_price,
                remaining_size,
                remaining_margin,
                trigger_reason,
                decision_log,
                status,
                executed_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                open_size,
                open_price,
                open_size * open_price / 10,
                current_price,
                maintenance['profit_rate'],
                'step2',
                'close_position',
                close_size,
                current_price,
                remain_size,
                remain_size * current_price / 10,
                f"亏损{maintenance['profit_rate']:.2f}%触发维护",
                f"平仓{close_percent:.1f}%：{total_after_add:.4f} 张中平掉 {close_size:.4f} 张，保留≤2U ≈ {remain_size:.4f} 张（实际 {remain_size * current_price / 10:.2f}U）；维护后平均价格：{average_price:.4f}（原价{open_price:.4f}）",
                'executed',
                now,
                now
            ))
            
            log_id_2 = cursor.lastrowid
            print(f"  4️⃣  维护日志 #{log_id_1}, #{log_id_2}: 已记录")
            
            # 5. **关键步骤：更新 position_opens 表，使用已计算的平均价格**
            cursor.execute('''
            UPDATE position_opens
            SET open_size = ?,
                open_price = ?,
                updated_time = ?
            WHERE inst_id = ? AND pos_side = ? AND is_anchor = 1 AND (trade_mode = ? OR trade_mode IS NULL)
            ''', (remain_size, average_price, now, inst_id, pos_side, self.trade_mode))
            
            rows_updated = cursor.rowcount
            print(f"  5️⃣  更新持仓记录: {inst_id} {pos_side}")
            print(f"     原价格: {open_price:.4f} → 平均价格: {average_price:.4f}")
            print(f"     原持仓: {open_size:.4f} → 剩余持仓: {remain_size:.4f}")
            print(f"     更新了 {rows_updated} 行")
            
            # 5. **关闭相关预警（维护完成后预警应该关闭）**
            cursor.execute('''
            UPDATE anchor_warning_monitor
            SET status = 'closed',
                updated_at = ?
            WHERE inst_id = ? AND pos_side = ? AND status = 'active'
            ''', (now, inst_id, pos_side))
            
            warnings_closed = cursor.rowcount
            if warnings_closed > 0:
                print(f"  6️⃣  关闭预警: {inst_id} {pos_side} (关闭了{warnings_closed}个预警)")
            
            # 6. 更新决策状态为已执行
            cursor.execute('''
            UPDATE trading_decisions
            SET executed = 1
            WHERE id = ?
            ''', (decision_id,))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 维护执行完成: {inst_id}")
            return True
            
        except Exception as e:
            print(f"❌ 执行维护失败: {e}")
            return False
    
    def log_maintenance_alert(self, maintenance: Dict):
        """输出维护告警"""
        print("\n" + "=" * 60)
        print("🚨 锚点单维护告警")
        print("=" * 60)
        print(f"📊 币种: {maintenance['inst_id']}")
        print(f"📍 方向: {'做多' if maintenance['pos_side'] == 'long' else '做空'}")
        print(f"💰 开仓价格: {maintenance['open_price']:.4f}")
        print(f"📈 当前价格: {maintenance['current_price']:.4f}")
        print(f"📉 亏损率: {maintenance['profit_rate']:.2f}%")
        print(f"🎯 触发条件: 亏损 ≥ 10%")
        print("\n🔧 维护方案:")
        print(f"  1️⃣  补仓金额: 原金额 × 10倍")
        print(f"  2️⃣  补仓后立即平掉 95%")
        print(f"  3️⃣  保留 5% 继续持有")
        print("=" * 60)
    
    def log_warning_alert(self, warning: Dict):
        """输出预警监控告警"""
        print("\n" + "=" * 60)
        print("⚠️  锚点单预警监控")
        print("=" * 60)
        print(f"📊 币种: {warning['inst_id']}")
        print(f"📍 方向: {'做多' if warning['pos_side'] == 'long' else '做空'}")
        print(f"💰 开仓价格: {warning['open_price']:.4f}")
        print(f"📈 当前价格: {warning['current_price']:.4f}")
        print(f"📉 亏损率: {warning['profit_rate']:.2f}%")
        print(f"🎯 监控阈值: 亏损 ≥ 8%（提前监控）")
        print(f"🚨 维护触发: 亏损 ≥ 10%")
        print(f"📏 距离触发: {abs(-10.0 - warning['profit_rate']):.2f}%")
        print("=" * 60)
    
    def scan_and_check(self):
        """扫描并检查所有锚点单"""
        try:
            # 记录扫描开始时间
            scan_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 获取所有锚点单
            positions = self.get_anchor_positions()
            
            if not positions:
                return
            
            print(f"\n🔍 扫描锚点单: {len(positions)}个 (检测时间: {scan_time})")
            
            maintenance_count = 0
            warning_count = 0
            
            for position in positions:
                # 检查是否需要维护或监控
                check_result = self.check_single_position(position)
                
                if check_result:
                    alert_level = check_result.get('alert_level', 'critical')
                    
                    if alert_level == 'critical':
                        # 触发维护
                        self.log_maintenance_alert(check_result)
                        decision_id = self.record_maintenance_trigger(check_result)
                        if decision_id:
                            maintenance_count += 1
                            # 立即执行维护
                            if self.execute_maintenance(check_result, decision_id):
                                print(f"✅ {check_result['inst_id']} 维护执行成功")
                            else:
                                print(f"❌ {check_result['inst_id']} 维护执行失败")
                    elif alert_level == 'warning':
                        # 提前监控预警
                        self.log_warning_alert(check_result)
                        warning_count += 1
            
            if maintenance_count > 0:
                print(f"\n🚨 本次扫描触发维护: {maintenance_count}个")
            if warning_count > 0:
                print(f"\n⚠️  本次扫描预警监控: {warning_count}个")
            if maintenance_count == 0 and warning_count == 0:
                print(f"✅ 扫描完成，无需维护")
                
        except Exception as e:
            print(f"❌ 扫描检查失败: {e}")
    
    def run(self):
        """运行守护进程"""
        print(f"\n🔄 开始监控锚点单...")
        
        while True:
            try:
                # 扫描并检查
                self.scan_and_check()
                
                # 等待下一次检查
                print(f"\n⏳ 等待{self.check_interval}秒后继续...\n")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n\n⛔ 接收到停止信号，退出...")
                sys.exit(0)
            except Exception as e:
                print(f"\n❌ 运行时错误: {e}")
                print(f"⏳ {self.check_interval}秒后重试...\n")
                time.sleep(self.check_interval)


if __name__ == '__main__':
    daemon = AnchorMaintenanceDaemon()
    daemon.run()
