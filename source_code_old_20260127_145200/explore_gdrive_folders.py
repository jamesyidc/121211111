#!/usr/bin/env python3
"""
探索 Google Drive 文件夹结构
Find the correct folder IDs from the grandparent folder
"""
import os
import sys

# Try to import Google API libraries
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    print("✅ Google API libraries imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Google API libraries: {e}")
    print("Please install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate():
    """Authenticate with Google Drive API"""
    creds = None
    token_path = 'token.pickle'
    credentials_path = 'credentials.json'
    
    # Check for existing token
    if os.path.exists(token_path):
        from pickle import load
        with open(token_path, 'rb') as token:
            creds = load(token)
    
    # If no valid credentials, try to authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(credentials_path):
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            print(f"❌ Credentials file not found: {credentials_path}")
            print("Available files:")
            for f in os.listdir('.'):
                if 'credential' in f.lower() or 'token' in f.lower():
                    print(f"   - {f}")
            return None
        
        # Save the credentials for the next run
        from pickle import dump
        with open(token_path, 'wb') as token:
            dump(creds, token)
    
    return creds

def list_folders(service, parent_id, indent=0):
    """List all folders in a parent folder"""
    try:
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, mimeType, createdTime, modifiedTime)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print(f"{'  ' * indent}   (No subfolders)")
            return []
        
        folders = []
        for item in items:
            print(f"{'  ' * indent}📁 {item['name']}")
            print(f"{'  ' * indent}   ID: {item['id']}")
            print(f"{'  ' * indent}   Created: {item.get('createdTime', 'N/A')}")
            print(f"{'  ' * indent}   Modified: {item.get('modifiedTime', 'N/A')}")
            folders.append(item)
        
        return folders
    
    except Exception as e:
        print(f"{'  ' * indent}❌ Error listing folders: {e}")
        return []

def count_files_in_folder(service, folder_id):
    """Count TXT files in a folder"""
    try:
        query = f"'{folder_id}' in parents and mimeType='text/plain' and trashed=false"
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        return len(items)
    except:
        return 0

def main():
    print("=" * 80)
    print("🔍 Google Drive 文件夹结构探索工具")
    print("=" * 80)
    print()
    
    # Grandparent folder ID from the shared link
    # https://drive.google.com/drive/folders/1U5VjRis2FYnBJvtR_8mmPrmFcJCMPGrH?usp=sharing
    grandparent_id = "1U5VjRis2FYnBJvtR_8mmPrmFcJCMPGrH"
    
    print(f"🎯 目标: 在爷爷文件夹中找到【首页数据】文件夹")
    print(f"📁 爷爷文件夹 ID: {grandparent_id}")
    print()
    
    # Authenticate
    print("🔐 正在认证...")
    creds = authenticate()
    if not creds:
        print("❌ Authentication failed")
        return
    
    try:
        service = build('drive', 'v3', credentials=creds)
        print("✅ Google Drive API 连接成功")
        print()
        
        # List folders in grandparent
        print("=" * 80)
        print("📂 爷爷文件夹的子文件夹:")
        print("=" * 80)
        level1_folders = list_folders(service, grandparent_id, indent=0)
        print()
        
        # Find "首页数据" folder
        homepage_folder = None
        for folder in level1_folders:
            if "首页" in folder['name'] or "数据" in folder['name']:
                homepage_folder = folder
                print(f"✅ 找到【首页数据】文件夹: {folder['name']}")
                print(f"   ID: {folder['id']}")
                print()
                break
        
        if not homepage_folder:
            print("⚠️ 未找到【首页数据】文件夹，显示所有子文件夹供选择:")
            for i, folder in enumerate(level1_folders, 1):
                file_count = count_files_in_folder(service, folder['id'])
                print(f"{i}. {folder['name']} (ID: {folder['id']}, {file_count} TXT files)")
            return
        
        # List folders in "首页数据"
        print("=" * 80)
        print(f"📂【首页数据】的子文件夹:")
        print("=" * 80)
        level2_folders = list_folders(service, homepage_folder['id'], indent=1)
        print()
        
        # Find today's folder or "可行" folder
        today = "2025-12-21"
        target_folder = None
        
        for folder in level2_folders:
            if today in folder['name'] or "可行" in folder['name']:
                target_folder = folder
                print(f"✅ 找到目标文件夹: {folder['name']}")
                print(f"   ID: {folder['id']}")
                
                # Count TXT files
                file_count = count_files_in_folder(service, folder['id'])
                print(f"   📄 TXT 文件数量: {file_count}")
                print()
                break
        
        # Summary
        print("=" * 80)
        print("📋 配置摘要:")
        print("=" * 80)
        print(f"爷爷文件夹 ID: {grandparent_id}")
        if homepage_folder:
            print(f"【首页数据】 ID: {homepage_folder['id']} ← 这是 parent_folder_id")
        if target_folder:
            print(f"【{target_folder['name']}】 ID: {target_folder['id']} ← 这是 folder_id")
        print()
        
        if homepage_folder and target_folder:
            print("✅ 建议更新 daily_folder_config.json:")
            print(f'''{{
    "current_date": "{today}",
    "folder_id": "{target_folder['id']}",
    "parent_folder_id": "{homepage_folder['id']}",
    "updated_at": "手动更新",
    "auto_updated": false,
    "file_count": {count_files_in_folder(service, target_folder['id'])}
}}''')
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
