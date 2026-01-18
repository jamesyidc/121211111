#!/usr/bin/env python3
"""
Google Drive TXT文件检测器 - 自动跨日期文件夹更新
"""
import os
import sys
import json
import time
import re
import requests
import sqlite3
from datetime import datetime
import pytz

# 配置
CONFIG_FILE = '/home/user/webapp/daily_folder_config.json'
DB_PATH = '/home/user/webapp/databases/crypto_data.db'
LOG_FILE = '/home/user/webapp/gdrive_final_detector.log'
CHECK_INTERVAL = 30  # 秒

def log_message(message):
    """记录日志"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    
    print(log_line, end='')
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception as e:
        print(f"写入日志失败: {e}")

def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_message(f"❌ 加载配置失败: {e}")
        return {}

def save_config(config):
    """保存配置"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_message(f"❌ 保存配置失败: {e}")
        return False

def get_beijing_time():
    """获取北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)

def find_today_folder(parent_folder_id, today_str):
    """在父文件夹中查找今天的子文件夹"""
    try:
        url = f"https://drive.google.com/embeddedfolderview?id={parent_folder_id}"
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 查找今日日期文件夹
        if today_str not in content:
            return None, f"父文件夹中未找到日期: {today_str}"
        
        # 查找日期出现的位置
        idx = content.find(today_str)
        if idx == -1:
            return None, f"无法定位日期: {today_str}"
        
        # 向前搜索500个字符，找到最近的文件夹链接
        search_start = max(0, idx - 500)
        search_text = content[search_start:idx + 50]
        
        # 提取文件夹链接: /drive/folders/ID
        folder_pattern = r'/drive/folders/([A-Za-z0-9_-]{25,})'
        matches = re.findall(folder_pattern, search_text)
        
        if matches:
            # 取最后一个匹配（最接近日期的）
            folder_id = matches[-1]
            log_message(f"   调试: 找到候选ID: {folder_id}")
            
            # 验证这个文件夹是否包含今日的TXT文件
            test_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
            test_response = requests.get(test_url, timeout=10)
            
            if test_response.status_code == 200:
                # 检查是否包含今日日期的TXT文件
                txt_pattern = rf'>{today_str}_\d{{4}}\.txt<'
                if re.search(txt_pattern, test_response.text):
                    log_message(f"   调试: 验证通过，包含今日TXT文件")
                    return folder_id, None
                else:
                    log_message(f"   调试: 验证失败，不包含今日TXT文件")
        
        return None, f"无法提取或验证文件夹ID for {today_str}"
        
    except Exception as e:
        return None, f"查找文件夹失败: {e}"

def get_txt_files(folder_id, date_str):
    """获取指定文件夹中的TXT文件列表"""
    try:
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 查找TXT文件
        pattern = rf'>{date_str}_(\d{{4}})\.txt<'
        matches = re.findall(pattern, content)
        
        if matches:
            # 排序（从新到旧）
            times_sorted = sorted(matches, reverse=True)
            return [f"{date_str}_{time}.txt" for time in times_sorted], None
        else:
            return [], None
            
    except Exception as e:
        return [], f"获取文件列表失败: {e}"

def download_txt_file(folder_id, filename):
    """下载TXT文件内容"""
    try:
        # 获取文件ID
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 新的匹配模式：查找所有 entry 并匹配 title
        entries = re.findall(r'id="entry-([A-Za-z0-9_-]+)".*?<div class="flip-entry-title">([^<]+)</div>', content, re.DOTALL)
        
        file_id = None
        for entry_id, title in entries:
            if title == filename:
                file_id = entry_id
                break
        
        if not file_id:
            return None, f"找不到文件ID: {filename}"
        
        log_message(f"   找到文件ID: {file_id}")
        
        # 下载文件
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        file_response = requests.get(download_url, timeout=30)
        
        if file_response.status_code == 200:
            return file_response.text, None
        else:
            return None, f"下载失败: HTTP {file_response.status_code}"
            
    except Exception as e:
        return None, f"下载文件失败: {e}"

def parse_txt_content(content, snapshot_time):
    """解析TXT文件内容
    
    文件格式：
    1|BTC|0.11|0|0|2026-01-05 15:08:15|126259.48|2025-10-07|-26.6|1.38|||13|91098.9|72.66%|111.97%
    
    映射到数据库：
    - [1]: inst_id (BTC, ETH, etc.)
    - [3]: rush_up
    - [4]: rush_down
    - [5]: snapshot_time
    - [6]: last_price
    - [8]: change_24h (百分比)
    - [12]: count
    - [13]: vol_24h
    """
    try:
        records = []
        lines = content.strip().split('\n')
        
        # 找到数据开始标记
        start_index = -1
        for i, line in enumerate(lines):
            if '[超级列表框_首页开始]' in line or '[超级列表框_首页开始]' in line.strip('\r'):
                start_index = i + 1
                break
        
        if start_index == -1:
            log_message("⚠️ 未找到数据开始标记")
            start_index = 0
        
        # 解析每一行
        for line in lines[start_index:]:
            line = line.strip().strip('\r')  # 移除 \r \n
            
            if not line or line.startswith('#') or line.startswith('透明标签') or '[' in line:
                continue
            
            # 使用管道符分割
            parts = line.split('|')
            
            if len(parts) >= 14:  # 至少需要14个字段
                try:
                    # 提取数据
                    inst_id = parts[1].strip()
                    if not inst_id:
                        continue
                    
                    # 添加USDT后缀（如果没有）
                    if not inst_id.endswith('USDT'):
                        inst_id = f"{inst_id}USDT"
                    
                    # 解析其他字段
                    rush_up = int(parts[3].strip()) if parts[3].strip() else 0
                    rush_down = int(parts[4].strip()) if parts[4].strip() else 0
                    last_price = float(parts[6].strip())
                    change_24h = float(parts[8].strip())
                    vol_24h = float(parts[13].strip())
                    count = int(parts[12].strip()) if parts[12].strip() else 0
                    
                    # 计算diff
                    diff = rush_up - rush_down
                    
                    # 计算status
                    if diff > 0:
                        status = '上涨'
                    elif diff < 0:
                        status = '下跌'
                    else:
                        status = '震荡'
                    
                    record = {
                        'inst_id': inst_id,
                        'last_price': last_price,
                        'rush_up': rush_up,
                        'rush_down': rush_down,
                        'diff': diff,
                        'count': count,
                        'status': status,
                        'vol_24h': vol_24h,
                        'change_24h': change_24h,
                        'snapshot_time': parts[5].strip(),  # 使用文件中的时间
                        'snapshot_date': parts[5].strip().split()[0]  # 提取日期部分
                    }
                    records.append(record)
                    
                except (ValueError, IndexError) as e:
                    log_message(f"⚠️ 解析行失败: {line[:50]}... 错误: {e}")
                    continue
        
        return records, None
    except Exception as e:
        return [], f"解析文件失败: {e}"

def save_to_database(records):
    """保存数据到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                snapshot_time TEXT NOT NULL,
                inst_id TEXT NOT NULL,
                last_price REAL NOT NULL,
                high_24h REAL,
                low_24h REAL,
                vol_24h REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rush_up INTEGER NOT NULL,
                rush_down INTEGER NOT NULL,
                diff INTEGER NOT NULL,
                count INTEGER NOT NULL,
                status TEXT NOT NULL,
                count_score_display TEXT,
                count_score_type TEXT,
                change_24h REAL,
                UNIQUE(inst_id, snapshot_time)
            )
        ''')
        
        # 插入数据
        inserted = 0
        for record in records:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO crypto_snapshots 
                    (snapshot_date, snapshot_time, inst_id, last_price, vol_24h,
                     rush_up, rush_down, diff, count, status, change_24h)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record['snapshot_date'], record['snapshot_time'], record['inst_id'],
                    record['last_price'], record['vol_24h'], record['rush_up'],
                    record['rush_down'], record['diff'], record['count'],
                    record['status'], record.get('change_24h', 0)
                ))
                inserted += 1
            except Exception as e:
                log_message(f"  ⚠️ 插入记录失败 {record['inst_id']}: {e}")
        
        conn.commit()
        conn.close()
        
        return inserted, None
    except Exception as e:
        return 0, f"保存到数据库失败: {e}"

def update_folder_config():
    """更新文件夹配置（跨日期自动切换）"""
    beijing_time = get_beijing_time()
    today_str = beijing_time.strftime('%Y-%m-%d')
    day_of_month = beijing_time.day
    is_odd_day = day_of_month % 2 == 1
    
    config = load_config()
    
    # 检查是否需要更新（日期变化或配置缺失）
    if config.get('current_date') == today_str and config.get('folder_id'):
        return config, None
    
    log_message(f"📅 检测到日期变化或配置缺失，开始更新文件夹配置...")
    log_message(f"   今天: {today_str} ({'单数' if is_odd_day else '双数'}日)")
    
    # 根据单双数选择父文件夹
    if is_odd_day:
        parent_folder_id = config.get('root_folder_odd')
        log_message(f"   使用单数日父文件夹: {parent_folder_id}")
    else:
        parent_folder_id = config.get('root_folder_even')
        log_message(f"   使用双数日父文件夹: {parent_folder_id}")
    
    if not parent_folder_id:
        error_msg = f"❌ 未配置{'单数' if is_odd_day else '双数'}日父文件夹ID，请在配置页面设置"
        log_message(error_msg)
        return None, error_msg
    
    # 查找今天的子文件夹
    today_folder_id, error = find_today_folder(parent_folder_id, today_str)
    if error:
        log_message(f"❌ {error}")
        return None, error
    
    log_message(f"✅ 找到今日文件夹: {today_folder_id}")
    
    # 获取TXT文件列表
    txt_files, error = get_txt_files(today_folder_id, today_str)
    if error:
        log_message(f"❌ {error}")
        return None, error
    
    log_message(f"✅ 找到 {len(txt_files)} 个TXT文件")
    
    # 更新配置
    config['current_date'] = today_str
    config['data_date'] = today_str
    config['folder_id'] = today_folder_id
    config['folder_name'] = today_str
    config['txt_count'] = len(txt_files)
    config['latest_txt'] = txt_files[0] if txt_files else ""
    config['last_update'] = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    config['update_reason'] = '自动跨日期切换'
    
    if save_config(config):
        log_message(f"✅ 配置已更新: {today_folder_id}")
        return config, None
    else:
        return None, "保存配置失败"

def check_and_import_latest():
    """检查并导入最新的TXT文件"""
    try:
        # 更新文件夹配置
        config, error = update_folder_config()
        if error:
            return False, error
        
        folder_id = config.get('folder_id')
        if not folder_id:
            return False, "未配置文件夹ID"
        
        beijing_time = get_beijing_time()
        today_str = beijing_time.strftime('%Y-%m-%d')
        
        # 获取最新的TXT文件列表
        txt_files, error = get_txt_files(folder_id, today_str)
        if error:
            return False, error
        
        if not txt_files:
            return False, "没有找到TXT文件"
        
        latest_file = txt_files[0]
        
        # 检查是否已导入
        last_imported = config.get('last_imported_file', '')
        if last_imported == latest_file:
            log_message(f"📄 最新文件已导入: {latest_file}")
            return True, None
        
        log_message(f"📥 开始导入新文件: {latest_file}")
        
        # 下载文件内容
        content, error = download_txt_file(folder_id, latest_file)
        if error:
            return False, error
        
        # 解析文件时间戳
        time_match = re.search(r'_(\d{4})\.txt$', latest_file)
        if time_match:
            time_str = time_match.group(1)
            snapshot_time = f"{today_str} {time_str[:2]}:{time_str[2:]}:00"
        else:
            snapshot_time = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 解析内容
        records, error = parse_txt_content(content, snapshot_time)
        if error:
            return False, error
        
        log_message(f"📊 解析到 {len(records)} 条记录")
        
        # 保存到数据库
        inserted, error = save_to_database(records)
        if error:
            return False, error
        
        log_message(f"✅ 成功导入 {inserted} 条记录到数据库")
        
        # 更新配置
        config['last_imported_file'] = latest_file
        config['last_import_time'] = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
        config['last_import_records'] = inserted
        save_config(config)
        
        return True, None
        
    except Exception as e:
        error_msg = f"导入失败: {e}"
        log_message(f"❌ {error_msg}")
        return False, error_msg

def main():
    """主函数"""
    log_message("=" * 60)
    log_message("🚀 Google Drive TXT检测器启动")
    log_message("=" * 60)
    
    check_count = 0
    
    while True:
        try:
            check_count += 1
            beijing_time = get_beijing_time()
            
            log_message(f"\n🔍 检查 #{check_count} - {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            success, error = check_and_import_latest()
            
            if success:
                log_message(f"✅ 检查完成")
            else:
                log_message(f"⚠️ 检查遇到问题: {error}")
            
            log_message(f"⏱️ 等待 {CHECK_INTERVAL} 秒...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log_message("\n⛔ 接收到停止信号，正在退出...")
            break
        except Exception as e:
            log_message(f"❌ 发生错误: {e}")
            log_message(f"⏱️ 等待 {CHECK_INTERVAL} 秒后重试...")
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
