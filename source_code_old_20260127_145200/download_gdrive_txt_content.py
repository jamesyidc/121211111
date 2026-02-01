#!/usr/bin/env python3
"""
提取真实Google Drive文件ID并下载内容
"""
import requests
import re

folder_id = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"
target_filename = "2025-12-09_1758.txt"
entry_id = "1Hpoye1MieqjxzsnNSeN4D5q7zF"  # 从entry-xxx中提取

print(f"📥 正在下载文件: {target_filename}")
print(f"   Entry ID: {entry_id}")
print()

# 方法1: 尝试直接下载
download_urls = [
    f"https://drive.google.com/uc?export=download&id={entry_id}",
    f"https://docs.google.com/uc?export=download&id={entry_id}",
    f"https://drive.google.com/file/d/{entry_id}/view",
]

for url in download_urls:
    try:
        print(f"🔄 尝试URL: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        
        if response.status_code == 200:
            content = response.text
            
            # 检查是否是HTML页面还是实际内容
            if '<html' in content.lower()[:100]:
                print(f"   ⚠️  返回的是HTML页面，不是文件内容")
                
                # 如果是view页面，尝试从中提取实际内容
                if 'file/d/' in url:
                    # 尝试找到真实的文件ID
                    real_id_match = re.search(r'"([a-zA-Z0-9_-]{33})"', content)
                    if real_id_match:
                        real_id = real_id_match.group(1)
                        print(f"   💡 找到真实ID: {real_id}")
                        
                        # 尝试用真实ID下载
                        real_url = f"https://drive.google.com/uc?export=download&id={real_id}"
                        print(f"   🔄 尝试真实URL: {real_url}")
                        real_response = requests.get(real_url, headers=headers, timeout=30)
                        
                        if real_response.status_code == 200:
                            content = real_response.text
                            if '<html' not in content.lower()[:100]:
                                print(f"   ✅ 成功下载文件内容！")
                                break
            else:
                print(f"   ✅ 成功下载文件内容！")
                break
        else:
            print(f"   ❌ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        continue

else:
    # 所有方法都失败了，使用最后的手段：
    # 利用现有的Google Drive文件夹结构来手动构造
    print("\n⚠️  所有直接下载方法失败")
    print("💡 使用alternative方案：模拟auto_gdrive_updater的逻辑")
    print()
    
    # 既然我们能看到文件夹列表，让我们尝试直接构造content
    # 或者利用gdrive_content_reader.py
    print("尝试使用gdrive_content_reader.py...")
    
    content = None

if content:
    # 保存到文件
    output_path = f"/home/user/webapp/{target_filename}"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ 文件已保存到: {output_path}")
    print(f"   文件大小: {len(content)} 字节")
    print()
    
    # 显示前几行
    lines = content.split('\n')
    print("📄 文件内容预览（前20行）:")
    print("-" * 60)
    for i, line in enumerate(lines[:20], 1):
        print(f"{i:2d}. {line}")
    print("-" * 60)
else:
    print("\n❌ 无法下载文件内容")
    print("💡 fallback: 使用gdrive_content_reader或web scraping...")

