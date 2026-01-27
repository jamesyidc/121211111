#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比价系统 - 加密货币价格比较和统计系统
功能：
1. 维护每个币种的最高价/最低价基准
2. 比较最新价格并更新基准
3. 统计每日创新高/创新低
4. 统计3日、7日创新高/创新低次数
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class PriceComparisonSystem:
    def __init__(self, db_path='crypto_data.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. 价格基准表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_baseline (
                symbol TEXT PRIMARY KEY,
                highest_price REAL NOT NULL,
                highest_count INTEGER DEFAULT 0,
                lowest_price REAL NOT NULL,
                lowest_count INTEGER DEFAULT 0,
                last_price REAL,
                highest_ratio REAL,
                lowest_ratio REAL,
                last_update_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. 每日创新高低记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_price_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                record_date DATE NOT NULL,
                record_type TEXT NOT NULL,  -- 'new_high' 或 'new_low'
                old_price REAL,
                new_price REAL,
                record_time TIMESTAMP,
                UNIQUE(symbol, record_date, record_type, record_time)
            )
        ''')
        
        # 3. 每日统计汇总表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                record_date DATE NOT NULL,
                new_high_count INTEGER DEFAULT 0,
                new_low_count INTEGER DEFAULT 0,
                UNIQUE(symbol, record_date)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_records_date ON daily_price_records(record_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_records_symbol ON daily_price_records(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_statistics(record_date)')
        
        conn.commit()
        conn.close()
        print("✅ 比价系统数据库初始化完成")
    
    def import_baseline_data(self, baseline_data: List[Dict]):
        """
        导入初始比价基准数据
        baseline_data格式：
        [
            {
                'symbol': 'BTC',
                'highest_price': 125370.20986,
                'highest_count': 2833,
                'lowest_price': 81359.05775,
                'lowest_count': 738
            },
            ...
        ]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        imported_count = 0
        for data in baseline_data:
            try:
                # 计算初始占比（使用最高价作为当前价格）
                current_price = data['highest_price']
                highest_ratio = (current_price / data['highest_price']) * 100 if data['highest_price'] > 0 else 0
                lowest_ratio = (current_price / data['lowest_price']) * 100 if data['lowest_price'] > 0 else 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO price_baseline 
                    (symbol, highest_price, highest_count, lowest_price, lowest_count, 
                     last_price, highest_ratio, lowest_ratio, last_update_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['symbol'],
                    data['highest_price'],
                    data['highest_count'],
                    data['lowest_price'],
                    data['lowest_count'],
                    current_price,
                    highest_ratio,
                    lowest_ratio,
                    datetime.now()
                ))
                imported_count += 1
            except Exception as e:
                print(f"❌ 导入 {data.get('symbol', '?')} 失败: {e}")
        
        conn.commit()
        conn.close()
        print(f"✅ 成功导入 {imported_count} 个币种的基准数据")
        return imported_count
    
    def compare_and_update(self, coin_data: Dict) -> Dict:
        """
        比价并更新
        coin_data格式：
        {
            'symbol': 'BTC',
            'currentPrice': '92401.66197',
            'updateTime': '2025-12-03 20:25:46'
        }
        
        返回更新结果：
        {
            'symbol': 'BTC',
            'action': 'new_high' / 'high_count_inc' / 'new_low' / 'low_count_inc' / 'no_change',
            'old_value': 125370.20986,
            'new_value': 130000.0,
            'highest_ratio': 98.5,
            'lowest_ratio': 115.3
        }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        symbol = coin_data['symbol']
        current_price = float(coin_data['currentPrice'])
        update_time = coin_data.get('updateTime', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 获取基准数据
        cursor.execute('''
            SELECT highest_price, highest_count, lowest_price, lowest_count
            FROM price_baseline
            WHERE symbol = ?
        ''', (symbol,))
        
        row = cursor.fetchone()
        
        if not row:
            # 如果没有基准数据，忽略
            conn.close()
            return {
                'symbol': symbol,
                'action': 'no_baseline',
                'message': f'{symbol} 没有基准数据'
            }
        
        highest_price, highest_count, lowest_price, lowest_count = row
        
        # 计算占比
        highest_ratio = (current_price / highest_price) * 100 if highest_price > 0 else 0
        lowest_ratio = (current_price / lowest_price) * 100 if lowest_price > 0 else 0
        
        result = {
            'symbol': symbol,
            'current_price': current_price,
            'highest_ratio': round(highest_ratio, 2),
            'lowest_ratio': round(lowest_ratio, 2),
            'action': 'no_change'
        }
        
        record_date = update_time.split(' ')[0]
        
        # 比价逻辑
        if current_price > highest_price:
            # 创新高：更新最高价，重置最高计次为0（重新开始计数）
            result['action'] = 'new_high'
            result['old_value'] = highest_price
            result['new_value'] = current_price
            
            # 更新最高价，重置计次为0
            cursor.execute('''
                UPDATE price_baseline
                SET highest_price = ?, 
                    highest_count = 0,
                    last_price = ?,
                    highest_ratio = ?,
                    lowest_ratio = ?,
                    last_update_time = ?
                WHERE symbol = ?
            ''', (current_price, current_price, highest_ratio, lowest_ratio, update_time, symbol))
            
            # 记录创新高
            cursor.execute('''
                INSERT OR IGNORE INTO daily_price_records
                (symbol, record_date, record_type, old_price, new_price, record_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, record_date, 'new_high', highest_price, current_price, update_time))
            
            # 更新每日统计
            cursor.execute('''
                INSERT INTO daily_statistics (symbol, record_date, new_high_count, new_low_count)
                VALUES (?, ?, 1, 0)
                ON CONFLICT(symbol, record_date) 
                DO UPDATE SET new_high_count = new_high_count + 1
            ''', (symbol, record_date))
            
        elif current_price >= lowest_price:
            # 在最高价和最低价之间：最高计次+1（徘徊次数累计）
            result['action'] = 'high_hover'
            
            cursor.execute('''
                UPDATE price_baseline
                SET highest_count = highest_count + 1,
                    last_price = ?,
                    highest_ratio = ?,
                    lowest_ratio = ?,
                    last_update_time = ?
                WHERE symbol = ?
            ''', (current_price, highest_ratio, lowest_ratio, update_time, symbol))
            
        elif current_price < lowest_price:
            # 创新低：更新最低价，重置最低计次为0（重新开始计数）
            result['action'] = 'new_low'
            result['old_value'] = lowest_price
            result['new_value'] = current_price
            
            # 更新最低价，重置计次为0
            cursor.execute('''
                UPDATE price_baseline
                SET lowest_price = ?,
                    lowest_count = 0,
                    last_price = ?,
                    highest_ratio = ?,
                    lowest_ratio = ?,
                    last_update_time = ?
                WHERE symbol = ?
            ''', (current_price, current_price, highest_ratio, lowest_ratio, update_time, symbol))
            
            # 记录创新低
            cursor.execute('''
                INSERT OR IGNORE INTO daily_price_records
                (symbol, record_date, record_type, old_price, new_price, record_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, record_date, 'new_low', lowest_price, current_price, update_time))
            
            # 更新每日统计
            cursor.execute('''
                INSERT INTO daily_statistics (symbol, record_date, new_high_count, new_low_count)
                VALUES (?, ?, 0, 1)
                ON CONFLICT(symbol, record_date)
                DO UPDATE SET new_low_count = new_low_count + 1
            ''', (symbol, record_date))
        
        else:
            # 最低价计次+1
            result['action'] = 'low_count_inc'
            
            cursor.execute('''
                UPDATE price_baseline
                SET lowest_count = lowest_count + 1,
                    last_price = ?,
                    highest_ratio = ?,
                    lowest_ratio = ?,
                    last_update_time = ?
                WHERE symbol = ?
            ''', (current_price, highest_ratio, lowest_ratio, update_time, symbol))
        
        conn.commit()
        conn.close()
        
        return result
    
    def batch_compare(self, coins_data: List[Dict]) -> List[Dict]:
        """批量比价"""
        results = []
        for coin in coins_data:
            result = self.compare_and_update(coin)
            if result['action'] != 'no_baseline':
                results.append(result)
        return results
    
    def get_baseline_data(self) -> List[Dict]:
        """获取所有基准数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, highest_price, highest_count, lowest_price, lowest_count,
                   last_price, highest_ratio, lowest_ratio, last_update_time
            FROM price_baseline
            ORDER BY display_order
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'symbol': row[0],
                'highest_price': row[1],
                'highest_count': row[2],
                'lowest_price': row[3],
                'lowest_count': row[4],
                'last_price': row[5],
                'highest_ratio': row[6],
                'lowest_ratio': row[7],
                'last_update_time': row[8]
            })
        
        conn.close()
        return results
    
    def get_daily_new_records(self, date: str = None) -> Dict:
        """
        获取每日创新高低记录
        返回格式：
        {
            'new_highs': [...],
            'new_lows': [...],
            'date': '2025-12-03'
        }
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取创新高记录
        cursor.execute('''
            SELECT symbol, old_price, new_price, record_time
            FROM daily_price_records
            WHERE record_date = ? AND record_type = 'new_high'
            ORDER BY record_time DESC
        ''', (date,))
        
        new_highs = []
        for row in cursor.fetchall():
            new_highs.append({
                'symbol': row[0],
                'old_price': row[1],
                'new_price': row[2],
                'record_time': row[3]
            })
        
        # 获取创新低记录
        cursor.execute('''
            SELECT symbol, old_price, new_price, record_time
            FROM daily_price_records
            WHERE record_date = ? AND record_type = 'new_low'
            ORDER BY record_time DESC
        ''', (date,))
        
        new_lows = []
        for row in cursor.fetchall():
            new_lows.append({
                'symbol': row[0],
                'old_price': row[1],
                'new_price': row[2],
                'record_time': row[3]
            })
        
        conn.close()
        
        return {
            'date': date,
            'new_highs': new_highs,
            'new_lows': new_lows,
            'new_high_count': len(new_highs),
            'new_low_count': len(new_lows)
        }
    
    def get_statistics_summary(self, days: int = 1) -> List[Dict]:
        """
        获取统计汇总
        days: 1 (当日), 3 (3日), 7 (7日)
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, 
                   SUM(new_high_count) as total_high,
                   SUM(new_low_count) as total_low
            FROM daily_statistics
            WHERE record_date BETWEEN ? AND ?
            GROUP BY symbol
            ORDER BY symbol
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'symbol': row[0],
                'new_high_count': row[1] or 0,
                'new_low_count': row[2] or 0,
                'days': days
            })
        
        conn.close()
        return results
    
    def get_full_report(self) -> Dict:
        """获取完整报告"""
        baseline = self.get_baseline_data()
        today_records = self.get_daily_new_records()
        stats_1day = self.get_statistics_summary(1)
        stats_3day = self.get_statistics_summary(3)
        stats_7day = self.get_statistics_summary(7)
        
        # 合并统计数据
        stats_by_symbol = {}
        for coin in baseline:
            symbol = coin['symbol']
            stats_by_symbol[symbol] = {
                'symbol': symbol,
                'day1_high': 0,
                'day1_low': 0,
                'day3_high': 0,
                'day3_low': 0,
                'day7_high': 0,
                'day7_low': 0
            }
        
        for stat in stats_1day:
            symbol = stat['symbol']
            if symbol in stats_by_symbol:
                stats_by_symbol[symbol]['day1_high'] = stat['new_high_count']
                stats_by_symbol[symbol]['day1_low'] = stat['new_low_count']
        
        for stat in stats_3day:
            symbol = stat['symbol']
            if symbol in stats_by_symbol:
                stats_by_symbol[symbol]['day3_high'] = stat['new_high_count']
                stats_by_symbol[symbol]['day3_low'] = stat['new_low_count']
        
        for stat in stats_7day:
            symbol = stat['symbol']
            if symbol in stats_by_symbol:
                stats_by_symbol[symbol]['day7_high'] = stat['new_high_count']
                stats_by_symbol[symbol]['day7_low'] = stat['new_low_count']
        
        # 计算汇总
        total_stats = {
            'day1_high_total': sum(s['day1_high'] for s in stats_by_symbol.values()),
            'day1_low_total': sum(s['day1_low'] for s in stats_by_symbol.values()),
            'day3_high_total': sum(s['day3_high'] for s in stats_by_symbol.values()),
            'day3_low_total': sum(s['day3_low'] for s in stats_by_symbol.values()),
            'day7_high_total': sum(s['day7_high'] for s in stats_by_symbol.values()),
            'day7_low_total': sum(s['day7_low'] for s in stats_by_symbol.values())
        }
        
        return {
            'baseline': baseline,
            'today_records': today_records,
            'statistics': list(stats_by_symbol.values()),
            'total': total_stats,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


if __name__ == '__main__':
    # 测试
    system = PriceComparisonSystem()
    print("✅ 比价系统初始化完成")
