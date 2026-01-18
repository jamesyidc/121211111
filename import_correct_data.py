#!/usr/bin/env python3
"""
正确的Google Drive TXT数据导入脚本
根据用户需求的正确数据结构导入
"""

import requests
import sqlite3
import re
from datetime import datetime

DB_PATH = '/home/user/webapp/databases/crypto_data.db'

def calculate_priority(max_ratio, min_ratio):
    """
    计算优先级等级
    等级1: 最高占比>90, 最低占比>120
    等级2: 最高占比>80, 最低占比>120
    等级3: 最高占比>90, 最低占比>110
    等级4: 最高占比>70, 最低占比>120
    等级5: 最高占比>80, 最低占比>110
    等级6: 其他
    """
    if max_ratio > 90 and min_ratio > 120:
        return 1
    elif max_ratio > 80 and min_ratio > 120:
        return 2
    elif max_ratio > 90 and min_ratio > 110:
        return 3
    elif max_ratio > 70 and min_ratio > 120:
        return 4
    elif max_ratio > 80 and min_ratio > 110:
        return 5
    else:
        return 6

def calculate_count_score(hour, count):
    """
    计算计次得分
    根据时间段和计次数计算星级
    """
    if hour < 6:
        if count <= 1: return "3颗实心星"
        elif 1 < count <= 2: return "2颗实心星"
        elif 2 < count <= 3: return "1颗实心星"
        elif 3 < count <= 4: return "1颗空心星"
        elif 4 < count <= 5: return "2颗空心星"
        else: return "3颗空心星"
    elif hour < 12:
        if count <= 2: return "3颗实心星"
        elif 2 < count <= 3: return "2颗实心星"
        elif 3 < count <= 4: return "1颗实心星"
        elif 5 < count <= 6: return "1颗空心星"
        elif 6 < count <= 7: return "2颗空心星"
        else: return "3颗空心星"
    elif hour < 18:
        if count <= 3: return "3颗实心星"
        elif 3 < count <= 4: return "2颗实心星"
        elif 4 < count <= 5: return "1颗实心星"
        elif 7 < count <= 8: return "1颗空心星"
        elif 8 < count <= 9: return "2颗空心星"
        else: return "3颗空心星"
    else:  # hour < 24
        if count <= 4: return "3颗实心星"
        elif 4 < count <= 5: return "2颗实心星"
        elif 5 < count <= 6: return "1颗实心星"
        elif 9 < count <= 10: return "1颗空心星"
        elif 10 < count <= 11: return "2颗空心星"
        else: return "3颗空心星"

def download_file(file_id):
    """下载Google Drive文件"""
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(download_url, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Download failed: HTTP {response.status_code}")
    return response.text

def parse_txt_content(content):
    """
    解析TXT文件内容
    返回: (summary_data, coins_data)
    """
    lines = content.strip().split('\n')
    
    # Parse header labels
    labels = {}
    for line in lines:
        line = line.strip()
        if line.startswith('透明标签_'):
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].replace('透明标签_', '')
                value = parts[1].strip()
                labels[key] = value
    
    # Extract summary data
    summary = {}
    
    # 急涨总和: "急涨：14"
    rush_up_text = labels.get('急涨总和', '')
    if '：' in rush_up_text:
        summary['rush_up_total'] = int(rush_up_text.split('：')[1])
    
    # 急跌总和: "急跌：17"
    rush_down_text = labels.get('急跌总和', '')
    if '：' in rush_down_text:
        summary['rush_down_total'] = int(rush_down_text.split('：')[1])
    
    # 状态: "状态：震荡无序"
    status_text = labels.get('五种状态', '')
    if '：' in status_text:
        summary['status'] = status_text.split('：')[1]
    
    # 比值: "比值：0.21"
    ratio_text = labels.get('急涨急跌比值', '')
    if '：' in ratio_text:
        summary['ratio'] = float(ratio_text.split('：')[1])
    
    # 绿色数量
    summary['green_count'] = int(labels.get('绿色数量', '0'))
    
    # 百分比: "31%"
    percentage_text = labels.get('百分比', '0%')
    summary['percentage'] = float(percentage_text.replace('%', ''))
    
    # 计次
    summary['count'] = int(labels.get('计次', '0'))
    
    # 差值: "差值：-3"
    diff_text = labels.get('差值结果', '')
    if '：' in diff_text:
        summary['diff'] = int(diff_text.split('：')[1].strip())
    
    # 仓位得分: "比价创新高 仓位加30% 8" or "比价最低 0 0"
    position_score = labels.get('仓位得分', '')
    summary['position_score_type'] = None
    summary['position_lowest'] = 0
    summary['position_newhigh'] = 0
    summary['position_percentage'] = None
    
    if '比价最低' in position_score:
        summary['position_score_type'] = '比价最低'
        parts = position_score.split()
        if len(parts) >= 3:
            summary['position_lowest'] = int(parts[1])
    elif '比价创新高' in position_score:
        summary['position_score_type'] = '比价创新高'
        parts = position_score.split()
        if len(parts) >= 3:
            summary['position_percentage'] = parts[1]  # "仓位加30%"
            summary['position_newhigh'] = int(parts[2])
    
    # Parse coin data
    coins = []
    data_started = False
    
    for line in lines:
        line = line.strip()
        
        if '[超级列表框_首页开始]' in line:
            data_started = True
            continue
        
        if not data_started or not line or line.startswith('#') or line.startswith('透明标签'):
            continue
        
        parts = line.split('|')
        if len(parts) >= 16:
            try:
                coin = {
                    'rank': int(parts[0]),
                    'coin_symbol': parts[1].strip(),
                    'change_24h': float(parts[2].strip()),
                    'rush_up': int(parts[3].strip()),
                    'rush_down': int(parts[4].strip()),
                    'update_time': parts[5].strip(),
                    'current_price': float(parts[6].strip()),
                    'high_time': parts[7].strip(),
                    'decline_from_high': float(parts[8].strip()),
                    'unknown_field': float(parts[9].strip()) if parts[9].strip() else None,
                    # parts[10] and parts[11] are empty (removed +4%, -3%)
                    'ranking': int(parts[12].strip()),
                    'historical_high': float(parts[13].strip()),
                    'max_ratio': float(parts[14].strip().replace('%', '')),
                    'min_ratio': float(parts[15].strip().replace('%', ''))
                }
                
                # Calculate priority
                coin['priority_level'] = calculate_priority(coin['max_ratio'], coin['min_ratio'])
                
                coins.append(coin)
            except Exception as e:
                print(f"⚠️  解析币种数据失败: {e}")
                continue
    
    # Get snapshot_time from first coin
    if coins:
        snapshot_time = coins[0]['update_time']
        summary['snapshot_time'] = snapshot_time
        
        # Calculate count score
        dt = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S')
        summary['count_score'] = calculate_count_score(dt.hour, summary['count'])
        
        # Calculate 24h rise/fall counts
        rise_count = sum(1 for c in coins if c['change_24h'] >= 10)
        fall_count = sum(1 for c in coins if c['change_24h'] <= -10)
        summary['rise_24h_count'] = rise_count
        summary['fall_24h_count'] = fall_count
    
    return summary, coins

