#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点系统24小时持续监控守护进程
功能：独立于浏览器运行，持续监控锚点单状态，收集分页活跃数据
作者：系统自动生成
日期：2026-01-14
"""

import time
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
import sys
import signal

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库路径
ANCHOR_DB = '/home/user/webapp/databases/anchor_system.db'

# 全局标志
running = True

def signal_handler(sig, frame):
    """处理终止信号"""
    global running
    print('\n🛑 收到终止信号，正在优雅退出...')
    running = False

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class AnchorDaemonMonitor:
    """锚点守护进程监控器"""
    
    def __init__(self):
        self.anchor_db = ANCHOR_DB
        self.check_interval = 60  # 每60秒检查一次
        self.init_monitor_table()
    
    def init_monitor_table(self):
        """初始化监控数据表"""
        try:
            conn = sqlite3.connect(self.anchor_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 创建分页活跃监控表（12小时分页统计）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS anchor_page_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_bucket TEXT NOT NULL,
                active_count INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(time_bucket)
            )
            ''')
            
            # 创建守护进程心跳表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS daemon_heartbeat (
                id INTEGER PRIMARY KEY,
                daemon_name TEXT NOT NULL,
                last_beat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'running'
            )
            ''')
            
            conn.commit()
            conn.close()
            
            print("✅ 监控数据表初始化完成")
            
        except Exception as e:
            print(f"❌ 数据表初始化失败: {e}")
    
    def get_active_anchors(self) -> List[Dict]:
        """获取所有活跃锚点单"""
        try:
            conn = sqlite3.connect(self.anchor_db, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT 
                inst_id,
                pos_side,
                pos_size,
                avg_price,
                mark_price,
                upl_ratio,
                profit_rate,
                created_at
            FROM anchor_monitors
            ORDER BY created_at DESC
            LIMIT 100
            ''')
            
            anchors = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return anchors
            
        except Exception as e:
            print(f"❌ 获取锚点单失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def calculate_time_bucket(self, timestamp=None):
        """计算当前时间所属的分页（12小时为单位）"""
        if timestamp is None:
            now = datetime.now(BEIJING_TZ)
        else:
            now = timestamp
        
        # 每12小时为一个分页
        # 0:00-11:59 为第一页，12:00-23:59为第二页
        hour = now.hour
        if hour < 12:
            page_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            page_start = now.replace(hour=12, minute=0, second=0, microsecond=0)
        
        return page_start.strftime('%Y-%m-%d %H:%M:%S')
    
    def update_page_activity(self, active_count: int):
        """更新分页活跃统计"""
        try:
            time_bucket = self.calculate_time_bucket()
            
            conn = sqlite3.connect(self.anchor_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 使用 INSERT OR REPLACE 更新统计
            cursor.execute('''
            INSERT OR REPLACE INTO anchor_page_activity 
            (time_bucket, active_count, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (time_bucket, active_count))
            
            conn.commit()
            conn.close()
            
            print(f"📊 分页活跃度更新: 时间段={time_bucket}, 活跃数={active_count}")
            
        except Exception as e:
            print(f"❌ 更新分页活跃度失败: {e}")
    
    def update_heartbeat(self):
        """更新守护进程心跳"""
        try:
            conn = sqlite3.connect(self.anchor_db, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO daemon_heartbeat 
            (id, daemon_name, last_beat, status)
            VALUES (1, 'anchor-monitor-daemon', CURRENT_TIMESTAMP, 'running')
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ 更新心跳失败: {e}")
    
    def cleanup_old_data(self, days=7):
        """清理旧数据（保留N天）"""
        try:
            cutoff_date = (datetime.now(BEIJING_TZ) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            conn = sqlite3.connect(self.anchor_db, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute('''
            DELETE FROM anchor_page_activity
            WHERE timestamp < ?
            ''', (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                print(f"🗑️ 清理了{deleted_count}条旧的活跃度记录")
            
        except Exception as e:
            print(f"❌ 清理旧数据失败: {e}")
    
    def run(self):
        """主循环 - 持续监控"""
        global running
        
        print("="*70)
        print("🚀 锚点监控守护进程启动")
        print("="*70)
        print(f"📍 数据库: {self.anchor_db}")
        print(f"⏰ 检查间隔: {self.check_interval}秒")
        print(f"🕐 启动时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        print("\n🔄 开始持续监控...\n")
        
        cycle_count = 0
        
        while running:
            try:
                cycle_count += 1
                current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"\n{'='*70}")
                print(f"🔍 第 {cycle_count} 次检查 - {current_time}")
                print(f"{'='*70}")
                
                # 1. 获取活跃锚点单
                active_anchors = self.get_active_anchors()
                active_count = len(active_anchors)
                
                print(f"📊 活跃锚点单: {active_count} 个")
                
                # 显示前5个锚点单
                if active_anchors:
                    print("\n最近的锚点单:")
                    for i, anchor in enumerate(active_anchors[:5], 1):
                        print(f"  {i}. {anchor['inst_id']} {anchor['pos_side']} "
                              f"均价:{anchor['avg_price']:.4f} "
                              f"持仓:{anchor['pos_size']:.3f} "
                              f"收益率:{anchor['profit_rate']:.2f}%")
                
                # 2. 更新分页活跃统计
                self.update_page_activity(active_count)
                
                # 3. 更新守护进程心跳
                self.update_heartbeat()
                
                # 4. 每隔100次循环清理一次旧数据
                if cycle_count % 100 == 0:
                    self.cleanup_old_data(days=7)
                
                print(f"\n✅ 检查完成，等待 {self.check_interval} 秒...")
                
                # 等待下次检查（可被中断）
                for _ in range(self.check_interval):
                    if not running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                print(f"\n❌ 监控循环异常: {e}")
                print("⏳ 等待10秒后重试...")
                time.sleep(10)
        
        # 优雅退出
        print("\n" + "="*70)
        print("👋 守护进程已停止")
        print(f"📊 总共运行了 {cycle_count} 个周期")
        print(f"🕐 停止时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

def main():
    """主函数"""
    try:
        monitor = AnchorDaemonMonitor()
        monitor.run()
    except Exception as e:
        print(f"\n❌ 守护进程启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
