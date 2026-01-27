#!/usr/bin/env python3
"""
通过修改时间戳定位 2025-12-12 文件夹
策略：检查所有候选ID，找到最近6小时内有更新的文件夹
"""
import requests
import re
from datetime import datetime, timedelta
import time

def get_folder_info(folder_id):
    """获取文件夹信息，包括最新文件时间"""
    try:
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        
        html = resp.text
        
        # 提取所有 TXT 文件名
        txt_files = re.findall(r'2025-12-\d{2}_\d{4}\.txt', html)
        
        if not txt_files:
            return None
        
        # 解析最新文件的时间
        latest_file = sorted(txt_files)[-1]
        date_str = latest_file.replace('.txt', '').replace('_', ' ')
        
        return {
            'folder_id': folder_id,
            'file_count': len(txt_files),
            'latest_file': latest_file,
            'date_from_filename': date_str
        }
    except Exception as e:
        return None

def main():
    print("🔍 根据用户截图（06:15修改时间）定位 2025-12-12 文件夹...")
    print("=" * 80)
    
    # 已知的文件夹ID
    known_folders = {
        '2025-12-08': '1iCt-xZE_ALhwjd57Wx2VOKMOurAEU2XY',
        '2025-12-09': '1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM',
        '2025-12-11': '1k3I_NALUR24-lAapPnSJ7_gMvCOiX5cV'
    }
    
    # 首先验证已知文件夹
    print("\n1️⃣ 验证已知文件夹...")
    for date, folder_id in known_folders.items():
        info = get_folder_info(folder_id)
        if info:
            print(f"✅ {date}: {info['file_count']} 个文件, 最新: {info['latest_file']}")
        time.sleep(1)
    
    # 从父文件夹获取所有候选ID
    print("\n2️⃣ 从父文件夹提取候选ID...")
    parent_url = "https://drive.google.com/embeddedfolderview?id=1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
    
    try:
        resp = requests.get(parent_url, timeout=15)
        all_ids = set(re.findall(r'[a-zA-Z0-9_-]{33}', resp.text))
        candidate_ids = all_ids - set(known_folders.values())
        print(f"   找到 {len(candidate_ids)} 个候选ID")
    except Exception as e:
        print(f"❌ 无法访问父文件夹: {e}")
        candidate_ids = []
    
    # 按字母顺序排序，因为12-12的ID可能在12-11之后
    candidate_ids = sorted(candidate_ids)
    
    # 重点：检查 ID 开头为 '1k' 的候选（因为12-11是 1k3I_...）
    print("\n3️⃣ 优先检查 '1k' 开头的候选ID (与12-11相似)...")
    priority_ids = [cid for cid in candidate_ids if cid.startswith('1k')]
    print(f"   找到 {len(priority_ids)} 个 '1k' 开头的候选")
    
    found_1212 = None
    
    for idx, folder_id in enumerate(priority_ids[:10], 1):  # 检查前10个
        print(f"\n   [{idx}/10] 检查 ID: {folder_id}")
        info = get_folder_info(folder_id)
        
        if info:
            print(f"      📁 文件数: {info['file_count']}")
            print(f"      📄 最新: {info['latest_file']}")
            
            # 检查是否包含 12-12 数据
            if '2025-12-12' in info['latest_file']:
                print(f"\n🎯 找到 2025-12-12 文件夹！")
                print(f"   ID: {folder_id}")
                print(f"   文件数: {info['file_count']}")
                print(f"   最新文件: {info['latest_file']}")
                found_1212 = folder_id
                break
        
        time.sleep(1)  # 避免请求过快
    
    # 如果没找到，检查剩余的候选
    if not found_1212:
        print("\n4️⃣ 检查其他候选ID...")
        other_ids = [cid for cid in candidate_ids if not cid.startswith('1k')]
        
        for idx, folder_id in enumerate(other_ids[:20], 1):  # 检查前20个
            if idx % 5 == 0:
                print(f"   已检查 {idx}/20...")
            
            info = get_folder_info(folder_id)
            if info and '2025-12-12' in info['latest_file']:
                print(f"\n🎯 找到 2025-12-12 文件夹！")
                print(f"   ID: {folder_id}")
                print(f"   文件数: {info['file_count']}")
                print(f"   最新文件: {info['latest_file']}")
                found_1212 = folder_id
                break
            
            time.sleep(1)
    
    # 输出结果
    print("\n" + "=" * 80)
    if found_1212:
        print("✅ 搜索成功！")
        print(f"📁 2025-12-12 文件夹 ID: {found_1212}")
        
        # 更新配置
        import json
        config_path = "/home/user/webapp/daily_folder_config.json"
        config = {
            "folder_id": found_1212,
            "data_date": "2025-12-12",
            "current_date": "2025-12-12",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 配置已更新到: {config_path}")
        print("\n⚠️ 需要执行：pm2 restart gdrive-monitor")
        
    else:
        print("❌ 未找到 2025-12-12 文件夹")
        print("   可能的原因：")
        print("   1. 文件夹尚未在 Google Drive 上公开")
        print("   2. 文件夹ID不在父目录的HTML中")
        print("   3. 需要用户提供具体的文件夹URL")

if __name__ == "__main__":
    main()
