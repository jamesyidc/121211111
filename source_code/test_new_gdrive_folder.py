#!/usr/bin/env python3
"""
测试新的 Google Drive 文件夹结构
"""
import requests
from bs4 import BeautifulSoup
import re

# 新的父文件夹 ID（用户提供的链接）
NEW_PARENT_FOLDER_ID = "1U5VjRis2FYnBJvtR_8mmPrmFcJCMPGrH"

def list_gdrive_folders(folder_id):
    """列出 Google Drive 文件夹中的子文件夹"""
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    print(f"\n🔍 检查文件夹: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有文件夹链接
            folders = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/folders/' in href:
                    folder_id_match = re.search(r'/folders/([a-zA-Z0-9_-]+)', href)
                    if folder_id_match:
                        folder_id = folder_id_match.group(1)
                        folder_name = link.get_text(strip=True)
                        if folder_name:
                            folders.append({
                                'id': folder_id,
                                'name': folder_name
                            })
            
            # 查找所有文件
            files = []
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)
                if '.txt' in text or '首页数据' in text:
                    files.append(text)
            
            print(f"\n📁 找到 {len(folders)} 个子文件夹:")
            for folder in folders:
                print(f"   - {folder['name']} (ID: {folder['id']})")
            
            print(f"\n📄 找到 {len(files)} 个相关文件/文件夹:")
            for file in files[:10]:  # 只显示前10个
                print(f"   - {file}")
            
            return folders
        else:
            print(f"❌ HTTP 错误: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 测试新的 Google Drive 文件夹结构")
    print("=" * 60)
    
    # 列出新父文件夹中的内容
    folders = list_gdrive_folders(NEW_PARENT_FOLDER_ID)
    
    # 查找"首页数据"文件夹
    homepage_folder = None
    for folder in folders:
        if "首页数据" in folder['name'] or "data" in folder['name'].lower():
            homepage_folder = folder
            print(f"\n✅ 找到首页数据文件夹: {folder['name']} (ID: {folder['id']})")
            
            # 列出首页数据文件夹中的内容
            print("\n" + "=" * 60)
            print(f"📂 检查 '{folder['name']}' 文件夹内容...")
            print("=" * 60)
            list_gdrive_folders(folder['id'])
            break
    
    if not homepage_folder:
        print("\n⚠️ 未找到'首页数据'文件夹")
        print("\n💡 请手动检查以下链接:")
        print(f"   https://drive.google.com/drive/folders/{NEW_PARENT_FOLDER_ID}")
