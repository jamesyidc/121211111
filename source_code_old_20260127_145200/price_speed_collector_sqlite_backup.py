#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1分钟价格涨跌速监控采集器
- 15秒采集一次价格
- 计算1分钟涨跌幅
- 根据涨跌幅分级预警
"""

import requests
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from collections import deque
import json
import os
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_speed_collector.log'),
        logging.StreamHandler()
    ]
)

# 监控币种配置（27个币种）
COINS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
    'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK', 'CRO', 'DOT', 'AAVE', 'UNI',
    'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
]

# 涨跌速预警阈值配置
ALERT_LEVELS = {
    'general_down': -0.5,      # 一般下跌预警
    'strong_down': -1.0,       # 较强下跌预警
    'very_strong_down': -1.5,  # 很强下跌预警
    'super_strong_down': -2.0, # 超强下跌预警
    'general_up': 0.5,         # 一般上涨预警
    'strong_up': 1.0,          # 较强上涨预警
    'very_strong_up': 1.5,     # 很强上涨预警
    'super_strong_up': 2.0     # 超强上涨预警
}

# 数据库配置
DB_NAME = 'price_speed_data.db'
COLLECT_INTERVAL = 15  # 15秒采集一次
CALC_WINDOW = 60       # 1分钟窗口

class PriceSpeedCollector:
    def __init__(self):
        self.db_name = DB_NAME
        self.price_cache = {coin: deque(maxlen=5) for coin in COINS}  # 保存最近5次数据（75秒）
        self.init_database()
        
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 创建价格历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建涨跌速监控表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_speed_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                current_price REAL NOT NULL,
                previous_price REAL NOT NULL,
                change_percent REAL NOT NULL,
                alert_level TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建最新状态表（每个币种只保留最新记录）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS latest_price_speed (
                symbol TEXT PRIMARY KEY,
                current_price REAL NOT NULL,
                previous_price REAL NOT NULL,
                change_percent REAL NOT NULL,
                alert_level TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_symbol ON price_history(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON price_speed_alerts(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON price_speed_alerts(timestamp)')
        
        conn.commit()
        conn.close()
        logging.info(f"✅ 数据库初始化完成: {self.db_name}")
        
    def get_coin_price(self, symbol):
        """从OKEx获取币种合约价格"""
        try:
            url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT-SWAP"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '0' and data.get('data'):
                price = float(data['data'][0]['last'])
                return price
            else:
                logging.warning(f"⚠️ {symbol}: API返回异常 - {data}")
                return None
                
        except Exception as e:
            logging.error(f"❌ {symbol}: 获取价格失败 - {e}")
            return None
    
    def calculate_change_percent(self, current_price, previous_price):
        """计算涨跌幅百分比"""
        if previous_price == 0:
            return 0
        return ((current_price - previous_price) / previous_price) * 100
    
    def get_alert_level(self, change_percent):
        """根据涨跌幅获取预警级别"""
        if change_percent <= ALERT_LEVELS['super_strong_down']:
            return 'super_strong_down', 'DOWN'
        elif change_percent <= ALERT_LEVELS['very_strong_down']:
            return 'very_strong_down', 'DOWN'
        elif change_percent <= ALERT_LEVELS['strong_down']:
            return 'strong_down', 'DOWN'
        elif change_percent <= ALERT_LEVELS['general_down']:
            return 'general_down', 'DOWN'
        elif change_percent >= ALERT_LEVELS['super_strong_up']:
            return 'super_strong_up', 'UP'
        elif change_percent >= ALERT_LEVELS['very_strong_up']:
            return 'very_strong_up', 'UP'
        elif change_percent >= ALERT_LEVELS['strong_up']:
            return 'strong_up', 'UP'
        elif change_percent >= ALERT_LEVELS['general_up']:
            return 'general_up', 'UP'
        else:
            return 'normal', 'NORMAL'
    
    def save_price_data(self, symbol, price, timestamp):
        """保存价格数据"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO price_history (symbol, price, timestamp)
            VALUES (?, ?, ?)
        ''', (symbol, price, timestamp))
        
        conn.commit()
        conn.close()
        
    def save_alert_data(self, symbol, current_price, previous_price, change_percent, alert_level, alert_type, timestamp):
        """保存预警数据"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 保存到历史表
        cursor.execute('''
            INSERT INTO price_speed_alerts (
                symbol, current_price, previous_price, change_percent, 
                alert_level, alert_type, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, current_price, previous_price, change_percent, alert_level, alert_type, timestamp))
        
        # 更新最新状态表（替换旧记录）
        cursor.execute('''
            INSERT OR REPLACE INTO latest_price_speed (
                symbol, current_price, previous_price, change_percent,
                alert_level, alert_type, timestamp, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (symbol, current_price, previous_price, change_percent, alert_level, alert_type, timestamp))
        
        conn.commit()
        conn.close()
        
    def get_1min_previous_price(self, symbol):
        """获取1分钟前的价格"""
        if len(self.price_cache[symbol]) < 4:  # 需要至少4条记录（60秒前）
            return None
        
        # 返回1分钟前的价格（4个15秒间隔前）
        return self.price_cache[symbol][0]['price']
    
    def collect_data(self):
        """采集数据主循环"""
        logging.info("🚀 1分钟涨跌速监控采集器启动")
        logging.info(f"📊 监控币种: {len(COINS)}个")
        logging.info(f"⏱️  采集间隔: {COLLECT_INTERVAL}秒")
        logging.info(f"📈 计算周期: {CALC_WINDOW}秒（1分钟）")
        logging.info("="*60)
        
        while True:
            try:
                # 使用北京时间
                beijing_tz = pytz.timezone('Asia/Shanghai')
                timestamp = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f"\n⏰ 开始新一轮采集: {timestamp} (北京时间)")
                
                success_count = 0
                alert_count = 0
                
                for symbol in COINS:
                    # 获取当前价格
                    current_price = self.get_coin_price(symbol)
                    if current_price is None:
                        continue
                    
                    # 如果价格为0，重试最多3次
                    retry_attempts = 0
                    max_retries = 3
                    while current_price == 0 and retry_attempts < max_retries:
                        retry_attempts += 1
                        logging.warning(f'⚠️ {symbol}: 价格为0，第{retry_attempts}次重试...')
                        time.sleep(2)  # 等待2秒后重试
                        current_price = self.get_coin_price(symbol)
                        if current_price is None:
                            break
                    
                    # 如果价格仍为0或None，跳过本次采集
                    if current_price is None or current_price == 0:
                        logging.error(f'❌ {symbol}: 价格为0或无效，已重试{retry_attempts}次，跳过本次采集')
                        continue
                    
                    # 保存价格到缓存
                    self.price_cache[symbol].append({
                        'price': current_price,
                        'timestamp': timestamp
                    })
                    
                    # 保存价格历史
                    self.save_price_data(symbol, current_price, timestamp)
                    
                    # 获取1分钟前的价格
                    previous_price = self.get_1min_previous_price(symbol)
                    
                    if previous_price is not None:
                        # 计算涨跌幅
                        change_percent = self.calculate_change_percent(current_price, previous_price)
                        
                        # 获取预警级别
                        alert_level, alert_type = self.get_alert_level(change_percent)
                        
                        # 保存预警数据
                        self.save_alert_data(
                            symbol, current_price, previous_price, 
                            change_percent, alert_level, alert_type, timestamp
                        )
                        
                        # 记录日志
                        if alert_type != 'NORMAL':
                            alert_count += 1
                            logging.info(f"⚠️  {symbol}: {change_percent:+.2f}% ({alert_level}) - ${current_price:.4f}")
                        else:
                            logging.info(f"✅ {symbol}: {change_percent:+.2f}% - ${current_price:.4f}")
                    else:
                        logging.info(f"📊 {symbol}: ${current_price:.4f} (数据积累中...)")
                    
                    success_count += 1
                    time.sleep(0.5)  # 避免请求过快
                
                logging.info(f"✅ 本轮采集完成: {success_count}/{len(COINS)} 成功, {alert_count} 个预警")
                logging.info("="*60)
                
                # 清理7天前的历史数据
                self.cleanup_old_data()
                
                # 等待下一次采集
                time.sleep(COLLECT_INTERVAL)
                
            except Exception as e:
                logging.error(f"❌ 采集过程出错: {e}")
                time.sleep(COLLECT_INTERVAL)
    
    def cleanup_old_data(self):
        """清理7天前的历史数据"""
        try:
            # 使用北京时间
            beijing_tz = pytz.timezone('Asia/Shanghai')
            seven_days_ago = (datetime.now(beijing_tz) - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
            
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # 清理价格历史
            cursor.execute('DELETE FROM price_history WHERE timestamp < ?', (seven_days_ago,))
            
            # 清理预警历史
            cursor.execute('DELETE FROM price_speed_alerts WHERE timestamp < ?', (seven_days_ago,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"清理历史数据失败: {e}")

if __name__ == '__main__':
    collector = PriceSpeedCollector()
    collector.collect_data()
