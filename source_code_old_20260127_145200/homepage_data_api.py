#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页数据 API
提供实时监控数据的RESTful接口
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
CORS(app)

# 数据库配置
DB_PATH = 'homepage_data.db'

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/homepage/latest')
def get_latest_data():
    """获取最新的首页数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最新的汇总数据
        cursor.execute('''
            SELECT * FROM summary_data 
            ORDER BY record_time DESC 
            LIMIT 1
        ''')
        summary_row = cursor.fetchone()
        
        if not summary_row:
            return jsonify({
                'success': False,
                'message': '暂无数据'
            })
        
        summary_data = dict(summary_row)
        summary_id = summary_data['id']
        
        # 获取对应的币种详情
        cursor.execute('''
            SELECT * FROM coin_details 
            WHERE summary_id = ? 
            ORDER BY seq_num
        ''', (summary_id,))
        
        coins_rows = cursor.fetchall()
        coins_data = [dict(row) for row in coins_rows]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'current_time': get_beijing_time().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': summary_data,
            'coins': coins_data,
            'count': len(coins_data)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/homepage/history')
def get_history_data():
    """获取历史数据"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        start_time = request.args.get('start_time', '00:00:00')
        end_time = request.args.get('end_time', '23:59:59')
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'message': '请提供start_date和end_date参数'
            }), 400
        
        start_datetime = f"{start_date} {start_time}"
        end_datetime = f"{end_date} {end_time}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询历史汇总数据
        cursor.execute('''
            SELECT * FROM summary_data 
            WHERE record_time >= ? AND record_time <= ?
            ORDER BY record_time DESC
        ''', (start_datetime, end_datetime))
        
        summary_rows = cursor.fetchall()
        history_data = []
        
        for summary_row in summary_rows:
            summary_dict = dict(summary_row)
            summary_id = summary_dict['id']
            
            # 获取对应的币种详情
            cursor.execute('''
                SELECT * FROM coin_details 
                WHERE summary_id = ? 
                ORDER BY seq_num
            ''', (summary_id,))
            
            coins_rows = cursor.fetchall()
            coins_data = [dict(row) for row in coins_rows]
            
            history_data.append({
                'summary': summary_dict,
                'coins': coins_data
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'start': start_datetime,
            'end': end_datetime,
            'count': len(history_data),
            'data': history_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/homepage/stats')
def get_stats():
    """获取统计信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute('SELECT COUNT(*) as count FROM summary_data')
        total_records = cursor.fetchone()['count']
        
        # 获取时间范围
        cursor.execute('''
            SELECT MIN(record_time) as min_time, MAX(record_time) as max_time 
            FROM summary_data
        ''')
        time_range = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_records': total_records,
            'date_range': {
                'start': time_range['min_time'],
                'end': time_range['max_time']
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/homepage/test')
def test_api():
    """测试API连接"""
    beijing_time = get_beijing_time()
    
    return jsonify({
        'success': True,
        'message': 'API连接正常',
        'beijing_time': beijing_time.strftime('%Y-%m-%d %H:%M:%S'),
        'database': DB_PATH
    })


if __name__ == '__main__':
    print("="*70)
    print("首页数据 API")
    print("="*70)
    print(f"启动时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"数据库: {DB_PATH}")
    print("="*70)
    print("\nAPI 端点:")
    print("  GET  /api/homepage/latest   - 获取最新数据")
    print("  GET  /api/homepage/history  - 获取历史数据")
    print("  GET  /api/homepage/stats    - 获取统计信息")
    print("  GET  /api/homepage/test     - 测试API")
    print("="*70)
    
    app.run(host='0.0.0.0', port=5004, debug=False)
