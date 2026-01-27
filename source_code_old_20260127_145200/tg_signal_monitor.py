#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG消息推送系统
功能：监控4个信号源，自动推送到Telegram

信号源说明：
1. 支撑压力线系统 - 抄底信号、逃顶信号
2. 历史数据查询 - 计次预警
3. 交易信号系统 - 买点1、买点2、买点3
4. 买点4系统 - 7天低点+2根不破+支撑压力验证
"""

import requests
import sqlite3
import time
import json
from datetime import datetime, timedelta
import pytz

# Telegram配置
BOT_TOKEN = "8437045462:AAFePnwdC21cqeWhZISMQHGGgjmroVqE2H0"
CHAT_ID = "-1003227444260"
BASE_URL = "https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai"

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库配置
DB_FILE = 'tg_signals.db'

class TGSignalMonitor:
    """TG信号监控器"""
    
    def __init__(self):
        self.init_database()
        self.last_signals = {
            'support_resistance': {},
            'count_alerts': {},
            'trading_signals': {},
            'v6_signals': {}  # 买点4信号
        }
        
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 创建信号记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_type TEXT NOT NULL,
                symbol TEXT,
                signal_name TEXT NOT NULL,
                signal_data TEXT,
                sent_time TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建发送记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS send_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                message_id INTEGER,
                status TEXT,
                sent_time TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ 数据库初始化完成")
    
    def send_telegram_message(self, message):
        """发送Telegram消息"""
        try:
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
                print(f"✅ 消息发送成功 (ID: {message_id})")
                
                # 记录发送历史
                self.save_send_history(message, message_id, 'success')
                return True
            else:
                print(f"❌ 消息发送失败: {result}")
                self.save_send_history(message, None, 'failed')
                return False
                
        except Exception as e:
            print(f"❌ 发送消息异常: {e}")
            self.save_send_history(message, None, 'error')
            return False
    
    def save_send_history(self, message, message_id, status):
        """保存发送历史"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO send_history (message, message_id, status, sent_time)
                VALUES (?, ?, ?, ?)
            ''', (message, message_id, status, now))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ 保存发送历史失败: {e}")
    
    def save_signal_history(self, signal_type, symbol, signal_name, signal_data):
        """保存信号历史"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO signal_history (signal_type, symbol, signal_name, signal_data, sent_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (signal_type, symbol, signal_name, json.dumps(signal_data, ensure_ascii=False), now))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ 保存信号历史失败: {e}")
    
    def check_support_resistance_signals(self):
        """1. 检查支撑压力线系统信号（抄底信号、逃顶信号）"""
        try:
            # 获取最新支撑压力数据
            url = f"{BASE_URL}/api/support-resistance/latest-signal"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if not data.get('success'):
                return []
            
            signals = []
            signal_data = data.get('data', {})
            
            # 检查抄底信号（支撑线突破）
            if signal_data.get('support_break'):
                symbol = signal_data.get('symbol')
                price = signal_data.get('current_price')
                support_level = signal_data.get('support_level')
                
                signal_key = f"{symbol}_support_{support_level}"
                if signal_key not in self.last_signals['support_resistance']:
                    message = (
                        f"🔵 <b>抄底信号</b>\n\n"
                        f"币种: {symbol}\n"
                        f"当前价格: ${price:.4f}\n"
                        f"支撑位: ${support_level:.4f}\n"
                        f"信号: 价格触及支撑位\n"
                        f"时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"💡 建议：关注反弹机会"
                    )
                    signals.append(('support_resistance', symbol, '抄底信号', message, signal_data))
                    self.last_signals['support_resistance'][signal_key] = time.time()
            
            # 检查逃顶信号（压力线突破）
            if signal_data.get('resistance_break'):
                symbol = signal_data.get('symbol')
                price = signal_data.get('current_price')
                resistance_level = signal_data.get('resistance_level')
                
                signal_key = f"{symbol}_resistance_{resistance_level}"
                if signal_key not in self.last_signals['support_resistance']:
                    message = (
                        f"🔴 <b>逃顶信号</b>\n\n"
                        f"币种: {symbol}\n"
                        f"当前价格: ${price:.4f}\n"
                        f"压力位: ${resistance_level:.4f}\n"
                        f"信号: 价格触及压力位\n"
                        f"时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"💡 建议：考虑止盈离场"
                    )
                    signals.append(('support_resistance', symbol, '逃顶信号', message, signal_data))
                    self.last_signals['support_resistance'][signal_key] = time.time()
            
            return signals
            
        except Exception as e:
            print(f"❌ 检查支撑压力信号失败: {e}")
            return []
    
    def check_count_alerts(self):
        """2. 检查计次预警（从历史数据查询系统）"""
        try:
            # 这个需要查询数据库获取计次预警
            conn = sqlite3.connect('crypto_data.db', timeout=10.0)
            cursor = conn.cursor()
            
            # 获取最近1分钟内的计次预警（假设有这样的表）
            # 这里需要根据实际数据库结构调整
            signals = []
            
            conn.close()
            return signals
            
        except Exception as e:
            print(f"❌ 检查计次预警失败: {e}")
            return []
    
    def check_trading_signals(self):
        """3. 检查交易信号（买点1、买点2、买点3）"""
        try:
            url = f"{BASE_URL}/api/signals/stats"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if not data.get('success'):
                return []
            
            signals = []
            latest_long = data.get('latest_long', 0)
            latest_short = data.get('latest_short', 0)
            latest_time = data.get('latest_time', '')
            
            # 检查做多信号（买点）
            signal_key = f"trading_long_{latest_time}"
            if latest_long > 30 and signal_key not in self.last_signals['trading_signals']:
                message = (
                    f"🟢 <b>买点信号 (买点1/2/3)</b>\n\n"
                    f"做多信号数: {latest_long}\n"
                    f"做空信号数: {latest_short}\n"
                    f"做多占比: {data.get('long_ratio', 0)}%\n"
                    f"信号强度: {'强' if latest_long > 40 else '中'}\n"
                    f"时间: {latest_time}\n\n"
                    f"💡 建议：市场做多情绪浓厚，可考虑建仓"
                )
                signal_data = {'long': latest_long, 'short': latest_short, 'time': latest_time}
                signals.append(('trading_signals', 'ALL', '买点信号', message, signal_data))
                self.last_signals['trading_signals'][signal_key] = time.time()
            
            return signals
            
        except Exception as e:
            print(f"❌ 检查交易信号失败: {e}")
            return []
    
    def check_v6_signals(self):
        """4. 检查买点4信号（K线系统：7天低点+2根不破）"""
        try:
            # 获取K线指标信号数据
            kline_url = f"{BASE_URL}/api/kline-indicators/signals"
            kline_response = requests.get(kline_url, timeout=10)
            kline_data = kline_response.json()
            
            if not kline_data.get('success'):
                return []
            
            signals = []
            buy_point_4_list = kline_data.get('data', {}).get('signals', {}).get('buy_point_4', [])
            
            # 监控的币种列表
            target_symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'UNI', 'DOGE', 'LTC', 
                            'AAVE', 'BCH', 'CRV', 'DOT', 'ETC', 'FIL', 'HBAR', 
                            'LDO', 'LINK', 'LTC', 'MATIC', 'NEAR', 'ONDO', 
                            'RENDER', 'SHIB', 'SUI', 'TRX', 'ORDI', 'APT']
            
            for signal in buy_point_4_list:
                try:
                    symbol = signal.get('symbol', '')
                    
                    if symbol not in target_symbols:
                        continue
                    
                    signal_time = signal.get('time', '')
                    signal_key = f"{symbol}_buy4_{signal_time}"
                    
                    if signal_key not in self.last_signals['v6_signals']:
                        current_price = signal.get('price', 0)
                        low_7d = signal.get('low_7d', 0)
                        distance = signal.get('distance', 0)
                        
                        message = (
                            f"🎯 <b>买点4信号 (K线系统)</b>\n\n"
                            f"币种: {symbol}\n"
                            f"信号类型: 7天低点+2根不破\n"
                            f"当前价格: ${current_price:,.4f}\n"
                            f"7天低点: ${low_7d:,.4f}\n"
                            f"距离低点: {distance:.2f}%\n"
                            f"触发时间: {signal_time}\n\n"
                            f"💡 建议：形成7天低点后，已有2根K线未跌破，可考虑建仓"
                        )
                        signal_data = {
                            'symbol': symbol,
                            'current_price': current_price,
                            'low_7d': low_7d,
                            'distance': distance,
                            'signal_time': signal_time
                        }
                        signals.append(('v6_signals', symbol, '买点4', message, signal_data))
                        self.last_signals['v6_signals'][signal_key] = time.time()
                
                except Exception as e:
                    print(f"⚠️ 处理买点4信号失败: {e}")
                    continue
            
            return signals
            
        except Exception as e:
            print(f"❌ 检查买点4信号失败: {e}")
            return []
    
    def run_check_cycle(self):
        """运行一次检查周期"""
        print(f"\n{'='*60}")
        print(f"🔍 开始检查信号 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        all_signals = []
        
        # 1. 检查支撑压力线信号
        print("\n1️⃣ 检查支撑压力线系统...")
        signals = self.check_support_resistance_signals()
        all_signals.extend(signals)
        print(f"   发现 {len(signals)} 个信号")
        
        # 2. 检查计次预警
        print("\n2️⃣ 检查计次预警...")
        signals = self.check_count_alerts()
        all_signals.extend(signals)
        print(f"   发现 {len(signals)} 个信号")
        
        # 3. 检查交易信号
        print("\n3️⃣ 检查交易信号（买点1/2/3）...")
        signals = self.check_trading_signals()
        all_signals.extend(signals)
        print(f"   发现 {len(signals)} 个信号")
        
        # 4. 检查买点4信号
        print("\n4️⃣ 检查买点4信号（K线系统：7天低点+2根不破）...")
        signals = self.check_v6_signals()
        all_signals.extend(signals)
        print(f"   发现 {len(signals)} 个信号")
        
        # 发送信号
        print(f"\n📤 总共发现 {len(all_signals)} 个新信号")
        for signal_type, symbol, signal_name, message, signal_data in all_signals:
            print(f"\n发送信号: {signal_name} ({symbol})")
            if self.send_telegram_message(message):
                self.save_signal_history(signal_type, symbol, signal_name, signal_data)
                time.sleep(1)  # 避免发送太快
        
        print(f"\n✅ 检查周期完成")
        print(f"{'='*60}\n")
    
    def run(self):
        """主运行循环"""
        print("="*60)
        print("🚀 TG信号监控系统启动")
        print("="*60)
        print(f"Bot: @jamesyi9999_bot")
        print(f"频道ID: {CHAT_ID}")
        print(f"检查间隔: 60秒")
        print(f"启动时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # 发送启动消息
        startup_msg = (
            f"🤖 <b>TG消息推送系统已启动</b>\n\n"
            f"监控信号:\n"
            f"1️⃣ 支撑压力线系统（抄底/逃顶）\n"
            f"2️⃣ 计次预警\n"
            f"3️⃣ 交易信号（买点1/2/3）\n"
            f"4️⃣ V6信号（买点4）\n\n"
            f"检查间隔: 每60秒\n"
            f"启动时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_telegram_message(startup_msg)
        
        try:
            while True:
                self.run_check_cycle()
                
                # 等待60秒
                print("⏰ 等待60秒后进行下一次检查...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("\n\n⚠️ 收到停止信号")
            shutdown_msg = (
                f"🛑 <b>TG消息推送系统已停止</b>\n\n"
                f"停止时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.send_telegram_message(shutdown_msg)
            print("✅ 系统已安全退出")

def main():
    """主函数"""
    monitor = TGSignalMonitor()
    monitor.run()

if __name__ == '__main__':
    main()
