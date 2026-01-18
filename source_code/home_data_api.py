#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页数据API
"""

from flask import Flask, jsonify, send_file
import asyncio
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

def parse_home_data(content):
    """解析首页数据内容"""
    lines = content.strip().split('\n')
    
    stats = {}
    coins = []
    
    in_coin_section = False
    
    for line in lines:
        line = line.strip()
        
        # 解析统计数据
        if line.startswith('透明标签_'):
            parts = line.split('=')
            if len(parts) == 2:
                key = parts[0].replace('透明标签_', '')
                value = parts[1]
                
                if '急涨总和' in key:
                    stats['rushUp'] = value.split('：')[1] if '：' in value else value
                elif '急跌总和' in key:
                    stats['rushDown'] = value.split('：')[1] if '：' in value else value
                elif '五种状态' in key:
                    stats['status'] = value.split('：')[1] if '：' in value else value
                elif '急涨急跌比值' in key:
                    stats['ratio'] = value.split('：')[1] if '：' in value else value
                elif '绿色数量' in key:
                    stats['greenCount'] = value
                elif '百分比' in key:
                    stats['percentage'] = value
        
        # 币种数据
        if '[超级列表框_首页开始]' in line:
            in_coin_section = True
            continue
        
        if '[超级列表框_首页结束]' in line:
            break
        
        if in_coin_section and '|' in line:
            parts = line.split('|')
            if len(parts) >= 16:
                coin = {
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
                    'rank': parts[12],
                    'currentPrice': parts[13],
                    'ratio1': parts[14],
                    'ratio2': parts[15]
                }
                coins.append(coin)
    
    # 获取更新时间（从第一个币种的时间）
    update_time = coins[0]['updateTime'] if coins else ''
    
    return {
        'stats': stats,
        'coins': coins,
        'updateTime': update_time
    }

@app.route('/')
def index():
    """首页"""
    return send_file('crypto_home.html')

@app.route('/api/home-data')
def get_home_data():
    """获取首页数据API"""
    try:
        # 导入读取器
        from gdrive_home_data_reader import get_latest_file_by_sorting
        
        # 获取最新数据
        result = asyncio.run(get_latest_file_by_sorting())
        
        if not result or not result.get('content'):
            return jsonify({
                'success': False,
                'error': '无法获取数据'
            }), 500
        
        # 解析数据
        parsed_data = parse_home_data(result['content'])
        
        return jsonify({
            'success': True,
            'data': parsed_data,
            'filename': result['filename'],
            'time_diff': result['time_diff']
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
    print("首页数据监控服务器")
    print("="*60)
    print("访问: http://0.0.0.0:5002/")
    print("="*60)
    app.run(host='0.0.0.0', port=5002, debug=False)
