#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于rclone的Google Drive自动更新器
使用rclone直接访问Google Drive，无需JavaScript渲染
"""

import os
import sys
import subprocess
import sqlite3
import re
from datetime import datetime
import pytz
import logging
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/auto_gdrive_updater_rclone.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 配置
RCLONE_REMOTE = 'gdrive'  # rclone远程名称
GDRIVE_BASE_PATH = '首页数据'  # Google Drive中的基础路径
DB_PATH = '/home/user/webapp/databases/crypto_data.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def check_rclone_config():
    """检查rclone是否已配置"""
    try:
        result = subprocess.run(
            ['rclone', 'listremotes'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        remotes = result.stdout.strip().split('\n')
        remotes = [r.rstrip(':') for r in remotes if r]
        
        if RCLONE_REMOTE in remotes:
            logger.info(f"✅ rclone远程'{RCLONE_REMOTE}'已配置")
            return True
        else:
            logger.error(f"❌ rclone远程'{RCLONE_REMOTE}'未配置")
            logger.error(f"可用的远程: {remotes}")
            logger.error(f"请运行: rclone config")
            return False
            
    except Exception as e:
        logger.error(f"❌ 检查rclone配置失败: {e}")
        return False

def list_folders_in_path(path):
    """列出指定路径下的所有文件夹"""
    try:
        remote_path = f'{RCLONE_REMOTE}:{path}'
        
        result = subprocess.run(
            ['rclone', 'lsf', '--dirs-only', remote_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"rclone lsf失败: {result.stderr}")
            return []
        
        folders = [f.rstrip('/') for f in result.stdout.strip().split('\n') if f]
        return folders
        
    except Exception as e:
        logger.error(f"列出文件夹失败: {e}")
        return []

def list_txt_files_in_folder(folder_path):
    """列出文件夹中的所有TXT文件"""
    try:
        remote_path = f'{RCLONE_REMOTE}:{folder_path}'
        
        result = subprocess.run(
            ['rclone', 'lsf', '--files-only', '--include', '*.txt', remote_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"列出TXT文件失败: {result.stderr}")
            return []
        
        files = [f for f in result.stdout.strip().split('\n') if f.endswith('.txt')]
        return sorted(files)
        
    except Exception as e:
        logger.error(f"列出TXT文件失败: {e}")
        return []

def download_file_content(file_path):
    """下载文件内容"""
    try:
        remote_path = f'{RCLONE_REMOTE}:{file_path}'
        
        result = subprocess.run(
            ['rclone', 'cat', remote_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.error(f"下载文件失败: {result.stderr}")
            return None
        
        return result.stdout
        
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return None

def check_if_imported(snapshot_time):
    """检查是否已导入"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM crypto_snapshots 
            WHERE snapshot_time = ?
        """, (snapshot_time,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    except Exception as e:
        logger.error(f"检查导入状态失败: {e}")
        return False

def import_txt_file(filename, content):
    """导入TXT文件到数据库"""
    try:
        # 解析文件名 (格式: YYYY-MM-DD_HHMM.txt)
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
        if not match:
            logger.warning(f"文件名格式错误: {filename}")
            return False
        
        date_part = match.group(1)
        time_part = match.group(2)
        snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
        
        # 检查是否已导入
        if check_if_imported(snapshot_time):
            logger.info(f"   ⚠️ 已存在，跳过: {filename}")
            return False
        
        # 插入数据库
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO crypto_snapshots (snapshot_time, data_content, source)
            VALUES (?, ?, 'gdrive_rclone')
        """, (snapshot_time, content))
        
        conn.commit()
        conn.close()
        
        logger.info(f"   ✅ 导入成功: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"导入失败: {filename}, 错误: {e}")
        return False

def process_date_folder(date_folder):
    """处理单个日期文件夹"""
    logger.info(f"\n📁 处理文件夹: {date_folder}")
    
    folder_path = f'{GDRIVE_BASE_PATH}/{date_folder}'
    
    # 列出TXT文件
    txt_files = list_txt_files_in_folder(folder_path)
    
    if not txt_files:
        logger.warning(f"   未找到TXT文件")
        return 0
    
    logger.info(f"   找到 {len(txt_files)} 个TXT文件")
    
    # 逐个处理
    success_count = 0
    for txt_file in txt_files:
        file_path = f'{folder_path}/{txt_file}'
        
        # 下载内容
        content = download_file_content(file_path)
        if not content:
            continue
        
        # 导入数据库
        if import_txt_file(txt_file, content):
            success_count += 1
    
    return success_count

def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 基于rclone的Google Drive自动更新器")
    logger.info("=" * 80)
    
    # 检查rclone配置
    if not check_rclone_config():
        logger.error("\n请先配置rclone:")
        logger.error("1. 运行: rclone config")
        logger.error("2. 选择: n (新建远程)")
        logger.error("3. 名称: gdrive")
        logger.error("4. 存储类型: drive (Google Drive)")
        logger.error("5. 按提示完成OAuth认证")
        sys.exit(1)
    
    # 获取今天的日期
    current_time = datetime.now(BEIJING_TZ)
    today = current_time.strftime('%Y-%m-%d')
    
    logger.info(f"\n今天日期: {today}")
    
    # 列出首页数据文件夹中的所有日期文件夹
    logger.info(f"\n📂 列出'{GDRIVE_BASE_PATH}'中的文件夹...")
    date_folders = list_folders_in_path(GDRIVE_BASE_PATH)
    
    if not date_folders:
        logger.error("未找到任何日期文件夹")
        sys.exit(1)
    
    # 过滤出日期格式的文件夹
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    date_folders = [f for f in date_folders if date_pattern.match(f)]
    date_folders.sort(reverse=True)
    
    logger.info(f"找到 {len(date_folders)} 个日期文件夹")
    logger.info(f"最新的5个: {date_folders[:5]}")
    
    # 检查今天的文件夹是否存在
    if today not in date_folders:
        logger.warning(f"\n⚠️ 未找到今天的文件夹: {today}")
        logger.info(f"最新的文件夹是: {date_folders[0] if date_folders else '无'}")
    else:
        logger.info(f"\n✅ 找到今天的文件夹: {today}")
        
        # 处理今天的文件夹
        success_count = process_date_folder(today)
        
        logger.info(f"\n📊 导入统计: 成功导入 {success_count} 个文件")

if __name__ == '__main__':
    main()
