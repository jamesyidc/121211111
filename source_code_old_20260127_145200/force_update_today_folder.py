#!/usr/bin/env python3
"""
强制更新今天的文件夹ID
用于跨日期时手动触发配置更新
"""
import requests
import re
import json
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

ROOT_FOLDER_ID = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"  # 根文件夹ID
CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_today_folder():
    """从根文件夹获取今天的文件夹ID"""
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    
    print(f"📅 今天日期: {today}")
    print(f"📂 访问根文件夹: {ROOT_FOLDER_ID}")
    
    url = f"https://drive.google.com/embeddedfolderview?id={ROOT_FOLDER_ID}"
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 查找所有文件夹链接
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link.get('href', '')
        foldername = link.get_text(strip=True)
        
        print(f"  检查: {foldername}")
        
        # 检查是否是今天日期的文件夹
        if foldername == today:
            # 提取文件夹ID
            if '/folders/' in href:
                match = re.search(r'/folders/([a-zA-Z0-9_-]+)', href)
                if match:
                    folder_id = match.group(1)
                    print(f"✅ 找到今天的文件夹!")
                    print(f"📂 文件夹ID: {folder_id}")
                    return today, folder_id
    
    print(f"❌ 未找到今天的文件夹: {today}")
    return None, None

def update_config(date, folder_id):
    """更新配置文件"""
    config = {
        'current_date': date,
        'folder_id': folder_id,
        'updated_at': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
        'update_reason': '手动强制更新'
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 配置文件已更新!")
    print(f"   日期: {date}")
    print(f"   文件夹ID: {folder_id}")

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 强制更新今天的文件夹ID")
    print("=" * 60)
    print("")
    
    date, folder_id = get_today_folder()
    
    if date and folder_id:
        update_config(date, folder_id)
        print("")
        print("✅ 更新成功! 请重启 gdrive-monitor 服务:")
        print("   pm2 restart gdrive-monitor")
    else:
        print("")
        print("❌ 更新失败! 请检查:")
        print("   1. 根文件夹ID是否正确")
        print("   2. 今天的日期文件夹是否存在")
        print(f"   3. 确保根文件夹下有名为 '{datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')}' 的子文件夹")
