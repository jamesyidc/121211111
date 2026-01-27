#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动交易决策主循环 - 整合锚点系统和交易决策系统
"""

import time
import json
import sqlite3
from datetime import datetime
import pytz

# 导入核心模块
from trading_rules import TakeProfitRules, AnchorMaintenance, save_trading_decision, save_anchor_maintenance
from okex_trader import OKExTrader, SafetyGate, execute_trading_decision

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
ANCHOR_DB = '/home/user/webapp/anchor_system.db'
TRADING_DB = '/home/user/webapp/trading_decision.db'
CONFIG_FILE = '/home/user/webapp/trading_config.json'

# 监控间隔（秒）
MONITOR_INTERVAL = 60


def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return {
            'market_mode': 'manual',
            'market_trend': 'neutral',
            'total_capital': 1000,
            'position_limit_percent': 60,
            'anchor_capital_limit': 200,
            'allow_long': False,
            'enabled': False
        }


def get_anchor_positions():
    """从锚点系统数据库获取当前持仓"""
    try:
        conn = sqlite3.connect(ANCHOR_DB, timeout=10.0)
        cursor = conn.cursor()
        
        # 查询最新的监控记录（每个币种/方向的最新一条）
        cursor.execute('''
        SELECT inst_id, pos_side, pos_size, avg_price, mark_price, 
               upl, margin, leverage, profit_rate, timestamp
        FROM anchor_monitors
        WHERE id IN (
            SELECT MAX(id) 
            FROM anchor_monitors 
            GROUP BY inst_id, pos_side
        )
        AND pos_size > 0
        ORDER BY inst_id, pos_side
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        positions = []
        for row in rows:
            positions.append({
                'instId': row[0],
                'posSide': row[1],
                'pos_size': row[2],
                'avgPx': row[3],
                'markPx': row[4],
                'upl': row[5],
                'margin': row[6],
                'lever': row[7],
                'profit_rate': row[8],
                'timestamp': row[9]
            })
        
        return positions
    except Exception as e:
        print(f"❌ 获取锚点持仓失败: {e}")
        return []


def process_position(position, config):
    """
    处理单个持仓，生成交易决策
    
    Args:
        position: 持仓信息
        config: 配置
    
    Returns:
        list: 交易决策列表
    """
    decisions = []
    
    inst_id = position['instId']
    pos_side = position['posSide']
    profit_rate = position['profit_rate']
    current_size = position['pos_size']
    current_price = position['markPx']
    
    print(f"\n{'='*80}")
    print(f"📊 处理持仓: {inst_id} - {pos_side}")
    print(f"   持仓量: {current_size:.4f} | 收益率: {profit_rate:.2f}% | 价格: {current_price}")
    print(f"{'='*80}")
    
    # 1. 检查锚点单维护（仅在多头行情）
    if config['market_trend'] == 'bullish' and pos_side == 'short':
        maintenance = AnchorMaintenance.check_maintenance_needed(position, config['market_trend'])
        
        if maintenance['need_maintenance']:
            print(f"🔧 锚点单维护触发: {maintenance['reason']}")
            
            # 保存维护记录
            maintenance_record = {
                'inst_id': inst_id,
                'pos_side': pos_side,
                'original_size': current_size,
                'original_price': position['avgPx'],
                'maintenance_price': current_price,
                'maintenance_size': maintenance.get('add_size', 0),
                'profit_rate': profit_rate,
                'action': maintenance['action'],
                'status': 'pending'
            }
            save_anchor_maintenance(maintenance_record)
            
            # 生成交易决策
            if maintenance['action'] == 'add_position':
                decisions.append({
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'action': 'add',
                    'decision_type': 'anchor_maintenance',
                    'current_size': current_size,
                    'target_size': maintenance['target_size'],
                    'close_size': maintenance['add_size'],
                    'close_percent': 0,
                    'profit_rate': profit_rate,
                    'current_price': current_price,
                    'reason': maintenance['reason']
                })
            elif maintenance['action'] == 'reduce_position':
                decisions.append({
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'action': 'close',
                    'decision_type': 'anchor_maintenance',
                    'current_size': current_size,
                    'target_size': maintenance['keep_size'],
                    'close_size': maintenance['sell_size'],
                    'close_percent': 75,
                    'profit_rate': profit_rate,
                    'current_price': current_price,
                    'reason': maintenance['reason']
                })
    
    # 2. 检查止盈条件
    take_profit = TakeProfitRules.get_take_profit_decision(
        pos_side, profit_rate, current_size, config['allow_long']
    )
    
    if take_profit['should_close']:
        print(f"💰 止盈触发: {take_profit['reason']}")
        
        decisions.append({
            'inst_id': inst_id,
            'pos_side': pos_side,
            'action': 'close',
            'decision_type': 'take_profit',
            'current_size': current_size,
            'target_size': current_size - take_profit['close_size'],
            'close_size': take_profit['close_size'],
            'close_percent': take_profit['close_percent'],
            'profit_rate': profit_rate,
            'current_price': current_price,
            'reason': take_profit['reason']
        })
    
    return decisions


def save_trading_signal(decision):
    """保存交易信号供其他账号使用"""
    try:
        conn = sqlite3.connect(TRADING_DB, timeout=10.0)
        cursor = conn.cursor()
        
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        INSERT INTO trading_signals (
            inst_id, signal_type, action, price, size, profit_rate,
            reason, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            decision['inst_id'],
            decision['decision_type'],
            decision['action'],
            decision['current_price'],
            decision['close_size'],
            decision['profit_rate'],
            decision['reason'],
            timestamp
        ))
        
        conn.commit()
        conn.close()
        print(f"📡 交易信号已保存: {decision['inst_id']}")
        return True
    except Exception as e:
        print(f"❌ 保存交易信号失败: {e}")
        return False


def trading_loop():
    """主循环"""
    print("\n" + "="*80)
    print("🚀 自动交易决策系统启动")
    print("="*80)
    
    loop_count = 0
    
    while True:
        try:
            loop_count += 1
            current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\n\n{'#'*80}")
            print(f"# 第 {loop_count} 轮监控 - {current_time}")
            print(f"{'#'*80}")
            
            # 1. 加载配置
            config = load_config()
            print(f"\n📋 当前配置:")
            print(f"   市场模式: {config['market_mode']}")
            print(f"   市场趋势: {config['market_trend']}")
            print(f"   总本金: {config['total_capital']}U")
            print(f"   允许开多: {config['allow_long']}")
            print(f"   系统开关: {'🟢 开启' if config['enabled'] else '🔴 关闭'}")
            
            # 2. 检查总开关
            if not config['enabled']:
                print("\n⚠️  系统开关已关闭，跳过本轮监控")
                time.sleep(MONITOR_INTERVAL)
                continue
            
            # 3. 获取当前持仓
            print(f"\n📊 获取持仓信息...")
            positions = get_anchor_positions()
            print(f"   持仓数量: {len(positions)}")
            
            if not positions:
                print("   ⚠️  暂无持仓")
                time.sleep(MONITOR_INTERVAL)
                continue
            
            # 4. 处理每个持仓
            all_decisions = []
            for position in positions:
                decisions = process_position(position, config)
                all_decisions.extend(decisions)
            
            # 5. 执行交易决策
            if all_decisions:
                print(f"\n\n{'='*80}")
                print(f"📝 本轮生成 {len(all_decisions)} 个交易决策")
                print(f"{'='*80}")
                
                for decision in all_decisions:
                    # 保存决策到数据库
                    save_trading_decision(decision)
                    
                    # 保存交易信号
                    save_trading_signal(decision)
                    
                    # 执行交易（默认dry_run模式）
                    execute_trading_decision(decision, config, dry_run=True)
            else:
                print(f"\n✅ 本轮无需执行交易")
            
            # 6. 等待下一轮
            print(f"\n⏰ 等待 {MONITOR_INTERVAL} 秒后开始下一轮监控...")
            time.sleep(MONITOR_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n" + "="*80)
            print("⛔ 收到停止信号，退出主循环")
            print("="*80)
            break
        except Exception as e:
            print(f"\n❌ 主循环异常: {e}")
            import traceback
            traceback.print_exc()
            print(f"\n⏰ 等待 {MONITOR_INTERVAL} 秒后重试...")
            time.sleep(MONITOR_INTERVAL)


if __name__ == '__main__':
    trading_loop()
