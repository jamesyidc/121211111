#!/usr/bin/env python3
"""
智能Google Drive TXT文件检测器
动态查找当天最新的TXT文件
"""
import requests
import re
import time
import sqlite3
from datetime import datetime
import pytz
import sys

# 配置
TODAY_FOLDER_ID = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"  # 直接使用今天的文件夹ID
CHECK_INTERVAL = 30  # 检测间隔（秒）
LOG_FILE = "/home/user/webapp/gdrive_smart_detector.log"
DB_PATH = "/home/user/webapp/crypto_data.db"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def log(message):
    """写入日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg, flush=True)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except:
        pass

def get_today_folder_id():
    """
    步骤1: 确认今天日期并返回文件夹ID
    """
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    log(f"📅 步骤1: 确认今天日期 = {today}")
    log(f"✅ 使用今天的文件夹ID: {TODAY_FOLDER_ID}")
    return TODAY_FOLDER_ID

def get_all_txt_files(folder_id):
    """
    步骤2-3: 进入文件夹，获取所有TXT文件名称和ID
    """
    log(f"📂 步骤2: 进入文件夹 {folder_id}")
    
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    
    try:
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 从HTML结构中提取文件名和ID
        # 格式: <div class="flip-entry" id="entry-FILE_ID">...文件名.txt...
        pattern = rf'id="entry-([^"]+)"[^>]*>.*?({today}_\d{{4}}\.txt)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        # 整理为(文件名, file_id)元组列表
        txt_files = [(filename, file_id) for file_id, filename in matches]
        
        log(f"📋 步骤3: 找到 {len(txt_files)} 个TXT文件")
        
        # 只记录前5个和后5个文件名（避免日志过长）
        if txt_files:
            sorted_files = sorted(txt_files, reverse=True)
            log(f"📝 最新5个文件:")
            for filename, file_id in sorted_files[:5]:
                log(f"   - {filename}")
            if len(txt_files) > 10:
                log(f"   ... 省略 {len(txt_files)-10} 个文件 ...")
            if len(txt_files) > 5:
                log(f"📝 最早5个文件:")
                for filename, file_id in sorted_files[-5:]:
                    log(f"   - {filename}")
        
        return txt_files
        
    except Exception as e:
        log(f"❌ 获取TXT文件列表失败: {e}")
        return []

def find_latest_txt(txt_files):
    """
    步骤4: 找到最新的TXT文件
    """
    if not txt_files:
        log("❌ 没有可用的TXT文件")
        return None, None
    
    log(f"🔍 步骤4: 从 {len(txt_files)} 个文件中找最新的")
    
    # 按文件名排序（格式: 2025-12-09_1234.txt）
    sorted_files = sorted(txt_files, key=lambda x: x[0], reverse=True)
    
    latest_filename, latest_file_id = sorted_files[0]
    log(f"✅ 最新文件: {latest_filename}")
    log(f"   文件ID: {latest_file_id}")
    
    return latest_filename, latest_file_id

def download_file_content(file_id):
    """下载文件内容"""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            log(f"❌ 下载失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        log(f"❌ 下载文件失败: {e}")
        return None

def parse_txt_content(content):
    """解析TXT文件内容"""
    try:
        # 提取时间戳
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})', content)
        if not timestamp_match:
            return None
        
        date_str, time_str = timestamp_match.groups()
        timestamp = f"{date_str} {time_str}"
        
        # 解析为datetime对象（只保留到分钟）
        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        snapshot_time = dt.strftime('%Y-%m-%d %H:%M:00')
        
        # 提取急涨急跌数据
        rush_up_match = re.search(r'本轮急涨.*?(\d+)/', content)
        rush_down_match = re.search(r'本轮急跌.*?(\d+)/', content)
        
        rush_up = int(rush_up_match.group(1)) if rush_up_match else 0
        rush_down = int(rush_down_match.group(1)) if rush_down_match else 0
        
        # 提取计次和状态
        count_match = re.search(r'计次[:：](\d+)', content)
        status_match = re.search(r'[★☆]+\s*\|\s*([^\n]+)', content)
        
        count = int(count_match.group(1)) if count_match else 0
        status = status_match.group(1).strip() if status_match else ""
        
        # 提取计次得分显示
        score_match = re.search(r'((?:[★☆])+(?:---)?)', content)
        count_score_display = score_match.group(1) if score_match else ""
        
        return {
            'snapshot_time': snapshot_time,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'count': count,
            'status': status,
            'count_score_display': count_score_display,
            'file_timestamp': timestamp
        }
        
    except Exception as e:
        log(f"❌ 解析内容失败: {e}")
        return None

def import_to_database(data):
    """导入数据到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查数据是否已存在
        cursor.execute("""
            SELECT COUNT(*) FROM crypto_snapshots 
            WHERE snapshot_time = ?
        """, (data['snapshot_time'],))
        
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            log(f"ℹ️  数据已存在: {data['snapshot_time']}")
            conn.close()
            return False
        
        # 插入新数据
        cursor.execute("""
            INSERT INTO crypto_snapshots 
            (snapshot_time, rush_up, rush_down, count, status, count_score_display, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', '+8 hours'))
        """, (
            data['snapshot_time'],
            data['rush_up'],
            data['rush_down'],
            data['count'],
            data['status'],
            data['count_score_display']
        ))
        
        conn.commit()
        conn.close()
        
        log(f"✅ 成功导入数据: {data['snapshot_time']} | 急涨:{data['rush_up']} 急跌:{data['rush_down']} | 计次:{data['count']} {data['count_score_display']} | {data['status']}")
        return True
        
    except Exception as e:
        log(f"❌ 数据库操作失败: {e}")
        return False

