#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条件单监控守护进程
功能：
1. 监控条件单触发条件
2. 触发后自动开仓
3. 自动平仓95%，保留1U保证金
4. 每天0点自动重置条件单
"""

import sqlite3
import time
import logging
from datetime import datetime, timedelta
import sys
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/conditional_order_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

DB_PATH = '/home/user/webapp/trading_decision.db'
CRYPTO_DB_PATH = '/home/user/webapp/crypto_data.db'
API_BASE_URL = 'http://localhost:5000/api/trading'

class ConditionalOrderMonitor:
    """条件单监控器"""
    
    def __init__(self):
        self.last_reset_date = None
        logger.info("🚀 条件单监控守护进程启动")
    
    def get_current_price(self, inst_id):
        """从crypto_data.db获取当前价格"""
        try:
            symbol = inst_id.replace('-USDT-SWAP', 'USDT')
            
            conn = sqlite3.connect(CRYPTO_DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT current_price
                FROM support_resistance_levels
                WHERE symbol = ?
                ORDER BY record_time DESC
                LIMIT 1
            ''', (symbol,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                logger.warning(f"⚠️ 未找到 {symbol} 的价格数据")
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取价格失败 {inst_id}: {e}")
            return None
    
    def check_and_trigger_orders(self):
        """检查并触发条件单"""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            
            # 查询所有待触发的条件单
            cursor.execute('''
                SELECT id, inst_id, pos_side, order_type, anchor_price, 
                       target_price, price_diff_percent, order_size
                FROM pending_orders
                WHERE status = 'pending'
            ''')
            
            orders = cursor.fetchall()
            
            for order in orders:
                order_id, inst_id, pos_side, order_type, anchor_price, \
                target_price, price_diff_percent, order_size = order
                
                # 获取当前价格
                current_price = self.get_current_price(inst_id)
                
                if current_price is None:
                    continue
                
                # 检查是否触发（做空的情况，价格上涨触发）
                if pos_side == 'short' and current_price >= target_price:
                    logger.info(f"🔔 条件单触发: {inst_id} 当前价格 {current_price} >= 触发价格 {target_price}")
                    self.execute_conditional_order(order_id, inst_id, pos_side, order_size, 
                                                   current_price, price_diff_percent)
                
                # 检查是否触发（做多的情况，价格下跌触发）
                elif pos_side == 'long' and current_price <= target_price:
                    logger.info(f"🔔 条件单触发: {inst_id} 当前价格 {current_price} <= 触发价格 {target_price}")
                    self.execute_conditional_order(order_id, inst_id, pos_side, order_size, 
                                                   current_price, price_diff_percent)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 检查条件单失败: {e}")
    
    def execute_conditional_order(self, order_id, inst_id, pos_side, order_size, 
                                  trigger_price, price_diff_percent):
        """执行条件单：开仓 + 立即平仓95%"""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            
            # 1. 更新条件单状态为已触发
            cursor.execute('''
                UPDATE pending_orders
                SET status = 'triggered',
                    timestamp = ?
                WHERE id = ?
            ''', (
                (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'),
                order_id
            ))
            
            # 2. 记录触发日志
            logger.info(f"✅ 条件单 {order_id} 已触发: {inst_id} {pos_side} 数量 {order_size}")
            
            # 3. 创建开仓记录（模拟开仓）
            # 注意：这里应该调用真实的OKX API开仓，目前只记录到数据库
            cursor.execute('''
                INSERT INTO position_opens (
                    inst_id, pos_side, open_price, open_size, open_percent,
                    granularity, total_positions, is_anchor, timestamp, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                trigger_price,
                order_size,
                0.0,  # open_percent
                0.0,  # granularity
                0,    # total_positions
                0,    # is_anchor (条件单开仓不是锚点单)
                (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'),
                (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            position_id = cursor.lastrowid
            
            # 4. 立即平仓95%，保留1U保证金（10U名义价值）
            leverage = 10  # 10x杠杆
            current_nominal = order_size * trigger_price
            current_margin = current_nominal / leverage
            
            # 保留1U保证金对应10U名义价值
            keep_margin = 1.0
            keep_nominal = keep_margin * leverage  # 10U
            
            # 计算需要平仓的部分
            close_nominal = current_nominal - keep_nominal
            close_margin = close_nominal / leverage
            close_size = close_nominal / trigger_price
            
            # 只有当持仓大于10U时才平仓
            if current_nominal > 10.0:
                # 更新持仓记录
                new_size = keep_nominal / trigger_price
                
                cursor.execute('''
                    UPDATE position_opens
                    SET open_size = ?,
                        updated_time = ?
                    WHERE id = ?
                ''', (
                    new_size,
                    (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'),
                    position_id
                ))
                
                # 记录平仓
                cursor.execute('''
                    INSERT INTO position_closes (
                        inst_id, pos_side, close_size, close_price, close_reason,
                        profit_rate, unrealized_pnl, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    inst_id,
                    pos_side,
                    close_size,
                    trigger_price,
                    f'条件单触发后自动平仓95%（{price_diff_percent}%触发，保留1U保证金）',
                    0.0,  # profit_rate (触发时刻没有盈亏)
                    0.0,  # unrealized_pnl
                    (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                logger.info(f"✅ 自动平仓95%: {inst_id} 平仓数量 {close_size:.4f} 保留 {new_size:.4f}")
            else:
                logger.info(f"⚠️ 持仓过小，不执行平仓: {inst_id} 名义价值 {current_nominal:.2f}U")
            
            # 5. 记录交易决策
            cursor.execute('''
                INSERT INTO trading_decisions (
                    inst_id, pos_side, action, decision_type, 
                    current_size, target_size, close_size, close_percent,
                    profit_rate, current_price, reason, executed, 
                    timestamp, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst_id,
                pos_side,
                'conditional_trigger_and_close',
                'conditional_order',
                order_size,
                new_size if current_nominal > 10.0 else order_size,
                close_size if current_nominal > 10.0 else 0,
                95.0 if current_nominal > 10.0 else 0,
                0.0,
                trigger_price,
                f'条件单触发（+{price_diff_percent}%）并自动平仓95%，保留1U保证金',
                1,
                (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S'),
                (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"🎉 条件单执行完成: {inst_id} 触发价 {trigger_price}")
            
        except Exception as e:
            logger.error(f"❌ 执行条件单失败 {order_id}: {e}")
    
    def reset_conditional_orders(self):
        """重置所有条件单（每天0点调用）"""
        try:
            logger.info("🔄 开始重置条件单...")
            
            # 调用创建条件单API
            response = requests.post(f"{API_BASE_URL}/orders/pending/create-auto")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"✅ 条件单重置成功: {data.get('message')}")
                    logger.info(f"   - 锚点单数量: {data.get('total_anchors')}")
                    logger.info(f"   - 条件单数量: {data.get('total_orders')}")
                else:
                    logger.error(f"❌ 条件单重置失败: {data.get('error')}")
            else:
                logger.error(f"❌ 条件单重置API调用失败: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ 重置条件单异常: {e}")
    
    def check_daily_reset(self):
        """检查是否需要每日重置"""
        now = datetime.now()
        current_date = now.date()
        
        # 检查是否是新的一天
        if self.last_reset_date != current_date:
            # 检查是否是0点后（允许0点到1点之间执行）
            if now.hour == 0:
                logger.info(f"📅 检测到新的一天: {current_date}，准备重置条件单")
                self.reset_conditional_orders()
                self.last_reset_date = current_date
    
    def run(self):
        """主循环"""
        logger.info("🔄 条件单监控守护进程运行中...")
        
        check_interval = 30  # 30秒检查一次
        
        while True:
            try:
                # 检查条件单触发
                self.check_and_trigger_orders()
                
                # 检查是否需要每日重置
                self.check_daily_reset()
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("⏹️ 收到停止信号，退出监控...")
                break
            except Exception as e:
                logger.error(f"❌ 监控循环异常: {e}")
                time.sleep(check_interval)

if __name__ == '__main__':
    monitor = ConditionalOrderMonitor()
    monitor.run()
