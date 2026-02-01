#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKEx交易执行模块 - 带安全闸门
"""

import hmac
import base64
import requests
import json
import time
from datetime import datetime
import pytz
import sqlite3

# OKEx API配置
OKEX_API_KEY = '0b05a729-40eb-4809-b3eb-eb2de75b7e9e'
OKEX_SECRET_KEY = '4E4DA8BE3B18D01AA07185A006BF9F8E'
OKEX_PASSPHRASE = 'Tencent@123'
OKEX_BASE_URL = 'https://www.okx.com'

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/trading_decision.db'


class SafetyGate:
    """安全闸门"""
    
    def __init__(self, db_path=None):
        """初始化安全闸门"""
        self.db_path = db_path or DB_PATH
    
    def is_master_switch_on(self):
        """检查总开关是否开启"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute('SELECT enabled FROM market_config ORDER BY updated_at DESC LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            return bool(result[0]) if result else False
        except:
            return False
    
    def check_can_trade(self, inst_id):
        """
        检查是否可以交易
        
        Args:
            inst_id: 币种ID
        
        Returns:
            bool: 是否可以交易
        """
        # 1. 检查总开关
        if not self.is_master_switch_on():
            return False
        
        # 2. 检查币种开关
        if not self.check_coin_switch(inst_id):
            return False
        
        return True
    
    def check_coin_switch(self, inst_id):
        """检查单个币种开关"""
        # TODO: 实现单个币种开关表
        return True
    
    @staticmethod
    def check_position_limit(inst_id, new_size, total_capital, position_limit_percent):
        """检查仓位限制"""
        # 计算允许的最大仓位
        max_allowed = total_capital * (position_limit_percent / 100)
        
        # 获取当前总仓位
        current_total = SafetyGate.get_current_total_position()
        
        if current_total + new_size > max_allowed:
            return False, f"仓位超限：当前{current_total}U + 新增{new_size}U > 限额{max_allowed}U"
        
        return True, "仓位检查通过"
    
    @staticmethod
    def get_current_total_position():
        """获取当前总仓位（USDT）"""
        # TODO: 从OKEx API获取实时仓位
        return 0
    
    @staticmethod
    def can_execute_trade(inst_id, action, size, pos_side, config):
        """
        综合检查是否可以执行交易
        
        Args:
            inst_id: 币种ID
            action: 动作类型 (open/add/close)
            size: 交易数量
            pos_side: 持仓方向 (long/short)
            config: 系统配置
        
        Returns:
            (bool, str): (是否允许, 原因)
        """
        # 创建临时实例检查总开关
        gate = SafetyGate()
        
        # 1. 检查总开关
        if not gate.is_master_switch_on():
            return False, "❌ 总开关已关闭"
        
        # 2. 检查币种开关
        if not gate.check_coin_switch(inst_id):
            return False, f"❌ {inst_id}币种开关已关闭"
        
        # 3. 对于开仓/补仓，检查方向是否允许
        if action in ['open', 'add']:
            # 检查是否允许做多
            if pos_side == 'long' and not config.get('allow_long', False):
                return False, f"❌ 系统禁止做多"
            
            # 检查是否允许做空
            if pos_side == 'short' and not config.get('allow_short', True):
                return False, f"❌ 系统禁止做空"
            
            # 检查方向仓位限制
            allowed, msg = SafetyGate.check_direction_position_limit(
                inst_id, size, pos_side, config
            )
            if not allowed:
                return False, msg
        
        return True, "✅ 安全检查通过"
    
    @staticmethod
    def check_direction_position_limit(inst_id, new_size, pos_side, config):
        """
        检查方向仓位限制
        
        Args:
            inst_id: 币种ID
            new_size: 新增仓位大小
            pos_side: 持仓方向 (long/short)
            config: 系统配置
        
        Returns:
            (bool, str): (是否允许, 原因)
        """
        # 获取当前方向的总仓位
        current_position = SafetyGate.get_direction_position(pos_side)
        
        # 获取该方向的最大仓位限制
        if pos_side == 'long':
            max_position = config.get('max_long_position', 500)
            direction_name = "多单"
        else:
            max_position = config.get('max_short_position', 600)
            direction_name = "空单"
        
        # 检查是否超限
        if current_position + new_size > max_position:
            return False, f"❌ {direction_name}仓位超限：当前{current_position:.2f}U + 新增{new_size:.2f}U > 限额{max_position:.2f}U"
        
        return True, f"✅ {direction_name}仓位检查通过"
    
    @staticmethod
    def get_direction_position(pos_side):
        """
        获取指定方向的当前总仓位（USDT）
        
        Args:
            pos_side: 持仓方向 (long/short)
        
        Returns:
            float: 当前该方向的总仓位
        """
        # TODO: 从OKEx API获取实时仓位
        # 这里应该调用OKEx API获取真实的持仓数据
        # 并按pos_side筛选计算总仓位
        return 0


