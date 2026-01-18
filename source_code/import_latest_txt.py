#!/usr/bin/env python3
"""
导入最新TXT文件到数据库 - 独立功能模块

功能：
1. 从Google Drive下载最新TXT文件
2. 解析文件内容
3. 导入到数据库

使用方法：
    python3 import_latest_txt.py
"""

import requests
import re
import sqlite3
from datetime import datetime
import pytz
import sys

# 配置
GOOGLE_DRIVE_FILE_ID = "1eyYiU6lU8n7SwWUvFtm_kUIvaZI0SO4U"
DB_PATH = '/home/user/webapp/crypto_data.db'
TIMEZONE = pytz.timezone('Asia/Shanghai')

def download_file():
    """下载文件"""
    print("正在下载Google Drive文件...")
    
    url = f"https://drive.google.com/uc?export=download&id={GOOGLE_DRIVE_FILE_ID}"
    headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            print(f"✓ 下载成功 ({len(response.content)} 字节)")
            return response.text
        else:
            print(f"✗ 下载失败: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ 下载异常: {e}")
        return None

def parse_data(content):
    """解析数据"""
    print("正在解析数据...")
    
    try:
        # 提取时间戳
        timestamps = re.findall(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})', content)
        if not timestamps:
            print("✗ 未找到时间戳")
            return None
        
        date_str, time_str = timestamps[0]
        hour = int(time_str.split(':')[0])
        minute = int(time_str.split(':')[1])
        snapshot_time = f"{date_str} {hour:02d}:{minute:02d}:00"
        
        # 提取数据
        rush_up = int(re.search(r'急涨：(\d+)', content).group(1))
        rush_down = int(re.search(r'急跌：(\d+)', content).group(1))
        count = int(re.search(r'透明标签_计次=(\d+)', content).group(1))
        status_match = re.search(r'透明标签_五种状态=(.+)', content)
        status = status_match.group(1).strip().replace('状态：', '').split('\r')[0] if status_match else '未知'
        
        # 计算计次得分
        if hour >= 18:
            if count <= 3:
                count_score_display = "★★★★★"
            elif count <= 5:
                count_score_display = "★★★★"
            elif count <= 8:
                count_score_display = "★★★"
            elif count <= 12:
                count_score_display = "★★"
            elif count <= 20:
                count_score_display = "★"
            else:
                count_score_display = "---"
        else:
            if count <= 10:
                count_score_display = "☆---"
            elif count <= 20:
                count_score_display = "☆☆"
            elif count <= 30:
                count_score_display = "☆☆☆"
            else:
                count_score_display = "---"
        
        data = {
            'snapshot_time': snapshot_time,
            'snapshot_date': date_str,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'count': count,
            'count_score_display': count_score_display,
            'status': status
        }
        
        print(f"✓ 解析成功:")
        print(f"  时间: {snapshot_time}")
        print(f"  急涨/急跌: {rush_up}/{rush_down}")
        print(f"  计次: {count} {count_score_display}")
        print(f"  状态: {status}")
        
        return data
        
    except Exception as e:
        print(f"✗ 解析失败: {e}")
        return None

def import_to_db(data):
    """导入到数据库"""
    print("\n正在导入数据库...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM crypto_snapshots WHERE snapshot_time = ?",
            (data['snapshot_time'],)
        )
        existing = cursor.fetchone()
        
        if existing:
            # 更新
            cursor.execute("""
                UPDATE crypto_snapshots SET
                    rush_up = ?, rush_down = ?,
                    count = ?, count_score_display = ?,
                    status = ?
                WHERE snapshot_time = ?
            """, (
                data['rush_up'], data['rush_down'],
                data['count'], data['count_score_display'],
                data['status'], data['snapshot_time']
            ))
            print(f"✓ 更新现有记录: {data['snapshot_time']}")
        else:
            # 插入
            cursor.execute("""
                INSERT INTO crypto_snapshots 
                (snapshot_time, snapshot_date, rush_up, rush_down, 
                 count, count_score_display, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data['snapshot_time'], data['snapshot_date'],
                data['rush_up'], data['rush_down'],
                data['count'], data['count_score_display'],
                data['status']
            ))
            print(f"✓ 插入新记录: {data['snapshot_time']}")
        
        conn.commit()
        conn.close()
        
        print("✓ 数据库操作成功")
        return True
        
    except Exception as e:
        print(f"✗ 数据库操作失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print("导入最新TXT文件")
    print("=" * 80)
    
    # 1. 下载
    content = download_file()
    if not content:
        print("\n❌ 导入失败: 无法下载文件")
        sys.exit(1)
    
    # 2. 解析
    data = parse_data(content)
    if not data:
        print("\n❌ 导入失败: 无法解析数据")
        sys.exit(1)
    
    # 3. 导入
    success = import_to_db(data)
    
    if success:
        print("\n" + "=" * 80)
        print("✅ 导入完成!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n❌ 导入失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
