#!/usr/bin/env python3
"""
加密货币数据库模块
用于存储和查询历史加密货币数据
"""

import sqlite3
from datetime import datetime
import json
from typing import List, Dict, Optional

class CryptoDatabase:
    def __init__(self, db_path='crypto_data.db'):
        """初始化数据库连接"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建主表：存储每个时间点的完整数据快照
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_time TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                rush_up INTEGER,
                rush_down INTEGER,
                diff INTEGER,
                count INTEGER,
                ratio REAL,
                status TEXT,
                green_count INTEGER,
                percentage TEXT,
                filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_time)
            )
        ''')
        
        # 创建信号监控数据表：存储做空/做多信号的历史数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_time TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                short_value INTEGER,
                short_change INTEGER,
                long_value INTEGER,
                long_change INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_time)
            )
        ''')
        
        # 创建恐慌清洗数据表：存储恐慌清洗指标的历史数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS panic_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_time TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                panic_indicator TEXT,
                trend_rating TEXT,
                market_zone TEXT,
                liquidation_24h_count TEXT,
                liquidation_24h_amount TEXT,
                total_position TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_time)
            )
        ''')
        
        # 创建币种数据表：存储每个币种在每个时间点的详细数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_coin_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                snapshot_time TEXT NOT NULL,
                symbol TEXT NOT NULL,
                index_order INTEGER DEFAULT 0,
                change REAL,
                rush_up INTEGER,
                rush_down INTEGER,
                update_time TEXT,
                high_price REAL,
                high_time TEXT,
                decline REAL,
                change_24h REAL,
                rank INTEGER,
                current_price REAL,
                ratio1 TEXT,
                ratio2 TEXT,
                priority_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES crypto_snapshots(id),
                UNIQUE(snapshot_time, symbol)
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshot_time 
            ON crypto_snapshots(snapshot_time)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshot_date 
            ON crypto_snapshots(snapshot_date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_coin_snapshot_time 
            ON crypto_coin_data(snapshot_time)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_coin_symbol 
            ON crypto_coin_data(symbol)
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ 数据库初始化完成: {self.db_path}")
    
    def save_snapshot(self, data: List[Dict], stats: Dict, 
                     snapshot_time: str, filename: str = '') -> int:
        """
        保存一个完整的数据快照
        
        Args:
            data: 币种数据列表
            stats: 统计数据
            snapshot_time: 快照时间 (格式: YYYY-MM-DD HH:MM:SS)
            filename: 源文件名
            
        Returns:
            snapshot_id: 快照ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 提取日期部分
            snapshot_date = snapshot_time.split()[0]
            
            # 保存快照统计数据
            cursor.execute('''
                INSERT OR REPLACE INTO crypto_snapshots 
                (snapshot_time, snapshot_date, rush_up, rush_down, diff, count, 
                 ratio, status, green_count, percentage, filename)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_time,
                snapshot_date,
                int(stats.get('rushUp', 0)),
                int(stats.get('rushDown', 0)),
                int(stats.get('diff', 0)),
                int(stats.get('count', 0)),
                float(stats.get('ratio', 0)),
                stats.get('status', ''),
                int(stats.get('greenCount', 0)),
                stats.get('percentage', ''),
                filename
            ))
            
            # 获取快照ID
            snapshot_id = cursor.lastrowid
            
            # 保存每个币种的数据，记录原始顺序
            for idx, coin in enumerate(data):
                cursor.execute('''
                    INSERT OR REPLACE INTO crypto_coin_data
                    (snapshot_id, snapshot_time, symbol, index_order, change, rush_up, rush_down,
                     update_time, high_price, high_time, decline, change_24h,
                     rank, current_price, ratio1, ratio2, priority_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    snapshot_id,
                    snapshot_time,
                    coin.get('symbol', ''),
                    idx,  # 记录原始顺序
                    float(coin.get('change', 0)),
                    int(coin.get('rushUp', 0)),
                    int(coin.get('rushDown', 0)),
                    coin.get('updateTime', ''),
                    float(coin.get('highPrice', 0)),
                    coin.get('highTime', ''),
                    float(coin.get('decline', 0)),
                    float(coin.get('change24h', 0)),
                    int(coin.get('rank', 0)),
                    float(coin.get('currentPrice', 0)),
                    coin.get('ratio1', ''),
                    coin.get('ratio2', ''),
                    coin.get('priorityLevel', '-')
                ))
            
            conn.commit()
            print(f"✅ 数据快照已保存: {snapshot_time} (ID: {snapshot_id}, {len(data)}个币种)")
            return snapshot_id
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 保存快照失败: {e}")
            raise
        finally:
            conn.close()
    
    def get_snapshot_by_time(self, snapshot_time: str) -> Optional[Dict]:
        """根据时间查询快照数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查询快照统计数据
            cursor.execute('''
                SELECT * FROM crypto_snapshots WHERE snapshot_time = ?
            ''', (snapshot_time,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 构建统计数据
            stats = {
                'id': row[0],
                'snapshot_time': row[1],
                'snapshot_date': row[2],
                'rushUp': str(row[3]),
                'rushDown': str(row[4]),
                'diff': str(row[5]),
                'count': str(row[6]),
                'ratio': str(row[7]),
                'status': row[8],
                'greenCount': str(row[9]),
                'percentage': row[10],
                'filename': row[11]
            }
            
            # 查询币种数据（按ID排序保持原始顺序）
            cursor.execute('''
                SELECT * FROM crypto_coin_data 
                WHERE snapshot_time = ?
                ORDER BY index_order, id
            ''', (snapshot_time,))
            
            coins = []
            for coin_row in cursor.fetchall():
                coins.append({
                    'symbol': coin_row[3],
                    'change': str(coin_row[4]),
                    'rushUp': str(coin_row[5]),
                    'rushDown': str(coin_row[6]),
                    'updateTime': coin_row[7],
                    'highPrice': str(coin_row[8]),
                    'highTime': coin_row[9],
                    'decline': str(coin_row[10]),
                    'change24h': str(coin_row[11]),
                    'rank': str(coin_row[12]),
                    'currentPrice': str(coin_row[13]),
                    'ratio1': coin_row[14],
                    'ratio2': coin_row[15],
                    'priorityLevel': coin_row[16]
                })
            
            return {
                'stats': stats,
                'data': coins
            }
            
        finally:
            conn.close()
    
    def get_snapshots_by_date(self, date: str) -> List[Dict]:
        """查询某一天的所有快照"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT snapshot_time, rush_up, rush_down, diff, count
                FROM crypto_snapshots
                WHERE snapshot_date = ?
                ORDER BY snapshot_time
            ''', (date,))
            
            snapshots = []
            for row in cursor.fetchall():
                snapshots.append({
                    'snapshot_time': row[0],
                    'rush_up': row[1],
                    'rush_down': row[2],
                    'diff': row[3],
                    'count': row[4]
                })
            
            return snapshots
            
        finally:
            conn.close()
    
    def get_coin_history(self, symbol: str, start_date: str = None, 
                        end_date: str = None) -> List[Dict]:
        """查询某个币种的历史数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = '''
                SELECT snapshot_time, current_price, change, change_24h,
                       ratio1, ratio2, priority_level
                FROM crypto_coin_data
                WHERE symbol = ?
            '''
            params = [symbol]
            
            if start_date:
                query += ' AND snapshot_time >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND snapshot_time <= ?'
                params.append(end_date)
            
            query += ' ORDER BY snapshot_time'
            
            cursor.execute(query, params)
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'snapshot_time': row[0],
                    'current_price': row[1],
                    'change': row[2],
                    'change_24h': row[3],
                    'ratio1': row[4],
                    'ratio2': row[5],
                    'priority_level': row[6]
                })
            
            return history
            
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 总快照数
            cursor.execute('SELECT COUNT(*) FROM crypto_snapshots')
            total_snapshots = cursor.fetchone()[0]
            
            # 日期范围
            cursor.execute('''
                SELECT MIN(snapshot_time), MAX(snapshot_time)
                FROM crypto_snapshots
            ''')
            date_range = cursor.fetchone()
            
            # 币种数量
            cursor.execute('SELECT COUNT(DISTINCT symbol) FROM crypto_coin_data')
            total_coins = cursor.fetchone()[0]
            
            # 总记录数
            cursor.execute('SELECT COUNT(*) FROM crypto_coin_data')
            total_records = cursor.fetchone()[0]
            
            return {
                'total_snapshots': total_snapshots,
                'start_time': date_range[0],
                'end_time': date_range[1],
                'total_coins': total_coins,
                'total_records': total_records
            }
            
        finally:
            conn.close()
    
    def save_signal_data(self, signal_data: Dict) -> bool:
        """
        保存信号监控数据
        
        Args:
            signal_data: 信号数据字典，包含 short, short_change, long, long_change, update_time
            
        Returns:
            bool: 保存成功返回 True，失败返回 False
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            snapshot_time = signal_data['update_time']
            snapshot_date = snapshot_time.split()[0]
            
            cursor.execute('''
                INSERT OR REPLACE INTO signal_history 
                (snapshot_time, snapshot_date, short_value, short_change, long_value, long_change)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_time,
                snapshot_date,
                int(signal_data['short']),
                int(signal_data['short_change']),
                int(signal_data['long']),
                int(signal_data['long_change'])
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 保存信号数据失败: {e}")
            return False
        finally:
            conn.close()
    
    def save_panic_data(self, panic_data: Dict) -> bool:
        """
        保存恐慌清洗数据
        
        Args:
            panic_data: 恐慌清洗数据字典
            
        Returns:
            bool: 保存成功返回 True，失败返回 False
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            snapshot_time = panic_data['update_time']
            snapshot_date = snapshot_time.split()[0]
            
            cursor.execute('''
                INSERT OR REPLACE INTO panic_history 
                (snapshot_time, snapshot_date, panic_indicator, trend_rating, 
                 market_zone, liquidation_24h_count, liquidation_24h_amount, total_position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_time,
                snapshot_date,
                panic_data['panic_indicator'],
                panic_data['trend_rating'],
                panic_data['market_zone'],
                panic_data['liquidation_24h_count'],
                panic_data['liquidation_24h_amount'],
                panic_data['total_position']
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 保存恐慌清洗数据失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_signal_history(self, date: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """
        查询信号历史数据
        
        Args:
            date: 指定日期 (YYYY-MM-DD)，不指定则查询最近的数据
            hours: 查询最近多少小时的数据（默认24小时）
            
        Returns:
            List[Dict]: 信号历史数据列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if date:
                # 查询指定日期的数据
                cursor.execute('''
                    SELECT snapshot_time, short_value, short_change, long_value, long_change
                    FROM signal_history
                    WHERE snapshot_date = ?
                    ORDER BY snapshot_time ASC
                ''', (date,))
            else:
                # 查询最近N小时的数据
                cursor.execute('''
                    SELECT snapshot_time, short_value, short_change, long_value, long_change
                    FROM signal_history
                    WHERE datetime(snapshot_time) >= datetime('now', '-' || ? || ' hours', 'localtime')
                    ORDER BY snapshot_time ASC
                ''', (hours,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'time': row[0],
                    'short': row[1],
                    'short_change': row[2],
                    'long': row[3],
                    'long_change': row[4]
                })
            
            return results
            
        finally:
            conn.close()
    
    def get_panic_history(self, date: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """
        查询恐慌清洗历史数据
        
        Args:
            date: 指定日期 (YYYY-MM-DD)，不指定则查询最近的数据
            hours: 查询最近多少小时的数据（默认24小时）
            
        Returns:
            List[Dict]: 恐慌清洗历史数据列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if date:
                # 查询指定日期的数据
                cursor.execute('''
                    SELECT snapshot_time, panic_indicator, trend_rating, market_zone,
                           liquidation_24h_count, liquidation_24h_amount, total_position
                    FROM panic_history
                    WHERE snapshot_date = ?
                    ORDER BY snapshot_time ASC
                ''', (date,))
            else:
                # 查询最近N小时的数据
                cursor.execute('''
                    SELECT snapshot_time, panic_indicator, trend_rating, market_zone,
                           liquidation_24h_count, liquidation_24h_amount, total_position
                    FROM panic_history
                    WHERE datetime(snapshot_time) >= datetime('now', '-' || ? || ' hours', 'localtime')
                    ORDER BY snapshot_time ASC
                ''', (hours,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'time': row[0],
                    'panic_indicator': row[1],
                    'trend_rating': row[2],
                    'market_zone': row[3],
                    'liquidation_24h_count': row[4],
                    'liquidation_24h_amount': row[5],
                    'total_position': row[6]
                })
            
            return results
            
        finally:
            conn.close()

if __name__ == '__main__':
    # 测试数据库
    db = CryptoDatabase()
    stats = db.get_statistics()
    print("\n数据库统计信息:")
    print(f"  快照总数: {stats['total_snapshots']}")
    print(f"  时间范围: {stats['start_time']} ~ {stats['end_time']}")
    print(f"  币种数量: {stats['total_coins']}")
    print(f"  总记录数: {stats['total_records']}")
