#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多单开仓监控系统
功能：监控空单盈利率，记录30%以上的锚点单，40%以上触发开仓
"""

import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库路径
TRADING_DB = '/home/user/webapp/trading_decision.db'
CRYPTO_DB = '/home/user/webapp/crypto_data.db'

class LongPositionMonitor:
    """多单开仓监控器"""
    
    def __init__(self):
        """初始化"""
        self.trading_db = TRADING_DB
        self.crypto_db = CRYPTO_DB
        self.monitoring_threshold = 30.0  # 监控阈值：30%
        self.trigger_threshold = 40.0     # 触发阈值：40%
        print("🚀 多单开仓监控系统启动")
        print(f"📊 监控阈值: {self.monitoring_threshold}%")
        print(f"🎯 触发阈值: {self.trigger_threshold}%")
        print("=" * 60)
    
    def get_anchor_positions(self) -> List[Dict]:
        """获取所有锚点单持仓"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取所有空单锚点单
            cursor.execute('''
            SELECT 
                id,
                inst_id,
                pos_side,
                open_size,
                open_price,
                created_at
            FROM position_opens
            WHERE is_anchor = 1 AND pos_side = 'short'
            ORDER BY created_at DESC
            ''')
            
            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'id': row['id'],
                    'inst_id': row['inst_id'],
                    'pos_side': row['pos_side'],
                    'open_size': row['open_size'],
                    'open_price': row['open_price'],
                    'created_at': row['created_at']
                })
            
            conn.close()
            return positions
            
        except Exception as e:
            print(f"❌ 获取锚点单持仓失败: {e}")
            return []
    
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
    
    def calculate_profit_rate(self, open_price: float, current_price: float, pos_side: str) -> float:
        """计算收益率（含10倍杠杆）"""
        if pos_side == 'short':
            # 空单：价格下跌盈利
            price_change = (open_price - current_price) / open_price
        else:
            # 多单：价格上涨盈利
            price_change = (current_price - open_price) / open_price
        
        # 10倍杠杆
        profit_rate = price_change * 10 * 100
        return profit_rate
    
    def log_monitoring(self, position: Dict, current_price: float, profit_rate: float, status: str):
        """记录监控日志"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 创建监控日志表（如果不存在）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS long_position_monitoring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,
                inst_id TEXT NOT NULL,
                pos_side TEXT NOT NULL,
                open_price REAL NOT NULL,
                current_price REAL NOT NULL,
                profit_rate REAL NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 生成消息
            if status == 'monitoring':
                message = f'空单盈利{profit_rate:.2f}%，进入监控（距离触发还差{self.trigger_threshold - profit_rate:.2f}%）'
            elif status == 'ready_to_open':
                message = f'空单盈利{profit_rate:.2f}%，达到开仓条件！'
            elif status == 'below_threshold':
                message = f'空单盈利{profit_rate:.2f}%，低于监控阈值'
            else:
                message = f'空单盈利{profit_rate:.2f}%'
            
            # 插入日志
            timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            INSERT INTO long_position_monitoring 
            (position_id, inst_id, pos_side, open_price, current_price, profit_rate, status, message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position['id'],
                position['inst_id'],
                position['pos_side'],
                position['open_price'],
                current_price,
                profit_rate,
                status,
                message,
                timestamp
            ))
            
            conn.commit()
            log_id = cursor.lastrowid
            conn.close()
            
            return log_id, message
            
        except Exception as e:
            print(f"❌ 记录监控日志失败: {e}")
            return None, str(e)
    
    def scan_positions(self) -> Dict:
        """扫描所有锚点单，记录监控日志"""
        print(f"\n{'='*60}")
        print(f"🔍 开始扫描锚点单盈利率 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 获取所有锚点单
        positions = self.get_anchor_positions()
        
        if not positions:
            print("📭 暂无锚点单持仓")
            return {
                'total': 0,
                'monitoring': 0,
                'ready_to_open': 0,
                'below_threshold': 0,
                'results': []
            }
        
        print(f"📊 找到 {len(positions)} 个空单锚点单\n")
        
        results = []
        monitoring_count = 0
        ready_count = 0
        below_count = 0
        
        for position in positions:
            inst_id = position['inst_id']
            open_price = position['open_price']
            
            # 获取当前价格
            current_price = self.get_current_price(inst_id)
            if not current_price:
                print(f"⚠️  {inst_id}: 无法获取当前价格，跳过")
                continue
            
            # 计算收益率
            profit_rate = self.calculate_profit_rate(open_price, current_price, position['pos_side'])
            
            # 判断状态
            if profit_rate >= self.trigger_threshold:
                # 达到触发条件（≥40%）
                status = 'ready_to_open'
                status_icon = '🔥'
                ready_count += 1
            elif profit_rate >= self.monitoring_threshold:
                # 进入监控（30%-40%）
                status = 'monitoring'
                status_icon = '👀'
                monitoring_count += 1
            else:
                # 低于监控阈值（<30%）
                status = 'below_threshold'
                status_icon = '📊'
                below_count += 1
            
            # 记录日志
            log_id, message = self.log_monitoring(position, current_price, profit_rate, status)
            
            # 打印结果
            print(f"{status_icon} {inst_id}")
            print(f"   开仓价: {open_price:.4f}")
            print(f"   当前价: {current_price:.4f}")
            print(f"   收益率: {profit_rate:.2f}%")
            print(f"   状态: {message}")
            print(f"   日志ID: #{log_id}")
            print()
            
            results.append({
                'inst_id': inst_id,
                'open_price': open_price,
                'current_price': current_price,
                'profit_rate': profit_rate,
                'status': status,
                'message': message,
                'log_id': log_id
            })
        
        # 汇总
        print(f"{'='*60}")
        print(f"📊 扫描完成汇总:")
        print(f"   总计: {len(positions)} 个")
        print(f"   🔥 达到触发条件（≥40%）: {ready_count} 个")
        print(f"   👀 进入监控（30%-40%）: {monitoring_count} 个")
        print(f"   📊 低于监控阈值（<30%）: {below_count} 个")
        print(f"{'='*60}\n")
        
        return {
            'total': len(positions),
            'monitoring': monitoring_count,
            'ready_to_open': ready_count,
            'below_threshold': below_count,
            'results': results
        }
    
    def get_monitoring_logs(self, limit: int = 50) -> List[Dict]:
        """获取监控日志"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT *
            FROM long_position_monitoring
            ORDER BY created_at DESC
            LIMIT ?
            ''', (limit,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'id': row['id'],
                    'position_id': row['position_id'],
                    'inst_id': row['inst_id'],
                    'open_price': row['open_price'],
                    'current_price': row['current_price'],
                    'profit_rate': row['profit_rate'],
                    'status': row['status'],
                    'message': row['message'],
                    'timestamp': row['timestamp'],
                    'created_at': row['created_at']
                })
            
            conn.close()
            return logs
            
        except Exception as e:
            print(f"❌ 获取监控日志失败: {e}")
            return []
    
    def print_monitoring_logs(self, limit: int = 20):
        """打印监控日志"""
        logs = self.get_monitoring_logs(limit)
        
        if not logs:
            print("📭 暂无监控日志")
            return
        
        print(f"\n{'='*60}")
        print(f"📋 最近 {len(logs)} 条监控日志")
        print(f"{'='*60}\n")
        
        for log in logs:
            status_icons = {
                'ready_to_open': '🔥',
                'monitoring': '👀',
                'below_threshold': '📊'
            }
            icon = status_icons.get(log['status'], '❓')
            
            print(f"{icon} #{log['id']} - {log['inst_id']}")
            print(f"   时间: {log['timestamp']}")
            print(f"   收益率: {log['profit_rate']:.2f}%")
            print(f"   状态: {log['message']}")
            print()

def main():
    """主函数"""
    monitor = LongPositionMonitor()
    
    # 扫描一次
    result = monitor.scan_positions()
    
    # 显示最近日志
    if result['total'] > 0:
        print("\n")
        monitor.print_monitoring_logs(limit=10)

if __name__ == "__main__":
    main()
