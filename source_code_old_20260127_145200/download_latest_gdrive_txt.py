#!/usr/bin/env python3
"""
从Google Drive下载并解析最新TXT文件
"""
import requests
import re
from datetime import datetime

# 文件信息
folder_id = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"
filename = "2025-12-09_1758.txt"

print(f"📥 正在下载文件: {filename}")
print(f"   从文件夹: {folder_id}")
print()

# Google Drive文件下载需要获取文件ID
# 方法1: 尝试通过embed view获取文件ID
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 获取文件夹内容
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    response = requests.get(embed_url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        content = response.text
        
        # 查找文件ID (Google Drive的文件ID通常在URL中)
        # 格式可能是: "id":"xxxxxx" 或者在链接中
        
        # 尝试从响应中提取文件列表JSON数据
        # Google Drive embed view返回的是JavaScript渲染的，我们需要找到文件ID
        
        # 让我们尝试构造直接下载URL
        # Google Drive的直接下载URL格式为:
        # https://drive.google.com/uc?export=download&id=FILE_ID
        
        # 但我们首先需要文件ID...
        # 由于我们无法直接获取文件ID，我们使用另一种方法：
        # 通过folder的export功能
        
        print("⚠️  无法直接获取文件ID，尝试alternative方法...")
        print()
        
        # Alternative: 使用已知的文件夹结构，直接构造可能的文件访问URL
        # 或者，我们可以使用crawler工具来获取文件内容
        
        print("✅ 使用crawler工具获取文件内容...")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("正在尝试使用crawler工具获取文件内容...")
print("="*60)

