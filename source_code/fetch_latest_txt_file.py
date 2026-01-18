#!/usr/bin/env python3
"""
从Google Drive获取指定的最新TXT文件
"""
import requests
import re

folder_id = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"
target_filename = "2025-12-09_1758"  # 不含.txt扩展名

print(f"🔍 正在获取文件: {target_filename}.txt")
print(f"   文件夹ID: {folder_id}")
print()

try:
    # 获取文件夹内容
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    response = requests.get(folder_url, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ HTTP请求失败: {response.status_code}")
        exit(1)
    
    print("✅ 成功获取文件夹页面")
    
    # 查找文件ID
    # 格式: "2025-12-09_1758.txt".*?"id":"FILE_ID"
    txt_pattern = r'"' + re.escape(target_filename) + r'\.txt".*?"id":"([^"]+)"'
    match = re.search(txt_pattern, response.text)
    
    if not match:
        print(f"❌ 未找到文件: {target_filename}.txt")
        print("尝试查找所有可能的ID...")
        
        # Alternative: 查找所有包含文件名的行
        all_matches = re.findall(target_filename, response.text)
        print(f"   找到 {len(all_matches)} 处文件名出现")
        
        # 更宽松的匹配
        pattern2 = r'(' + re.escape(target_filename) + r'[^"]*)"[^}]*"id":"([^"]+)"'
        matches2 = re.findall(pattern2, response.text)
        
        if matches2:
            print(f"   使用宽松匹配找到 {len(matches2)} 个候选")
            file_id = matches2[0][1]
            print(f"✅ 文件ID: {file_id}")
        else:
            exit(1)
    else:
        file_id = match.group(1)
        print(f"✅ 文件ID: {file_id}")
    
    # 构造下载URL
    download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
    print(f"📥 下载URL: {download_url}")
    print()
    
    # 下载文件
    print("正在下载文件...")
    download_response = requests.get(download_url, timeout=30)
    
    if download_response.status_code == 200:
        content = download_response.text
        
        # 检查是否需要确认（大文件）
        if 'download_warning' in content:
            # 需要确认下载
            print("   需要确认下载（大文件）...")
            confirm_token = re.search(r'download_warning[^"]*', content)
            if confirm_token:
                confirmed_url = f"{download_url}&confirm={confirm_token.group(0)}"
                download_response = requests.get(confirmed_url, timeout=30)
                content = download_response.text
        
        # 保存文件
        output_filename = f"{target_filename}.txt"
        output_path = f"/home/user/webapp/{output_filename}"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 文件已保存: {output_path}")
        print(f"   文件大小: {len(content)} 字节")
        print()
        
        # 显示文件前20行
        lines = content.split('\n')
        print("📄 文件内容预览（前20行）:")
        print("=" * 70)
        for i, line in enumerate(lines[:20], 1):
            print(f"{i:2d}. {line}")
        print("=" * 70)
        print(f"总行数: {len(lines)}")
        
    else:
        print(f"❌ 下载失败: HTTP {download_response.status_code}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

