#!/usr/bin/env python3
"""
每日00:10自动更新父文件夹ID任务
从Google Drive URL获取最新的父文件夹结构并更新配置
"""
import requests
import re
import json
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
LOG_FILE = "/home/user/webapp/parent_folder_update.log"
GDRIVE_URL = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV?usp=sharing"
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

def extract_folder_id_from_url(url):
    """从Google Drive URL提取文件夹ID"""
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

def get_latest_date_folder_from_gdrive(parent_folder_id):
    """从Google Drive父文件夹获取最新的日期子文件夹"""
    try:
        url = f"https://drive.google.com/embeddedfolderview?id={parent_folder_id}"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有文件夹链接
        all_links = soup.find_all('a', href=True)
        date_folders = {}
        
        for link in all_links:
            href = link.get('href', '')
            foldername = link.get_text(strip=True)
            
            # 检查是否是日期格式的文件夹 YYYY-MM-DD
            if re.match(r'\d{4}-\d{2}-\d{2}$', foldername):
                # 提取文件夹ID
                if '/folders/' in href:
                    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', href)
                    if match:
                        folder_id = match.group(1)
                        date_folders[foldername] = folder_id
        
        return date_folders
    except Exception as e:
        log(f"❌ 获取Google Drive文件夹失败: {e}")
        return {}

def update_parent_folder():
    """更新父文件夹ID的主函数"""
    log("")
    log("=" * 80)
    log("🔄 开始每日父文件夹ID更新任务")
    log("=" * 80)
    
    # 1. 获取当前日期
    today = datetime.now(BEIJING_TZ)
    today_str = today.strftime('%Y-%m-%d')
    day_num = today.day
    is_odd = day_num % 2 == 1
    day_type = "单数" if is_odd else "双数"
    
    log(f"📅 当前日期: {today_str} ({day_num}号 - {day_type})")
    log(f"🔗 Google Drive URL: {GDRIVE_URL}")
    
    # 2. 从URL提取父文件夹ID
    parent_folder_id = extract_folder_id_from_url(GDRIVE_URL)
    if not parent_folder_id:
        log("❌ 无法从URL提取文件夹ID")
        return False
    
    log(f"📂 提取到父文件夹ID: {parent_folder_id}")
    
    # 3. 扫描父文件夹，获取所有日期子文件夹
    log(f"🔍 扫描父文件夹中的日期子文件夹...")
    date_folders = get_latest_date_folder_from_gdrive(parent_folder_id)
    
    if not date_folders:
        log("⚠️  未找到任何日期子文件夹")
        return False
    
    log(f"✅ 找到 {len(date_folders)} 个日期子文件夹")
    
    # 显示最近的10个文件夹
    sorted_dates = sorted(date_folders.keys(), reverse=True)
    log(f"\n📋 最近的日期文件夹:")
    for i, date in enumerate(sorted_dates[:10], 1):
        marker = " ← 今天" if date == today_str else ""
        log(f"   {i}. {date}{marker}")
    
    # 4. 查找今天的子文件夹
    if today_str not in date_folders:
        log(f"\n⚠️  未找到今天的子文件夹: {today_str}")
        log(f"💡 最新可用日期: {sorted_dates[0]}")
        # 使用最新的文件夹
        latest_date = sorted_dates[0]
        today_folder_id = date_folders[latest_date]
        log(f"📂 使用最新文件夹: {latest_date}")
    else:
        today_folder_id = date_folders[today_str]
        log(f"\n✅ 找到今天的子文件夹: {today_str}")
    
    log(f"📂 子文件夹ID: {today_folder_id}")
    
    # 5. 更新配置文件
    log(f"\n📝 更新配置文件...")
    
    try:
        # 读取现有配置
        existing_config = {}
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
        except:
            pass
        
        # 更新配置
        config = {
            'root_folder_odd': parent_folder_id if is_odd else existing_config.get('root_folder_odd', parent_folder_id),
            'root_folder_even': parent_folder_id if not is_odd else existing_config.get('root_folder_even', parent_folder_id),
            'current_date': today_str,
            'data_date': today_str,
            'folder_id': today_folder_id,
            'last_update': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'update_reason': f'每日00:10自动更新（{day_type}日期）',
            'parent_folder_url': GDRIVE_URL,
            'last_auto_update': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'auto_update_status': 'success',
            'root_folder_description': {
                'odd': '单数日期父文件夹 (1, 3, 5, 7, 9, 11...)',
                'even': '双数日期父文件夹 (2, 4, 6, 8, 10, 12...)'
            }
        }
        
        # 保留清理记录（如果存在）
        if 'last_cleanup' in existing_config:
            config['last_cleanup'] = existing_config['last_cleanup']
        if 'cleanup_reason' in existing_config:
            config['cleanup_reason'] = existing_config['cleanup_reason']
        
        # 保存配置
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        log(f"   ✅ 配置文件已更新")
        log(f"\n📊 更新结果:")
        log(f"   ├─ 父文件夹ID: {parent_folder_id}")
        log(f"   ├─ 子文件夹ID: {today_folder_id}")
        log(f"   ├─ 日期: {today_str}")
        log(f"   └─ 类型: {day_type}日期")
        
        log(f"\n✅ 父文件夹ID更新任务完成")
        log("=" * 80)
        log("")
        
        return True
        
    except Exception as e:
        log(f"❌ 更新配置文件失败: {e}")
        import traceback
        log(f"错误详情: {traceback.format_exc()}")
        
        # 记录失败状态
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            config['last_auto_update'] = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            config['auto_update_status'] = 'failed'
            config['auto_update_error'] = str(e)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except:
            pass
        
        return False

if __name__ == "__main__":
    success = update_parent_folder()
    exit(0 if success else 1)
