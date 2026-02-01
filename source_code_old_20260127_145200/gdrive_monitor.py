#!/usr/bin/env python3
"""
Google Drive TXT文件监控器
每10分钟检查一次最新文件并自动导入
"""
import time
import requests
import re
import sqlite3
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/gdrive_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 配置
FOLDER_ID = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"  # 2025-12-09 folder
KNOWN_FILE_ID = "1eyYiU6lU8n7SwWUvFtm_kUIvaZI0SO4U"  # This ID updates with latest content
DB_PATH = '/home/user/webapp/crypto_data.db'
CHECK_INTERVAL = 600  # 10分钟

def download_latest_file():
    """下载最新文件内容"""
    try:
        url = f"https://drive.google.com/uc?export=download&id={KNOWN_FILE_ID}"
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"下载失败: HTTP {response.status_code}")
            return None
        
        content = response.text
        
        # 验证内容
        if '透明标签' not in content or 'BTC' not in content:
            logger.error("文件内容无效")
            return None
        
        return content
        
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return None

def parse_data(content):
    """解析TXT文件数据"""
    try:
        # 提取时间戳
        timestamps = re.findall(r'2025-12-09 (\d{2}:\d{2}:\d{2})', content)
        if not timestamps:
            logger.error("未找到时间戳")
            return None
        
        time_str = timestamps[0]
        hour = int(time_str.split(':')[0])
        minute = int(time_str.split(':')[1])
        snapshot_time = f"2025-12-09 {hour:02d}:{minute:02d}:00"
        
        # 提取数据
        rush_up = int(re.search(r'急涨：(\d+)', content).group(1))
        rush_down = int(re.search(r'急跌：(\d+)', content).group(1))
        count = int(re.search(r'透明标签_计次=(\d+)', content).group(1))
        status = re.search(r'透明标签_五种状态=(.+)', content).group(1).strip().replace('状态：', '')
        
        # 计算计次得分
        if hour >= 18:  # 18:00-23:59
            if count <= 3:
                count_score_display = "★★★★★"
            elif count <= 5:
                count_score_display = "★★★★"
            elif count <= 8:
                count_score_display = "★★★"
            elif count <= 12:
                count_score_display = "★★"
            elif count <= 20:
                count_score_display = "★"
            else:
                count_score_display = "---"
        else:  # Before 18:00
            if count <= 10:
                count_score_display = "☆---"
            elif count <= 20:
                count_score_display = "☆☆"
            elif count <= 30:
                count_score_display = "☆☆☆"
            else:
                count_score_display = "---"
        
        return {
            'snapshot_time': snapshot_time,
            'snapshot_date': '2025-12-09',
            'rush_up': rush_up,
            'rush_down': rush_down,
            'count': count,
            'count_score_display': count_score_display,
            'status': status
        }
        
    except Exception as e:
        logger.error(f"解析失败: {e}")
        return None

def import_to_database(data):
    """导入数据到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM crypto_snapshots WHERE snapshot_time = ?", 
                      (data['snapshot_time'],))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute("""
                UPDATE crypto_snapshots SET
                    rush_up = ?, rush_down = ?,
                    count = ?, count_score_display = ?,
                    status = ?
                WHERE snapshot_time = ?
            """, (data['rush_up'], data['rush_down'],
                  data['count'], data['count_score_display'],
                  data['status'], data['snapshot_time']))
            
            logger.info(f"✓ 更新记录: {data['snapshot_time']}")
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO crypto_snapshots 
                (snapshot_time, snapshot_date, rush_up, rush_down, 
                 count, count_score_display, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data['snapshot_time'], data['snapshot_date'],
                  data['rush_up'], data['rush_down'],
                  data['count'], data['count_score_display'],
                  data['status']))
            
            logger.info(f"✓ 插入新记录: {data['snapshot_time']}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        return False

def check_and_import():
    """检查并导入最新数据"""
    logger.info("="*60)
    logger.info("开始检查新数据...")
    
    # 1. 下载
    content = download_latest_file()
    if not content:
        logger.error("下载失败,跳过本次检查")
        return False
    
    # 2. 解析
    data = parse_data(content)
    if not data:
        logger.error("解析失败,跳过本次检查")
        return False
    
    logger.info(f"发现数据: {data['snapshot_time']} | 计次:{data['count']} {data['count_score_display']} | {data['status']}")
    
    # 3. 导入
    success = import_to_database(data)
    
    if success:
        logger.info("✓ 数据导入成功")
    else:
        logger.error("✗ 数据导入失败")
    
    return success

def main():
    """主循环"""
    logger.info("="*60)
    logger.info("Google Drive监控器启动")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒 ({CHECK_INTERVAL//60}分钟)")
    logger.info(f"数据库: {DB_PATH}")
    logger.info("="*60)
    
    # 立即执行第一次检查
    check_and_import()
    
    # 循环检查
    while True:
        try:
            logger.info(f"\n等待 {CHECK_INTERVAL//60} 分钟后下次检查...")
            time.sleep(CHECK_INTERVAL)
            
            check_and_import()
            
        except KeyboardInterrupt:
            logger.info("\n收到停止信号,正在退出...")
            break
        except Exception as e:
            logger.error(f"发生错误: {e}")
            logger.info("等待下次检查...")
            time.sleep(60)  # 出错后等待1分钟再继续

if __name__ == '__main__':
    main()
