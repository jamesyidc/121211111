#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恐慌清洗指标API - 新版本
"""

from flask import Flask, jsonify, send_file
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import asyncio
from panic_wash_new import MockPanicWashCalculator, PanicWashCalculator
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

app = Flask(__name__)
CORS(app)

DB_PATH = 'crypto_data.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/panic-wash/latest')
def get_latest():
    """获取最新数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM panic_wash_new 
            ORDER BY record_time DESC 
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'success': True,
                'data': {
                    'id': row['id'],
                    'record_time': row['record_time'],
                    'hour_1_amount': row['hour_1_amount'],
                    'hour_24_amount': row['hour_24_amount'],
                    'hour_24_people': row['hour_24_people'],
                    'total_position': row['total_position'],
                    'panic_index': row['panic_index'],
                    'created_at': row['created_at']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '暂无数据'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/panic-wash/history')
def get_history():
    """获取历史数据（最近24小时）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最近24小时的数据
        time_24h_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT * FROM panic_wash_new 
            WHERE record_time >= ?
            ORDER BY record_time ASC
        ''', (time_24h_ago,))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                'record_time': row['record_time'],
                'hour_1_amount': row['hour_1_amount'],
                'hour_24_amount': row['hour_24_amount'],
                'hour_24_people': row['hour_24_people'],
                'total_position': row['total_position'],
                'panic_index': row['panic_index']
            })
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/panic-wash/refresh', methods=['POST'])
def refresh_data():
    """手动刷新数据"""
    try:
        # 创建计算器实例
        if PLAYWRIGHT_AVAILABLE:
            calculator = PanicWashCalculator(DB_PATH)
        else:
            calculator = MockPanicWashCalculator(DB_PATH)
        
        # 异步执行数据采集
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(calculator.run_once())
        loop.close()
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': '数据刷新成功',
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'message': '数据刷新失败',
                'error': result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/panic-wash')
def panic_wash_page():
    """恐慌清洗指标页面"""
    return send_file('panic_wash_new.html')

@app.route('/api/panic-wash/query')
def query_data():
    """按日期时间范围查询数据"""
    try:
        from flask import request
        start_time = request.args.get('start')
        end_time = request.args.get('end')
        
        if not start_time or not end_time:
            return jsonify({
                'success': False,
                'message': '请提供start和end参数'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM panic_wash_new 
            WHERE record_time >= ? AND record_time <= ?
            ORDER BY record_time ASC
        ''', (start_time, end_time))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                'record_time': row['record_time'],
                'hour_1_amount': row['hour_1_amount'],
                'hour_24_amount': row['hour_24_amount'],
                'hour_24_people': row['hour_24_people'],
                'total_position': row['total_position'],
                'panic_index': row['panic_index']
            })
        
        return jsonify({
            'success': True,
            'count': len(data),
            'start_time': start_time,
            'end_time': end_time,
            'data': data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/panic-wash/stats')
def get_stats():
    """获取统计信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最近24小时统计
        time_24h_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT 
                COUNT(*) as count,
                AVG(panic_index) as avg_index,
                MIN(panic_index) as min_index,
                MAX(panic_index) as max_index,
                AVG(hour_24_people) as avg_people,
                AVG(total_position) as avg_position
            FROM panic_wash_new 
            WHERE record_time >= ?
        ''', (time_24h_ago,))
        
        row = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'sample_count': row['count'],
                'avg_panic_index': row['avg_index'],
                'min_panic_index': row['min_index'],
                'max_panic_index': row['max_index'],
                'avg_liquidation_people': row['avg_people'],
                'avg_total_position': row['avg_position']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("="*70)
    print("恐慌清洗指标 API 服务器")
    print("="*70)
    print(f"启动时间: {datetime.now()}")
    print(f"Playwright: {'✅ 已安装' if PLAYWRIGHT_AVAILABLE else '❌ 未安装（使用模拟数据）'}")
    print("="*70)
    print("\nAPI 端点:")
    print("  GET  /api/panic-wash/latest    - 获取最新数据")
    print("  GET  /api/panic-wash/history   - 获取历史数据")
    print("  GET  /api/panic-wash/stats     - 获取统计信息")
    print("  POST /api/panic-wash/refresh   - 手动刷新数据")
    print("  GET  /panic-wash               - 查看页面")
    print("="*70)
    
    app.run(host='0.0.0.0', port=5002, debug=True)
