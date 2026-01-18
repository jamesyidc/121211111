#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动Google Drive数据更新器 - 工作版本
使用嵌入式视图获取文件列表，不需要OAuth认证
"""

import os
import sys
import time
import sqlite3
import requests
import re
from datetime import datetime
import pytz
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/auto_gdrive_updater.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 配置
HOME_DATA_FOLDER_ID = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'  # 首页数据文件夹ID
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
CHECK_INTERVAL = 600  # 10分钟
DB_PATH = '/home/user/webapp/databases/crypto_data.db'


def get_date_folder_id(parent_folder_id, target_date):
    """
    从父文件夹中获取指定日期文件夹的ID
    使用嵌入式视图方法
    """
    try:
        embed_url = f"https://drive.google.com/embeddedfolderview?id={parent_folder_id}#list"
        response = requests.get(embed_url, timeout=30)
        html = response.text
        
        # 查找所有<a>标签
        a_tags = re.findall(r'<a[^>]+>.*?</a>', html, re.DOTALL)
        
        for tag in a_tags:
            if target_date in tag:
                # 提取href中的文件夹ID
                href_match = re.search(r'href="https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]{33})"', tag)
                if href_match:
                    folder_id = href_match.group(1)
                    logger.info(f"找到文件夹ID: {folder_id}")
                    return folder_id
        
        logger.warning(f"未找到文件夹: {target_date}")
        return None
        
    except Exception as e:
        logger.error(f"获取日期文件夹ID失败: {e}")
        return None


def get_txt_files_from_folder(folder_id, target_date):
    """
    从文件夹中获取所有TXT文件列表
    """
    try:
        embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
        response = requests.get(embed_url, timeout=30)
        html = response.text
        
        # 查找所有TXT文件名
        txt_pattern = rf'({re.escape(target_date)}_\d{{4}})\.txt'
        txt_files = re.findall(txt_pattern, html)
        unique_files = sorted(set(txt_files), reverse=True)
        
        if not unique_files:
            logger.warning(f"未找到TXT文件")
            return []
        
        logger.info(f"找到 {len(unique_files)} 个TXT文件")
        
        # 获取每个文件的ID和下载链接
        files_info = []
        for filename in unique_files:
            # 在HTML中查找文件名附近的ID
            file_pattern = rf'{re.escape(filename)}\.txt.*?href="https://drive\.google\.com/file/d/([a-zA-Z0-9_-]{{33}})'
            matches = re.findall(file_pattern, html, re.DOTALL)
            
            if not matches:
                # 备用方案：查找任何包含文件名的链接
                file_pattern2 = rf'{re.escape(filename)}.*?([a-zA-Z0-9_-]{{33}})'
                matches = re.findall(file_pattern2, html)
            
            if matches:
                file_id = matches[0]
                download_url = f'https://drive.google.com/uc?id={file_id}&export=download'
                
                files_info.append({
                    'filename': f'{filename}.txt',
                    'file_id': file_id,
                    'download_url': download_url,
                    'time': filename.split('_')[1]  # 提取时间部分
                })
        
        return files_info
        
    except Exception as e:
        logger.error(f"获取TXT文件列表失败: {e}")
        return []


def get_latest_txt_file():
    """获取Google Drive中最新的TXT文件"""
    try:
        current_time = datetime.now(BEIJING_TZ)
        folder_name = current_time.strftime('%Y-%m-%d')
        
        logger.info(f"检查文件夹: {folder_name}")
        
        # 1. 获取日期文件夹ID
        date_folder_id = get_date_folder_id(HOME_DATA_FOLDER_ID, folder_name)
        if not date_folder_id:
            return None
        
        logger.info(f"找到文件夹ID: {date_folder_id}")
        
        # 2. 获取文件夹中的TXT文件
        txt_files = get_txt_files_from_folder(date_folder_id, folder_name)
        if not txt_files:
            return None
        
        # 3. 返回最新文件
        latest_file = txt_files[0]
        logger.info(f"最新文件: {latest_file['filename']}")
        return latest_file
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return None


def check_if_imported(filename):
    """检查文件是否已导入"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 从文件名提取时间
        # 格式: 2026-01-18_1800.txt -> 2026-01-18 18:00:00
        date_part, time_part = filename.replace('.txt', '').split('_')
        snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
        
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


def download_and_import(file_info):
    """下载并导入TXT文件"""
    try:
        filename = file_info['filename']
        download_url = file_info['download_url']
        
        logger.info(f"开始下载: {filename}")
        
        # 下载文件
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()
        
        # 保存到临时文件
        temp_file = f'/tmp/{filename}'
        with open(temp_file, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"文件已下载到: {temp_file}")
        
        # 转换编码为UTF-8（如果需要）
        temp_utf8_file = temp_file  # 先尝试直接使用
        try:
            # 尝试以UTF-8读取
            with open(temp_file, 'r', encoding='utf-8') as f:
                f.read()
        except UnicodeDecodeError:
            # 如果失败，进行编码转换
            temp_utf8_file = f'/tmp/{filename.replace(".txt", "_utf8.txt")}'
            os.system(f'iconv -f GBK -t UTF-8 "{temp_file}" > "{temp_utf8_file}" 2>/dev/null')
            logger.info(f"已转换编码")
        
        # 直接使用自己的导入逻辑
        success = import_txt_to_db(temp_utf8_file, filename)  # 传递原始文件名
        
        # 清理临时文件
        try:
            os.remove(temp_file)
            if temp_utf8_file != temp_file:
                os.remove(temp_utf8_file)
        except:
            pass
        
        if success:
            logger.info(f"✓ 成功导入: {filename}")
            return True
        else:
            logger.error(f"✗ 导入失败: {filename}")
            return False
            
    except Exception as e:
        logger.error(f"下载或导入失败: {e}")
        return False


def import_txt_to_db(file_path, original_filename=None):
    """导入TXT文件到数据库"""
    try:
        # 使用原始文件名来解析时间
        filename = original_filename if original_filename else os.path.basename(file_path)
        
        # 解析文件名: YYYY-MM-DD_HHMM.txt
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
        if not match:
            logger.error(f"文件名格式错误: {filename}")
            return False
        
        date_part = match.group(1)
        time_part = match.group(2)
        snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            logger.error(f"文件内容为空")
            return False
        
        # 插入数据库
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO crypto_snapshots (snapshot_time, data_content, source)
            VALUES (?, ?, 'gdrive_auto')
        """, (snapshot_time, content))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"导入数据库失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("自动Google Drive数据更新器启动")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒 ({CHECK_INTERVAL // 60}分钟)")
    logger.info("=" * 80)
    
    while True:
        try:
            current_time = datetime.now(BEIJING_TZ)
            logger.info("")
            logger.info(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 开始检查...")
            
            # 获取最新文件信息
            latest_file = get_latest_txt_file()
            
            if not latest_file:
                logger.warning("未找到新文件")
            else:
                filename = latest_file['filename']
                
                # 检查是否已导入
                if check_if_imported(filename):
                    logger.info(f"文件已导入: {filename}")
                else:
                    # 下载并导入
                    download_and_import(latest_file)
            
            logger.info(f"下次检查时间: {CHECK_INTERVAL}秒后")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("")
            logger.info("收到停止信号，退出...")
            break
        except Exception as e:
            logger.error(f"检查过程出错: {e}")
            logger.info("等待60秒后重试...")
            time.sleep(60)


if __name__ == '__main__':
    main()
