#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟币系统信号监控 API
从 Google Drive 读取信号数据并存储到数据库
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import pytz
import re
import os
import sqlite3
import threading
import time

app = Flask(__name__)
CORS(app)

# Google Drive 共享链接
GOOGLE_DRIVE_FOLDER_ID = "1-IfqZxMVVCSg3ct6XVMyFtAbuCV3huQ"

# 数据库配置
DB_PATH = 'signal_data.db'

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 初始化数据库
def init_database():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建信号数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_count INTEGER NOT NULL,
            short_change INTEGER NOT NULL,
            long_count INTEGER NOT NULL,
            long_change INTEGER NOT NULL,
            record_time TEXT NOT NULL,
            folder_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(record_time)
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_time ON signal_data(record_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_folder_date ON signal_data(folder_date)')
    
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_PATH}")

def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)

def get_today_folder_name():
    """获取今天的文件夹名称（北京时间）"""
    beijing_now = get_beijing_time()
    
    # 如果是0点到0点5分之间，使用昨天的日期
    if beijing_now.hour == 0 and beijing_now.minute < 5:
        beijing_now = beijing_now - timedelta(days=1)
    
    return beijing_now.strftime('%Y-%m-%d')

def parse_google_drive_folder_id(share_link):
    """从Google Drive分享链接提取folder ID"""
    # 已经提取好了
    return GOOGLE_DRIVE_FOLDER_ID

def list_drive_files(folder_id):
    """列出Google Drive文件夹中的文件
    注意：这需要Google Drive API权限，这里使用简化方案
    """
    try:
        # 使用公开访问方式（如果文件夹是公开的）
        # 实际实现需要Google Drive API
        # 这里先返回模拟数据，实际需要配置API
        
        # 方案：使用Google Drive API v3
        # 需要credentials和API key
        
        return {
            'success': False,
            'message': '需要配置Google Drive API credentials'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def parse_signal_line(line):
    """解析信号数据行: 做空|变化|做多|变化|时间"""
    try:
        parts = line.strip().split('|')
        if len(parts) >= 5:
            # 处理可能包含负号的数字
            def safe_int(s):
                s = s.strip()
                if s.lstrip('-').isdigit():
                    return int(s)
                return 0
            
            return {
                'short_count': safe_int(parts[0]),
                'short_change': safe_int(parts[1]),
                'long_count': safe_int(parts[2]),
                'long_change': safe_int(parts[3]),
                'record_time': parts[4].strip()
            }
    except Exception as e:
        print(f"解析行失败: {line}, 错误: {e}")
    return None

def save_signal_to_db(signal_data, folder_date):
    """保存信号数据到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO signal_data 
            (short_count, short_change, long_count, long_change, record_time, folder_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            signal_data['short_count'],
            signal_data['short_change'],
            signal_data['long_count'],
            signal_data['long_change'],
            signal_data['record_time'],
            folder_date
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"保存数据失败: {e}")
        return False

def get_latest_signal_from_db():
    """从数据库获取最新信号"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT short_count, short_change, long_count, long_change, 
                   record_time, folder_date
            FROM signal_data
            ORDER BY record_time DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'short_count': row[0],
                'short_change': row[1],
                'long_count': row[2],
                'long_change': row[3],
                'record_time': row[4],
                'folder_date': row[5]
            }
    except Exception as e:
        print(f"查询数据失败: {e}")
    return None

def get_signal_history_from_db(start_datetime, end_datetime):
    """从数据库查询历史信号数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT short_count, short_change, long_count, long_change, 
                   record_time, folder_date
            FROM signal_data
            WHERE record_time >= ? AND record_time <= ?
            ORDER BY record_time ASC
        ''', (start_datetime, end_datetime))
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signals.append({
                'short_count': row[0],
                'short_change': row[1],
                'long_count': row[2],
                'long_change': row[3],
                'record_time': row[4],
                'folder_date': row[5]
            })
        
        return signals
    except Exception as e:
        print(f"查询历史数据失败: {e}")
        return []

@app.route('/api/signal-monitor/latest')
def get_latest_signal():
    """获取最新信号数据"""
    try:
        today_folder = get_today_folder_name()
        beijing_time = get_beijing_time()
        
        # 从数据库获取最新数据
        latest_data = get_latest_signal_from_db()
        
        if latest_data:
            return jsonify({
                'success': True,
                'current_folder': today_folder,
                'current_time': beijing_time.strftime('%Y-%m-%d %H:%M:%S'),
                'data': latest_data
            })
        else:
            return jsonify({
                'success': True,
                'current_folder': today_folder,
                'current_time': beijing_time.strftime('%Y-%m-%d %H:%M:%S'),
                'message': '暂无数据，请等待数据采集',
                'data': {
                    'short_count': 0,
                    'short_change': 0,
                    'long_count': 0,
                    'long_change': 0,
                    'record_time': beijing_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'folder_date': today_folder
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/signal-monitor/history')
def get_signal_history():
    """获取历史信号数据"""
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
        
        # 构造完整的日期时间字符串
        start_datetime = f"{start_date} {start_time}"
        end_datetime = f"{end_date} {end_time}"
        
        # 从数据库查询历史数据
        history_data = get_signal_history_from_db(start_datetime, end_datetime)
        
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

@app.route('/api/signal-monitor/stats')
def get_signal_stats():
    """获取信号统计数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute('SELECT COUNT(*) FROM signal_data')
        total_count = cursor.fetchone()[0]
        
        # 获取日期范围
        cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM signal_data')
        date_range = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_records': total_count,
            'date_range': {
                'start': date_range[0] if date_range[0] else None,
                'end': date_range[1] if date_range[1] else None
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/signal-monitor/test')
def test_api():
    """测试API连接"""
    beijing_time = get_beijing_time()
    today_folder = get_today_folder_name()
    
    return jsonify({
        'success': True,
        'message': 'API连接正常',
        'beijing_time': beijing_time.strftime('%Y-%m-%d %H:%M:%S'),
        'today_folder': today_folder,
        'drive_folder_id': GOOGLE_DRIVE_FOLDER_ID
    })

if __name__ == '__main__':
    # 初始化数据库
    init_database()
    
    print("="*70)
    print("虚拟币系统信号监控 API")
    print("="*70)
    print(f"启动时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"数据库: {DB_PATH}")
    print(f"Google Drive Folder ID: {GOOGLE_DRIVE_FOLDER_ID}")
    print(f"今天文件夹: {get_today_folder_name()}")
    print("="*70)
    print("\nAPI 端点:")
    print("  GET  /api/signal-monitor/latest   - 获取最新信号")
    print("  GET  /api/signal-monitor/history  - 获取历史信号")
    print("  GET  /api/signal-monitor/stats    - 获取统计信息")
    print("  GET  /api/signal-monitor/test     - 测试API")
    print("="*70)
    
    app.run(host='0.0.0.0', port=5003, debug=False)
