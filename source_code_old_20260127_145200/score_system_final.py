#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密货币得分系统 V3.0 - 最终版
- 使用路径后缀而非不同端口
- 支持历史数据查询
- 修正币种名称（排除MATIC和OKB）
"""

import sqlite3
import json
import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import threading
import time

class ScoreDatabase:
    """得分数据库管理 - 支持历史数据"""
    
    def __init__(self, db_path='crypto_data.db'):
        self.db_path = db_path
        self.init_database()
        # 排除的币种列表
        self.excluded_coins = ['MATIC-USDT-SWAP', 'OKB-USDT-SWAP']
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建得分历史记录表 - 保留所有历史数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS score_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                time_range TEXT NOT NULL,
                long_score REAL,
                short_score REAL,
                score_diff REAL,
                data_source TEXT,
                record_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建得分统计表 - 按时间记录统计快照
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS score_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_range TEXT NOT NULL,
                avg_long_score REAL,
                avg_short_score REAL,
                avg_diff REAL,
                coin_count INTEGER,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_score_history_time 
            ON score_history(record_time DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_score_history_symbol_time 
            ON score_history(symbol, time_range, record_time DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_statistics_time
            ON score_statistics(update_time DESC)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ 数据库初始化完成")
    
    def clean_excluded_coins(self):
        """清理排除的币种"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for coin in self.excluded_coins:
            cursor.execute('DELETE FROM score_history WHERE symbol = ?', (coin,))
            print(f"🗑️  删除排除币种: {coin}")
        
        conn.commit()
        conn.close()
    
    def save_score_record(self, symbol: str, time_range: str, 
                         long_score: float, short_score: float, 
                         data_source: str = 'web_scraper'):
        """保存单条得分记录"""
        # 跳过排除的币种
        if symbol in self.excluded_coins:
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        score_diff = long_score - short_score
        
        try:
            cursor.execute('''
                INSERT INTO score_history 
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
        """保存统计数据快照"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO score_statistics 
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
        
        # 获取最新一批统计数据
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
        
        # 获取每个币种每个时间段的最新记录
        cursor.execute('''
            SELECT h1.symbol, h1.time_range, h1.long_score, h1.short_score, 
                   h1.score_diff, h1.record_time
            FROM score_history h1
            INNER JOIN (
                SELECT symbol, time_range, MAX(record_time) as max_time
                FROM score_history
                WHERE record_time >= ?
                GROUP BY symbol, time_range
            ) h2 ON h1.symbol = h2.symbol 
                AND h1.time_range = h2.time_range 
                AND h1.record_time = h2.max_time
            ORDER BY h1.symbol, 
                CASE h1.time_range
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
            # 跳过排除的币种
            if symbol in self.excluded_coins:
                continue
                
            if symbol not in coins:
                coins[symbol] = {}
            
            coins[symbol][row['time_range']] = {
                'long_score': round(row['long_score'], 2),
                'short_score': round(row['short_score'], 2),
                'diff': round(row['score_diff'], 2),
                'update_time': row['record_time']
            }
        
        return coins
    
    def get_history_dates(self, days: int = 30) -> List[str]:
        """获取历史记录日期列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        cursor.execute('''
            SELECT DISTINCT DATE(record_time) as record_date
            FROM score_history
            WHERE record_time >= ?
            ORDER BY record_date DESC
        ''', (cutoff.strftime('%Y-%m-%d'),))
        
        dates = [row['record_date'] for row in cursor.fetchall()]
        conn.close()
        return dates
    
    def get_history_by_date(self, date: str) -> Dict:
        """获取指定日期的历史数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取该日期的统计记录
        cursor.execute('''
            SELECT time_range, avg_long_score, avg_short_score, 
                   avg_diff, coin_count, update_time
            FROM score_statistics
            WHERE DATE(update_time) = ?
            ORDER BY update_time DESC, 
                CASE time_range
                    WHEN '3m' THEN 1
                    WHEN '1h' THEN 2
                    WHEN '3h' THEN 3
                    WHEN '6h' THEN 4
                    WHEN '12h' THEN 5
                    WHEN '24h' THEN 6
                END
            LIMIT 6
        ''', (date,))
        
        stats_rows = cursor.fetchall()
        
        result = {
            'date': date,
            'update_time': None,
            'statistics': []
        }
        
        for row in stats_rows:
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
        
        conn.close()
        return result


class WebScoreCollector:
    """从网页抓取得分数据"""
    
    def __init__(self, db: ScoreDatabase):
        self.db = db
        self.urls = {
            'source_1': 'https://3000-i42fq2f1mk8544uuc8pew-5c13a017.sandbox.novita.ai/score_overview.html',
            'source_2': 'https://3000-itkyuobnbphje7wgo4xbk-c07dda5e.sandbox.novita.ai/score_overview.html'
        }
        self.time_ranges = ['3m', '1h', '3h', '6h', '12h', '24h']
    
    async def scrape_page(self, page, url: str, source_name: str) -> Dict:
        """抓取单个页面的数据"""
        print(f"📡 正在加载: {url}")
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_selector('table tbody tr', timeout=10000)
            await asyncio.sleep(3)
            
            rows = await page.query_selector_all('table tbody tr')
            print(f"✅ {source_name}: 找到 {len(rows)} 行数据")
            
            data = {}
            
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) < 4:
                    continue
                
                coin_cell = cells[0]
                coin_text = await coin_cell.inner_text()
                coin_name = coin_text.strip()
                
                if not coin_name:
                    continue
                
                if not coin_name.endswith('-USDT-SWAP'):
                    coin_name = f"{coin_name}-USDT-SWAP"
                
                # 跳过排除的币种
                if coin_name in self.db.excluded_coins:
                    print(f"⏭️  跳过排除币种: {coin_name}")
                    continue
                
                data[coin_name] = {}
                
                cell_idx = 1
                for time_range in self.time_ranges:
                    if cell_idx + 2 < len(cells):
                        try:
                            long_cell = cells[cell_idx]
                            short_cell = cells[cell_idx + 1]
                            diff_cell = cells[cell_idx + 2]
                            
                            long_text = await long_cell.inner_text()
                            short_text = await short_cell.inner_text()
                            diff_text = await diff_cell.inner_text()
                            
                            long_score = self.extract_number(long_text)
                            short_score = self.extract_number(short_text)
                            diff_score = self.extract_number(diff_text)
                            
                            if long_score is not None and short_score is not None:
                                data[coin_name][time_range] = {
                                    'long_score': long_score,
                                    'short_score': short_score,
                                    'diff': diff_score if diff_score is not None else (long_score - short_score)
                                }
                        except Exception as e:
                            pass
                        
                        cell_idx += 3
                
                if not data[coin_name]:
                    del data[coin_name]
            
            return data
            
        except Exception as e:
            print(f"❌ {source_name}: 抓取失败 - {e}")
            return {}
    
    def extract_number(self, text: str) -> float:
        """从文本中提取数字"""
        if not text:
            return None
        
        cleaned = re.sub(r'[^\d.\-+]', '', text.strip())
        if not cleaned or cleaned in ['-', '+', '.']:
            return None
        
        try:
            return float(cleaned)
        except:
            return None
    
    async def collect_all_scores(self):
        """抓取所有数据源"""
        print(f"\n🔄 开始抓取得分数据... {datetime.now().strftime('%H:%M:%S')}")
        
        all_data = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # 抓取第一个数据源
            data1 = await self.scrape_page(page, self.urls['source_1'], 'source_1')
            if data1:
                print(f"✅ 数据源1: 获取到 {len(data1)} 个币种")
                all_data.update(data1)
            
            await asyncio.sleep(2)
            
            # 抓取第二个数据源
            data2 = await self.scrape_page(page, self.urls['source_2'], 'source_2')
            if data2:
                print(f"✅ 数据源2: 获取到 {len(data2)} 个币种")
                for coin, scores in data2.items():
                    if coin not in all_data:
                        all_data[coin] = scores
            
            await browser.close()
        
        # 保存到数据库
        collected_count = 0
        for symbol, scores in all_data.items():
            for time_range, score_data in scores.items():
                self.db.save_score_record(
                    symbol=symbol,
                    time_range=time_range,
                    long_score=score_data['long_score'],
                    short_score=score_data['short_score'],
                    data_source='web_scraper'
                )
                collected_count += 1
        
        print(f"✅ 采集完成: {collected_count} 条记录")
        return collected_count
    
    def calculate_and_save_statistics(self):
        """计算并保存统计数据"""
        print("📊 计算统计数据...")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT MAX(record_time) FROM score_history')
        latest_time = cursor.fetchone()[0]
        
        if not latest_time:
            print("❌ 没有可用数据")
            conn.close()
            return
        
        for time_range in self.time_ranges:
            # 排除特定币种的统计
            excluded_condition = ' AND ' + ' AND '.join([f"symbol != '{coin}'" for coin in self.db.excluded_coins])
            
            cursor.execute(f'''
                SELECT AVG(long_score) as avg_long, 
                       AVG(short_score) as avg_short,
                       AVG(score_diff) as avg_diff,
                       COUNT(*) as coin_count
                FROM score_history
                WHERE time_range = ? 
                AND record_time = ?
                {excluded_condition}
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
collector = WebScoreCollector(db)


@app.route('/')
@app.route('/score')
def index():
    """主页 - 实时评分"""
    return send_from_directory('.', 'score_system.html')


@app.route('/history')
def history_page():
    """历史数据页面"""
    return send_from_directory('.', 'score_history.html')


@app.route('/api/score/statistics')
def get_statistics():
    """获取最新统计数据API"""
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
        # 在新的事件循环中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(collector.collect_all_scores())
        loop.close()
        
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


@app.route('/api/history/dates')
def get_history_dates():
    """获取历史记录日期列表"""
    days = int(request.args.get('days', 30))
    dates = db.get_history_dates(days)
    return jsonify({'dates': dates})


@app.route('/api/history/<date>')
def get_history_data(date):
    """获取指定日期的历史数据"""
    data = db.get_history_by_date(date)
    return jsonify(data)


def auto_update_loop():
    """自动更新循环"""
    while True:
        try:
            print(f"\n⏰ 定时更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 在新的事件循环中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(collector.collect_all_scores())
            loop.close()
            
            collector.calculate_and_save_statistics()
            print("✅ 自动更新完成\n")
        except Exception as e:
            print(f"❌ 自动更新失败: {e}")
        
        # 每3分钟更新一次
        time.sleep(180)


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 加密货币得分系统 V3.0 - 最终版")
    print("="*80)
    
    # 初始化数据库
    print("📦 初始化数据库...")
    db.init_database()
    
    # 清理排除的币种
    print("🗑️  清理排除币种...")
    db.clean_excluded_coins()
    
    # 首次采集数据
    print("📊 首次数据采集...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(collector.collect_all_scores())
    loop.close()
    
    collector.calculate_and_save_statistics()
    
    # 启动自动更新线程
    print("⏰ 启动自动更新线程 (每3分钟)...")
    update_thread = threading.Thread(target=auto_update_loop, daemon=True)
    update_thread.start()
    
    # 启动Web服务
    port = 5010
    print(f"\n🌐 Web服务启动:")
    print(f"   主页: http://0.0.0.0:{port}/")
    print(f"   实时评分: http://0.0.0.0:{port}/score")
    print(f"   历史数据: http://0.0.0.0:{port}/history")
    print(f"   统计API: http://0.0.0.0:{port}/api/score/statistics")
    print(f"   币种API: http://0.0.0.0:{port}/api/score/coins")
    print(f"   刷新API: http://0.0.0.0:{port}/api/score/refresh")
    print(f"   历史日期API: http://0.0.0.0:{port}/api/history/dates")
    print("="*80)
    print("按 Ctrl+C 停止服务\n")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")


if __name__ == '__main__':
    main()