def import_to_database(summary, coins):
    """导入数据到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Import summary data
        cursor.execute('''
            INSERT OR REPLACE INTO crypto_summary 
            (snapshot_time, rush_up_total, rush_down_total, status, ratio, 
             green_count, percentage, count, count_score, position_lowest, 
             position_newhigh, position_score_type, position_percentage, diff,
             rise_24h_count, fall_24h_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary.get('snapshot_time'),
            summary.get('rush_up_total'),
            summary.get('rush_down_total'),
            summary.get('status'),
            summary.get('ratio'),
            summary.get('green_count'),
            summary.get('percentage'),
            summary.get('count'),
            summary.get('count_score'),
            summary.get('position_lowest'),
            summary.get('position_newhigh'),
            summary.get('position_score_type'),
            summary.get('position_percentage'),
            summary.get('diff'),
            summary.get('rise_24h_count'),
            summary.get('fall_24h_count')
        ))
        
        # Import coin details
        for coin in coins:
            cursor.execute('''
                INSERT OR REPLACE INTO crypto_coin_detail
                (snapshot_time, priority_level, coin_symbol, rush_up, rush_down,
                 update_time, historical_high, high_time, decline_from_high,
                 change_24h, ranking, current_price, max_ratio, min_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary.get('snapshot_time'),
                coin['priority_level'],
                coin['coin_symbol'],
                coin['rush_up'],
                coin['rush_down'],
                coin['update_time'],
                coin['historical_high'],
                coin['high_time'],
                coin['decline_from_high'],
                coin['change_24h'],
                coin['ranking'],
                coin['current_price'],
                coin['max_ratio'],
                coin['min_ratio']
            ))
        
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def import_file(file_id, filename):
    """导入单个文件"""
    print(f"\n{'='*80}")
    print(f"📥 正在导入: {filename}")
    print(f"{'='*80}")
    
    try:
        # Download
        content = download_file(file_id)
        print(f"✅ 下载成功: {len(content)} 字节")
        
        # Parse
        summary, coins = parse_txt_content(content)
        print(f"✅ 解析成功: 汇总数据 + {len(coins)} 种币")
        
        # Import
        success, error = import_to_database(summary, coins)
        if success:
            print(f"✅ 导入成功!")
            print(f"   时间: {summary.get('snapshot_time')}")
            print(f"   急涨: {summary.get('rush_up_total')}, 急跌: {summary.get('rush_down_total')}")
            print(f"   状态: {summary.get('status')}, 计次: {summary.get('count')}")
            print(f"   币种数: {len(coins)}")
            return True
        else:
            print(f"❌ 导入失败: {error}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    # Test with 15:58 file
    file_id = "1TUNDwsDyvmnZEJ3tX6CHA5WIj_T3Lk4Q"
    filename = "2026-01-05_1558.txt"
    
    success = import_file(file_id, filename)
    
    if success:
        print("\n" + "="*80)
        print("🎉 15:58 数据导入完成!")
        print("="*80)
