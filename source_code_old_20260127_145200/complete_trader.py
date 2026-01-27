#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的自动交易执行器 - 整合所有模块
包含：止盈、锚点维护、开仓、补仓、挂单
"""

import sqlite3
import json
import time
import sys
from datetime import datetime
import pytz

# 导入所有模块
from trading_rules import TakeProfitRules, AnchorMaintenance
from position_manager import PositionOpener, PositionAdder, AnchorOrderManager
from okex_trader import OKExTrader, SafetyGate

# 配置
DB_PATH = '/home/user/webapp/trading_decision.db'
ANCHOR_DB_PATH = '/home/user/webapp/anchor_system.db'
CONFIG_PATH = '/home/user/webapp/trading_config.json'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 监控间隔（秒）
MONITOR_INTERVAL = 60


class CompleteAutoTrader:
    """完整的自动交易执行器"""
    
    def __init__(self, dry_run=True):
        """
        初始化
        
        Args:
            dry_run: 是否模拟运行
        """
        self.dry_run = dry_run
        
        # 初始化所有模块
        self.safety_gate = SafetyGate(DB_PATH)
        self.okex_trader = OKExTrader(dry_run=dry_run)
        self.take_profit_rules = TakeProfitRules(DB_PATH)
        self.anchor_maintenance = AnchorMaintenance(DB_PATH)
        self.position_opener = PositionOpener(DB_PATH)
        self.position_adder = PositionAdder(DB_PATH)
        self.anchor_order_mgr = AnchorOrderManager(DB_PATH)
        
        print("=" * 80)
        print(f"🤖 完整自动交易系统已启动 ({'模拟模式' if dry_run else '实盘模式'})")
        print("=" * 80)
        print("\n📦 已加载模块:")
        print("  ✅ 止盈规则 (TakeProfitRules)")
        print("  ✅ 锚点维护 (AnchorMaintenance)")
        print("  ✅ 开仓管理 (PositionOpener)")
        print("  ✅ 补仓管理 (PositionAdder)")
        print("  ✅ 挂单管理 (AnchorOrderManager)")
        print("  ✅ 安全闸门 (SafetyGate)")
        print("  ✅ OKEx交易 (OKExTrader)")
    
    def get_market_config(self):
        """获取市场配置"""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM market_config ORDER BY updated_at DESC LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'market_mode': result[1],
                    'market_trend': result[2],
                    'total_capital': result[3],
                    'position_limit_mode': result[4],
                    'position_limit_percent': result[5],
                    'anchor_capital_limit': result[6],
                    'anchor_capital_percent': result[7],
                    'allow_long': bool(result[8]),
                    'min_granularity': result[9],
                    'long_granularity': result[10],
                    'enabled': bool(result[11])
                }
            return None
        except Exception as e:
            print(f"❌ 获取配置失败: {e}")
            return None
    
    def get_current_positions(self):
        """从锚点系统获取当前持仓"""
        try:
            conn = sqlite3.connect(ANCHOR_DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            
            # 获取最新的持仓快照
            cursor.execute('''
            SELECT inst_id, pos_side, pos_size, avg_price, mark_price, 
                   upl, margin, leverage, profit_rate, timestamp
            FROM anchor_monitors
            WHERE timestamp = (SELECT MAX(timestamp) FROM anchor_monitors)
            ''')
            
            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'inst_id': row[0],
                    'pos_side': row[1],
                    'pos_size': float(row[2]),
                    'avg_price': float(row[3]),
                    'mark_price': float(row[4]),
                    'upl': float(row[5]),
                    'margin': float(row[6]),
                    'leverage': float(row[7]),
                    'profit_rate': float(row[8]),
                    'timestamp': row[9]
                })
            
            conn.close()
            return positions
        except Exception as e:
            print(f"❌ 获取持仓失败: {e}")
            return []
    
    def process_position(self, position, config):
        """
        处理单个持仓的所有逻辑
        
        优先级：
        1. 止损检查（最高优先级）
        2. 锚点单维护
        3. 补仓检查
        4. 止盈检查
        5. 挂单检查
        
        Args:
            position: 持仓信息
            config: 市场配置
        
        Returns:
            dict: 处理结果
        """
        inst_id = position['inst_id']
        pos_side = position['pos_side']
        profit_rate = position['profit_rate']
        current_size = position['pos_size']
        current_price = position['mark_price']
        
        print(f"\n{'─'*80}")
        print(f"🪙 {inst_id} ({pos_side})")
        print(f"   仓位: {current_size} | 收益率: {profit_rate:.2f}%")
        print(f"   开仓价: {position['avg_price']} | 当前价: {current_price}")
        
        # 1. 止损检查（最高优先级）
        if self.check_and_execute_stop_loss(position, config):
            return {'action': 'stop_loss', 'executed': True}
        
        # 2. 锚点单维护（第二优先级）
        if self.check_and_execute_anchor_maintenance(position, config):
            return {'action': 'anchor_maintenance', 'executed': True}
        
        # 3. 补仓检查
        if self.check_and_execute_position_add(position, config):
            return {'action': 'position_add', 'executed': True}
        
        # 4. 止盈检查
        if self.check_and_execute_take_profit(position, config):
            return {'action': 'take_profit', 'executed': True}
        
        # 5. 挂单检查
        if self.check_and_execute_pending_orders(position, config):
            return {'action': 'pending_order', 'executed': True}
        
        print(f"⏳ {inst_id} 无需操作")
        return {'action': 'none', 'executed': False}
    
    def check_and_execute_stop_loss(self, position, config):
        """检查并执行止损"""
        add_decision = self.position_adder.check_add_condition(
            inst_id=position['inst_id'],
            pos_side=position['pos_side'],
            current_size=position['pos_size'],
            profit_rate=position['profit_rate'],
            current_price=position['mark_price'],
            total_capital=config['total_capital']
        )
        
        if add_decision.get('should_stop_loss'):
            print(f"🛑 {position['inst_id']} 触发止损!")
            print(f"   当前收益率: {position['profit_rate']:.2f}%")
            print(f"   平仓金额: {add_decision['close_size']}")
            print(f"   保留金额: {add_decision['keep_size']}")
            print(f"   原因: {add_decision['reason']}")
            
            # 检查安全闸门
            if not self.safety_gate.check_can_trade(position['inst_id']):
                print(f"🚫 安全闸门关闭，无法执行止损")
                return False
            
            # 确定交易方向
            side = 'buy' if position['pos_side'] == 'short' else 'sell'
            
            # 执行止损
            success = self.okex_trader.execute_trade(
                inst_id=position['inst_id'],
                trade_mode='isolated',
                pos_side=position['pos_side'],
                side=side,
                order_type='market',
                size=add_decision['close_size'],
                reason=add_decision['reason']
            )
            
            if success:
                print(f"✅ 止损执行成功: {position['inst_id']}")
                # 保存决策记录
                self.save_decision_record(
                    position, 'stop_loss', add_decision['close_size'],
                    (add_decision['close_size'] / position['pos_size']) * 100,
                    add_decision['reason'], 1
                )
            
            return success
        
        return False
    
    def check_and_execute_anchor_maintenance(self, position, config):
        """检查并执行锚点单维护"""
        # 只有在多头主导且是空单时才需要维护
        if config['market_trend'] != 'bullish' or position['pos_side'] != 'short':
            return False
        
        if position['profit_rate'] <= -10:
            print(f"⚠️  {position['inst_id']} 锚点单需要维护!")
            
            # 检查维护记录
            maintenance_record = self.anchor_maintenance.get_latest_maintenance(
                position['inst_id'], 
                position['pos_side']
            )
            
            # 如果已维护且收益回正，卖出75%
            if maintenance_record and maintenance_record['status'] == 'maintained':
                if position['profit_rate'] > 0:
                    print(f"✅ {position['inst_id']} 锚点单收益已回正，执行卖出75%")
                    return self.execute_anchor_recovery(position, maintenance_record)
                else:
                    print(f"⏳ {position['inst_id']} 锚点单已维护，等待收益回正...")
                    return False
            
            # 执行锚点单维护（加仓2倍）
            return self.execute_anchor_maintenance(position, config)
        
        return False
    
    def execute_anchor_maintenance(self, position, config):
        """执行锚点单维护"""
        maintenance_size = position['pos_size'] * 2
        
        if not self.safety_gate.check_can_trade(position['inst_id']):
            print(f"🚫 安全闸门关闭，无法执行维护")
            return False
        
        success = self.okex_trader.execute_trade(
            inst_id=position['inst_id'],
            trade_mode='isolated',
            pos_side=position['pos_side'],
            side='buy',
            order_type='market',
            size=maintenance_size,
            reason=f"锚点单维护: 收益率{position['profit_rate']:.2f}%"
        )
        
        if success:
            self.anchor_maintenance.save_maintenance(
                inst_id=position['inst_id'],
                pos_side=position['pos_side'],
                original_size=position['pos_size'],
                original_price=position['avg_price'],
                maintenance_price=position['mark_price'],
                maintenance_size=maintenance_size,
                profit_rate=position['profit_rate'],
                action='add',
                status='maintained'
            )
            print(f"✅ 锚点单维护成功: {position['inst_id']}")
        
        return success
    
    def execute_anchor_recovery(self, position, maintenance_record):
        """执行锚点单收益回正卖出"""
        close_size = position['pos_size'] * 0.75
        
        if not self.safety_gate.check_can_trade(position['inst_id']):
            return False
        
        success = self.okex_trader.execute_trade(
            inst_id=position['inst_id'],
            trade_mode='isolated',
            pos_side=position['pos_side'],
            side='sell',
            order_type='market',
            size=close_size,
            reason=f"锚点单收益回正卖出75%"
        )
        
        if success:
            self.anchor_maintenance.update_maintenance_status(
                maintenance_record['id'],
                'recovered'
            )
            print(f"✅ 锚点单收益回正卖出成功")
        
        return success
    
    def check_and_execute_position_add(self, position, config):
        """检查并执行补仓"""
        add_decision = self.position_adder.check_add_condition(
            inst_id=position['inst_id'],
            pos_side=position['pos_side'],
            current_size=position['pos_size'],
            profit_rate=position['profit_rate'],
            current_price=position['mark_price'],
            total_capital=config['total_capital']
        )
        
        if add_decision.get('should_add'):
            print(f"➕ {position['inst_id']} 触发补仓!")
            print(f"   Level: {add_decision['level']}")
            print(f"   触发收益率: {add_decision['profit_rate_trigger']}%")
            print(f"   补仓金额: {add_decision['add_size']}")
            print(f"   补仓后总额: {add_decision['total_size_after']}")
            
            if not self.safety_gate.check_can_trade(position['inst_id']):
                print(f"🚫 安全闸门关闭，无法执行补仓")
                return False
            
            # 确定交易方向（补空单=买入，补多单=买入）
            side = 'buy'
            
            success = self.okex_trader.execute_trade(
                inst_id=position['inst_id'],
                trade_mode='isolated',
                pos_side=position['pos_side'],
                side=side,
                order_type='market',
                size=add_decision['add_size'],
                reason=add_decision['reason']
            )
            
            if success:
                self.position_adder.save_position_add(
                    inst_id=position['inst_id'],
                    pos_side=position['pos_side'],
                    add_price=add_decision['add_price'],
                    add_size=add_decision['add_size'],
                    add_percent=add_decision['add_percent'],
                    profit_rate_trigger=add_decision['profit_rate_trigger'],
                    level=add_decision['level'],
                    total_size_after=add_decision['total_size_after']
                )
                print(f"✅ 补仓执行成功")
            
            return success
        
        return False
    
    def check_and_execute_take_profit(self, position, config):
        """检查并执行止盈"""
        decision = self.take_profit_rules.get_take_profit_decision(
            pos_side=position['pos_side'],
            profit_rate=position['profit_rate'],
            current_size=position['pos_size'],
            allow_long=config['allow_long']
        )
        
        if not decision['should_close']:
            return False
        
        print(f"💰 {position['inst_id']} 触发止盈!")
        print(f"   收益率: {position['profit_rate']:.2f}%")
        print(f"   止盈比例: {decision['close_percent']}%")
        print(f"   止盈数量: {decision['close_size']}")
        
        if not self.safety_gate.check_can_trade(position['inst_id']):
            print(f"🚫 安全闸门关闭，无法执行止盈")
            return False
        
        side = 'sell' if position['pos_side'] == 'long' else 'buy'
        
        success = self.okex_trader.execute_trade(
            inst_id=position['inst_id'],
            trade_mode='isolated',
            pos_side=position['pos_side'],
            side=side,
            order_type='market',
            size=decision['close_size'],
            reason=decision['reason']
        )
        
        if success:
            self.take_profit_rules.save_decision(
                inst_id=position['inst_id'],
                pos_side=position['pos_side'],
                action='close',
                decision_type='take_profit',
                current_size=position['pos_size'],
                target_size=position['pos_size'] - decision['close_size'],
                close_size=decision['close_size'],
                close_percent=decision['close_percent'],
                profit_rate=position['profit_rate'],
                current_price=position['mark_price'],
                reason=decision['reason'],
                executed=1
            )
            print(f"✅ 止盈执行成功")
        
        return success
    
    def check_and_execute_pending_orders(self, position, config):
        """检查并执行挂单触发"""
        triggered_orders = self.anchor_order_mgr.check_pending_order_triggered(
            position['inst_id'],
            position['mark_price']
        )
        
        if not triggered_orders:
            return False
        
        for order in triggered_orders:
            print(f"📋 {position['inst_id']} 挂单触发!")
            print(f"   类型: {order['order_type']}")
            print(f"   目标价: {order['target_price']}")
            print(f"   当前价: {order['current_price']}")
            print(f"   挂单额: {order['order_size']}")
            
            if not self.safety_gate.check_can_trade(position['inst_id']):
                print(f"🚫 安全闸门关闭，无法执行挂单")
                continue
            
            success = self.okex_trader.execute_trade(
                inst_id=position['inst_id'],
                trade_mode='isolated',
                pos_side='short',  # 挂单都是空单
                side='sell',
                order_type='market',
                size=order['order_size'],
                reason=f"挂单触发: {order['order_type']}"
            )
            
            if success:
                self.anchor_order_mgr.update_order_status(order['order_id'], 'triggered')
                print(f"✅ 挂单执行成功")
                return True
        
        return False
    
    def save_decision_record(self, position, decision_type, close_size, close_percent, reason, executed):
        """保存决策记录"""
        self.take_profit_rules.save_decision(
            inst_id=position['inst_id'],
            pos_side=position['pos_side'],
            action='close',
            decision_type=decision_type,
            current_size=position['pos_size'],
            target_size=position['pos_size'] - close_size,
            close_size=close_size,
            close_percent=close_percent,
            profit_rate=position['profit_rate'],
            current_price=position['mark_price'],
            reason=reason,
            executed=executed
        )
    
    def monitor_once(self):
        """执行一次完整监控"""
        print(f"\n{'='*80}")
        print(f"⏰ {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} - 开始完整监控")
        print(f"{'='*80}")
        
        # 获取配置
        config = self.get_market_config()
        if not config:
            print("❌ 无法获取市场配置")
            return
        
        # 检查系统是否启用
        if not config['enabled']:
            print("⏸️  自动交易系统未启用")
            return
        
        # 检查总开关
        if not self.safety_gate.is_master_switch_on():
            print("🚫 安全闸门总开关关闭")
            return
        
        print(f"📊 市场模式: {config['market_mode']}")
        print(f"📈 市场趋势: {config['market_trend']}")
        print(f"💼 总本金: {config['total_capital']} USDT")
        print(f"💰 可开仓额: {config['total_capital'] * config['position_limit_percent'] / 100:.2f} USDT")
        print(f"🎯 允许开多: {'是' if config['allow_long'] else '否'}")
        
        # 获取持仓
        positions = self.get_current_positions()
        if not positions:
            print("📭 当前无持仓")
            return
        
        print(f"\n📦 当前持仓数量: {len(positions)}")
        
        # 处理每个持仓
        results = []
        for position in positions:
            result = self.process_position(position, config)
            results.append(result)
        
        # 统计
        executed_count = sum(1 for r in results if r['executed'])
        print(f"\n{'='*80}")
        print(f"✅ 本轮监控完成")
        print(f"   处理持仓: {len(positions)}")
        print(f"   执行操作: {executed_count}")
        print(f"{'='*80}\n")
    
    def start(self):
        """启动持续监控"""
        print(f"\n🚀 完整自动交易监控已启动")
        print(f"⏱️  监控间隔: {MONITOR_INTERVAL} 秒")
        print(f"🔒 模式: {'模拟运行' if self.dry_run else '实盘运行'}")
        print(f"\n按 Ctrl+C 停止监控\n")
        
        try:
            while True:
                try:
                    self.monitor_once()
                except Exception as e:
                    print(f"❌ 监控异常: {e}")
                    import traceback
                    traceback.print_exc()
                
                time.sleep(MONITOR_INTERVAL)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  监控已停止")
            sys.exit(0)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='完整自动交易执行器')
    parser.add_argument('--live', action='store_true', help='实盘模式（默认为模拟模式）')
    parser.add_argument('--once', action='store_true', help='只执行一次监控')
    args = parser.parse_args()
    
    trader = CompleteAutoTrader(dry_run=not args.live)
    
    if args.once:
        trader.monitor_once()
    else:
        trader.start()


if __name__ == '__main__':
    main()