class OKExTrader:
    """OKEx交易执行器"""
    
    def __init__(self, dry_run=True):
        """
        初始化OKEx交易执行器
        
        Args:
            dry_run: 是否模拟运行（True不实际下单）
        """
        self.api_key = OKEX_API_KEY
        self.secret_key = OKEX_SECRET_KEY
        self.passphrase = OKEX_PASSPHRASE
        self.base_url = OKEX_BASE_URL
        self.dry_run = dry_run
    
    def get_signature(self, timestamp, method, request_path, body=''):
        """生成签名"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
    
    def get_headers(self, method, request_path, body=''):
        """获取请求头"""
        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
        signature = self.get_signature(timestamp, method, request_path, body)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    def get_positions(self):
        """获取当前持仓"""
        method = 'GET'
        request_path = '/api/v5/account/positions'
        
        try:
            headers = self.get_headers(method, request_path)
            response = requests.get(
                self.base_url + request_path,
                headers=headers,
                timeout=10
            )
            
            data = response.json()
            if data.get('code') == '0':
                positions = data.get('data', [])
                # 只返回有持仓的
                return [p for p in positions if float(p.get('pos', 0)) != 0]
            else:
                print(f"❌ 获取持仓失败: {data.get('msg')}")
                return []
        except Exception as e:
            print(f"❌ 获取持仓异常: {e}")
            return []
    
    def close_position(self, inst_id, pos_side, close_size, price=None):
        """
        平仓
        
        Args:
            inst_id: 币种
            pos_side: 持仓方向 (long/short)
            close_size: 平仓数量
            price: 价格（None为市价）
        """
        # 平空单 = 买入，平多单 = 卖出
        side = 'buy' if pos_side == 'short' else 'sell'
        
        order_data = {
            'instId': inst_id,
            'tdMode': 'cross',  # 全仓模式
            'side': side,
            'posSide': pos_side,
            'ordType': 'market' if price is None else 'limit',
            'sz': str(close_size)
        }
        
        if price:
            order_data['px'] = str(price)
        
        return self.place_order(order_data)
    
    def place_order(self, order_data):
        """下单"""
        method = 'POST'
        request_path = '/api/v5/trade/order'
        body = json.dumps(order_data)
        
        try:
            headers = self.get_headers(method, request_path, body)
            response = requests.post(
                self.base_url + request_path,
                headers=headers,
                data=body,
                timeout=10
            )
            
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ 下单成功: {order_data['instId']} {order_data.get('side')} {order_data.get('sz')}")
                return True, data
            else:
                print(f"❌ 下单失败: {data.get('msg')}")
                return False, data
        except Exception as e:
            print(f"❌ 下单异常: {e}")
            return False, {'error': str(e)}
    
    def execute_trade(self, inst_id, trade_mode, pos_side, side, order_type, size, reason=''):
        """
        执行交易
        
        Args:
            inst_id: 币种
            trade_mode: 交易模式 (isolated/cross)
            pos_side: 持仓方向 (long/short)
            side: 买卖方向 (buy/sell)
            order_type: 订单类型 (market/limit)
            size: 数量
            reason: 原因
        
        Returns:
            bool: 是否成功
        """
        if self.dry_run:
            print(f"🔸 [模拟] {reason}")
            print(f"   {inst_id} {pos_side} {side} {size}")
            return True
        
        order_data = {
            'instId': inst_id,
            'tdMode': trade_mode,
            'side': side,
            'posSide': pos_side,
            'ordType': order_type,
            'sz': str(size)
        }
        
        success, data = self.place_order(order_data)
        return success


def execute_trading_decision(decision, config, dry_run=True):
    """
    执行交易决策
    
    Args:
        decision: 交易决策
        config: 配置
        dry_run: 是否模拟运行（不实际下单）
    """
    inst_id = decision.get('inst_id')
    action = decision.get('action')
    size = decision.get('close_size', 0)
    
    print("\n" + "=" * 80)
    print(f"📋 执行交易决策: {inst_id} - {action}")
    print("=" * 80)
    
    # 安全检查
    can_trade, reason = SafetyGate.can_execute_trade(inst_id, action, size, config)
    print(f"🔒 安全检查: {reason}")
    
    if not can_trade:
        print("❌ 交易被阻止")
        return False
    
    if dry_run:
        print("🎭 模拟模式 - 不实际执行交易")
        print(f"   币种: {inst_id}")
        print(f"   动作: {action}")
        print(f"   数量: {size}")
        print(f"   原因: {decision.get('reason')}")
        return True
    else:
        print("💰 实盘模式 - 执行交易")
        trader = OKExTrader()
        
        if action == 'close':
            success, result = trader.close_position(
                inst_id,
                decision.get('pos_side'),
                size
            )
            return success
        
        return False


if __name__ == '__main__':
    print("=" * 80)
    print("OKEx交易执行模块测试")
    print("=" * 80)
    
    # 测试获取持仓
    trader = OKExTrader()
    print("\n【测试1】获取当前持仓")
    positions = trader.get_positions()
    print(f"持仓数量: {len(positions)}")
    for pos in positions[:3]:
        print(f"  - {pos.get('instId')}: {pos.get('pos')} ({pos.get('posSide')})")
    
    # 测试安全闸门
    print("\n【测试2】安全闸门检查")
    print(f"总开关状态: {SafetyGate.check_master_switch()}")
    
    # 测试模拟交易
    print("\n【测试3】模拟交易执行")
    test_decision = {
        'inst_id': 'BTC-USDT-SWAP',
        'pos_side': 'short',
        'action': 'close',
        'close_size': 0.001,
        'reason': '测试平仓'
    }
    execute_trading_decision(test_decision, {'total_capital': 1000}, dry_run=True)
    
    print("\n✅ 测试完成")
