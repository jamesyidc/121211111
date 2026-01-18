#!/usr/bin/env python3
"""
自动更新每日文件夹ID脚本
每天自动从父文件夹中查找今天的子文件夹并更新配置
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import sys
import os

# 配置
PARENT_FOLDER_ID = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
PARENT_URL = f"https://drive.google.com/embeddedfolderview?id={PARENT_FOLDER_ID}"
CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
LOG_FILE = "/home/user/webapp/auto_folder_update.log"

def log(message):
    """写入日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')

def get_beijing_time():
    """获取北京时间"""
    return datetime.utcnow() + timedelta(hours=8)

def find_today_folder():
    """从父文件夹中查找今天的子文件夹"""
    beijing_now = get_beijing_time()
    today = beijing_now.strftime('%Y-%m-%d')
    
    log(f"🔍 查找今天 ({today}) 的文件夹...")
    
    try:
        # 请求父文件夹
        response = requests.get(PARENT_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        # 查找今天的文件夹
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if '/folders/' in href and (today in text or text == today):
                folder_id = href.split('/folders/')[1].split('?')[0].split('/')[0]
                log(f"✅ 找到今天的文件夹: {text} -> {folder_id}")
                return folder_id, today
        
        log(f"❌ 未找到今天 ({today}) 的文件夹")
        return None, today
        
    except Exception as e:
        log(f"❌ 查找文件夹时出错: {e}")
        return None, today

def verify_folder(folder_id, today):
    """验证文件夹是否包含今天的TXT文件"""
    try:
        folder_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        response = requests.get(folder_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        txt_files = []
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            if text.endswith('.txt') and today in text:
                txt_files.append(text)
        
        log(f"   找到 {len(txt_files)} 个今天的TXT文件")
        
        if txt_files:
            latest_files = sorted(txt_files)[-3:]
            log(f"   最新文件: {', '.join(latest_files)}")
        
        return len(txt_files)
        
    except Exception as e:
        log(f"❌ 验证文件夹时出错: {e}")
        return 0

def update_config(folder_id, today, file_count):
    """更新配置文件"""
    beijing_now = get_beijing_time()
    
    config = {
        "current_date": today,
        "folder_id": folder_id,
        "parent_folder_id": PARENT_FOLDER_ID,
        "updated_at": beijing_now.strftime('%Y-%m-%d %H:%M:%S'),
        "auto_updated": True,
        "file_count": file_count
    }
    
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log(f"✅ 配置已更新: {CONFIG_FILE}")
        return True
        
    except Exception as e:
        log(f"❌ 更新配置文件失败: {e}")
        return False

def check_current_config():
    """检查当前配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        today = get_beijing_time().strftime('%Y-%m-%d')
        
        log(f"📋 当前配置:")
        log(f"   日期: {config.get('current_date')}")
        log(f"   文件夹ID: {config.get('folder_id')}")
        log(f"   文件数: {config.get('file_count', 0)}")
        log(f"   更新时间: {config.get('updated_at')}")
        
        if config.get('current_date') == today:
            log(f"✅ 配置已是今天的，无需更新")
            return True
        else:
            log(f"⚠️  配置日期 ({config.get('current_date')}) 不是今天 ({today})，需要更新")
            return False
            
    except FileNotFoundError:
        log(f"⚠️  配置文件不存在，将创建新配置")
        return False
    except Exception as e:
        log(f"❌ 读取配置文件失败: {e}")
        return False

def main():
    """主函数"""
    log("=" * 70)
    log("🚀 开始自动更新每日文件夹ID")
    log("=" * 70)
    
    # 检查当前配置
    if check_current_config():
        log("✅ 配置已是最新，无需更新")
        return 0
    
    # 查找今天的文件夹
    folder_id, today = find_today_folder()
    
    if not folder_id:
        log("❌ 未找到今天的文件夹，保持现有配置")
        return 1
    
    # 验证文件夹
    file_count = verify_folder(folder_id, today)
    
    if file_count == 0:
        log("⚠️  文件夹中没有找到今天的文件，但仍将更新配置")
    
    # 更新配置
    if update_config(folder_id, today, file_count):
        log("✅ 更新成功！检测器将在30秒内自动使用新配置")
        return 0
    else:
        log("❌ 更新失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
