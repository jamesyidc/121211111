#!/usr/bin/env python3
"""
使用 Google Drive API 获取最新文件
注意：需要 OAuth 认证才能突破限制
"""

from googleapiclient.discovery import build
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def try_api_key_method():
    """尝试使用API密钥（公开文件夹）"""
    print("方法1: 尝试无认证访问（公开文件夹）...")
    try:
        # 尝试构建无认证的服务
        service = build('drive', 'v3', developerKey='', cache_discovery=False)
        
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and name contains '2025-12-06'",
            pageSize=100,
            fields="files(id, name, modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        print(f"找到 {len(files)} 个文件")
        return files
        
    except Exception as e:
        print(f"失败: {e}")
        return None

def try_oauth_method():
    """尝试使用OAuth认证"""
    print("\n方法2: 尝试OAuth认证...")
    
    creds = None
    # token.pickle存储用户的访问和刷新令牌
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # 如果没有有效凭证
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists('credentials.json'):
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            # 保存凭证供下次使用
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        else:
            print("需要 credentials.json 文件")
            return None
    
    try:
        service = build('drive', 'v3', credentials=creds)
        
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and name contains '2025-12-06'",
            pageSize=100,
            orderBy='modifiedTime desc',
            fields="files(id, name, modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        print(f"找到 {len(files)} 个文件")
        return files
        
    except Exception as e:
        print(f"失败: {e}")
        return None

# 尝试两种方法
files = try_api_key_method()

if not files:
    files = try_oauth_method()

if files:
    print("\n最新10个文件:")
    for f in files[:10]:
        print(f"  - {f['name']} (modified: {f.get('modifiedTime', 'N/A')})")
else:
    print("\n" + "="*70)
    print("无法使用Google Drive API突破限制")
    print("需要：")
    print("1. Google Cloud项目的credentials.json文件")
    print("2. OAuth 2.0认证")
    print("="*70)

