#!/usr/bin/env python3
"""
位置系统数据采集器
- 采集27个币种在不同时间周期（4h/12h/24h/48h）的价格位置百分比
- 从OKEx API获取K线数据，计算最高价、最低价
- 位置百分比 = (当前价格 - 最低价) / (最高价 - 最低价) * 100%
- 采集间隔: 5分钟
"""

import sqlite3
import requests
import time
import json
from datetime import datetime, timedelta
import logging
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/position_system.log'),
        logging.StreamHandler()
    ]
)

# OKEx API配置
OKEX_BASE_URL = "https://www.okx.com"
OKEX_API_URL = "https://www.okx.com/api/v5"

# 27个币种列表（OKEx永续合约）
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP',
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

# 时间周期配置（小时）
TIME_PERIODS = {
    '4h': 4,
    '12h': 12,
    '24h': 24,
    '48h': 48
}

class PositionSystemCollector:
    def __init__(self, db_path='crypto_data.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建位置系统数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_system (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_time TEXT NOT NULL,
                symbol TEXT NOT NULL,
                current_price REAL NOT NULL,
                
                -- 4小时数据
                high_4h REAL,
                low_4h REAL,
                position_4h REAL,
                
                -- 12小时数据
                high_12h REAL,
                low_12h REAL,
                position_12h REAL,
                
                -- 24小时数据
                high_24h REAL,
                low_24h REAL,
                position_24h REAL,
                
                -- 48小时数据
                high_48h REAL,
                low_48h REAL,
                position_48h REAL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(record_time, symbol)
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_position_time_symbol 
            ON position_system(record_time, symbol)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_position_symbol 
            ON position_system(symbol)
        ''')
        
        # 创建统计数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_system_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_time TEXT NOT NULL UNIQUE,
                count_below_1_4h INTEGER DEFAULT 0,
                count_below_1_12h INTEGER DEFAULT 0,
                count_below_1_24h INTEGER DEFAULT 0,
                count_below_1_48h INTEGER DEFAULT 0,
                total_coins INTEGER DEFAULT 27,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_stats_record_time 
            ON position_system_stats(record_time)
        ''')
        
        conn.commit()
        conn.close()
        logging.info("✅ 数据库初始化完成")
    
    def fetch_kline_data(self, symbol, bar='1H', limit=48):
        """
        获取K线数据
        
        参数:
            symbol: 币种符号（如 BTC-USDT-SWAP）
            bar: K线周期（1H = 1小时）
            limit: 获取数量
        """
        try:
            url = f"{OKEX_API_URL}/market/candles"
            params = {
                'instId': symbol,
                'bar': bar,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('code') == '0' and data.get('data'):
                return data['data']
            else:
                logging.warning(f"⚠️ {symbol} K线数据获取失败: {data.get('msg', 'Unknown error')}")
                return None
            
        except Exception as e:
            logging.error(f"❌ {symbol} K线数据获取异常: {str(e)}")
            return None
    
    def calculate_position_percentage(self, current_price, high_price, low_price):
        """
        计算价格位置百分比
        
        公式: (当前价格 - 最低价) / (最高价 - 最低价) * 100%
        
        返回:
            位置百分比（0-100）
        """
        if high_price == low_price:
            return 50.0  # 如果最高价=最低价，返回50%
        
        position = ((current_price - low_price) / (high_price - low_price)) * 100
        return round(position, 2)
    
    def get_period_high_low(self, kline_data, hours):
        """
        从K线数据中获取指定小时数的最高价和最低价
        
        参数:
            kline_data: K线数据列表
            hours: 小时数
        
        返回:
            (highest, lowest, current_price)
        """
        if not kline_data or len(kline_data) < hours:
            return None, None, None
        
        # 取最近N小时的数据
        recent_data = kline_data[:hours]
        
        # K线数据格式: [timestamp, open, high, low, close, volume, ...]
        highest = max(float(candle[2]) for candle in recent_data)  # high
        lowest = min(float(candle[3]) for candle in recent_data)   # low
        current_price = float(recent_data[0][4])  # 最新收盘价
        
        return highest, lowest, current_price
    
    def collect_symbol_data(self, symbol):
        """采集单个币种的位置数据"""
        try:
            # 获取48小时的K线数据（1小时周期）
            kline_data = self.fetch_kline_data(symbol, bar='1H', limit=50)
            
            if not kline_data:
                return None
            
            # 获取当前价格
            current_price = float(kline_data[0][4])
            
            # 计算各周期的位置数据
            position_data = {
                'symbol': symbol,
                'current_price': current_price,
                'record_time': datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 计算各时间周期的位置百分比
            for period_name, hours in TIME_PERIODS.items():
                high, low, _ = self.get_period_high_low(kline_data, hours)
                
                if high is not None and low is not None:
                    position_pct = self.calculate_position_percentage(current_price, high, low)
                    
                    position_data[f'high_{period_name}'] = high
                    position_data[f'low_{period_name}'] = low
                    position_data[f'position_{period_name}'] = position_pct
                else:
                    position_data[f'high_{period_name}'] = None
                    position_data[f'low_{period_name}'] = None
                    position_data[f'position_{period_name}'] = None
            
            return position_data
            
        except Exception as e:
            logging.error(f"❌ {symbol} 数据采集失败: {str(e)}")
            return None
    
    def save_data(self, position_data_list):
        """保存位置数据到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for data in position_data_list:
                cursor.execute('''
                    INSERT OR REPLACE INTO position_system (
                        record_time, symbol, current_price,
                        high_4h, low_4h, position_4h,
                        high_12h, low_12h, position_12h,
                        high_24h, low_24h, position_24h,
                        high_48h, low_48h, position_48h
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['record_time'], data['symbol'], data['current_price'],
                    data['high_4h'], data['low_4h'], data['position_4h'],
                    data['high_12h'], data['low_12h'], data['position_12h'],
                    data['high_24h'], data['low_24h'], data['position_24h'],
                    data['high_48h'], data['low_48h'], data['position_48h']
                ))
            
            conn.commit()
            conn.close()
            logging.info(f"💾 数据保存成功: {len(position_data_list)} 个币种")
            
        except Exception as e:
            logging.error(f"❌ 数据保存失败: {str(e)}")
    
    def save_stats(self, position_data_list, record_time):
        """
        保存统计数据：计算各周期低于1%的币种数量
        
        参数:
            position_data_list: 位置数据列表
            record_time: 记录时间
        """
        try:
            # 统计各周期低于1%的币种数量
            count_below_1_4h = sum(1 for d in position_data_list if d.get('position_4h') is not None and d['position_4h'] < 1)
            count_below_1_12h = sum(1 for d in position_data_list if d.get('position_12h') is not None and d['position_12h'] < 1)
            count_below_1_24h = sum(1 for d in position_data_list if d.get('position_24h') is not None and d['position_24h'] < 1)
            count_below_1_48h = sum(1 for d in position_data_list if d.get('position_48h') is not None and d['position_48h'] < 1)
            
            total_coins = len(position_data_list)
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO position_system_stats (
                    record_time, count_below_1_4h, count_below_1_12h, 
                    count_below_1_24h, count_below_1_48h, total_coins
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (record_time, count_below_1_4h, count_below_1_12h, 
                  count_below_1_24h, count_below_1_48h, total_coins))
            
            conn.commit()
            conn.close()
            
            logging.info(f"📊 统计数据保存成功:")
            logging.info(f"    4h低于1%: {count_below_1_4h}/{total_coins}")
            logging.info(f"   12h低于1%: {count_below_1_12h}/{total_coins}")
            logging.info(f"   24h低于1%: {count_below_1_24h}/{total_coins}")
            logging.info(f"   48h低于1%: {count_below_1_48h}/{total_coins}")
            
        except Exception as e:
            logging.error(f"❌ 统计数据保存失败: {str(e)}")
    
    def collect_all_data(self):
        """采集所有币种的位置数据"""
        logging.info("📊 开始采集位置系统数据...")
        logging.info(f"📋 币种列表: {len(SYMBOLS)} 个币种")
        
        # 统一的记录时间（所有币种使用同一时间）
        unified_record_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        
        position_data_list = []
        success_count = 0
        
        for i, symbol in enumerate(SYMBOLS, 1):
            logging.info(f"  [{i}/{len(SYMBOLS)}] 采集 {symbol}...")
            
            data = self.collect_symbol_data(symbol)
            if data:
                # 使用统一的记录时间
                data['record_time'] = unified_record_time
                position_data_list.append(data)
                success_count += 1
                
                # 显示位置数据
                logging.info(f"    💰 当前价格: ${data['current_price']}")
                logging.info(f"    📊 位置: 4h={data['position_4h']}% | 12h={data['position_12h']}% | 24h={data['position_24h']}% | 48h={data['position_48h']}%")
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 保存数据
        if position_data_list:
            self.save_data(position_data_list)
            # 保存统计数据
            self.save_stats(position_data_list, unified_record_time)
        
        logging.info(f"✅ 数据采集完成: 成功 {success_count}/{len(SYMBOLS)}")
        
        return success_count
    
    def run_daemon(self, interval=300):
        """
        守护进程模式运行
        
        参数:
            interval: 采集间隔（秒），默认300秒=5分钟
        """
        logging.info(f"🚀 位置系统采集器启动，采集间隔: {interval}秒")
        
        while True:
            try:
                self.collect_all_data()
                logging.info(f"⏳ 等待 {interval} 秒后进行下一次采集...\n")
                time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("⛔ 收到停止信号，退出采集器")
                break
            except Exception as e:
                logging.error(f"❌ 采集循环异常: {str(e)}")
                logging.info(f"⏳ 等待 {interval} 秒后重试...")
                time.sleep(interval)

if __name__ == '__main__':
    collector = PositionSystemCollector()
    
    # 先执行一次立即采集
    collector.collect_all_data()
    
    # 启动守护进程（每5分钟采集一次）
    collector.run_daemon(interval=300)
