#!/usr/bin/env python3
"""
智能Google Drive文件夹查找器
自动搜索包含最新数据的文件夹并更新配置
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
CONFIG_FILE = '/home/user/webapp/daily_folder_config.json'

# 已知的文件夹ID（按日期倒序）
KNOWN_FOLDERS = [
    {"date": "2025-12-11", "id": "1k3I_NALUR24-lAapPnSJ7_gMvCOiX5cV"},
    {"date": "2025-12-09", "id": "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"},
]

def check_folder_latest_date(folder_id):
    """检查文件夹中最新的数据日期"""
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        latest_date = None
        file_count = 0
        
        for link in soup.find_all('a', href=True):
            filename = link.get_text(strip=True)
            if filename.endswith('.txt'):
                file_count += 1
                match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                if match:
                    file_date = match.group(1)
                    if latest_date is None or file_date > latest_date:
                        latest_date = file_date
        
        return {
            'folder_id': folder_id,
            'latest_date': latest_date,
            'file_count': file_count
        }
    except Exception as e:
        print(f"❌ 检查文件夹 {folder_id} 失败: {e}")
        return None

def find_best_folder():
    """查找包含最新数据的文件夹"""
    print("🔍 开始智能搜索最新数据文件夹...")
    print("=" * 60)
    
    candidates = []
    
    for folder_info in KNOWN_FOLDERS:
        folder_date = folder_info['date']
        folder_id = folder_info['id']
        
        print(f"\n📂 检查 {folder_date} 的文件夹: {folder_id}")
        result = check_folder_latest_date(folder_id)
        
        if result and result['latest_date']:
            print(f"   ✅ 找到数据: 最新日期={result['latest_date']}, 文件数={result['file_count']}")
            candidates.append(result)
        else:
            print(f"   ⚠️ 无有效数据")
    
    if not candidates:
        print("\n❌ 未找到任何有效的文件夹")
        return None
    
    # 选择数据最新的文件夹
    best = max(candidates, key=lambda x: x['latest_date'])
    
    print(f"\n🎯 选择最佳文件夹:")
    print(f"   文件夹ID: {best['folder_id']}")
    print(f"   数据日期: {best['latest_date']}")
    print(f"   文件数量: {best['file_count']}")
    
    return best

def update_config(folder_id, data_date):
    """更新配置文件"""
    beijing_now = datetime.now(BEIJING_TZ)
    today_str = beijing_now.strftime('%Y-%m-%d')
    
    config = {
        'current_date': today_str,
        'folder_id': folder_id,
        'data_date': data_date,
        'last_update': beijing_now.strftime('%Y-%m-%d %H:%M:%S'),
        'note': f'智能选择：使用{data_date}的数据文件夹'
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 配置已更新到: {CONFIG_FILE}")
    print(json.dumps(config, indent=2, ensure_ascii=False))

def main():
    print("🚀 智能Google Drive文件夹查找器")
    print("=" * 60)
    
    best_folder = find_best_folder()
    
    if best_folder:
        update_config(best_folder['folder_id'], best_folder['latest_date'])
        print("\n✅ 完成！")
        return 0
    else:
        print("\n❌ 失败：未找到有效的文件夹")
        return 1

if __name__ == '__main__':
    exit(main())
