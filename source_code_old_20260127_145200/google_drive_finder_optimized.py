#!/usr/bin/env python3
"""
自动查找Google Drive中当日文件夹里最后更新的txt文件
针对文件命名格式优化: YYYY-MM-DD_HHMM.txt
例如: 2025-12-02_1806.txt (2025年12月2日 18:06)
"""

import os
import sys
import re
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

def parse_filename_timestamp(filename):
    """
    从文件名中解析时间戳
    格式: YYYY-MM-DD_HHMM.txt
    例如: 2025-12-02_1806.txt
    
    Args:
        filename: 文件名
        
    Returns:
        datetime对象，如果解析失败返回None
    """
    # 匹配格式: YYYY-MM-DD_HHMM.txt
    pattern = r'(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})\.txt'
    match = re.match(pattern, filename)
    
    if match:
        year, month, day, hour, minute = match.groups()
        try:
            dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
            beijing_tz = pytz.timezone('Asia/Shanghai')
            dt = beijing_tz.localize(dt)
            return dt
        except ValueError:
            return None
    return None

def get_drive_service(credentials_file='credentials.json'):
    """创建Google Drive API服务对象"""
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
    """在指定父文件夹中查找指定名称的子文件夹"""
    try:
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
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
    """列出指定文件夹中的所有txt文件"""
    try:
        query = f"'{folder_id}' in parents and trashed=false and name contains '.txt'"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, size)',
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        
        # 过滤确保是txt文件
        txt_files = [f for f in files if f['name'].endswith('.txt')]
        
        return txt_files
        
    except HttpError as error:
        print(f"❌ API错误: {error}")
        return []

def sort_files_by_filename_timestamp(files):
    """
    根据文件名中的时间戳排序
    
    Args:
        files: 文件列表
        
    Returns:
        排序后的文件列表（最新的在前）
    """
    files_with_time = []
    files_without_time = []
    
    for file in files:
        timestamp = parse_filename_timestamp(file['name'])
        if timestamp:
            files_with_time.append((file, timestamp))
        else:
            files_without_time.append(file)
    
    # 按时间戳降序排序（最新的在前）
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # 返回排序后的文件列表
    sorted_files = [f[0] for f in files_with_time] + files_without_time
    
    return sorted_files, files_with_time

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

def format_timestamp(dt):
    """格式化时间戳为易读格式"""
    return dt.strftime('%Y-%m-%d %H:%M (北京时间)')

def main():
    print("=" * 80)
    print("📁 Google Drive 当日文件夹最新txt文件查找器 (优化版)")
    print("=" * 80)
    print("文件命名格式: YYYY-MM-DD_HHMM.txt")
    print("例如: 2025-12-02_1806.txt = 2025年12月2日 18:06")
    print("=" * 80)
    
    # 获取北京时间今天的日期
    beijing_date = get_beijing_date()
    print(f"\n📅 北京时间今天的日期: {beijing_date}")
    
    # 检查凭证文件
    credentials_file = 'credentials.json'
    if not os.path.exists(credentials_file):
        print(f"\n❌ 错误: 未找到凭证文件 {credentials_file}")
        print("\n请运行设置向导: python3 setup_guide.py")
        print(f"或查看详细说明: USAGE_CN.md")
        return 1
    
    # 创建Drive服务
    print(f"\n🔐 正在加载凭证文件...")
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
    
    # 按文件名中的时间戳排序
    print(f"\n🔄 正在按文件名时间戳排序...")
    sorted_files, files_with_time = sort_files_by_filename_timestamp(txt_files)
    
    print("\n" + "=" * 80)
    print("文件列表 (按文件名时间戳降序):")
    print("=" * 80)
    
    for idx, (file, timestamp) in enumerate(files_with_time, 1):
        print(f"\n[{idx}] {file['name']}")
        print(f"    文件ID: {file['id']}")
        print(f"    文件时间: {format_timestamp(timestamp)}")
        if 'size' in file:
            print(f"    文件大小: {format_size(file['size'])}")
    
    # 如果有无法解析时间的文件，也列出来
    files_without_parsed_time = sorted_files[len(files_with_time):]
    if files_without_parsed_time:
        print("\n" + "-" * 80)
        print("以下文件无法从文件名解析时间（格式不匹配）:")
        print("-" * 80)
        for idx, file in enumerate(files_without_parsed_time, len(files_with_time) + 1):
            print(f"\n[{idx}] {file['name']}")
            print(f"    文件ID: {file['id']}")
            if 'size' in file:
                print(f"    文件大小: {format_size(file['size'])}")
    
    # 最新的文件
    if sorted_files:
        latest_file = sorted_files[0]
        latest_timestamp = parse_filename_timestamp(latest_file['name'])
        
        print("\n" + "=" * 80)
        print("🎯 最后更新的txt文件:")
        print("=" * 80)
        print(f"文件名: {latest_file['name']}")
        print(f"文件ID: {latest_file['id']}")
        if latest_timestamp:
            print(f"文件时间: {format_timestamp(latest_timestamp)}")
        if 'size' in latest_file:
            print(f"文件大小: {format_size(latest_file['size'])}")
        print(f"文件链接: https://drive.google.com/file/d/{latest_file['id']}/view")
        print("=" * 80)
        
        # 简洁输出（用于自动化）
        print("\n" + "=" * 80)
        print("📌 简洁答案:")
        print("=" * 80)
        print(f"最新txt文件: {latest_file['name']}")
        if latest_timestamp:
            # 解析文件名中的时间
            time_str = latest_file['name'].split('_')[1].replace('.txt', '')
            hour = time_str[:2]
            minute = time_str[2:4]
            print(f"更新时间: {beijing_date} {hour}:{minute}")
        print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
