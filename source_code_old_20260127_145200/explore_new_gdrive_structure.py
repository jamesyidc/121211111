#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive 文件夹探索工具
探索新的父文件夹结构
"""

import requests
import re
import json

# 新的父文件夹ID（你提供的）
PARENT_FOLDER_ID = '1U5VjRis2FYnBJvtR_8mmPrmFcJCMPGrH'

print("=" * 80)
print("🔍 Google Drive 文件夹结构探索")
print("=" * 80)
print(f"\n父文件夹ID: {PARENT_FOLDER_ID}")
print(f"链接: https://drive.google.com/drive/folders/{PARENT_FOLDER_ID}")

# 获取父文件夹内容
try:
    url = f'https://drive.google.com/drive/folders/{PARENT_FOLDER_ID}'
    response = requests.get(url, timeout=15)
    
    # 查找所有文件夹（包括中文）
    # 匹配格式: "文件夹名"..."id":"文件夹ID"
    folder_pattern = r'\[null,"([^"]+)"\].*?"id":"([^"]+)".*?"application/vnd\.google-apps\.folder"'
    folders = re.findall(folder_pattern, response.text)
    
    print(f"\n📁 找到 {len(folders)} 个子文件夹:\n")
    
    for i, (folder_name, folder_id) in enumerate(folders, 1):
        print(f"{i}. 【{folder_name}】")
        print(f"   ID: {folder_id}")
        print(f"   链接: https://drive.google.com/drive/folders/{folder_id}")
        print()
        
        # 如果是"首页数据"文件夹，进一步探索
        if '首页数据' in folder_name:
            print(f"   🔍 探索【首页数据】文件夹内容...")
            sub_url = f'https://drive.google.com/drive/folders/{folder_id}'
            sub_response = requests.get(sub_url, timeout=15)
            
            # 查找日期格式的文件夹 (YYYY-MM-DD)
            date_pattern = r'"(202[0-9]-[0-9]{2}-[0-9]{2})"'
            dates = re.findall(date_pattern, sub_response.text)
            dates_unique = list(set(dates))
            dates_unique.sort(reverse=True)
            
            if dates_unique:
                print(f"   ✅ 找到 {len(dates_unique)} 个日期文件夹:")
                for date in dates_unique[:5]:  # 显示最近5个
                    print(f"      - {date}")
            else:
                print(f"   ❌ 没有找到日期文件夹")
                
                # 查找TXT文件
                txt_pattern = r'"([^"]+\.txt)"'
                txt_files = re.findall(txt_pattern, sub_response.text)
                txt_files_unique = list(set(txt_files))
                
                if txt_files_unique:
                    print(f"   📄 找到 {len(txt_files_unique)} 个TXT文件:")
                    for txt_file in sorted(txt_files_unique)[:10]:
                        print(f"      - {txt_file}")
                        
                # 查找子文件夹
                sub_folder_pattern = r'\[null,"([^"]+)"\].*?"id":"([^"]+)".*?"application/vnd\.google-apps\.folder"'
                sub_folders = re.findall(sub_folder_pattern, sub_response.text)
                
                if sub_folders:
                    print(f"   📁 找到 {len(sub_folders)} 个子文件夹:")
                    for sub_name, sub_id in sub_folders[:10]:
                        print(f"      - {sub_name} (ID: {sub_id})")
            
            print()

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
