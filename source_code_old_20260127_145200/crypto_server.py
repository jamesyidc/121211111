#!/usr/bin/env python3
"""
加密货币数据服务器
定期从Google Drive获取最新txt文件并解析数据
提供API接口给前端页面
"""

import os
import sys
import re
import json
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import io

# 配置
MAIN_FOLDER_ID = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

app = Flask(__name__, static_folder='.')
CORS(app)

# 缓存数据
cached_data = {
    'data': [],
    'stats': {},
    'updateTime': None,
    'lastFetch': None
}

def get_beijing_date():
    """获取北京时间的今天日期"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    beijing_time = datetime.now(beijing_tz)
    return beijing_time.strftime('%Y-%m-%d')

def get_drive_service():
    """创建Google Drive API服务"""
    credentials_file = 'credentials.json'
    if not os.path.exists(credentials_file):
        print(f"错误: 未找到 {credentials_file}")
        return None
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"创建Drive服务失败: {e}")
        return None

def find_folder_by_name(service, parent_folder_id, folder_name):
    """查找指定名称的文件夹"""
    try:
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)', pageSize=10).execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None
    except HttpError as error:
        print(f"API错误: {error}")
        return None

def parse_filename_timestamp(filename):
    """从文件名解析时间戳: YYYY-MM-DD_HHMM.txt"""
    pattern = r'(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})\.txt'
    match = re.match(pattern, filename)
    if match:
        year, month, day, hour, minute = match.groups()
        try:
            dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
            beijing_tz = pytz.timezone('Asia/Shanghai')
            return beijing_tz.localize(dt)
        except ValueError:
            return None
    return None

def list_txt_files(service, folder_id):
    """列出文件夹中的所有txt文件"""
    try:
        query = f"'{folder_id}' in parents and trashed=false and name contains '.txt'"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=100
        ).execute()
        files = results.get('files', [])
        return [f for f in files if f['name'].endswith('.txt')]
    except HttpError as error:
        print(f"API错误: {error}")
        return []

def get_latest_txt_file(service, folder_id):
    """获取最新的txt文件"""
    files = list_txt_files(service, folder_id)
    if not files:
        return None
    
    files_with_time = []
    for file in files:
        timestamp = parse_filename_timestamp(file['name'])
        if timestamp:
            files_with_time.append((file, timestamp))
    
    if not files_with_time:
        return None
    
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    return files_with_time[0][0]

def download_file_content(service, file_id):
    """下载文件内容"""
    try:
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        
        from googleapiclient.http import MediaIoBaseDownload
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_content.seek(0)
        return file_content.read().decode('utf-8')
    except Exception as e:
        print(f"下载文件失败: {e}")
        return None

def parse_txt_content(content):
    """解析txt文件内容"""
    lines = content.strip().split('\n')
    
    # 解析统计数据（从透明标签开始）
    stats = {}
    data_lines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('透明标签_'):
            # 解析统计标签
            parts = line.split('=')
            if len(parts) == 2:
                key = parts[0].replace('透明标签_', '')
                value = parts[1]
                stats[key] = value
        elif line.startswith('[超级列表框_首页开始]'):
            continue
        elif line.startswith('[超级列表框_首页结束]'):
            break
        elif line and not line.startswith('透明标签_') and not line.startswith('['):
            # 数据行
            data_lines.append(line)
    
    # 解析数据行
    parsed_data = []
    for line in data_lines:
        parts = line.split('|')
        if len(parts) >= 15:
            try:
                row = {
                    'index': parts[0],
                    'symbol': parts[1],
                    'change': parts[2],
                    'rushUp': parts[3],
                    'rushDown': parts[4],
                    'updateTime': parts[5],
                    'highPrice': parts[6],
                    'highTime': parts[7],
                    'decline': parts[8],
                    'change24h': parts[9],
                    'col10': parts[10] if len(parts) > 10 else '',
                    'col11': parts[11] if len(parts) > 11 else '',
                    'col12': parts[12] if len(parts) > 12 else '',
                    'rank': parts[13] if len(parts) > 13 else '',
                    'currentPrice': parts[14] if len(parts) > 14 else '',
                    'ratio1': parts[15] if len(parts) > 15 else '',
                    'ratio2': parts[16] if len(parts) > 16 else ''
                }
                parsed_data.append(row)
            except Exception as e:
                print(f"解析行失败: {line}, 错误: {e}")
                continue
    
    return parsed_data, stats

def load_history_data():
    """加载当天所有历史txt文件，补全图表数据"""
    print(f"[{datetime.now()}] 开始加载历史数据...")
    
    service = get_drive_service()
    if not service:
        return []
    
    beijing_date = get_beijing_date()
    folder_id = find_folder_by_name(service, MAIN_FOLDER_ID, beijing_date)
    
    if not folder_id:
        print(f"未找到今天的文件夹: {beijing_date}")
        return []
    
    # 获取所有txt文件
    all_files = list_txt_files(service, folder_id)
    if not all_files:
        print("未找到txt文件")
        return []
    
    # 按文件名排序（时间从早到晚）
    files_with_time = []
    for file in all_files:
        timestamp = parse_filename_timestamp(file['name'])
        if timestamp:
            files_with_time.append((file, timestamp))
    
    files_with_time.sort(key=lambda x: x[1])
    
    print(f"找到 {len(files_with_time)} 个历史文件")
    
    # 解析每个文件，提取统计数据
    history_stats = []
    for file, timestamp in files_with_time:
        try:
            content = download_file_content(service, file['id'])
            if content:
                _, stats = parse_txt_content(content)
                
                # 提取时间（小时:分钟）
                time_str = timestamp.strftime('%H:%M')
                
                history_stats.append({
                    'time': time_str,
                    'timestamp': timestamp.isoformat(),
                    'rushUp': stats.get('急涨总和', '').replace('急涨：', '').strip(),
                    'rushDown': stats.get('急跌总和', '').replace('急跌：', '').strip()
                })
                
                print(f"  加载: {file['name']} -> 急涨:{history_stats[-1]['rushUp']}, 急跌:{history_stats[-1]['rushDown']}")
        except Exception as e:
            print(f"  解析文件失败: {file['name']}, 错误: {e}")
            continue
    
    print(f"成功加载 {len(history_stats)} 个历史数据点")
    return history_stats

def fetch_latest_data():
    """获取最新数据"""
    print(f"[{datetime.now()}] 开始获取最新数据...")
    
    service = get_drive_service()
    if not service:
        print("无法创建Drive服务")
        return False
    
    beijing_date = get_beijing_date()
    print(f"查找文件夹: {beijing_date}")
    
    folder_id = find_folder_by_name(service, MAIN_FOLDER_ID, beijing_date)
    if not folder_id:
        print(f"未找到文件夹: {beijing_date}")
        return False
    
    print(f"找到文件夹: {folder_id}")
    
    latest_file = get_latest_txt_file(service, folder_id)
    if not latest_file:
        print("未找到txt文件")
        return False
    
    print(f"找到最新文件: {latest_file['name']}")
    
    content = download_file_content(service, latest_file['id'])
    if not content:
        print("下载文件内容失败")
        return False
    
    print(f"文件内容长度: {len(content)} 字节")
    
    # 解析内容
    data, stats = parse_txt_content(content)
    
    print(f"解析到 {len(data)} 条数据")
    
    # 更新缓存
    cached_data['data'] = data
    cached_data['stats'] = {
        'rushUp': stats.get('急涨总和', '').replace('急涨：', ''),
        'rushDown': stats.get('急跌总和', '').replace('急跌：', ''),
        'status': stats.get('五种状态', '').replace('状态：', ''),
        'ratio': stats.get('急涨急跌比值', '').replace('比值：', '').replace(' ★★', ''),
        'greenCount': stats.get('绿色数量', ''),
        'percentage': stats.get('百分比', ''),
        'count': stats.get('计次', ''),
        'diff': stats.get('差值结果', '').replace('差值：', '').replace(' ★★', '')
    }
    cached_data['updateTime'] = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
    cached_data['lastFetch'] = datetime.now()
    cached_data['filename'] = latest_file['name']
    
    print(f"[{datetime.now()}] 数据更新成功")
    return True

@app.route('/')
def index():
    """首页"""
    return send_from_directory('.', 'crypto_dashboard.html')

@app.route('/api/crypto-data')
def get_crypto_data():
    """获取加密货币数据API"""
    # 如果缓存为空或超过10分钟，重新获取
    if not cached_data['data'] or not cached_data['lastFetch'] or \
       (datetime.now() - cached_data['lastFetch']).total_seconds() > 600:
        fetch_latest_data()
    
    return jsonify({
        'success': True,
        'data': cached_data['data'],
        'stats': cached_data['stats'],
        'updateTime': cached_data['updateTime'],
        'filename': cached_data.get('filename', '')
    })

@app.route('/api/history-chart')
def get_history_chart():
    """获取历史图表数据API"""
    history = load_history_data()
    return jsonify({
        'success': True,
        'history': history
    })

@app.route('/api/refresh')
def refresh_data():
    """手动刷新数据"""
    success = fetch_latest_data()
    return jsonify({
        'success': success,
        'message': '数据刷新成功' if success else '数据刷新失败'
    })

if __name__ == '__main__':
    print("=" * 80)
    print("加密货币数据监控服务器")
    print("=" * 80)
    print(f"启动时间: {datetime.now()}")
    print(f"监控文件夹: {MAIN_FOLDER_ID}")
    print("=" * 80)
    
    # 启动时先获取一次数据
    fetch_latest_data()
    
    # 启动服务器
    port = 5000
    print(f"\n服务器运行在: http://0.0.0.0:{port}")
    print(f"访问页面: http://0.0.0.0:{port}/")
    print(f"API接口: http://0.0.0.0:{port}/api/crypto-data")
    print(f"手动刷新: http://0.0.0.0:{port}/api/refresh")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
