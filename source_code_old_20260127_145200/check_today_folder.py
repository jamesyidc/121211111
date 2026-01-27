#!/usr/bin/env python3
"""
检查今天的文件夹和最新的 TXT 文件
"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# 首页数据文件夹 ID（这个没有变）
HOMEPAGE_DATA_FOLDER_ID = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"

def list_gdrive_content(folder_id, filter_date=None):
    """列出 Google Drive 文件夹中的内容"""
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
                        fid = folder_id_match.group(1)
                        folder_name = link.get_text(strip=True)
                        if folder_name and re.match(r'\d{4}-\d{2}-\d{2}', folder_name):
                            folders.append({
                                'id': fid,
                                'name': folder_name
                            })
            
            # 排序，最新的在前
            folders.sort(key=lambda x: x['name'], reverse=True)
            
            print(f"\n📁 找到 {len(folders)} 个日期文件夹 (显示最近5个):")
            for folder in folders[:5]:
                print(f"   - {folder['name']} (ID: {folder['id']})")
            
            # 如果指定了日期过滤
            if filter_date:
                for folder in folders:
                    if folder['name'] == filter_date:
                        return folder
                return None
            
            return folders[0] if folders else None
        else:
            print(f"❌ HTTP 错误: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

def list_txt_files(folder_id):
    """列出文件夹中的 TXT 文件"""
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    print(f"\n🔍 检查 TXT 文件: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有 .txt 文件
            txt_files = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if '.txt' in text and re.match(r'\d{4}-\d{2}-\d{2}_\d{4}\.txt', text):
                    # 提取文件ID
                    file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', href) or \
                                    re.search(r'id=([a-zA-Z0-9_-]+)', href)
                    file_id = file_id_match.group(1) if file_id_match else None
                    
                    txt_files.append({
                        'name': text,
                        'id': file_id
                    })
            
            # 排序，最新的在前
            txt_files.sort(key=lambda x: x['name'], reverse=True)
            
            print(f"\n📄 找到 {len(txt_files)} 个 TXT 文件 (显示最近5个):")
            for txt in txt_files[:5]:
                print(f"   - {txt['name']} (ID: {txt['id']})")
            
            return txt_files
        else:
            print(f"❌ HTTP 错误: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 检查今天的数据文件夹")
    print("=" * 60)
    
    # 获取今天的日期
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n📅 今天的日期: {today}")
    
    # 1. 列出首页数据文件夹中的所有日期文件夹
    print("\n" + "=" * 60)
    print("步骤 1: 查找今天的文件夹")
    print("=" * 60)
    today_folder = list_gdrive_content(HOMEPAGE_DATA_FOLDER_ID, filter_date=today)
    
    if today_folder:
        print(f"\n✅ 找到今天的文件夹: {today_folder['name']} (ID: {today_folder['id']})")
        
        # 2. 列出今天文件夹中的所有 TXT 文件
        print("\n" + "=" * 60)
        print("步骤 2: 查找今天的 TXT 文件")
        print("=" * 60)
        txt_files = list_txt_files(today_folder['id'])
        
        if txt_files:
            latest_txt = txt_files[0]
            print(f"\n✅ 最新的 TXT 文件: {latest_txt['name']}")
            print(f"   文件 ID: {latest_txt['id']}")
            
            # 3. 尝试下载并读取最新文件
            if latest_txt['id']:
                print("\n" + "=" * 60)
                print("步骤 3: 尝试读取最新文件内容")
                print("=" * 60)
                
                download_url = f"https://drive.google.com/uc?export=download&id={latest_txt['id']}"
                try:
                    resp = requests.get(download_url, timeout=10)
                    if resp.status_code == 200:
                        content = resp.text
                        print(f"\n✅ 文件内容 (前500字符):")
                        print(content[:500])
                        print("\n" + "=" * 60)
                        print("📝 配置建议:")
                        print("=" * 60)
                        print(f"今天的文件夹 ID: {today_folder['id']}")
                        print(f"最新文件名: {latest_txt['name']}")
                        print(f"最新文件 ID: {latest_txt['id']}")
                    else:
                        print(f"❌ 下载失败: HTTP {resp.status_code}")
                except Exception as e:
                    print(f"❌ 下载错误: {e}")
        else:
            print(f"\n⚠️ 今天的文件夹中没有找到 TXT 文件")
    else:
        print(f"\n⚠️ 未找到今天 ({today}) 的文件夹")
        print("\n请确认:")
        print(f"   1. 今天的日期文件夹是否已创建")
        print(f"   2. 文件夹名称格式是否为: {today}")
