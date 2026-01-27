#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据接收器 - 接收txt文件内容并保存到数据库
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
CORS(app)

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = 'homepage_data.db'


def parse_summary_line(line):
    """解析汇总数据行"""
    try:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 12:
            def safe_int(s):
                try:
                    return int(s) if s and s.strip() else 0
                except:
                    return 0
            
            def safe_float(s):
                try:
                    return float(s) if s and s.strip() else 0.0
                except:
                    return 0.0
            
            return {
                'rise_total': safe_int(parts[0]),
                'fall_total': safe_int(parts[1]),
                'five_states': parts[2] if len(parts) > 2 else '',
                'rise_fall_ratio': safe_float(parts[3]),
                'green_count': safe_int(parts[4]),
                'green_percent': safe_float(parts[5]),
                'count_times': safe_int(parts[6]),
                'all_green_score': safe_float(parts[7]),
                'price_lowest_score': safe_float(parts[8]),
                'price_new_high': safe_int(parts[9]),
                'fall_count': safe_int(parts[10]),
                'diff_result': safe_float(parts[11])
            }
    except Exception as e:
        print(f"解析汇总行失败: {e}")
    return None


def parse_coin_line(line):
    """解析币种详情行"""
    try:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 16:
            def safe_int(s):
                try:
                    return int(s) if s and s.strip() else 0
                except:
                    return 0
            
            def safe_float(s):
                try:
                    return float(s) if s and s.strip() else 0.0
                except:
                    return 0.0
            
            return {
                'seq_num': safe_int(parts[0]),
                'coin_name': parts[1] if len(parts) > 1 else '',
                'rise_speed': safe_float(parts[2]),
                'rise_signal': safe_int(parts[3]),
                'fall_signal': safe_int(parts[4]),
                'update_time': parts[5] if len(parts) > 5 else '',
                'history_high': safe_float(parts[6]),
                'high_time': parts[7] if len(parts) > 7 else '',
                'drop_from_high': safe_float(parts[8]),
                'change_24h': safe_float(parts[9]),
                'plus_4_percent': safe_int(parts[10]),
                'minus_3_percent': safe_int(parts[11]),
                'ranking': safe_int(parts[12]),
                'current_price': safe_float(parts[13]),
                'high_ratio': safe_float(parts[14]),
                'low_ratio': safe_float(parts[15]),
                'anomaly': parts[16] if len(parts) > 16 else ''
            }
    except Exception as e:
        print(f"解析币种行失败: {e}")
    return None


def save_to_database(summary_data, coins_data, record_time):
    """保存数据到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 保存汇总数据
        cursor.execute('''
            INSERT OR REPLACE INTO summary_data 
            (rise_total, fall_total, five_states, rise_fall_ratio, green_count, 
             green_percent, count_times, all_green_score, price_lowest_score, 
             price_new_high, fall_count, diff_result, record_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary_data['rise_total'],
            summary_data['fall_total'],
            summary_data['five_states'],
            summary_data['rise_fall_ratio'],
            summary_data['green_count'],
            summary_data['green_percent'],
            summary_data['count_times'],
            summary_data['all_green_score'],
            summary_data['price_lowest_score'],
            summary_data['price_new_high'],
            summary_data['fall_count'],
            summary_data['diff_result'],
            record_time
        ))
        
        summary_id = cursor.lastrowid
        
        # 保存币种详情
        for coin in coins_data:
            cursor.execute('''
                INSERT INTO coin_details 
                (summary_id, seq_num, coin_name, rise_speed, rise_signal, fall_signal,
                 update_time, history_high, high_time, drop_from_high, change_24h,
                 plus_4_percent, minus_3_percent, ranking, current_price, 
                 high_ratio, low_ratio, anomaly, record_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary_id,
                coin['seq_num'],
                coin['coin_name'],
                coin['rise_speed'],
                coin['rise_signal'],
                coin['fall_signal'],
                coin['update_time'],
                coin['history_high'],
                coin['high_time'],
                coin['drop_from_high'],
                coin['change_24h'],
                coin['plus_4_percent'],
                coin['minus_3_percent'],
                coin['ranking'],
                coin['current_price'],
                coin['high_ratio'],
                coin['low_ratio'],
                coin['anomaly'],
                record_time
            ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"保存数据失败: {e}")
        return False


@app.route('/api/data/upload', methods=['POST'])
def upload_data():
    """接收txt文件内容"""
    try:
        data = request.json
        txt_content = data.get('content', '')
        
        if not txt_content:
            return jsonify({'success': False, 'message': '内容为空'})
        
        # 解析内容
        lines = txt_content.strip().split('\n')
        
        if len(lines) < 2:
            return jsonify({'success': False, 'message': '数据格式错误：行数不足'})
        
        # 第一行是汇总数据
        summary_data = parse_summary_line(lines[0])
        if not summary_data:
            return jsonify({'success': False, 'message': '解析汇总数据失败'})
        
        # 后续行是币种数据
        coins_data = []
        for line in lines[1:]:
            if line.strip():
                coin_data = parse_coin_line(line)
                if coin_data:
                    coins_data.append(coin_data)
        
        if len(coins_data) == 0:
            return jsonify({'success': False, 'message': '未解析到币种数据'})
        
        # 使用当前北京时间作为记录时间
        beijing_now = datetime.now(BEIJING_TZ)
        record_time = beijing_now.strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存到数据库
        if save_to_database(summary_data, coins_data, record_time):
            return jsonify({
                'success': True,
                'message': '数据保存成功',
                'record_time': record_time,
                'summary': summary_data,
                'coins_count': len(coins_data)
            })
        else:
            return jsonify({'success': False, 'message': '数据保存失败'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'错误: {str(e)}'})


@app.route('/api/data/test', methods=['GET'])
def test():
    """测试接口"""
    return jsonify({
        'success': True,
        'message': '数据接收器运行正常',
        'time': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    })


if __name__ == '__main__':
    print("="*70)
    print("数据接收器")
    print("="*70)
    print("监听端口: 5005")
    print("上传接口: POST /api/data/upload")
    print("  请求格式: {\"content\": \"txt文件内容...\"}")
    print("测试接口: GET /api/data/test")
    print("="*70)
    
    app.run(host='0.0.0.0', port=5005, debug=True)
