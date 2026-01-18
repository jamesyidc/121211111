#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计次监控系统
功能：每15分钟采集一次计次数据，间隔3个15分钟（45分钟）如果计次增加>=2，则发送TG预警
"""

import sqlite3
import time
import requests
import json
from datetime import datetime, timedelta
import pytz
import os

# Telegram配置
BOT_TOKEN = "8437045462:AAFePnwdC21cqeWhZISMQHGGgjmroVqE2H0"
CHAT_ID = "-1003227444260"

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 监控数据库
MONITOR_DB = 'count_monitor.db'
# 源数据库
SOURCE_DB = 'crypto_data.db'

class CountMonitor:
    """计次监控器"""
    
    def __init__(self):
        self.init_database()
        print(f"✅ 计次监控系统初始化完成")
        print(f"📊 监控频率: 每15分钟")
        print(f"🔔 预警条件: 3个15分钟内计次增加>=2")
        print(f"📱 TG群组: {CHAT_ID}")
        
    def init_database(self):
        """初始化监控数据库"""
        conn = sqlite3.connect(MONITOR_DB)
        cursor = conn.cursor()
        
        # 创建计次采样表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS count_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_time TEXT NOT NULL,
                count_value INTEGER NOT NULL,
                snapshot_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建预警记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS count_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_time TEXT NOT NULL,
                count_before INTEGER NOT NULL,
                count_after INTEGER NOT NULL,
                count_diff INTEGER NOT NULL,
                message TEXT,
                sent_status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def get_latest_count(self):
        """从crypto_data.db获取最新的计次数据"""
        try:
            if not os.path.exists(SOURCE_DB):
                print(f"❌ 数据库文件不存在: {SOURCE_DB}")
                return None, None
                
            conn = sqlite3.connect(SOURCE_DB, timeout=10.0)
            cursor = conn.cursor()
            
            # 查询最新的计次数据
            cursor.execute("""
                SELECT snapshot_time, count
                FROM crypto_snapshots
                ORDER BY snapshot_time DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                snapshot_time, count_value = result
                print(f"📊 获取最新计次: {count_value} (时间: {snapshot_time})")
                return snapshot_time, count_value
            else:
                print(f"⚠️ 未找到计次数据")
                return None, None
                
        except Exception as e:
            print(f"❌ 获取计次数据失败: {e}")
            return None, None
    
    def save_sample(self, snapshot_time, count_value):
        """保存采样数据"""
        try:
            conn = sqlite3.connect(MONITOR_DB)
            cursor = conn.cursor()
            
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO count_samples (sample_time, count_value, snapshot_time)
                VALUES (?, ?, ?)
            ''', (now, count_value, snapshot_time))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 采样数据已保存: 计次={count_value}, 时间={now}")
            
        except Exception as e:
            print(f"❌ 保存采样数据失败: {e}")
    
    def check_alert_condition(self):
        """检查预警条件：3个15分钟内计次增加>=2"""
        try:
            conn = sqlite3.connect(MONITOR_DB)
            cursor = conn.cursor()
            
            # 获取最近4条采样数据（当前+前3次）
            cursor.execute('''
                SELECT id, sample_time, count_value
                FROM count_samples
                ORDER BY id DESC
                LIMIT 4
            ''')
            
            samples = cursor.fetchall()
            conn.close()
            
            if len(samples) < 4:
                print(f"ℹ️ 采样数据不足（当前{len(samples)}条，需要4条），暂不检查预警")
                return False
            
            # samples[0]是最新的，samples[3]是3个15分钟前的
            current_id, current_time, current_count = samples[0]
            before_id, before_time, before_count = samples[3]
            
            count_diff = current_count - before_count
            
            print(f"\n{'='*80}")
            print(f"📊 预警条件检查")
            print(f"{'='*80}")
            print(f"45分钟前（3个15分钟前）: 计次={before_count}, 时间={before_time}")
            print(f"当前: 计次={current_count}, 时间={current_time}")
            print(f"差值: {count_diff}")
            print(f"预警条件: 差值 >= 2")
            
            if count_diff >= 2:
                print(f"🔔 触发预警! 计次增加 {count_diff}")
                self.send_alert(before_time, current_time, before_count, current_count, count_diff)
                return True
            else:
                print(f"✅ 未触发预警（差值={count_diff}）")
                return False
                
        except Exception as e:
            print(f"❌ 检查预警条件失败: {e}")
            return False
    
    def send_alert(self, before_time, current_time, before_count, current_count, count_diff):
        """发送TG预警消息"""
        try:
            message = (
                f"🔔 <b>计次预警</b>\n\n"
                f"⏰ 时间范围: 45分钟\n"
                f"📊 45分钟前: {before_count}\n"
                f"📊 当前计次: {current_count}\n"
                f"📈 增加数量: +{count_diff}\n\n"
                f"⚠️ <b>预警原因:</b> 3个15分钟内计次增加≥2\n\n"
                f"🕐 开始时间: {before_time}\n"
                f"🕐 结束时间: {current_time}\n\n"
                f"💡 建议: 关注市场波动，注意风险"
            )
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                message_id = result['result']['message_id']
                print(f"✅ TG消息发送成功 (ID: {message_id})")
                
                # 保存预警记录
                self.save_alert_record(before_time, current_time, before_count, current_count, count_diff, message, 'success')
                return True
            else:
                print(f"❌ TG消息发送失败: {result}")
                self.save_alert_record(before_time, current_time, before_count, current_count, count_diff, message, 'failed')
                return False
                
        except Exception as e:
            print(f"❌ 发送TG消息异常: {e}")
            self.save_alert_record(before_time, current_time, before_count, current_count, count_diff, message, 'error')
            return False
    
    def save_alert_record(self, before_time, current_time, before_count, current_count, count_diff, message, status):
        """保存预警记录"""
        try:
            conn = sqlite3.connect(MONITOR_DB)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO count_alerts 
                (alert_time, count_before, count_after, count_diff, message, sent_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (current_time, before_count, current_count, count_diff, message, status))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 预警记录已保存: 差值={count_diff}, 状态={status}")
            
        except Exception as e:
            print(f"❌ 保存预警记录失败: {e}")
    
    def run_once(self):
        """执行一次监控"""
        print(f"\n{'='*80}")
        print(f"🔄 开始计次监控 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        # 1. 获取最新计次
        snapshot_time, count_value = self.get_latest_count()
        
        if snapshot_time is None or count_value is None:
            print(f"⚠️ 无法获取计次数据，跳过本次监控")
            return
        
        # 2. 保存采样
        self.save_sample(snapshot_time, count_value)
        
        # 3. 检查预警条件
        self.check_alert_condition()
        
        print(f"\n✅ 本次监控完成\n")
    
    def run(self):
        """持续运行监控"""
        print(f"🚀 计次监控系统启动")
        print(f"📍 每15分钟执行一次监控")
        print(f"🔔 预警条件: 3个15分钟（45分钟）内计次增加>=2")
        print(f"{'='*80}\n")
        
        while True:
            try:
                self.run_once()
                
                # 等待15分钟
                sleep_seconds = 15 * 60
                next_run = datetime.now(BEIJING_TZ) + timedelta(seconds=sleep_seconds)
                print(f"⏰ 下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"💤 休眠 {sleep_seconds} 秒...\n")
                
                time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                print(f"\n⛔ 收到中断信号，停止监控")
                break
            except Exception as e:
                print(f"❌ 监控异常: {e}")
                print(f"⏰ 60秒后重试...\n")
                time.sleep(60)

def main():
    """主函数"""
    monitor = CountMonitor()
    monitor.run()

if __name__ == '__main__':
    main()
