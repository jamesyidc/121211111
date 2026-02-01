#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Google Drive直接下载并导入TXT文件
用户只需提供2026-01-18文件夹的链接即可
"""

import os
import sys
import requests
import re
import sqlite3
from datetime import datetime
import pytz

DB_PATH = '/home/user/webapp/databases/crypto_data.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def extract_folder_id(url_or_id):
    """从URL或直接ID中提取文件夹ID"""
    if 'drive.google.com' in url_or_id:
        match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url_or_id)
        if match:
            return match.group(1)
    return url_or_id

def get_txt_files_from_folder(folder_id):
    """从Google Drive文件夹获取所有TXT文件"""
    print(f"\n📁 访问文件夹: {folder_id}")
    url = f'https://drive.google.com/drive/folders/{folder_id}'
    
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ 访问失败，状态码: {response.status_code}")
            return []
        
        content = response.text
        
        # 查找所有TXT文件 (格式: YYYY-MM-DD_HHMM.txt)
        pattern = r'"(202[0-9]-[01][0-9]-[0-3][0-9]_[0-2][0-9][0-5][0-9]\.txt)"[^}]*?"id":"([^"]+)"'
        matches = re.findall(pattern, content)
        
        if not matches:
            print("⚠️ 未找到TXT文件")
            return []
        
        print(f"✅ 找到 {len(matches)} 个TXT文件")
        
        txt_files = []
        for filename, file_id in matches:
            txt_files.append({
                'filename': filename,
                'file_id': file_id,
                'download_url': f'https://drive.google.com/uc?id={file_id}&export=download'
            })
        
        return sorted(txt_files, key=lambda x: x['filename'])
        
    except Exception as e:
        print(f"❌ 获取文件列表失败: {e}")
        return []

def download_and_import_txt(file_info):
    """下载并导入单个TXT文件"""
    filename = file_info['filename']
    download_url = file_info['download_url']
    
    print(f"\n  📄 {filename}")
    
    try:
        # 解析文件名获取时间
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
        if not match:
            print(f"     ❌ 文件名格式错误")
            return False
        
        date_part = match.group(1)
        time_part = match.group(2)
        snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
        
        # 检查是否已导入
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crypto_snapshots WHERE snapshot_time = ?", (snapshot_time,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            print(f"     ⚠️ 已存在，跳过")
            return False
        conn.close()
        
        # 下载文件内容
        print(f"     ⬇️ 下载中...")
        response = requests.get(download_url, timeout=30)
        
        if response.status_code != 200:
            print(f"     ❌ 下载失败，状态码: {response.status_code}")
            return False
        
        content = response.text.strip()
        
        if not content:
            print(f"     ❌ 文件内容为空")
            return False
        
        print(f"     📊 大小: {len(content)} 字节")
        
        # 导入数据库
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO crypto_snapshots (snapshot_time, data_content, source)
            VALUES (?, ?, 'gdrive_manual')
        """, (snapshot_time, content))
        
        conn.commit()
        conn.close()
        
        print(f"     ✅ 导入成功")
        return True
        
    except Exception as e:
        print(f"     ❌ 失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print("🚀 Google Drive TXT文件批量导入工具")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  python3 gdrive_batch_import.py <文件夹链接或ID>")
        print("\n示例:")
        print("  python3 gdrive_batch_import.py https://drive.google.com/drive/folders/1abcdefg...")
        print("  python3 gdrive_batch_import.py 1abcdefg...")
        print("\n说明:")
        print("  请提供2026-01-18文件夹的Google Drive链接")
        sys.exit(1)
    
    folder_input = sys.argv[1]
    folder_id = extract_folder_id(folder_input)
    
    print(f"\n文件夹ID: {folder_id}")
    print(f"链接: https://drive.google.com/drive/folders/{folder_id}")
    
    # 获取文件列表
    txt_files = get_txt_files_from_folder(folder_id)
    
    if not txt_files:
        print("\n❌ 没有找到TXT文件")
        sys.exit(1)
    
    print(f"\n共找到 {len(txt_files)} 个TXT文件")
    
    # 询问是否继续
    print("\n是否开始导入？(y/n): ", end='')
    choice = input().lower().strip()
    
    if choice != 'y':
        print("取消导入")
        sys.exit(0)
    
    # 批量导入
    print("\n" + "=" * 80)
    print("开始导入")
    print("=" * 80)
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for file_info in txt_files:
        result = download_and_import_txt(file_info)
        if result:
            success_count += 1
        elif result is False:
            # 检查是否因为已存在而跳过
            filename = file_info['filename']
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
            if match:
                date_part = match.group(1)
                time_part = match.group(2)
                snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
                
                conn = sqlite3.connect(DB_PATH, timeout=10.0)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM crypto_snapshots WHERE snapshot_time = ?", (snapshot_time,))
                if cursor.fetchone()[0] > 0:
                    skip_count += 1
                else:
                    fail_count += 1
                conn.close()
    
    # 统计
    print("\n" + "=" * 80)
    print("📊 导入统计")
    print("=" * 80)
    print(f"✅ 成功导入: {success_count} 个")
    print(f"⚠️ 已存在跳过: {skip_count} 个")
    print(f"❌ 导入失败: {fail_count} 个")
    print(f"📁 总计文件: {len(txt_files)} 个")
    
    if success_count > 0:
        print("\n🎉 导入完成！")
        print("\n查看结果:")
        print("  访问: https://5000-xxx.sandbox.novita.ai/gdrive-detector")

if __name__ == '__main__':
    main()
