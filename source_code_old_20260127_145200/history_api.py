#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据查询API
"""

from flask import Flask, jsonify, request, send_file
import sqlite3
from datetime import datetime, timedelta
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_history_simple import import_current_data

app = Flask(__name__)
DB_PATH = 'crypto_data.db'

def query_history_data(start_time=None, end_time=None, limit=100):
    """查询历史数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        where_clauses = []
        params = []
        
        if start_time:
            where_clauses.append('record_time >= ?')
            params.append(start_time)
        
        if end_time:
            where_clauses.append('record_time <= ?')
            params.append(end_time)
        
        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        # 查询统计数据
        cursor.execute(f'''
            SELECT * FROM stats_history
            WHERE {where_sql}
            ORDER BY record_time DESC
            LIMIT ?
        ''', params + [limit])
        
        stats_records = [dict(row) for row in cursor.fetchall()]
        
        # 为每条统计数据查询对应的币种数据
        for record in stats_records:
            cursor.execute('''
                SELECT * FROM coin_history
                WHERE stats_id = ?
                ORDER BY index_num
            ''', (record['id'],))
            
            record['coins'] = [dict(row) for row in cursor.fetchall()]
        
        return stats_records
        
    finally:
        conn.close()

def get_available_dates():
    """获取数据库中有数据的日期列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT DISTINCT DATE(record_time) as date
            FROM stats_history
            ORDER BY date DESC
        ''')
        
        dates = [row[0] for row in cursor.fetchall()]
        return dates
        
    finally:
        conn.close()

def get_time_range_for_date(date_str):
    """获取指定日期的时间范围"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT MIN(record_time) as min_time, MAX(record_time) as max_time
            FROM stats_history
            WHERE DATE(record_time) = ?
        ''', (date_str,))
        
        row = cursor.fetchone()
        return {
            'min_time': row[0],
            'max_time': row[1]
        }
        
    finally:
        conn.close()

@app.route('/')
def index():
    """历史回看页面"""
    return send_file('history_viewer.html')

@app.route('/api/history/dates')
def get_dates():
    """获取有数据的日期列表"""
    try:
        dates = get_available_dates()
        
        # 获取每个日期的统计信息
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        date_info = []
        for date in dates:
            cursor.execute('''
                SELECT COUNT(*) as count,
                       MIN(record_time) as min_time,
                       MAX(record_time) as max_time
                FROM stats_history
                WHERE DATE(record_time) = ?
            ''', (date,))
            
            row = cursor.fetchone()
            date_info.append({
                'date': date,
                'count': row[0],
                'min_time': row[1],
                'max_time': row[2]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'dates': date_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/history/query')
def query_history():
    """查询历史数据"""
    try:
        # 获取查询参数
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        date = request.args.get('date')  # 如果只查询某一天
        limit = int(request.args.get('limit', 100))
        
        # 如果指定了日期，自动设置时间范围
        if date:
            start_time = f"{date} 00:00:00"
            end_time = f"{date} 23:59:59"
        
        records = query_history_data(start_time, end_time, limit)
        
        return jsonify({
            'success': True,
            'count': len(records),
            'data': records,
            'query': {
                'start_time': start_time,
                'end_time': end_time,
                'limit': limit
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/history/stats')
def get_stats():
    """获取数据库统计信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM stats_history')
        stats_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM coin_history')
        coin_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM stats_history')
        time_range = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(DISTINCT DATE(record_time)) FROM stats_history')
        day_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_records': stats_count,
                'total_coins': coin_count,
                'earliest': time_range[0],
                'latest': time_range[1],
                'days': day_count
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/import/current', methods=['POST'])
def import_current():
    """导入当前最新数据"""
    try:
        asyncio.run(import_current_data())
        return jsonify({
            'success': True,
            'message': '导入成功'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("="*60)
    print("历史数据查询服务")
    print("="*60)
    print("访问: http://0.0.0.0:5004/")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5004, debug=False, threaded=True)
