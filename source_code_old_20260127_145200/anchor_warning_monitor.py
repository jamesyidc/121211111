#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单预警监控系统
功能：监控锚点单，记录-8%预警，为-10%维护提供早期信号
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库路径
TRADING_DB = '/home/user/webapp/trading_decision.db'
ANCHOR_DB = '/home/user/webapp/anchor_system.db'

class AnchorWarningMonitor:
    """锚点单预警监控"""
    
    def __init__(self, trade_mode='paper'):
        """初始化"""
        self.trading_db = TRADING_DB
        self.anchor_db = ANCHOR_DB
        self.warning_threshold = -8.0  # 预警阈值
        self.critical_threshold = -10.0  # 临界阈值
        self.trade_mode = trade_mode  # paper 或 live
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 创建预警监控表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS anchor_warning_monitor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inst_id TEXT NOT NULL,
                pos_side TEXT NOT NULL,
                open_price REAL NOT NULL,
                current_price REAL NOT NULL,
                profit_rate REAL NOT NULL,
                open_size REAL NOT NULL,
                open_percent REAL NOT NULL,
                warning_level TEXT DEFAULT 'warning',
                alert_message TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建索引
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_warning_inst 
            ON anchor_warning_monitor(inst_id, pos_side)
            ''')
            
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_warning_created 
            ON anchor_warning_monitor(created_at)
            ''')
            
            # 创建预警操作日志表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS anchor_warning_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                warning_id INTEGER,
                inst_id TEXT NOT NULL,
                pos_side TEXT NOT NULL,
                action TEXT NOT NULL,
                profit_rate REAL NOT NULL,
                current_price REAL NOT NULL,
                operator TEXT DEFAULT 'system',
                remark TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_warning_logs_inst 
            ON anchor_warning_logs(inst_id, pos_side)
            ''')
            
            conn.commit()
            conn.close()
            
            print("✅ 预警监控数据库初始化完成")
            
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
    
    def get_anchor_positions(self) -> List[Dict]:
        """获取所有锚点单持仓"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT 
                inst_id,
                pos_side,
                open_size,
                open_price,
                open_percent,
                total_positions,
                mark_price,
                profit_rate,
                timestamp,
                created_at
            FROM position_opens
            WHERE is_anchor = 1 AND (trade_mode = ? OR trade_mode IS NULL)
            ''', (self.trade_mode,))
            
            positions = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return positions
            
        except Exception as e:
            print(f"❌ 获取锚点单失败: {e}")
            return []
    
    def get_current_price(self, inst_id: str, pos_side: str = 'short') -> Optional[float]:
        """获取当前价格（模拟盘从数据库读取，实盘从OKEx API获取）"""
        try:
            # 模拟盘：从数据库读取 mark_price
            if self.trade_mode == 'paper':
                conn = sqlite3.connect(self.trading_db, timeout=10.0)
                cursor = conn.cursor()
                cursor.execute('''
                SELECT mark_price FROM position_opens
                WHERE inst_id = ? AND pos_side = ? AND is_anchor = 1 AND (trade_mode = ? OR trade_mode IS NULL)
                ORDER BY updated_time DESC
                LIMIT 1
                ''', (inst_id, pos_side, self.trade_mode))
                
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0]:
                    return float(result[0])
                return None
            
            # 实盘：从 OKEx API 获取
            import sys
            sys.path.append('/home/user/webapp')
            from anchor_system import get_positions
            
            # 从 OKEx API 获取所有持仓
            positions = get_positions()
            
            if not positions:
                return None
            
            # 查找对应的持仓
            for pos in positions:
                if pos.get('instId') == inst_id:
                    mark_price = float(pos.get('markPx', 0))
                    return mark_price if mark_price > 0 else None
            
            return None
            
        except Exception as e:
            print(f"❌ 获取价格失败 {inst_id}: {e}")
            return None
    
    def calculate_profit_rate(self, open_price: float, current_price: float, pos_side: str) -> float:
        """计算收益率（不含杠杆，数据库中已按10x计算）"""
        if pos_side == 'long':
            profit_rate = (current_price - open_price) / open_price * 100
        else:  # short
            profit_rate = (open_price - current_price) / open_price * 100
        return profit_rate
    
    def check_existing_warning(self, inst_id: str, pos_side: str) -> Optional[Dict]:
        """检查是否已有活跃预警"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM anchor_warning_monitor
            WHERE inst_id = ? AND pos_side = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            ''', (inst_id, pos_side))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            print(f"❌ 检查预警失败: {e}")
            return None
    
    def record_warning(self, position: Dict, current_price: float, profit_rate: float) -> Optional[int]:
        """记录预警"""
        try:
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 确定预警级别
            if profit_rate <= self.critical_threshold:
                warning_level = 'critical'
                alert_message = f"❗ 临界预警：亏损{profit_rate:.2f}%，即将触发维护"
            elif profit_rate <= self.warning_threshold:
                warning_level = 'warning'
                alert_message = f"⚠️ 预警：亏损{profit_rate:.2f}%，距离维护阈值{abs(profit_rate - self.critical_threshold):.2f}%"
            else:
                warning_level = 'info'
                alert_message = f"ℹ️ 监控：收益率{profit_rate:.2f}%"
            
            # 插入预警记录
            cursor.execute('''
            INSERT INTO anchor_warning_monitor (
                inst_id, pos_side, open_price, current_price, profit_rate,
                open_size, open_percent, warning_level, alert_message,
                status, created_at, updated_at, trade_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position['inst_id'],
                position['pos_side'],
                position['open_price'],
                current_price,
                profit_rate,
                position['open_size'],
                position['open_percent'],
                warning_level,
                alert_message,
                'active',
                now,
                now,
                self.trade_mode
            ))
            
            warning_id = cursor.lastrowid
            
            # 记录操作日志
            cursor.execute('''
            INSERT INTO anchor_warning_logs (
                warning_id, inst_id, pos_side, action, profit_rate, 
                current_price, operator, remark, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                warning_id,
                position['inst_id'],
                position['pos_side'],
                'create_warning',
                profit_rate,
                current_price,
                'system',
                alert_message,
                now
            ))
            
            conn.commit()
            conn.close()
            
            return warning_id
            
        except Exception as e:
            print(f"❌ 记录预警失败: {e}")
            return None
    
    def update_warning(self, warning_id: int, current_price: float, profit_rate: float) -> bool:
        """更新预警记录"""
        try:
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 确定预警级别
            if profit_rate <= self.critical_threshold:
                warning_level = 'critical'
                alert_message = f"❗ 临界预警：亏损{profit_rate:.2f}%，即将触发维护"
            elif profit_rate <= self.warning_threshold:
                warning_level = 'warning'
                alert_message = f"⚠️ 预警：亏损{profit_rate:.2f}%，距离维护阈值{abs(profit_rate - self.critical_threshold):.2f}%"
            else:
                warning_level = 'info'
                alert_message = f"ℹ️ 监控：收益率{profit_rate:.2f}%"
            
            # 更新预警记录
            cursor.execute('''
            UPDATE anchor_warning_monitor
            SET current_price = ?, profit_rate = ?, warning_level = ?,
                alert_message = ?, updated_at = ?
            WHERE id = ?
            ''', (current_price, profit_rate, warning_level, alert_message, now, warning_id))
            
            # 获取inst_id和pos_side
            cursor.execute('SELECT inst_id, pos_side FROM anchor_warning_monitor WHERE id = ?', (warning_id,))
            result = cursor.fetchone()
            
            if result:
                inst_id, pos_side = result
                
                # 记录操作日志
                cursor.execute('''
                INSERT INTO anchor_warning_logs (
                    warning_id, inst_id, pos_side, action, profit_rate, 
                    current_price, operator, remark, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    warning_id,
                    inst_id,
                    pos_side,
                    'update_warning',
                    profit_rate,
                    current_price,
                    'system',
                    alert_message,
                    now
                ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ 更新预警失败: {e}")
            return False
    
    def close_warning(self, warning_id: int, reason: str = '恢复正常') -> bool:
        """关闭预警"""
        try:
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 获取预警信息
            cursor.execute('''
            SELECT inst_id, pos_side, profit_rate, current_price 
            FROM anchor_warning_monitor 
            WHERE id = ?
            ''', (warning_id,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            inst_id, pos_side, profit_rate, current_price = result
            
            # 更新预警状态
            cursor.execute('''
            UPDATE anchor_warning_monitor
            SET status = 'closed', updated_at = ?
            WHERE id = ?
            ''', (now, warning_id))
            
            # 记录操作日志
            cursor.execute('''
            INSERT INTO anchor_warning_logs (
                warning_id, inst_id, pos_side, action, profit_rate, 
                current_price, operator, remark, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                warning_id,
                inst_id,
                pos_side,
                'close_warning',
                profit_rate,
                current_price,
                'system',
                reason,
                now
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ 关闭预警失败: {e}")
            return False
    
    def scan_warnings(self) -> Dict:
        """扫描并更新预警"""
        try:
            positions = self.get_anchor_positions()
            
            if not positions:
                return {
                    'success': True,
                    'total_scanned': 0,
                    'warnings': [],
                    'message': '无锚点单需要监控'
                }
            
            warnings = []
            
            for position in positions:
                inst_id = position['inst_id']
                pos_side = position['pos_side']
                open_price = float(position['open_price'])
                
                # 优先使用数据库中的 mark_price 和 profit_rate
                if position.get('mark_price') and position.get('profit_rate') is not None:
                    current_price = float(position['mark_price'])
                    profit_rate = float(position['profit_rate'])
                else:
                    # 获取当前价格
                    current_price = self.get_current_price(inst_id, pos_side)
                    if not current_price:
                        continue
                    
                    # 计算收益率
                    profit_rate = self.calculate_profit_rate(open_price, current_price, pos_side)
                
                # 检查是否需要预警（亏损超过-8%）
                if profit_rate <= self.warning_threshold:
                    # 检查是否已有预警
                    existing = self.check_existing_warning(inst_id, pos_side)
                    
                    if existing:
                        # 更新现有预警
                        self.update_warning(existing['id'], current_price, profit_rate)
                        warning_id = existing['id']
                    else:
                        # 创建新预警
                        warning_id = self.record_warning(position, current_price, profit_rate)
                    
                    warnings.append({
                        'warning_id': warning_id,
                        'inst_id': inst_id,
                        'pos_side': pos_side,
                        'open_price': open_price,
                        'current_price': current_price,
                        'profit_rate': profit_rate,
                        'warning_level': 'critical' if profit_rate <= self.critical_threshold else 'warning'
                    })
                else:
                    # 收益率恢复，关闭预警
                    existing = self.check_existing_warning(inst_id, pos_side)
                    if existing:
                        self.close_warning(existing['id'], f'收益率恢复至{profit_rate:.2f}%')
            
            return {
                'success': True,
                'total_scanned': len(positions),
                'warnings_count': len(warnings),
                'warnings': warnings
            }
            
        except Exception as e:
            print(f"❌ 扫描预警失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_active_warnings(self) -> List[Dict]:
        """获取所有活跃预警"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM anchor_warning_monitor
            WHERE status = 'active'
            ORDER BY profit_rate ASC, created_at DESC
            ''')
            
            warnings = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return warnings
            
        except Exception as e:
            print(f"❌ 获取活跃预警失败: {e}")
            return []
    
    def get_warning_logs(self, inst_id: str = None, limit: int = 100) -> List[Dict]:
        """获取预警操作日志"""
        try:
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if inst_id:
                cursor.execute('''
                SELECT * FROM anchor_warning_logs
                WHERE inst_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                ''', (inst_id, limit))
            else:
                cursor.execute('''
                SELECT * FROM anchor_warning_logs
                ORDER BY created_at DESC
                LIMIT ?
                ''', (limit,))
            
            logs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return logs
            
        except Exception as e:
            print(f"❌ 获取预警日志失败: {e}")
            return []
    
    def clean_old_warnings(self, days: int = 5) -> int:
        """清理旧预警记录（保留N天）"""
        try:
            cutoff_date = (datetime.now(BEIJING_TZ) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            conn = sqlite3.connect(self.trading_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 删除旧预警
            cursor.execute('''
            DELETE FROM anchor_warning_monitor
            WHERE created_at < ?
            ''', (cutoff_date,))
            
            warning_count = cursor.rowcount
            
            # 删除旧日志
            cursor.execute('''
            DELETE FROM anchor_warning_logs
            WHERE created_at < ?
            ''', (cutoff_date,))
            
            log_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"✅ 清理完成: 删除{warning_count}条预警，{log_count}条日志")
            return warning_count + log_count
            
        except Exception as e:
            print(f"❌ 清理失败: {e}")
            return 0

if __name__ == '__main__':
    monitor = AnchorWarningMonitor()
    result = monitor.scan_warnings()
    
    print("\n" + "="*60)
    print(f"📊 扫描结果: 共{result.get('total_scanned', 0)}个锚点单")
    print(f"⚠️ 活跃预警: {result.get('warnings_count', 0)}个")
    print("="*60)
    
    if result.get('warnings'):
        for warning in result['warnings']:
            print(f"\n{'❗' if warning['warning_level'] == 'critical' else '⚠️'} {warning['inst_id']}")
            print(f"   方向: {warning['pos_side']}")
            print(f"   开仓价: {warning['open_price']:.4f}")
            print(f"   当前价: {warning['current_price']:.4f}")
            print(f"   收益率: {warning['profit_rate']:.2f}%")
            print(f"   预警级别: {warning['warning_level']}")
