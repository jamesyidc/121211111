#!/usr/bin/env python3
"""
自动查找Google Drive中当日文件夹里最后更新的txt文件
使用Google Drive API v3
"""

import os
import sys
from datetime import datetime
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Drive 主文件夹ID
MAIN_FOLDER_ID = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"

# API 权限范围
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_beijing_date():
    """获取北京时间的今天日期，格式：YYYY-MM-DD"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    beijing_time = datetime.now(beijing_tz)
    return beijing_time.strftime('%Y-%m-%d')

def get_drive_service(credentials_file='credentials.json'):
    """
    创建Google Drive API服务对象
    
    Args:
        credentials_file: Service Account凭证文件路径
        
    Returns:
        Google Drive API服务对象
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"❌ 创建Drive服务失败: {e}")
        print(f"请确保 {credentials_file} 文件存在且格式正确")
        return None

def find_folder_by_name(service, parent_folder_id, folder_name):
    """
    在指定父文件夹中查找指定名称的子文件夹
    
    Args:
        service: Google Drive API服务对象
        parent_folder_id: 父文件夹ID
        folder_name: 要查找的文件夹名称
        
    Returns:
        文件夹ID，如果未找到返回None
    """
    try:
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, createdTime, modifiedTime)',
            pageSize=10
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            print(f"⚠️  未找到文件夹: {folder_name}")
            return None
        
        if len(files) > 1:
            print(f"⚠️  找到多个同名文件夹: {folder_name}，使用第一个")
        
        folder = files[0]
        print(f"✅ 找到文件夹: {folder['name']} (ID: {folder['id']})")
        return folder['id']
        
    except HttpError as error:
        print(f"❌ API错误: {error}")
        return None

def list_txt_files(service, folder_id):
    """
    列出指定文件夹中的所有txt文件，按修改时间降序排列
    
    Args:
        service: Google Drive API服务对象
        folder_id: 文件夹ID
        
    Returns:
        txt文件列表
    """
    try:
        query = f"'{folder_id}' in parents and trashed=false and (name contains '.txt' or mimeType='text/plain')"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, createdTime, modifiedTime, size)',
            orderBy='modifiedTime desc',
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        
        # 过滤确保是txt文件
        txt_files = [f for f in files if f['name'].endswith('.txt')]
        
        return txt_files
        
    except HttpError as error:
        print(f"❌ API错误: {error}")
        return []

def format_datetime(datetime_str):
    """格式化日期时间字符串为更易读的格式"""
    try:
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        beijing_tz = pytz.timezone('Asia/Shanghai')
        beijing_dt = dt.astimezone(beijing_tz)
        return beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return datetime_str

def format_size(size_bytes):
    """格式化文件大小"""
    try:
        size = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    except:
        return "Unknown"

def main():
    print("=" * 80)
    print("📁 Google Drive 当日文件夹最新txt文件查找器")
    print("=" * 80)
    
    # 获取北京时间今天的日期
    beijing_date = get_beijing_date()
    print(f"\n📅 北京时间今天的日期: {beijing_date}")
    
    # 检查凭证文件
    credentials_file = 'credentials.json'
    if not os.path.exists(credentials_file):
        print(f"\n❌ 错误: 未找到凭证文件 {credentials_file}")
        print("\n请按以下步骤设置Google Drive API访问:")
        print("1. 访问 https://console.cloud.google.com/")
        print("2. 创建新项目或选择现有项目")
        print("3. 启用 Google Drive API")
        print("4. 创建 Service Account")
        print("5. 下载 JSON 密钥文件并重命名为 credentials.json")
        print("6. 将 Google Drive 文件夹共享给 Service Account 的邮箱地址")
        print(f"7. 将 credentials.json 放在当前目录: {os.getcwd()}")
        return 1
    
    # 创建Drive服务
    print(f"\n🔐 正在加载凭证文件: {credentials_file}")
    service = get_drive_service(credentials_file)
    if not service:
        return 1
    
    print("✅ Drive API服务已创建")
    
    # 查找今天的文件夹
    print(f"\n🔍 正在查找文件夹: {beijing_date}")
    today_folder_id = find_folder_by_name(service, MAIN_FOLDER_ID, beijing_date)
    
    if not today_folder_id:
        print(f"\n❌ 未找到今天的文件夹: {beijing_date}")
        print("可能的原因:")
        print("  1. 文件夹尚未创建")
        print("  2. Service Account没有访问权限")
        print("  3. 文件夹名称格式不匹配")
        return 1
    
    # 列出所有txt文件
    print(f"\n📄 正在查找txt文件...")
    txt_files = list_txt_files(service, today_folder_id)
    
    if not txt_files:
        print(f"\n⚠️  文件夹中没有找到txt文件")
        return 1
    
    print(f"\n✅ 找到 {len(txt_files)} 个txt文件")
    print("\n" + "=" * 80)
    print("文件列表 (按修改时间降序):")
    print("=" * 80)
    
    for idx, file in enumerate(txt_files, 1):
        print(f"\n[{idx}] {file['name']}")
        print(f"    文件ID: {file['id']}")
        print(f"    修改时间: {format_datetime(file['modifiedTime'])} (北京时间)")
        print(f"    创建时间: {format_datetime(file['createdTime'])} (北京时间)")
        if 'size' in file:
            print(f"    文件大小: {format_size(file['size'])}")
    
    # 最新的文件
    latest_file = txt_files[0]
    print("\n" + "=" * 80)
    print("🎯 最后更新的txt文件:")
    print("=" * 80)
    print(f"文件名: {latest_file['name']}")
    print(f"文件ID: {latest_file['id']}")
    print(f"修改时间: {format_datetime(latest_file['modifiedTime'])} (北京时间)")
    print(f"文件链接: https://drive.google.com/file/d/{latest_file['id']}/view")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
