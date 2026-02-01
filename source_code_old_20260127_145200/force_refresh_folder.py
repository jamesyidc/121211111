#!/usr/bin/env python3
"""
手动触发11分钟超时恢复机制
强制重新搜索今天的父文件夹和子文件夹
"""
import requests
import re
import json
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
ROOT_FOLDER_ODD = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"
ROOT_FOLDER_EVEN = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_root_folder_for_today():
    """根据今天是单数还是双数，获取对应的父文件夹ID"""
    today = datetime.now(BEIJING_TZ)
    day_of_month = today.day
    is_odd_day = day_of_month % 2 == 1
    
    # 从配置文件读取单数/双数父文件夹ID
    root_folder_odd = ROOT_FOLDER_ODD
    root_folder_even = ROOT_FOLDER_EVEN
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if 'root_folder_odd' in config:
                root_folder_odd = config['root_folder_odd']
            if 'root_folder_even' in config:
                root_folder_even = config['root_folder_even']
    except:
        pass
    
    # 根据日期选择父文件夹
    if is_odd_day:
        print(f"📅 今天是{day_of_month}号（单数日期）")
        print(f"📂 应该使用单数日期父文件夹: {root_folder_odd}")
        return root_folder_odd, is_odd_day
    else:
        print(f"📅 今天是{day_of_month}号（双数日期）")
        print(f"📂 应该使用双数日期父文件夹: {root_folder_even}")
        return root_folder_even, is_odd_day

def force_refresh():
    """强制刷新，重新获取今天的文件夹"""
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    
    print("\n" + "="*80)
    print("🔄 手动触发文件夹刷新")
    print("="*80 + "\n")
    
    # 1. 获取应该使用的父文件夹ID
    root_folder_id, is_odd = get_root_folder_for_today()
    
    print(f"\n📂 步骤1: 访问父文件夹 {root_folder_id}")
    print(f"🔍 查找目标子文件夹: {today}")
    
    try:
        # 2. 访问父文件夹，查找今天日期的子文件夹
        url = f"https://drive.google.com/embeddedfolderview?id={root_folder_id}"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有文件夹链接
        all_links = soup.find_all('a', href=True)
        today_folder_id = None
        
        print(f"\n🔎 扫描父文件夹中的子文件夹...")
        found_folders = []
        
        for link in all_links:
            href = link.get('href', '')
            foldername = link.get_text(strip=True)
            
            # 收集所有日期格式的文件夹
            if re.match(r'\d{4}-\d{2}-\d{2}', foldername):
                found_folders.append(foldername)
                
                # 检查是否是今天日期的文件夹
                if foldername == today:
                    # 提取文件夹ID
                    if '/folders/' in href:
                        match = re.search(r'/folders/([a-zA-Z0-9_-]+)', href)
                        if match:
                            today_folder_id = match.group(1)
                            print(f"   ✅ 找到今天的子文件夹: {today}")
                            print(f"   📂 子文件夹ID: {today_folder_id}")
        
        print(f"\n📋 父文件夹中找到的日期文件夹:")
        if found_folders:
            for folder in sorted(found_folders, reverse=True)[:10]:
                marker = " ← 今天" if folder == today else ""
                print(f"   - {folder}{marker}")
        else:
            print("   ⚠️  未找到任何日期格式的文件夹")
        
        if not today_folder_id:
            print(f"\n❌ 未找到今天日期的子文件夹: {today}")
            print(f"⚠️  请确保父文件夹下存在名为 '{today}' 的子文件夹")
            print(f"\n💡 提示:")
            print(f"   1. 检查父文件夹ID是否正确: {root_folder_id}")
            print(f"   2. 确认Google Drive中存在 {today} 文件夹")
            print(f"   3. 如果需要更新父文件夹ID，运行:")
            if is_odd:
                print(f"      python3 update_root_folders.py --odd '正确的单数父文件夹ID'")
            else:
                print(f"      python3 update_root_folders.py --even '正确的双数父文件夹ID'")
            return None
        
        # 3. 更新配置文件
        print(f"\n📝 步骤2: 更新配置文件")
        
        # 读取现有配置，保留单数/双数父文件夹ID
        existing_config = {}
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
        except:
            pass
        
        # 更新配置
        config = {
            'root_folder_odd': existing_config.get('root_folder_odd', ROOT_FOLDER_ODD),
            'root_folder_even': existing_config.get('root_folder_even', ROOT_FOLDER_EVEN),
            'current_date': today,
            'data_date': today,
            'folder_id': today_folder_id,
            'last_update': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'update_reason': '手动强制刷新',
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
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print(f"   ✅ 配置文件已更新")
        print(f"\n📊 更新后的配置:")
        print(f"   ├─ 当前日期: {today}")
        print(f"   ├─ 单数父文件夹: {config.get('root_folder_odd', 'N/A')}")
        if 'root_folder_even' in config:
            print(f"   ├─ 双数父文件夹: {config['root_folder_even']}")
        else:
            print(f"   ├─ 双数父文件夹: 🧹 已清理")
        print(f"   └─ 子账号文件夹: {today_folder_id}")
        
        print(f"\n✅ 刷新完成！")
        print("="*80 + "\n")
        
        return today_folder_id
        
    except Exception as e:
        print(f"\n❌ 刷新失败: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    force_refresh()
