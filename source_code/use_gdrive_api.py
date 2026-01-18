import requests
from bs4 import BeautifulSoup
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

# 方法1: 尝试使用Google Drive的RSS feed
print("方法1: 尝试RSS feed...")
try:
    rss_url = f"https://drive.google.com/feed/folders/{FOLDER_ID}"
    response = requests.get(rss_url, timeout=10)
    print(f"RSS状态码: {response.status_code}")
    if response.status_code == 200:
        print("RSS内容长度:", len(response.text))
except Exception as e:
    print(f"RSS失败: {e}")

# 方法2: 尝试Google Drive的JSON API（公开）
print("\n方法2: 尝试JSON API...")
try:
    json_url = f"https://www.googleapis.com/drive/v3/files?q='{FOLDER_ID}'+in+parents&key=AIzaSyDummy"
    response = requests.get(json_url, timeout=10)
    print(f"JSON API状态码: {response.status_code}")
except Exception as e:
    print(f"JSON API失败: {e}")

# 方法3: 尝试直接请求文件夹页面的完整内容
print("\n方法3: 直接请求完整HTML...")
try:
    url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=20)
    print(f"HTML状态码: {response.status_code}")
    
    # 在HTML中查找所有文件时间
    times = re.findall(r'2025-12-06_(\d{4})', response.text)
    if times:
        unique_times = sorted(set(times))
        print(f"找到 {len(unique_times)} 个唯一时间戳")
        print(f"最后10个: {unique_times[-10:]}")
        print(f"最新: {unique_times[-1]}")
    else:
        print("未找到时间戳")
        
    # 查找是否有分页信息
    if 'nextPageToken' in response.text:
        print("✓ 发现分页token")
    if 'pageToken' in response.text:
        print("✓ 发现页面token")
        
except Exception as e:
    print(f"HTML请求失败: {e}")

# 方法4: 检查是否有API密钥或认证信息
print("\n方法4: 检查本地是否有Google API配置...")
import os
home = os.path.expanduser("~")
possible_configs = [
    os.path.join(home, '.config/gcloud'),
    os.path.join(home, '.google'),
    '/home/user/webapp/credentials.json',
    '/home/user/webapp/token.json',
]
for config in possible_configs:
    if os.path.exists(config):
        print(f"✓ 找到配置: {config}")

