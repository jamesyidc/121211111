#!/usr/bin/env python3
"""
加密货币数据服务器 - 真实数据版本
直接从数据库读取真实数据
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from datetime import datetime
import pytz
import sqlite3
import os

app = Flask(__name__, static_folder='.')
CORS(app)

DB_PATH = 'homepage_data.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """首页"""
    response = send_from_directory('.', 'index.html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/live-data')
def live_data_page():
    """实时监控数据页面"""
    file_path = os.path.join(os.path.dirname(__file__), 'live_monitor.html')
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    response = app.make_response(content)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/trend-chart')
def trend_chart():
    """趋势图表页面"""
    response = send_from_directory('.', 'trend_chart.html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/upload')
def upload_page():
    """上传页面"""
    response = send_from_directory('.', 'upload_data.html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/homepage/latest')
def get_homepage_latest():
    """获取最新首页数据 - 从数据库读取"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最新的汇总数据
        cursor.execute("""
            SELECT * FROM summary_data 
            ORDER BY id DESC 
            LIMIT 1
        """)
        summary_row = cursor.fetchone()
        
        if not summary_row:
            return jsonify({
                'success': False,
                'message': '数据库中没有数据'
            }), 404
        
        summary_id = summary_row['id']
        
        # 获取对应的币种数据
        cursor.execute("""
            SELECT * FROM coin_details 
            WHERE summary_id = ?
            ORDER BY seq_num
        """, (summary_id,))
        coin_rows = cursor.fetchall()
        
        conn.close()
        
        # 构造返回数据
        summary = {
            'id': summary_row['id'],
            'rise_total': summary_row['rise_total'],
            'fall_total': summary_row['fall_total'],
            'five_states': summary_row['five_states'],
            'rise_fall_ratio': summary_row['rise_fall_ratio'],
            'green_count': summary_row['green_count'],
            'green_percent': summary_row['green_percent'],
            'count_times': summary_row['count_times'],
            'diff_result': summary_row['diff_result'],
            'record_time': summary_row['record_time']
        }
        
        coins = []
        for row in coin_rows:
            coins.append({
                'seq_num': row['seq_num'],
                'coin_name': row['coin_name'],
                'rise_speed': row['rise_speed'],
                'rise_signal': row['rise_signal'],
                'fall_signal': row['fall_signal'],
                'update_time': row['update_time'],
                'history_high': row['history_high'],
                'high_time': row['high_time'],
                'drop_from_high': row['drop_from_high'],
                'change_24h': row['change_24h'],
                'plus_4_percent': row['plus_4_percent'] if 'plus_4_percent' in row.keys() else 0,
                'minus_3_percent': row['minus_3_percent'] if 'minus_3_percent' in row.keys() else 0,
                'ranking': row['ranking'],
                'current_price': row['current_price'],
                'high_ratio': row['high_ratio'],
                'low_ratio': row['low_ratio'],
                'anomaly': row['anomaly'] if 'anomaly' in row.keys() else '',
                'record_time': row['record_time']
            })
        
        return jsonify({
            'success': True,
            'summary': summary,
            'coins': coins
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/homepage/history')
def get_homepage_history():
    """获取历史数据"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM summary_data 
                WHERE record_time BETWEEN ? AND ?
                ORDER BY record_time
            """, (start_date, end_date))
        else:
            # 默认返回最近100条
            cursor.execute("""
                SELECT * FROM summary_data 
                ORDER BY id DESC 
                LIMIT 100
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                'id': row['id'],
                'rise_total': row['rise_total'],
                'fall_total': row['fall_total'],
                'five_states': row['five_states'],
                'rise_fall_ratio': row['rise_fall_ratio'],
                'green_count': row['green_count'],
                'green_percent': row['green_percent'],
                'count_times': row['count_times'],
                'diff_result': row['diff_result'],
                'record_time': row['record_time']
            })
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("\n" + "="*80)
    print("加密货币数据服务器 - 真实数据版本")
    print("="*80)
    print(f"数据库: {DB_PATH}")
    print(f"服务器运行在: http://0.0.0.0:5001")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