def main():
    """主函数"""
    log("=" * 80)
    log("🚀 智能Google Drive TXT检测器启动")
    log(f"📁 今天文件夹ID: {TODAY_FOLDER_ID}")
    log(f"🔄 检测间隔: {CHECK_INTERVAL}秒")
    log(f"💾 数据库: {DB_PATH}")
    log("=" * 80)
    
    last_file_id = None
    check_count = 0
    
    while True:
        try:
            check_count += 1
            log(f"\n{'='*80}")
            log(f"🔍 检查 #{check_count} | {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
            log("=" * 80)
            
            # 步骤1: 获取今天的文件夹ID
            today_folder_id = get_today_folder_id()
            if not today_folder_id:
                log("⏰ 等待下次检查...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 步骤2-3: 获取所有TXT文件
            txt_files = get_all_txt_files(today_folder_id)
            if not txt_files:
                log("⏰ 等待下次检查...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 步骤4: 找到最新的TXT文件
            latest_filename, latest_file_id = find_latest_txt(txt_files)
            if not latest_file_id:
                log("⏰ 等待下次检查...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 检查是否是新文件
            if latest_file_id == last_file_id:
                log(f"ℹ️  文件未更新，仍是: {latest_filename}")
                log("⏰ 等待下次检查...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 发现新文件
            log(f"🎉 发现新文件: {latest_filename}")
            log(f"📥 开始下载并解析...")
            
            # 下载文件内容
            content = download_file_content(latest_file_id)
            if not content:
                log("⏰ 等待下次检查...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 解析内容
            data = parse_txt_content(content)
            if not data:
                log("⏰ 等待下次检查...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            log(f"📊 解析结果:")
            log(f"   时间: {data['snapshot_time']}")
            log(f"   急涨/急跌: {data['rush_up']}/{data['rush_down']}")
            log(f"   计次: {data['count']} {data['count_score_display']}")
            log(f"   状态: {data['status']}")
            
            # 导入到数据库
            if import_to_database(data):
                log("✅ 数据导入成功")
                last_file_id = latest_file_id
            
            log("⏰ 等待下次检查...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("\n👋 收到停止信号，正在退出...")
            sys.exit(0)
        except Exception as e:
            log(f"❌ 发生错误: {e}")
            log("⏰ 等待下次检查...")
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
