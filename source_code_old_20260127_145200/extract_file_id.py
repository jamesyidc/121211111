#!/usr/bin/env python3
"""
从Google Drive HTML中提取特定文件的ID
"""
import requests
import re
import json

folder_id = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"
target_filename = "2025-12-09_1758.txt"

print(f"🔍 正在查找文件: {target_filename}")
print(f"   文件夹ID: {folder_id}")
print()

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 使用embed view
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    response = requests.get(embed_url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        content = response.text
        
        # Google Drive的embed view包含JSON数据
        # 尝试查找包含文件名的模式
        
        # 方法1: 查找 "2025-12-09_1758.txt" 周围的ID模式
        # Google Drive ID通常是33个字符的字符串
        
        # 查找文件名附近的潜在ID
        pattern = r'([a-zA-Z0-9_-]{33})["\s\,]*.*?' + re.escape(target_filename)
        matches = re.findall(pattern, content)
        
        if matches:
            file_id = matches[0]
            print(f"✅ 找到文件ID (方法1): {file_id}")
            print(f"   直接访问URL: https://drive.google.com/file/d/{file_id}/view")
            print(f"   下载URL: https://drive.google.com/uc?export=download&id={file_id}")
            print()
        else:
            # 方法2: 查找反向模式
            pattern2 = re.escape(target_filename) + r'["\s\,]*.*?([a-zA-Z0-9_-]{33})'
            matches2 = re.findall(pattern2, content)
            
            if matches2:
                file_id = matches2[0]
                print(f"✅ 找到文件ID (方法2): {file_id}")
                print(f"   直接访问URL: https://drive.google.com/file/d/{file_id}/view")
                print(f"   下载URL: https://drive.google.com/uc?export=download&id={file_id}")
                print()
            else:
                print("⚠️  未找到文件ID，使用alternative下载方法...")
                print()
                
                # 方法3: 尝试查找所有的ID，然后根据位置推断
                all_ids = re.findall(r'"([a-zA-Z0-9_-]{33})"', content)
                print(f"   找到 {len(all_ids)} 个潜在ID")
                
                # 由于文件是按时间排序的，1758应该是最后几个
                # 从embed view的响应中，文件通常按字母/时间顺序排列
                
                # 让我们尝试另一种方法：直接构造URL并测试
                print("\n🔄 尝试alternative方法：通过文件夹API...")
                
                # Google Drive有一个list API (虽然需要认证)
                # 但我们可以尝试通过公共分享链接来获取
                
                # 构造文件的可能share URL
                # Google Drive的分享文件URL格式:
                # https://drive.google.com/file/d/FILE_ID/view?usp=sharing
                
                # 但我们还是需要file_id...
                
                print("\n💡 使用智能方案：利用已有的auto_gdrive_updater.py...")
                
    else:
        print(f"❌ HTTP请求失败: {response.status_code}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("尝试使用现有的auto_gdrive_updater机制...")
print("="*60)

