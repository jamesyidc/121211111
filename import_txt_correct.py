#!/usr/bin/env python3
"""
正确的TXT数据导入脚本 - 根据用户提供的精确映射
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
    解析TXT文件内容 - 使用正确的字段映射
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
    
    # Extract summary data with CORRECT mapping
    summary = {}
    
    # 急涨: "急涨：14" → 14
    rush_up_text = labels.get('急涨总和', '')
    if '：' in rush_up_text:
        summary['rush_up_total'] = int(rush_up_text.split('：')[1])
    
    # 急跌: "急跌：18" → 18
    rush_down_text = labels.get('急跌总和', '')
    if '：' in rush_down_text:
        summary['rush_down_total'] = int(rush_down_text.split('：')[1])
    
    # 状态: "状态：震荡无序" → 震荡无序
    status_text = labels.get('五种状态', '')
    if '：' in status_text:
        summary['status'] = status_text.split('：')[1]
    
    # 比值: "比值：0.29" → 0.29
    ratio_text = labels.get('急涨急跌比值', '')
    if '：' in ratio_text:
        summary['ratio'] = float(ratio_text.split('：')[1])
    
    # 计次: "3" → 3
    summary['count'] = int(labels.get('计次', '0'))
    
    # 差值: "差值：-4" → -4
    diff_text = labels.get('差值结果', '')
    if '：' in diff_text:
        summary['diff'] = int(diff_text.split('：')[1].strip())
    
    # 比价最低: "比价最低 0 0" → 取第2个数字 = 0
    position_lowest_label = labels.get('比价最低得分', '')
    if '比价最低' in position_lowest_label:
        parts = position_lowest_label.split()
        if len(parts) >= 3:
            summary['position_lowest'] = int(parts[2])  # 第3个数字
        else:
            summary['position_lowest'] = 0
    
    # 比价创新高: "比价创新高 仓位加10% 1" → 取最后一个数字 = 1
    position_score_label = labels.get('仓位得分', '')
    if '比价创新高' in position_score_label:
        parts = position_score_label.split()
        if len(parts) >= 3:
            summary['position_newhigh'] = int(parts[-1])  # 最后一个数字
        else:
            summary['position_newhigh'] = 0
    elif '比价最低' in position_score_label:
        summary['position_newhigh'] = 0
    
    # Parse coin data
    coins = []
    data_started = False
    
    for line in lines:
        line = line.strip()
        
        if '[超级列表框_首页开始]' in line:
            data_started = True
            continue
        
        if '[超级列表框_首页结束]' in line:
            break
        
        if not data_started or not line or line.startswith('#') or line.startswith('透明标签'):
            continue
        
        parts = line.split('|')
        if len(parts) >= 15:  # 去掉+4%和-3%后是15个字段
            try:
                # 字段映射（去掉了字段10和11的+4%和-3%）：
                # 0:序号 1:币名 2:急涨 3:急跌 4:更新时间 5:历史高位 6:高位时间
                # 7:距离高位跌幅 8:24涨幅 9:排行 10:当前价格 11:最高占比 12:最低占比
                
                coin = {
                    'rank': int(parts[0]),
                    'coin_symbol': parts[1].strip(),
                    'rush_up': int(parts[2].strip()),  # 字段2: 急涨
                    'rush_down': int(parts[3].strip()),  # 字段3: 急跌
                    'update_time': parts[4].strip(),
                    'current_price': float(parts[5].strip()),
                    'high_time': parts[6].strip(),
                    'decline_from_high': float(parts[7].strip()),
                    'change_24h': float(parts[8].strip()),
                    # parts[9] 和 parts[10] 是空的（原+4%和-3%列）
                    'ranking': int(parts[11].strip()),
                    'historical_high': float(parts[12].strip()),
                    'max_ratio': float(parts[13].strip().replace('%', '')),
                    'min_ratio': float(parts[14].strip().replace('%', '').replace('\r', ''))
                }
                
                # Calculate priority
                coin['priority_level'] = calculate_priority(coin['max_ratio'], coin['min_ratio'])
                
                coins.append(coin)
            except Exception as e:
                print(f"⚠️  解析币种数据失败: {e}, line: {line}")
                continue
    
    # Get snapshot_time from first coin
    if coins:
        snapshot_time = coins[0]['update_time']
        summary['snapshot_time'] = snapshot_time
        
        # Calculate count score
        dt = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S')
        summary['count_score'] = calculate_count_score(dt.hour, summary['count'])
        
        # 本轮急涨/本轮急跌: 从币种数据的字段2和3汇总
        summary['round_rush_up'] = sum(c['rush_up'] for c in coins)
        summary['round_rush_down'] = sum(c['rush_down'] for c in coins)
        
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
             count, count_score, position_lowest, position_newhigh, diff,
             rise_24h_count, fall_24h_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary.get('snapshot_time'),
            summary.get('rush_up_total'),
            summary.get('rush_down_total'),
            summary.get('status'),
            summary.get('ratio'),
            summary.get('count'),
            summary.get('count_score'),
            summary.get('position_lowest'),
            summary.get('position_newhigh'),
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
    print(f"\n{'='*100}")
    print(f"📥 正在导入: {filename}")
    print(f"{'='*100}")
    
    try:
        # Download
        content = download_file(file_id)
        print(f"✅ 下载成功: {len(content)} 字节")
        
        # Parse
        summary, coins = parse_txt_content(content)
        print(f"✅ 解析成功: 汇总数据 + {len(coins)} 种币")
        
        # Show summary
        print(f"\n【汇总数据】")
        print(f"  运算时间: {summary.get('snapshot_time')}")
        print(f"  急涨: {summary.get('rush_up_total')}")
        print(f"  急跌: {summary.get('rush_down_total')}")
        print(f"  本轮急涨: {summary.get('round_rush_up')}")
        print(f"  本轮急跌: {summary.get('round_rush_down')}")
        print(f"  计次: {summary.get('count')}")
        print(f"  计次得分: {summary.get('count_score')}")
        print(f"  状态: {summary.get('status')}")
        print(f"  比值: {summary.get('ratio')}")
        print(f"  差值: {summary.get('diff')}")
        print(f"  比价最低: {summary.get('position_lowest')}")
        print(f"  比价创新高: {summary.get('position_newhigh')}")
        print(f"  24h涨≥10%: {summary.get('rise_24h_count')}")
        print(f"  24h跌≤-10%: {summary.get('fall_24h_count')}")
        
        # Import
        success, error = import_to_database(summary, coins)
        if success:
            print(f"\n✅ 导入成功!")
            return True
        else:
            print(f"\n❌ 导入失败: {error}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test with the example you provided (16:38 data)
    # You need to provide the file_id
    print("请提供文件ID以测试导入")
