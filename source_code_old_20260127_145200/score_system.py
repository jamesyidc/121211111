#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密货币得分系统 V1.0
整合多个数据源的做多做空评分，计算各时间段的平均得分和差值
"""

import sqlite3
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import statistics
from flask import Flask, jsonify, render_template_string, send_from_directory, request
from flask_cors import CORS
import threading
import time

class ScoreDatabase:
    """得分数据库管理"""
    
    def __init__(self, db_path='crypto_data.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建得分历史记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS score_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                time_range TEXT NOT NULL,
                long_score REAL,
                short_score REAL,
                score_diff REAL,
                data_source TEXT,
                record_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, time_range, record_time)
            )
        ''')
        
        # 创建得分统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS score_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_range TEXT NOT NULL,
                avg_long_score REAL,
                avg_short_score REAL,
                avg_diff REAL,
                coin_count INTEGER,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(time_range, update_time)
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_score_history_time 
            ON score_history(record_time DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_score_history_symbol 
            ON score_history(symbol, time_range)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ 数据库初始化完成")
    
    def save_score_record(self, symbol: str, time_range: str, 
                         long_score: float, short_score: float, 
                         data_source: str = 'unknown'):
        """保存单条得分记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        score_diff = long_score - short_score
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO score_history 
                (symbol, time_range, long_score, short_score, score_diff, data_source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, time_range, long_score, short_score, score_diff, data_source))
            conn.commit()
        except Exception as e:
            print(f"❌ 保存得分记录失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_statistics(self, time_range: str, avg_long: float, 
                       avg_short: float, avg_diff: float, coin_count: int):
        """保存统计数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO score_statistics 
                (time_range, avg_long_score, avg_short_score, avg_diff, coin_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (time_range, avg_long, avg_short, avg_diff, coin_count))
            conn.commit()
        except Exception as e:
            print(f"❌ 保存统计数据失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_latest_statistics(self) -> Dict:
        """获取最新的统计数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT time_range, avg_long_score, avg_short_score, avg_diff, 
                   coin_count, update_time
            FROM score_statistics
            WHERE update_time = (SELECT MAX(update_time) FROM score_statistics)
            ORDER BY 
                CASE time_range
                    WHEN '3m' THEN 1
                    WHEN '1h' THEN 2
                    WHEN '3h' THEN 3
                    WHEN '6h' THEN 4
                    WHEN '12h' THEN 5
                    WHEN '24h' THEN 6
                END
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        result = {
            'update_time': None,
            'statistics': []
        }
        
        for row in rows:
            if result['update_time'] is None:
                result['update_time'] = row['update_time']
            
            result['statistics'].append({
                'time_range': row['time_range'],
                'avg_long_score': round(row['avg_long_score'], 2),
                'avg_short_score': round(row['avg_short_score'], 2),
                'avg_diff': round(row['avg_diff'], 2),
                'coin_count': row['coin_count'],
                'trend': '📈 看多' if row['avg_diff'] > 0 else '📉 看空'
            })
        
        return result
    
    def get_coin_scores(self, hours: int = 24) -> Dict:
        """获取各币种的最新得分"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        cursor.execute('''
            SELECT symbol, time_range, long_score, short_score, 
                   score_diff, record_time
            FROM score_history
            WHERE record_time >= ?
            ORDER BY symbol, 
                CASE time_range
                    WHEN '3m' THEN 1
                    WHEN '1h' THEN 2
                    WHEN '3h' THEN 3
                    WHEN '6h' THEN 4
                    WHEN '12h' THEN 5
                    WHEN '24h' THEN 6
                END
        ''', (cutoff_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 按币种组织数据
        coins = {}
        for row in rows:
            symbol = row['symbol']
            if symbol not in coins:
                coins[symbol] = {}
            
            coins[symbol][row['time_range']] = {
                'long_score': round(row['long_score'], 2),
                'short_score': round(row['short_score'], 2),
                'diff': round(row['score_diff'], 2),
                'update_time': row['record_time']
            }
        
        return coins


class ScoreCollector:
    """得分数据采集器"""
    
    def __init__(self, db: ScoreDatabase):
        self.db = db
        self.time_ranges = ['3m', '1h', '3h', '6h', '12h', '24h']
        
        # 定义币种列表（示例数据）
        self.symbols = [
            'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'BNB-USDT-SWAP',
            'SOL-USDT-SWAP', 'DOT-USDT-SWAP', 'LINK-USDT-SWAP',
            'ADA-USDT-SWAP', 'FIL-USDT-SWAP', 'DOGE-USDT-SWAP',
            'UNI-USDT-SWAP', 'TAO-USDT-SWAP', 'CFX-USDT-SWAP',
            'BCH-USDT-SWAP', 'XLM-USDT-SWAP', 'HBAR-USDT-SWAP',
            'ETC-USDT-SWAP', 'AVAX-USDT-SWAP', 'MATIC-USDT-SWAP',
            'OKB-USDT-SWAP'
        ]
    
    def generate_mock_score(self, symbol: str, time_range: str) -> Tuple[float, float]:
        """
        生成模拟得分数据
        实际应用中应该从真实API获取
        """
        import random
        
        # 基础得分范围 40-60
        base_long = 45 + random.uniform(-5, 15)
        base_short = 45 + random.uniform(-5, 15)
        
        # 根据时间范围调整波动
        time_multiplier = {
            '3m': 1.0,
            '1h': 0.9,
            '3h': 0.8,
            '6h': 0.7,
            '12h': 0.6,
            '24h': 0.5
        }.get(time_range, 1.0)
        
        long_score = base_long * time_multiplier + random.uniform(-3, 3)
        short_score = base_short * time_multiplier + random.uniform(-3, 3)
        
        # 限制范围在0-100之间
        long_score = max(0, min(100, long_score))
        short_score = max(0, min(100, short_score))
        
        return round(long_score, 2), round(short_score, 2)
    
    def collect_all_scores(self):
        """采集所有币种所有时间范围的得分"""
        print(f"\n🔄 开始采集得分数据... {datetime.now().strftime('%H:%M:%S')}")
        
        collected_count = 0
        for symbol in self.symbols:
            for time_range in self.time_ranges:
                long_score, short_score = self.generate_mock_score(symbol, time_range)
                self.db.save_score_record(
                    symbol=symbol,
                    time_range=time_range,
                    long_score=long_score,
                    short_score=short_score,
                    data_source='mock'
                )
                collected_count += 1
        
        print(f"✅ 采集完成: {collected_count} 条记录")
        return collected_count
    
    def calculate_and_save_statistics(self):
        """计算并保存统计数据"""
        print("📊 计算统计数据...")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # 获取最新的记录时间
        cursor.execute('SELECT MAX(record_time) FROM score_history')
        latest_time = cursor.fetchone()[0]
        
        if not latest_time:
            print("❌ 没有可用数据")
            conn.close()
            return
        
        # 对每个时间范围计算统计
        for time_range in self.time_ranges:
            cursor.execute('''
                SELECT AVG(long_score) as avg_long, 
                       AVG(short_score) as avg_short,
                       AVG(score_diff) as avg_diff,
                       COUNT(*) as coin_count
                FROM score_history
                WHERE time_range = ? 
                AND record_time = ?
            ''', (time_range, latest_time))
            
            row = cursor.fetchone()
            if row and row['coin_count'] > 0:
                self.db.save_statistics(
                    time_range=time_range,
                    avg_long=row['avg_long'],
                    avg_short=row['avg_short'],
                    avg_diff=row['avg_diff'],
                    coin_count=row['coin_count']
                )
        
        conn.close()
        print("✅ 统计计算完成")


# Flask Web应用
app = Flask(__name__)
CORS(app)

# 全局变量
db = ScoreDatabase()
collector = ScoreCollector(db)


@app.route('/')
def index():
    """主页"""
    return send_from_directory('.', 'score_system.html')


@app.route('/api/score/statistics')
def get_statistics():
    """获取统计数据API"""
    data = db.get_latest_statistics()
    return jsonify(data)


@app.route('/api/score/coins')
def get_coin_scores():
    """获取各币种得分API"""
    hours = int(request.args.get('hours', 24))
    data = db.get_coin_scores(hours)
    return jsonify(data)


@app.route('/api/score/refresh')
def refresh_data():
    """手动刷新数据"""
    try:
        collector.collect_all_scores()
        collector.calculate_and_save_statistics()
        return jsonify({
            'success': True,
            'message': '数据刷新成功',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'刷新失败: {str(e)}'
        }), 500


def auto_update_loop():
    """自动更新循环"""
    while True:
        try:
            print(f"\n⏰ 定时更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            collector.collect_all_scores()
            collector.calculate_and_save_statistics()
            print("✅ 自动更新完成\n")
        except Exception as e:
            print(f"❌ 自动更新失败: {e}")
        
        # 每3分钟更新一次
        time.sleep(180)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 加密货币得分系统 V1.0")
    print("="*80)
    
    # 初始化数据库
    print("📦 初始化数据库...")
    db.init_database()
    
    # 首次采集数据
    print("📊 首次数据采集...")
    collector.collect_all_scores()
    collector.calculate_and_save_statistics()
    
    # 启动自动更新线程
    print("⏰ 启动自动更新线程 (每3分钟)...")
    update_thread = threading.Thread(target=auto_update_loop, daemon=True)
    update_thread.start()
    
    # 启动Web服务
    port = 5009
    print(f"\n🌐 Web服务启动:")
    print(f"   主页: http://0.0.0.0:{port}/")
    print(f"   统计API: http://0.0.0.0:{port}/api/score/statistics")
    print(f"   币种API: http://0.0.0.0:{port}/api/score/coins")
    print(f"   刷新API: http://0.0.0.0:{port}/api/score/refresh")
    print("="*80)
    print("按 Ctrl+C 停止服务\n")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")


if __name__ == '__main__':
    main()
