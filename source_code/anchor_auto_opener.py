#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单自动开仓系统
根据逃顶信号自动创建和维护锚点单
"""

import sqlite3
import time
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Tuple
from anchor_trigger import AnchorTrigger
from anchor_manager import AnchorPositionManager
from position_manager import PositionManager

# 配置
DB_PATH = '/home/user/webapp/trading_decision.db'
CRYPTO_DB_PATH = '/home/user/webapp/crypto_data.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 规则配置（根据用户确认后修改）
RULES = {
    # 维护锚点单规则：
    # 1. 满足逃顶信号 + 没有锚点单 → 开新锚点单
    # 2. 满足逃顶信号 + 已有锚点单 + 满足补仓条件(-10%) → 执行补仓
    # 3. 满足逃顶信号 + 已有锚点单 + 不满足补仓条件 → 只监控
    'check_add_position': True,         # True: 检查补仓条件, False: 只监控不补仓
    'add_position_trigger': -10.0,      # 补仓触发：亏损达到-10%
    'min_amount_handling': 'dynamic',   # 'dynamic': 动态调整, 'skip': 跳过
    'prevent_duplicate_minutes': 5,     # 防止重复触发的时间间隔（分钟）
}


class AnchorAutoOpener:
    """锚点单自动开仓系统"""
    
    def __init__(self):
        """初始化"""
        self.trigger = AnchorTrigger()
        self.anchor_manager = AnchorPositionManager(DB_PATH)
        self.position_manager = PositionManager()
        self.db_path = DB_PATH
        self.crypto_db_path = CRYPTO_DB_PATH
        
        # 确保触发记录表存在
        self._create_trigger_table()
    
    def _create_trigger_table(self):
        """创建触发记录表"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS anchor_triggers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inst_id TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            has_existing_anchor INTEGER,
            pressure1 REAL NOT NULL,
            pressure2 REAL NOT NULL,
            current_price REAL NOT NULL,
            open_amount REAL,
            action_taken TEXT NOT NULL,
            skip_reason TEXT,
            trigger_reason TEXT,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def check_existing_anchor(self, inst_id: str) -> Tuple[bool, Dict]:
        """
        检查是否存在原始锚点单
        
        Returns:
            (是否存在, 锚点单信息)
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, open_price, open_size, granularity, timestamp, created_at
        FROM position_opens
        WHERE inst_id = ? 
          AND pos_side = 'short'
          AND is_anchor = 1
        ORDER BY created_at DESC
        LIMIT 1
        ''', (inst_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return True, {
                'id': row[0],
                'open_price': row[1],
                'open_size': row[2],
                'granularity': row[3],
                'timestamp': row[4],
                'created_at': row[5]
            }
        return False, {}
    
    def check_duplicate_trigger(self, inst_id: str, minutes: int = 5) -> bool:
        """
        检查是否在指定时间内已触发过
        
        Returns:
            True: 重复触发, False: 可以触发
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now(BEIJING_TZ) - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        SELECT COUNT(*) FROM anchor_triggers
        WHERE inst_id = ?
          AND timestamp > ?
          AND action_taken != 'skipped'
        ''', (inst_id, cutoff_time))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def calculate_open_amount(self, inst_id: str, current_price: float) -> Tuple[float, str]:
        """
        计算开仓金额
        
        Returns:
            (开仓金额, 说明)
        """
        # 基础金额：1 USDT
        base_amount = 1.0
        
        # TODO: 从OKX API获取最小合约大小
        # 这里先用简单逻辑：如果币价很高，可能需要更大金额
        
        if current_price > 50000:  # BTC类
            min_amount = 5.0
        elif current_price > 5000:  # ETH类
            min_amount = 2.0
        else:
            min_amount = 1.0
        
        if RULES['min_amount_handling'] == 'dynamic':
            final_amount = max(base_amount, min_amount)
            note = f"动态调整: {final_amount} USDT (最小要求: {min_amount} USDT)"
        else:
            final_amount = base_amount
            note = f"固定金额: {final_amount} USDT"
        
        return final_amount, note
    
    def record_trigger(self, inst_id: str, trigger_type: str, signal: Dict, 
                      action_taken: str, skip_reason: str = None, 
                      open_amount: float = None) -> int:
        """记录触发日志"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        has_existing, _ = self.check_existing_anchor(inst_id)
        
        cursor.execute('''
        INSERT INTO anchor_triggers (
            inst_id, trigger_type, has_existing_anchor,
            pressure1, pressure2, current_price, open_amount,
            action_taken, skip_reason, trigger_reason, status, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inst_id,
            trigger_type,
            1 if has_existing else 0,
            signal.get('pressure1'),
            signal.get('pressure2'),
            signal.get('current_price'),
            open_amount,
            action_taken,
            skip_reason,
            f"逃顶信号: 压力1={signal.get('pressure1'):.4f}, 压力2={signal.get('pressure2'):.4f}",
            'completed',
            timestamp
        ))
        
        trigger_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trigger_id
    
    def process_new_anchor(self, inst_id: str, signal: Dict) -> Dict:
        """
        处理新建锚点单
        
        Returns:
            处理结果字典
        """
        result = {
            'inst_id': inst_id,
            'trigger_type': 'new',
            'success': False,
            'action': 'skipped',
            'reason': '',
            'open_amount': 0,
            'decision_log': []  # 新增：决策日志
        }
        
        result['decision_log'].append(f"🎯 检测到逃顶信号")
        result['decision_log'].append(f"📍 压力线1: {signal['pressure1']:.4f}")
        result['decision_log'].append(f"📍 压力线2: {signal['pressure2']:.4f}")
        result['decision_log'].append(f"💰 当前价: {signal['current_price']:.4f}")
        result['decision_log'].append(f"📊 距离压力线1: {signal['distance_to_resistance_1']:.2f}%")
        
        # 检查1：重复触发防护
        if self.check_duplicate_trigger(inst_id, RULES['prevent_duplicate_minutes']):
            result['reason'] = f"⏳ {RULES['prevent_duplicate_minutes']}分钟内已触发过，跳过"
            result['decision_log'].append(f"⏳ 重复触发防护: {RULES['prevent_duplicate_minutes']}分钟内已触发")
            self.record_trigger(inst_id, 'new', signal, 'skipped', result['reason'])
            return result
        
        result['decision_log'].append(f"✅ 重复触发检查通过")
        
        # 检查2：计算开仓金额
        open_amount, amount_note = self.calculate_open_amount(
            inst_id, signal['current_price']
        )
        result['open_amount'] = open_amount
        result['decision_log'].append(f"💰 开仓金额: {open_amount} USDT ({amount_note})")
        
        # 检查3：单币种限制
        passed, reason = self.trigger.check_single_coin_limit(inst_id, open_amount)
        if not passed:
            result['reason'] = f"❌ 单币种限制: {reason}"
            result['decision_log'].append(f"❌ 单币种限制检查失败: {reason}")
            self.record_trigger(inst_id, 'new', signal, 'failed', result['reason'], open_amount)
            return result
        
        result['decision_log'].append(f"✅ 单币种限制检查通过: {reason}")
        
        # 检查4：获取配置
        config = self.trigger.get_config()
        if not config['allow_anchor']:
            result['reason'] = "❌ 系统未启用锚点单"
            result['decision_log'].append("❌ 配置检查: allow_anchor=False")
            self.record_trigger(inst_id, 'new', signal, 'skipped', result['reason'], open_amount)
            return result
        
        if not config['enabled']:
            result['reason'] = "❌ 系统未启用"
            result['decision_log'].append("❌ 配置检查: enabled=False")
            self.record_trigger(inst_id, 'new', signal, 'skipped', result['reason'], open_amount)
            return result
        
        result['decision_log'].append("✅ 系统配置检查通过")
        
        # 执行开仓
        try:
            # 记录到 position_opens 表
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO position_opens (
                inst_id, pos_side, open_price, open_size, open_percent,
                granularity, total_positions, is_anchor, timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id, 'short', signal['current_price'], open_amount, 1.0,
                'anchor', 1, 1, timestamp, timestamp
            ))
            
            position_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            result['success'] = True
            result['action'] = 'created'
            result['reason'] = f"✅ 锚点单创建成功 (ID: {position_id}, 金额: {open_amount} USDT)"
            result['decision_log'].append(f"✅ 锚点单已创建")
            result['decision_log'].append(f"📝 仓位ID: {position_id}")
            result['decision_log'].append(f"📝 方向: 做空(short)")
            result['decision_log'].append(f"📝 标记: 锚点单(is_anchor=True)")
            
            # 记录触发日志
            self.record_trigger(inst_id, 'new', signal, 'created', None, open_amount)
            
            print(f"✅ {inst_id} 新建锚点单: {open_amount} USDT @ {signal['current_price']:.4f}")
            
        except Exception as e:
            result['reason'] = f"❌ 创建失败: {str(e)}"
            result['decision_log'].append(f"❌ 执行失败: {str(e)}")
            self.record_trigger(inst_id, 'new', signal, 'failed', result['reason'], open_amount)
        
        return result
    
    def process_maintain_anchor(self, inst_id: str, signal: Dict, anchor_info: Dict) -> Dict:
        """
        处理维护锚点单
        新规则：
        1. 满足逃顶信号 + 已有锚点单 + 满足补仓条件(-10%) → 执行补仓
        2. 满足逃顶信号 + 已有锚点单 + 不满足补仓条件 → 只监控
        
        Returns:
            处理结果字典
        """
        result = {
            'inst_id': inst_id,
            'trigger_type': 'maintain',
            'success': False,
            'action': 'monitored',
            'reason': '',
            'open_amount': 0,
            'decision_log': []  # 新增：决策日志
        }
        
        # 计算当前盈亏率
        open_price = anchor_info['open_price']
        current_price = signal['current_price']
        
        # 🔴 重要：10倍杠杆下的盈亏计算
        # 做空：价格上涨1% → 亏损10%（1% × 10倍杠杆）
        # 做空：价格下跌1% → 盈利10%（1% × 10倍杠杆）
        price_change_rate = ((current_price - open_price) / open_price) * 100  # 价格变动%
        leverage = 10  # 10倍杠杆
        profit_rate = -price_change_rate * leverage  # 做空：价格涨→亏损，价格跌→盈利
        
        result['decision_log'].append(f"📊 已有锚点单: 开仓价={open_price:.4f}, 当前价={current_price:.4f}")
        result['decision_log'].append(f"📊 价格变动: {price_change_rate:+.2f}%")
        result['decision_log'].append(f"📊 杠杆盈亏率: {profit_rate:+.2f}% (10倍杠杆)")  
        
        # 检查是否需要补仓
        if not RULES['check_add_position']:
            result['action'] = 'monitored'
            result['reason'] = f"👁️ 监控模式: 当前盈亏 {profit_rate:.2f}%，不检查补仓条件"
            result['decision_log'].append("⚙️ 配置: check_add_position=False，只监控不补仓")
            self.record_trigger(inst_id, 'maintain', signal, 'monitored', result['reason'])
            print(f"👁️ {inst_id} 维护监控: 盈亏 {profit_rate:.2f}%")
            result['success'] = True
            return result
        
        # 检查补仓条件：亏损是否达到触发值
        add_trigger = RULES['add_position_trigger']
        result['decision_log'].append(f"⚙️ 补仓触发设置: {add_trigger}%")
        
        if profit_rate <= add_trigger:
            # 满足补仓条件
            result['decision_log'].append(f"✅ 满足补仓条件: {profit_rate:.2f}% <= {add_trigger}%")
            
            # 计算补仓金额（原金额的10倍）
            original_amount = anchor_info['open_size']
            add_amount = original_amount * 10
            result['open_amount'] = add_amount
            
            result['decision_log'].append(f"💰 补仓金额计算: {original_amount} × 10 = {add_amount} USDT")
            
            # 检查单币种限制
            passed, reason = self.trigger.check_single_coin_limit(inst_id, add_amount)
            if not passed:
                result['action'] = 'failed'
                result['reason'] = f"❌ 单币种限制: {reason}"
                result['decision_log'].append(f"❌ 单币种限制检查失败: {reason}")
                self.record_trigger(inst_id, 'maintain', signal, 'failed', result['reason'], add_amount)
                return result
            
            result['decision_log'].append(f"✅ 单币种限制检查通过")
            
            # 执行补仓
            try:
                from position_manager import PositionManager
                manager = PositionManager()
                
                # 调用补仓逻辑
                # 注意：这里需要实际的补仓执行逻辑
                # 暂时记录为待执行
                result['action'] = 'add_position_ready'
                result['reason'] = f"🔄 准备补仓: {add_amount} USDT (原{original_amount} USDT × 10倍)"
                result['decision_log'].append(f"🔄 执行补仓: {add_amount} USDT")
                result['decision_log'].append(f"📝 补仓后需立即平掉100 USDT，保留10 USDT名义（1U保证金）")
                
                self.record_trigger(inst_id, 'maintain', signal, 'add_position_ready', result['reason'], add_amount)
                print(f"🔄 {inst_id} 满足补仓条件: 盈亏 {profit_rate:.2f}%, 补仓 {add_amount} USDT")
                
            except Exception as e:
                result['action'] = 'failed'
                result['reason'] = f"❌ 补仓失败: {str(e)}"
                result['decision_log'].append(f"❌ 执行失败: {str(e)}")
                self.record_trigger(inst_id, 'maintain', signal, 'failed', result['reason'], add_amount)
        else:
            # 不满足补仓条件
            result['action'] = 'monitored'
            result['reason'] = f"👁️ 监控中: 盈亏 {profit_rate:.2f}% > {add_trigger}%，未达补仓条件"
            result['decision_log'].append(f"❌ 未满足补仓条件: {profit_rate:.2f}% > {add_trigger}%")
            result['decision_log'].append(f"👁️ 继续监控，等待触发")
            self.record_trigger(inst_id, 'maintain', signal, 'monitored', result['reason'])
            print(f"👁️ {inst_id} 继续监控: 盈亏 {profit_rate:.2f}%")
        
        result['success'] = True
        return result
    
    def scan_and_process(self) -> Dict:
        """
        扫描并处理锚点单开仓机会
        
        Returns:
            执行结果汇总
        """
        print("\n" + "=" * 80)
        print(f"🔍 锚点单自动开仓系统 - 扫描开始")
        print(f"⏰ 时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 获取逃顶信号
        signals = self.trigger.get_escape_top_signals()
        
        if not signals:
            print("📭 暂无逃顶信号")
            return {
                'success': True,
                'total_signals': 0,
                'processed': [],
                'summary': '暂无逃顶信号'
            }
        
        print(f"📊 发现 {len(signals)} 个逃顶信号\n")
        
        processed_results = []
        
        for signal in signals:
            inst_id = signal['inst_id']
            print(f"\n🎯 处理: {inst_id}")
            print(f"   压力线1: {signal['pressure1']:.4f}")
            print(f"   压力线2: {signal['pressure2']:.4f}")
            print(f"   当前价: {signal['current_price']:.4f}")
            
            # 检查是否已有原始锚点单
            has_anchor, anchor_info = self.check_existing_anchor(inst_id)
            
            if has_anchor:
                print(f"   ℹ️  已有锚点单: 开仓价 {anchor_info['open_price']:.4f}, 金额 {anchor_info['open_size']} USDT")
                result = self.process_maintain_anchor(inst_id, signal, anchor_info)
            else:
                print(f"   ✨ 没有锚点单，准备新建")
                result = self.process_new_anchor(inst_id, signal)
            
            print(f"   {result['reason']}")
            processed_results.append(result)
        
        # 生成汇总
        total = len(processed_results)
        created = sum(1 for r in processed_results if r['action'] == 'created')
        monitored = sum(1 for r in processed_results if r['action'] == 'monitored')
        skipped = sum(1 for r in processed_results if r['action'] == 'skipped')
        failed = sum(1 for r in processed_results if r.get('action') == 'failed')
        
        print("\n" + "=" * 80)
        print(f"📊 扫描完成汇总:")
        print(f"   总信号数: {total}")
        print(f"   ✅ 创建成功: {created}")
        print(f"   👁️  监控维护: {monitored}")
        print(f"   ⏭️  跳过: {skipped}")
        print(f"   ❌ 失败: {failed}")
        print("=" * 80 + "\n")
        
        return {
            'success': True,
            'total_signals': total,
            'created': created,
            'monitored': monitored,
            'skipped': skipped,
            'failed': failed,
            'processed': processed_results,
            'summary': f"处理{total}个信号: 创建{created}, 监控{monitored}, 跳过{skipped}, 失败{failed}"
        }
    
    def get_trigger_history(self, limit: int = 20) -> List[Dict]:
        """获取触发历史记录"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, inst_id, trigger_type, has_existing_anchor,
               pressure1, pressure2, current_price, open_amount,
               action_taken, skip_reason, trigger_reason, timestamp
        FROM anchor_triggers
        ORDER BY created_at DESC
        LIMIT ?
        ''', (limit,))
        
        records = []
        for row in cursor.fetchall():
            records.append({
                'id': row[0],
                'inst_id': row[1],
                'trigger_type': row[2],
                'has_existing_anchor': bool(row[3]),
                'pressure1': row[4],
                'pressure2': row[5],
                'current_price': row[6],
                'open_amount': row[7],
                'action_taken': row[8],
                'skip_reason': row[9],
                'trigger_reason': row[10],
                'timestamp': row[11]
            })
        
        conn.close()
        return records


def test_auto_opener():
    """测试自动开仓系统"""
    print("🧪 测试锚点单自动开仓系统")
    print()
    
    opener = AnchorAutoOpener()
    
    # 执行一次扫描
    result = opener.scan_and_process()
    
    # 显示历史记录
    print("\n📜 最近触发记录:")
    history = opener.get_trigger_history(limit=10)
    
    if history:
        for record in history:
            print(f"\n{record['timestamp']} - {record['inst_id']}")
            print(f"  类型: {record['trigger_type']}")
            print(f"  动作: {record['action_taken']}")
            if record['skip_reason']:
                print(f"  原因: {record['skip_reason']}")
    else:
        print("  暂无记录")
    
    print("\n✅ 测试完成")


if __name__ == '__main__':
    test_auto_opener()
