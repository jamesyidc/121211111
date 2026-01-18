#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点系统 - 自动交易执行器
整合所有决策逻辑，实现自动化交易监控和执行
"""

import sqlite3
import json
import time
import sys
from datetime import datetime
import pytz

# 导入其他模块
from trading_rules import TakeProfitRules, AnchorMaintenance
from okex_trader import OKExTrader, SafetyGate

# 配置
DB_PATH = '/home/user/webapp/trading_decision.db'
ANCHOR_DB_PATH = '/home/user/webapp/anchor_system.db'
CONFIG_PATH = '/home/user/webapp/trading_config.json'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 监控间隔（秒）
MONITOR_INTERVAL = 60


class AutoTrader:
    """自动交易执行器"""
    
    def __init__(self, dry_run=True):
        """
        初始化自动交易执行器
        
        Args:
            dry_run: 是否模拟运行（True不实际下单）
        """
        self.dry_run = dry_run
        self.safety_gate = SafetyGate(DB_PATH)
        self.okex_trader = OKExTrader(dry_run=dry_run)
        self.take_profit_rules = TakeProfitRules(DB_PATH)
        self.anchor_maintenance = AnchorMaintenance(DB_PATH)
        
        print("=" * 80)
        print(f"🤖 自动交易执行器已启动 ({'模拟模式' if dry_run else '实盘模式'})")
        print("=" * 80)
    
    def get_market_config(self):
        """获取市场配置"""
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
    
    def get_current_positions(self):
        """从锚点系统数据库获取当前持仓"""
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
    
    def check_anchor_maintenance(self, position, config):
        """
        检查锚点单维护条件
        
        Args:
            position: 持仓信息
            config: 市场配置
        
        Returns:
            bool: 是否需要维护
        """
        # 只有在多头主导(bullish)市场且是空单时才需要维护锚点单
        if config['market_trend'] != 'bullish':
            return False
        
        if position['pos_side'] != 'short':
            return False
        
        # 收益率低于-10%时触发维护
        if position['profit_rate'] <= -10:
            print(f"⚠️  {position['inst_id']} 锚点单需要维护!")
            print(f"   收益率: {position['profit_rate']:.2f}%")
            
            # 检查是否已经维护过
            maintenance_record = self.anchor_maintenance.get_latest_maintenance(
                position['inst_id'], 
                position['pos_side']
            )
            
            # 如果已维护且收益已回正，则卖出75%
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
        """
        执行锚点单维护
        
        Args:
            position: 持仓信息
            config: 市场配置
        
        Returns:
            bool: 是否执行成功
        """
        # 计算加仓数量（原仓位的2倍）
        maintenance_size = position['pos_size'] * 2
        
        # 检查安全闸门
        if not self.safety_gate.check_can_trade(position['inst_id']):
            print(f"🚫 安全闸门关闭，无法执行锚点单维护")
            return False
        
        # 执行加仓
        success = self.okex_trader.execute_trade(
            inst_id=position['inst_id'],
            trade_mode='isolated',
            pos_side=position['pos_side'],
            side='buy',  # 空单维护是买入
            order_type='market',
            size=maintenance_size,
            reason=f"锚点单维护: 收益率{position['profit_rate']:.2f}%"
        )
        
        if success:
            # 记录维护动作
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
            print(f"✅ 锚点单维护成功: {position['inst_id']} 加仓 {maintenance_size}")
        
        return success
    
    def execute_anchor_recovery(self, position, maintenance_record):
        """
        执行锚点单收益回正后的卖出操作
        
        Args:
            position: 持仓信息
            maintenance_record: 维护记录
        
        Returns:
            bool: 是否执行成功
        """
        # 计算卖出数量（75%）
        close_size = position['pos_size'] * 0.75
        
        # 检查安全闸门
        if not self.safety_gate.check_can_trade(position['inst_id']):
            print(f"🚫 安全闸门关闭，无法执行卖出")
            return False
        
        # 执行卖出
        success = self.okex_trader.execute_trade(
            inst_id=position['inst_id'],
            trade_mode='isolated',
            pos_side=position['pos_side'],
            side='sell',  # 空单卖出
            order_type='market',
            size=close_size,
            reason=f"锚点单收益回正卖出75%: 收益率{position['profit_rate']:.2f}%"
        )
        
        if success:
            # 更新维护记录
            self.anchor_maintenance.update_maintenance_status(
                maintenance_record['id'],
                'recovered'
            )
            print(f"✅ 锚点单收益回正卖出成功: {position['inst_id']} 卖出 {close_size}")
        
        return success
    
    def check_take_profit(self, position, config):
        """
        检查止盈条件
        
        Args:
            position: 持仓信息
            config: 市场配置
        
        Returns:
            bool: 是否需要止盈
        """
        # 获取止盈决策
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
        print(f"   原因: {decision['reason']}")
        
        # 执行止盈
        return self.execute_take_profit(position, decision)
    
    def execute_take_profit(self, position, decision):
        """
        执行止盈操作
        
        Args:
            position: 持仓信息
            decision: 止盈决策
        
        Returns:
            bool: 是否执行成功
        """
        # 检查安全闸门
        if not self.safety_gate.check_can_trade(position['inst_id']):
            print(f"🚫 安全闸门关闭，无法执行止盈")
            return False
        
        # 确定交易方向
        if position['pos_side'] == 'long':
            side = 'sell'  # 多单止盈是卖出
        else:
            side = 'buy'  # 空单止盈是买入
        
        # 执行止盈
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
            # 保存止盈决策记录
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
            print(f"✅ 止盈执行成功: {position['inst_id']}")
        
        return success
    
    def monitor_once(self):
        """执行一次监控"""
        print(f"\n{'='*80}")
        print(f"⏰ {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} - 开始监控")
        print(f"{'='*80}")
        
        # 获取市场配置
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
            print("🚫 安全闸门总开关关闭，停止监控")
            return
        
        print(f"📊 市场模式: {config['market_trend']}")
        print(f"💼 总本金: {config['total_capital']} USDT")
        print(f"📈 允许开多: {'是' if config['allow_long'] else '否'}")
        
        # 获取当前持仓
        positions = self.get_current_positions()
        if not positions:
            print("📭 当前无持仓")
            return
        
        print(f"\n📦 当前持仓数量: {len(positions)}")
        
        # 遍历所有持仓
        for position in positions:
            print(f"\n{'─'*80}")
            print(f"🪙 {position['inst_id']} ({position['pos_side']})")
            print(f"   仓位: {position['pos_size']} | 收益率: {position['profit_rate']:.2f}%")
            print(f"   开仓价: {position['avg_price']} | 当前价: {position['mark_price']}")
            
            # 1. 检查锚点单维护（优先级最高）
            if self.check_anchor_maintenance(position, config):
                print(f"✅ {position['inst_id']} 锚点单维护处理完成")
                continue
            
            # 2. 检查止盈条件
            if self.check_take_profit(position, config):
                print(f"✅ {position['inst_id']} 止盈处理完成")
                continue
            
            print(f"⏳ {position['inst_id']} 无需操作")
        
        print(f"\n{'='*80}")
        print(f"✅ 本轮监控完成")
        print(f"{'='*80}\n")
    
    def start(self):
        """启动自动交易监控"""
        print(f"\n🚀 自动交易监控已启动")
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
                
                # 等待下一轮
                time.sleep(MONITOR_INTERVAL)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  监控已停止")
            sys.exit(0)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='锚点系统 - 自动交易执行器')
    parser.add_argument('--live', action='store_true', help='实盘模式（默认为模拟模式）')
    parser.add_argument('--once', action='store_true', help='只执行一次监控')
    args = parser.parse_args()
    
    # 创建自动交易执行器
    trader = AutoTrader(dry_run=not args.live)
    
    if args.once:
        # 只执行一次
        trader.monitor_once()
    else:
        # 持续监控
        trader.start()


if __name__ == '__main__':
    main()
